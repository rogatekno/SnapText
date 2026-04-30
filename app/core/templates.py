"""Document template registry for automatic classification and mapping.

This module dynamically loads document templates from JSON files in the 'templates' directory.
Templates are reloaded automatically if any JSON file is modified (dev-friendly hot reload).
"""

import os
import json
from typing import Any, Dict
from pathlib import Path
from loguru import logger

# Get the directory of the current file
TEMPLATE_DIR = Path(__file__).parent / "templates"

# Internal cache: {template_id: (mtime, content)}
_template_cache: Dict[str, tuple] = {}


def load_templates() -> Dict[str, Dict[str, Any]]:
    """Load all JSON templates from the templates directory.

    Uses file modification time to detect changes — returns fresh data
    if any template file has been modified or added since last load.

    Returns:
        Dictionary mapping template IDs (filenames without .json) to their content.
    """
    templates = {}

    if not TEMPLATE_DIR.exists():
        logger.warning(f"Template directory not found: {TEMPLATE_DIR}")
        return {}

    for file_path in TEMPLATE_DIR.glob("*.json"):
        template_id = file_path.stem
        try:
            mtime = os.path.getmtime(file_path)
            cached = _template_cache.get(template_id)

            if cached and cached[0] == mtime:
                # File unchanged — use cache
                templates[template_id] = cached[1]
            else:
                # New or modified file — reload
                with open(file_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                _template_cache[template_id] = (mtime, content)
                templates[template_id] = content
                logger.info(f"Template loaded/reloaded: {file_path.name}")

        except Exception as e:
            logger.error(f"Failed to load template {file_path.name}: {e}")

    return templates


def get_templates() -> Dict[str, Dict[str, Any]]:
    """Get current templates, reloading from disk if any file has changed.

    Call this instead of accessing DOCUMENT_TEMPLATES directly when you need
    guaranteed freshness (e.g. in classify_document).
    """
    return load_templates()


# Singleton registry loaded on import (for backward compatibility)
DOCUMENT_TEMPLATES: Dict[str, Dict[str, Any]] = load_templates()
