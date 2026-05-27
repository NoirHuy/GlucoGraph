"""
property_packer.py — post_processing module to clean, pack clinical quantitative values,
                      and enrich nodes with ontology metadata (Hybrid Approach).
"""

import re
import os
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Pattern to capture comparison signs (<, >, <=, >=, =) and numbers with optional units
_PAT_COMPARATOR = re.compile(
    r"([<>]=?|=)\s*(\d+(?:\.\d+)?)\s*(?:mg/dL|mg|ml|units?|u|%)?",
    re.IGNORECASE
)

# Pattern to capture percentage adjustments (e.g., "increase by 20%", "reduce by 10%")
_PAT_PERCENT_ADJUST = re.compile(
    r"(increase|decrease|reduce|raise|up|down)\s+(?:dose\s+)?(?:by\s+)?(\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE
)

# Local dictionary mapping 20+ common clinical concepts in diabetes/medications to their ontology IDs
LOCAL_ONTOLOGY_DB: Dict[str, Dict[str, str]] = {
    "insulin": {
        "umls_cui": "C0021853",
        "umls_canonical": "Insulin",
        "umls_semantic_type": "Pharmacologic Substance (T121)",
        "rxnorm_id": "RXN8609",
        "description": "A peptide hormone produced by beta cells of the pancreatic islets; it regulates carbohydrate and fat metabolism."
    },
    "insulin replacement": {
        "umls_cui": "C0021853",
        "umls_canonical": "Insulin",
        "umls_semantic_type": "Therapeutic or Preventive Procedure (T061)",
        "rxnorm_id": "RXN8609",
        "description": "Exogenous administration of insulin to replace or supplement endogenous production in diabetes."
    },
    "basal insulin": {
        "umls_cui": "C1516104",
        "umls_canonical": "Basal Insulin",
        "umls_semantic_type": "Pharmacologic Substance (T121)",
        "rxnorm_id": "RXN1605101",
        "description": "Long-acting or intermediate-acting insulin that provides a steady plateau of insulin coverage throughout the day and night."
    },
    "regular insulin": {
        "umls_cui": "C0043135",
        "umls_canonical": "Regular Insulin",
        "umls_semantic_type": "Pharmacologic Substance (T121)",
        "rxnorm_id": "RXN11202",
        "description": "Short-acting soluble insulin that is structurally identical to native human insulin."
    },
    "insulin lispro": {
        "umls_cui": "C0282638",
        "umls_canonical": "Insulin Lispro",
        "umls_semantic_type": "Pharmacologic Substance (T121)",
        "rxnorm_id": "RXN85698",
        "description": "A rapid-acting human insulin analog used to reduce postprandial blood glucose spikes."
    },
    "insulin aspart": {
        "umls_cui": "C0908861",
        "umls_canonical": "Insulin Aspart",
        "umls_semantic_type": "Pharmacologic Substance (T121)",
        "rxnorm_id": "RXN261551",
        "description": "A rapid-acting human insulin analog created by replacing proline with aspartic acid."
    },
    "insulin glargine": {
        "umls_cui": "C0909569",
        "umls_canonical": "Insulin Glargine",
        "umls_semantic_type": "Pharmacologic Substance (T121)",
        "rxnorm_id": "RXN274786",
        "description": "A long-acting human insulin analog given once daily as a basal insulin."
    },
    "insulin detemir": {
        "umls_cui": "C1123497",
        "umls_canonical": "Insulin Detemir",
        "umls_semantic_type": "Pharmacologic Substance (T121)",
        "rxnorm_id": "RXN358265",
        "description": "A long-acting basal insulin analog with a fatty acid side chain."
    },
    "insulin isophane": {
        "umls_cui": "C0021865",
        "umls_canonical": "Insulin Isophane",
        "umls_semantic_type": "Pharmacologic Substance (T121)",
        "rxnorm_id": "RXN11207",
        "description": "Intermediate-acting Neutral Protamine Hagedorn (NPH) insulin suspension."
    },
    "metformin": {
        "umls_cui": "C0025598",
        "umls_canonical": "Metformin",
        "umls_semantic_type": "Pharmacologic Substance (T121)",
        "rxnorm_id": "RXN6809",
        "description": "First-line oral biguanide antihyperglycemic medication that decreases hepatic glucose production."
    },
    "pioglitazone": {
        "umls_cui": "C0699298",
        "umls_canonical": "Pioglitazone",
        "umls_semantic_type": "Pharmacologic Substance (T121)",
        "rxnorm_id": "RXN220067",
        "description": "A thiazolidinedione oral antihyperglycemic agent that increases insulin sensitivity via PPAR-gamma."
    },
    "type 1 diabetes": {
        "umls_cui": "C0011854",
        "umls_canonical": "Type 1 Diabetes Mellitus",
        "umls_semantic_type": "Disease or Syndrome (T047)",
        "icd10_code": "E10",
        "description": "An autoimmune disorder characterized by destruction of insulin-producing pancreatic beta-cells."
    },
    "type 1 diabetes mellitus": {
        "umls_cui": "C0011854",
        "umls_canonical": "Type 1 Diabetes Mellitus",
        "umls_semantic_type": "Disease or Syndrome (T047)",
        "icd10_code": "E10",
        "description": "An autoimmune disorder characterized by destruction of insulin-producing pancreatic beta-cells."
    },
    "type 2 diabetes": {
        "umls_cui": "C0011860",
        "umls_canonical": "Type 2 Diabetes Mellitus",
        "umls_semantic_type": "Disease or Syndrome (T047)",
        "icd10_code": "E11",
        "description": "A metabolic disease characterized by chronic high blood sugar, insulin resistance, and relative lack of insulin."
    },
    "type 2 diabetes mellitus": {
        "umls_cui": "C0011860",
        "umls_canonical": "Type 2 Diabetes Mellitus",
        "umls_semantic_type": "Disease or Syndrome (T047)",
        "icd10_code": "E11",
        "description": "A metabolic disease characterized by chronic high blood sugar, insulin resistance, and relative lack of insulin."
    },
    "obesity": {
        "umls_cui": "C0028754",
        "umls_canonical": "Obesity",
        "umls_semantic_type": "Disease or Syndrome (T047)",
        "icd10_code": "E66",
        "description": "A chronic medical condition characterized by excess body fat accumulation that impairs health."
    },
    "hyperglycemia": {
        "umls_cui": "C0020456",
        "umls_canonical": "Hyperglycemia",
        "umls_semantic_type": "Finding (T033)",
        "icd10_code": "R73.9",
        "description": "An abnormally high concentration of glucose in the circulating blood."
    },
    "hypoglycemia": {
        "umls_cui": "C0020615",
        "umls_canonical": "Hypoglycemia",
        "umls_semantic_type": "Finding (T033)",
        "icd10_code": "E16.2",
        "description": "An abnormally low concentration of glucose in the circulating blood."
    },
    "ketoacidosis": {
        "umls_cui": "C0022638",
        "umls_canonical": "Diabetic Ketoacidosis",
        "umls_semantic_type": "Disease or Syndrome (T047)",
        "icd10_code": "E10.1",
        "description": "A life-threatening complication of diabetes characterized by high ketonemia and metabolic acidosis."
    },
    "hba1c": {
        "umls_cui": "C0523829",
        "umls_canonical": "Hemoglobin A, Glycated",
        "umls_semantic_type": "Clinical Attribute (T201)",
        "description": "Glycated hemoglobin level, representing a 3-month average of plasma glucose concentrations."
    },
    "fasting blood glucose": {
        "umls_cui": "C0202054",
        "umls_canonical": "Fasting Blood Glucose",
        "umls_semantic_type": "Laboratory Procedure (T059)",
        "description": "Measurement of blood glucose concentration after a period of fasting for at least 8 hours."
    },
    "pancreatic islet cells": {
        "umls_cui": "C0022131",
        "umls_canonical": "Islets of Langerhans",
        "umls_semantic_type": "Cell (T025)",
        "description": "Regions of the pancreas that contain endocrine cells, including beta-cells."
    },
    "pancreatic beta-cells": {
        "umls_cui": "C0229983",
        "umls_canonical": "Insulin-Secreting Cells",
        "umls_semantic_type": "Cell (T025)",
        "description": "Pancreatic endocrine cells that synthesize and secrete insulin."
    },
    "heart failure": {
        "umls_cui": "C0018801",
        "umls_canonical": "Heart Failure",
        "umls_semantic_type": "Disease or Syndrome (T047)",
        "icd10_code": "I50",
        "description": "A chronic condition where the heart muscle is unable to pump blood efficiently to meet physiological needs."
    }
}


def normalize_entity_type(t: str) -> str:
    """Normalize entity type spelling and casing to match standard target schema groups."""
    if not t:
        return "Unknown"
    norm = t.strip().lower().replace("_", " ").replace("-", " ")
    
    mapping = {
        "disease": "Disease",
        "drug": "Drug",
        "symptom": "Symptom",
        "clinical metric": "Clinical Metric",
        "clinicalmetric": "Clinical Metric",
        "anatomical site": "Anatomical Site",
        "anatomicalsite": "Anatomical Site",
        "treatment procedure": "Treatment Procedure",
        "treatmentprocedure": "Treatment Procedure",
        "dosage value": "Dosage Value",
        "dosagevalue": "Dosage Value"
    }
    return mapping.get(norm, t.strip())


def extract_clean_value(raw_val: str) -> Optional[str]:
    """Clean clinical value by removing extra units/spaces and returning normalized form.
    
    Examples:
        - "< 70 mg/dL" -> "<70"
        - "> 180 mg/dL" -> ">180"
        - "increase by 20%" -> "+20%"
        - "reduce dose by 10%" -> "-10%"
        - "10 units" -> "10u"
    """
    if not raw_val:
        return None
        
    val_strip = raw_val.strip()
    
    # 1. Match comparators like < 70, >= 8.0
    comp_match = _PAT_COMPARATOR.search(val_strip)
    if comp_match:
        operator = comp_match.group(1)
        number = comp_match.group(2)
        if number.endswith(".0"):
            number = number[:-2]
        return f"{operator}{number}"
        
    # 2. Match percentage adjustments
    percent_match = _PAT_PERCENT_ADJUST.search(val_strip)
    if percent_match:
        direction = percent_match.group(1).lower()
        amount = percent_match.group(2)
        if amount.endswith(".0"):
            amount = amount[:-2]
            
        sign = "+" if direction in ["increase", "raise", "up"] else "-"
        return f"{sign}{amount}%"
        
    # 3. Clean up generic dosage numbers like "10 units", "5 mg"
    generic_dose = re.search(r"^(\d+(?:\.\d+)?)\s*(units?|u|mg|ml)$", val_strip, re.IGNORECASE)
    if generic_dose:
        num = generic_dose.group(1)
        raw_unit = generic_dose.group(2).lower()
        if num.endswith(".0"):
            num = num[:-2]
            
        if "unit" in raw_unit or raw_unit == "u":
            unit = "u"
        elif raw_unit == "ml":
            unit = "ml"
        else:
            unit = "mg"
        return f"{num}{unit}"
        
    # Fallback to trimmed raw string if it is short, otherwise return None
    if len(val_strip) < 25:
        return val_strip
    return None


def is_value_like(relation: str, obj: str) -> bool:
    """Check if a triple object represents a clinical quantitative threshold/value."""
    rel_norm = relation.lower().replace(" ", "_").strip()
    
    # Relations that inherently point to dosage values/thresholds
    if rel_norm in ["has_clinical_threshold", "has_dose_adjustment"]:
        return True
        
    # If the object starts with comparator signs or contains numbers and units
    obj_clean = obj.strip()
    if any(obj_clean.startswith(c) for c in ["<", ">", "=", "<=", ">="]):
        return True
        
    if re.search(r"\d+\s*(?:mg/dL|%|units?|u|mg|ml)", obj_clean, re.IGNORECASE):
        return True
        
    return False


def enrich_ontology_metadata(
    node_id: str,
    node_labels: List[str],
    normalizer: Optional[Any] = None
) -> Dict[str, str]:
    """Enrich node properties with UMLS, RxNorm, and ICD-10 metadata using a Hybrid Approach."""
    properties = {}
    term_key = node_id.lower().strip()
    
    # 1. Local Database Lookup (Instant Offline Mapping)
    if term_key in LOCAL_ONTOLOGY_DB:
        entry = LOCAL_ONTOLOGY_DB[term_key]
        properties.update(entry)
    else:
        # 2. Optional Online UMLS UTS API Querying
        if normalizer:
            try:
                res = normalizer.query_term(node_id)
                if res and res.get("cui") != "NONE":
                    properties["umls_cui"] = res["cui"]
                    properties["umls_canonical"] = res["canonical"]
                    properties["umls_semantic_type"] = res["semantic_type"]
                    properties["description"] = f"UMLS Standard Term: {res['canonical']}"
            except Exception as e:
                logger.warning(f"Failed to query online UMLS API for node '{node_id}': {e}")
                
    # 3. Handle default values for critical keys if not mapped
    if "umls_cui" not in properties:
        properties["umls_cui"] = "NONE"
    if "umls_canonical" not in properties:
        properties["umls_canonical"] = node_id  # Hybrid Approach: Fallback to original term name!
    if "umls_semantic_type" not in properties:
        properties["umls_semantic_type"] = "Unknown"
        
    # Standardize label specific keys
    if "Drug" in node_labels and "rxnorm_id" not in properties:
        properties["rxnorm_id"] = "NONE"
    if "Disease" in node_labels and "icd10_code" not in properties:
        properties["icd10_code"] = "NONE"
        
    return properties


def pack_properties(records: List[dict], umls_api_key: Optional[str] = None) -> Dict[str, Any]:
    """Iterate through OIE records, resolve, and pack clinical values and ontology metadata.
    
    Generates a structured graph dictionary containing clean Nodes and Relationships with properties.
    """
    nodes: Dict[str, dict] = {}
    relationships: List[dict] = []
    
    # Optional UMLS API initialization
    normalizer = None
    if umls_api_key:
        try:
            from edc.post_processing.umls_normalizer import UMLSNormalizer
            normalizer = UMLSNormalizer(api_key=umls_api_key)
            logger.info("Online UMLS UTS API Normalizer initialized for property packing.")
        except Exception as e:
            logger.warning(f"Failed to initialize UMLSNormalizer: {e}")
            
    for idx, record in enumerate(records):
        triplets = record.get("schema_canonicalizaiton", [])
        if not triplets:
            continue
            
        # Build local entity name -> type mapping from schema_definition._entries
        entity_types: Dict[str, str] = {}
        sd_entries = record.get("schema_definition", {}).get("_entries", [])
        for entry in sd_entries:
            if isinstance(entry, dict):
                s = entry.get("subject", "")
                o = entry.get("object", "")
                s_type = entry.get("subject_type_canon") or entry.get("subject_type")
                o_type = entry.get("object_type_canon") or entry.get("object_type")
                if s and s_type:
                    entity_types[s] = normalize_entity_type(s_type)
                if o and o_type:
                    entity_types[o] = normalize_entity_type(o_type)
                    
        # Maps to store values extracted during this document record
        thresholds_map: Dict[str, str] = {}   # ClinicalMetric -> cleaned_threshold
        adjustments_map: Dict[str, str] = {}  # Drug -> cleaned_adjustment
        
        # Value-based triples to be processed and packed
        value_triples: List[Tuple[str, str, str]] = []
        # Concept-to-concept semantic triples
        concept_triples: List[Tuple[str, str, str]] = []
        
        # Step 1: Classify triples
        for t in triplets:
            if not t or len(t) < 3:
                continue
            s, r, o = t[0], t[1], t[2]
            
            if is_value_like(r, o):
                value_triples.append((s, r, o))
                cleaned = extract_clean_value(o)
                if cleaned:
                    r_norm = r.lower().replace(" ", "_").strip()
                    if r_norm in ["has_clinical_threshold", "has_titration_rule"]:
                        thresholds_map[s] = cleaned
                    elif r_norm in ["has_dose_adjustment"]:
                        adjustments_map[s] = cleaned
            else:
                # Add concept-to-concept semantic triples directly
                concept_triples.append((s, r, o))
                
        # Step 2: Ensure all concepts exist as nodes and assign canonical entity type labels
        for s, r, o in concept_triples:
            for entity in [s, o]:
                if entity not in nodes:
                    e_type = entity_types.get(entity, "Unknown")
                    labels = ["Concept"]
                    if e_type != "Unknown":
                        labels.append(e_type)
                    
                    # Enrich node with UMLS/RxNorm/ICD-10 clinical metadata
                    props = enrich_ontology_metadata(entity, labels, normalizer=normalizer)
                    nodes[entity] = {"id": entity, "labels": labels, "properties": props}
                    
        # Step 3: Process concept-to-concept relationships and pack merged properties
        processed_relations = set()
        
        for s, r, o in concept_triples:
            r_norm = r.lower().replace(" ", "_").strip()
            
            # Case A: Drug titration rule pointing to a Clinical Metric
            if r_norm == "has_titration_rule":
                props = {}
                
                # Check if we have threshold packed for the clinical metric
                if o in thresholds_map:
                    props["threshold"] = thresholds_map[o]
                # Check if we have adjustment packed for the drug
                if s in adjustments_map:
                    props["adjustment"] = adjustments_map[s]
                    
                relationships.append({
                    "start": s,
                    "end": o,
                    "type": "has_titration_rule",
                    "properties": props
                })
                processed_relations.add((s, r, o))
                
        # Step 4: Add all remaining non-titration concept-to-concept relationships
        for s, r, o in concept_triples:
            if (s, r, o) in processed_relations:
                continue
            relationships.append({
                "start": s,
                "end": o,
                "type": r.lower().replace(" ", "_").strip(),
                "properties": {}
            })
            
        # Step 5: Pack remaining standalone values directly onto concept nodes
        for s, r, o in value_triples:
            cleaned = extract_clean_value(o)
            if not cleaned:
                continue
                
            r_norm = r.lower().replace(" ", "_").strip()
            
            is_packed_on_edge = False
            for rel in relationships:
                if rel["type"] == "has_titration_rule" and (rel["start"] == s or rel["end"] == s):
                    is_packed_on_edge = True
                    break
                    
            if not is_packed_on_edge:
                # Pack directly onto the concept node
                if s not in nodes:
                    s_type = entity_types.get(s, "Unknown")
                    labels = ["Concept"]
                    if s_type != "Unknown":
                        labels.append(s_type)
                    
                    props = enrich_ontology_metadata(s, labels, normalizer=normalizer)
                    nodes[s] = {"id": s, "labels": labels, "properties": props}
                
                # Determine property key
                prop_key = "target_threshold" if r_norm in ["has_clinical_threshold", "has_titration_rule"] else "dosage_value"
                nodes[s]["properties"][prop_key] = cleaned
                
    # Return formatted Neo4j structure
    return {
        "nodes": list(nodes.values()),
        "relationships": relationships
    }
