"""Advanced Spatial Extraction Engine for structured and tabular data."""

from typing import Any, Dict, List, Optional
import re
from rapidfuzz import fuzz

from app.services.extraction.base import ExtractionStrategy
from app.core.logging import get_logger

logger = get_logger("spatial_engine")

class SpatialExtractionEngine(ExtractionStrategy):
    """Engine that extracts data based purely on coordinate math."""

    def extract(
        self, 
        regions: List[Dict[str, Any]], 
        fields: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Perform spatial extraction."""
        if not regions:
            return {}

        template = kwargs.get("template") or {}
        
        # Ensure augmented
        if "_center_y" not in regions[0]:
            self.augment_spatial_metadata(regions)

        # Calculate document horizontal bounds to implement columnar constraints
        doc_max_x = max(r["_max_x"] for r in regions)
        doc_x_cutoff = doc_max_x * 0.85 # Cut off noise at the extreme right (85%)

        mapped_data = {}

        # 1. Extract Key-Value Fields
        fields_to_find = template.get("fields", fields or [])
        if fields_to_find:
            # Gather ALL known labels (anchors + fields + extra) to use as boundaries
            all_labels = []
            all_labels.extend(template.get("anchors", []))
            all_labels.extend(template.get("fields", []))
            all_labels.extend(template.get("extra_labels", []))
            
            mapped_data.update(self._extract_fields(regions, fields_to_find, all_labels, x_cutoff=doc_x_cutoff))

        # 1b. Apply pattern filtering (exclude_value_patterns)
        exclude_patterns = template.get("exclude_value_patterns", [])
        if exclude_patterns:
            for key, val in mapped_data.items():
                if isinstance(val, str):
                    for pattern in exclude_patterns:
                        mapped_data[key] = re.sub(pattern, "", mapped_data[key]).strip()

        # 2. Extract Tables
        tables = template.get("tables", [])
        for table_def in tables:
            table_name = table_def.get("name", "items")
            table_data = self._extract_table(regions, table_def)
            mapped_data[table_name] = table_data

        return mapped_data

    def _extract_fields(
        self, 
        regions: List[Dict[str, Any]], 
        fields: List[str], 
        boundary_labels: Optional[List[str]] = None,
        x_cutoff: Optional[float] = None
    ) -> Dict[str, str]:
        """Extract key-value pairs by looking to the right of an anchor, stopping at boundaries."""
        data = {}
        for field in fields:
            # 1. Find the anchor region
            best_r = None
            best_score = 0
            for r in regions:
                # Use stricter matching for anchors to avoid "Agama" matching "Nama"
                score = fuzz.partial_ratio(field.lower(), r["text"].lower())
                
                # Boost score if length is similar or ends with colon
                if score >= 85:
                    if len(r["text"]) < 5: # Short labels need higher precision
                        score = fuzz.ratio(field.lower(), r["text"].lower())
                    
                    if score > best_score and score >= 90: # Higher threshold (90)
                        best_score = score
                        best_r = r
                        
            if not best_r:
                continue
                
            clean_key = re.sub(r'[^a-zA-Z0-9]', '_', field).lower().strip('_')
            
            # 2. Identify the boundary to the right (if any other template label exists on the same line)
            x_boundary = x_cutoff or float('inf')
            y_tol = best_r["_height"] * 0.7
            
            if boundary_labels:
                for label in boundary_labels:
                    # Skip the current field label itself
                    if label.lower() == field.lower():
                        continue
                        
                    # Find if this label exists to the right on the same line
                    for r in regions:
                        if r["_center_x"] > (best_r["_max_x"] + 10): # Significant distance only
                            if abs(r["_center_y"] - best_r["_center_y"]) <= y_tol:
                                # Use strict ratio for boundary detection to avoid ':' matching 'NIK :'
                                if fuzz.ratio(label.lower(), r["text"].lower()) >= 85:
                                    # This is a boundary!
                                    if r["_min_x"] < x_boundary:
                                        x_boundary = r["_min_x"]

            # 3. Find regions to the right (same line) within boundaries
            matching_regions = []
            
            # Adaptive Jump Strategy:
            # - First word can be far (to jump aligned colon gap)
            # - Subsequent words must be close (to avoid picking footers)
            initial_gap = 450.0 # Enough to jump KTP colon layout
            proximity_gap = best_r["_height"] * 4.0
            
            line_regions = []
            for r in regions:
                if r["_center_x"] > (best_r["_max_x"] - 5): # Small overlap allowed
                    if r["_center_x"] < x_boundary:
                        if abs(r["_center_y"] - best_r["_center_y"]) <= y_tol:
                            line_regions.append(r)
            
            # Sort by X to process line left-to-right
            line_regions.sort(key=lambda x: x["_min_x"])
            
            current_x = best_r["_max_x"]
            found_data = False
            
            for r in line_regions:
                gap = r["_min_x"] - current_x
                
                # Determine limit based on whether we have started collecting data
                limit = initial_gap if not found_data else proximity_gap
                
                if gap < limit:
                    matching_regions.append(r)
                    current_x = r["_max_x"]
                    # Consider it "found data" if it's not a lonely colon
                    if re.search(r'[a-zA-Z0-9]', r["text"]):
                        found_data = True
                else:
                    # Gap too large!
                    break
            
            if matching_regions:
                # Combine text
                val = " ".join([r["text"] for r in matching_regions])
                data[clean_key] = val


        return data

    def _extract_table(self, regions: List[Dict[str, Any]], table_def: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract multi-row tabular data using column boundaries."""
        columns = table_def.get("columns", [])
        if not columns:
            return []

        # 1. Find column headers
        headers = []
        for col_name in columns:
            best_r = None
            best_score = 0
            for r in regions:
                score = fuzz.partial_ratio(col_name.lower(), r["text"].lower())
                if score > best_score and score >= 85:
                    best_score = score
                    best_r = r
            if best_r:
                clean_key = re.sub(r'[^a-zA-Z0-9]', '_', col_name).lower().strip('_')
                headers.append({
                    "name": col_name,
                    "key": clean_key,
                    "region": best_r,
                    "min_x": best_r["_min_x"],
                    "max_x": best_r["_max_x"],
                    "center_x": best_r["_center_x"]
                })

        if not headers:
            return []

        # Sort headers by X coordinate to establish left-to-right structure
        headers.sort(key=lambda h: h["center_x"])
        
        avg_height = sum(h["region"]["_height"] for h in headers) / len(headers)
        y_header_center = sum(h["region"]["_center_y"] for h in headers) / len(headers)

        # Calculate logical X boundaries for columns based on midpoint between headers
        for i, header in enumerate(headers):
            if i == 0:
                header["bound_left"] = 0
            else:
                header["bound_left"] = (headers[i-1]["max_x"] + header["min_x"]) / 2
                
            if i == len(headers) - 1:
                header["bound_right"] = float('inf')
            else:
                header["bound_right"] = (header["max_x"] + headers[i+1]["min_x"]) / 2

        # 2. Collect cells BELOW the headers and bin them into columns
        cells = []
        for r in regions:
            # Below the header (+ small tolerance so headers themselves aren't caught)
            if r["_center_y"] > (y_header_center + (avg_height * 0.8)):
                assigned_col = None
                for h in headers:
                    if h["bound_left"] <= r["_center_x"] <= h["bound_right"]:
                        assigned_col = h
                        break
                
                if assigned_col:
                    cells.append({
                        "text": r["text"],
                        "col": assigned_col["key"],
                        "center_y": r["_center_y"],
                        "min_x": r["_min_x"]
                    })

        if not cells:
            return []

        # 3. Y-Clustering (Group cells into distinct Rows)
        cells.sort(key=lambda x: x["center_y"])
        
        rows = []
        current_row_cells = [cells[0]]
        
        # Tolerance is very generous to catch multiline cells that belong to same row
        y_tol = avg_height * 0.8 
        
        for i in range(1, len(cells)):
            curr = cells[i]
            prev = cells[i-1]
            
            if abs(curr["center_y"] - prev["center_y"]) <= y_tol:
                current_row_cells.append(curr)
            else:
                rows.append(self._build_row_dict(current_row_cells))
                current_row_cells = [curr]
                
        if current_row_cells:
            rows.append(self._build_row_dict(current_row_cells))

        return rows

    def _build_row_dict(self, cells: List[Dict]) -> Dict[str, str]:
        """Combine cells into a dictionary representing a row."""
        row_dict = {}
        from collections import defaultdict
        grouped = defaultdict(list)
        for c in cells:
            grouped[c["col"]].append(c)
            
        for col_key, col_cells in grouped.items():
            # Sort horizontally inside the cell
            col_cells.sort(key=lambda x: x["min_x"])
            row_dict[col_key] = " ".join([c["text"] for c in col_cells])
            
        return row_dict
