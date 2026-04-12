"""Unit tests for DocumentProcessor."""

import math
import numpy as np
import cv2
import pytest
from app.utils.document_processor import DocumentProcessor


def test_bytes_to_cv_and_back():
    processor = DocumentProcessor()
    img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    img_bytes = processor.cv_to_bytes(img)
    img_back = processor.bytes_to_cv(img_bytes)
    assert img_back.shape == (100, 100, 3)
    assert np.all(img_back == 255)


def test_enhance_document_preserves_color():
    """Enhancement should preserve the image's color channels."""
    processor = DocumentProcessor()
    # A colored test image (blue channel dominant)
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[:, :, 0] = 50  # blue channel
    img[:, :, 2] = 200  # red channel
    enhanced = processor.enhance_document(img)
    # Should remain 3-channel BGR
    assert enhanced.shape == (100, 100, 3)


def test_auto_preprocess_output_is_bytes():
    """auto_preprocess should return bytes without crashing."""
    processor = DocumentProcessor()
    img = np.ones((100, 100, 3), dtype=np.uint8) * 128
    img_bytes = processor.cv_to_bytes(img)
    result = processor.auto_preprocess(img_bytes)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_get_skew_angle_from_regions_horizontal():
    """Horizontal bboxes should report ~0 degree skew."""
    processor = DocumentProcessor()
    regions = [
        {"bbox": [[10, 50], [100, 50], [100, 70], [10, 70]]},
        {"bbox": [[10, 90], [100, 90], [100, 110], [10, 110]]},
    ]
    angle = processor.get_skew_angle_from_regions(regions)
    assert abs(angle) < 1.0


def test_get_skew_angle_from_regions_tilted():
    """Tilted bboxes should report non-zero skew angle."""
    processor = DocumentProcessor()
    tilt_deg = 10.0
    tilt_rad = math.radians(tilt_deg)
    # Top edge of a box tilted by 10 degrees
    p0 = [10, 50]
    p1 = [p0[0] + 80 * math.cos(tilt_rad), p0[1] + 80 * math.sin(tilt_rad)]
    regions = [
        {"bbox": [p0, p1, [p1[0], p1[1] + 20], [p0[0], p0[1] + 20]]},
    ]
    angle = processor.get_skew_angle_from_regions(regions)
    assert abs(angle - tilt_deg) < 2.0  # within 2 degrees


def test_rotate_regions_corrects_skew():
    """rotate_regions should normalize y-coordinates for tilted regions."""
    processor = DocumentProcessor()
    # Two regions that appear on the same row but with a tilt
    regions = [
        {"bbox": [[10, 50], [100, 55], [100, 75], [10, 70]], "text": "Label"},
        {"bbox": [[120, 58], [200, 63], [200, 83], [120, 78]], "text": "Value"},
    ]
    rotated = processor.rotate_regions(regions, angle_deg=5.0, img_w=300, img_h=150)
    # After correction, their center_y values should be closer together
    cy0 = rotated[0]["_center_y"]
    cy1 = rotated[1]["_center_y"]
    assert abs(cy0 - cy1) < 5  # should be near the same row
