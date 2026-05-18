"""
Entity-Type-Aware Schema Canonicalization (Phase 3 Extension).

Mirrors the existing SchemaCanonicalizer but operates on Entity Types instead
of Relations.  The pipeline is identical:

  1. Embed the definition of the extracted entity type (from Phase 2).
  2. Retrieve the Top-K most similar entity types from the target schema via
     cosine similarity (using the configured embedding model).
  3. Ask the LLM (verifier) to pick the best matching canonical type from the
     shortlist, or return None if no match is good enough.

The target entity-type schema is supplied as a simple dict:
  { "Disease/Condition":       "definition ...",
    "Treatment/Medication":    "definition ...",
    ... }

This module is designed to be called from edc_framework.py after the
relation-level SchemaCanonicalizer finishes, operating on the same
canonicalized triplet list but enriching each triple with a typed tuple:
  (subject, relation, object, subject_type, object_type)
"""

from __future__ import annotations

import copy
import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

import edc.utils.llm_utils as llm_utils
from transformers import AutoModelForCausalLM, AutoTokenizer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default target entity-type schema (UMLS-aligned, diabetes domain)
# Extend or replace this dict via the constructor if you have a CSV schema.
# ---------------------------------------------------------------------------
DEFAULT_ENTITY_TYPE_SCHEMA: Dict[str, str] = {
    "Disease/Condition": (
        "A pathological state, disorder, or medical condition that affects the "
        "normal structure or function of a living organism, including chronic "
        "diseases, acute conditions, and comorbidities such as diabetes mellitus, "
        "hypertension, or chronic kidney disease."
    ),
    "Treatment/Medication": (
        "A pharmacological agent, drug class, medical procedure, surgical "
        "intervention, or lifestyle-based intervention intended to manage, cure, "
        "or prevent a disease or condition, including medications such as Metformin "
        "or GLP-1 receptor agonists, and interventions such as lifestyle modification "
        "or bariatric surgery."
    ),
    "Symptom/Clinical Finding": (
        "A subjective complaint or objective clinical observation that indicates the "
        "presence or severity of a disease, including laboratory findings, physical "
        "examination findings, and patient-reported symptoms such as hyperglycemia, "
        "polyuria, or insulin resistance."
    ),
    "Clinical Metric/Lab Test": (
        "A quantitative measurement, laboratory test, or clinical assessment used "
        "to evaluate disease status, treatment response, or risk stratification, "
        "such as HbA1c, eGFR, fasting blood glucose, LDL cholesterol, or blood "
        "pressure readings."
    ),
    "Anatomical Site": (
        "A specific organ, tissue, cell type, or body structure that is the "
        "primary location of a pathological finding or disease manifestation, such "
        "as the pancreas, kidney, retina, peripheral nerve, or beta cells."
    ),
}


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class EntityTypeCanonicalizer:
    """
    Canonicalizes entity types produced by Phase 2 against a target schema
    using embedding-based retrieval + LLM verification.

    Parameters
    ----------
    target_entity_schema : dict
        Mapping of canonical entity type label → definition string.
        Defaults to DEFAULT_ENTITY_TYPE_SCHEMA if None.
    embedder : SentenceTransformer or compatible API-backed embedder
        Used to encode entity-type definitions for similarity search.
    verify_openai_model : str, optional
        OpenRouter / OpenAI model ID for the LLM verifier step.
    verify_model / verify_tokenizer : optional
        Local HF model+tokenizer alternative.
    top_k : int
        Number of candidate types retrieved before LLM verification.
    """

    def __init__(
        self,
        embedder,
        target_entity_schema: Optional[Dict[str, str]] = None,
        verify_openai_model: Optional[str] = None,
        verify_model: Optional[AutoModelForCausalLM] = None,
        verify_tokenizer: Optional[AutoTokenizer] = None,
        top_k: int = 5,
    ) -> None:
        assert verify_openai_model is not None or (
            verify_model is not None and verify_tokenizer is not None
        ), "Provide either verify_openai_model or (verify_model, verify_tokenizer)."

        self.embedder              = embedder
        self.verifier_openai_model = verify_openai_model
        self.verifier_model        = verify_model
        self.verifier_tokenizer    = verify_tokenizer
        self.top_k                 = top_k
        self.schema                = target_entity_schema or DEFAULT_ENTITY_TYPE_SCHEMA

        # Pre-embed all target entity-type definitions
        logger.info("[ET-CANON] Embedding target entity-type schema...")
        self._schema_embeddings: Dict[str, np.ndarray] = {
            label: self.embedder.encode(definition)
            for label, definition in self.schema.items()
        }

    # ------------------------------------------------------------------
    # 1. Embedding-based retrieval
    # ------------------------------------------------------------------
    def _retrieve_candidates(self, query_definition: str) -> Dict[str, str]:
        """Return top_k canonical entity types ranked by cosine similarity."""
        labels     = list(self._schema_embeddings.keys())
        embeddings = np.array(list(self._schema_embeddings.values()))

        if hasattr(self.embedder, "prompts") and "sts_query" in self.embedder.prompts:
            q_vec = self.embedder.encode(query_definition, prompt_name="sts_query")
        else:
            q_vec = self.embedder.encode(query_definition)

        scores  = (np.array([q_vec]) @ embeddings.T)[0]
        indices = np.argsort(-scores)[: self.top_k]

        return {labels[i]: self.schema[labels[i]] for i in indices}

    # ------------------------------------------------------------------
    # 2. LLM verification (multiple-choice)
    # ------------------------------------------------------------------
    def _llm_verify(
        self,
        input_text_str: str,
        query_entity: str,
        query_entity_type: str,
        query_entity_type_definition: str,
        candidate_types: Dict[str, str],
        prompt_template_str: str,
    ) -> Optional[str]:
        """
        Ask the LLM to select the best canonical entity type from candidates.

        Returns the canonical label string, or None if "None of the above".
        """
        labels       = list(candidate_types.keys())
        choice_letters: List[str] = []
        choices_str  = ""

        for idx, label in enumerate(labels):
            letter = chr(ord("A") + idx)
            choice_letters.append(letter)
            choices_str += f"{letter}. '{label}': {candidate_types[label]}\n"

        # Final "None of the above" option
        none_letter = chr(ord("A") + len(labels))
        choices_str += f"{none_letter}. None of the above.\n"

        prompt = prompt_template_str.format_map(
            {
                "input_text":                   input_text_str,
                "query_entity":                 query_entity,
                "query_entity_type":            query_entity_type,
                "query_entity_type_definition": query_entity_type_definition,
                "choices":                      choices_str,
            }
        )

        messages = [{"role": "user", "content": prompt}]

        if self.verifier_openai_model is None:
            raw = llm_utils.generate_completion_transformers(
                messages, self.verifier_model, self.verifier_tokenizer,
                answer_prepend="Answer: ", max_new_token=5,
            )
        else:
            raw = llm_utils.api_chat_completion(
                self.verifier_openai_model, None, messages, max_tokens=5
            )

        if not raw:
            return None

        # Robustly extract the first valid letter
        for char in raw.strip(" `\"'*:-_"):
            if char.upper() in choice_letters:
                return labels[choice_letters.index(char.upper())]

        return None  # "None of the above" or unrecognised response

    # ------------------------------------------------------------------
    # 3. Single-entity canonicalization
    # ------------------------------------------------------------------
    def canonicalize_entity_type(
        self,
        input_text_str: str,
        entity: str,
        open_entity_type: str,
        open_entity_type_definition: str,
        prompt_template_str: str,
    ) -> Optional[str]:
        """
        Canonicalize a single entity's type.

        Returns
        -------
        str  — canonical entity type label from the target schema, or
        None — if no suitable canonical type was found.
        """
        # Fast path: already canonical
        if open_entity_type in self.schema:
            return open_entity_type

        if not open_entity_type_definition:
            logger.debug(f"[ET-CANON] No definition for entity '{entity}', skipping.")
            return None

        candidates = self._retrieve_candidates(open_entity_type_definition)
        canonical  = self._llm_verify(
            input_text_str,
            entity,
            open_entity_type,
            open_entity_type_definition,
            candidates,
            prompt_template_str,
        )

        if canonical is None:
            logger.debug(f"[ET-CANON] No canonical type found for '{entity}' (type: '{open_entity_type}').")

        return canonical

    # ------------------------------------------------------------------
    # 4. Full-list canonicalization (called from edc_framework.py)
    # ------------------------------------------------------------------
    def canonicalize_all(
        self,
        input_text_list: List[str],
        canonicalized_triplets_list: List[List[List[str]]],
        sd_result_list: List[Dict],
        prompt_template_str: str,
    ) -> List[List[Tuple]]:
        """
        Process every sentence and return a typed-triplet list:
            [ [(subj, rel, obj, subj_type, obj_type), ...], [], ... ]

        Parameters
        ----------
        input_text_list         : per-sentence source text
        canonicalized_triplets_list : output of relation-level Phase 3
        sd_result_list          : output of EntityAwareSchemaDefiner.define_schema()
                                  — each element is a dict with keys:
                                    "entity_types", "relation_definitions"
        prompt_template_str     : content of sc_entity_template.txt
        """
        typed_output: List[List[Tuple]] = []

        for idx, (text, triplets, sd_result) in enumerate(
            zip(input_text_list, canonicalized_triplets_list, sd_result_list)
        ):
            open_entity_types: Dict[str, str] = sd_result.get("entity_types", {})
            typed_triplets: List[Tuple] = []

            for triple in triplets:
                if triple is None or len(triple) != 3:
                    continue
                subj, rel, obj = triple

                # ── Subject type ─────────────────────────────────────────
                raw_subj_type = open_entity_types.get(subj, "")
                # Build a pseudo-definition from the type label itself when
                # no richer definition is available.
                subj_def = self.schema.get(raw_subj_type, raw_subj_type)
                canon_subj_type = self.canonicalize_entity_type(
                    text, subj, raw_subj_type, subj_def, prompt_template_str
                )

                # ── Object type ──────────────────────────────────────────
                raw_obj_type = open_entity_types.get(obj, "")
                obj_def      = self.schema.get(raw_obj_type, raw_obj_type)
                canon_obj_type = self.canonicalize_entity_type(
                    text, obj, raw_obj_type, obj_def, prompt_template_str
                )

                typed_triplets.append((subj, rel, obj, canon_subj_type, canon_obj_type))
                logger.debug(
                    f"[ET-CANON] ({subj} [{canon_subj_type}]) "
                    f"--{rel}--> ({obj} [{canon_obj_type}])"
                )

            typed_output.append(typed_triplets)

        return typed_output
