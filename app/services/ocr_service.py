"""OCR service layer for business logic.

This module contains the business logic that orchestrates OCR operations,
coordinates between the API and repository layers, and handles
validation and error handling.
"""

import io
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image
from pydantic import ValidationError
from rapidfuzz import process, fuzz

from app.core.config import get_settings
from app.core.exceptions import (
    FileProcessingError,
    ImageFormatError,
    FileSizeError,
    OCRError,
)
from app.models.schemas import BoundingBox, TextRegion, OCRResult
from app.repositories.base import OCRRepositoryInterface
from app.repositories.ocr_repository import get_ocr_repository

settings = get_settings()


class OCRService:
    """Service for OCR operations.

    Coordinates between API endpoints and the OCR repository,
    handling validation, business logic, and response formatting.
    """

    def __init__(self, repository: Optional[OCRRepositoryInterface] = None):
        """Initialize OCR service.

        Args:
            repository: OCR repository instance (uses singleton if not provided)
        """
        self._repository = repository or get_ocr_repository()

    async def initialize(self) -> None:
        """Initialize the OCR service.

        Should be called on application startup to ensure
        the OCR model is loaded.
        """
        await self._repository.initialize()

    async def extract_text_from_file(
        self, file_content: bytes, filename: str, lang: str = "en"
    ) -> Dict[str, Any]:
        """Extract text from uploaded image file.

        Args:
            file_content: Raw file content as bytes
            filename: Original filename
            lang: OCR language code (e.g., 'en', 'id')

        Returns:
            OCR extraction result dictionary

        Raises:
            ValidationError: If file validation fails
            FileProcessingError: If file processing fails
            OCRError: If OCR extraction fails
        """
        # Validate and load image
        image = await self._validate_and_load_image(file_content, filename)

        # Extract text
        result = await self._repository.extract_text(image, lang)

        # Add metadata
        result["filename"] = filename

        return result

    async def map_text_from_file(
        self,
        file_content: bytes,
        filename: str,
        fields: List[str],
        tables: Optional[List[Dict[str, Any]]] = None,
        lang: str = "en",
    ) -> Dict[str, Any]:
        """Extract specific fields and tables from document.

        Args:
            file_content: Raw file content
            filename: Original filename
            fields: List of label strings for flat fields
            tables: List of table definitions (name and columns)
            lang: OCR language code

        Returns:
            Dictionary with flat fields and extracted tables
        """
        # 1. OCR the image
        ocr_result = await self.extract_text_from_file(file_content, filename, lang)
        regions = ocr_result.get("regions", [])

        if not regions:
            results = {re.sub(r'[^a-zA-Z0-9]', '_', f).lower().strip('_'): None for f in fields}
            if tables:
                for t in tables:
                    results[t["name"]] = []
            return results

        # 2. Extract flat fields
        results = self._perform_mapping(regions, fields)

        # 3. Extract tables if requested
        if tables:
            table_results = self._extract_tables(regions, tables)
            results.update(table_results)

        return results

    def _extract_tables(self, regions: List[Dict[str, Any]], table_definitions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Extract tabular data based on column headers."""
        from rapidfuzz import process, fuzz
        import re

        table_results = {}

        # 1. Group all regions into horizontal lines based on Y-overlap
        lines = []
        sorted_regions = sorted(regions, key=lambda x: x["_center_y"])
        
        if not sorted_regions:
            return {t["name"]: [] for t in table_definitions}

        current_line = [sorted_regions[0]]
        for i in range(1, len(sorted_regions)):
            r = sorted_regions[i]
            prev_r = current_line[-1]
            
            # If Y distance between centers is small enough, it's the same line
            # Threshold: 50% of average region height
            if abs(r["_center_y"] - prev_r["_center_y"]) < (r["_height"] * 0.5):
                current_line.append(r)
            else:
                lines.append(sorted(current_line, key=lambda x: x["_min_x"]))
                current_line = [r]
        lines.append(sorted(current_line, key=lambda x: x["_min_x"]))

        for table_def in table_definitions:
            name = table_def["name"]
            columns = table_def["columns"]
            table_results[name] = []
            
            # slugify column names for output keys
            col_keys = {col: re.sub(r'[^a-zA-Z0-9]', '_', col).lower().strip('_') for col in columns}
            
            # Find the header row
            header_line_idx = -1
            col_x_map = {} # maps col_name -> (min_x, max_x)
            
            for l_idx, line in enumerate(lines):
                line_text = " ".join([r["text"] for r in line])
                found_cols = 0
                temp_map = {}
                
                for col in columns:
                    match = process.extractOne(col, [r["text"] for r in line], scorer=fuzz.WRatio)
                    if match and match[1] > 75:
                        found_cols += 1
                        matched_region = line[match[2]]
                        temp_map[col] = (matched_region["_min_x"], matched_region["_max_x"])
                
                # If majority of columns found, assume this is the header row
                if found_cols >= len(columns) * 0.6:
                    header_line_idx = l_idx
                    col_x_map = temp_map
                    break
            
            if header_line_idx == -1:
                continue

            # Process rows below header
            for i in range(header_line_idx + 1, len(lines)):
                line = lines[i]
                row_data = {col_keys[col]: None for col in columns}
                has_any_data = False
                
                for r in line:
                    # Assign region to a column based on X-center proximity
                    best_col = None
                    min_dist = float('inf')
                    
                    for col, (c_min_x, c_max_x) in col_x_map.items():
                        # If region is within column bounds or very close to center
                        c_center = (c_min_x + c_max_x) / 2
                        dist = abs(r["_center_x"] - c_center)
                        
                        # Tolerance: 0.5 * column width or explicit overlap
                        if (c_min_x - r["_width"]*0.5 <= r["_center_x"] <= c_max_x + r["_width"]*0.5) or dist < (c_max_x - c_min_x):
                           if dist < min_dist:
                               min_dist = dist
                               best_col = col
                    
                    if best_col:
                        key = col_keys[best_col]
                        if row_data[key]:
                            row_data[key] += " " + r["text"]
                        else:
                            row_data[key] = r["text"]
                        has_any_data = True
                
                if has_any_data:
                    # Cleanup row data
                    for k, v in row_data.items():
                        if v:
                            row_data[k] = re.sub(r'^[:=\- ]+', '', v).strip()
                            if row_data[k] == "-": row_data[k] = None
                    
                    table_results[name].append(row_data)
                    
        return table_results

    def _perform_mapping(self, regions: List[Dict[str, Any]], target_labels: List[str]) -> Dict[str, Any]:
        """Perform spatial mapping of labels to values.

        Heuristics:
        - Labels are matched using fuzzy matching (RapidFuzz).
        - Values are expected to be either to the right of or below the label.
        - Common delimiters (:, =, -) are stripped.
        """
        results = {}

        def normalize(t: str) -> str:
            """Normalize text for better matching."""
            return re.sub(r'[^a-zA-Z0-9]', '', t).lower().strip()

        # Augment regions with spatial metadata for easier searching
        for r in regions:
            bbox = r["bbox"]
            # bbox: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            r["_min_x"], r["_max_x"] = min(xs), max(xs)
            r["_min_y"], r["_max_y"] = min(ys), max(ys)
            r["_center_x"] = (r["_min_x"] + r["_max_x"]) / 2
            r["_center_y"] = (r["_min_y"] + r["_max_y"]) / 2
            r["_height"] = r["_max_y"] - r["_min_y"]
            r["_width"] = r["_max_x"] - r["_min_x"]

        # 0. Identify all possible label matches first to exclude them from values
        label_region_indices = set()
        normalized_region_texts = [normalize(r["text"]) for r in regions]
        
        # 1. First pass: find all label regions
        active_mappings = [] # List of (clean_key, label, label_region, match_idx)
        
        for label in target_labels:
            clean_key = re.sub(r'[^a-zA-Z0-9]', '_', label).lower().strip('_')
            results[clean_key] = None
            
            norm_label = normalize(label)
            if not norm_label: continue
            
            matches = process.extractOne(norm_label, normalized_region_texts, scorer=fuzz.WRatio)
            if matches and matches[1] >= 75:
                match_idx = matches[2]
                label_region = regions[match_idx]
                label_region_indices.add(match_idx)
                active_mappings.append((clean_key, label, label_region, match_idx))

        # 2. Second pass: find values for each identified label
        for clean_key, label, label_region, match_idx in active_mappings:
            best_match_text = label_region["text"]
            
            # Try same-region value (e.g. "Nama: John")
            label_parts = re.split(r'[:=]', best_match_text, 1)
            if len(label_parts) > 1 and len(label_parts[1].strip()) > 1:
                results[clean_key] = label_parts[1].strip()
                continue

            # Look for values in other regions
            potential_values = []
            for i, r in enumerate(regions):
                if i in label_region_indices: # Skip any region that was identified as a label
                    continue
                
                # Skip delimiter-only regions
                if re.fullmatch(r'[:=\-\s\.]+ \d*', r["text"]) or not normalize(r["text"]):
                    continue

                # HEURISTIC A: Same line (horizontal), to the right
                v_dist = abs(r["_center_y"] - label_region["_center_y"])
                h_dist = r["_min_x"] - label_region["_max_x"]
                
                if v_dist < label_region["_height"] * 0.8 and 0 < h_dist < label_region["_width"] * 5:
                    # Give a bonus to horizontal (lower distance equivalent)
                    potential_values.append((r, h_dist, "horizontal"))

                # HEURISTIC B: Directly below (vertical)
                elif abs(r["_center_x"] - label_region["_center_x"]) < label_region["_width"] * 0.6:
                    v_gap = r["_min_y"] - label_region["_max_y"]
                    if 0 < v_gap < label_region["_height"] * 2.0:
                        # Apply a penalty to vertical distance to prioritize horizontal same-line values
                        potential_values.append((r, v_gap * 3, "vertical"))

            if potential_values:
                # Sort by effective distance
                potential_values.sort(key=lambda x: x[1])
                best_val_region = potential_values[0][0]
                val_text = best_val_region["text"]
                
                # Cleanup: remove leading colons/symbols
                val_text = re.sub(r'^[:=\- ]+', '', val_text).strip()
                results[clean_key] = val_text if len(val_text) > 0 else None

        return results

    async def visualize_file(
        self, file_content: bytes, filename: str
    ) -> Tuple[bytes, str, Dict[str, Any]]:
        """Create visualization with bounding boxes marked.

        Args:
            file_content: Raw file content as bytes
            filename: Original filename

        Returns:
            Tuple of (image bytes, format, metadata)

        Raises:
            ValidationError: If file validation fails
            FileProcessingError: If file processing fails
            OCRError: If visualization fails
        """
        # Validate and load image
        image = await self._validate_and_load_image(file_content, filename)

        # Create visualization
        annotated_image, metadata = await self._repository.visualize_detections(image)

        # Convert to bytes
        img_bytes = self._image_to_bytes(annotated_image, "PNG")

        return img_bytes, "PNG", metadata

    async def _validate_and_load_image(
        self, file_content: bytes, filename: str
    ) -> Image.Image:
        """Validate and load image from bytes.

        Args:
            file_content: Raw file content
            filename: Original filename

        Returns:
            PIL Image object

        Raises:
            FileSizeError: If file exceeds size limit
            ImageFormatError: If format is not supported
            FileProcessingError: If image loading fails
        """
        # Check file size
        file_size = len(file_content)
        if file_size > settings.max_upload_size_bytes:
            raise FileSizeError(
                filename=filename,
                size_bytes=file_size,
                max_size_bytes=settings.max_upload_size_bytes,
            )

        # Check file extension
        file_ext = self._get_file_extension(filename)
        if file_ext.lower() not in settings.allowed_extensions:
            raise ImageFormatError(
                filename=filename,
                format=file_ext,
                allowed_formats=settings.allowed_extensions,
            )

        # Try to load the image
        try:
            image = Image.open(io.BytesIO(file_content))

            # Verify image
            image.verify()

            # Reopen after verify (verify closes the file)
            image = Image.open(io.BytesIO(file_content))

            # Convert to RGB if necessary
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGB")

            # Optimize image size for memory efficiency
            image = self._optimize_image(image)

            return image

        except ImageFormatError:
            raise
        except Exception as e:
            raise FileProcessingError(
                message=f"Failed to process image: {str(e)}",
                filename=filename,
                details={"size_bytes": file_size, "extension": file_ext},
            ) from e

    def _optimize_image(self, image: Image.Image) -> Image.Image:
        """Optimize image by resizing if it exceeds max dimensions.

        This prevents excessive memory usage and potential crashes on 
        low-spec systems when processing very large images.

        Args:
            image: PIL Image object

        Returns:
            Optimized PIL Image object
        """
        max_dim = settings.ocr_max_dimension
        width, height = image.size

        if max(width, height) > max_dim:
            if width > height:
                new_width = max_dim
                new_height = int(height * (max_dim / width))
            else:
                new_height = max_dim
                new_width = int(width * (max_dim / height))

            from app.core.logging import get_logger
            logger = get_logger("ocr_service")
            logger.info(f"Optimizing image: resizing from {width}x{height} to {new_width}x{new_height}")

            # Use Lanczos for high-quality downsampling
            return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        return image

    @staticmethod
    def _get_file_extension(filename: str) -> str:
        """Extract file extension from filename.

        Args:
            filename: Original filename

        Returns:
            File extension without dot (e.g., 'jpg', 'png')

        Raises:
            FileProcessingError: If no extension found
        """
        parts = filename.rsplit(".", 1)
        if len(parts) != 2:
            raise FileProcessingError(
                message="File has no extension",
                filename=filename,
            )
        return parts[1]

    @staticmethod
    def _image_to_bytes(image: Image.Image, format: str = "PNG") -> bytes:
        """Convert PIL Image to bytes.

        Args:
            image: PIL Image object
            format: Image format (PNG, JPEG, etc.)

        Returns:
            Image bytes
        """
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        return buffer.getvalue()

    async def get_supported_formats(self) -> List[str]:
        """Get list of supported image formats.

        Returns:
            List of supported file extensions
        """
        return settings.allowed_extensions.copy()

    async def get_max_file_size(self) -> Dict[str, Any]:
        """Get maximum allowed file size.

        Returns:
            Dict with size in bytes and MB
        """
        return {
            "bytes": settings.max_upload_size_bytes,
            "mb": settings.max_upload_size_mb,
        }

    def is_ready(self) -> bool:
        """Check if OCR service is ready.

        Returns:
            True if service is initialized and ready
        """
        return self._repository.is_model_loaded()


# Singleton instance
_ocr_service: OCRService | None = None


def get_ocr_service() -> OCRService:
    """Get or create singleton OCR service instance.

    Returns:
        Cached OCRService instance
    """
    global _ocr_service

    if _ocr_service is None:
        _ocr_service = OCRService()

    return _ocr_service
