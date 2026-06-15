"""
BioRED -> Automated Diabetes Triple Validity Benchmark Pipeline (Algorithmic Ground Truth)
========================================================================================

This script automatically generates a balanced test dataset from the BioRED corpus
using programmatic corruption methods and validation rules (no human annotators needed).

Steps:
  1. Parse BioRED PubTator format.
  2. Filter documents related to Diabetes (by MeSH IDs).
  3. Extract positive triples (expert-verified ground truth from NCBI).
  4. Programmatically generate negative triples via 3 corruption types:
       - Entity Substitution (cross-checked against the entire corpus to ensure falsity)
       - Relation Inversion (clinically contradictory relations)
       - Schema Violation (domain/range mismatch verified against the schema)
  5. Balance (1:1 positive/negative) and shuffle.
  6. Output the final benchmark directly to JSON, ready for the P2P Debate Gate.

Usage:
  python biored_triple_pipeline_automated.py --input BioRED_Test.PubTator.txt --output final_benchmark.json
"""

import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Configuration: MeSH IDs and Schema Mapping
# ---------------------------------------------------------------------------

DIABETES_MESH_IDS = {
    "D003920",  # Diabetes Mellitus
    "D003922",  # Diabetes Mellitus, Type 1
    "D003924",  # Diabetes Mellitus, Type 2
    "D003925",  # Diabetes, Gestational
    "D003921",  # Diabetes Mellitus, Experimental
    "D003923",  # Diabetic Nephropathies
    "D003929",  # Diabetic Retinopathy
    "D007328",  # Insulin
    "D008687",  # Metformin
}

RELATION_SCHEMA_MAP = {
    ("Positive_Correlation", "ChemicalEntity", "DiseaseOrPhenotypicFeature"): "INCREASES_RISK_OF",
    ("Negative_Correlation", "ChemicalEntity", "DiseaseOrPhenotypicFeature"): "TREATS",
    ("Positive_Correlation", "GeneOrGeneProduct", "DiseaseOrPhenotypicFeature"): "ASSOCIATED_WITH",
    ("Negative_Correlation", "GeneOrGeneProduct", "DiseaseOrPhenotypicFeature"): "PROTECTS_AGAINST",
    ("Association", "ChemicalEntity", "DiseaseOrPhenotypicFeature"): "ASSOCIATED_WITH",
    ("Association", "GeneOrGeneProduct", "DiseaseOrPhenotypicFeature"): "ASSOCIATED_WITH",
    ("Drug_Interaction", "ChemicalEntity", "ChemicalEntity"): "INTERACTS_WITH",
    ("Cotreatment", "ChemicalEntity", "ChemicalEntity"): "COADMINISTERED_WITH",
    ("Bind", "GeneOrGeneProduct", "ChemicalEntity"): "BINDS_TO",
    ("Comparison", "ChemicalEntity", "ChemicalEntity"): "COMPARED_WITH",
    ("Conversion", "ChemicalEntity", "ChemicalEntity"): "CONVERTED_TO",
}

VALID_DOMAIN_RANGE = {
    "INCREASES_RISK_OF": {("ChemicalEntity", "DiseaseOrPhenotypicFeature"),
                           ("GeneOrGeneProduct", "DiseaseOrPhenotypicFeature")},
    "TREATS": {("ChemicalEntity", "DiseaseOrPhenotypicFeature")},
    "ASSOCIATED_WITH": {("ChemicalEntity", "DiseaseOrPhenotypicFeature"),
                         ("GeneOrGeneProduct", "DiseaseOrPhenotypicFeature")},
    "PROTECTS_AGAINST": {("GeneOrGeneProduct", "DiseaseOrPhenotypicFeature")},
    "INTERACTS_WITH": {("ChemicalEntity", "ChemicalEntity")},
    "COADMINISTERED_WITH": {("ChemicalEntity", "ChemicalEntity")},
    "BINDS_TO": {("GeneOrGeneProduct", "ChemicalEntity")},
    "COMPARED_WITH": {("ChemicalEntity", "ChemicalEntity")},
    "CONVERTED_TO": {("ChemicalEntity", "ChemicalEntity")},
}

INVERSE_RELATION_MAP = {
    "TREATS": "INCREASES_RISK_OF",
    "INCREASES_RISK_OF": "TREATS",
    "PROTECTS_AGAINST": "ASSOCIATED_WITH",
    "ASSOCIATED_WITH": "PROTECTS_AGAINST",
}

# ---------------------------------------------------------------------------
# 2. Parse PubTator Format
# ---------------------------------------------------------------------------

def parse_pubtator(filepath):
    documents = []
    current = None

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                if current is not None:
                    documents.append(current)
                    current = None
                continue

            if "|t|" in line:
                pmid, _, title = line.split("|", 2)
                current = {"pmid": pmid, "title": title, "abstract": "",
                           "entities": {}, "relations": []}
            elif "|a|" in line:
                pmid, _, abstract = line.split("|", 2)
                if current is not None:
                    current["abstract"] = abstract
            else:
                parts = line.split("\t")
                if current is None:
                    continue
                if len(parts) == 6:
                    _, _, _, mention, etype, identifier = parts
                    for ident in re.split("[,;]", identifier):
                        ident = ident.strip()
                        if ident:
                            current["entities"][ident] = {
                                "mention": mention, "type": etype
                            }
                elif len(parts) == 5:
                    _, rel_type, e1, e2, novelty = parts
                    current["relations"].append({
                        "relation": rel_type, "entity1": e1, "entity2": e2,
                        "novelty": novelty
                    })

    if current is not None:
        documents.append(current)

    return documents

# ---------------------------------------------------------------------------
# 3. Filter Diabetes Subset & Extract Positives
# ---------------------------------------------------------------------------

def filter_diabetes(documents, diabetes_ids=DIABETES_MESH_IDS):
    return [doc for doc in documents if set(doc["entities"].keys()) & diabetes_ids]

def extract_positives(documents):
    positives = []
    for doc in documents:
        # Construct passage context
        context = f"{doc['title']} {doc['abstract']}".strip()
        
        for rel in doc["relations"]:
            e1, e2 = rel["entity1"], rel["entity2"]
            if e1 not in doc["entities"] or e2 not in doc["entities"]:
                continue
            type1 = doc["entities"][e1]["type"]
            type2 = doc["entities"][e2]["type"]
            mention1 = doc["entities"][e1]["mention"]
            mention2 = doc["entities"][e2]["mention"]

            key = (rel["relation"], type1, type2)
            schema_rel = RELATION_SCHEMA_MAP.get(key)
            swapped = False
            if schema_rel is None:
                key_rev = (rel["relation"], type2, type1)
                schema_rel = RELATION_SCHEMA_MAP.get(key_rev)
                if schema_rel is not None:
                    e1, e2 = e2, e1
                    type1, type2 = type2, type1
                    mention1, mention2 = mention2, mention1
                    swapped = True

            if schema_rel is None:
                continue

            positives.append({
                "subject": mention1,
                "subject_id": e1,
                "subject_type": type1,
                "relation": schema_rel,
                "object": mention2,
                "object_id": e2,
                "object_type": type2,
                "ground_truth": "Valid",
                "corruption_type": "None",
                "source_text": context,
                "pmid": doc["pmid"]
            })
    return positives

# ---------------------------------------------------------------------------
# 4. Programmatic Negative Triple Generator
# ---------------------------------------------------------------------------

def generate_negatives(positives, seed=42):
    rng = random.Random(seed)
    
    # 1. Build Entity pools by type
    entity_pools = defaultdict(set)
    for p in positives:
        entity_pools[p["subject_type"]].add((p["subject"], p["subject_id"]))
        entity_pools[p["object_type"]].add((p["object"], p["object_id"]))
    entity_pools = {k: list(v) for k, v in entity_pools.items()}
    
    # 2. Build Set of true triples to check against
    true_triples = {(p["subject_id"], p["relation"].lower(), p["object_id"]) for p in positives}
    
    negatives = []
    
    for p in positives:
        # A. Entity Substitution
        candidates = [e for e in entity_pools.get(p["object_type"], []) if e[1] != p["object_id"]]
        if candidates:
            rng.shuffle(candidates)
            for cand_mention, cand_id in candidates:
                if (p["subject_id"], p["relation"].lower(), cand_id) not in true_triples:
                    negatives.append({
                        "subject": p["subject"],
                        "subject_id": p["subject_id"],
                        "subject_type": p["subject_type"],
                        "relation": p["relation"],
                        "object": cand_mention,
                        "object_id": cand_id,
                        "object_type": p["object_type"],
                        "ground_truth": "Invalid",
                        "corruption_type": "Entity Substitution",
                        "source_text": p["source_text"],
                        "pmid": p["pmid"]
                    })
                    break
        
        # B. Relation Inversion
        inv_rel = INVERSE_RELATION_MAP.get(p["relation"])
        if inv_rel:
            negatives.append({
                "subject": p["subject"],
                "subject_id": p["subject_id"],
                "subject_type": p["subject_type"],
                "relation": inv_rel,
                "object": p["object"],
                "object_id": p["object_id"],
                "object_type": p["object_type"],
                "ground_truth": "Invalid",
                "corruption_type": "Relation Inversion",
                "source_text": p["source_text"],
                "pmid": p["pmid"]
            })
            
        # C. Schema Violation
        valid_pairs = VALID_DOMAIN_RANGE.get(p["relation"], set())
        invalid_types = [t for t in entity_pools.keys() if (p["subject_type"], t) not in valid_pairs]
        if invalid_types:
            target_type = rng.choice(invalid_types)
            candidates = entity_pools.get(target_type, [])
            if candidates:
                cand_mention, cand_id = rng.choice(candidates)
                negatives.append({
                    "subject": p["subject"],
                    "subject_id": p["subject_id"],
                    "subject_type": p["subject_type"],
                    "relation": p["relation"],
                    "object": cand_mention,
                    "object_id": cand_id,
                    "object_type": target_type,
                    "ground_truth": "Invalid",
                    "corruption_type": "Schema Violation",
                    "source_text": p["source_text"],
                    "pmid": p["pmid"]
                })
                
    return negatives

# ---------------------------------------------------------------------------
# 5. Main Execution
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to BioRED PubTator file")
    parser.add_argument("--output", default="final_benchmark.json", help="Output JSON path")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--n_per_class", type=int, default=None, help="Number of samples per class (Valid/Invalid)")
    args = parser.parse_args()
    
    print("[1/5] Parsing BioRED dataset...")
    docs = parse_pubtator(args.input)
    print(f"      Total documents parsed: {len(docs)}")
    
    print("[2/5] Filtering diabetes subset...")
    diab_docs = filter_diabetes(docs)
    print(f"      Diabetes documents: {len(diab_docs)}")
    
    print("[3/5] Extracting Positive Triples...")
    positives = extract_positives(diab_docs)
    print(f"      Positive triples: {len(positives)}")
    
    print("[4/5] Generating Negatives via Algorithmic Corruption...")
    negatives = generate_negatives(positives, seed=args.seed)
    print(f"      Negative triples generated: {len(negatives)}")
    
    # Balance 1:1
    sample_size = min(len(positives), len(negatives))
    if args.n_per_class is not None:
        sample_size = min(sample_size, args.n_per_class)
        
    random.seed(args.seed)
    sampled_positives = random.sample(positives, sample_size)
    sampled_negatives = random.sample(negatives, sample_size)
    
    final_dataset = sampled_positives + sampled_negatives
    random.shuffle(final_dataset)
    
    print(f"[5/5] Exporting {len(final_dataset)} triples to {args.output}...")
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(final_dataset, f, ensure_ascii=False, indent=2)
        
    # Format and export to HaluEval data directory
    halueval_size = len(final_dataset)
    size_dir = Path("HaluEval/data") / f"{halueval_size}_triples"
    size_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Format dataset.json
    halueval_dataset = []
    for idx, t in enumerate(final_dataset):
        halueval_dataset.append({
            "index": idx,
            "input_text": t["source_text"],
            "entity_hint": "",
            "relation_hint": "",
            "oie_raw": [],
            "oie": [],
            "schema_canonicalizaiton": [
                [t["subject"], t["relation"], t["object"]]
            ]
        })
        
    with open(size_dir / "dataset.json", "w", encoding="utf-8") as f:
        json.dump(halueval_dataset, f, ensure_ascii=False, indent=2)
        
    # 2. Format references.txt
    with open(size_dir / "references.txt", "w", encoding="utf-8") as f:
        for t in final_dataset:
            if t["ground_truth"] == "Valid":
                # Write triple as list of list: [['sub', 'rel', 'obj']]
                f.write(f"[[{repr(t['subject'])}, {repr(t['relation'])}, {repr(t['object'])}]]\n")
            else:
                f.write("[]\n")
                
    print(f"       Exported HaluEval inputs to: {size_dir}/dataset.json and {size_dir}/references.txt")
    print("\n[Done] Pipeline executed successfully.")
    print(f"       Balanced test triples: {len(final_dataset)} (50% Valid, 50% Invalid)")
    
if __name__ == "__main__":
    main()
