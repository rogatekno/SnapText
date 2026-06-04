"""Local LLM Extraction Engine for structuring data.

Uses document templates (JSON) as the single source of truth for:
- Field rules and descriptions
- Noise labels to pre-filter from OCR text
- Output schema
- Few-shot examples

Adding a new document type = add a new JSON template file. No Python changes needed.
"""

import json
import re
import time
import os
from typing import Any, Dict, List, Optional

from llama_cpp import Llama

from app.services.extraction.base import ExtractionStrategy
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("llm_engine")
settings = get_settings()

# Generic fallback rules for documents without llm_field_rules in their template
_GENERIC_RULES = [
    "Extract all relevant key-value pairs from the OCR text.",
    "Use snake_case for all keys.",
    "Use null for any field not found.",
    "CRITICAL: Always preserve spaces between words in Names and Addresses (e.g. 'MIRA SETIAWAN' not 'MIRASETIAWAN').",
    "CRITICAL: If the OCR text merged words without spaces (e.g. 'LUKISETIAWAN' or 'DUSUNNARINGUL'), you MUST fix it by adding the correct spaces (e.g. 'LUKI SETIAWAN' and 'DUSUN NARINGUL'). Do NOT change the spelling of the words, only insert missing spaces.",
]


class LLMExtractionEngine(ExtractionStrategy):
    """Engine that uses a local LLM to format and extract data.

    Prompt construction is fully driven by document JSON templates.
    To support a new document format, add a new template file to
    app/core/templates/ with the llm_* fields populated.
    """

    def __init__(self):
        self._llm = None
        self._is_loaded = False

    def initialize(self):
        """Load the model into memory. Downloads from HF if missing."""
        if not self._is_loaded:
            model_path = settings.llm_model_path
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(model_path), exist_ok=True)

            if not os.path.exists(model_path):
                repo_id = os.getenv("LLM_MODEL_REPO", "Qwen/Qwen2.5-0.5B-Instruct-GGUF")
                filename = os.getenv("LLM_MODEL_FILE", "qwen2.5-0.5b-instruct-q4_k_m.gguf")
                
                logger.info(f"LLM model not found at {model_path}. Attempting to download {filename} from {repo_id}...")
                try:
                    from huggingface_hub import hf_hub_download
                    import shutil

                    # Download to cache first (guaranteed writeable)
                    downloaded_path = hf_hub_download(
                        repo_id=repo_id,
                        filename=filename,
                        cache_dir="/tmp/huggingface_cache"
                    )
                    
                    # Try to move it to the final destination
                    try:
                        os.makedirs(os.path.dirname(model_path), exist_ok=True)
                        shutil.copy2(downloaded_path, model_path)
                        logger.info(f"Model persisted to {model_path}")
                    except Exception as persist_error:
                        logger.warning(f"Could not persist model to {model_path}: {persist_error}. Using cached version instead.")
                        model_path = downloaded_path
                        
                    logger.info(f"Model ready at: {model_path}")
                except Exception as e:
                    logger.error(f"Failed to download model from Hugging Face: {e}")
                    return

            logger.info(f"Loading LLM model from: {model_path} on CPU")
            try:
                # Cap at 4 threads — more threads on CPU causes contention in llama-cpp,
                # especially on Windows where thread overhead is significant.
                n_threads = min(os.cpu_count() or 4, 4)
                logger.info(f"Initializing Llama with n_threads={n_threads}, use_mmap=True")
                self._llm = Llama(
                    model_path=model_path,
                    n_ctx=settings.llm_n_ctx,
                    n_gpu_layers=0,
                    n_threads=n_threads,
                    n_batch=256,  # Reduced for balanced CPU usage in shared environments
                    use_mmap=True,
                    use_mlock=False,
                    verbose=False,
                )
                self._is_loaded = True
                logger.info("LLM model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load LLM model: {e}")

    def extract(
        self,
        regions: List[Dict[str, Any]],
        fields: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Perform extraction using LLM.

        Args:
            regions: OCR regions with spatial metadata.
            fields: Optional list of field names (not used directly by LLM engine).
            kwargs: May include 'template' (dict) for the detected document type.

        Returns:
            Dict containing extracted data plus '_llm_stats' with performance metrics.
        """
        if not regions:
            return {}

        if not self._is_loaded:
            logger.warning("LLM model is not loaded. Initialization might have failed.")
            return {}

        # 1. Prepare raw text — sort by Y then X for natural reading order
        if not regions[0].get("_center_y"):
            self.augment_spatial_metadata(regions)

        sorted_regions = sorted(regions, key=lambda r: (r.get("_center_y", 0), r.get("_center_x", 0)))

        # Group OCR regions by line (similar Y-axis) then join words with space.
        raw_text_lines = self._group_regions_by_line(sorted_regions)

        # 2. Retrieve template (passed from OCRService after classification)
        template: Dict[str, Any] = kwargs.get("template") or {}
        doc_type: str = template.get("doc_type", "document")

        # 3. Pre-filter noise labels from OCR text BEFORE sending to LLM
        #    This is more reliable than asking the model to ignore them.
        noise_labels: List[str] = template.get("llm_noise_labels", [])
        raw_text = self._filter_noise(raw_text_lines, noise_labels)

        logger.info(f"OCR text after noise filtering ({len(raw_text)} chars):\n{raw_text}")

        # 4. Build template-driven prompt
        prompt = self._build_prompt(raw_text, template)
        logger.info(f"Sending prompt to LLM ({len(prompt)} chars)...")

        # 5. Inference with timing
        output_text = ""
        t_start = time.perf_counter()

        try:
            response = self._llm(
                prompt,
                max_tokens=450,
                stop=["<|im_end|>"],
                temperature=0.05,
                top_p=0.9,
                echo=False,
            )

            t_end = time.perf_counter()
            elapsed = t_end - t_start

            output_text = response["choices"][0]["text"].strip()

            # Extract token usage for tokens/second
            usage = response.get("usage", {})
            completion_tokens = usage.get("completion_tokens", 0)
            prompt_tokens = usage.get("prompt_tokens", 0)
            total_tokens = usage.get("total_tokens", completion_tokens + prompt_tokens)
            tokens_per_second = round(completion_tokens / elapsed, 2) if elapsed > 0 and completion_tokens > 0 else None

            logger.info(
                f"LLM done in {elapsed:.2f}s — "
                f"prompt={prompt_tokens}t, completion={completion_tokens}t, "
                f"speed={tokens_per_second} tok/s"
            )

            # Clean potential markdown formatting
            output_text = re.sub(r"```json", "", output_text, flags=re.IGNORECASE)
            output_text = re.sub(r"```", "", output_text)
            output_text = output_text.strip()

            # Build stats payload (reused across parse attempts)
            llm_stats = {
                "provider": "local",
                "elapsed_seconds": round(elapsed, 3),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "tokens_per_second": tokens_per_second,
            }

            # Attempt 1: normal parse
            try:
                extracted_data = json.loads(output_text)
                extracted_data["_llm_stats"] = llm_stats
                return extracted_data
            except json.JSONDecodeError:
                pass

            # Attempt 2: repair truncated JSON (add missing closing braces)
            repaired = self._repair_json(output_text)
            if repaired:
                try:
                    extracted_data = json.loads(repaired)
                    logger.warning("LLM output was truncated — repaired and parsed successfully.")
                    extracted_data["_llm_stats"] = llm_stats
                    return extracted_data
                except json.JSONDecodeError:
                    pass

            # Attempt 3: extract just the entities block via regex
            entities = self._extract_entities_fallback(output_text)
            if entities:
                logger.warning("LLM output malformed — extracted entities via regex fallback.")
                result = {"document_type": doc_type, "entities": entities, "_llm_stats": llm_stats}
                return result

            logger.error(f"All JSON parse attempts failed.\nRaw Output: {output_text}")
            return {}

        except Exception as e:
            logger.error(f"LLM inference error: {e}")
            return {}

    # ─────────────────────────────────────────────────────────────────────────
    # Template-driven prompt builder
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_prompt(raw_text: str, template: Dict[str, Any]) -> str:
        """Build the full LLM prompt from template metadata.

        Falls back to generic instructions if template lacks llm_* fields.
        """
        doc_name = template.get("name", "document")
        field_rules: List[str] = template.get("llm_field_rules", _GENERIC_RULES)
        few_shot: Optional[Dict] = template.get("llm_few_shot")
        output_schema: Optional[Dict] = template.get("llm_output_schema")

        # Build system prompt
        rules_text = "\n".join(f"- {rule}" for rule in field_rules)

        schema_hint = ""
        if output_schema:
            schema_hint = (
                "\nCRITICAL: You MUST output a JSON object using EXACTLY these keys. DO NOT invent keys. DO NOT use Indonesian labels as keys. Use these EXACT English keys:\n"
                + json.dumps({"document_type": template.get("doc_type", "document"), "entities": output_schema},
                              ensure_ascii=False)
            )

        few_shot_text = ""
        if few_shot:
            few_shot_output = json.dumps(few_shot["output"], ensure_ascii=False, separators=(",", ":"))
            few_shot_text = (
                f"\nEXAMPLE INPUT:\n{few_shot['input']}\n"
                f"EXAMPLE OUTPUT: {few_shot_output}"
            )

        system_prompt = (
            f"You are an OCR data extractor for Indonesian {doc_name}.\n"
            "Extract fields from raw OCR text and return ONLY a valid JSON object. No explanation.\n\n"
            f"FIELD RULES:\n{rules_text}"
            f"{schema_hint}"
            f"{few_shot_text}"
        )

        user_prompt = (
            f"OCR Text:\n{raw_text}\n\n"
            "Return ONLY the JSON object (no extra text):"
        )

        return f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n"

    # ─────────────────────────────────────────────────────────────────────────
    # Pre-processing: line grouping and noise label filtering
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _group_regions_by_line(regions: List[Dict[str, Any]]) -> List[str]:
        """Group OCR regions that share the same visual line into space-joined strings."""
        if not regions:
            return []

        # Augment metadata if missing
        if not regions[0].get("_center_y"):
            LLMExtractionEngine.augment_spatial_metadata(regions)

        # Calculate average height for tolerance
        heights = [r.get("_height", 0) for r in regions if r.get("_height", 0) > 0]
        avg_height = sum(heights) / len(heights) if heights else 20
        # Increased tolerance to 80% of height to be more forgiving of slight tilts
        y_tolerance = avg_height * 0.8

        # Sort primarily by Y for line identification
        sorted_by_y = sorted(regions, key=lambda r: r.get("_center_y", 0))

        lines_of_regions: List[List[Dict[str, Any]]] = []
        if not sorted_by_y:
            return []
            
        current_line = [sorted_by_y[0]]
        current_y = sorted_by_y[0].get("_center_y", 0)

        for r in sorted_by_y[1:]:
            cy = r.get("_center_y", 0)
            if abs(cy - current_y) <= y_tolerance:
                current_line.append(r)
            else:
                lines_of_regions.append(current_line)
                current_line = [r]
                current_y = cy
        
        if current_line:
            lines_of_regions.append(current_line)

        # Process each line: sort by X and join
        final_lines = []
        for line_regions in lines_of_regions:
            # Sort by X to ensure reading order within the line
            sorted_line = sorted(line_regions, key=lambda r: r.get("_min_x", 0))
            if not sorted_line:
                continue
            
            line_text = ""
            prev_max_x = None
            
            # calculate heuristic character width based on average line height
            max_h = max([r.get("_height", 20) for r in sorted_line if r.get("_height", 0) > 0], default=20)
            avg_char_w = max_h * 0.45
            
            for r in sorted_line:
                text = r.get("text", "").strip()
                if not text:
                    continue
                min_x = r.get("_min_x", 0)
                if prev_max_x is not None:
                    distance = min_x - prev_max_x
                    if distance > avg_char_w * 3.5:
                        line_text += "    "  # 4 spaces for a large column gap
                    elif distance > avg_char_w * 1.5:
                        line_text += "  "    # 2 spaces for a noticeable gap
                    else:
                        line_text += " "     # Standard space, ensures we never accidentally merge separate boxes
                
                line_text += text
                # Try to use actual _max_x if present, otherwise guess based on char count
                # Usually paddleocr or similar provides _max_x or bbox
                bbox = r.get("bbox", [])
                if bbox and len(bbox) == 4:
                    prev_max_x = max(pt[0] for pt in bbox)
                elif "_max_x" in r:
                    prev_max_x = r.get("_max_x")
                else:
                    prev_max_x = min_x + (len(text) * avg_char_w)

            if line_text:
                final_lines.append(line_text.strip())

        return final_lines


    @staticmethod
    def _filter_noise(lines: List[str], noise_labels: List[str]) -> str:
        """Remove OCR label tokens (e.g. 'Gol. Darah', 'NIK :') from text lines.

        This is done BEFORE sending to LLM — more reliable than asking the
        model to ignore them via prompt instructions alone.
        """
        if not noise_labels:
            return "\n".join(lines)

        # Build a regex that matches any noise label (case-insensitive, word-boundary aware)
        pattern = re.compile(
            r"(?<!\w)(" + "|".join(re.escape(lbl) for lbl in noise_labels) + r")(?:\s*[:.]?\s*)?",
            re.IGNORECASE,
        )

        filtered = []
        for line in lines:
            cleaned = pattern.sub("", line).strip()
            if cleaned:  # Drop lines that become empty after stripping
                filtered.append(cleaned)

        return "\n".join(filtered)

    # ─────────────────────────────────────────────────────────────────────────
    # JSON repair helpers
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _repair_json(text: str) -> str:
        """Attempt to repair truncated JSON by closing any unclosed braces/brackets.

        Handles the common case where max_tokens cuts off the output mid-JSON.
        """
        start = text.find("{")
        if start == -1:
            return ""
        text = text[start:]

        # Trim any trailing comma that appeared before truncation
        text = re.sub(r",\s*$", "", text.rstrip())

        # Count and close any unclosed structures
        open_braces = text.count("{") - text.count("}")
        open_brackets = text.count("[") - text.count("]")

        # Check if we're inside an unclosed string
        in_string = False
        escape_next = False
        for ch in text:
            if escape_next:
                escape_next = False
                continue
            if ch == "\\":
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string

        if in_string:
            text += '"'  # Close the dangling string

        text += "]" * max(0, open_brackets)
        text += "}" * max(0, open_braces)

        return text

    @staticmethod
    def _extract_entities_fallback(text: str) -> Optional[Dict[str, Any]]:
        """Last-resort: extract the entities object from malformed JSON output."""
        match = re.search(r'"entities"\s*:\s*(\{[^}]+\})', text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
