"""
Entity Type Canonicalization for EDC Phase 3b.

This module implements the LLM-based Entity Type Canonicalization pipeline
following the EDC paper methodology:
  1. Phase 2 produces open entity types + definitions (via SchemaDefiner)
  2. Phase 3b uses embedding similarity (vector search) to find Top-K candidate
     entity types from the Target Schema, then uses an LLM verifier to select
     the best match (multiple-choice alignment).
"""

from typing import List, Dict, Optional, Tuple
import numpy as np
import copy
import json
import logging
import edc.utils.llm_utils as llm_utils

logger = logging.getLogger(__name__)


class EntityTypeCanonicalizer:
    """
    Canonicalizes open entity types produced by Phase 2 (Schema Definition)
    to standardized entity types in a Target Schema, following the same
    Embed → Retrieve → Verify paradigm as SchemaCanonicalizer (for relations).

    Target Schema format:
        {
            "Disease": "A chronic or acute pathological condition affecting the body.",
            "Drug": "A pharmacological agent used to treat or manage a disease.",
            "Symptom": "A clinical sign or patient-reported feeling caused by a disease.",
            "Clinical Metric": "A quantifiable measurement used to assess disease or treatment.",
            "Anatomical Site": "A specific location in the body associated with a disease finding.",
            "Treatment Procedure": "A non-pharmacological clinical intervention or medical procedure."
        }
    """

    def __init__(
        self,
        target_entity_type_schema: Dict[str, str],
        embedder,
        verify_openai_model: str = None,
        verify_model=None,
        verify_tokenizer=None,
    ):
        assert verify_openai_model is not None or (
            verify_model is not None and verify_tokenizer is not None
        ), "Either verify_openai_model or (verify_model + verify_tokenizer) must be provided."

        self.target_schema = target_entity_type_schema   # {type_name: definition}
        self.embedder = embedder
        self.verify_openai_model = verify_openai_model
        self.verify_model = verify_model
        self.verify_tokenizer = verify_tokenizer

        # Pre-compute embeddings for all target entity types
        self.type_embedding_dict: Dict[str, np.ndarray] = {}
        logger.info("Embedding target entity type schema...")
        for type_name, type_definition in target_entity_type_schema.items():
            self.type_embedding_dict[type_name] = self.embedder.encode(type_definition)

    # ──────────────────────────────────────────────────────────────────────────
    # Step 1: Vector Search — retrieve Top-K similar entity types
    # ──────────────────────────────────────────────────────────────────────────
    def retrieve_similar_entity_types(
        self,
        query_definition: str,
        top_k: int = 5,
    ) -> Tuple[Dict[str, str], List[float]]:
        """
        Encode query_definition and return Top-K candidate entity types from
        the target schema ranked by cosine similarity.

        Returns:
            (candidate_dict, scores)  where candidate_dict = {type_name: definition}
        """
        target_types = list(self.type_embedding_dict.keys())
        target_embeddings = np.array(list(self.type_embedding_dict.values()))

        if hasattr(self.embedder, "prompts") and "sts_query" in self.embedder.prompts:
            query_emb = self.embedder.encode(query_definition, prompt_name="sts_query")
        else:
            query_emb = self.embedder.encode(query_definition)

        # Cosine similarity
        scores = np.array([query_emb]) @ target_embeddings.T
        scores = scores[0]
        ranked_indices = np.argsort(-scores)

        top_k_indices = ranked_indices[:top_k]
        candidate_dict = {
            target_types[i]: self.target_schema[target_types[i]]
            for i in top_k_indices
        }
        candidate_scores = [float(scores[i]) for i in top_k_indices]

        return candidate_dict, candidate_scores

    # ──────────────────────────────────────────────────────────────────────────
    # Step 2: LLM Verify — select best candidate via multiple-choice prompt
    # ──────────────────────────────────────────────────────────────────────────
    def llm_verify_entity_type(
        self,
        input_text: str,
        entity: str,
        predicted_type: str,
        predicted_definition: str,
        candidate_dict: Dict[str, str],
        prompt_template_str: str,
    ) -> Optional[str]:
        """
        Present the Top-K candidates to the LLM as a multiple-choice question.
        Returns the selected canonical entity type name, or None if the LLM
        selects "None of the above".
        """
        choice_letters = []
        choices_str = ""
        candidate_list = list(candidate_dict.keys())

        for idx, type_name in enumerate(candidate_list):
            letter = chr(ord("A") + idx)
            choice_letters.append(letter)
            choices_str += f"{letter}. '{type_name}': {candidate_dict[type_name]}\n"
        # Add "None of the above" as last option
        none_letter = chr(ord("A") + len(candidate_list))
        choices_str += f"{none_letter}. None of the above.\n"

        filled_prompt = prompt_template_str.format_map({
            "input_text":          input_text,
            "entity":              entity,
            "predicted_type":      predicted_type,
            "predicted_definition": predicted_definition,
            "choices":             choices_str,
        })
        messages = [{"role": "user", "content": filled_prompt}]

        if self.verify_openai_model:
            raw_output = llm_utils.api_chat_completion(
                self.verify_openai_model, None, messages, max_tokens=5
            )
        else:
            raw_output = llm_utils.generate_completion_transformers(
                messages, self.verify_model, self.verify_tokenizer,
                answer_prepend="Answer: ", max_new_token=5
            )

        # Robustly extract the selected letter
        selected_letter = None
        if raw_output:
            for char in raw_output.strip(" `\"'*:-_"):
                if char.upper() in choice_letters:
                    selected_letter = char.upper()
                    break

        if selected_letter is None:
            return None   # "None of the above" or unrecognized output

        return candidate_list[choice_letters.index(selected_letter)]

    # ──────────────────────────────────────────────────────────────────────────
    # Main entry: canonicalize one entity
    # ──────────────────────────────────────────────────────────────────────────
    def canonicalize_entity_type(
        self,
        input_text: str,
        entity: str,
        predicted_type: str,
        predicted_definition: str,
        prompt_template_str: str,
        top_k: int = 5,
    ) -> Optional[str]:
        """
        Full pipeline for one entity:
          1. If predicted_type already exists in target schema → return it directly.
          2. Otherwise embed predicted_definition → retrieve Top-K candidates.
          3. LLM verifier picks the best match or returns None.

        Returns canonical entity type string, or None if no match.
        """
        # Fast-path: already canonical
        if predicted_type in self.target_schema:
            return predicted_type

        if not predicted_definition:
            logger.debug(f"[ET-CANON] No definition for '{entity}' ({predicted_type}), skipping.")
            return None

        # Vector search
        candidate_dict, candidate_scores = self.retrieve_similar_entity_types(
            predicted_definition, top_k=top_k
        )
        logger.debug(
            f"[ET-CANON] Top-{top_k} candidates for '{entity}' ({predicted_type}): "
            f"{list(candidate_dict.keys())} scores={[f'{s:.3f}' for s in candidate_scores]}"
        )

        # LLM verification
        canonical_type = self.llm_verify_entity_type(
            input_text, entity, predicted_type, predicted_definition,
            candidate_dict, prompt_template_str
        )

        if canonical_type:
            logger.debug(f"[ET-CANON] '{entity}' → '{canonical_type}'")
        else:
            logger.debug(f"[ET-CANON] '{entity}' could not be aligned to target schema.")

        return canonical_type

    # ──────────────────────────────────────────────────────────────────────────
    # Batch: canonicalize all entity types in a full triplets list
    # ──────────────────────────────────────────────────────────────────────────
    def canonicalize_all(
        self,
        input_text_list: List[str],
        canonicalized_triplets_list: List[List[List[str]]],
        sd_result_list: List[List[dict]],
        prompt_template_str: str,
        top_k: int = 5,
    ) -> Tuple[List[List[List[str]]], List[List[dict]]]:
        """
        Apply entity type canonicalization to every triple across the full dataset.

        Args:
            input_text_list:            Per-sentence source texts.
            canonicalized_triplets_list: Per-sentence relation-canonicalized triples.
            sd_result_list:             Per-sentence Phase 2 output (list of dicts with
                                        subject_type, subject_type_definition, etc.).
            prompt_template_str:        Loaded content of sc_entity_type_template.txt.
            top_k:                      Number of top candidates for embedding search.

        Returns:
            (updated_triplets_list, updated_sd_result_list) — sd results now contain
            'subject_type_canon' and 'object_type_canon' keys.
        """
        total_aligned = 0
        total_failed  = 0

        updated_triplets  = copy.deepcopy(canonicalized_triplets_list)
        updated_sd_result = copy.deepcopy(sd_result_list)

        for sent_idx, (input_text, triplets) in enumerate(
            zip(input_text_list, canonicalized_triplets_list)
        ):
            sd_entries = sd_result_list[sent_idx] if sent_idx < len(sd_result_list) else []

            # Build lookup: entity string → (type, definition)
            entity_info: Dict[str, Tuple[str, str]] = {}
            for entry in sd_entries:
                if isinstance(entry, dict):
                    subj = entry.get("subject", "")
                    obj  = entry.get("object", "")
                    if subj:
                        entity_info[subj] = (
                            entry.get("subject_type", "Unknown"),
                            entry.get("subject_type_definition", ""),
                        )
                    if obj:
                        entity_info[obj] = (
                            entry.get("object_type", "Unknown"),
                            entry.get("object_type_definition", ""),
                        )

            for entry in updated_sd_result[sent_idx] if sent_idx < len(updated_sd_result) else []:
                if not isinstance(entry, dict):
                    continue
                for slot in [("subject", "subject_type", "subject_type_definition", "subject_type_canon"),
                              ("object",  "object_type",  "object_type_definition",  "object_type_canon")]:
                    entity_key, type_key, def_key, canon_key = slot
                    entity    = entry.get(entity_key, "")
                    pred_type = entry.get(type_key, "Unknown")
                    pred_def  = entry.get(def_key, "")

                    canonical = self.canonicalize_entity_type(
                        input_text, entity, pred_type, pred_def,
                        prompt_template_str, top_k=top_k
                    )
                    entry[canon_key] = canonical
                    if canonical:
                        total_aligned += 1
                    else:
                        total_failed += 1

        logger.info(
            f"[ET-CANON] Batch complete: aligned={total_aligned}, failed/None={total_failed}"
        )
        return updated_triplets, updated_sd_result
