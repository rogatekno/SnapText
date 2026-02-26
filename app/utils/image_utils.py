"""Image processing utilities.

This module provides helper functions for image processing operations
used across the application.
"""

import io
from typing import Optional, Tuple

import numpy as np
from PIL import Image


def load_image_from_bytes(content: bytes) -> Image.Image:
    """Load PIL Image from bytes.

    Args:
        content: Image bytes

    Returns:
        PIL Image object

    Raises:
        ValueError: If image cannot be loaded
    """
    try:
        image = Image.open(io.BytesIO(content))
        image.verify()

        # Reopen after verify (verify closes the file)
        image = Image.open(io.BytesIO(content))

        return image
    except Exception as e:
        raise ValueError(f"Failed to load image: {str(e)}") from e


def image_to_bytes(image: Image.Image, format: str = "PNG", quality: int = 95) -> bytes:
    """Convert PIL Image to bytes.

    Args:
        image: PIL Image object
        format: Image format (PNG, JPEG, etc.)
        quality: Quality for lossy formats (default: 95)

    Returns:
        Image bytes
    """
    buffer = io.BytesIO()

    save_kwargs = {"format": format}

    # Add quality parameter for JPEG
    if format.upper() in ("JPEG", "JPG"):
        save_kwargs["quality"] = quality

    image.save(buffer, **save_kwargs)
    return buffer.getvalue()


def resize_image(
    image: Image.Image,
    max_width: Optional[int] = None,
    max_height: Optional[int] = None,
    maintain_aspect_ratio: bool = True,
) -> Image.Image:
    """Resize image while optionally maintaining aspect ratio.

    Args:
        image: PIL Image object
        max_width: Maximum width (None = no limit)
        max_height: Maximum height (None = no limit)
        maintain_aspect_ratio: Whether to maintain aspect ratio

    Returns:
        Resized PIL Image
    """
    if max_width is None and max_height is None:
        return image

    original_width, original_height = image.size

    # Calculate new dimensions
    if maintain_aspect_ratio:
        if max_width and max_height:
            # Both constraints - fit within bounds
            ratio = min(
                max_width / original_width,
                max_height / original_height,
            )
            new_width = int(original_width * ratio)
            new_height = int(original_height * ratio)
        elif max_width:
            # Width constraint only
            ratio = max_width / original_width
            new_width = max_width
            new_height = int(original_height * ratio)
        else:
            # Height constraint only
            ratio = max_height / original_height
            new_width = int(original_width * ratio)
            new_height = max_height
    else:
        new_width = max_width or original_width
        new_height = max_height or original_height

    # Only resize if dimensions changed
    if new_width != original_width or new_height != original_height:
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    return image


def convert_to_rgb(image: Image.Image) -> Image.Image:
    """Convert image to RGB format.

    Args:
        image: PIL Image object

    Returns:
        RGB PIL Image
    """
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def get_image_info(image: Image.Image) -> dict:
    """Get information about an image.

    Args:
        image: PIL Image object

    Returns:
        Dict with image metadata
    """
    return {
        "mode": image.mode,
        "size": image.size,
        "width": image.width,
        "height": image.height,
        "format": image.format,
        "has_transparency": image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info,
    }


def validate_image_dimensions(
    image: Image.Image,
    min_width: int = 1,
    min_height: int = 1,
    max_width: int = 10000,
    max_height: int = 10000,
) -> bool:
    """Validate image dimensions are within acceptable range.

    Args:
        image: PIL Image object
        min_width: Minimum width
        min_height: Minimum height
        max_width: Maximum width
        max_height: Maximum height

    Returns:
        True if valid, False otherwise
    """
    width, height = image.size
    return min_width <= width <= max_width and min_height <= height <= max_height


def create_thumbnail(
    image: Image.Image, size: Tuple[int, int] = (128, 128)
) -> Image.Image:
    """Create thumbnail of image.

    Args:
        image: PIL Image object
        size: Thumbnail size (width, height)

    Returns:
        Thumbnail PIL Image
    """
    thumbnail = image.copy()
    thumbnail.thumbnail(size, Image.Resampling.LANCZOS)
    return thumbnail


def get_file_extension(filename: str, default: str = "") -> str:
    """Extract file extension from filename.

    Args:
        filename: Original filename
        default: Default value if no extension

    Returns:
        File extension without dot (e.g., 'jpg', 'png')
    """
    parts = filename.rsplit(".", 1)
    return parts[1].lower() if len(parts) == 2 else default


def is_supported_image_format(filename: str, supported_formats: list[str]) -> bool:
    """Check if file has supported image format.

    Args:
        filename: Filename to check
        supported_formats: List of supported extensions

    Returns:
        True if format is supported
    """
    ext = get_file_extension(filename)
    return ext in [f.lower().lstrip(".") for f in supported_formats]
