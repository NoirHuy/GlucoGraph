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
    
    # Assert nodes
    nodes_map = {n["id"]: n for n in packed["nodes"]}
    assert "basal insulin" in nodes_map
    assert "fasting blood glucose" in nodes_map
    assert "type 2 diabetes" in nodes_map
    
    # Assert value nodes DO NOT exist as standalone concept nodes
    assert ">180 mg/dL" not in nodes_map
    assert "increase by 20%" not in nodes_map
    
    # Assert relationship has packed properties
    titration_rels = [r for r in packed["relationships"] if r["type"] == "has_titration_rule"]
    assert len(titration_rels) == 1
    rel = titration_rels[0]
    assert rel["start"] == "basal insulin"
    assert rel["end"] == "fasting blood glucose"
    assert rel["properties"]["threshold"] == ">180"
    assert rel["properties"]["adjustment"] == "+20%"
    
    # Other relationships should exist without properties
    treated_rels = [r for r in packed["relationships"] if r["type"] == "treated_by"]
    assert len(treated_rels) == 1
    assert treated_rels[0]["start"] == "type 2 diabetes"
    assert treated_rels[0]["end"] == "basal insulin"
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
    
    # Assert nodes
    nodes_map = {n["id"]: n for n in packed["nodes"]}
    assert "LDL Cholesterol Lipoproteins" in nodes_map
    assert "type 2 diabetes" in nodes_map
    assert "< 70 mg/dL" not in nodes_map
    
    # Standalone threshold should be packed onto the LDL Cholesterol Lipoproteins node property
    ldl_node = nodes_map["LDL Cholesterol Lipoproteins"]
    assert ldl_node["properties"]["target_threshold"] == "<70"
    
    # Standard relationships should exist
    assoc_rels = [r for r in packed["relationships"] if r["type"] == "associated_condition_of"]
    assert len(assoc_rels) == 1
    assert assoc_rels[0]["start"] == "LDL Cholesterol Lipoproteins"
    assert assoc_rels[0]["end"] == "type 2 diabetes"
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
    nodes_map = {n["id"]: n for n in packed["nodes"]}
    
    # Check 1: Label Assignment from schema_definition (canon preferred)
    assert "type 2 diabetes mellitus" in nodes_map
    assert "insulin" in nodes_map
    assert "fasting blood glucose" in nodes_map
    
    # Nodes should have both "Concept" and their specific clinical label
    assert set(nodes_map["type 2 diabetes mellitus"]["labels"]) == {"Concept", "Disease"}
    assert set(nodes_map["insulin"]["labels"]) == {"Concept", "Drug"}
    assert set(nodes_map["fasting blood glucose"]["labels"]) == {"Concept", "Clinical Metric"}
    
    # Check 2: Relationships
    treated_rels = [r for r in packed["relationships"] if r["type"] == "treated_by"]
    assert len(treated_rels) == 2
    
    # Check 3: Local Ontology Mapping & Enrichment (Hybrid Approach)
    insulin_node = nodes_map["insulin"]
    assert insulin_node["properties"]["umls_cui"] == "C0021853"
    assert insulin_node["properties"]["umls_canonical"] == "Insulin"
    assert insulin_node["properties"]["rxnorm_id"] == "RXN8609"
    assert "peptide hormone" in insulin_node["properties"]["description"]
    
    diabetes_node = nodes_map["type 2 diabetes mellitus"]
    assert diabetes_node["properties"]["umls_cui"] == "C0011860"
    assert diabetes_node["properties"]["umls_canonical"] == "Type 2 Diabetes Mellitus"
    assert diabetes_node["properties"]["icd10_code"] == "E11"
    assert "chronic high blood sugar" in diabetes_node["properties"]["description"]
    
    logger.info("✅ test_labels_and_ontology_enrichment PASSED")


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
        test_labels_and_ontology_enrichment
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
    
    if errors:
        sys.exit(1)
    else:
        print("\nAll property packer tests passed!")
        sys.exit(0)
