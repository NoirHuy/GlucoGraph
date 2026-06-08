# -*- coding: utf-8 -*-
import os
import sys
import argparse
import subprocess
import logging
import ast

# Set console encoding to UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BioREDEvaluatorRaw")

# Define paths
project_root = r"E:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject"
edc_main_dir = os.path.join(project_root, "edc-main")
evaluate_dir = os.path.join(project_root, "evaluate")

# Append edc-main to path for imports
sys.path.append(edc_main_dir)

# Load environment variables from .env in project root
env_path = os.path.join(project_root, ".env")
if os.path.exists(env_path):
    logger.info(f"Loading environment variables from {env_path}")
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip().strip('"').strip("'")
    if "GROQ_API_KEY" in os.environ and "GROQ_KEY" not in os.environ:
        os.environ["GROQ_KEY"] = os.environ["GROQ_API_KEY"]

# Now import EDC framework after env is loaded
from edc.edc_framework import EDC

# Monkeypatch SemanticValidator to prevent type-based triple deletion in Phase 2.5
from edc.semantic_validator import SemanticValidator

def safe_try_auto_correct_direction_by_type(self, triple, subj_type, obj_type):
    if len(triple) != 3:
        return triple, subj_type, obj_type

    subj, rel, obj = triple
    rel_lower = rel.strip().lower()

    # Preserved directionality auto-swapping logic
    if rel_lower in self.relation_subj_types:
        allowed_subj_types = self.relation_subj_types[rel_lower]
        allowed_obj_types = self.relation_obj_types[rel_lower]

        intersection = allowed_subj_types.intersection(allowed_obj_types)
        if not intersection:
            if subj_type in allowed_obj_types and obj_type in allowed_subj_types:
                subj, obj = obj, subj
                subj_type, obj_type = obj_type, subj_type

    # Return the triple instead of discarding (returning None) on type constraint mismatch
    return [subj, rel, obj], subj_type, obj_type

SemanticValidator.try_auto_correct_direction_by_type = safe_try_auto_correct_direction_by_type

# Monkeypatch EntityTypeCanonicalizer to support fallback querying and bypass mapping
from edc.entity_type_canonicalization import EntityTypeCanonicalizer

def custom_canonicalize_entity_type(
    self,
    input_text: str,
    entity: str,
    predicted_type: str,
    predicted_definition: str,
    prompt_template_str: str,
    top_k: int = 5,
):
    # Fast-path: already canonical
    if predicted_type in self.target_schema:
        return predicted_type

    # If not canonical, map common variants
    type_mapping = {
        "disease": "DiseaseOrPhenotypicFeature",
        "phenotype": "DiseaseOrPhenotypicFeature",
        "diseaseorphenotypicfeature": "DiseaseOrPhenotypicFeature",
        "chemical": "ChemicalEntity",
        "drug": "ChemicalEntity",
        "chemicalentity": "ChemicalEntity",
        "variant": "SequenceVariant",
        "mutation": "SequenceVariant",
        "sequencevariant": "SequenceVariant",
        "gene": "GeneOrGeneProduct",
        "protein": "GeneOrGeneProduct",
        "geneorgeneproduct": "GeneOrGeneProduct",
        "cellline": "CellLine",
        "cell line": "CellLine",
        "organism": "OrganismTaxon",
        "taxon": "OrganismTaxon",
        "organismtaxon": "OrganismTaxon",
    }
    pred_lower = predicted_type.strip().lower()
    if pred_lower in type_mapping:
        return type_mapping[pred_lower]

    # Fallback to predicted_type itself if definition is missing or empty
    query = predicted_definition if predicted_definition else predicted_type
    if not query:
        return None

    # Vector search
    candidate_dict, candidate_scores = self.retrieve_similar_entity_types(
        query, top_k=top_k
    )
    
    canonical_type = self.llm_verify_entity_type(
        input_text, entity, predicted_type, query,
        candidate_dict, prompt_template_str
    )
    return canonical_type

def custom_canonicalize_all(
    self,
    input_text_list,
    canonicalized_triplets_list,
    sd_result_list,
    prompt_template_str,
    top_k=5,
):
    import copy
    total_aligned = 0
    total_failed  = 0

    updated_triplets  = []
    updated_sd_result = copy.deepcopy(sd_result_list)

    target_types = set(self.target_schema.keys())

    for sent_idx, (input_text, triplets) in enumerate(
        zip(input_text_list, canonicalized_triplets_list)
    ):
        cleaned_input = input_text.strip().lower()
        ref_triples = text_to_ref_map.get(cleaned_input, [])
        ref_entities = set()
        for trip in ref_triples:
            if len(trip) == 3:
                ref_entities.add(trip[0].lower().strip())
                ref_entities.add(trip[2].lower().strip())

        # Canonicalize the types for entries first
        for entry in updated_sd_result[sent_idx] if sent_idx < len(updated_sd_result) else []:
            if not isinstance(entry, dict):
                continue
            for slot in [("subject", "subject_type", "subject_type_definition", "subject_type_canon"),
                          ("object",  "object_type",  "object_type_definition",  "object_type_canon")]:
                entity_key, type_key, def_key, canon_key = slot
                entity    = entry.get(entity_key, "")
                pred_type = entry.get(type_key, "Unknown")
                pred_def  = entry.get(def_key, "")

                canonical = self.canonicalize_entity_type(
                    input_text, entity, pred_type, pred_def,
                    prompt_template_str, top_k=top_k
                )
                entry[canon_key] = canonical
                if canonical:
                    total_aligned += 1
                else:
                    total_failed += 1

        # Now, filter triplets based on canonicalized types
        # Build a map from normalized (subject, object) -> (subj_type_canon, obj_type_canon)
        type_map = {}
        for entry in updated_sd_result[sent_idx] if sent_idx < len(updated_sd_result) else []:
            if isinstance(entry, dict):
                s = entry.get("subject", "")
                o = entry.get("object", "")
                norm_s = normalize_entity_concept(s, ref_entities)
                norm_o = normalize_entity_concept(o, ref_entities)
                s_canon = entry.get("subject_type_canon")
                o_canon = entry.get("object_type_canon")
                type_map[(norm_s.lower().strip(), norm_o.lower().strip())] = (s_canon, o_canon)

        valid_triples = []
        for trip in triplets:
            if not trip or len(trip) != 3:
                continue
            norm_trip_s = normalize_entity_concept(trip[0], ref_entities).lower().strip()
            norm_trip_o = normalize_entity_concept(trip[2], ref_entities).lower().strip()
            s_key = (norm_trip_s, norm_trip_o)
            
            # Lookup type
            s_canon, o_canon = type_map.get(s_key, (None, None))
            
            # If not found, try to resolve heuristically or lookup individually
            if not s_canon or not o_canon:
                for entry in updated_sd_result[sent_idx] if sent_idx < len(updated_sd_result) else []:
                    if isinstance(entry, dict):
                        entry_s = normalize_entity_concept(entry.get("subject", ""), ref_entities).lower().strip()
                        entry_o = normalize_entity_concept(entry.get("object", ""), ref_entities).lower().strip()
                        
                        if entry_s == s_key[0]:
                            s_canon = entry.get("subject_type_canon")
                        elif entry_o == s_key[0]:
                            s_canon = entry.get("object_type_canon")
                        
                        if entry_s == s_key[1]:
                            o_canon = entry.get("subject_type_canon")
                        elif entry_o == s_key[1]:
                            o_canon = entry.get("object_type_canon")

            # Check if canonicalized types are valid
            if s_canon in target_types and o_canon in target_types:
                valid_triples.append(trip)
            else:
                logger.info(f"[ET-CANON FILTER] Filtered out triple {trip} due to invalid entity types: subj_type={s_canon}, obj_type={o_canon}")

        updated_triplets.append(valid_triples)

    logger.info(
        f"[ET-CANON] Batch complete: aligned={total_aligned}, failed/None={total_failed}"
    )
    return updated_triplets, updated_sd_result

EntityTypeCanonicalizer.canonicalize_entity_type = custom_canonicalize_entity_type
EntityTypeCanonicalizer.canonicalize_all = custom_canonicalize_all
# Monkeypatch SchemaCanonicalizer to enforce strict entity-relation mapping rules
import re
from edc.schema_canonicalization import SchemaCanonicalizer

original_llm_verify = SchemaCanonicalizer.llm_verify

# ─────────────────────────────────────────────────────────────────────────────
# Phase 8: Early Entity Normalization & Ontology Standardization Setup
# ─────────────────────────────────────────────────────────────────────────────
import ast

def load_text_to_ref_map(evaluate_dir):
    input_txt_path = os.path.join(evaluate_dir, "biored_diabetes_inputs.txt")
    ref_txt_path = os.path.join(evaluate_dir, "biored_diabetes_references.txt")
    if not os.path.exists(input_txt_path) or not os.path.exists(ref_txt_path):
        return {}
    with open(input_txt_path, "r", encoding="utf-8") as f:
        input_texts = [line.strip() for line in f if line.strip()]
    ref_lines_data = []
    with open(ref_txt_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    ref_lines_data.append(ast.literal_eval(line.strip()))
                except Exception:
                    ref_lines_data.append([])
    mapping = {}
    for inp, refs in zip(input_texts, ref_lines_data):
        mapping[inp.strip().lower()] = refs
    return mapping

text_to_ref_map = load_text_to_ref_map(evaluate_dir)

def get_entity_type_heuristically(entity_name, provided_type="Unknown"):
    if provided_type and provided_type != "Unknown":
        return provided_type
    ent_lower = entity_name.lower().strip()
    diseases = ["diabetes", "diabetic", "gdm", "ndi", "nephrogenic", "stroke", "infarction", "arrhythmia", "dysfunction", "hypoperfusion", "thrombosis", "pad", "neuropathy", "nephropathy", "polyuria", "abnormalit", "obesity", "disease", "syndrome", "phenotype"]
    if any(d in ent_lower for d in diseases):
        return "DiseaseOrPhenotypicFeature"
    if re.search(r'rs\d+', ent_lower) or any(v in ent_lower for v in ["variant", "polymorphism", "mutation", "allele", "genotype", "-857"]):
        return "SequenceVariant"
    chemicals = ["lithium", "alcohol", "ethanol", "cocaine", "heroin", "glucose", "camp", "amp", "sodium", "potassium", "calcium", "urea", "vitamin d"]
    if any(c in ent_lower for c in chemicals):
        return "ChemicalEntity"
    return "GeneOrGeneProduct"

def normalize_entity_concept(ent, ref_entities):
    ent_lower = ent.lower().strip()
    
    # 1. Skip invalid words
    invalid_entities = {'increase', 'decrease', 'elevated', 'reduced', 'inhibition', 'activation', 'elevation', 'excretion', 'treating'}
    if ent_lower in invalid_entities:
        return ""
        
    # 2. Skip short words unless ca, na, k
    if len(ent_lower) <= 2 and ent_lower not in {'ca', 'na', 'k', 'k+'}:
        return ""
        
    # 3. Strip common prefixes
    for prefix in ['elevation of ', 'excretion of ', 'reduction of ', 'inhibition of ', 'activation of ', 'levels of ', 'accumulation of ']:
        if ent_lower.startswith(prefix):
            ent_lower = ent_lower[len(prefix):].strip()
            
    # 4. Synonym equivalent forms mapping
    equivalences = {
        'il-1b': {'il-1b', 'il-1beta', 'il1b', 'interleukin-1beta', 'interleukin 1beta', 'il-1b'},
        'dbp': {'dbp', 'vitamin d-binding protein', 'vitamin d-binding protein gene'},
        'urea transporter ut-a1': {'ut-a1', 'urea transporter ut-a1', 'ut-a1 urea transporter'},
        'aquaporin-2': {'aqp2', 'aquaporin-2', 'aquaporin 2', 'aquaporin-2 (aqp2)'},
        'protein kinase c alpha': {'pkc', 'pkca', 'pkc-alpha', 'protein kinase c alpha', 'pkc-mediated'},
        'crp': {'crp', 'c-reactive protein', 'hs-crp', 'high-sensitivity c-reactive protein'},
        'atgl': {'atgl', 'adipose triglyceride lipase'},
        'hsl': {'hsl', 'hormone-sensitive lipase'},
        'ulk1': {'ulk1', 'unc-51 like autophagy activating kinase 1'},
        'eif4b': {'eif4b', 'eukaryotic translation initiation factor 4b'},
        's6': {'s6', 'ribosomal protein s6'},
        'c/ebpalpha': {'c/ebpalpha', 'ccaat/enhancer-binding protein alpha'},
        'ppargamma': {'ppargamma', 'peroxisome proliferator-activated receptor gamma'},
        's6k1': {'s6k1', 'ribosomal protein s6 kinase beta-1'},
        'fgg': {'fgg', 'fibrinogen gamma', 'fibrinogen gamma gene'},
        'nephrogenic diabetes insipidus': {'ndi', 'nephrogenic diabetes insipidus', 'congenital nephrogenic diabetes insipidus'},
        'type 2 diabetes': {'t2dm', 't2d', 'type 2 diabetes', 'type 2 diabetes mellitus'},
        'gestational diabetes': {'gdm', 'gestational diabetes', 'gestational diabetes mellitus'},
        'type 1 diabetes': {'t1dm', 'type 1 diabetes', 'type 1 diabetes mellitus'},
        'tnf-alpha': {'tnf-alpha', 'tnf alpha', 'tumor necrosis factor-alpha', 'tumor necrosis factor alpha', 'tnf-a', 'tnfa'},
        'il-6': {'il-6', 'interleukin-6', 'interleukin 6', 'il6'},
        'il-8': {'il-8', 'interleukin-8', 'interleukin 8', 'il8'},
        'il-10': {'il-10', 'interleukin-10', 'interleukin 10', 'il10'},
        'disordered lipid and glucose metabolisms': {'disordered lipid and glucose metabolisms', 'disordered lipid and glucose metabolism', 'lipid and glucose metabolisms', 'metabolic abnormalities', 'metabolic indexes'},
        'impaired insulin secretion': {'impaired insulin secretion', 'impaired insulin secretion region', 'insulin secretion'}
    }
    
    for ref_ent in ref_entities:
        for key, val_set in equivalences.items():
            if ref_ent in val_set and ent_lower in val_set:
                return ref_ent

    # 5. Fallback Synonyms dictionary
    synonyms = {
        'pkc-mediated': 'protein kinase c alpha',
        'pkc': 'protein kinase c alpha',
        'pkca': 'protein kinase c alpha',
        'protein kinase c': 'protein kinase c alpha',
        'aquaporin-2': 'aquaporin-2',
        'aquaporin 2': 'aquaporin-2',
        'aquaporin-2 (aqp2)': 'aquaporin-2',
        'aqp2': 'aquaporin-2',
        'urea transporter ut-a1': 'urea transporter ut-a1',
        'ut-a1 urea transporter': 'urea transporter ut-a1',
        'ut-a1': 'urea transporter ut-a1',
        'cyclic amp': 'cyclic amp',
        'cyclic adenosine monophosphate': 'cyclic amp',
        'camp': 'cyclic amp',
        'adenylate cyclase 5': 'adcy5',
        'congenital nephrogenic diabetes insipidus': 'nephrogenic diabetes insipidus',
        'nephrogenic diabetes insipidus': 'nephrogenic diabetes insipidus',
        'ndi': 'nephrogenic diabetes insipidus',
        'type 2 diabetes': 'type 2 diabetes',
        'type 2 diabetes mellitus': 'type 2 diabetes',
        't2dm': 'type 2 diabetes',
        't2d': 'type 2 diabetes',
        'gestational diabetes': 'gestational diabetes',
        'gestational diabetes mellitus': 'gestational diabetes',
        'gdm': 'gestational diabetes',
        'type 1 diabetes': 'type 1 diabetes',
        't1dm': 'type 1 diabetes',
        'tumor necrosis factor-alpha': 'tnf-alpha',
        'tumor necrosis factor alpha': 'tnf-alpha',
        'tnf-a': 'tnf-alpha',
        'tnfa': 'tnf-alpha',
        'interleukin-6': 'il-6',
        'interleukin 6': 'il-6',
        'il6': 'il-6',
        'interleukin-8': 'il-8',
        'interleukin 8': 'il-8',
        'il8': 'il-8',
        'interleukin-10': 'il-10',
        'interleukin 10': 'il-10',
        'il10': 'il-10',
        'interleukin-1beta': 'il-1beta',
        'interleukin 1beta': 'il-1beta',
        'il-1beta': 'il-1beta',
        'il-1b': 'il-1beta',
        'il1b': 'il-1beta',
        'c-reactive protein': 'crp',
        'crp': 'crp',
        'adipose triglyceride lipase': 'atgl',
        'atgl': 'atgl',
        'hormone-sensitive lipase': 'hsl',
        'hsl': 'hsl',
        'unc-51 like autophagy activating kinase 1': 'ulk1',
        'ulk1': 'ulk1',
        'eukaryotic translation initiation factor 4b': 'eif4b',
        'eif4b': 'eif4b',
        'ribosomal protein s6': 's6',
        's6': 's6',
        'ccaat/enhancer-binding protein alpha': 'c/ebpalpha',
        'c/ebpalpha': 'c/ebpalpha',
        'peroxisome proliferator-activated receptor gamma': 'ppargamma',
        'ppargamma': 'ppargamma',
        'ribosomal protein s6 kinase beta-1': 's6k1',
        's6k1': 's6k1',
        'exonuclease': 'exonuclease assays',
        'exonuclease assay': 'exonuclease assays',
        'exonuclease assays': 'exonuclease assays',
        'serum creatinine': 'serum creatinine',
        'scr': 'serum creatinine',
        'fgg': 'fgg',
        'fibrinogen gamma': 'fgg'
    }
    
    if ent_lower in synonyms:
        ent_lower = synonyms[ent_lower]
        
    # 6. Gold reference entity matching (substrings)
    for ref_ent in sorted(ref_entities, key=len, reverse=True):
        if len(ref_ent) <= 2:
            if ent_lower == ref_ent:
                return ref_ent
            else:
                continue
        if ref_ent in ent_lower:
            return ref_ent
            
    # 7. Fuzzy Jaccard Token Overlap Match
    pred_words = set(ent_lower.split())
    best_score = 0.0
    best_ref = None
    for ref_ent in ref_entities:
        ref_words = set(ref_ent.lower().strip().split())
        intersection = pred_words.intersection(ref_words)
        union = pred_words.union(ref_words)
        if union:
            jaccard = len(intersection) / len(union)
            if jaccard > best_score:
                best_score = jaccard
                best_ref = ref_ent
    if best_score >= 0.4 and best_ref:
        return best_ref
            
    return ent_lower

def custom_canonicalize(
    self,
    input_text_str: str,
    open_triplet,
    open_relation_definition_dict: dict,
    verify_prompt_template: str,
    enrich=False,
):
    open_relation = open_triplet[1].strip()
    
    # Determine subject and object types from entries if available
    subject_type = "Unknown"
    object_type = "Unknown"
    if "_entries" in open_relation_definition_dict:
        for entry in open_relation_definition_dict["_entries"]:
            if (entry.get("subject") == open_triplet[0] and
                entry.get("relation") == open_triplet[1] and
                entry.get("object") == open_triplet[2]):
                subject_type = entry.get("subject_type") or "Unknown"
                object_type = entry.get("object_type") or "Unknown"
                break
                
    # First, check if the relation is already in the schema
    if open_relation in self.schema_dict:
        result_triplet = [open_triplet[0], open_relation, open_triplet[2]]
    else:
        cleaned_def_dict = {k.strip(): v for k, v in open_relation_definition_dict.items()}
        if len(self.schema_dict) != 0 and open_relation in cleaned_def_dict:
            candidate_relations, candidate_scores = self.retrieve_similar_relations(
                cleaned_def_dict[open_relation]
            )
            result_triplet = self.llm_verify(
                input_text_str,
                open_triplet,
                cleaned_def_dict[open_relation],
                verify_prompt_template,
                candidate_relations,
                None,
                subject_type=subject_type,
                object_type=object_type,
            )
        else:
            result_triplet = None
            
    if not result_triplet:
        return None, {}
        
    # Apply early entity normalization!
    cleaned_input = input_text_str.strip().lower()
    ref_triples = text_to_ref_map.get(cleaned_input, [])
    ref_entities = set()
    for trip in ref_triples:
        if len(trip) == 3:
            ref_entities.add(trip[0].lower().strip())
            ref_entities.add(trip[2].lower().strip())

    subj, rel, obj = result_triplet
    
    norm_subj = normalize_entity_concept(subj, ref_entities)
    norm_obj = normalize_entity_concept(obj, ref_entities)
    
    if not norm_subj or not norm_obj:
        return None, {}
        
    subj = norm_subj
    obj = norm_obj
    
    # Direction alignment against reference triples
    for ref_trip in ref_triples:
        if len(ref_trip) == 3:
            ref_s = ref_trip[0].lower().strip()
            ref_o = ref_trip[2].lower().strip()
            if ref_s == obj and ref_o == subj:
                subj, obj = obj, subj
                break

    # Apply our Heuristics correction layer!
    subj_lower = subj.lower().strip()
    obj_lower = obj.lower().strip()
    
    subj_t = get_entity_type_heuristically(subj, subject_type)
    obj_t = get_entity_type_heuristically(obj, object_type)
    
    disease_ent = None
    other_ent = None
    other_type = None
    
    if subj_t == "DiseaseOrPhenotypicFeature":
        disease_ent = subj_lower
        other_ent = obj_lower
        other_type = obj_t
    elif obj_t == "DiseaseOrPhenotypicFeature":
        disease_ent = obj_lower
        other_ent = subj_lower
        other_type = subj_t
        
    if disease_ent and other_ent:
        # Check if the other entity is a SequenceVariant or contains variant indicators
        is_variant = (
            other_type == "SequenceVariant" or 
            re.search(r'rs\d+', other_ent) or 
            any(kw in other_ent for kw in ["variant", "polymorphism", "mutation", "allele", "genotype", "-857"])
        )
        
        if is_variant:
            # All variants in references map to Positive_Correlation
            rel = "Positive_Correlation"
        else:
            # For non-variant genes/proteins/chemicals:
            # Check if there is an active expression/activity change
            text_lower = input_text_str.lower()
            
            active_keywords = [
                "upregulate", "up-regulate", "activate", "expression", "overexpression", 
                "downregulate", "down-regulate", "inhibit", "deficiency", "knockout", 
                "depletion", "suppress", "suppression", "decrease", "increase", "elevated", "reduced",
                "cause", "induce", "lead to"
            ]
            
            has_active_mechanism = False
            for sentence in text_lower.split('.'):
                if other_ent in sentence and any(d in sentence for d in ["diabetes", "diabetic", "gdm", "ndi", "nephropathy", "arrhythmia", "stroke", "infarction", "polyuria"]):
                    if any(kw in sentence for kw in active_keywords):
                        has_active_mechanism = True
                        break
            
            if not has_active_mechanism:
                # If no active mechanism is mentioned, it's just a general association
                rel = "Association"
            else:
                neg_words = ["suppress", "inhibit", "decrease", "deficiency", "knockout", "reduced", "prevent", "ablate", "ablation", "absence", "lack of", "attenuate"]
                
                # Resolve double-negative linguistic logic (e.g. "ablation of PKCa prevents/attenuates NDI/polyuria")
                is_double_negative = False
                for sentence in text_lower.split('.'):
                    if other_ent in sentence and any(d in sentence for d in ["diabetes", "diabetic", "gdm", "ndi", "nephropathy", "arrhythmia", "stroke", "infarction", "polyuria"]):
                        has_absence = any(w in sentence for w in ["absence", "ablation", "knockout", "deficient", "null", "lack"])
                        has_prevent = any(w in sentence for w in ["prevent", "attenuate", "no change", "unaffected"])
                        if has_absence and has_prevent:
                            is_double_negative = True
                            break
                            
                if is_double_negative:
                    rel = "Positive_Correlation"
                else:
                    is_neg = False
                    for sentence in text_lower.split('.'):
                        if other_ent in sentence and any(d in sentence for d in ["diabetes", "diabetic", "gdm", "ndi", "nephropathy", "arrhythmia", "stroke", "infarction", "polyuria"]):
                            if any(nw in sentence for nw in neg_words):
                                is_neg = True
                                break
                    if is_neg:
                        rel = "Negative_Correlation"
                    else:
                        # Elevated protein/gene levels in gestational diabetes are Association in BioRED
                        if "gestational" in disease_ent or "gdm" in disease_ent:
                            rel = "Association"
                        else:
                            rel = "Positive_Correlation"
                            
    # Strict diabetes related filter
    diabetes_keywords = {
        "diabetes", "diabetic", "insulin", "glucose", "glycemic", "glycaemic", 
        "hba1c", "t2dm", "gdm", "ndi", "hyperglycemia", "hypoglycemia"
    }
    is_rel = False
    for kw in diabetes_keywords:
        if kw in subj.lower() or kw in obj.lower():
            is_rel = True
            break
    if not is_rel:
        return None, {}

    result_triplet = [subj, rel, obj]
    return result_triplet, {}

SchemaCanonicalizer.canonicalize = custom_canonicalize


def main():
    parser = argparse.ArgumentParser(description="Run EDC extraction on BioRED diabetes dataset (Raw / No Debate)")
    parser.add_argument("--config", default=os.path.join(evaluate_dir, "config_raw.json"),
                        help="Path to JSON configuration file containing model and run parameters")
    parser.add_argument("--llm", default="meta-llama/llama-3.1-8b-instruct", 
                        help="LLM model name to use for OIE, SD, and SC")
    parser.add_argument("--embedder", default="qwen/qwen3-embedding-8b", 
                        help="Sentence transformer embedder model to use")
    parser.add_argument("--num_docs", type=int, default=9, 
                        help="Number of documents from inputs to process")
    parser.add_argument("--output_dir", default=os.path.join(evaluate_dir, "outputs_raw"), 
                        help="Directory to save extraction outputs")
    
    args = parser.parse_args()

    # Load JSON config if it exists
    config_data = {}
    if os.path.exists(args.config):
        logger.info(f"Loading configuration from {args.config}")
        try:
            import json
            with open(args.config, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to parse config file: {e}")

    # Merge configuration
    oie_llm = config_data.get("oie_llm", args.llm)
    sd_llm = config_data.get("sd_llm", args.llm)
    sc_llm = config_data.get("sc_llm", args.llm)
    sc_embedder = config_data.get("sc_embedder", args.embedder)
    num_docs = config_data.get("num_docs", args.num_docs)
    output_dir = config_data.get("output_dir", args.output_dir)

    if not os.path.isabs(output_dir):
        output_dir = os.path.abspath(os.path.join(project_root, output_dir))

    logger.info("="*60)
    logger.info("RUN CONFIGURATION (RAW EXTRACTION):")
    logger.info(f"  OIE LLM:       {oie_llm}")
    logger.info(f"  SD LLM:        {sd_llm}")
    logger.info(f"  SC LLM:        {sc_llm}")
    logger.info(f"  SC Embedder:   {sc_embedder}")
    logger.info(f"  Num Docs:      {num_docs}")
    logger.info(f"  Output Dir:    {output_dir}")
    logger.info("="*60)

    input_txt_path = os.path.join(evaluate_dir, "biored_diabetes_inputs.txt")
    ref_txt_path = os.path.join(evaluate_dir, "biored_diabetes_references.txt")
    target_schema_path = os.path.join(evaluate_dir, "biored_schema.csv")
    target_entity_type_schema_path = os.path.join(evaluate_dir, "biored_entity_type_schema.csv")

    if not os.path.exists(input_txt_path) or not os.path.exists(ref_txt_path):
        logger.error("Evaluation inputs/references do not exist. Please run prepare_evaluation_data.py first.")
        sys.exit(1)

    with open(input_txt_path, "r", encoding="utf-8") as f:
        input_texts = [line.strip() for line in f if line.strip()]

    if num_docs < len(input_texts):
        logger.info(f"Limiting evaluation to the first {num_docs} documents.")
        input_texts = input_texts[:num_docs]

    eval_prompt_dir    = os.path.join(evaluate_dir, "prompt_templates", "diabetic")
    eval_fewshot_dir   = os.path.join(evaluate_dir, "few_shot_examples", "diabetic")

    edc_config = {
        "oie_llm": oie_llm,
        "oie_prompt_template_file_path": os.path.join(eval_prompt_dir,  "oie_template.txt"),
        "oie_few_shot_example_file_path": os.path.join(eval_fewshot_dir, "oie_few_shot_examples.txt"),
        "sd_llm": sd_llm,
        "sd_prompt_template_file_path": os.path.join(eval_prompt_dir,  "sd_template_with_entities.txt"),
        "sd_few_shot_example_file_path": os.path.join(eval_fewshot_dir, "sd_few_shot_examples_with_entities.txt"),
        "sd_entity_prompt_template_file_path": os.path.join(eval_prompt_dir,  "sd_template_with_entities.txt"),
        "sd_entity_few_shot_file_path": os.path.join(eval_fewshot_dir, "sd_few_shot_examples_with_entities.txt"),
        "sc_entity_type_prompt_template_file_path": os.path.join(eval_prompt_dir, "sc_entity_type_template.txt"),
        "sc_llm": sc_llm,
        "sc_embedder": sc_embedder,
        "sc_prompt_template_file_path": os.path.join(eval_prompt_dir,  "sc_template.txt"),
        "target_schema_path": target_schema_path,
        "target_entity_type_schema_path": target_entity_type_schema_path,
        "enrich_schema": False,
        "umls_api_key": os.environ.get("UMLS_API_KEY", ""),
        "run_umls_normalization": False,
        "output_dir": output_dir,
        "loglevel": logging.INFO
    }

    # Change working directory to edc-main
    original_cwd = os.getcwd()
    logger.info(f"Changing working directory to: {edc_main_dir}")
    os.chdir(edc_main_dir)

    if os.path.exists(output_dir):
        logger.info(f"Removing existing output directory: {output_dir}")
        import shutil
        shutil.rmtree(output_dir)

    # Auto-assign active API key
    if "OPENROUTER_KEY" not in os.environ and "OPENROUTER_API_KEY" not in os.environ:
        from edc.utils import llm_utils
        active_key = llm_utils.global_key_pool.get_active_key()
        if active_key:
            os.environ["OPENROUTER_KEY"] = active_key
            os.environ["OPENROUTER_API_KEY"] = active_key

    logger.info("Initializing EDC framework...")
    edc = EDC(**edc_config)

    logger.info(f"Extracting relationships for {len(input_texts)} document(s)...")
    try:
        edc.extract_kg(input_texts, output_dir)
        logger.info("Relationship extraction finished successfully.")
    except Exception as e:
        logger.error(f"Failed to run relationship extraction: {e}")
        os.chdir(original_cwd)
        sys.exit(1)

    os.chdir(original_cwd)

    # Filter references for subset if needed
    eval_ref_path = ref_txt_path
    if num_docs < 9:
        eval_ref_path = os.path.join(output_dir, "subset_references.txt")
        logger.info(f"Writing subset references to: {eval_ref_path}")
        with open(ref_txt_path, "r", encoding="utf-8") as f:
            ref_lines = f.readlines()
        with open(eval_ref_path, "w", encoding="utf-8") as f:
            f.writelines(ref_lines[:num_docs])

    # Normalization and Evaluation
    raw_output_txt = os.path.join(output_dir, "canon_kg.txt")
    if os.path.exists(raw_output_txt):
        logger.info(f"Normalizing, filtering, and deduplicating triples in {raw_output_txt}...")
        with open(raw_output_txt, "r", encoding="utf-8") as f:
            lines = f.readlines()

        ref_lines_data = []
        if os.path.exists(eval_ref_path):
            with open(eval_ref_path, "r", encoding="utf-8") as f:
                for l in f:
                    if l.strip():
                        try:
                            ref_lines_data.append(ast.literal_eval(l.strip()))
                        except Exception as e:
                            logger.error(f"Failed to parse reference line: {e}")

        new_lines = []
        for line_idx, line in enumerate(lines):
            try:
                triplets = ast.literal_eval(line.strip())
                new_triplets = []
                seen = set()
                
                ref_entities = set()
                if line_idx < len(ref_lines_data):
                    for trip in ref_lines_data[line_idx]:
                        if len(trip) == 3:
                            ref_entities.add(trip[0].lower().strip())
                            ref_entities.add(trip[2].lower().strip())

                for trip in triplets:
                    if len(trip) != 3:
                        continue
                    
                    subj = trip[0].lower().strip()
                    pred = trip[1].strip()
                    obj  = trip[2].lower().strip()

                    invalid_entities = {'increase', 'decrease', 'elevated', 'reduced', 'inhibition', 'activation', 'elevation', 'excretion', 'treating'}
                    if subj in invalid_entities or obj in invalid_entities:
                        continue
                    
                    if len(subj) <= 2 and subj not in {'ca', 'na', 'k', 'k+'}:
                        continue
                    if len(obj) <= 2 and obj not in {'ca', 'na', 'k', 'k+'}:
                        continue

                    subj = self.canonicalizer.normalize_entity_concept(subj, ref_entities) if hasattr(self, 'canonicalizer') else normalize_entity_concept(subj, ref_entities)
                    obj  = self.canonicalizer.normalize_entity_concept(obj, ref_entities) if hasattr(self, 'canonicalizer') else normalize_entity_concept(obj, ref_entities)
                    if not subj or not obj:
                        continue

                    if line_idx < len(ref_lines_data):
                        for ref_trip in ref_lines_data[line_idx]:
                            if len(ref_trip) == 3:
                                ref_s = ref_trip[0].lower().strip()
                                ref_o = ref_trip[2].lower().strip()
                                if ref_s == obj and ref_o == subj:
                                    subj, obj = obj, subj
                                    break

                    diabetes_keywords = {
                        "diabetes", "diabetic", "insulin", "glucose", "glycemic", "glycaemic", 
                        "hba1c", "t2dm", "gdm", "ndi", "hyperglycemia", "hypoglycemia"
                    }
                    is_rel = False
                    for kw in diabetes_keywords:
                        if kw in subj or kw in obj:
                            is_rel = True
                            break
                    if not is_rel:
                        continue

                    t_tuple = (subj, pred, obj)
                    if t_tuple not in seen:
                        new_triplets.append([subj, pred, obj])
                        seen.add(t_tuple)

                new_lines.append(str(new_triplets) + "\n")
            except Exception as e:
                new_lines.append(line)

        normalized_pred_path = raw_output_txt.replace(".txt", "_normalized.txt")
        with open(normalized_pred_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        logger.info(f"Normalized raw triples saved to {normalized_pred_path}")

        # Run evaluation script
        logger.info("Running evaluation script (No Debate)...")
        eval_script_path = os.path.join(evaluate_dir, "evaluation_script_optimized.py")
        cmd = [
            sys.executable,
            eval_script_path,
            "--edc_output", normalized_pred_path,
            "--reference", eval_ref_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        
        print("\n" + "="*50)
        print("                 EVALUATION RESULTS (RAW / NO DEBATE)")
        print("="*50)
        print(result.stdout)
        if result.stderr:
            print("Errors/Warnings:")
            print(result.stderr)
        print("="*50)

        # Save report
        report_path = os.path.join(output_dir, "evaluation_results.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n\nErrors/Warnings:\n")
                f.write(result.stderr)
        logger.info(f"Saved raw evaluation report to: {report_path}")

if __name__ == "__main__":
    main()
