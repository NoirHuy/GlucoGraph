"""
Entity-Type-Aware Schema Definition (Phase 2 Extension).

Replaces the plain-text relation-only SchemaDefiner with a combined definer that:
  - Assigns an Entity Type to every unique entity (subject / object) in the triplets.
  - Writes a concise definition for every unique Relation.
  - Returns a unified dict suitable for the extended Schema Canonicalization pipeline.

Output structure
----------------
{
  "entity_types": {
      "type 2 diabetes mellitus": "Disease/Condition",
      "Metformin":                "Treatment/Medication",
      ...
  },
  "relation_definitions": {
      "may be treated by": "The disease ... (subject) ...",
      ...
  }
}
"""

from __future__ import annotations

import json
import logging
import re
from typing import Dict, List, Optional

import edc.utils.llm_utils as llm_utils
from transformers import AutoModelForCausalLM, AutoTokenizer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Allowed entity types — these must match what the target schema uses.
# ---------------------------------------------------------------------------
ALLOWED_ENTITY_TYPES: List[str] = [
    "Disease/Condition",
    "Treatment/Medication",
    "Symptom/Clinical Finding",
    "Clinical Metric/Lab Test",
    "Anatomical Site",
]


# ---------------------------------------------------------------------------
# Parsing helper
# ---------------------------------------------------------------------------

def _parse_sd_entity_response(raw: Optional[str]) -> Dict:
    """
    Parse the LLM response (expected JSON) into the unified schema-definition dict.
    Falls back to empty dicts if parsing fails.
    """
    if not raw:
        return {"entity_types": {}, "relation_definitions": {}}

    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    # Find the outermost { … } block
    start = cleaned.find("{")
    end   = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        logger.warning("[SD-ENTITY] Could not locate JSON block in LLM response.")
        return {"entity_types": {}, "relation_definitions": {}}

    try:
        parsed = json.loads(cleaned[start:end])
        return {
            "entity_types":        parsed.get("entity_types", {}),
            "relation_definitions": parsed.get("relation_definitions", {}),
        }
    except json.JSONDecodeError as exc:
        logger.warning(f"[SD-ENTITY] JSON parse error: {exc}\nRaw response:\n{raw[:400]}")
        return {"entity_types": {}, "relation_definitions": {}}


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class EntityAwareSchemaDefiner:
    """
    Extended Schema Definer that assigns entity types AND defines relations
    in a single LLM call, returning a unified JSON-parsed dict.

    Parameters
    ----------
    openai_model : str, optional
        OpenRouter / OpenAI model ID.  Either this or (model + tokenizer) must be set.
    model : AutoModelForCausalLM, optional
        Local HuggingFace model (mutually exclusive with openai_model).
    tokenizer : AutoTokenizer, optional
        Corresponding tokenizer for the local HF model.
    """

    def __init__(
        self,
        openai_model: Optional[str] = None,
        model: Optional[AutoModelForCausalLM] = None,
        tokenizer: Optional[AutoTokenizer] = None,
    ) -> None:
        assert openai_model is not None or (
            model is not None and tokenizer is not None
        ), "Provide either openai_model or (model, tokenizer)."
        self.openai_model = openai_model
        self.model        = model
        self.tokenizer    = tokenizer

    # ------------------------------------------------------------------
    def define_schema(
        self,
        input_text_str: str,
        extracted_triplets_list: List[List[str]],
        few_shot_examples_str: str,
        prompt_template_str: str,
    ) -> Dict:
        """
        Given a sentence and its extracted triplets, ask the LLM to:
          1. Assign an Entity Type to every unique Subject / Object.
          2. Write a definition for every unique Relation.

        Returns
        -------
        dict with keys "entity_types" and "relation_definitions".
        """
        if not extracted_triplets_list:
            return {"entity_types": {}, "relation_definitions": {}}

        filled_prompt = prompt_template_str.format_map(
            {
                "text":             input_text_str,
                "few_shot_examples": few_shot_examples_str,
                "triples":          extracted_triplets_list,
            }
        )

        messages = [{"role": "user", "content": filled_prompt}]

        if self.openai_model is None:
            raw = llm_utils.generate_completion_transformers(
                messages, self.model, self.tokenizer, answer_prepend="Answer:\n"
            )
        else:
            raw = llm_utils.api_chat_completion(self.openai_model, None, messages)

        result = _parse_sd_entity_response(raw)

        # Sanity-check: warn if any entity or relation is missing
        all_entities = {t[0] for t in extracted_triplets_list} | {t[2] for t in extracted_triplets_list}
        all_relations = {t[1] for t in extracted_triplets_list}

        for ent in all_entities:
            if ent not in result["entity_types"]:
                logger.debug(f"[SD-ENTITY] Entity type missing for: '{ent}'")

        for rel in all_relations:
            if rel not in result["relation_definitions"]:
                logger.debug(f"[SD-ENTITY] Relation definition missing for: '{rel}'")

        return result
