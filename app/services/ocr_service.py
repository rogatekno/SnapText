"""OCR service layer for business logic.

This module contains the business logic that orchestrates OCR operations,
coordinates between the API and repository layers, and handles
validation and error handling.
"""

import io
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image
from pydantic import ValidationError
from rapidfuzz import process, fuzz

from app.core.config import get_settings
from app.core.templates import DOCUMENT_TEMPLATES
from app.core.exceptions import (
    FileProcessingError,
    ImageFormatError,
    FileSizeError,
    OCRError,
)
from app.models.schemas import BoundingBox, TextRegion, OCRResult
from app.repositories.base import OCRRepositoryInterface
from app.repositories.ocr_repository import RapidOCRRepository, get_ocr_repository
from app.utils.document_processor import DocumentProcessor

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
        self._doc_processor = DocumentProcessor()

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
        lang: str = "id",
        auto_preprocess: bool = True
    ) -> Dict[str, Any]:
        """Perform OCR and map extracted text to specific fields or tables.

        Args:
            file_content: Image file content
            filename: Original filename
            fields: List of labels to look for
            tables: Optional list of table definitions
            lang: OCR language
            auto_preprocess: Whether to automatically deskew and enhance image

        Returns:
            Mapped data and optional metadata
        """
        # Preprocess if requested
        if auto_preprocess:
            try:
                file_content = self._doc_processor.auto_preprocess(file_content)
            except Exception:
                # Fallback to original if preprocessing fails
                pass

        # Run OCR first
        ocr_result = await self.extract_text_from_file(file_content, filename, lang)
        regions = ocr_result.get("regions", [])
        
        document_type = None
        
        # If no fields provided, try auto-classification
        if not fields and not tables:
            document_type = self.classify_document(regions)
            if document_type:
                template = DOCUMENT_TEMPLATES[document_type]
                fields = template.get("fields", [])
                tables = template.get("tables", [])

        # Extract extra labels and exclude patterns from template
        extra_labels = []
        exclude_patterns = []
        mapping_strategy = "default"
        if document_type:
            template = DOCUMENT_TEMPLATES[document_type]
            extra_labels = template.get("extra_labels", [])
            exclude_patterns = template.get("exclude_value_patterns", [])
            mapping_strategy = template.get("mapping_strategy", "default")

        # Apply post-OCR coordinate skew correction (does NOT modify image)
        # This makes label-value spatial heuristics work for tilted photos
        if auto_preprocess and regions:
            try:
                skew_angle = self._doc_processor.get_skew_angle_from_regions(regions)
                if abs(skew_angle) > 1.0:  # Only correct if clearly tilted
                    # Get image dimensions for rotation center
                    import io as _io
                    from PIL import Image as _PILImage
                    _im = _PILImage.open(_io.BytesIO(file_content))
                    img_w, img_h = _im.size
                    regions = self._doc_processor.rotate_regions(regions, skew_angle, img_w, img_h)
            except Exception:
                pass  # Fallback: no skew correction

        if mapping_strategy == "sequential":
            mapped_data = self._perform_sequential_mapping(regions, fields, document_type)
        else:
            mapped_data = self._perform_mapping(regions, fields, extra_labels)

        # Perform table mapping if requested
        if tables:
            stop_keywords = template.get("stop_keywords", []) if document_type else []
            table_results = self._extract_tables(regions, tables, stop_keywords=stop_keywords)
            mapped_data.update(table_results)

        # Add document type if detected
        if document_type:
            mapped_data["_document_type"] = document_type

        # Post-process and format values
        for key, val in mapped_data.items():
            if isinstance(val, str):
                # Apply template-level exclusion patterns first
                for pattern in exclude_patterns:
                    val = re.sub(pattern, '', val, flags=re.IGNORECASE).strip()
                # Strip leftover separators/punctuation after pattern removal
                val = re.sub(r'^[,\s·:;=\-]+|[,\s·:;=\-]+$', '', val).strip()
                mapped_data[key] = self._format_value(key, val) if val else None

        return mapped_data

    def classify_document(self, regions: List[Dict[str, Any]]) -> Optional[str]:
        """Classify document type based on anchor keywords in regions.

        Strategy:
        1. First check exclusive_anchors - if partial fuzzy match found, immediately return that type.
           This handles cases like KK ('KARTU KELUARGA') vs KTP who share many words.
        2. Fall back to scoring all anchors and returning highest match count.

        Args:
            regions: List of detected text regions

        Returns:
            Detected document type key (e.g., 'ktp', 'kk') or None
        """
        if not regions:
            return None

        # Concatenated text for document-wide search
        raw_full_text = " ".join(r["text"] for r in regions).lower()
        
        def normalize(t: str) -> str:
            return re.sub(r'[^a-zA-Z0-9]', '', t).lower().strip()

        normalized_full_text = normalize(raw_full_text)
        normalized_region_texts = [normalize(r["text"]) for r in regions]

        # 1. EXCLUSIVE anchor check — highest priority
        # Use fuzzy partial match on the full text to handle multi-line or noisy titles
        for doc_type, template in DOCUMENT_TEMPLATES.items():
            for anchor in template.get("exclusive_anchors", []):
                # Check for near-exact match on concatenated text
                if fuzz.partial_ratio(anchor.lower(), raw_full_text) >= 90:
                    return doc_type
                # Also check normalized version
                norm_anchor = normalize(anchor)
                if norm_anchor and norm_anchor in normalized_full_text:
                    return doc_type

        # 2. Fuzzy scoring across all anchors
        best_type = None
        max_matches = 0

        for doc_type, template in DOCUMENT_TEMPLATES.items():
            anchors = template.get("anchors", [])
            match_count = 0

            for anchor in anchors:
                norm_anchor = normalize(anchor)
                if not norm_anchor:
                    continue

                # Look for high confidence fuzzy matches in individual regions
                matches = process.extractOne(norm_anchor, normalized_region_texts, scorer=fuzz.ratio)
                if matches and matches[1] >= 85:
                    match_count += 1

            if match_count > 0 and match_count >= max_matches:
                max_matches = match_count
                best_type = doc_type

        return best_type

    def _extract_tables(self, regions: List[Dict[str, Any]], table_definitions: List[Dict[str, Any]], stop_keywords: List[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Extract tabular data based on column headers.
        
        Args:
            regions: List of text regions
            table_definitions: List of table schemas from template
            stop_keywords: Optional list of keywords that trigger early termination (e.g. signature areas)
        """
        from rapidfuzz import process, fuzz
        import re

        table_results = {}
        stop_keywords = [s.lower() for s in (stop_keywords or [])]

        # Filter out regions that look like noise/indices (e.g. "(1)", "(2)")
        def is_index_noise(text: str) -> bool:
            return bool(re.match(r'^\(\d+\)$', text.strip()))

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
            if abs(r["_center_y"] - prev_r["_center_y"]) < (r["_height"] * 0.5):
                current_line.append(r)
            else:
                lines.append(sorted(current_line, key=lambda x: x["_min_x"]))
                current_line = [r]
        lines.append(sorted(current_line, key=lambda x: x["_min_x"]))

        # 2. Extract each table defined in the template
        for table_def in table_definitions:
            name = table_def["name"]
            columns = table_def["columns"]
            table_results[name] = []
            
            col_keys = {col: re.sub(r'[^a-zA-Z0-9]', '_', col).lower().strip('_') for col in columns}
            
            # Find the header row
            header_line_idx = -1
            col_x_map = {} 
            
            for l_idx, line in enumerate(lines):
                # STOP if we hit a terminal keyword (global footer detection)
                line_text = " ".join([r["text"] for r in line]).lower()
                if any(sk in line_text for sk in stop_keywords):
                    break

                found_cols = 0
                temp_map = {}
                
                for col in columns:
                    match = process.extractOne(col, [r["text"] for r in line], scorer=fuzz.WRatio)
                    if match and match[1] >= 80:
                        found_cols += 1
                        matched_region = line[match[2]]
                        temp_map[col] = (matched_region["_min_x"], matched_region["_max_x"])
                
                if found_cols >= len(columns) * 0.5: # Lowered threshold slightly for noisy KK headers
                    header_line_idx = l_idx
                    col_x_map = temp_map
                    break
            
            if header_line_idx == -1:
                continue

            # 3. Process rows below header
            for i in range(header_line_idx + 1, len(lines)):
                line = lines[i]
                line_text = " ".join([r["text"] for r in line]).lower()
                
                # Check for stop keywords SPECIFIC to this table extraction
                if any(sk in line_text for sk in stop_keywords):
                    break

                # Filter out pure index rows (e.g. "(1) (2) (3)")
                non_noise_regions = [r for r in line if not is_index_noise(r["text"])]
                if not non_noise_regions:
                    continue

                row_data = {col_keys[col]: None for col in columns}
                has_any_data = False
                
                for r in line:
                    if is_index_noise(r["text"]): continue

                    best_col = None
                    min_dist = float('inf')
                    
                    for col, (c_min_x, c_max_x) in col_x_map.items():
                        c_center = (c_min_x + c_max_x) / 2
                        dist = abs(r["_center_x"] - c_center)
                        
                        # Tolerance: 0.8 * column width
                        col_w = c_max_x - c_min_x
                        if (c_min_x - col_w*0.3 <= r["_center_x"] <= c_max_x + col_w*0.3) or dist < col_w:
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
                    significant_field_count = 0
                    for k, v in row_data.items():
                        if v:
                            # Strip leading/trailing symbols, including common KK dashes
                            v_clean = re.sub(r'^[,\s·:;=\-]+|[,\s·:;=\-]+$', '', v).strip()
                            if v_clean and v_clean != "-":
                                # Skip very common placeholders like just a dot or a single non-word char
                                if len(v_clean) > 1 or v_clean.isalnum():
                                    row_data[k] = v_clean
                                    # Don't count "no" or "no_" column as significant data for empty row check
                                    if k not in ["no", "no_"]:
                                        significant_field_count += 1
                                else:
                                    row_data[k] = None
                            else:
                                row_data[k] = None
                    
                    # Only append if at least one significant field (besides row index) was found
                    if significant_field_count > 0:
                        table_results[name].append(row_data)
                    
        return table_results

    def _perform_mapping(self, regions: List[Dict[str, Any]], target_labels: List[str], extra_exclude_labels: List[str] = None) -> Dict[str, Any]:
        """Perform spatial mapping of labels to values.

        Heuristics:
        - Labels are matched using fuzzy matching (RapidFuzz).
        - Values are expected to be either to the right of or below the label.
        - Common delimiters (:, =, -) are stripped.
        - extra_exclude_labels: Additional labels (e.g. "Gol. Darah") whose regions
          should be excluded from value matching but not output as fields.
        """
        results = {}
        extra_exclude_labels = extra_exclude_labels or []

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
        
        # 1. First pass: find all label regions (target + extra exclusion labels)
        active_mappings = []  # List of (clean_key, label, label_region, match_idx)
        all_labels_to_find = [(l, True) for l in target_labels] + [(l, False) for l in extra_exclude_labels]
        
        for label, is_target in all_labels_to_find:
            norm_label = normalize(label)
            if not norm_label: continue
            
            if is_target:
                clean_key = re.sub(r'[^a-zA-Z0-9]', '_', label).lower().strip('_')
                results[clean_key] = None

            matches = process.extractOne(norm_label, normalized_region_texts, scorer=fuzz.WRatio)
            if matches and matches[1] >= 75:
                match_idx = matches[2]
                label_region = regions[match_idx]
                label_region_indices.add(match_idx)
                if is_target:
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
                
                # Skip regions that are empty or contain ONLY delimiters and no alphanumeric content
                if not normalize(r["text"]):
                    continue

                # HEURISTIC A: Same line (horizontal), to the right
                # Tightened horizontal tolerance (2.2x height) to avoid cross-column bleeding in 2-column layouts
                v_dist = abs(r["_center_y"] - label_region["_center_y"])
                h_dist = r["_min_x"] - label_region["_max_x"]
                
                if v_dist < label_region["_height"] * 0.8 and 0 < h_dist < label_region["_width"] * 2.2:
                    # Give a bonus to horizontal (lower distance equivalent)
                    potential_values.append((r, h_dist, "horizontal"))

                # HEURISTIC B: Directly below (vertical)
                elif abs(r["_center_x"] - label_region["_center_x"]) < label_region["_width"] * 0.7:
                    v_gap = r["_min_y"] - label_region["_max_y"]
                    if 0 < v_gap < label_region["_height"] * 2.0:
                        # Apply a penalty to vertical distance to prioritize horizontal same-line values
                        potential_values.append((r, v_gap * 3, "vertical"))

            if potential_values:
                # 1. Sort by effective distance
                potential_values.sort(key=lambda x: x[1])
                
                # 2. Heuristic: If horizontal, collect ALL regions on the same line to the right
                if potential_values[0][2] == "horizontal":
                    line_regions = []
                    label_y = label_region["_center_y"]
                    label_h = label_region["_height"]
                    
                    # Sort by X first so we process left-to-right
                    horizontal_regions = [(r, dist) for r, dist, strategy in potential_values if strategy == "horizontal" and abs(r["_center_y"] - label_y) < label_h * 0.8]
                    horizontal_regions.sort(key=lambda x: x[0]["_min_x"])
                    
                    for r, dist in horizontal_regions:
                        # Gap threshold: based on previous joining region's width (not label width)
                        # This prevents absorbing Gol.Darah which is far to the right
                        if not line_regions:
                            line_regions.append(r)
                        else:
                            prev = line_regions[-1]
                            gap = r["_min_x"] - prev["_max_x"]
                            max_gap = max(prev["_width"] * 0.8, label_region["_height"] * 2.0)
                            if gap < max_gap:
                                line_regions.append(r)
                            else:
                                break  # Large gap = separate element (e.g. blood type / photo area)
                    
                    # Sort by X to ensure correct order
                    line_regions.sort(key=lambda x: x["_min_x"])
                    val_text = " ".join([r["text"] for r in line_regions])
                else:
                    # For vertical, just take the closest one for now
                    best_val_region = potential_values[0][0]
                    val_text = best_val_region["text"]
                
                # Cleanup: remove leading colons/symbols (including full-width equivalents)
                val_text = re.sub(r'^[:：=＝\-\－\.． ]+', '', val_text).strip()
                results[clean_key] = val_text if len(val_text) > 0 else None

        return results

    def _perform_sequential_mapping(self, regions: List[Dict[str, Any]], fields: List[str], doc_type: str) -> Dict[str, Any]:
        """Map fields based on vertical sequence below a primary anchor.
        
        Used for documents like BPJS TK that have no labels but a fixed vertical layout.
        """
        results = {re.sub(r'[^a-zA-Z0-9]', '_', f).lower().strip('_'): None for f in fields}
        
        # 0. Prep spatial metadata
        for r in regions:
            bbox = r["bbox"]
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            r["_min_x"], r["_max_x"] = min(xs), max(xs)
            r["_min_y"], r["_max_y"] = min(ys), max(ys)
            r["_center_x"] = (r["_min_x"] + r["_max_x"]) / 2
            r["_center_y"] = (r["_min_y"] + r["_max_y"]) / 2
            r["_height"] = r["_max_y"] - r["_min_y"]
            r["_width"] = r["_max_x"] - r["_min_x"]

        # 1. Find the primary anchor
        template = DOCUMENT_TEMPLATES.get(doc_type, {})
        anchors = template.get("anchors", [])
        primary_anchor_region = None
        
        for r in regions:
            for anchor in anchors:
                if anchor.lower() in r["text"].lower():
                    primary_anchor_region = r
                    break
            if primary_anchor_region: break
            
        if not primary_anchor_region:
            return results

        # 2. Find all regions below the anchor
        below_regions = []
        anchor_bottom = primary_anchor_region["_max_y"]
        
        for r in regions:
            if r["_min_y"] > anchor_bottom and r != primary_anchor_region:
                # Filter out regions that are too far right (likely QR codes)
                if r["_center_x"] < primary_anchor_region["_max_x"] * 1.5:
                    below_regions.append(r)
        
        # 3. Group regions into lines
        lines = []
        if not below_regions:
            return results
            
        sorted_below = sorted(below_regions, key=lambda x: x["_center_y"])
        current_line = [sorted_below[0]]
        
        for i in range(1, len(sorted_below)):
            r = sorted_below[i]
            prev_r = current_line[-1]
            if abs(r["_center_y"] - prev_r["_center_y"]) < (r["_height"] * 0.7):
                current_line.append(r)
            else:
                lines.append(" ".join([x["text"] for x in sorted(current_line, key=lambda x: x["_min_x"])]))
                current_line = [r]
        lines.append(" ".join([x["text"] for x in sorted(current_line, key=lambda x: x["_min_x"])]))
        
        # 4. Map lines to fields sequentially
        field_keys = [re.sub(r'[^a-zA-Z0-9]', '_', f).lower().strip('_') for f in fields]
        
        for i, val in enumerate(lines):
            if i < len(field_keys):
                results[field_keys[i]] = val
                
        return results

    def _format_value(self, key: str, value: str) -> str:
        """Apply formatting rules based on field key."""
        if not value:
            return value

        # 1. Normalize spaces
        value = re.sub(r'\s+', ' ', value).strip()

        # 2. Key-specific formatting
        low_key = key.lower()
        
        # Preserve NIK as uppercase
        if "nik" in low_key:
            return value.upper()

        # Title Case for name-related and other descriptive fields
        # Matches: nama, pekerjaan, alamat, agama, status, etc.
        name_patterns = ["nama", "kepala_keluarga", "lengkap", "tempat", "pekerjaan", "agama", "status", "alamat", "kewarganegaraan", "faskes", "jenis_kelamin", "kelurahan", "kecamatan", "desa"]
        if any(p in low_key for p in name_patterns):
            # Only apply title case if it's currently uppercase or looks like raw OCR noise
            # or if it's a multi-word string that is mostly lowercase/mixed
            if value.isupper() or len(value.split()) >= 1:
                return value.title()

        return value

    async def generate_debug_image(
        self, file_content: bytes, filename: str, lang: str = "id"
    ) -> Optional[str]:
        """Generate a debug image with preprocessing applied and OCR bounding boxes drawn.

        Returns:
            Base64-encoded PNG string, or None if generation fails.
        """
        import base64
        import cv2 as _cv2
        import numpy as _np

        try:
            # Apply preprocessing (same as smart-scan)
            preprocessed = file_content
            try:
                preprocessed = self._doc_processor.auto_preprocess(file_content)
            except Exception:
                pass

            # Run OCR on preprocessed image
            ocr_result = await self.extract_text_from_file(preprocessed, filename, lang)
            regions = ocr_result.get("regions", [])

            # Load preprocessed image for drawing
            nparr = _np.frombuffer(preprocessed, _np.uint8)
            img = _cv2.imdecode(nparr, _cv2.IMREAD_COLOR)
            if img is None:
                return None

            # Draw bounding boxes and label text
            for r in regions:
                bbox = r.get("bbox", [])
                text = r.get("text", "")
                if len(bbox) < 4:
                    continue

                pts = _np.array(bbox, _np.int32).reshape((-1, 1, 2))
                _cv2.polylines(img, [pts], isClosed=True, color=(0, 200, 80), thickness=2)
                # Draw text label above the box
                x, y = int(bbox[0][0]), max(int(bbox[0][1]) - 4, 12)
                _cv2.putText(img, text[:40], (x, y), _cv2.FONT_HERSHEY_SIMPLEX,
                             0.45, (0, 100, 255), 1, _cv2.LINE_AA)

            _, buf = _cv2.imencode(".png", img)
            return base64.b64encode(buf.tobytes()).decode("utf-8")

        except Exception:
            return None

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
