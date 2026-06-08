# -*- coding: utf-8 -*-
"""
HaluEval — Schema Validator
============================
Validates each corrupted triple against the BioRED relation schema
and entity-type schema. Implements 4 distinct rejection detectors:

  1. SemanticInversionDetector   — directional plausibility check
  2. OntologyViolationDetector   — domain/range type constraint check
  3. EntityBoundaryDetector      — entity span length & atomicity check
  4. OutOfSchemaDetector         — diabetes keyword + schema membership check
"""

import re
from typing import List, Tuple, Dict, Optional

# ─────────────────────────────────────────────────────────────────────────────
# BioRED canonical schema constants
# ─────────────────────────────────────────────────────────────────────────────

BIORED_RELATIONS = {
    "Association",
    "Positive_Correlation",
    "Negative_Correlation",
    "Bind",
    "Conversion",
    "Cotreatment",
    "Comparison",
    "Drug_Interaction",
}

BIORED_ENTITY_TYPES = {
    "DiseaseOrPhenotypicFeature",
    "ChemicalEntity",
    "SequenceVariant",
    "GeneOrGeneProduct",
    "CellLine",
    "OrganismTaxon",
}

# Valid (subject_type, relation, object_type) triples per BioRED schema
VALID_DOMAIN_RANGE: Dict[str, Dict[str, List[str]]] = {
    "Association":             {"subj": list(BIORED_ENTITY_TYPES), "obj": list(BIORED_ENTITY_TYPES)},
    "Positive_Correlation":    {"subj": list(BIORED_ENTITY_TYPES), "obj": list(BIORED_ENTITY_TYPES)},
    "Negative_Correlation":    {"subj": list(BIORED_ENTITY_TYPES), "obj": list(BIORED_ENTITY_TYPES)},
    "Bind":                    {"subj": ["GeneOrGeneProduct", "ChemicalEntity"], "obj": ["GeneOrGeneProduct", "ChemicalEntity"]},
    "Conversion":              {"subj": ["ChemicalEntity"],                       "obj": ["ChemicalEntity"]},
    "Cotreatment":             {"subj": ["ChemicalEntity"],                       "obj": ["ChemicalEntity"]},
    "Comparison":              {"subj": ["ChemicalEntity"],                       "obj": ["ChemicalEntity"]},
    "Drug_Interaction":        {"subj": ["ChemicalEntity"],                       "obj": ["ChemicalEntity"]},
}

# Out-of-schema relations that should always be rejected
OUT_OF_SCHEMA_RELATIONS = {
    "contraindicated_with",
    "has_side_effect",
    "upregulates",
    "downregulates",
    "causes",
    "destroys",
    "is_stabilized_by",
    "is_observed_at",
    "is_driven_by",
    "is_contraindicated_with",
}

DIABETES_KEYWORDS = {
    "diabetes", "diabetic", "insulin", "glucose", "glycemic", "glycaemic",
    "hba1c", "t2dm", "gdm", "ndi", "hyperglycemia", "hypoglycemia",
    "metformin", "glipizide", "glibenclamide", "glucagon", "beta cell",
    "islets of langerhans", "nephropathy", "neuropathy", "retinopathy",
    "polydipsia", "polyuria", "fasting plasma glucose", "hemoglobin a1c",
}

# Known out-of-domain oncology / irrelevant biomedical entities
OUT_OF_DOMAIN_ENTITIES = {
    "kras", "brca1", "brca2", "tp53", "egfr", "her2", "alk", "ret",
    "braf", "met", "ros1", "kras g12c", "lung carcinoma",
    "pancreatic ductal adenocarcinoma", "colorectal cancer",
    "non-small cell lung", "adenocarcinoma", "melanoma", "leukemia",
    "lymphoma", "myeloma", "glioblastoma", "cd19", "cd20",
    "chimeric antigen receptor", "car-t",
}

# Atomic entity token length threshold (above this = likely boundary flaw)
ENTITY_ATOMICITY_TOKEN_THRESHOLD = 10


# ─────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────────────────────────────────────

def _token_count(text: str) -> int:
    return len(text.strip().split())


def _contains_keyword(text: str, keywords: set) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


def _is_diabetes_related(subj: str, obj: str) -> bool:
    return _contains_keyword(subj, DIABETES_KEYWORDS) or _contains_keyword(obj, DIABETES_KEYWORDS)


# ─────────────────────────────────────────────────────────────────────────────
# Attack Detector 1: Semantic Inversion
# ─────────────────────────────────────────────────────────────────────────────

# (subject_keyword, relation, object_keyword) patterns that are semantically inverted
_INVERTED_PATTERNS = [
    # insulin causes diabetes → always wrong
    ({"insulin"}, {"causes", "induces", "triggers"}, {"diabetes", "t2dm", "t2d"}),
    # diabetes cures itself
    ({"diabetes"}, {"cures", "treats"}, {"diabetes"}),
    # hyperglycemia stabilized by sugar
    ({"hyperglycemia"}, {"is_stabilized_by", "treated_by", "controlled_by"}, {"fructose", "sugar", "glucose", "corn syrup"}),
    # symptom causes drug
    ({"polydipsia", "polyuria", "neuropathy"}, {"causes", "produces", "requires"}, {"metformin", "insulin", "glipizide"}),
]

def detect_semantic_inversion(subj: str, rel: str, obj: str) -> Tuple[bool, str]:
    """Returns (is_inverted, reason)."""
    s_low, r_low, o_low = subj.lower(), rel.lower(), obj.lower()
    for s_kws, r_kws, o_kws in _INVERTED_PATTERNS:
        if (any(k in s_low for k in s_kws) and
                any(k in r_low for k in r_kws) and
                any(k in o_low for k in o_kws)):
            return True, (
                f"Semantic inversion detected: '{subj}' [{rel}] '{obj}' "
                f"violates known clinical causality direction."
            )
    return False, ""


# ─────────────────────────────────────────────────────────────────────────────
# Attack Detector 2: Ontology Violation
# ─────────────────────────────────────────────────────────────────────────────

def detect_ontology_violation(rel: str) -> Tuple[bool, str]:
    """Returns (is_violation, reason)."""
    rel_lower = rel.strip().lower()
    if rel_lower in {r.lower() for r in OUT_OF_SCHEMA_RELATIONS}:
        return True, (
            f"Ontology violation: relation '{rel}' is not part of the BioRED "
            f"schema. Valid relations: {sorted(BIORED_RELATIONS)}"
        )
    if rel not in BIORED_RELATIONS:
        return True, (
            f"Out-of-schema relation '{rel}' — not found in canonical BioRED schema."
        )
    return False, ""


# ─────────────────────────────────────────────────────────────────────────────
# Attack Detector 3: Entity Boundary Flaw
# ─────────────────────────────────────────────────────────────────────────────

def detect_entity_boundary_flaw(subj: str, obj: str) -> Tuple[bool, str]:
    """Returns (is_boundary_flaw, reason)."""
    reasons = []
    for name, span in [("subject", subj), ("object", obj)]:
        count = _token_count(span)
        if count > ENTITY_ATOMICITY_TOKEN_THRESHOLD:
            reasons.append(
                f"Non-atomic {name} entity ({count} tokens): '{span[:80]}...'"
            )
        # Check for conversational filler patterns
        filler_patterns = [
            r"\bcommonly referred to\b", r"\bwidely reported\b",
            r"\bvarious leading\b", r"\bmultiple peer.reviewed\b",
            r"\bstatistically significantly\b", r"\bas confirmed by\b",
            r"\bwhat clinicians\b", r"\boften quite\b",
        ]
        for pattern in filler_patterns:
            if re.search(pattern, span, re.IGNORECASE):
                reasons.append(f"Conversational filler detected in {name}: '{pattern}'")
                break

    if reasons:
        return True, "Entity boundary flaw: " + "; ".join(reasons)
    return False, ""


# ─────────────────────────────────────────────────────────────────────────────
# Attack Detector 4: Out-of-Schema Hallucination
# ─────────────────────────────────────────────────────────────────────────────

def detect_out_of_schema_hallucination(subj: str, rel: str, obj: str) -> Tuple[bool, str]:
    """Returns (is_hallucination, reason)."""
    combined = f"{subj} {rel} {obj}".lower()

    # Check if any out-of-domain entity appears
    for entity in OUT_OF_DOMAIN_ENTITIES:
        if entity in combined:
            return True, (
                f"Out-of-schema hallucination: out-of-domain oncology/unrelated "
                f"entity '{entity}' detected in triple. This entity has no "
                f"established diabetes schema relationship."
            )

    # Additionally check if triple is entirely non-diabetes-related
    if not _is_diabetes_related(subj, obj):
        return True, (
            f"Out-of-schema hallucination: neither subject '{subj}' nor object "
            f"'{obj}' contains diabetes-domain keywords."
        )

    return False, ""


# ─────────────────────────────────────────────────────────────────────────────
# Unified Schema Validator
# ─────────────────────────────────────────────────────────────────────────────

class HaluEvalSchemaValidator:
    """
    Runs all 4 adversarial attack detectors on a given triple
    and returns a structured verdict with detailed reasons.
    """

    def validate_triple(
        self, subj: str, rel: str, obj: str
    ) -> Dict:
        """
        Validate a single (subject, relation, object) triple.

        Returns:
            dict with keys:
                - triple: (subj, rel, obj)
                - verdict: "ACCEPT" | "REJECT"
                - attack_type_detected: str | None
                - reasons: List[str]
        """
        reasons = []
        attack_type = None
        verdict = "ACCEPT"

        # 1. Semantic Inversion
        inverted, reason = detect_semantic_inversion(subj, rel, obj)
        if inverted:
            reasons.append(reason)
            attack_type = "Semantic Inversion"
            verdict = "REJECT"

        # 2. Ontology Violation
        violated, reason = detect_ontology_violation(rel)
        if violated:
            reasons.append(reason)
            if not attack_type:
                attack_type = "Ontology Violation"
            verdict = "REJECT"

        # 3. Entity Boundary Flaw
        boundary_flaw, reason = detect_entity_boundary_flaw(subj, obj)
        if boundary_flaw:
            reasons.append(reason)
            if not attack_type:
                attack_type = "Entity Boundary Flaw"
            verdict = "REJECT"

        # 4. Out-of-Schema Hallucination
        hallucinated, reason = detect_out_of_schema_hallucination(subj, rel, obj)
        if hallucinated:
            reasons.append(reason)
            if not attack_type:
                attack_type = "Out-of-Schema Hallucination"
            verdict = "REJECT"

        return {
            "triple": (subj, rel, obj),
            "verdict": verdict,
            "attack_type_detected": attack_type,
            "reasons": reasons,
        }

    def validate_all(
        self, triples: List[List[str]]
    ) -> List[Dict]:
        """Validate a list of triples."""
        return [self.validate_triple(t[0], t[1], t[2]) for t in triples]
