"""
Test suite for Property Packing post-processing module with clinical labeling and ontology mapping.
"""

import sys
import os
import logging

# Ensure the package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

from post_processing.property_packer import (
    extract_clean_value,
    is_value_like,
    pack_properties,
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Value Cleaning & Extraction Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_clean_comparators():
    """Verify that clinical comparators are cleaned correctly."""
    assert extract_clean_value("< 70 mg/dL") == "<70"
    assert extract_clean_value("> 180 mg/dL") == ">180"
    assert extract_clean_value("<= 7.5 %") == "<=7.5"
    assert extract_clean_value(">= 8.0") == ">=8"
    assert extract_clean_value("= 140 mg/dL") == "=140"
    logger.info("✅ test_clean_comparators PASSED")


def test_clean_percentage_adjustments():
    """Verify that percentage dosage adjustments are cleaned correctly."""
    assert extract_clean_value("increase by 20%") == "+20%"
    assert extract_clean_value("reduce dose by 10%") == "-10%"
    assert extract_clean_value("raise dose by 5%") == "+5%"
    assert extract_clean_value("decrease by 15.0%") == "-15%"
    logger.info("✅ test_clean_percentage_adjustments PASSED")


def test_clean_generic_doses():
    """Verify that generic dosages are cleaned and formatted correctly."""
    assert extract_clean_value("10 units") == "10u"
    assert extract_clean_value("5 mg") == "5mg"
    assert extract_clean_value("15.0 ml") == "15ml"
    logger.info("✅ test_clean_generic_doses PASSED")


def test_is_value_like():
    """Verify that value-like triples are correctly identified."""
    assert is_value_like("has clinical threshold", ">180 mg/dL") is True
    assert is_value_like("has dose adjustment", "increase by 20%") is True
    assert is_value_like("treated by", "< 70 mg/dL") is True
    # Concept to concept should be False
    assert is_value_like("treated by", "insulin") is False
    assert is_value_like("is a", "rapid-acting insulin") is False
    logger.info("✅ test_is_value_like PASSED")


# ═══════════════════════════════════════════════════════════════════════════
# 2. Property Packing & Merging Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_pack_titration_merging():
    """Verify that titration rules, thresholds, and adjustments are merged on edges."""
    mock_records = [
        {
            "input_text": "Basal insulin titration rule if glucose >180 mg/dL.",
            "schema_definition": {
                "_entries": [
                    {
                        "subject": "basal insulin",
                        "subject_type": "Drug",
                        "relation": "has titration rule",
                        "object": "fasting blood glucose",
                        "object_type": "Clinical Metric"
                    },
                    {
                        "subject": "type 2 diabetes",
                        "subject_type": "Disease",
                        "relation": "treated by",
                        "object": "basal insulin",
                        "object_type": "Drug"
                    }
                ]
            },
            "schema_canonicalizaiton": [
                ["basal insulin", "has titration rule", "fasting blood glucose"],
                ["fasting blood glucose", "has clinical threshold", ">180 mg/dL"],
                ["basal insulin", "has dose adjustment", "increase by 20%"],
                ["type 2 diabetes", "treated_by", "basal insulin"]
            ]
        }
    ]
    
    packed = pack_properties(mock_records)

    # Build lookup helpers (nodes may be keyed by CUI after Pass 4b)
    nodes_map = {n["id"]: n for n in packed["nodes"]}

    def find_node_by_name(name: str):
        """Find a node whose id or aliases contain the given name (case-insensitive)."""
        name_lower = name.lower()
        for node in packed["nodes"]:
            if node["id"].lower() == name_lower:
                return node
            if any(a.lower() == name_lower for a in node["properties"].get("aliases", [])):
                return node
            if node["properties"].get("umls_canonical", "").lower() == name_lower:
                return node
        return None

    basal_node = find_node_by_name("basal insulin")
    fbg_node = find_node_by_name("fasting blood glucose")
    t2d_node = find_node_by_name("type 2 diabetes")

    assert basal_node is not None, "'basal insulin' node (or its CUI equivalent) should exist"
    assert fbg_node is not None, "'fasting blood glucose' node (or its CUI equivalent) should exist"
    assert t2d_node is not None, "'type 2 diabetes' node (or its CUI equivalent) should exist"

    # Assert value nodes DO NOT exist as standalone concept nodes
    assert ">180 mg/dL" not in nodes_map
    assert "increase by 20%" not in nodes_map

    # Assert relationship has packed properties
    titration_rels = [r for r in packed["relationships"] if r["type"] == "has_titration_rule"]
    assert len(titration_rels) == 1, f"Expected 1 titration rel, got {len(titration_rels)}"
    rel = titration_rels[0]
    assert rel["properties"]["threshold"] == ">180"
    assert rel["properties"]["adjustment"] == "+20%"

    # Check start/end resolve to the right nodes
    assert rel["start"] == basal_node["id"]
    assert rel["end"] == fbg_node["id"]

    # Other relationships should exist without properties
    treated_rels = [r for r in packed["relationships"] if r["type"] == "treated_by"]
    assert len(treated_rels) == 1
    assert treated_rels[0]["start"] == t2d_node["id"]
    assert treated_rels[0]["end"] == basal_node["id"]
    assert treated_rels[0]["properties"] == {}

    logger.info("✅ test_pack_titration_merging PASSED")


def test_pack_standalone_node_properties():
    """Verify that standalone quantitative targets are packed directly onto concept nodes."""
    mock_records = [
        {
            "input_text": "LDL Cholesterol target is <70 mg/dL.",
            "schema_definition": {
                "_entries": [
                    {
                        "subject": "LDL Cholesterol Lipoproteins",
                        "subject_type": "Clinical Metric",
                        "relation": "associated condition of",
                        "object": "type 2 diabetes",
                        "object_type": "Disease"
                    }
                ]
            },
            "schema_canonicalizaiton": [
                ["LDL Cholesterol Lipoproteins", "has titration rule", "< 70 mg/dL"],
                ["LDL Cholesterol Lipoproteins", "associated condition of", "type 2 diabetes"]
            ]
        }
    ]
    
    packed = pack_properties(mock_records)

    def find_node_by_name(name: str):
        name_lower = name.lower()
        for node in packed["nodes"]:
            if node["id"].lower() == name_lower:
                return node
            if any(a.lower() == name_lower for a in node["properties"].get("aliases", [])):
                return node
            if node["properties"].get("umls_canonical", "").lower() == name_lower:
                return node
        return None

    nodes_map = {n["id"]: n for n in packed["nodes"]}
    ldl_node = find_node_by_name("LDL Cholesterol Lipoproteins")
    t2d_node = find_node_by_name("type 2 diabetes")

    assert ldl_node is not None, "'LDL Cholesterol Lipoproteins' node (or CUI equivalent) should exist"
    assert t2d_node is not None, "'type 2 diabetes' node (or CUI equivalent) should exist"
    assert "< 70 mg/dL" not in nodes_map

    # Standalone threshold should be packed onto the LDL node
    assert ldl_node["properties"]["target_threshold"] == "<70", (
        f"Expected target_threshold='<70' on LDL node, got: {ldl_node['properties']}"
    )

    # Standard relationships should exist
    assoc_rels = [r for r in packed["relationships"] if r["type"] == "associated_condition_of"]
    assert len(assoc_rels) == 1
    assert assoc_rels[0]["start"] == ldl_node["id"]
    assert assoc_rels[0]["end"] == t2d_node["id"]
    assert assoc_rels[0]["properties"] == {}

    logger.info("✅ test_pack_standalone_node_properties PASSED")


# ═══════════════════════════════════════════════════════════════════════════
# 3. Specific Clinical Labels and Ontology Enrichment Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_labels_and_ontology_enrichment():
    """Verify schema specific node labels and ontology properties under the Hybrid Approach."""
    mock_records = [
        {
            "input_text": "Insulin is used in patients with type 2 diabetes mellitus.",
            "schema_definition": {
                "_entries": [
                    {
                        "subject": "type 2 diabetes mellitus",
                        "subject_type_canon": "Disease",
                        "relation": "treated_by",
                        "object": "insulin",
                        "object_type_canon": "Drug"
                    },
                    {
                        "subject": "fasting blood glucose",
                        "subject_type": "Clinical Metric",
                        "relation": "treated_by",
                        "object": "insulin",
                        "object_type": "Drug"
                    }
                ]
            },
            "schema_canonicalizaiton": [
                ["type 2 diabetes mellitus", "treated_by", "insulin"],
                ["fasting blood glucose", "treated_by", "insulin"]
            ]
        }
    ]
    
    packed = pack_properties(mock_records)

    def find_node_by_name(name: str):
        name_lower = name.lower()
        for node in packed["nodes"]:
            if node["id"].lower() == name_lower:
                return node
            if any(a.lower() == name_lower for a in node["properties"].get("aliases", [])):
                return node
            if node["properties"].get("umls_canonical", "").lower() == name_lower:
                return node
        return None

    t2dm_node = find_node_by_name("type 2 diabetes mellitus")
    insulin_node = find_node_by_name("insulin")
    fbg_node = find_node_by_name("fasting blood glucose")

    assert t2dm_node is not None, "'type 2 diabetes mellitus' (or CUI equivalent) should exist"
    assert insulin_node is not None, "'insulin' (or CUI equivalent) should exist"
    assert fbg_node is not None, "'fasting blood glucose' (or CUI equivalent) should exist"

    # Labels should include both Concept and specific clinical type
    assert "Disease" in t2dm_node["labels"], f"T2DM node labels: {t2dm_node['labels']}"
    assert "Drug" in insulin_node["labels"], f"insulin node labels: {insulin_node['labels']}"
    assert "Clinical Metric" in fbg_node["labels"], f"FBG node labels: {fbg_node['labels']}"

    # Relationships should exist (one remains 'treated_by', one is corrected to 'decreases')
    treated_rels = [r for r in packed["relationships"] if r["type"] == "treated_by"]
    decreases_rels = [r for r in packed["relationships"] if r["type"] == "decreases"]
    assert len(treated_rels) == 1, f"Expected 1 treated_by rel, got {len(treated_rels)}"
    assert len(decreases_rels) == 1, f"Expected 1 decreases rel, got {len(decreases_rels)}"

    # Check 3: offline/no-key mode — umls_cui can be NONE or a real CUI depending on cache
    # (Just check the property exists)
    assert "umls_cui" in insulin_node["properties"]
    assert "umls_canonical" in insulin_node["properties"]

    logger.info("✅ test_labels_and_ontology_enrichment PASSED")


def test_cui_primary_key_redirection_and_deduplication():
    """Verify that nodes with identical CUIs are merged under the CUI as the primary key ID,
    synonyms are saved to aliases, and relationship endpoints are remapped to the CUI.
    """
    class MockNormalizer:
        def __init__(self):
            self.api_key = "dummy_key"
            
        def query_term(self, term: str, node_labels=None):
            t = term.lower().strip()
            if t in ["metformin", "glucophage"]:
                return {
                    "cui": "C0025598",
                    "canonical": "Metformin",
                    "semantic_type": "Pharmacologic Substance (T121)",
                    "icd10_code": "NONE",
                    "rxnorm_id": "6809",
                    "definition": "A biguanide hypoglycemic agent."
                }
            elif t in ["type 2 diabetes", "t2dm"]:
                return {
                    "cui": "C0011860",
                    "canonical": "Diabetes Mellitus, Non-Insulin-Dependent",
                    "semantic_type": "Disease or Syndrome (T047)",
                    "icd10_code": "E11",
                    "rxnorm_id": "NONE",
                    "definition": "A chronic metabolic disorder."
                }
            return {
                "cui": "NONE",
                "canonical": term,
                "semantic_type": "Unknown",
                "score": 0.0,
                "icd10_code": "NONE",
                "rxnorm_id": "NONE",
                "definition": ""
            }

    # Setup OIE mock records
    mock_records = [
        {
            "schema_definition": {
                "_entries": [
                    {
                        "subject": "Glucophage",
                        "subject_type": "Drug",
                        "relation": "treated_by",
                        "object": "type 2 diabetes",
                        "object_type": "Disease"
                    },
                    {
                        "subject": "metformin",
                        "subject_type": "Drug",
                        "relation": "treated_by",
                        "object": "T2DM",
                        "object_type": "Disease"
                    }
                ]
            },
            "schema_canonicalizaiton": [
                ["Glucophage", "treated_by", "type 2 diabetes"],
                ["metformin", "treated_by", "T2DM"]
            ]
        }
    ]

    normalizer = MockNormalizer()
    packed = pack_properties(mock_records, normalizer=normalizer)
    
    # Assert canonical name redirection
    nodes_map = {n["id"]: n for n in packed["nodes"]}
    
    # There should only be canonical name-based nodes!
    assert "Metformin" in nodes_map
    assert "Diabetes Mellitus, Non-Insulin-Dependent" in nodes_map
    assert "C0025598" not in nodes_map
    assert "C0011860" not in nodes_map
    assert "Glucophage" not in nodes_map
    assert "metformin" not in nodes_map
    assert "type 2 diabetes" not in nodes_map
    assert "T2DM" not in nodes_map

    # Assert aliases & properties merging
    metformin_node = nodes_map["Metformin"]
    assert metformin_node["properties"]["umls_cui"] == "C0025598"
    assert metformin_node["properties"]["umls_canonical"] == "Metformin"
    assert metformin_node["properties"]["rxnorm_id"] == "6809"
    assert metformin_node["properties"]["description"] == "A biguanide hypoglycemic agent."
    
    # Original raw names should be in the aliases list
    aliases = metformin_node["properties"]["aliases"]
    assert "Glucophage" in aliases
    assert "metformin" in aliases
    
    # Assert relationship re-mapping
    rels = packed["relationships"]
    assert len(rels) == 1  # The duplicate was merged!
    rel = rels[0]
    assert rel["start"] == "Metformin"
    assert rel["end"] == "Diabetes Mellitus, Non-Insulin-Dependent"
    assert rel["type"] == "treated_by"
    
    logger.info("✅ test_cui_primary_key_redirection_and_deduplication PASSED")


# ═══════════════════════════════════════════════════════════════════════════
# 4. New Tests — B1 & B2 Regression Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_entity_dedup_without_cui():
    """B2: Verify that entities with no CUI but matching abbreviation/case variants
    are deduplicated into a single node via normalize_entity_for_dedup().
    e.g. 'T2DM' + 'type 2 diabetes mellitus' + 'Type 2 Diabetes Mellitus' → 1 node.
    """
    from post_processing.property_packer import normalize_entity_for_dedup

    # All three should produce identical normalized keys
    key_abbrev = normalize_entity_for_dedup("T2DM")
    key_full_lower = normalize_entity_for_dedup("type 2 diabetes mellitus")
    key_full_title = normalize_entity_for_dedup("Type 2 Diabetes Mellitus")
    assert key_abbrev == key_full_lower, (
        f"T2DM ({key_abbrev!r}) should equal type 2 diabetes mellitus ({key_full_lower!r})"
    )
    assert key_full_lower == key_full_title, (
        f"lowercase ({key_full_lower!r}) should equal title case ({key_full_title!r})"
    )

    # Now verify inside pack_properties that they are merged into 1 node
    mock_records = [
        {
            "schema_definition": {
                "_entries": [
                    {
                        "subject": "T2DM",
                        "subject_type": "Disease",
                        "relation": "treated_by",
                        "object": "metformin",
                        "object_type": "Drug"
                    },
                    {
                        "subject": "Type 2 Diabetes Mellitus",
                        "subject_type": "Disease",
                        "relation": "has_finding",
                        "object": "hyperglycemia",
                        "object_type": "Symptom"
                    }
                ]
            },
            "schema_canonicalizaiton": [
                ["T2DM", "treated_by", "metformin"],
                ["Type 2 Diabetes Mellitus", "has_finding", "hyperglycemia"]
            ]
        }
    ]

    packed = pack_properties(mock_records)
    nodes_map = {n["id"]: n for n in packed["nodes"]}

    # 'T2DM' and 'Type 2 Diabetes Mellitus' should be merged → exactly 1 disease node
    disease_nodes = [
        n for n in packed["nodes"]
        if "Disease" in n.get("labels", [])
    ]
    assert len(disease_nodes) == 1, (
        f"Expected 1 disease node after dedup, got {len(disease_nodes)}: "
        f"{[n['id'] for n in disease_nodes]}"
    )

    # The merged node should have both raw names in its aliases
    disease_node = disease_nodes[0]
    aliases = disease_node["properties"].get("aliases", [])
    raw_ids_in_group = {"T2DM", "Type 2 Diabetes Mellitus"}
    # At least one should be the canonical id, the other in aliases
    all_names = set(aliases) | {disease_node["id"]}
    assert raw_ids_in_group.issubset(all_names), (
        f"Both 'T2DM' and 'Type 2 Diabetes Mellitus' should appear in id+aliases. "
        f"Got: id={disease_node['id']!r}, aliases={aliases}"
    )

    logger.info("✅ test_entity_dedup_without_cui PASSED")


def test_safe_tuis_coverage():
    """B1: Verify that a MockNormalizer returning TUI T116 (Amino Acid, Peptide, or Protein)
    — which is the real UMLS type for insulin — is NOT rejected and results in a CUI
    being assigned to the insulin node.
    """
    class MockNormalizerWithT116:
        """Simulates UMLS returning T116 (insulin's real semantic type)."""
        def __init__(self):
            self.api_key = "dummy_key"

        def query_term(self, term: str, node_labels=None):
            t = term.lower().strip()
            if "insulin" in t:
                return {
                    "cui": "C0021641",
                    "canonical": "Insulin",
                    "semantic_type": "Amino Acid, Peptide, or Protein (T116)",
                    "icd10_code": "NONE",
                    "rxnorm_id": "5856",
                    "definition": "A protein hormone secreted by beta cells of the pancreas."
                }
            return {
                "cui": "NONE",
                "canonical": term,
                "semantic_type": "Unknown",
                "score": 0.0,
                "icd10_code": "NONE",
                "rxnorm_id": "NONE",
                "definition": ""
            }

    mock_records = [
        {
            "schema_definition": {
                "_entries": [
                    {
                        "subject": "type 2 diabetes",
                        "subject_type": "Disease",
                        "relation": "treated_by",
                        "object": "insulin",
                        "object_type": "Drug"
                    }
                ]
            },
            "schema_canonicalizaiton": [
                ["type 2 diabetes", "treated_by", "insulin"]
            ]
        }
    ]

    normalizer = MockNormalizerWithT116()
    packed = pack_properties(mock_records, normalizer=normalizer)
    nodes_map = {n["id"]: n for n in packed["nodes"]}

    # Insulin should be mapped to canonical name "Insulin"
    assert "Insulin" in nodes_map, (
        f"Expected node with id 'Insulin' (insulin canonical name). Got nodes: {list(nodes_map.keys())}"
    )
    insulin_node = nodes_map["Insulin"]
    assert insulin_node["properties"]["umls_cui"] == "C0021641"
    assert insulin_node["properties"]["rxnorm_id"] == "5856"
    assert insulin_node["properties"]["umls_canonical"] == "Insulin"
    assert "insulin" in [a.lower() for a in insulin_node["properties"].get("aliases", [])]

    logger.info("✅ test_safe_tuis_coverage PASSED")


# ═══════════════════════════════════════════════════════════════════════════
# Main Runner
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("  post_processing.PropertyPacker — Unit Test Suite")
    print("=" * 70)
    
    tests = [
        test_clean_comparators,
        test_clean_percentage_adjustments,
        test_clean_generic_doses,
        test_is_value_like,
        test_pack_titration_merging,
        test_pack_standalone_node_properties,
        test_labels_and_ontology_enrichment,
        test_cui_primary_key_redirection_and_deduplication,
        # B2 & B1 regression tests
        test_entity_dedup_without_cui,
        test_safe_tuis_coverage,
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            failed += 1
            errors.append((test_fn.__name__, str(e)))
            logger.error(f"❌ {test_fn.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            
    print("\n" + "=" * 70)
    print(f"  Results: {passed}/{len(tests)} passed, {failed} failed")
    print("=" * 70)
    print("  Tests: 8 original + 2 new regression (B1: safe_tuis, B2: dedup)")
    
    if errors:
        sys.exit(1)
    else:
        print("\nAll property packer tests passed!")
        sys.exit(0)
