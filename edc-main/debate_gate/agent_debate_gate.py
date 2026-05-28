"""
AgentLLMDebateGate — Standalone Multi-Agent Debate Verification for Medical KG Triples
=============================================================================

Based on: "Improving Factuality and Reasoning in Language Models through
           Multiagent Debate" (MIT & Google Brain, 2023).

This module verifies (Subject, Relation, Object) triples through a structured
multi-agent debate before they are loaded into Neo4j.

Architecture:
    - 3 LLM Agents with adaptive weighted personas
    - 2 Phases: Initialization (Round 1) + Extended Debate (Rounds 2-3)
    - Final Consensus Score (FCS) >= 80 threshold
    - Veto power: any agent concluding [SAI] with confidence > 70 triggers rejection

Valid Relations (12):
    is_a, has_anatomic_site, cause_of, has_finding, has_biomarker,
    co_occurs_with, treated_by, has_adverse_effect, contraindicated_with,
    preferred_over, has_evaluation, has_titration_rule
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Constants & Enums
# ─────────────────────────────────────────────────────────────────────────────

VALID_RELATIONS = frozenset([
    "is_a", "has_anatomic_site", "cause_of", "has_finding",
    "has_biomarker", "co_occurs_with", "treated_by", "has_adverse_effect",
    "contraindicated_with", "preferred_over", "has_evaluation", "has_titration_rule",
    "increases_risk_of", "administered_via", "dispenses",
])

# Canonical display map: underscore form → human-friendly
RELATION_DISPLAY = {r: r.replace("_", " ") for r in VALID_RELATIONS}
# Reverse map for normalization
RELATION_NORMALIZE = {}
for _r in VALID_RELATIONS:
    RELATION_NORMALIZE[_r] = _r
    RELATION_NORMALIZE[_r.replace("_", " ")] = _r


class Verdict(str, Enum):
    """Possible verdicts from an agent."""
    CORRECT = "ĐÚNG"
    INCORRECT = "SAI"
    UNCERTAIN = "KHÔNG_CHẮC_CHẮN"

    @classmethod
    def from_str(cls, raw: str) -> "Verdict":
        """Parse verdict from raw string, with fuzzy matching."""
        raw_upper = raw.strip().upper()
        for v in cls:
            # Fuzzy match direct string or with underscores replaced by spaces
            if v.value in raw_upper or v.value.replace("_", " ") in raw_upper:
                return v
        # Fuzzy fallback for English variants — check longer strings first
        # to avoid "CORRECT" matching inside "INCORRECT"
        eng_map_ordered = [
            ("INCORRECT", cls.INCORRECT),
            ("WRONG", cls.INCORRECT),
            ("FALSE", cls.INCORRECT),
            ("UNCERTAIN", cls.UNCERTAIN),
            ("UNSURE", cls.UNCERTAIN),
            ("CORRECT", cls.CORRECT),
            ("TRUE", cls.CORRECT),
        ]
        for key, val in eng_map_ordered:
            if key in raw_upper:
                return val
        return cls.UNCERTAIN


# ─────────────────────────────────────────────────────────────────────────────
# Data Structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AgentResponse:
    """Parsed response from a single agent in a single round."""
    agent_name: str
    round_number: int
    verdict: Verdict
    confidence: int  # 0-100
    reasoning: str
    raw_response: str
    weight: float

    @property
    def weighted_score(self) -> float:
        """Weighted contribution to FCS.
        ĐÚNG → positive, SAI → negative, KHÔNG_CHẮC_CHẮN → half penalty.
        """
        if self.verdict == Verdict.CORRECT:
            return self.weight * self.confidence
        elif self.verdict == Verdict.INCORRECT:
            return -(self.weight * self.confidence)
        else:  # UNCERTAIN
            return self.weight * self.confidence * 0.3  # Minimal positive bias


@dataclass
class DebateResult:
    """Final result for a single triple after multi-agent debate."""
    triple: Tuple[str, str, str]
    accepted: bool
    fcs_score: float
    vetoed: bool
    veto_agent: Optional[str]
    rounds_completed: int
    consensus_reached: bool
    agent_responses: List[AgentResponse] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict:
        d = {
            "triple": list(self.triple),
            "accepted": self.accepted,
            "fcs_score": round(self.fcs_score, 2),
            "vetoed": self.vetoed,
            "veto_agent": self.veto_agent,
            "rounds_completed": self.rounds_completed,
            "consensus_reached": self.consensus_reached,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "agent_responses": [
                {
                    "agent": r.agent_name,
                    "round": r.round_number,
                    "verdict": r.verdict.name,
                    "confidence": r.confidence,
                    "reasoning": r.reasoning[:500],  # Truncate for brevity
                }
                for r in self.agent_responses
            ],
        }
        return d


@dataclass
class AgentPersona:
    """Configuration for a single debate agent."""
    name: str
    weight: float
    system_prompt: str
    temperature: float = 0.3
    model_name: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Prompt Templates
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT_CLINICAL_SPECIALIST = """You are **Clinical_Specialist**, a senior clinical pharmacologist and endocrinologist with 20+ years of experience in diabetes mellitus management.

YOUR EXPERTISE:
- Deep knowledge of insulin therapies (rapid-acting, long-acting, basal-bolus, premixed)
- Pharmacodynamics, pharmacokinetics, adverse effects, and drug interactions
- Clinical guidelines (ADA, EASD, WHO) for diabetes management
- Pathophysiology of Type 1, Type 2, gestational, and secondary diabetes

YOUR ROLE IN THIS DEBATE:
- Evaluate whether a medical Knowledge Graph triple is **clinically accurate** based on established medical evidence
- Focus on: Does this triple represent a real, evidence-based medical relationship?
- Consider standard clinical guidelines, peer-reviewed literature, and pharmacological databases

CONFIDENCE SCORE CALIBRATION (CRITICAL):
You must calibrate your confidence score carefully. Do NOT default to 95-100% unless it is an absolute textbook fact with zero ambiguity.
- **95-100% (Absolute Certainty):** Flawless, standard textbook medical fact directly backed by the source text, with no clinical ambiguity.
- **80-94% (High Certainty):** The relationship is highly accurate and clinically validated, but has minor clinical subtleties, missing non-essential context, or minor wording nuances.
- **60-79% (Moderate Certainty):** The triple is clinically reasonable, but is debatable, lacks clear clinical guidelines, or there are multiple valid viewpoints.
- **40-59% (Uncertain/Debatable):** Clinically speculative, highly contextual, or lacks sufficient supporting medical evidence.
- **Below 40% (Low Certainty):** Highly ambiguous or clinically incorrect.

RESPONSE FORMAT (REQUIRED):
Provide your clinical reasoning, then on the LAST LINE of your response, write EXACTLY:
Status: [CORRECT] or [INCORRECT] or [UNCERTAIN] | Confidence: [CONFIDENCE: <number from 0-100>]"""

_SYSTEM_PROMPT_ONTOLOGY_INSPECTOR = """You are **Ontology_Inspector**, an expert in biomedical ontologies, knowledge representation, and semantic web technologies.

YOUR EXPERTISE:
- UMLS Metathesaurus, SNOMED CT, ICD-10, MeSH, RxNorm, NCI Thesaurus
- OWL/RDF ontology design principles and relationship semantics
- Domain/range constraints for medical predicates
- Entity type classification: Disease, Drug, Symptom, Clinical_Metric, Treatment_Procedure, Biomarker, Anatomic_Site

YOUR ROLE IN THIS DEBATE:
- Evaluate whether the triple uses the **correct ontological relationship** between subject and object
- Verify domain/range type compatibility (e.g., 'treated_by' requires Subject=Disease, Object=Drug/Treatment)
- Check for semantic coherence: is the relationship label appropriate for these two entities?
- Detect misclassifications (e.g., a symptom labeled as a drug, or a temporal value as a disease)

VALID RELATIONS AND THEIR DEFINITIONS (DYNAMICALLY LOADED FROM SCHEMA CSV):
__VALID_RELATIONS_WITH_DEFINITIONS__

Note: Relation labels are case-insensitive and can be written with either spaces or underscores (e.g., 'increases risk of' and 'increases_risk_of' are equivalent). Both formats are ontologically identical and valid.

CONFIDENCE SCORE CALIBRATION (CRITICAL):
You must calibrate your confidence score carefully. Do NOT default to 95-100% unless it is an absolute textbook ontological fact with zero ambiguity.
- **95-100% (Absolute Certainty):** The triple perfectly complies with formal ontology schema, domain/range constraints, and entity classifications with zero ambiguity.
- **80-94% (High Certainty):** The relationship is ontologically correct, but has minor representation details, slightly debatable boundaries, or minor stylistic entity phrasing.
- **60-79% (Moderate Certainty):** The triple is semantically plausible, but lacks clear ontological consensus, has borderline domain/range fit, or has alternative valid schemas.
- **40-59% (Uncertain/Debatable):** Significant ontological ambiguity, borderline entity types, or doubtful relation alignment.
- **Below 40% (Low Certainty):** Clear ontology schema violation or misclassified entity.

RESPONSE FORMAT (REQUIRED):
Provide your ontological analysis, then on the LAST LINE of your response, write EXACTLY:
Status: [CORRECT] or [INCORRECT] or [UNCERTAIN] | Confidence: [CONFIDENCE: <number from 0-100>]"""

_SYSTEM_PROMPT_MEDICAL_SKEPTIC = """You are **Medical_Skeptic**, a critical analyst specialized in detecting extraction errors, hallucinations, and logical fallacies in biomedical NLP outputs.

YOUR EXPERTISE:
- Identifying common NLP extraction errors: reversed subject/object, incorrect relation assignment
- Detecting over-generalization and under-specification in medical statements
- Recognizing when extracted triples conflate correlation with causation
- Spotting entity boundary errors (e.g., partial entities, concatenated terms)
- Flagging temporal/numerical values incorrectly extracted as medical entities

YOUR ROLE IN THIS DEBATE:
- Act as a **critical yet objective medical auditor** — carefully examine whether the triple is faithful to the source text and medically plausible.
- Reject a triple (INCORRECT) only if it contains clear extraction errors (e.g., reversed direction, wrong relation type, polluted entities) or represents an inaccurate/misleading medical statement.
- Do not reject triples over minor stylistic, grammatical, or ontological representation details if the core medical fact is accurate, clinically useful, and supported by the source text.
- Challenge assumptions made by other agents only when they lead to factual inaccuracies.

CONFIDENCE SCORE CALIBRATION (CRITICAL):
You must calibrate your confidence score carefully. Do NOT default to 95-100% unless there is an absolute factuality/extraction error or absolute factuality/extraction correctness.
- **95-100% (Absolute Certainty):** Clear, unambiguous factuality/extraction correctness (if CORRECT) or clear, indisputable extraction/clinical error (if INCORRECT).
- **80-94% (High Certainty):** Highly likely correct/incorrect, but with minor text interpretation subtleties or minor boundary issues.
- **60-79% (Moderate Certainty):** Reasonable argument either way, moderate ambiguity in text support, or debatable clinical logic.
- **40-59% (Uncertain/Debatable):** Highly ambiguous source text support, weak extraction rationale, or borderline clinical validity.
- **Below 40% (Low Certainty):** Purely speculative or completely lacks support from the source text.

RESPONSE FORMAT (REQUIRED):
Provide your critical analysis, then on the LAST LINE of your response, write EXACTLY:
Status: [CORRECT] or [INCORRECT] or [UNCERTAIN] | Confidence: [CONFIDENCE: <number from 0-100>]"""


_ROUND1_USER_TEMPLATE = """## Triple Verification Task

You are evaluating a Knowledge Graph triple extracted from a medical text about diabetes mellitus.

**Triple to verify:**
- Subject: `{subject}`
- Relation: `{relation}` ({relation_definition})
- Object: `{object}`

**Source text (context):**
> {source_text}

**Instructions:**
1. Analyze whether this triple is clinically/ontologically accurate
2. Consider the source text context — does the triple faithfully represent the information?
3. Check if the relation type is appropriate for the subject-object pair
4. Assess entity validity — are both subject and object legitimate medical concepts?

Provide your analysis, then conclude with the required format on the LAST LINE."""


_DEBATE_USER_TEMPLATE = """## Debate Round {round_number} — Triple Re-evaluation

You are continuing the debate about the following Knowledge Graph triple:

**Triple:**
- Subject: `{subject}`
- Relation: `{relation}` ({relation_definition})
- Object: `{object}`

**Source text:**
> {source_text}

---

### Other Agents' Assessments from Previous Round:

{other_agents_responses}

---

**Instructions:**
1. Consider the other agents' reasoning carefully
2. If they raise valid points you missed, update your assessment
3. If you disagree with their reasoning, explain WHY with specific evidence
4. You may change your verdict if convinced by superior arguments
5. Maintain intellectual honesty — do NOT simply agree to reach consensus

Provide your updated analysis, then conclude with the required format on the LAST LINE."""


# ─────────────────────────────────────────────────────────────────────────────
# Regex Parsing Engine
# ─────────────────────────────────────────────────────────────────────────────

class ResponseParser:
    """Robust regex-based parser for agent verdict extraction.
    
    Designed to handle multiple output formats and edge cases from LLM responses.
    Searches from the LAST LINE upward to find the verdict/confidence pattern.
    """

    # Primary patterns (English / Vietnamese format)
    _PAT_VERDICT = re.compile(
        r"\[?\s*(ĐÚNG|SAI|KHÔNG[_\s]?CHẮC[_\s]?CHẮN|CORRECT|INCORRECT|UNCERTAIN)\s*\]?",
        re.IGNORECASE,
    )
    _PAT_CONFIDENCE = re.compile(
        r"(?:ĐỘ[_\s]?TIN[_\s]?CẬY|CONFIDENCE|TIN\s*CẬY)\s*[:=]?\s*\[?\s*(?:ĐỘ[_\s]?TIN[_\s]?CẬY\s*[:=]?\s*)?(\d{1,3})\s*\]?",
        re.IGNORECASE,
    )
    # Fallback: any [NUMBER] pattern at the end
    _PAT_CONFIDENCE_FALLBACK = re.compile(r"\[\s*(\d{1,3})\s*\]")
    # Status line pattern: catches "Status: [X]" or "Trạng thái: [X]"
    _PAT_STATUS_LINE = re.compile(
        r"(?:Trạng\s*thái|Status)\s*:\s*\[?\s*(ĐÚNG|SAI|KHÔNG[_\s]?CHẮC[_\s]?CHẮN|CORRECT|INCORRECT|UNCERTAIN)\s*\]?",
        re.IGNORECASE,
    )

    @classmethod
    def parse(cls, raw_response: str) -> Tuple[Verdict, int, str]:
        """Parse verdict and confidence from raw LLM response.
        
        Returns: (verdict, confidence_0_to_100, reasoning_text)
        
        Strategy:
        1. Search from the last line upward for the status pattern
        2. Extract verdict using primary regex
        3. Extract confidence using primary → fallback regex
        4. Everything before the verdict line is treated as reasoning
        """
        lines = raw_response.strip().split("\n")
        
        verdict = Verdict.UNCERTAIN
        confidence = 50  # Default to uncertain midpoint
        verdict_line_idx = len(lines)
        
        # Scan from bottom up to find the verdict line
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if not line:
                continue
                
            # Try the full status line pattern first
            status_match = cls._PAT_STATUS_LINE.search(line)
            if status_match:
                verdict = Verdict.from_str(status_match.group(1))
                verdict_line_idx = i
                
                # Extract confidence from the same line
                conf_match = cls._PAT_CONFIDENCE.search(line)
                if conf_match:
                    confidence = min(100, max(0, int(conf_match.group(1))))
                else:
                    fallback = cls._PAT_CONFIDENCE_FALLBACK.findall(line)
                    if fallback:
                        # Take the last number in brackets
                        confidence = min(100, max(0, int(fallback[-1])))
                break
            
            # Try just the verdict pattern
            verdict_match = cls._PAT_VERDICT.search(line)
            if verdict_match:
                verdict = Verdict.from_str(verdict_match.group(1))
                verdict_line_idx = i
                
                # Look for confidence on this line or adjacent lines
                conf_match = cls._PAT_CONFIDENCE.search(line)
                if conf_match:
                    confidence = min(100, max(0, int(conf_match.group(1))))
                else:
                    # Search nearby lines for confidence
                    for j in range(max(0, i - 2), min(len(lines), i + 3)):
                        conf_match = cls._PAT_CONFIDENCE.search(lines[j])
                        if conf_match:
                            confidence = min(100, max(0, int(conf_match.group(1))))
                            break
                    else:
                        fallback = cls._PAT_CONFIDENCE_FALLBACK.findall(line)
                        if fallback:
                            confidence = min(100, max(0, int(fallback[-1])))
                break
        
        # Extract reasoning as everything before the verdict line
        reasoning = "\n".join(lines[:verdict_line_idx]).strip()
        if not reasoning:
            reasoning = raw_response.strip()
        
        return verdict, confidence, reasoning


# ─────────────────────────────────────────────────────────────────────────────
# Core Module: AgentLLMDebateGate
# ─────────────────────────────────────────────────────────────────────────────

class AgentLLMDebateGate:
    """Multi-Agent Debate Gate for verifying medical KG triples.
    
    Implements the multiagent debate methodology from MIT & Google Brain to
    achieve high-confidence triple verification through structured argumentation
    between specialized LLM agents with adaptive weighted personas.
    
    Configuration:
        - 3 Agents: Clinical_Specialist (0.4), Ontology_Inspector (0.3), Medical_Skeptic (0.3)
        - Max 3 rounds of debate (Round 1: initialization, Rounds 2-3: extended debate)
        - FCS threshold: 80 (configurable)
        - Veto: any agent with [SAI] and confidence > 70 triggers immediate rejection
    """

    def __init__(
        self,
        model_name: str,
        schema: Dict[str, str],
        *,
        fcs_threshold: float = 80.0,
        veto_confidence_threshold: int = 70,
        max_rounds: int = 3,
        consensus_early_stop: bool = True,
        max_concurrent: int = 5,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        retry_attempts: int = 3,
        retry_delay: float = 2.0,
        clinical_specialist_model: Optional[str] = None,
        ontology_inspector_model: Optional[str] = None,
        medical_skeptic_model: Optional[str] = None,
    ):
        """Initialize the Debate Gate.
        
        Args:
            model_name: Fallback LLM model identifier.
            schema: Relation schema dict {relation_name: definition_string}.
            fcs_threshold: Final Consensus Score threshold. >= this → accepted. Default: 80.
            veto_confidence_threshold: If any agent says [SAI] with confidence > this, triple is vetoed. Default: 70.
            max_rounds: Maximum debate rounds. Default: 3.
            consensus_early_stop: Stop early if all agents agree. Default: True.
            max_concurrent: Maximum concurrent triple verifications. Default: 5.
            temperature: LLM sampling temperature. Default: 0.3.
            max_tokens: Max tokens per LLM response. Default: 1024.
            retry_attempts: Number of API retry attempts. Default: 3.
            retry_delay: Base delay between retries in seconds. Default: 2.0.
            clinical_specialist_model: Dedicated model for Clinical_Specialist.
            ontology_inspector_model: Dedicated model for Ontology_Inspector.
            medical_skeptic_model: Dedicated model for Medical_Skeptic.
        """
        self.model_name = model_name
        self.schema = schema
        self.fcs_threshold = fcs_threshold
        self.veto_confidence_threshold = veto_confidence_threshold
        self.max_rounds = max_rounds
        self.consensus_early_stop = consensus_early_stop
        self.max_concurrent = max_concurrent
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        
        # Build relation lookup maps from the provided schema (100% data-driven)
        self._relation_definitions = {}
        for rel_name, rel_def in self.schema.items():
            # Normalize: "has adverse effect" → "has_adverse_effect"
            normalized = rel_name.strip().replace(" ", "_").lower()
            self._relation_definitions[normalized] = rel_def
            # Also keep original form
            self._relation_definitions[rel_name.strip().lower()] = rel_def
        
        # Dynamically build VALID RELATIONS list with definitions from the active schema for the Ontology Inspector
        valid_relations_list = []
        for rel_name, rel_def in self.schema.items():
            normalized = rel_name.strip().replace(" ", "_").lower()
            original = rel_name.strip().lower()
            valid_relations_list.append(f"- {normalized} (or '{original}'): {rel_def}")
        
        valid_relations_str = "\n".join(sorted(valid_relations_list))
        
        # Replace the placeholder in _SYSTEM_PROMPT_ONTOLOGY_INSPECTOR dynamically
        ontology_system_prompt = _SYSTEM_PROMPT_ONTOLOGY_INSPECTOR.replace(
            "__VALID_RELATIONS_WITH_DEFINITIONS__",
            valid_relations_str
        )
        
        # Initialize the 3 weighted agent personas with dedicated or fallback models
        self.agents: List[AgentPersona] = [
            AgentPersona(
                name="Clinical_Specialist",
                weight=0.4,
                system_prompt=_SYSTEM_PROMPT_CLINICAL_SPECIALIST,
                temperature=temperature,
                model_name=clinical_specialist_model or model_name,
            ),
            AgentPersona(
                name="Ontology_Inspector",
                weight=0.3,
                system_prompt=ontology_system_prompt,
                temperature=temperature,
                model_name=ontology_inspector_model or model_name,
            ),
            AgentPersona(
                name="Medical_Skeptic",
                weight=0.3,
                system_prompt=_SYSTEM_PROMPT_MEDICAL_SKEPTIC,
                temperature=temperature + 0.1,  # Slightly higher for creative skepticism
                model_name=medical_skeptic_model or model_name,
            ),
        ]
        
        # Statistics counters
        self._stats = {
            "total_verified": 0,
            "total_accepted": 0,
            "total_rejected": 0,
            "total_vetoed": 0,
            "total_api_calls": 0,
            "total_rounds": 0,
        }
        
        logger.info(
            f"[DebateGate] Initialized with model={model_name}, "
            f"FCS_threshold={fcs_threshold}, veto_threshold={veto_confidence_threshold}, "
            f"max_rounds={max_rounds}, agents={[a.name for a in self.agents]}"
        )

    # ─────────────────────────────────────────────────────────────
    # LLM API Call (uses project's existing llm_utils infrastructure)
    # ─────────────────────────────────────────────────────────────

    async def _query_agent_async(
        self,
        agent: AgentPersona,
        user_message: str,
    ) -> str:
        """Call the LLM API asynchronously for a single agent.
        
        Uses the project's existing llm_utils.api_chat_completion via
        asyncio.to_thread to avoid blocking the event loop.
        """
        import edc.utils.llm_utils as llm_utils
        
        messages = [{"role": "user", "content": user_message}]
        
        # Use agent's specific model if configured, fallback to global model
        model_to_use = agent.model_name or self.model_name
        
        for attempt in range(self.retry_attempts):
            try:
                # Run the synchronous API call in a thread pool
                response = await asyncio.to_thread(
                    llm_utils.api_chat_completion,
                    model_to_use,
                    agent.system_prompt,
                    messages,
                    temperature=agent.temperature,
                    max_tokens=self.max_tokens,
                )
                self._stats["total_api_calls"] += 1
                return response
            except Exception as e:
                delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(
                    f"[DebateGate] API call failed for {agent.name} "
                    f"(attempt {attempt + 1}/{self.retry_attempts}): {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
        
        # All retries exhausted — return a fallback response
        logger.error(f"[DebateGate] All {self.retry_attempts} API attempts failed for {agent.name}")
        return "Status: [UNCERTAIN] | Confidence: [CONFIDENCE: 30]"

    # ─────────────────────────────────────────────────────────────
    # Prompt Construction
    # ─────────────────────────────────────────────────────────────

    def _get_relation_definition(self, relation: str) -> str:
        """Look up relation definition from schema. Fully data-driven."""
        rel_lower = relation.strip().lower()
        rel_normalized = rel_lower.replace(" ", "_")
        
        if rel_normalized in self._relation_definitions:
            return self._relation_definitions[rel_normalized]
        if rel_lower in self._relation_definitions:
            return self._relation_definitions[rel_lower]
        
        # Fuzzy match: try substring
        for key, val in self._relation_definitions.items():
            if key.replace("_", " ") == rel_lower.replace("_", " "):
                return val
        
        return f"(No definition found for relation '{relation}')"

    def _build_round1_prompt(
        self, subject: str, relation: str, obj: str, source_text: str
    ) -> str:
        """Build the Round 1 (Initialization Phase) user prompt."""
        rel_def = self._get_relation_definition(relation)
        return _ROUND1_USER_TEMPLATE.format(
            subject=subject,
            relation=relation,
            relation_definition=rel_def,
            object=obj,
            source_text=source_text,
        )

    def _build_debate_prompt(
        self,
        subject: str,
        relation: str,
        obj: str,
        source_text: str,
        round_number: int,
        current_agent_name: str,
        previous_responses: List[AgentResponse],
    ) -> str:
        """Build the Debate Phase (Round 2+) user prompt with other agents' responses."""
        rel_def = self._get_relation_definition(relation)
        
        # Format other agents' responses
        other_responses_parts = []
        for resp in previous_responses:
            if resp.agent_name == current_agent_name:
                continue
            verdict_emoji = {
                Verdict.CORRECT: "✅",
                Verdict.INCORRECT: "❌",
                Verdict.UNCERTAIN: "❓",
            }.get(resp.verdict, "❓")
            
            other_responses_parts.append(
                f"**{resp.agent_name}** {verdict_emoji} [{resp.verdict.name}] "
                f"(Confidence: {resp.confidence}%)\n"
                f"```\n{resp.reasoning[:800]}\n```"
            )
        
        other_agents_text = "\n\n---\n\n".join(other_responses_parts)
        if not other_agents_text:
            other_agents_text = "(No other agent responses available)"
        
        return _DEBATE_USER_TEMPLATE.format(
            round_number=round_number,
            subject=subject,
            relation=relation,
            relation_definition=rel_def,
            object=obj,
            source_text=source_text,
            other_agents_responses=other_agents_text,
        )

    # ─────────────────────────────────────────────────────────────
    # Debate Orchestration
    # ─────────────────────────────────────────────────────────────

    async def _run_debate_round(
        self,
        round_number: int,
        subject: str,
        relation: str,
        obj: str,
        source_text: str,
        previous_responses: Optional[List[AgentResponse]] = None,
    ) -> List[AgentResponse]:
        """Run a single debate round for all agents concurrently."""
        
        async def _agent_task(agent: AgentPersona) -> AgentResponse:
            if round_number == 1:
                prompt = self._build_round1_prompt(subject, relation, obj, source_text)
            else:
                prompt = self._build_debate_prompt(
                    subject, relation, obj, source_text,
                    round_number, agent.name, previous_responses or []
                )
            
            raw_response = await self._query_agent_async(agent, prompt)
            verdict, confidence, reasoning = ResponseParser.parse(raw_response)
            
            return AgentResponse(
                agent_name=agent.name,
                round_number=round_number,
                verdict=verdict,
                confidence=confidence,
                reasoning=reasoning,
                raw_response=raw_response,
                weight=agent.weight,
            )
        
        # Run all 3 agents concurrently
        tasks = [_agent_task(agent) for agent in self.agents]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        valid_responses = []
        for i, resp in enumerate(responses):
            if isinstance(resp, Exception):
                logger.error(f"[DebateGate] Agent {self.agents[i].name} raised exception: {resp}")
                valid_responses.append(AgentResponse(
                    agent_name=self.agents[i].name,
                    round_number=round_number,
                    verdict=Verdict.UNCERTAIN,
                    confidence=30,
                    reasoning=f"Agent error: {str(resp)}",
                    raw_response="",
                    weight=self.agents[i].weight,
                ))
            else:
                valid_responses.append(resp)
        
        return valid_responses

    def _check_consensus(self, responses: List[AgentResponse]) -> bool:
        """Check if all agents in the latest round agree on the verdict."""
        if not responses:
            return False
        verdicts = {r.verdict for r in responses}
        return len(verdicts) == 1

    def _check_veto(self, responses: List[AgentResponse]) -> Optional[str]:
        """Check if any agent triggers a veto (SAI with confidence > threshold).
        
        Returns the name of the vetoing agent, or None if no veto.
        """
        for resp in responses:
            if (resp.verdict == Verdict.INCORRECT 
                    and resp.confidence > self.veto_confidence_threshold):
                return resp.agent_name
        return None

    def _calculate_fcs(self, all_responses: List[AgentResponse]) -> float:
        """Calculate Final Consensus Score (FCS) from all rounds.
        
        FCS = Σ(weight_i × confidence_i × direction_i) for the LAST round
        
        Where direction_i:
            +1 if ĐÚNG
            -1 if SAI  
             0.3 if KHÔNG_CHẮC_CHẮN
        
        Normalized to 0-100 scale.
        """
        if not all_responses:
            return 0.0
        
        # Use only the latest round's responses for FCS
        max_round = max(r.round_number for r in all_responses)
        latest_responses = [r for r in all_responses if r.round_number == max_round]
        
        # Calculate raw weighted sum
        total_positive = 0.0
        total_weight = sum(r.weight for r in latest_responses)
        
        for resp in latest_responses:
            if resp.verdict == Verdict.CORRECT:
                total_positive += resp.weight * resp.confidence
            elif resp.verdict == Verdict.INCORRECT:
                total_positive -= resp.weight * resp.confidence
            else:  # UNCERTAIN
                total_positive += resp.weight * resp.confidence * 0.3
        
        # Normalize: max possible = 100 * total_weight, min = -100 * total_weight
        # Map from [-100*tw, +100*tw] → [0, 100]
        if total_weight == 0:
            return 50.0
        
        fcs = (total_positive / total_weight + 100) / 2
        return max(0.0, min(100.0, fcs))

    # ─────────────────────────────────────────────────────────────
    # Main Verification Methods
    # ─────────────────────────────────────────────────────────────

    async def verify_triple(
        self,
        triple: Tuple[str, str, str],
        source_text: str = "",
    ) -> DebateResult:
        """Verify a single (Subject, Relation, Object) triple through multi-agent debate.
        
        Args:
            triple: (subject, relation, object) tuple
            source_text: The original text from which the triple was extracted
            
        Returns:
            DebateResult with acceptance decision, FCS score, and full debate log
        """
        start_time = time.time()
        subject, relation, obj = triple
        
        logger.info(f"[DebateGate] ═══ Verifying: ({subject}, {relation}, {obj}) ═══")
        
        all_responses: List[AgentResponse] = []
        vetoed = False
        veto_agent = None
        consensus = False
        rounds_completed = 0
        
        for round_num in range(1, self.max_rounds + 1):
            rounds_completed = round_num
            self._stats["total_rounds"] += 1
            
            logger.info(f"[DebateGate] ── Round {round_num}/{self.max_rounds} ──")
            
            # Get previous round's responses for debate context
            prev_round_responses = [
                r for r in all_responses if r.round_number == round_num - 1
            ] if round_num > 1 else None
            
            round_responses = await self._run_debate_round(
                round_number=round_num,
                subject=subject,
                relation=relation,
                obj=obj,
                source_text=source_text,
                previous_responses=prev_round_responses,
            )
            
            all_responses.extend(round_responses)
            
            # Log round results
            self._log_round(round_num, round_responses)
            
            # ── Check Veto ──
            veto_agent = self._check_veto(round_responses)
            if veto_agent:
                vetoed = True
                logger.warning(
                    f"[DebateGate] ⛔ VETO triggered by {veto_agent} "
                    f"in Round {round_num}! Triple REJECTED."
                )
                break
            
            # ── Check Consensus (Early Stop) ──
            consensus = self._check_consensus(round_responses)
            if consensus and self.consensus_early_stop and round_num < self.max_rounds:
                unanimous_verdict = round_responses[0].verdict
                logger.info(
                    f"[DebateGate] ✓ Consensus reached in Round {round_num}: "
                    f"All agents agree [{unanimous_verdict.name}]. Early stopping."
                )
                break
        
        # ── Calculate FCS ──
        fcs = self._calculate_fcs(all_responses)
        
        # ── Final Decision ──
        if vetoed:
            accepted = False
        else:
            accepted = fcs >= self.fcs_threshold
        
        elapsed = time.time() - start_time
        
        result = DebateResult(
            triple=triple,
            accepted=accepted,
            fcs_score=fcs,
            vetoed=vetoed,
            veto_agent=veto_agent,
            rounds_completed=rounds_completed,
            consensus_reached=consensus,
            agent_responses=all_responses,
            elapsed_seconds=elapsed,
        )
        
        # Update stats
        self._stats["total_verified"] += 1
        if accepted:
            self._stats["total_accepted"] += 1
        else:
            self._stats["total_rejected"] += 1
        if vetoed:
            self._stats["total_vetoed"] += 1
        
        # Log final decision
        status_icon = "✅ ACCEPTED" if accepted else "❌ REJECTED"
        logger.info(
            f"[DebateGate] ═══ {status_icon} ═══ "
            f"FCS={fcs:.1f} (threshold={self.fcs_threshold}) | "
            f"Vetoed={vetoed} | Rounds={rounds_completed} | "
            f"Time={elapsed:.2f}s"
        )
        
        return result

    async def verify_batch(
        self,
        triples: List[Tuple[str, str, str]],
        source_texts: List[str],
        *,
        output_log_path: Optional[str] = None,
    ) -> List[DebateResult]:
        """Verify a batch of triples with concurrency control.
        
        Args:
            triples: List of (subject, relation, object) tuples
            source_texts: List of source texts, one per triple.
                          If shorter than triples, the last text is reused.
            output_log_path: Optional path to write JSON debate log.
            
        Returns:
            List of DebateResult objects
        """
        if not triples:
            return []
        
        # Pad source_texts if needed
        while len(source_texts) < len(triples):
            source_texts.append(source_texts[-1] if source_texts else "")
        
        logger.info(
            f"[DebateGate] ╔══════════════════════════════════════════╗\n"
            f"[DebateGate] ║  Batch Verification: {len(triples)} triples        ║\n"
            f"[DebateGate] ║  Concurrency: {self.max_concurrent}                       ║\n"
            f"[DebateGate] ╚══════════════════════════════════════════╝"
        )
        
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def _sem_verify(triple, text):
            async with semaphore:
                return await self.verify_triple(triple, text)
        
        tasks = [
            _sem_verify(triple, text)
            for triple, text in zip(triples, source_texts)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        final_results = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                logger.error(f"[DebateGate] Triple {triples[i]} verification failed: {res}")
                final_results.append(DebateResult(
                    triple=triples[i],
                    accepted=False,
                    fcs_score=0.0,
                    vetoed=False,
                    veto_agent=None,
                    rounds_completed=0,
                    consensus_reached=False,
                    elapsed_seconds=0.0,
                ))
            else:
                final_results.append(res)
        
        # Log summary
        accepted_count = sum(1 for r in final_results if r.accepted)
        rejected_count = len(final_results) - accepted_count
        vetoed_count = sum(1 for r in final_results if r.vetoed)
        
        logger.info(
            f"\n[DebateGate] ╔══════════════════════════════════════════╗\n"
            f"[DebateGate] ║  BATCH RESULTS SUMMARY                  ║\n"
            f"[DebateGate] ╠══════════════════════════════════════════╣\n"
            f"[DebateGate] ║  Total:    {len(final_results):>4}                          ║\n"
            f"[DebateGate] ║  Accepted: {accepted_count:>4} ✅                         ║\n"
            f"[DebateGate] ║  Rejected: {rejected_count:>4} ❌                         ║\n"
            f"[DebateGate] ║  Vetoed:   {vetoed_count:>4} ⛔                         ║\n"
            f"[DebateGate] ╚══════════════════════════════════════════╝"
        )
        
        # Write debug log if requested
        if output_log_path:
            self._write_log(final_results, output_log_path)
        
        return final_results

    def verify_batch_sync(
        self,
        triples: List[Tuple[str, str, str]],
        source_texts: List[str],
        **kwargs,
    ) -> List[DebateResult]:
        """Synchronous wrapper for verify_batch.
        
        Handles event loop creation/reuse automatically.
        Use this method when calling from synchronous code (e.g., run_debate.py).
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
            # We're already inside an event loop — create a new one in a thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    asyncio.run,
                    self.verify_batch(triples, source_texts, **kwargs)
                )
                return future.result()
        else:
            return asyncio.run(self.verify_batch(triples, source_texts, **kwargs))

    # ─────────────────────────────────────────────────────────────
    # Logging & Visualization
    # ─────────────────────────────────────────────────────────────

    def _log_round(self, round_number: int, responses: List[AgentResponse]) -> None:
        """Pretty-print a single round's results to the logger."""
        verdict_icons = {
            Verdict.CORRECT: "✅",
            Verdict.INCORRECT: "❌",
            Verdict.UNCERTAIN: "❓",
        }
        
        header = f"┌─── Round {round_number} Results ───┐"
        logger.info(f"[DebateGate] {header}")
        
        for resp in responses:
            icon = verdict_icons.get(resp.verdict, "❓")
            bar_len = resp.confidence // 5  # Scale to ~20 chars max
            bar = "█" * bar_len + "░" * (20 - bar_len)
            
            logger.info(
                f"[DebateGate] │ {resp.agent_name:<22} "
                f"{icon} [{resp.verdict.name:<18}] "
                f"Conf: {resp.confidence:>3}% |{bar}| "
                f"(w={resp.weight})"
            )
        
        footer = f"└{'─' * (len(header) - 2)}┘"
        logger.info(f"[DebateGate] {footer}")

    def _write_log(self, results: List[DebateResult], path: str) -> None:
        """Write detailed debate log to a JSON file."""
        log_data = {
            "config": {
                "model": self.model_name,
                "fcs_threshold": self.fcs_threshold,
                "veto_threshold": self.veto_confidence_threshold,
                "max_rounds": self.max_rounds,
                "agents": [{"name": a.name, "weight": a.weight} for a in self.agents],
            },
            "stats": dict(self._stats),
            "results": [r.to_dict() for r in results],
        }
        
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[DebateGate] Debate log written to: {path}")

    def get_stats(self) -> Dict[str, Any]:
        """Return accumulated statistics."""
        return dict(self._stats)

    def reset_stats(self) -> None:
        """Reset all statistics counters."""
        for key in self._stats:
            self._stats[key] = 0


# ─────────────────────────────────────────────────────────────────────────────
# Utility: Filter triples using debate results
# ─────────────────────────────────────────────────────────────────────────────

def filter_triples_by_debate(
    triples: List[List[str]],
    results: List[DebateResult],
) -> List[List[str]]:
    """Filter out rejected triples based on debate results.
    
    Args:
        triples: Original list of [subject, relation, object] triples
        results: Corresponding DebateResult objects
        
    Returns:
        List of accepted triples only
    """
    assert len(triples) == len(results), \
        f"Mismatched lengths: {len(triples)} triples vs {len(results)} results"
    
    accepted = []
    for triple, result in zip(triples, results):
        if result.accepted:
            accepted.append(triple)
        else:
            reason = "vetoed" if result.vetoed else f"FCS={result.fcs_score:.1f}<80"
            logger.info(f"[DebateGate] Filtered out: {triple} ({reason})")
    
    return accepted
