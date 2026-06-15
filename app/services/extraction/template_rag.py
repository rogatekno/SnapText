"""Template RAG Store — retrieve only relevant validation hints from templates.

Instead of dumping ALL field rules into the LLM prompt, we:

1. **Always include** structural rules (how to extract, which arrays to build,
   which fields exist) and the full output schema — these are non-negotiable.
2. **RAG-filter** only the per-field validation hints (e.g. "kode_pos must be
   5-digit", "kewarganegaraan must be WNI, NEVER ISLAM") based on what the
   OCR text actually contains.

This reduces prompt tokens by cutting irrelevant validation hints while keeping
the extraction structure intact — the small local LLM always knows *what* to
extract, and only gets told *how to validate* the fields it actually sees.

Uses the same sentence-transformers model already loaded by LLMExtractionEngine.
No external vector database required — all in-memory numpy.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.core.logging import get_logger

logger = get_logger("template_rag")

# ─────────────────────────────────────────────────────────────────────────────
# Rules that are STRUCTURAL — they define WHAT to extract, not just how to
# validate. These MUST always appear in the prompt regardless of RAG score.
# ─────────────────────────────────────────────────────────────────────────────
_STRUCTURAL_SUBSTRINGS = [
    "extract all",
    "for each family member",
    "for each member",
    "into the ",
    "into the '",
    "array",
    "preserve spaces",
    "null if a field is empty",
    "use null",
]

# Rules that are VALIDATION HINTS — per-field constraints that can be RAG'd.
# A rule is a validation hint if it starts with a field_name: pattern.
_FIELD_HINT_PREFIX = tuple(
    f"{k}:"
    for k in [
        "nomor_kk", "nama_kepala_keluarga", "alamat", "rt_rw",
        "desa_kelurahan", "kecamatan", "kabupaten_kota", "kode_pos",
        "provinsi", "nik", "jenis_kelamin", "tempat_lahir",
        "tanggal_lahir", "agama", "pendidikan", "jenis_pekerjaan",
        "status_perkawinan", "status_hubungan", "kewarganegaraan",
        "nama_ayah", "nama_ibu", "name", "birth_place", "birth_date",
        "gender", "address", "village", "district", "religion",
        "marital_status", "occupation", "citizenship", "valid_until",
        "nomor_peserta", "nomor_kpj", "registration_date",
    ]
)


def _is_structural_rule(text: str) -> bool:
    """Check if a rule is structural (must always include).

    A rule is structural if it contains structural keywords AND is not
    a per-field validation hint. Field hints that happen to contain words
    like "never" should still be RAG-eligible.
    """
    # Per-field hints are never structural, even if they contain keywords
    if _is_field_hint(text):
        return False
    lower = text.lower()
    return any(sub in lower for sub in _STRUCTURAL_SUBSTRINGS)


def _is_field_hint(text: str) -> bool:
    """Check if a rule is a per-field validation hint (can be RAG'd)."""
    return text.strip().lower().startswith(_FIELD_HINT_PREFIX)


class TemplateRAGStore:
    """Chunk a document template and retrieve only relevant validation hints.

    Structural rules and the full output schema are ALWAYS included.
    Only per-field validation hints are filtered by RAG.
    """

    def __init__(self, embed_model):
        """
        Args:
            embed_model: A sentence-transformers model with an ``.encode()`` method.
        """
        self._embed_model = embed_model
        # Cache: doc_type -> (hint_texts, hint_vectors, hint_meta)
        self._index_cache: Dict[str, Tuple[List[str], np.ndarray, List[Dict]]] = {}

    # ─────────────────────────────────────────────────────────────────────
    # Indexing — only index field validation hints, not structural rules
    # ─────────────────────────────────────────────────────────────────────

    def _chunk_hints(self, template: Dict[str, Any]) -> Tuple[List[str], List[Dict]]:
        """Extract per-field validation hints from the template for indexing.

        Structural rules are NOT indexed — they always go into the prompt.
        Only field hints (rules starting with "field_name:") are indexed.
        """
        chunks: List[str] = []
        meta: List[Dict] = []

        doc_type = template.get("doc_type", "document")

        for i, rule in enumerate(template.get("llm_field_rules", [])):
            if _is_field_hint(rule) and not _is_structural_rule(rule):
                chunks.append(rule)
                meta.append({"type": "field_hint", "index": i, "doc_type": doc_type})

        return chunks, meta

    def _ensure_indexed(self, template: Dict[str, Any]) -> Tuple[List[str], np.ndarray, List[Dict]]:
        """Build or retrieve cached vector index for a template's field hints."""
        doc_type = template.get("doc_type", "document")

        if doc_type in self._index_cache:
            return self._index_cache[doc_type]

        hint_texts, hint_meta = self._chunk_hints(template)

        if not hint_texts or self._embed_model is None:
            empty_vecs = np.array([]).reshape(0, 0)
            self._index_cache[doc_type] = (hint_texts, empty_vecs, hint_meta)
            return self._index_cache[doc_type]

        # Encode hint chunks
        vectors = self._embed_model.encode(hint_texts, normalize_embeddings=True)
        if hasattr(vectors, "numpy"):
            vectors = vectors.numpy()
        vectors = np.asarray(vectors, dtype=np.float32)

        self._index_cache[doc_type] = (hint_texts, vectors, hint_meta)
        logger.info(
            f"Template RAG indexed {len(hint_texts)} field hints for '{doc_type}'"
        )
        return self._index_cache[doc_type]

    # ─────────────────────────────────────────────────────────────────────
    # Retrieval
    # ─────────────────────────────────────────────────────────────────────

    def retrieve(
        self,
        template: Dict[str, Any],
        ocr_text: str,
        top_k: int = 10,
    ) -> Dict[str, Any]:
        """Build a mini-template with structural rules + relevant field hints.

        - ALL structural rules are always included.
        - Only field validation hints relevant to the OCR text are included.
        - Full output schema is always included.
        - Few-shot examples are always included (they're too important to drop).

        Args:
            template: The full document template dict.
            ocr_text: The OCR text to match hints against.
            top_k: Max number of field hints to retrieve.

        Returns:
            A template dict with filtered rules but complete schema.
        """
        hint_texts, hint_vectors, hint_meta = self._ensure_indexed(template)

        # ── Always-include: structural rules ────────────────────────────
        all_rules = template.get("llm_field_rules", [])
        structural_rules = [r for r in all_rules if _is_structural_rule(r)]
        # Also include rules that are neither structural nor field hints
        # (e.g. generic formatting instructions)
        other_rules = [
            r for r in all_rules
            if not _is_structural_rule(r) and not _is_field_hint(r)
        ]

        # ── RAG-filter: field validation hints ──────────────────────────
        retrieved_hints: List[str] = []

        if hint_texts and self._embed_model is not None and hint_vectors.size > 0:
            query_vec = self._embed_model.encode([ocr_text], normalize_embeddings=True)
            if hasattr(query_vec, "numpy"):
                query_vec = query_vec.numpy()
            query_vec = np.asarray(query_vec, dtype=np.float32)

            scores = (hint_vectors @ query_vec.T).flatten()
            top_indices = np.argsort(scores)[::-1][:top_k].tolist()

            retrieved_hints = [hint_texts[i] for i in top_indices]

            logger.info(
                f"Template RAG retrieved {len(retrieved_hints)}/{len(hint_texts)} "
                f"field hints (structural: {len(structural_rules)}, other: {len(other_rules)})"
            )
        else:
            # No embedding model — include all hints as fallback
            retrieved_hints = hint_texts
            logger.warning("Template RAG skipped — no embed model, including all field hints")

        # ── Build mini-template ─────────────────────────────────────────
        # Order: structural → field hints → other rules
        # Structural rules first so the LLM sees the extraction structure
        # before the per-field validation constraints.
        combined_rules = structural_rules + retrieved_hints + other_rules

        mini_template: Dict[str, Any] = {
            "name": template.get("name", "document"),
            "doc_type": template.get("doc_type", "document"),
            "llm_field_rules": combined_rules,
            # Schema is ALWAYS complete — never filtered
            "llm_output_schema": template.get("llm_output_schema", {}),
        }

        # Few-shot is always included (too important to RAG-filter)
        if "llm_few_shot" in template:
            mini_template["llm_few_shot"] = template["llm_few_shot"]

        # Noise labels pass through unchanged
        if "llm_noise_labels" in template:
            mini_template["llm_noise_labels"] = template["llm_noise_labels"]

        return mini_template
