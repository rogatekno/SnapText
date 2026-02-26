"""Pydantic models for request/response validation.

This module defines all schemas used for API request validation
and response formatting.
"""

from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Base Schemas
# ============================================================================


class BaseResponse(BaseModel):
    """Base response schema with common fields."""

    success: bool = Field(default=True, description="Request success status")
    message: Optional[str] = Field(None, description="Optional message")


class ErrorDetail(BaseModel):
    """Error detail schema."""

    code: str = Field(description="Error code for programmatic handling")
    message: str = Field(description="Human-readable error message")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional context")


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    success: bool = Field(default=False, description="Always false for errors")
    error: ErrorDetail = Field(description="Error details")


# ============================================================================
# Health Check Schemas
# ============================================================================


class HealthResponse(BaseResponse):
    """Health check response schema."""

    status: str = Field(description="Health status: 'healthy' or 'unhealthy'")
    version: str = Field(description="Application version")
    paddleocr_loaded: bool = Field(description="Whether PaddleOCR is loaded")
    environment: str = Field(description="Current environment (dev/prod)")


# ============================================================================
# OCR Schemas
# ============================================================================


class BoundingBox(BaseModel):
    """Bounding box coordinates for a text region.

    Coordinates are represented as 4 points: [x1,y1], [x2,y2], [x3,y3], [x4,y4]
    """

    coordinates: List[List[int]] = Field(
        description="4 corner points of the bounding box",
        min_length=4,
        max_length=4,
    )

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, v: List[List[int]]) -> List[List[int]]:
        """Validate bounding box coordinates.

        Args:
            v: List of coordinate pairs

        Returns:
            Validated coordinates

        Raises:
            ValueError: If coordinates are invalid
        """
        if len(v) != 4:
            raise ValueError("Bounding box must have exactly 4 points")

        for point in v:
            if len(point) != 2:
                raise ValueError("Each point must have exactly 2 coordinates (x, y)")
            if point[0] < 0 or point[1] < 0:
                raise ValueError("Coordinates must be non-negative")

        return v


class TextRegion(BaseModel):
    """Detected text region with metadata."""

    text: str = Field(description="Extracted text content")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score (0-1)"
    )
    bbox: BoundingBox = Field(description="Bounding box coordinates")
    region_id: Optional[int] = Field(None, description="Sequential region ID")


class OCRResult(BaseModel):
    """OCR extraction result."""

    text: str = Field(description="Full extracted text")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Average confidence score"
    )
    regions: List[TextRegion] = Field(
        default_factory=list, description="Individual text regions"
    )
    region_count: int = Field(default=0, description="Number of regions detected")
    language: Optional[str] = Field(None, description="Detected/specified language")


class OCRDataResponse(BaseResponse):
    """OCR extract endpoint data response."""

    data: OCRResult = Field(description="OCR extraction results")
    processing_time_ms: float = Field(description="Processing time in milliseconds")


# ============================================================================
# OCR Extract Request/Response
# ============================================================================


class OCRExtractResponse(OCRDataResponse):
    """Response schema for OCR extract endpoint."""

    pass


# ============================================================================
# OCR Visualize Schemas
# ============================================================================


class VisualizationMetadata(BaseModel):
    """Metadata for visualization response."""

    format: str = Field(description="Image format (e.g., 'png')")
    regions_marked: int = Field(description="Number of regions marked")
    processing_time_ms: float = Field(description="Processing time in milliseconds")


class OCRVisualizeHeaders(BaseModel):
    """Headers for visualize response."""

    x_regions_count: int = Field(description="Number of regions detected")
    x_processing_time_ms: float = Field(description="Processing time in ms")
    x_format: str = Field(description="Image format")


# ============================================================================
# Upload Schemas
# ============================================================================


class FileUploadMetadata(BaseModel):
    """Metadata about uploaded file."""

    filename: str = Field(description="Original filename")
    content_type: str = Field(description="MIME type")
    size_bytes: int = Field(ge=0, description="File size in bytes")
    size_mb: float = Field(description="File size in MB")


class UploadValidation(BaseModel):
    """Upload validation result."""

    valid: bool = Field(description="Whether upload is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")


# ============================================================================
# Batch OCR Schemas (Future Enhancement)
# ============================================================================


class BatchOCRRequest(BaseModel):
    """Request schema for batch OCR processing."""

    files: List[str] = Field(description="List of file identifiers")
    language: str = Field(default="en", description="OCR language")
    options: dict[str, Any] = Field(
        default_factory=dict, description="Additional processing options"
    )


class BatchOCRItem(BaseModel):
    """Single item in batch OCR result."""

    filename: str = Field(description="File identifier")
    success: bool = Field(description="Processing success status")
    result: Optional[OCRResult] = Field(None, description="OCR result if successful")
    error: Optional[str] = Field(None, description="Error message if failed")


class BatchOCRResponse(BaseResponse):
    """Response schema for batch OCR processing."""

    total: int = Field(description="Total number of files")
    successful: int = Field(description="Number of successful processes")
    failed: int = Field(description="Number of failed processes")
    results: List[BatchOCRItem] = Field(description="Individual results")
