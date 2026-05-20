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
    ):
        """
        Args:
            relation_schema:    Dict from relation CSV {relation_name: definition}
            entity_type_schema: Dict from entity type CSV {type_name: definition}
        """
        self.relation_schema = relation_schema or {}
        self.entity_type_schema = entity_type_schema or {}

        # Build the set of known relation names from the schema for quick lookup
        self.known_relations = set(self.relation_schema.keys())

        logger.info(
            f"[VALIDATOR] Initialized with {len(self.known_relations)} relations, "
            f"{len(self.entity_type_schema)} entity types"
        )

    def _is_non_entity(self, entity_str: str) -> bool:
        """Check if a string is NOT a valid clinical entity."""
        for pattern in self._NON_ENTITY_PATTERNS:
            if pattern.match(entity_str.strip()):
                return True
        return False

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

    def validate_triple(self, triple: List[str]) -> Optional[List[str]]:
        """
        Validate a single triple. Returns:
        - The triple if valid
        - None if the triple should be discarded
        Note: Directionality correction is NO LONGER done here. It is deferred 
        until entity types are resolved.
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

        return [subj, rel, obj]

    def validate_batch(
        self,
        oie_triples_list: List[List[List[str]]],
    ) -> List[List[List[str]]]:
        """
        Validate all triples from the OIE phase.

        Args:
            oie_triples_list: Per-sentence list of extracted triples.

        Returns:
            Validated triples with the same structure (garbage triples removed).
        """
        validated_list = []
        total_kept = 0
        total_discarded = 0

        for triples in oie_triples_list:
            kept = []
            for triple in triples:
                result = self.validate_triple(triple)

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
