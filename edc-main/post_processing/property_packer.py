"""
property_packer.py — post_processing module to clean, pack clinical quantitative values,
                      and enrich nodes with ontology metadata (Hybrid Approach).

Improvements:
- B5: Robust import path with try/except fallback for UMLSNormalizer
- B2: Added LOCAL_MEDICAL_ABBREVIATIONS (~30 clinical aliases)
- B2: Added normalize_entity_for_dedup() with 3-layer normalization
- B2: Refactored deduplication block to use normalize_entity_for_dedup()
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

# ─────────────────────────────────────────────────────────────────────────────
# Regex patterns for clinical value extraction
# ─────────────────────────────────────────────────────────────────────────────

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

# ─────────────────────────────────────────────────────────────────────────────
# B2 — Medical Abbreviation Expansion Table
# Maps common clinical abbreviations / aliases → canonical lowercase form.
# Used in normalize_entity_for_dedup() to collapse variants before comparison.
# ─────────────────────────────────────────────────────────────────────────────
LOCAL_MEDICAL_ABBREVIATIONS: Dict[str, str] = {
    # Diabetes diseases
    "t2dm": "type 2 diabetes mellitus",
    "t1dm": "type 1 diabetes mellitus",
    "dm": "diabetes mellitus",
    "dm2": "type 2 diabetes mellitus",
    "dm1": "type 1 diabetes mellitus",
    "niddm": "type 2 diabetes mellitus",
    "iddm": "type 1 diabetes mellitus",
    "dka": "diabetic ketoacidosis",
    "hhs": "hyperosmolar hyperglycemic state",
    # Biomarkers & labs
    "hba1c": "hemoglobin a1c",
    "a1c": "hemoglobin a1c",
    "fbg": "fasting blood glucose",
    "fpg": "fasting plasma glucose",
    "bg": "blood glucose",
    "ppg": "postprandial glucose",
    "ogtt": "oral glucose tolerance test",
    "ldl": "ldl cholesterol",
    "hdl": "hdl cholesterol",
    "tg": "triglycerides",
    "egfr": "estimated glomerular filtration rate",
    "gfr": "glomerular filtration rate",
    "bmi": "body mass index",
    "sbp": "systolic blood pressure",
    "dbp": "diastolic blood pressure",
    "bp": "blood pressure",
    # Drugs
    "metformin hcl": "metformin",
    "glp-1": "glucagon-like peptide-1",
    "glp1": "glucagon-like peptide-1",
    "dpp-4": "dipeptidyl peptidase-4",
    "dpp4": "dipeptidyl peptidase-4",
    "sglt-2": "sodium-glucose cotransporter-2",
    "sglt2": "sodium-glucose cotransporter-2",
    "ace inhibitor": "angiotensin converting enzyme inhibitor",
    "ace-i": "angiotensin converting enzyme inhibitor",
    "arb": "angiotensin receptor blocker",
    # Anatomy
    "cns": "central nervous system",
    "cvd": "cardiovascular disease",
    "ckd": "chronic kidney disease",
    "esrd": "end stage renal disease",
    # Procedures
    "cabg": "coronary artery bypass grafting",
    "pci": "percutaneous coronary intervention",
}

# ─────────────────────────────────────────────────────────────────────────────
# Medical stopwords — removed before canonical comparison to reduce false negatives
# ─────────────────────────────────────────────────────────────────────────────
_MEDICAL_STOPWORDS = frozenset({
    "the", "a", "an", "of", "with", "in", "and", "or", "to", "for",
    "mellitus", "syndrome", "disease", "disorder", "condition",
    "associated", "related", "induced", "dependent", "independent",
})


def normalize_entity_for_dedup(term: str) -> str:
    """Normalize a clinical entity name for deduplication comparison.

    Applies 4 layers of normalization:
      Layer 0 — OR-pattern collapsing: 'rapid- or short-acting' → 'rapid-acting'
      Layer 1 — Abbreviation expansion: e.g. 'T2DM' → 'type 2 diabetes mellitus'
      Layer 2 — Canonical form: lowercase, remove punctuation/hyphens, remove medical stopwords
      Layer 3 — Stemming: strip common English/medical suffixes (-s, -ic, -al, -tion, -ity)

    Returns a normalized string for equality comparison (NOT for display).
    """
    if not term:
        return ""

    # Strip leading/trailing whitespace, collapse internal whitespace
    clean = re.sub(r"\s+", " ", term.strip()).lower()

    # Layer 0: Collapse 'X- or Y-adjective' → 'X-adjective'
    # e.g. 'rapid- or short-acting insulin' → 'rapid-acting insulin'
    # e.g. 'short- or long-acting' → 'short-acting'
    clean = re.sub(r'-(\s+or\s+\S+-)', '-', clean)

    # Remove common punctuation that shouldn't affect identity
    clean = re.sub(r"[,;:()\[\]\"']", " ", clean)
    # Normalize hyphens: replace hyphens between words with space
    # e.g. 'rapid-acting' → 'rapid acting', 'long-term' → 'long term'
    clean = re.sub(r"-", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()

    # Layer 1: Abbreviation expansion
    # Check the whole term first (handles 'T2DM', 'HbA1c')
    if clean in LOCAL_MEDICAL_ABBREVIATIONS:
        clean = LOCAL_MEDICAL_ABBREVIATIONS[clean]

    # Also expand tokens inside multi-word terms
    tokens = clean.split()
    expanded_tokens = [LOCAL_MEDICAL_ABBREVIATIONS.get(t, t) for t in tokens]
    clean = " ".join(expanded_tokens)

    # Layer 2: Remove medical stopwords
    words = clean.split()
    words = [w for w in words if w not in _MEDICAL_STOPWORDS]
    clean = " ".join(words)

    # Layer 3: Light stemming — strip common suffixes
    stemmed = []
    for w in clean.split():
        # Order matters: longer suffixes before shorter
        for suffix in ("tion", "ity", "ous", "ical", "ic", "al", "ing", "s"):
            if w.endswith(suffix) and len(w) - len(suffix) >= 4:
                w = w[: -len(suffix)]
                break
        stemmed.append(w)

    return " ".join(sorted(stemmed))  # sort words for order-invariant comparison


# ─────────────────────────────────────────────────────────────────────────────
# B5 — Robust UMLSNormalizer import with fallback paths
# ─────────────────────────────────────────────────────────────────────────────
try:
    from post_processing.umls_normalizer import UMLSNormalizer
    logger.debug("[PropertyPacker] Imported UMLSNormalizer from post_processing")
except ImportError:
    try:
        import sys
        _pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        if _pkg_root not in sys.path:
            sys.path.insert(0, _pkg_root)
        from post_processing.umls_normalizer import UMLSNormalizer
        logger.debug("[PropertyPacker] Imported UMLSNormalizer via sys.path injection")
    except ImportError:
        UMLSNormalizer = None
        logger.warning(
            "[PropertyPacker] UMLSNormalizer could not be imported. "
            "UMLS enrichment will be skipped. Check that post_processing/umls_normalizer.py exists."
        )


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
            res = normalizer.query_term(node_id, node_labels=node_labels)
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
        properties["umls_canonical"] = node_id  # Fallback to the extracted entity name
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
    umls_cache_path: Optional[str] = None,
    normalizer: Optional[Any] = None
) -> Dict[str, Any]:
    """Iterate through OIE records, resolve, and pack clinical values and ontology metadata.

    Generates a structured graph dictionary containing clean Nodes and Relationships with properties.

    Args:
        records: List of OIE records (from result_at_each_stage_debated.json).
        umls_api_key: Optional UMLS API key. Falls back to UMLS_API_KEY env var.
        umls_cache_path: Optional path for persistent UMLS query cache.
        normalizer: Pre-initialized UMLSNormalizer instance (takes precedence).
    """
    nodes: Dict[str, dict] = {}
    relationships: List[dict] = []

    # Automatically extract document-level clinical context keywords
    context_words = set()
    try:
        from collections import Counter
        all_words = []
        for record in records:
            for t in record.get("schema_canonicalizaiton", []):
                if t and len(t) >= 3:
                    all_words.extend(re.findall(r'[a-zA-Z]+', str(t[0]).lower()))
                    all_words.extend(re.findall(r'[a-zA-Z]+', str(t[2]).lower()))
        counter = Counter(all_words)
        stopwords = {'the', 'and', 'a', 'of', 'in', 'to', 'for', 'with', 'on', 'at', 'by', 'an', 'is', 'or', 'that', 'this', 'are', 'was', 'were', 'be', 'been'}
        context_words = {word for word, count in counter.most_common(60) if word not in stopwords and len(word) > 2}
        logger.info(f"[PropertyPacker] Automatically extracted {len(context_words)} dynamic clinical context words from document.")
    except Exception as e:
        logger.warning(f"Failed to dynamically extract document clinical context: {e}")

    # Optional UMLS API initialization if not already provided
    if normalizer is None and UMLSNormalizer is not None:
        api_key_to_use = umls_api_key or os.environ.get("UMLS_API_KEY", "")
        if api_key_to_use:
            try:
                kwargs = {"api_key": api_key_to_use}
                if umls_cache_path:
                    kwargs["cache_path"] = umls_cache_path
                normalizer = UMLSNormalizer(**kwargs)
                logger.info("Online UMLS UTS API Normalizer initialized for property packing.")
            except Exception as e:
                logger.warning(f"Failed to initialize UMLSNormalizer: {e}")

    if normalizer is not None and hasattr(normalizer, "set_context_words"):
        normalizer.set_context_words(context_words)

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

    # ─────────────────────────────────────────────────────────────────────────
    # B2 — Entity Deduplication / Resolution (Enhanced)
    # Strategy:
    #   Priority 1: Nodes with CUI → use CUI as canonical ID (exact, reliable)
    #   Priority 2: Nodes without CUI → use normalize_entity_for_dedup() for
    #               3-layer normalization (abbreviation expansion + stopword
    #               removal + stemming) before comparing
    # ─────────────────────────────────────────────────────────────────────────
    deduped_nodes: Dict[str, dict] = {}
    node_id_mapping: Dict[str, str] = {}  # raw_id -> canonical_id

    # Pass 1: Assign canonical IDs
    # Build a reverse index: dedup_key -> first canonical_id seen for that key
    dedup_key_to_canon: Dict[str, str] = {}

    for raw_id, node in nodes.items():
        cui = node["properties"].get("umls_cui", "NONE")
        if cui != "NONE":
            # CUI-based canonical ID — most reliable
            node_id_mapping[raw_id] = cui
            dedup_key_to_canon[cui] = cui
        else:
            # Compute normalized dedup key for alias-aware comparison
            dedup_key = normalize_entity_for_dedup(raw_id)
            if dedup_key in dedup_key_to_canon:
                # Another node with the same normalized form already registered → merge into it
                node_id_mapping[raw_id] = dedup_key_to_canon[dedup_key]
            else:
                # First occurrence: use the original raw_id as canonical
                node_id_mapping[raw_id] = raw_id
                dedup_key_to_canon[dedup_key] = raw_id

    # Pass 2: Group nodes by their canonical ID
    canon_groups: Dict[str, List[dict]] = {}
    for raw_id, node in nodes.items():
        canon_id = node_id_mapping[raw_id]
        canon_groups.setdefault(canon_id, []).append(node)

    # Pass 3: Merge nodes in each group
    for canon_id, group in canon_groups.items():
        # Find best node to use as base (prefer node with valid UMLS CUI if available)
        base_node = group[0]
        for node in group:
            if node["properties"].get("umls_cui", "NONE") != "NONE":
                base_node = node
                break

        merged_labels: set = set()
        merged_aliases: set = set()
        merged_props: Dict[str, Any] = {}

        # Collect all labels, aliases, and properties from the group
        for node in group:
            merged_labels.update(node.get("labels", []))
            merged_aliases.add(node["id"].strip())
            if "aliases" in node["properties"]:
                existing = node["properties"]["aliases"]
                if isinstance(existing, list):
                    merged_aliases.update(existing)
                elif isinstance(existing, str):
                    merged_aliases.add(existing)

            # Merge properties: prefer first non-empty value
            for k, v in node.get("properties", {}).items():
                if v and v != "NONE" and v != "Unknown" and v != "":
                    if k not in merged_props or merged_props[k] in ["NONE", "Unknown", ""]:
                        merged_props[k] = v

        # Standardize canonical fields
        cui_val = merged_props.get("umls_cui", "NONE")
        if cui_val != "NONE":
            merged_props["umls_cui"] = cui_val
            merged_props["umls_canonical"] = merged_props.get("umls_canonical", canon_id)
        else:
            merged_props["umls_cui"] = "NONE"
            merged_props["umls_canonical"] = merged_props.get("umls_canonical", canon_id)

        merged_props["umls_semantic_type"] = merged_props.get("umls_semantic_type", "Unknown")
        merged_props["description"] = merged_props.get("description", "")

        # Target thresholds and dosage values — inherit from any node in group
        for k in ["target_threshold", "dosage_value", "icd10_code", "rxnorm_id"]:
            for node in group:
                if k in node["properties"] and node["properties"][k] not in ["NONE", "", None]:
                    merged_props[k] = node["properties"][k]
                    break
            # Default fallback for label-specific properties
            if k in ["icd10_code", "rxnorm_id"] and k not in merged_props:
                if (k == "icd10_code" and "Disease" in merged_labels) or \
                   (k == "rxnorm_id" and "Drug" in merged_labels):
                    merged_props[k] = "NONE"

        # Clean aliases: remove the canon_id and umls_canonical from aliases list
        canonical_name = merged_props["umls_canonical"]
        merged_aliases.discard(canon_id)
        merged_aliases.discard(canonical_name)

        # Populate sorted unique aliases array
        merged_props["aliases"] = sorted(list(merged_aliases))

        # Dynamically infer specific medical labels from UMLS Semantic Type if node only has "Concept" label
        clean_labels = {l for l in merged_labels if l not in ["Concept", "Unknown", ""]}
        if not clean_labels:
            inferred = False
            sem_type_str = merged_props.get("umls_semantic_type", "").lower()
            if any(t in sem_type_str for t in ["pharmacologic substance", "clinical drug", "amino acid, peptide, or protein", "hormone", "biologically active substance"]):
                merged_labels.add("Drug")
                inferred = True
            if any(t in sem_type_str for t in ["disease or syndrome", "injury or poisoning"]):
                merged_labels.add("Disease")
                inferred = True
            if any(t in sem_type_str for t in ["sign or symptom", "finding"]):
                merged_labels.add("Symptom")
                inferred = True
            if any(t in sem_type_str for t in ["body part, organ, or organ component", "body location or region"]):
                merged_labels.add("Anatomical Site")
                inferred = True
            if any(t in sem_type_str for t in ["laboratory procedure", "diagnostic procedure", "therapeutic or preventive procedure"]):
                merged_labels.add("Treatment Procedure")
                inferred = True
            if any(t in sem_type_str for t in ["laboratory or test result", "quantitative concept"]):
                merged_labels.add("Clinical Metric")
                inferred = True
            
            if inferred:
                merged_labels.discard("Concept")
        else:
            # If we already have a specific label, discard Concept so it doesn't conflict
            merged_labels.discard("Concept")

        deduped_nodes[canon_id] = {
            "id": canon_id,
            "labels": sorted(list(merged_labels)),
            "properties": merged_props
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Pass 4b: Reverse CUI alias lookup
    # ─────────────────────────────────────────────────────────────────────────
    # Problem: If a node was named 'type 1 diabetes mellitus' (NONE CUI) but
    # another node already has CUI C0011854 with alias 'type 1 diabetes',
    # the two remain separate because they were processed independently.
    # Solution: After all nodes are merged, index every alias/canonical name of
    # CUI nodes, then check all remaining NONE-CUI nodes against that index.
    # ─────────────────────────────────────────────────────────────────────────

    # Build alias → cui_canon_id index from all CUI-resolved nodes
    alias_key_to_cui_node: Dict[str, str] = {}  # normalized_key → canon_id of CUI node
    for canon_id, node in deduped_nodes.items():
        if node["properties"].get("umls_cui", "NONE") == "NONE":
            continue
        # Index normalized canonical UMLS name
        umls_name = node["properties"].get("umls_canonical", "")
        if umls_name:
            alias_key_to_cui_node[normalize_entity_for_dedup(umls_name)] = canon_id
        # Index all existing aliases
        for alias in node["properties"].get("aliases", []):
            if alias:
                alias_key_to_cui_node[normalize_entity_for_dedup(alias)] = canon_id
        # Also index the node id (CUI string) itself
        alias_key_to_cui_node[normalize_entity_for_dedup(canon_id)] = canon_id

    # Check all NONE-CUI nodes — see if they match any CUI node alias
    secondary_remap: Dict[str, str] = {}  # none_cui_canon_id → target_cui_canon_id
    for canon_id, node in deduped_nodes.items():
        if node["properties"].get("umls_cui", "NONE") != "NONE":
            continue  # already has CUI, skip
        dedup_key = normalize_entity_for_dedup(canon_id)
        if dedup_key in alias_key_to_cui_node:
            target = alias_key_to_cui_node[dedup_key]
            if target != canon_id:
                secondary_remap[canon_id] = target
                logger.info(
                    f"[PropertyPacker] Reverse CUI lookup: '{canon_id}' → merging into '{target}' "
                    f"(CUI={deduped_nodes[target]['properties']['umls_cui']})"
                )

    # Perform the secondary merges
    for none_id, cui_id in secondary_remap.items():
        none_node = deduped_nodes.pop(none_id, None)
        if none_node is None:
            continue
        target_node = deduped_nodes[cui_id]

        # Collect aliases from the NONE-CUI node into the CUI node
        merged_aliases_set = set(target_node["properties"].get("aliases", []))
        merged_aliases_set.add(none_id)  # the old raw id becomes an alias
        for a in none_node["properties"].get("aliases", []):
            merged_aliases_set.add(a)

        # Merge labels
        merged_labels_set = set(target_node.get("labels", []))
        merged_labels_set.update(none_node.get("labels", []))

        # Merge properties — NONE-CUI node's values fill gaps in the CUI node
        for k, v in none_node.get("properties", {}).items():
            if k == "aliases":
                continue
            if v and v not in ("NONE", "Unknown", ""):
                if k not in target_node["properties"] or \
                   target_node["properties"][k] in ("NONE", "Unknown", ""):
                    target_node["properties"][k] = v

        # Remove canon name and node id from aliases
        merged_aliases_set.discard(cui_id)
        merged_aliases_set.discard(target_node["properties"].get("umls_canonical", ""))
        target_node["properties"]["aliases"] = sorted(list(merged_aliases_set))
        target_node["labels"] = sorted(list(merged_labels_set))

    # Update node_id_mapping for relationship remapping
    for none_id, cui_id in secondary_remap.items():
        node_id_mapping[none_id] = cui_id
        # Also remap any nodes that were previously pointing to none_id
        for k, v in node_id_mapping.items():
            if v == none_id:
                node_id_mapping[k] = cui_id

    logger.info(
        f"[PropertyPacker] Pass 4b: Reverse CUI lookup merged {len(secondary_remap)} additional node(s)."
    )

    # Pass 5: Remap and deduplicate relationships
    deduped_relationships: List[dict] = []
    seen_relations: set = set()

    for rel in relationships:
        old_start = rel["start"]
        old_end = rel["end"]

        new_start = node_id_mapping.get(old_start, old_start)
        new_end = node_id_mapping.get(old_end, old_end)

        # Avoid self-loops created by deduplication merging
        if new_start == new_end:
            continue

        rel_type = rel["type"]

        # ── Generic Semantic-Based Relationship Correction ──
        if rel_type == "treated_by":
            start_node = deduped_nodes.get(new_start)
            end_node = deduped_nodes.get(new_end)
            if start_node and end_node:
                start_labels = set(start_node.get("labels", []))
                end_labels = set(end_node.get("labels", []))
                start_sem_type = start_node["properties"].get("umls_semantic_type", "")
                end_sem_type = end_node["properties"].get("umls_semantic_type", "")
                start_cui = start_node["properties"].get("umls_cui", "")

                is_start_lab_or_metric = (
                    any(t in start_sem_type for t in ["T059", "T060", "T061", "T034", "T081"]) or
                    "Clinical Metric" in start_labels or
                    "Treatment Procedure" in start_labels or
                    start_cui in ["C0474680", "C0202042"]
                )

                is_end_drug = (
                    any(t in end_sem_type for t in ["T121", "T200", "T116", "T125"]) or
                    "Drug" in end_labels
                )

                if is_start_lab_or_metric and is_end_drug:
                    logger.info(
                        f"[PropertyPacker] Relationship correction: Swapping '{new_start}' and '{new_end}' "
                        f"and changing relation from 'treated_by' to 'decreases' (Clinical Metric -> Drug mismatch detected)."
                    )
                    new_start, new_end = new_end, new_start
                    rel_type = "decreases"

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
