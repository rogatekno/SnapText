
import re
from rapidfuzz import process, fuzz

def normalize(t: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '', t).lower().strip()

def perform_mapping(regions, target_labels):
    results = {}
    
    # Pre-process regions
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

    normalized_region_texts = [normalize(r["text"]) for r in regions]
    label_region_indices = set()
    active_mappings = []

    # 1. Identify all labels
    for label in target_labels:
        clean_key = re.sub(r'[^a-zA-Z0-9]', '_', label).lower().strip('_')
        results[clean_key] = None
        norm_label = normalize(label)
        if not norm_label: continue
        
        matches = process.extractOne(norm_label, normalized_region_texts, scorer=fuzz.WRatio)
        if matches and matches[1] >= 75:
            idx = matches[2]
            label_region_indices.add(idx)
            active_mappings.append((clean_key, regions[idx], idx))

    # 2. Find values
    for clean_key, label_region, match_idx in active_mappings:
        potential_values = []
        for i, r in enumerate(regions):
            if i in label_region_indices: continue
            if not normalize(r["text"]): continue # skip delimiters
            
            # Horizontal same-line
            v_dist = abs(r["_center_y"] - label_region["_center_y"])
            h_dist = r["_min_x"] - label_region["_max_x"]
            
            if v_dist < label_region["_height"] * 0.8 and 0 < h_dist < label_region["_width"] * 5:
                # Bonus for horizontal: multiplier 1x
                potential_values.append((r, h_dist))
                
            # Vertical below
            elif abs(r["_center_x"] - label_region["_center_x"]) < label_region["_width"] * 0.6:
                v_gap = r["_min_y"] - label_region["_max_y"]
                if 0 < v_gap < label_region["_height"] * 1.5:
                    # Penalty for vertical: multiplier 4x (increased from 3x)
                    potential_values.append((r, v_gap * 4))

        if potential_values:
            potential_values.sort(key=lambda x: x[1])
            val_text = potential_values[0][0]["text"]
            val_text = re.sub(r'^[:=\- ]+', '', val_text).strip()
            results[clean_key] = val_text
            
    return results

# KTP Simulation Data
# NIK is at Y=100. Nama is at Y=130 (close together)
# The Number is at X=200.
regions = [
    {"text": "NIK", "bbox": [[50, 100], [100, 100], [100, 120], [50, 120]]},
    {"text": ":", "bbox": [[120, 100], [130, 100], [130, 120], [120, 120]]},
    {"text": "3171234567890123", "bbox": [[150, 100], [350, 100], [350, 120], [150, 120]]},
    
    {"text": "Nama", "bbox": [[50, 130], [105, 130], [105, 150], [50, 150]]},
    {"text": ":", "bbox": [[120, 130], [130, 130], [130, 150], [120, 150]]},
    {"text": "MIRA SETIAWAN", "bbox": [[150, 130], [350, 130], [350, 150], [150, 150]]},
]

# Case 1: Search for NIK and Nama
target = ["NIK", "Nama"]
res = perform_mapping(regions, target)
print(f"Results: {res}")

assert res["nik"] == "3171234567890123"
assert res["nama"] == "MIRA SETIAWAN"
print("Validation Successful!")
