"""Document template registry for automatic classification and mapping.

This module dynamically loads document templates from JSON files in the 'templates' directory.
"""

import os
import json
from typing import Any, Dict, List
from pathlib import Path
from loguru import logger

# Get the directory of the current file
TEMPLATE_DIR = Path(__file__).parent / "templates"

def load_templates() -> Dict[str, Dict[str, Any]]:
    """Load all JSON templates from the templates directory.
    
    Returns:
        Dictionary mapping template IDs (filenames) to their content.
    """
    templates = {}
    
    if not TEMPLATE_DIR.exists():
        logger.warning(f"Template directory not found: {TEMPLATE_DIR}")
        return {}
    
    for file_path in TEMPLATE_DIR.glob("*.json"):
        try:
            template_id = file_path.stem
            with open(file_path, "r", encoding="utf-8") as f:
                content = json.load(f)
                templates[template_id] = content
        except Exception as e:
            logger.error(f"Failed to load template {file_path.name}: {e}")
            
    return templates

# Singleton registry loaded on import
DOCUMENT_TEMPLATES: Dict[str, Dict[str, Any]] = load_templates()
