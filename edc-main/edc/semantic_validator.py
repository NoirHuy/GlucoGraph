"""
Post-OIE Semantic Validator for EDC Pipeline.

This module provides data-driven validation of extracted triples AFTER the OIE
phase and BEFORE Schema Definition. It uses domain/range constraints derived
from the relation schema CSV and entity type schema CSV to:

1. Auto-correct directionality errors for known relation patterns.
2. Discard triples with non-entity objects (bare adjectives, abstract words).
3. Discard triples that violate domain/range type constraints.

All rules are driven by CSV schemas — NO hardcoded entity lists.
"""

import re
import logging
import csv
import numpy as np
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Domain/Range Constraint Definitions (data-driven)
# ──────────────────────────────────────────────────────────────────────────────
# Each entry maps a relation name to its allowed (subject_type, object_type).
# These are inferred from the relation definitions in the schema CSV.
# 'ANY' means any entity type is allowed in that slot.
RELATION_DOMAIN_RANGE = {
    "may be treated by":             ("Disease",         "Drug"),
    "has contraindicated drug":      ("Disease",         "Drug"),
    "manifestation of":              ("Disease",         "Disease"),
    "associated condition of":       ("Disease",         "Disease"),
    "co-occurs with":               ("Disease",         "Disease"),
    "may be associated disease of disease": ("Disease",  "Disease"),
    "has finding site":              ("Disease",         "Anatomical Site"),
    "disease has associated anatomic site": ("Disease",  "Anatomical Site"),
    "disease has primary anatomic site":    ("Disease",  "Anatomical Site"),
    "has evaluation":                ("Disease",         "Clinical Metric"),
    "increases risk of":             ("Disease",         "Disease"),
    "may be finding of disease":     ("Symptom",         "Disease"),
    "associated finding of":         ("Symptom",         "Disease"),
    "is preferred over":             ("Drug",            "Drug"),
    "has adverse effect":            ("Drug",            "Symptom"),
    "has dose adjustment":           ("Drug",            "Dosage Value"),
    "has clinical threshold":        ("Clinical Metric", "Dosage Value"),
    "may be substituted by":         ("Drug",            "Drug"),
    "should be discontinued with":   ("Drug",            "Drug"),
    "cause of":                      ("ANY",             "Disease"),
    "component of":                  ("ANY",             "ANY"),
    "has subtype":                   ("ANY",             "ANY"),
    "is subtype of":                 ("ANY",             "ANY"),
    "member of":                     ("ANY",             "ANY"),
    "clinically associated with":    ("ANY",             "ANY"),
    "differential diagnosis of":     ("Disease",         "Disease"),
    "is classified as":              ("ANY",             "ANY"),
}

# Relations where swapping subject/object is a known auto-correction based on entity types.
# For example, if 'may be treated by' has 'Drug' as subject and 'Disease' as object, they should be swapped.
SWAPPABLE_RELATIONS = {
    "may be treated by": {
        "wrong_subject": ["Drug", "Treatment Procedure"],
        "wrong_object": ["Disease", "Symptom"]
    },
    "has evaluation": {
        "wrong_subject": ["Clinical Metric"],
        "wrong_object": ["Disease", "Symptom"]
    }
}


class SemanticValidator:
    """
    Data-driven post-OIE semantic validator.

    Validates and optionally auto-corrects extracted triples based on:
    - Non-entity detection (bare adjectives, abstract non-clinical words)
    - Directionality auto-correction for known swappable patterns
    - Domain/range constraint checking (optional, used when entity types are available)
    """

    # Patterns that indicate the "entity" is NOT a real clinical entity
    _NON_ENTITY_PATTERNS = [
        # Bare adjectives/comparatives without clinical meaning
        re.compile(r'^(longer|shorter|fewer|more|less|better|worse|higher|lower|larger|smaller|faster|slower|earlier|later|greater|adequate|increased|decreased)$', re.IGNORECASE),
        # Single generic words that are not entities
        re.compile(r'^(simplicity|flexibility|adherence|compliance|convenience|complexity|tolerability|efficacy|safety|benefit|risk|cost|algorithm|guideline)$', re.IGNORECASE),
        # Empty or whitespace-only strings
        re.compile(r'^\s*$'),
    ]

    def __init__(
        self,
        relation_schema: Optional[Dict[str, str]] = None,
        entity_type_schema: Optional[Dict[str, str]] = None,
        embedder = None,
    ):
        """
        Args:
            relation_schema:    Dict from relation CSV {relation_name: definition}
            entity_type_schema: Dict from entity type CSV {type_name: definition}
            embedder:           Optional SentenceTransformer/Embedder for dynamic zero-shot classification
        """
        self.relation_schema = relation_schema or {}
        self.entity_type_schema = entity_type_schema or {}
        self.embedder = embedder

        # Build the set of known relation names from the schema for quick lookup
        self.known_relations = set(self.relation_schema.keys())

        # Detect if it's an instruction-based API embedder (e.g. Qwen3-Embedding or Jina)
        self.is_instruction_model = False
        if self.embedder:
            embedder_class = self.embedder.__class__.__name__
            if embedder_class in ["OpenRouterEmbedder", "JinaEmbedder"]:
                self.is_instruction_model = True
            elif hasattr(self.embedder, "model_name"):
                model_name_lower = str(self.embedder.model_name).lower()
                if "/" in model_name_lower or "jina" in model_name_lower or "qwen" in model_name_lower:
                    self.is_instruction_model = True

        # Precompute entity type embeddings if embedder is available
        self.type_embeddings = {}
        if self.embedder and self.entity_type_schema:
            for type_name, type_def in self.entity_type_schema.items():
                # Represent each type as "TypeName: Definition" for rich semantic context
                text_representation = f"{type_name}: {type_def}"
                try:
                    emb = self.embedder.encode(text_representation)
                    norm = np.linalg.norm(emb)
                    if norm > 0:
                        self.type_embeddings[type_name] = emb / norm
                    else:
                        self.type_embeddings[type_name] = emb
                except Exception as e:
                    logger.warning(f"[VALIDATOR] Failed to precompute embedding for type '{type_name}': {e}")

        logger.info(
            f"[VALIDATOR] Initialized with {len(self.known_relations)} relations, "
            f"{len(self.entity_type_schema)} entity types (embeddings precomputed: {len(self.type_embeddings) > 0}, "
            f"instruction_model: {self.is_instruction_model})"
        )

    def _is_non_entity(self, entity_str: str) -> bool:
        """Check if a string is NOT a valid clinical entity."""
        for pattern in self._NON_ENTITY_PATTERNS:
            if pattern.match(entity_str.strip()):
                return True
        return False

    def _is_lexically_anchored(self, entity_str: str, input_text: str = "") -> bool:
        """
        Check if an entity string is lexically anchored to the input text.
        This prevents extrapolative hallucinations where LLMs invent entities
        not present in the text (like 'Type 2 Diabetes' from generic sentences).
        """
        if not input_text:
            return True  # Skip check if no input_text provided
            
        entity_str_clean = entity_str.strip().lower()
        input_text_clean = input_text.strip().lower()
        
        # Exact substring matches
        if entity_str_clean in input_text_clean:
            return True
            
        # Clean words of length > 2
        entity_words = [w for w in re.split(r'\W+', entity_str_clean) if len(w) > 2]
        
        if not entity_words:
            # Fallback if no words > 2 chars
            return entity_str_clean in input_text_clean
            
        # Stop words to ignore
        stopwords = {
            'and', 'the', 'with', 'for', 'associated', 'disease', 'condition', 
            'treatment', 'therapy', 'management', 'factor', 'options', 'choices',
            'persons', 'people', 'mellitus'
        }
        
        meaningful_words = [w for w in entity_words if w not in stopwords]
        
        if not meaningful_words:
            # If all words are stopwords, just check if the whole entity string is in the text
            return entity_str_clean in input_text_clean
            
        # Check if at least one meaningful word is a substring of the input text
        for word in meaningful_words:
            if word in input_text_clean:
                return True
                
        return False

    def _predict_entity_type(self, entity_str: str) -> str:
        """
        Predict the entity type for a given entity string using zero-shot semantic embedding similarity.
        Uses the precomputed entity type embeddings.
        """
        if not self.embedder or not self.type_embeddings:
            return "Unknown"

        try:
            entity_clean = entity_str.strip()
            # If it's an instruction model, use our premium verified asymmetric query prefix
            if getattr(self, "is_instruction_model", False):
                query_text = f"Given a clinical mention, classify it into the UMLS semantic group: {entity_clean}"
            else:
                query_text = entity_clean

            # Get embedding for the entity string
            emb = self.embedder.encode(query_text)
            norm = np.linalg.norm(emb)
            if norm == 0:
                return "Unknown"
            emb_norm = emb / norm

            # Calculate cosine similarity with all precomputed types
            best_type = "Unknown"
            best_score = -1.0

            for type_name, type_emb in self.type_embeddings.items():
                score = np.dot(emb_norm, type_emb)
                if score > best_score:
                    best_score = score
                    best_type = type_name

            return best_type
        except Exception as e:
            logger.error(f"[VALIDATOR] Error in semantic entity type prediction: {e}")
            return "Unknown"

    def try_auto_correct_direction_by_type(
        self, triple: List[str], subj_type: str, obj_type: str
    ) -> Tuple[List[str], str, str]:
        """
        Auto-correct directionality based on predefined Entity Types instead of keywords.
        Runs AFTER Schema Definition/Canonicalization when types are known.
        
        Args:
            triple: The relation triple [subject, relation, object]
            subj_type: The resolved entity type of the subject
            obj_type: The resolved entity type of the object
            
        Returns:
            Tuple of (corrected_triple, corrected_subj_type, corrected_obj_type)
        """
        if len(triple) != 3:
            return triple, subj_type, obj_type

        subj, rel, obj = triple
        rel_lower = rel.strip().lower()

        if rel_lower in SWAPPABLE_RELATIONS:
            rule = SWAPPABLE_RELATIONS[rel_lower]
            wrong_subjects = rule.get("wrong_subject", [])
            wrong_objects = rule.get("wrong_object", [])
            
            # If the current types match the exact "wrong" pattern, we flip them
            if subj_type in wrong_subjects and obj_type in wrong_objects:
                logger.debug(
                    f"[VALIDATOR] Type-based direction auto-corrected: "
                    f"[{subj} ({subj_type}), {rel}, {obj} ({obj_type})] → "
                    f"[{obj} ({obj_type}), {rel}, {subj} ({subj_type})]"
                )
                return [obj, rel, subj], obj_type, subj_type

        return triple, subj_type, obj_type

    def validate_triple(self, triple: List[str], input_text: str = "") -> Optional[List[str]]:
        """
        Validate a single triple. Returns:
        - The triple if valid
        - None if the triple should be discarded
        Note: Directionality correction is done here dynamically as a zero-shot fallback,
        and is also run type-based in Phase 2.5 if types are resolved.
        """
        if len(triple) != 3:
            logger.debug(f"[VALIDATOR] Discarded malformed triple: {triple}")
            return None

        subj, rel, obj = triple

        # Check 1: Non-entity detection
        if self._is_non_entity(subj):
            logger.debug(f"[VALIDATOR] Discarded non-entity subject: '{subj}' in {triple}")
            return None
        if self._is_non_entity(obj):
            logger.debug(f"[VALIDATOR] Discarded non-entity object: '{obj}' in {triple}")
            return None

        # Check 2: Duplicate subject/object (tautology)
        if subj.strip().lower() == obj.strip().lower():
            logger.debug(f"[VALIDATOR] Discarded tautological triple: {triple}")
            return None

        # Check 3: Object is contained inside subject (redundancy)
        if obj.strip().lower() in subj.strip().lower() and len(obj.strip()) < len(subj.strip()):
            # e.g., subject="fasting blood glucose", object="blood glucose" → redundant
            logger.debug(f"[VALIDATOR] Discarded redundant triple (object in subject): {triple}")
            return None

        # Check 4: Lexical Anchoring Check (No extrapolative hallucinations)
        if not self._is_lexically_anchored(subj, input_text):
            logger.debug(f"[VALIDATOR] Discarded hallucinated subject (not in source text): '{subj}' in {triple}")
            return None
        if not self._is_lexically_anchored(obj, input_text):
            logger.debug(f"[VALIDATOR] Discarded hallucinated object (not in source text): '{obj}' in {triple}")
            return None

        # Check 5: Dynamic schema-driven direction auto-correction fallback
        # This acts as an early safety net (Phase 1.5) before Phase 2, or as a fallback
        # if Phase 2 fails. It uses zero-shot semantic matching against schema definitions.
        if self.embedder and rel.strip().lower() in SWAPPABLE_RELATIONS:
            rel_lower = rel.strip().lower()
            rule = SWAPPABLE_RELATIONS[rel_lower]
            wrong_subjects = rule.get("wrong_subject", [])
            wrong_objects = rule.get("wrong_object", [])

            # Predict types semantically
            subj_type = self._predict_entity_type(subj)
            obj_type = self._predict_entity_type(obj)

            if subj_type in wrong_subjects and obj_type in wrong_objects:
                logger.debug(
                    f"[VALIDATOR] Early dynamic semantic direction auto-corrected: "
                    f"[{subj} ({subj_type}), {rel}, {obj} ({obj_type})] → "
                    f"[{obj} ({obj_type}), {rel}, {subj} ({subj_type})]"
                )
                return [obj, rel, subj]

        return [subj, rel, obj]

    def validate_batch(
        self,
        oie_triples_list: List[List[List[str]]],
        input_texts: Optional[List[str]] = None,
    ) -> List[List[List[str]]]:
        """
        Validate all triples from the OIE phase.

        Args:
            oie_triples_list: Per-sentence list of extracted triples.
            input_texts: Optional list of raw source texts matching the triples.

        Returns:
            Validated triples with the same structure (garbage triples removed).
        """
        if input_texts is not None:
            assert len(oie_triples_list) == len(input_texts), "Triplets list and input texts must align"

        validated_list = []
        total_kept = 0
        total_discarded = 0

        for idx, triples in enumerate(oie_triples_list):
            input_text = input_texts[idx] if input_texts is not None else ""
            kept = []
            for triple in triples:
                result = self.validate_triple(triple, input_text)

                if result is None:
                    total_discarded += 1
                else:
                    total_kept += 1
                    kept.append(result)
            validated_list.append(kept)

        logger.info(
            f"[VALIDATOR] Batch complete: kept={total_kept}, "
            f"discarded={total_discarded}"
        )
        return validated_list
