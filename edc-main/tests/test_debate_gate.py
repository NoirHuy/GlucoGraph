"""
Test suite for AgentLLMDebateGate module.

Tests the response parser, verdict scoring, FCS calculation, and veto logic
without making actual API calls (uses mocked LLM responses).
"""

import asyncio
import sys
import os
import logging

# Ensure the edc-main package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# ─── Import module components ───────────────────────────────────────────────
from debate_gate.agent_debate_gate import (
    AgentLLMDebateGate,
    ResponseParser,
    Verdict,
    AgentResponse,
    DebateResult,
    filter_triples_by_debate,
    VALID_RELATIONS,
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. ResponseParser Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_parser_standard_format():
    """Test parsing the standard Vietnamese format output."""
    raw = """This triple is clinically accurate. Insulin is indeed used to treat 
Type 1 Diabetes Mellitus as per ADA guidelines.

Trạng thái: [ĐÚNG] | Độ tin cậy: [ĐỘ_TIN_CẬY: 95]"""
    
    verdict, confidence, reasoning = ResponseParser.parse(raw)
    assert verdict == Verdict.CORRECT, f"Expected ĐÚNG, got {verdict}"
    assert confidence == 95, f"Expected 95, got {confidence}"
    assert "clinically accurate" in reasoning
    logger.info("✅ test_parser_standard_format PASSED")


def test_parser_incorrect_verdict():
    """Test parsing SAI verdict."""
    raw = """This is factually wrong. Regular insulin is not an adverse effect 
of insulin lispro.

Trạng thái: [SAI] | Độ tin cậy: [ĐỘ_TIN_CẬY: 88]"""
    
    verdict, confidence, reasoning = ResponseParser.parse(raw)
    assert verdict == Verdict.INCORRECT, f"Expected SAI, got {verdict}"
    assert confidence == 88
    logger.info("✅ test_parser_incorrect_verdict PASSED")


def test_parser_uncertain_verdict():
    """Test parsing KHÔNG_CHẮC_CHẮN verdict."""
    raw = """I'm not sure about this relationship. More context is needed.

Trạng thái: [KHÔNG_CHẮC_CHẮN] | Độ tin cậy: [ĐỘ_TIN_CẬY: 45]"""
    
    verdict, confidence, reasoning = ResponseParser.parse(raw)
    assert verdict == Verdict.UNCERTAIN, f"Expected KHÔNG_CHẮC_CHẮN, got {verdict}"
    assert confidence == 45
    logger.info("✅ test_parser_uncertain_verdict PASSED")


def test_parser_no_brackets():
    """Test parsing without brackets around verdict."""
    raw = """Analysis complete.

Trạng thái: ĐÚNG | Độ tin cậy: ĐỘ_TIN_CẬY: 90"""
    
    verdict, confidence, reasoning = ResponseParser.parse(raw)
    assert verdict == Verdict.CORRECT
    assert confidence == 90
    logger.info("✅ test_parser_no_brackets PASSED")


def test_parser_english_fallback():
    """Test parsing English verdict labels (fallback)."""
    raw = """This is correct.

Status: [CORRECT] | Confidence: [85]"""
    
    verdict, confidence, reasoning = ResponseParser.parse(raw)
    assert verdict == Verdict.CORRECT
    logger.info("✅ test_parser_english_fallback PASSED")


def test_parser_confidence_clamping():
    """Test that confidence values are clamped to [0, 100]."""
    raw = """Trạng thái: [ĐÚNG] | Độ tin cậy: [ĐỘ_TIN_CẬY: 150]"""
    _, confidence, _ = ResponseParser.parse(raw)
    assert confidence == 100, f"Expected 100 (clamped), got {confidence}"
    logger.info("✅ test_parser_confidence_clamping PASSED")


def test_parser_malformed_response():
    """Test parsing a malformed response defaults to UNCERTAIN."""
    raw = """I don't know what format to use. Here's my analysis.
    The triple seems okay but I'm not sure."""
    
    verdict, confidence, reasoning = ResponseParser.parse(raw)
    assert verdict == Verdict.UNCERTAIN, f"Expected UNCERTAIN fallback, got {verdict}"
    assert confidence == 50, f"Expected default confidence 50, got {confidence}"
    logger.info("✅ test_parser_malformed_response PASSED")


# ═══════════════════════════════════════════════════════════════════════════
# 2. Verdict Enum Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_verdict_from_str():
    """Test Verdict.from_str with various inputs."""
    assert Verdict.from_str("ĐÚNG") == Verdict.CORRECT
    assert Verdict.from_str("SAI") == Verdict.INCORRECT
    assert Verdict.from_str("KHÔNG_CHẮC_CHẮN") == Verdict.UNCERTAIN
    assert Verdict.from_str("KHÔNG CHẮC CHẮN") == Verdict.UNCERTAIN
    assert Verdict.from_str("CORRECT") == Verdict.CORRECT
    assert Verdict.from_str("INCORRECT") == Verdict.INCORRECT
    assert Verdict.from_str("unknown_garbage") == Verdict.UNCERTAIN
    logger.info("✅ test_verdict_from_str PASSED")


# ═══════════════════════════════════════════════════════════════════════════
# 3. FCS Calculation Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_fcs_all_correct():
    """FCS should be high when all agents say CORRECT with high confidence."""
    schema = {"treated_by": "test definition"}
    gate = AgentLLMDebateGate(model_name="test-model", schema=schema)
    
    responses = [
        AgentResponse("Clinical_Specialist", 1, Verdict.CORRECT, 90, "", "", 0.4),
        AgentResponse("Ontology_Inspector", 1, Verdict.CORRECT, 85, "", "", 0.3),
        AgentResponse("Medical_Skeptic", 1, Verdict.CORRECT, 80, "", "", 0.3),
    ]
    
    fcs = gate._calculate_fcs(responses)
    assert fcs > 80, f"Expected FCS > 80 for all-correct, got {fcs:.1f}"
    logger.info(f"✅ test_fcs_all_correct PASSED (FCS={fcs:.1f})")


def test_fcs_all_incorrect():
    """FCS should be low when all agents say INCORRECT."""
    schema = {"treated_by": "test"}
    gate = AgentLLMDebateGate(model_name="test-model", schema=schema)
    
    responses = [
        AgentResponse("Clinical_Specialist", 1, Verdict.INCORRECT, 90, "", "", 0.4),
        AgentResponse("Ontology_Inspector", 1, Verdict.INCORRECT, 85, "", "", 0.3),
        AgentResponse("Medical_Skeptic", 1, Verdict.INCORRECT, 80, "", "", 0.3),
    ]
    
    fcs = gate._calculate_fcs(responses)
    assert fcs < 20, f"Expected FCS < 20 for all-incorrect, got {fcs:.1f}"
    logger.info(f"✅ test_fcs_all_incorrect PASSED (FCS={fcs:.1f})")


def test_fcs_mixed_verdict():
    """FCS should be moderate with mixed verdicts."""
    schema = {"treated_by": "test"}
    gate = AgentLLMDebateGate(model_name="test-model", schema=schema)
    
    responses = [
        AgentResponse("Clinical_Specialist", 1, Verdict.CORRECT, 90, "", "", 0.4),
        AgentResponse("Ontology_Inspector", 1, Verdict.CORRECT, 70, "", "", 0.3),
        AgentResponse("Medical_Skeptic", 1, Verdict.INCORRECT, 60, "", "", 0.3),
    ]
    
    fcs = gate._calculate_fcs(responses)
    # Should be somewhere in the middle but leaning positive due to weighted majority
    assert 40 < fcs < 85, f"Expected moderate FCS, got {fcs:.1f}"
    logger.info(f"✅ test_fcs_mixed_verdict PASSED (FCS={fcs:.1f})")


# ═══════════════════════════════════════════════════════════════════════════
# 4. Veto Logic Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_veto_triggered():
    """Veto should trigger when an agent says SAI with confidence > threshold."""
    schema = {"treated_by": "test"}
    gate = AgentLLMDebateGate(model_name="test-model", schema=schema, veto_confidence_threshold=70)
    
    responses = [
        AgentResponse("Clinical_Specialist", 1, Verdict.CORRECT, 90, "", "", 0.4),
        AgentResponse("Ontology_Inspector", 1, Verdict.CORRECT, 85, "", "", 0.3),
        AgentResponse("Medical_Skeptic", 1, Verdict.INCORRECT, 75, "", "", 0.3),
    ]
    
    veto_agent = gate._check_veto(responses)
    assert veto_agent == "Medical_Skeptic", f"Expected Medical_Skeptic veto, got {veto_agent}"
    logger.info("✅ test_veto_triggered PASSED")


def test_veto_not_triggered():
    """Veto should NOT trigger when SAI confidence is below threshold."""
    schema = {"treated_by": "test"}
    gate = AgentLLMDebateGate(model_name="test-model", schema=schema, veto_confidence_threshold=70)
    
    responses = [
        AgentResponse("Clinical_Specialist", 1, Verdict.CORRECT, 90, "", "", 0.4),
        AgentResponse("Ontology_Inspector", 1, Verdict.CORRECT, 85, "", "", 0.3),
        AgentResponse("Medical_Skeptic", 1, Verdict.INCORRECT, 60, "", "", 0.3),
    ]
    
    veto_agent = gate._check_veto(responses)
    assert veto_agent is None, f"Expected no veto, got {veto_agent}"
    logger.info("✅ test_veto_not_triggered PASSED")


def test_veto_correct_does_not_trigger():
    """A CORRECT verdict should never trigger veto regardless of confidence."""
    schema = {"treated_by": "test"}
    gate = AgentLLMDebateGate(model_name="test-model", schema=schema, veto_confidence_threshold=70)
    
    responses = [
        AgentResponse("Clinical_Specialist", 1, Verdict.CORRECT, 95, "", "", 0.4),
        AgentResponse("Ontology_Inspector", 1, Verdict.CORRECT, 99, "", "", 0.3),
        AgentResponse("Medical_Skeptic", 1, Verdict.CORRECT, 99, "", "", 0.3),
    ]
    
    veto_agent = gate._check_veto(responses)
    assert veto_agent is None
    logger.info("✅ test_veto_correct_does_not_trigger PASSED")


# ═══════════════════════════════════════════════════════════════════════════
# 5. Consensus Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_consensus_all_agree():
    """Consensus = True when all agents have the same verdict."""
    schema = {"treated_by": "test"}
    gate = AgentLLMDebateGate(model_name="test-model", schema=schema)
    
    responses = [
        AgentResponse("A", 1, Verdict.CORRECT, 90, "", "", 0.4),
        AgentResponse("B", 1, Verdict.CORRECT, 85, "", "", 0.3),
        AgentResponse("C", 1, Verdict.CORRECT, 80, "", "", 0.3),
    ]
    
    assert gate._check_consensus(responses) is True
    logger.info("✅ test_consensus_all_agree PASSED")


def test_consensus_disagree():
    """Consensus = False when agents disagree."""
    schema = {"treated_by": "test"}
    gate = AgentLLMDebateGate(model_name="test-model", schema=schema)
    
    responses = [
        AgentResponse("A", 1, Verdict.CORRECT, 90, "", "", 0.4),
        AgentResponse("B", 1, Verdict.INCORRECT, 85, "", "", 0.3),
        AgentResponse("C", 1, Verdict.CORRECT, 80, "", "", 0.3),
    ]
    
    assert gate._check_consensus(responses) is False
    logger.info("✅ test_consensus_disagree PASSED")


# ═══════════════════════════════════════════════════════════════════════════
# 6. Relation Definition Lookup Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_relation_lookup_with_spaces():
    """Schema uses spaces ('has adverse effect'), gate should handle both forms."""
    schema = {
        "has adverse effect": "Indicates negative consequence",
        "treated by": "Managed by therapy",
    }
    gate = AgentLLMDebateGate(model_name="test-model", schema=schema)
    
    # Both forms should work
    assert "negative consequence" in gate._get_relation_definition("has_adverse_effect")
    assert "negative consequence" in gate._get_relation_definition("has adverse effect")
    assert "Managed by" in gate._get_relation_definition("treated_by")
    assert "Managed by" in gate._get_relation_definition("treated by")
    logger.info("✅ test_relation_lookup_with_spaces PASSED")


def test_relation_lookup_missing():
    """Unknown relation should return a fallback message."""
    schema = {"treated_by": "test"}
    gate = AgentLLMDebateGate(model_name="test-model", schema=schema)
    
    result = gate._get_relation_definition("nonexistent_relation")
    assert "No definition found" in result
    logger.info("✅ test_relation_lookup_missing PASSED")


# ═══════════════════════════════════════════════════════════════════════════
# 7. Filter Utility Test
# ═══════════════════════════════════════════════════════════════════════════

def test_filter_triples_by_debate():
    """Test that filter_triples_by_debate correctly removes rejected triples."""
    triples = [
        ["type 1 diabetes", "treated_by", "insulin"],
        ["insulin", "is_a", "30 minutes"],
        ["metformin", "treated_by", "type 2 diabetes"],
    ]
    
    results = [
        DebateResult(
            triple=tuple(triples[0]), accepted=True, fcs_score=92.0,
            vetoed=False, veto_agent=None, rounds_completed=1,
            consensus_reached=True, elapsed_seconds=1.0,
        ),
        DebateResult(
            triple=tuple(triples[1]), accepted=False, fcs_score=15.0,
            vetoed=True, veto_agent="Ontology_Inspector", rounds_completed=1,
            consensus_reached=False, elapsed_seconds=1.0,
        ),
        DebateResult(
            triple=tuple(triples[2]), accepted=False, fcs_score=35.0,
            vetoed=False, veto_agent=None, rounds_completed=3,
            consensus_reached=False, elapsed_seconds=3.0,
        ),
    ]
    
    accepted = filter_triples_by_debate(triples, results)
    assert len(accepted) == 1
    assert accepted[0] == ["type 1 diabetes", "treated_by", "insulin"]
    logger.info("✅ test_filter_triples_by_debate PASSED")


# ═══════════════════════════════════════════════════════════════════════════
# 8. Prompt Construction Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_round1_prompt_contains_triple():
    """Round 1 prompt should contain the subject, relation, and object."""
    schema = {"treated_by": "Managed by therapy"}
    gate = AgentLLMDebateGate(model_name="test-model", schema=schema)
    
    prompt = gate._build_round1_prompt(
        "type 1 diabetes", "treated_by", "insulin",
        "Type 1 diabetes is treated by insulin."
    )
    
    assert "type 1 diabetes" in prompt
    assert "treated_by" in prompt
    assert "insulin" in prompt
    assert "Managed by therapy" in prompt
    logger.info("✅ test_round1_prompt_contains_triple PASSED")


def test_debate_prompt_contains_other_responses():
    """Debate prompt should include other agents' reasoning."""
    schema = {"treated_by": "test"}
    gate = AgentLLMDebateGate(model_name="test-model", schema=schema)
    
    prev_responses = [
        AgentResponse("Clinical_Specialist", 1, Verdict.CORRECT, 90, 
                      "Clinically validated by ADA guidelines.", "", 0.4),
        AgentResponse("Medical_Skeptic", 1, Verdict.INCORRECT, 75,
                      "Direction might be reversed.", "", 0.3),
    ]
    
    prompt = gate._build_debate_prompt(
        "type 1 diabetes", "treated_by", "insulin",
        "Type 1 diabetes is treated by insulin.",
        round_number=2,
        current_agent_name="Ontology_Inspector",
        previous_responses=prev_responses,
    )
    
    # Should contain other agents' responses but NOT Ontology_Inspector's own
    assert "Clinical_Specialist" in prompt
    assert "Medical_Skeptic" in prompt
    assert "ADA guidelines" in prompt
    assert "Direction might be reversed" in prompt
    logger.info("✅ test_debate_prompt_contains_other_responses PASSED")


# ═══════════════════════════════════════════════════════════════════════════
# 9. DebateResult Serialization Test
# ═══════════════════════════════════════════════════════════════════════════

def test_debate_result_to_dict():
    """Test DebateResult.to_dict() produces valid JSON-serializable dict."""
    result = DebateResult(
        triple=("type 1 diabetes", "treated_by", "insulin"),
        accepted=True,
        fcs_score=92.5,
        vetoed=False,
        veto_agent=None,
        rounds_completed=2,
        consensus_reached=True,
        agent_responses=[
            AgentResponse("A", 1, Verdict.CORRECT, 90, "Reasoning text", "raw", 0.4),
        ],
        elapsed_seconds=2.5,
    )
    
    d = result.to_dict()
    assert d["accepted"] is True
    assert d["fcs_score"] == 92.5
    assert d["triple"] == ["type 1 diabetes", "treated_by", "insulin"]
    assert len(d["agent_responses"]) == 1
    
    # Verify JSON serializable
    import json
    json_str = json.dumps(d, ensure_ascii=False)
    assert len(json_str) > 0
    logger.info("✅ test_debate_result_to_dict PASSED")


# ═══════════════════════════════════════════════════════════════════════════
# 10. VALID_RELATIONS constant test
# ═══════════════════════════════════════════════════════════════════════════

def test_valid_relations_count():
    """Verify all 12 valid relations are defined."""
    assert len(VALID_RELATIONS) == 12, f"Expected 12 relations, got {len(VALID_RELATIONS)}"
    expected = {
        "is_a", "has_anatomic_site", "cause_of", "has_finding",
        "has_biomarker", "co_occurs_with", "treated_by", "has_adverse_effect",
        "contraindicated_with", "preferred_over", "has_evaluation", "has_titration_rule",
    }
    assert VALID_RELATIONS == expected
    logger.info("✅ test_valid_relations_count PASSED")


# ═══════════════════════════════════════════════════════════════════════════
# 11. Dedicated Model Configuration Test
# ═══════════════════════════════════════════════════════════════════════════

def test_dedicated_agent_models():
    """Verify that dedicated agent model configurations are correctly assigned."""
    schema = {"treated_by": "test"}
    gate = AgentLLMDebateGate(
        model_name="fallback-model",
        schema=schema,
        clinical_specialist_model="specialist-model",
        ontology_inspector_model="inspector-model",
        medical_skeptic_model="skeptic-model",
    )
    
    # Assert specific model assignments
    agents_map = {a.name: a for a in gate.agents}
    assert agents_map["Clinical_Specialist"].model_name == "specialist-model"
    assert agents_map["Ontology_Inspector"].model_name == "inspector-model"
    assert agents_map["Medical_Skeptic"].model_name == "skeptic-model"
    
    # Verify fallback behavior when not provided
    gate_fallback = AgentLLMDebateGate(
        model_name="fallback-model",
        schema=schema,
    )
    for agent in gate_fallback.agents:
        assert agent.model_name == "fallback-model"
        
    logger.info("✅ test_dedicated_agent_models PASSED")


# ═══════════════════════════════════════════════════════════════════════════
# Main Runner
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("  AgentLLMDebateGate — Unit Test Suite")
    print("=" * 70)
    
    tests = [
        # Parser tests
        test_parser_standard_format,
        test_parser_incorrect_verdict,
        test_parser_uncertain_verdict,
        test_parser_no_brackets,
        test_parser_english_fallback,
        test_parser_confidence_clamping,
        test_parser_malformed_response,
        # Verdict enum
        test_verdict_from_str,
        # FCS calculation
        test_fcs_all_correct,
        test_fcs_all_incorrect,
        test_fcs_mixed_verdict,
        # Veto logic
        test_veto_triggered,
        test_veto_not_triggered,
        test_veto_correct_does_not_trigger,
        # Consensus
        test_consensus_all_agree,
        test_consensus_disagree,
        # Relation lookup
        test_relation_lookup_with_spaces,
        test_relation_lookup_missing,
        # Filter utility
        test_filter_triples_by_debate,
        # Prompt construction
        test_round1_prompt_contains_triple,
        test_debate_prompt_contains_other_responses,
        # Serialization
        test_debate_result_to_dict,
        # Constants
        test_valid_relations_count,
        # Dedicated models configuration
        test_dedicated_agent_models,
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
    
    print("\n" + "=" * 70)
    print(f"  Results: {passed}/{len(tests)} passed, {failed} failed")
    print("=" * 70)
    
    if errors:
        print("\nFailed tests:")
        for name, err in errors:
            print(f"  ❌ {name}: {err}")
        sys.exit(1)
    else:
        print("\nAll tests passed!")
        sys.exit(0)
