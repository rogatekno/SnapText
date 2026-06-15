"""Base interface for data extraction strategies."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class ExtractionStrategy(ABC):
    """Abstract base class for extraction engines."""

    @staticmethod
    def augment_spatial_metadata(regions: List[Dict[str, Any]]) -> None:
        """Add centroid and dimensional metadata to OCR regions."""
        for r in regions:
            bbox = r.get("bbox")
            if not bbox:
                r.update({"_min_x": 0, "_max_x": 0, "_min_y": 0, "_max_y": 0, "_center_x": 0, "_center_y": 0, "_height": 0, "_width": 0})
                continue
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            r["_min_x"], r["_max_x"] = min(xs), max(xs)
            r["_min_y"], r["_max_y"] = min(ys), max(ys)
            r["_center_x"] = (r["_min_x"] + r["_max_x"]) / 2
            r["_center_y"] = (r["_min_y"] + r["_max_y"]) / 2
            r["_height"] = r["_max_y"] - r["_min_y"]
            r["_width"] = r["_max_x"] - r["_min_x"]

    @abstractmethod
    def extract(
        self, 
        regions: List[Dict[str, Any]], 
        fields: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Perform data extraction from OCR regions.
        
        Args:
            regions: List of OCR detected text regions with coordinates.
            fields: Optional list of specific fields to look for.
            
        Returns:
            Dictionary of extracted key-value pairs.
        """
        pass
