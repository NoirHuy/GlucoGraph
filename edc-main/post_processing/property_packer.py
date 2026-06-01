"""
property_packer.py — post_processing module to clean, pack clinical quantitative values,
                      and enrich nodes with ontology metadata (Hybrid Approach).
"""

import re
import os
import logging
from typing import Any, Dict, List, Optional, Tuple

# Try loading .env variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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
LOCAL_ONTOLOGY_DB: Dict[str, Dict[str, str]] = {}


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
    """Enrich node properties with UMLS, RxNorm, and ICD-10 metadata by querying the online UMLS UTS REST API.
    
    Dynamically maps raw entities to their standard UMLS CUI codes and semantic types.
    """
    properties = {}
    
    # 1. Query the online UMLS REST API directly
    if normalizer and normalizer.api_key:
        try:
            res = normalizer.query_term(node_id)
            if res and res.get("cui") != "NONE":
                properties["umls_cui"] = res["cui"]
                properties["umls_canonical"] = res["canonical"]
                properties["umls_semantic_type"] = res["semantic_type"]
                properties["icd10_code"] = res.get("icd10_code", "NONE")
                properties["rxnorm_id"] = res.get("rxnorm_id", "NONE")
                
                # Set description from definition if non-empty, else fallback
                definition = res.get("definition", "").strip()
                if definition:
                    properties["description"] = definition
                else:
                    properties["description"] = f"UMLS Standard Term: {res['canonical']}"
        except Exception as e:
            logger.warning(f"Failed to query online UMLS API for node '{node_id}': {e}")
                
    # 2. Handle default values for critical keys if not mapped or if offline/unmapped
    if "umls_cui" not in properties:
        properties["umls_cui"] = "NONE"
    if "umls_canonical" not in properties:
        properties["umls_canonical"] = node_id  # Fallback to the extracted entity name!
    if "umls_semantic_type" not in properties:
        properties["umls_semantic_type"] = "Unknown"
    if "description" not in properties:
        properties["description"] = ""
        
    # Standardize label-specific keys
    if "Drug" in node_labels:
        properties["rxnorm_id"] = properties.get("rxnorm_id", "NONE")
    if "Disease" in node_labels:
        properties["icd10_code"] = properties.get("icd10_code", "NONE")
        
    return properties


def pack_properties(
    records: List[dict],
    umls_api_key: Optional[str] = None,
    normalizer: Optional[Any] = None
) -> Dict[str, Any]:
    """Iterate through OIE records, resolve, and pack clinical values and ontology metadata.
    
    Generates a structured graph dictionary containing clean Nodes and Relationships with properties.
    """
    nodes: Dict[str, dict] = {}
    relationships: List[dict] = []
    
    # Optional UMLS API initialization if not already provided
    if normalizer is None:
        api_key_to_use = umls_api_key or os.environ.get("UMLS_API_KEY", "")
        if api_key_to_use:
            try:
                from edc.post_processing.umls_normalizer import UMLSNormalizer
                normalizer = UMLSNormalizer(api_key=api_key_to_use)
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
                    
    # === Integrate Entity Deduplication / Resolution ===
    deduped_nodes: Dict[str, dict] = {}
    node_id_mapping: Dict[str, str] = {}  # Old Raw ID -> New Canonical CUI/Raw ID

    # 1. Build mapping from raw node ID to its new canonical ID (CUI or case-insensitive raw fallback)
    for raw_id, node in nodes.items():
        cui = node["properties"].get("umls_cui", "NONE")
        if cui != "NONE":
            node_id_mapping[raw_id] = cui
        else:
            # Case-insensitive normalization for none-CUI nodes
            norm_name = raw_id.strip()
            # Check if we already mapped another casing of this raw_id to a canonical ID
            found_id = None
            for k, v in node_id_mapping.items():
                if k.strip().lower() == norm_name.lower():
                    found_id = v
                    break
            if found_id:
                node_id_mapping[raw_id] = found_id
            else:
                node_id_mapping[raw_id] = raw_id

    # 2. Group nodes by their new canonical ID
    canon_groups: Dict[str, List[dict]] = {}
    for raw_id, node in nodes.items():
        canon_id = node_id_mapping[raw_id]
        canon_groups.setdefault(canon_id, []).append(node)

    # 3. Merge nodes in each group
    for canon_id, group in canon_groups.items():
        # Find best node to use as base (prefer non-empty properties/valid UMLS CUI if available)
        base_node = group[0]
        for node in group:
            if node["properties"].get("umls_cui", "NONE") != "NONE":
                base_node = node
                break

        merged_labels = set()
        merged_aliases = set()
        merged_props = {}

        # Collect all labels and aliases from the group
        for node in group:
            merged_labels.update(node.get("labels", []))
            merged_aliases.add(node["id"].strip())
            if "aliases" in node["properties"]:
                merged_aliases.update(node["properties"]["aliases"])

            # Merge properties
            for k, v in node.get("properties", {}).items():
                if v and v != "NONE" and v != "Unknown" and v != "":
                    if k not in merged_props or merged_props[k] in ["NONE", "Unknown", ""]:
                        merged_props[k] = v

        # Set standardized canonical fields
        # If canon_id is a CUI, prioritize standard UMLS fields
        cui_val = merged_props.get("umls_cui", "NONE")
        if cui_val != "NONE":
            merged_props["umls_cui"] = cui_val
            merged_props["umls_canonical"] = merged_props.get("umls_canonical", canon_id)
        else:
            merged_props["umls_cui"] = "NONE"
            merged_props["umls_canonical"] = merged_props.get("umls_canonical", canon_id)

        # Standardize empty values
        merged_props["umls_semantic_type"] = merged_props.get("umls_semantic_type", "Unknown")
        merged_props["description"] = merged_props.get("description", "")

        # Target thresholds and dosage values
        for k in ["target_threshold", "dosage_value", "icd10_code", "rxnorm_id"]:
            # Ensure they are set if present in any node in the group
            for node in group:
                if k in node["properties"] and node["properties"][k] not in ["NONE", "", None]:
                    merged_props[k] = node["properties"][k]
                    break
            # Default fallback for label-specific properties
            if k in ["icd10_code", "rxnorm_id"] and k not in merged_props:
                if (k == "icd10_code" and "Disease" in merged_labels) or (k == "rxnorm_id" and "Drug" in merged_labels):
                    merged_props[k] = "NONE"

        # Remove the CUI or standard raw name itself from the aliases to keep it clean (or keep it if it differs)
        canonical_name = merged_props["umls_canonical"]
        merged_aliases.discard(canon_id)
        merged_aliases.discard(canonical_name)
        
        # Populate aliases array property (sorted and unique)
        merged_props["aliases"] = sorted(list(merged_aliases))

        deduped_nodes[canon_id] = {
            "id": canon_id,
            "labels": sorted(list(merged_labels)),
            "properties": merged_props
        }

    # 4. Remap and deduplicate relationships
    deduped_relationships: List[dict] = []
    seen_relations = set()

    for rel in relationships:
        old_start = rel["start"]
        old_end = rel["end"]
        
        new_start = node_id_mapping.get(old_start, old_start)
        new_end = node_id_mapping.get(old_end, old_end)
        
        # Avoid self-loops from deduplication merging
        if new_start == new_end:
            continue
            
        rel_type = rel["type"]
        rel_key = (new_start, rel_type, new_end)
        
        if rel_key not in seen_relations:
            seen_relations.add(rel_key)
            deduped_relationships.append({
                "start": new_start,
                "end": new_end,
                "type": rel_type,
                "properties": rel.get("properties", {})
            })

    # Return formatted Neo4j structure with deduped nodes and edges
    return {
        "nodes": list(deduped_nodes.values()),
        "relationships": deduped_relationships
    }
