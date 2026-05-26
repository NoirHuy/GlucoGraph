from typing import List
import os
import json
import re
from pathlib import Path
import edc.utils.llm_utils as llm_utils
from transformers import AutoModelForCausalLM, AutoTokenizer
import logging

logger = logging.getLogger(__name__)


def parse_sd_json_output(raw_output: str) -> List[dict]:
    """
    Parse the JSON array output from the updated Phase 2 SD prompt.
    Returns a list of dicts with keys:
        subject, subject_type, subject_type_definition,
        relation, relation_definition,
        object, object_type, object_type_definition

    Falls back gracefully on malformed output.
    """
    if not raw_output:
        return []

    # Try to find a JSON array in the output (model may add preamble)
    try:
        # Find the first '[' and last ']'
        start = raw_output.index("[")
        end   = raw_output.rindex("]") + 1
        json_str = raw_output[start:end]
        result = json.loads(json_str)
        if isinstance(result, list):
            return result
    except (ValueError, json.JSONDecodeError):
        pass

    logger.debug(f"[SD] Could not parse JSON from output: {raw_output[:200]}")
    return []


def build_relation_definition_dict(sd_entries: List[dict]) -> dict:
    """
    Build the legacy relation_definition_dict from Phase 2 JSON entries.
    This keeps backward compatibility with Phase 3 (SchemaCanonicalizer).
    Returns: { relation_label: definition_string }
    """
    rel_def_dict = {}
    for entry in sd_entries:
        if not isinstance(entry, dict):
            continue
        rel   = (entry.get("relation") or "").strip()
        defn  = (entry.get("relation_definition") or "").strip()
        if rel and defn:
            rel_def_dict[rel] = defn
    return rel_def_dict


class SchemaDefiner:
    """Handles Phase 2: Schema Definition (relation + entity type definitions)."""

    def __init__(
        self,
        model: AutoModelForCausalLM = None,
        tokenizer: AutoTokenizer = None,
        openai_model: str = None,
        use_entity_types: bool = True,
        allowed_entity_types: List[str] = None,
    ) -> None:
        assert openai_model is not None or (model is not None and tokenizer is not None)
        self.model        = model
        self.tokenizer    = tokenizer
        self.openai_model = openai_model
        self.use_entity_types = use_entity_types
        self.allowed_entity_types = allowed_entity_types or [
            "Disease", "Drug", "Symptom", "Clinical Metric", 
            "Anatomical Site", "Treatment Procedure", "Dosage Value", "Unknown"
        ]

    def define_schema(
        self,
        input_text_str: str,
        extracted_triplets_list: List[List[str]],
        few_shot_examples_str: str,
        prompt_template_str: str,
    ) -> dict:
        """
        Given source text and extracted triplets, ask the LLM to:
          - Define each unique relation (backward-compatible output).
          - Assign entity types + definitions for each subject/object
            (new output when use_entity_types=True).

        Returns:
            When use_entity_types=False (legacy mode):
                { relation_label: definition }
            When use_entity_types=True (new mode):
                {
                  "_entries": [ { subject, subject_type, ..., relation, ..., object, ... }, ... ],
                  relation_label: definition,   # kept for SchemaCanonicalizer compatibility
                  ...
                }
        """
        if not extracted_triplets_list:
            if self.use_entity_types:
                return {"_entries": []}
            return {}

        relations_present = set()
        for t in extracted_triplets_list:
            if len(t) >= 2:
                relations_present.add(t[1])

        types_str = ", ".join(self.allowed_entity_types)
        filled_prompt = prompt_template_str.format_map(
            {
                "text":                 input_text_str,
                "few_shot_examples":    few_shot_examples_str,
                "relations":           relations_present,
                "triples":             extracted_triplets_list,
                "allowed_entity_types": types_str,
            }
        )
        messages = [{"role": "user", "content": filled_prompt}]

        if self.openai_model is None:
            completion = llm_utils.generate_completion_transformers(
                messages, self.model, self.tokenizer, answer_prepend="Answer: "
            )
        else:
            completion = llm_utils.api_chat_completion(self.openai_model, None, messages)

        # ── New JSON-based parsing (entity types enabled) ──
        if self.use_entity_types:
            sd_entries = parse_sd_json_output(completion)
            rel_def_dict = build_relation_definition_dict(sd_entries)
            # Store raw entries under special key for Phase 3b
            rel_def_dict["_entries"] = sd_entries

            missing = [r for r in relations_present if r not in rel_def_dict]
            if missing:
                logger.debug(f"[SD] Relations missing from definition: {missing}")
            return rel_def_dict

        # ── Legacy plain-text parsing (backward compat) ──
        relation_definition_dict = llm_utils.parse_relation_definition(completion)
        missing = [r for r in relations_present if r not in relation_definition_dict]
        if missing:
            logger.debug(f"[SD] Relations {missing} are missing from the relation definition!")
        return relation_definition_dict
