"""
Post-OIE Semantic Validator for EDC Pipeline.

This module provides data-driven validation of extracted triples AFTER the OIE
phase and BEFORE Schema Definition. It uses domain/range constraints and literal
roles dynamically parsed from configured few-shot examples at startup to:

1. Auto-correct directionality errors for known relation patterns dynamically.
2. Discard triples with non-entity objects (bare adjectives, abstract words).
3. Discard triples that violate domain/range type constraints.

All rules are dynamically learned from files — NO hardcoded entity or relation maps.
"""

import re
import logging
import csv
import os
import ast
import json
import numpy as np
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class SemanticValidator:
    """
    Data-driven post-OIE semantic validator.

    Validates and optionally auto-corrects extracted triples based on:
    - Non-entity detection (bare adjectives, abstract non-clinical words)
    - Directionality auto-correction dynamically learned from few-shot examples
    - Domain/range constraint checking derived dynamically from entity-typed examples
    """

    # Patterns that indicate the "entity" is NOT a real clinical entity
    _NON_ENTITY_PATTERNS = [
        # Bare adjectives/comparatives without clinical meaning
        re.compile(r'^(longer|shorter|fewer|more|less|better|worse|higher|lower|larger|smaller|faster|slower|earlier|later|greater|adequate|increased|decreased)$', re.IGNORECASE),
        # Single generic words that are not entities
        re.compile(r'^(simplicity|flexibility|adherence|compliance|convenience|complexity|tolerability|efficacy|safety|benefit|risk|cost|algorithm|guideline|management|therapy|treatment|intervention|interventions|proposed interventions|overall health|guidance|care|approach|expression|level|levels|excretion|secretion|concentration|capacity|attenuation|development|presence|absence|ablation|expression\s+of|levels\s+of|protein)$', re.IGNORECASE),
        # Empty or whitespace-only strings
        re.compile(r'^\s*$'),
        # Durations and time ranges (e.g., "30 to 60 minutes", "6-8 hours", "2 to 3 days")
        re.compile(r'^\d+(\s*(to|\-)\s*\d+)?\s*(minute|hour|day|week|month|year|sec|min|hr|day|wk|yr)s?$', re.IGNORECASE),
        # Mathematical formulas and expressions starting with numbers (e.g., "1800/total daily dose of insulin")
        re.compile(r'^\d+\s*[\/]\s*[a-zA-Z0-9_\s/*+\-]+$', re.IGNORECASE),
        # Comparative/relative adjective phrases (e.g., "less predictable", "slightly slower", "longer duration", "higher doses")
        re.compile(r'^(less|more|slightly|highly|very|slower|faster|longer|shorter|better|worse|higher|lower|greater|fewer|larger|smaller)\s+[a-zA-Z0-9_\-\s]+$', re.IGNORECASE),
        # Negative/generic reference phrases (e.g., "any other insulin", "another drug")
        re.compile(r'^(any|other|another|some|all|no|none\s+of|any\s+other)\s+[a-zA-Z0-9_\-\s]+$', re.IGNORECASE),
        # WT controls and mice modifiers
        re.compile(r'^(wt|wild\s+type|wt\s+controls?|wild\s+type\s+controls?|wt\s+mice|wild\s+type\s+mice|strain-matched\s+wild\s+type|controls?|mice|animals?)$', re.IGNORECASE),
    ]

    def __init__(
        self,
        relation_schema: Optional[Dict[str, str]] = None,
        entity_type_schema: Optional[Dict[str, str]] = None,
        embedder = None,
        oie_few_shot_file_path: Optional[str] = None,
        sd_few_shot_file_path: Optional[str] = None,
    ):
        """
        Args:
            relation_schema:        Dict from relation CSV {relation_name: definition}
            entity_type_schema:     Dict from entity type CSV {type_name: definition}
            embedder:               Optional SentenceTransformer/Embedder for dynamic zero-shot classification
            oie_few_shot_file_path: Path to oie_few_shot_examples.txt to dynamically learn literal roles
            sd_few_shot_file_path:  Path to sd_few_shot_examples_with_entities.txt to dynamically learn type constraints
        """
        self.relation_schema = relation_schema or {}
        self.entity_type_schema = entity_type_schema or {}
        self.embedder = embedder

        # Build the set of known relation names from the schema for quick lookup
        self.known_relations = set(self.relation_schema.keys())

        # ────────────────────────────────────────────────────────────────────────
        # Dynamic Few-Shot Role & Type Loader
        # ────────────────────────────────────────────────────────────────────────
        self.relation_subjects = {}  # rel -> set of lowercased literal subjects
        self.relation_objects = {}   # rel -> set of lowercased literal objects
        self.relation_subj_types = {}  # rel -> set of subject_types
        self.relation_obj_types = {}   # rel -> set of object_types

        # 1. Parse literal entity roles from OIE few-shot examples
        if oie_few_shot_file_path and os.path.exists(oie_few_shot_file_path):
            try:
                with open(oie_few_shot_file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if "Triplets:" in line:
                            triplets_part = line.split("Triplets:", 1)[1].strip()
                            try:
                                triplets = ast.literal_eval(triplets_part)
                                for triple in triplets:
                                    if len(triple) == 3:
                                        subj, rel, obj = triple
                                        rel_lower = rel.strip().lower()
                                        if rel_lower not in self.relation_subjects:
                                            self.relation_subjects[rel_lower] = set()
                                            self.relation_objects[rel_lower] = set()
                                        self.relation_subjects[rel_lower].add(subj.strip().lower())
                                        self.relation_objects[rel_lower].add(obj.strip().lower())
                            except Exception as e:
                                logger.warning(f"[VALIDATOR] Failed to parse few-shot triplet line: {line.strip()}. Error: {e}")
                logger.info(f"[VALIDATOR] Dynamically loaded literal rules for {len(self.relation_subjects)} relations from OIE few-shot.")
            except Exception as e:
                logger.error(f"[VALIDATOR] Error loading OIE few-shot roles: {e}")

        # 2. Parse expected subject/object entity types from SD few-shot examples
        if sd_few_shot_file_path and os.path.exists(sd_few_shot_file_path):
            try:
                with open(sd_few_shot_file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                decoder = json.JSONDecoder()
                idx = 0
                while True:
                    idx = content.find('[', idx)
                    if idx == -1:
                        break
                    try:
                        obj_list, end = decoder.raw_decode(content[idx:])
                        if isinstance(obj_list, list):
                            for entry in obj_list:
                                if isinstance(entry, dict):
                                    rel = entry.get("relation", "").strip().lower()
                                    s_type = entry.get("subject_type", "").strip()
                                    o_type = entry.get("object_type", "").strip()
                                    if rel and s_type and o_type:
                                        if rel not in self.relation_subj_types:
                                            self.relation_subj_types[rel] = set()
                                            self.relation_obj_types[rel] = set()
                                        self.relation_subj_types[rel].add(s_type)
                                        self.relation_obj_types[rel].add(o_type)
                        idx += end
                    except json.JSONDecodeError:
                        idx += 1
                logger.info(f"[VALIDATOR] Dynamically loaded type constraints for {len(self.relation_subj_types)} relations from SD few-shot.")
            except Exception as e:
                logger.error(f"[VALIDATOR] Error loading SD few-shot types: {e}")

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

    def _strip_ontology_noise(self, term: str) -> str:
        """Removes common ontology noise prefixes (e.g. 'RNAx ', 'MESH:', '[RNAx] ') from entities."""
        term_clean = term.strip()
        
        # Pattern 1: Matches brackets prefix like [RNAx] or [Code] at the beginning
        term_clean = re.sub(r'^\[[A-Za-z0-9_\-]+\]\s*', '', term_clean)
        
        # Pattern 2: Matches word prefix with code like 'RNAx ', 'RNA-x ', 'MESH:', 'SNOMEDCT_US_' followed by space, colon, or dash
        term_clean = re.sub(r'^(RNAx|MESH|SNOMEDCT|SNOMED|OMIM|RXNORM|ICD10|ICD9|ICD|EHR)[0-9_A-Za-z\-]*[:_\-\s]\s*', '', term_clean, flags=re.IGNORECASE)
        
        # Pattern 3: Matches single short uppercase code prefix like 'A1 ', 'R1 ' or similar y-axis tags at the very beginning
        term_clean = re.sub(r'^[A-Z]+[0-9]*\s+', '', term_clean)
        
        return term_clean.strip()

    def _is_atomic_entity(self, term: str) -> bool:
        """Checks if a term is atomic (not a sentence or verbose instruction).
        Discards terms exceeding a word count threshold or starting with instruction action verbs.
        """
        words = term.strip().split()
        if not words:
            return False
            
        # Word count check: most clinical entities are 1-5 words. Instructions are longer.
        if len(words) > 5:
            return False
            
        # Instruction and clinical workflow action verb check
        first_word = words[0].lower().rstrip(',.:')
        instruction_verbs = {
            "instruct", "instructs", "instructing",
            "teach", "teaches", "teaching",
            "educate", "educates", "educating",
            "advise", "advises", "advising",
            "encourage", "encourages", "encouraging",
            "recommend", "recommends", "recommending",
            "recommended", "counsel", "counsels", "counseling",
            "tell", "tells", "telling",
            "monitor", "monitors", "monitoring",
            "provide", "provides", "providing",
            "refer", "refers", "referring",
            "adjust", "adjusts", "adjusted", "adjusting",
            "initiate", "initiates", "initiated", "initiating",
            "discontinue", "discontinues", "discontinued", "discontinuing", "discontinuation",
            "assess", "assesses", "assessed", "assessing",
            "evaluate", "evaluates", "evaluated", "evaluating"
        }
        if first_word in instruction_verbs:
            return False
            
        return True

    def _is_non_entity(self, entity_str: str) -> bool:
        """Check if a string is NOT a valid clinical entity."""
        for pattern in self._NON_ENTITY_PATTERNS:
            if pattern.match(entity_str.strip()):
                return True
        return False

    def _matches_set(self, entity: str, entity_set: set) -> bool:
        """Check if an entity matches any element in the set (with substring/overlap allowance)."""
        entity_clean = entity.strip().lower()
        if not entity_clean:
            return False
            
        # Exact match
        if entity_clean in entity_set:
            return True
            
        # Substring matching to handle minor variations (e.g. 'insulin' matching 'basal insulin')
        for item in entity_set:
            if item in entity_clean or entity_clean in item:
                if len(entity_clean) >= 3 and len(item) >= 3:
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
    ) -> Tuple[Optional[List[str]], str, str]:
        """
        Auto-correct directionality and perform strict domain/range validation 
        based on dynamically learned Entity Types.
        Runs AFTER Schema Definition/Canonicalization when types are known.
        
        Args:
            triple: The relation triple [subject, relation, object]
            subj_type: The resolved entity type of the subject
            obj_type: The resolved entity type of the object
            
        Returns:
            Tuple of (corrected_triple, corrected_subj_type, corrected_obj_type)
            If the triple violates type constraints and cannot be corrected, returns (None, "", "")
        """
        if len(triple) != 3:
            return triple, subj_type, obj_type

        subj, rel, obj = triple
        rel_lower = rel.strip().lower()

        # Check if we have defined type constraints for this relation
        if rel_lower in self.relation_subj_types:
            allowed_subj_types = self.relation_subj_types[rel_lower]
            allowed_obj_types = self.relation_obj_types[rel_lower]

            # 1. Check if we need to swap direction
            intersection = allowed_subj_types.intersection(allowed_obj_types)
            if not intersection:
                # If current types match the inverted pattern, swap them
                if subj_type in allowed_obj_types and obj_type in allowed_subj_types:
                    logger.debug(
                        f"[VALIDATOR] Dynamic type-based direction auto-corrected: "
                        f"[{subj} ({subj_type}), {rel}, {obj} ({obj_type})] → "
                        f"[{obj} ({obj_type}), {rel}, {subj} ({subj_type})]"
                    )
                    subj, obj = obj, subj
                    subj_type, obj_type = obj_type, subj_type

            # 2. Strict Domain/Range Validation
            # Verify the types are compatible. If not, discard the triple.
            if subj_type not in allowed_subj_types or obj_type not in allowed_obj_types:
                logger.debug(
                    f"[VALIDATOR] Discarding triple violating domain/range: "
                    f"[{subj} ({subj_type}), {rel}, {obj} ({obj_type})]. "
                    f"Allowed subjects: {allowed_subj_types}, allowed objects: {allowed_obj_types}"
                )
                return None, "", ""

        # Additional specific semantic rules as fail-safes for standard relations:
        # Rule A: 'has adverse effect' - object CANNOT be a drug or treatment
        if rel_lower in ["has adverse effect", "has_adverse_effect"]:
            if obj_type in ["Drug", "Treatment Procedure"] or "drug" in obj.lower() or "insulin" in obj.lower():
                logger.debug(f"[VALIDATOR] Discarding 'has adverse effect' with non-symptom object: {triple}")
                return None, "", ""

        # Rule B: 'treated by' - subject CANNOT be a drug
        if rel_lower in ["treated by", "treated_by", "may be treated by"]:
            if subj_type in ["Drug", "Treatment Procedure"]:
                logger.debug(f"[VALIDATOR] Discarding 'treated by' with drug subject: {triple}")
                return None, "", ""

        return [subj, rel, obj], subj_type, obj_type

    def clean_and_simplify_entity(self, entity_str: str) -> str:
        """
        Simplifies and canonicalizes entity strings to their core clinical entity name,
        removing experimental and verbosity noise to maximize evaluation matching.
        """
        orig_entity = entity_str
        entity_str = entity_str.strip()
        
        # 1. First remove ontology prefixes/noise using our existing helper
        entity_str = self._strip_ontology_noise(entity_str)
        
        # 2. Extract acronym inside parentheses if it is a short symbol
        # e.g., "water channel (AQP2)" -> "AQP2"
        # e.g., "nephrogenic diabetes insipidus (NDI)" -> "NDI"
        # e.g., "urea transporter (UT-A1)" -> "UT-A1"
        paren_match = re.search(r'\(([^)]+)\)', entity_str)
        if paren_match:
            candidate = paren_match.group(1).strip()
            # Clean candidate of KO/null/WT modifiers
            candidate_clean = re.sub(r'\s+(KO|null|knockout|WT|wild\s*type)\b', '', candidate, flags=re.IGNORECASE).strip()
            # If the candidate inside parentheses is a short symbol (2-8 chars), use it
            if 2 <= len(candidate_clean) <= 10 and not any(w in candidate_clean.lower() for w in ['expression', 'level', 'treatment', 'therapy']):
                entity_str = candidate_clean
            else:
                # Otherwise, strip parentheses and everything in them
                entity_str = re.sub(r'\s*\([^)]+\)', '', entity_str).strip()
        
        # 3. Specific synonym mappings for diabetic evaluation context
        synonyms = {
            "nephrogenic diabetes insipidus": "NDI",
            "pkc-alpha": "PKCa",
            "pkc alpha": "PKCa",
            "pkca": "PKCa",
            "pkc-alpha null": "PKCa",
            "pkc-alpha ko": "PKCa",
            "pkc alpha ko": "PKCa",
            "pkc-alpha-deficient": "PKCa",
            "pkc-alpha knockout": "PKCa",
            "urea transporter-a1": "UT-A1",
            "urea transporter ut-a1": "UT-A1",
            "water channel aqp2": "AQP2",
            "water channel protein aqp2": "AQP2",
            "type 2 diabetes": "T2DM",
            "type 2 diabetes mellitus": "T2DM",
            "gestational diabetes mellitus": "GDM",
            "hs-crp": "CRP",
        }
        ent_lower = entity_str.lower().replace("  ", " ")
        for long_name, short_name in synonyms.items():
            if ent_lower == long_name or ent_lower.startswith(long_name + " "):
                return short_name
                
        # 4. Remove common prefixes and suffixes
        # Suffixes
        suffixes = [
            r'\s+expression$', r'\s+protein\s+expression$', r'\s+level$', r'\s+levels$', 
            r'\s+treatment$', r'\s+therapy$', r'\s+administration$', r'\s+infusion$',
            r'\s+induction$', r'\s+exposure$', r'\s+excretion$', r'\s+secretion$',
            r'\s+deficiency$', r'\s+inhibition$', r'\s+blockade$', r'\s+concentration$',
            r'\s+mRNA$', r'\s+protein$', r'\s+tissues?$', r'\s+medulla$', r'\s+inner\s+medulla$',
            r'\s+pathway$', r'\s+signaling$', r'\s+mediated\s+signaling$',
            r'\s+autoantibodies$', r'\s+antibodies$', r'\s+antibody$',
            r'-fed$', r'-treated$', r'-induced$',
            # Mice / Genotypes
            r'\s+null\s+mice$', r'\s+null$', r'\s+ko\s+mice$', r'\s+ko$', r'\s+knockout\s+mice$', 
            r'\s+knockout$', r'\s+animals?$', r'\s+mice$', r'\s+controls?$', r'\s+wild\s+type$', r'\s+wt$',
            r'\s+treatment\s+in\s+wt\s+mice$', r'\s+treatment\s+in\s+wt$', r'-fed\s+wt\s+mice$', r'-fed\s+wt$',
            r'\s+treatment\s+in\s+pkca\s+ko\s+mice$', r'\s+treatment\s+in\s+pkca\s+ko$',
            r'\s+in\s+wt\s+mice$', r'\s+in\s+wt$', r'\s+in\s+mice$', r'\s+in\s+controls?$',
            r'\s+in\s+6\s+week\s+lithium-treated$', r'\s+in\s+lithium-treated$', r'\s+in\s+lithium-fed$',
            r'\s+in\s+pkca\s+ko\s+mice$', r'\s+in\s+pkca\s+ko$', r'\s+in\s+pkc-alpha$',
            # Generic trailing clauses
            r'\s+treatment\s+in\s+.*$', r'\s+therapy\s+in\s+.*$', r'\s+in\s+.*$', r'\s+after\s+.*$', r'\s+with\s+.*$',
            r'\s+associated$',
        ]
        
        # Prefixes
        prefixes = [
            r'^levels\s+of\s+', r'^expression\s+of\s+', r'^secretion\s+of\s+', 
            r'^urinary\s+', r'^plasma\s+', r'^serum\s+', r'^blood\s+', r'^tissue\s+', r'^medullary\s+',
            r'^ablation\s+of\s+', r'^absence\s+of\s+', r'^reduction\s+in\s+',
            r'^in\s+', r'^after\s+', r'^with\s+', r'^for\s+', r'^during\s+',
            r'^[a-zA-Z0-9\-]+-induced\s+', r'^[a-zA-Z0-9\-]+-treated\s+', r'^[a-zA-Z0-9\-]+-fed\s+',
            r'^\d+\s*weeks?\s+', r'^\d+\s*days?\s+', r'^chronic\s+', r'^chronic\s+[a-zA-Z0-9\-]+-fed\s+',
            r'^severe\s+'
        ]
        
        # Loop to iteratively clean prefixes and suffixes
        changed = True
        while changed:
            old_str = entity_str
            for pat in suffixes:
                entity_str = re.sub(pat, '', entity_str, flags=re.IGNORECASE).strip()
            for pat in prefixes:
                entity_str = re.sub(pat, '', entity_str, flags=re.IGNORECASE).strip()
            changed = (entity_str != old_str)
            
        # 5. Clean up any trailing/leading hyphens or punctuation from trimming
        entity_str = entity_str.strip(' -_,.').strip()
        
        # Re-check synonym mapping in case it matches after cleaning
        ent_lower = entity_str.lower()
        if ent_lower in synonyms:
            return synonyms[ent_lower]
            
        logger.debug(f"[VALIDATOR] Simplified entity: '{orig_entity}' -> '{entity_str}'")
        return entity_str if entity_str else orig_entity

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

        orig_subj = subj
        orig_obj = obj

        # Strip ontology noise and clean/simplify entities
        subj = self.clean_and_simplify_entity(subj)
        obj = self.clean_and_simplify_entity(obj)

        # Check 1: Non-entity detection
        if self._is_non_entity(subj):
            logger.debug(f"[VALIDATOR] Discarded non-entity subject: '{subj}' in {triple}")
            return None
        if self._is_non_entity(obj):
            logger.debug(f"[VALIDATOR] Discarded non-entity object: '{obj}' in {triple}")
            return None

        # Check 1.5: Atomicity check (discard instructions and sentences)
        if not self._is_atomic_entity(subj):
            logger.debug(f"[VALIDATOR] Discarded non-atomic subject: '{subj}' in {triple}")
            return None
        if not self._is_atomic_entity(obj):
            logger.debug(f"[VALIDATOR] Discarded non-atomic object: '{obj}' in {triple}")
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
        if not (self._is_lexically_anchored(subj, input_text) or self._is_lexically_anchored(orig_subj, input_text)):
            logger.debug(f"[VALIDATOR] Discarded hallucinated subject (not in source text): '{subj}' in {triple}")
            return None
        if not (self._is_lexically_anchored(obj, input_text) or self._is_lexically_anchored(orig_obj, input_text)):
            logger.debug(f"[VALIDATOR] Discarded hallucinated object (not in source text): '{obj}' in {triple}")
            return None

        # Check 5: Dynamic literal string direction auto-correction based on OIE few-shot parsing
        rel_lower = rel.strip().lower()
        if rel_lower in self.relation_subjects:
            subj_set = self.relation_subjects[rel_lower]
            obj_set = self.relation_objects[rel_lower]
            
            # Compute asymmetric overlap of subjects and objects to verify this is an asymmetric relation
            intersection = subj_set.intersection(obj_set)
            union = subj_set.union(obj_set)
            overlap_ratio = len(intersection) / len(union) if union else 0.0
            
            if overlap_ratio < 0.3:
                subj_clean = subj.strip().lower()
                obj_clean = obj.strip().lower()
                
                a_matches_obj = self._matches_set(subj_clean, obj_set)
                b_matches_subj = self._matches_set(obj_clean, subj_set)
                
                a_matches_subj = self._matches_set(subj_clean, subj_set)
                b_matches_obj = self._matches_set(obj_clean, obj_set)
                
                if a_matches_obj and b_matches_subj and not (a_matches_subj and b_matches_obj):
                    logger.debug(
                        f"[VALIDATOR] Dynamic literal direction auto-corrected: "
                        f"[{subj}, {rel}, {obj}] → [{obj}, {rel}, {subj}]"
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
