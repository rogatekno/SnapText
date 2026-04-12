"""Document image preprocessing utilities.

This module provides tools for image enhancement and skew-correction
specifically optimized for documents like ID cards.

Design principle:
- `auto_preprocess` only performs SAFE image enhancement (contrast, denoise).
  It does NOT rotate the image, since rotation changes coordinates and
  breaks the spatial label-value mapping.
- Skew correction is done in coordinate-space AFTER OCR, via
  `get_skew_angle_from_regions` + `rotate_regions`, so the mapping
  heuristics work correctly without distorting the image.
"""

import math
import cv2
import numpy as np
from PIL import Image
from typing import List, Dict, Any, Optional, Tuple


class DocumentProcessor:
    """Processor for document-specific image manipulation."""

    @staticmethod
    def bytes_to_cv(image_bytes: bytes) -> np.ndarray:
        """Convert image bytes to OpenCV (BGR) format."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img

    @staticmethod
    def cv_to_bytes(img: np.ndarray, fmt: str = ".png") -> bytes:
        """Convert OpenCV image to bytes."""
        _, buffer = cv2.imencode(fmt, img)
        return buffer.tobytes()

    @staticmethod
    def pil_to_cv(pil_img: Image.Image) -> np.ndarray:
        """Convert PIL Image to OpenCV (BGR) format."""
        open_cv_image = np.array(pil_img)
        if len(open_cv_image.shape) == 3:
            open_cv_image = open_cv_image[:, :, ::-1].copy()
        return open_cv_image

    @staticmethod
    def cv_to_pil(cv_img: np.ndarray) -> Image.Image:
        """Convert OpenCV (BGR) image to PIL Image."""
        color_converted = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        return Image.fromarray(color_converted)

    def enhance_document(self, img: np.ndarray) -> np.ndarray:
        """Apply gentle document-focused image enhancement.
        
        Strategy:
        - CLAHE on the luminance channel only (preserve color)
        - Light denoising
        - NO rotation, NO sharpening (these cause OCR layout issues)
        """
        # Work in YCrCb to enhance only luminance (preserves color for OCR)
        ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycrcb)

        # Apply CLAHE to Y channel (luminance)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        y_enhanced = clahe.apply(y)

        # Gentle denoise on luminance
        y_denoised = cv2.fastNlMeansDenoising(y_enhanced, None, h=7, templateWindowSize=7, searchWindowSize=15)

        # Merge back
        merged = cv2.merge([y_denoised, cr, cb])
        return cv2.cvtColor(merged, cv2.COLOR_YCrCb2BGR)

    def auto_preprocess(self, img_bytes: bytes) -> bytes:
        """Perform safe document enhancement (NO rotation).
        
        Rotation is intentionally excluded because:
        - Rotating changes region coordinates which breaks spatial mapping
        - Skew correction is handled post-OCR via rotate_regions()
        """
        img = self.bytes_to_cv(img_bytes)
        img = self.enhance_document(img)
        return self.cv_to_bytes(img)

    # ─────────────────────────────────────────────────────────────────────
    # Post-OCR coordinate-space skew correction
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def get_skew_angle_from_regions(regions: List[Dict[str, Any]]) -> float:
        """Estimate document skew angle from OCR region bounding boxes.
        
        Uses the median angle of the bottom edge of each bbox to compute
        the overall document tilt in degrees.
        """
        angles = []
        for r in regions:
            bbox = r.get("bbox", [])
            if len(bbox) < 4:
                continue
            # Bottom edge: from point[3] to point[2] (or [0] to [1])
            # We use top edge: [0] -> [1]
            p0, p1 = bbox[0], bbox[1]
            dx = p1[0] - p0[0]
            dy = p1[1] - p0[1]
            if abs(dx) > 5:  # only consider near-horizontal edges
                angle_deg = math.degrees(math.atan2(dy, dx))
                angles.append(angle_deg)

        if not angles:
            return 0.0

        return float(np.median(angles))

    @staticmethod
    def rotate_point(x: float, y: float, cx: float, cy: float, angle_rad: float) -> Tuple[float, float]:
        """Rotate a 2D point around a center by angle_rad radians."""
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        nx = cos_a * (x - cx) - sin_a * (y - cy) + cx
        ny = sin_a * (x - cx) + cos_a * (y - cy) + cy
        return nx, ny

    def rotate_regions(self, regions: List[Dict[str, Any]], angle_deg: float,
                       img_w: float, img_h: float) -> List[Dict[str, Any]]:
        """Rotate all region bounding box coordinates around the image center.
        
        This corrects skew in coordinate-space without modifying the image.
        Returns regions with updated _center_x, _center_y etc. spatial metadata.
        """
        if abs(angle_deg) < 0.5:
            return regions  # No correction needed

        cx, cy = img_w / 2, img_h / 2
        angle_rad = math.radians(-angle_deg)  # Negate to correct skew

        for r in regions:
            bbox = r.get("bbox", [])
            if not bbox:
                continue

            rotated_pts = [self.rotate_point(p[0], p[1], cx, cy, angle_rad) for p in bbox]

            xs = [p[0] for p in rotated_pts]
            ys = [p[1] for p in rotated_pts]

            r["_min_x"] = min(xs)
            r["_max_x"] = max(xs)
            r["_min_y"] = min(ys)
            r["_max_y"] = max(ys)
            r["_center_x"] = (r["_min_x"] + r["_max_x"]) / 2
            r["_center_y"] = (r["_min_y"] + r["_max_y"]) / 2
            r["_height"] = r["_max_y"] - r["_min_y"]
            r["_width"] = r["_max_x"] - r["_min_x"]

        return regions
