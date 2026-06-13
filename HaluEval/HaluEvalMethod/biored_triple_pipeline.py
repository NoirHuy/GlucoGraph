"""
BioRED -> Diabetes Triple Validity Benchmark Pipeline
=======================================================

Pipeline nay xu ly file BioRED (dang PubTator hoac BioC XML da convert sang
PubTator format) de:
  1. Loc subset cac document lien quan Diabetes (dua tren MeSH ID)
  2. Tach Positive Triples (ground truth relations)
  3. Sinh Negative Triples theo 3 phuong phap:
       - Entity Substitution
       - Relation Inversion
       - Schema/Domain-Range Violation
  4. Can bang & lay mau
  5. Xuat file annotation (blind) cho 2 nguoi cham
  6. Tinh Cohen's kappa sau khi co annotation
  7. Xuat final_benchmark.csv

Cach dung:
  python biored_triple_pipeline.py --input BioRED_Test.PubTator.txt --outdir output/

Yeu cau cai dat:
  pip install pandas scikit-learn --break-system-packages
"""

import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# 1. CAU HINH: MeSH ID lien quan Diabetes va Schema mapping
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

# Anh xa relation BioRED -> relation schema cua GlucoGraph (tuy chinh theo schema thuc te)
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

# Domain/Range hop le cho moi relation schema (dung de tao Schema Violation va kiem tra)
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

# Quan he doi nghich ve mat lam sang, dung cho Relation Inversion
INVERSE_RELATION_MAP = {
    "TREATS": "INCREASES_RISK_OF",
    "INCREASES_RISK_OF": "TREATS",
    "PROTECTS_AGAINST": "ASSOCIATED_WITH",
    "ASSOCIATED_WITH": "PROTECTS_AGAINST",
}


# ---------------------------------------------------------------------------
# 2. PARSE PUBTATOR FORMAT
# ---------------------------------------------------------------------------
# Dinh dang PubTator (moi document):
#   PMID|t|Title
#   PMID|a|Abstract
#   PMID\tstart\tend\tmention\ttype\tidentifier
#   ... (nhieu dong annotation)
#   PMID\trelation_type\tentity1_id\tentity2_id\tnovelty
#   ... (nhieu dong relation)
#   <dong trong cach giua document>

def parse_pubtator(filepath):
    """Tra ve list cac document, moi document la dict gom:
    pmid, title, abstract, entities (dict id -> {mention, type}), relations (list)
    """
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
                    # annotation line: pmid start end mention type identifier
                    _, _, _, mention, etype, identifier = parts
                    # mot identifier co the co nhieu ID phan tach boi ',' hoac ';'
                    for ident in re.split("[,;]", identifier):
                        ident = ident.strip()
                        if ident:
                            current["entities"][ident] = {
                                "mention": mention, "type": etype
                            }
                elif len(parts) == 5:
                    # relation line: pmid relation_type entity1_id entity2_id novelty
                    _, rel_type, e1, e2, novelty = parts
                    current["relations"].append({
                        "relation": rel_type, "entity1": e1, "entity2": e2,
                        "novelty": novelty
                    })

    if current is not None:
        documents.append(current)

    return documents


# ---------------------------------------------------------------------------
# 3. LOC SUBSET DIABETES
# ---------------------------------------------------------------------------

def filter_diabetes_documents(documents, diabetes_ids=DIABETES_MESH_IDS):
    """Giu lai cac document co chua it nhat 1 entity thuoc DIABETES_MESH_IDS."""
    filtered = []
    for doc in documents:
        entity_ids = set(doc["entities"].keys())
        if entity_ids & diabetes_ids:
            filtered.append(doc)
    return filtered


# ---------------------------------------------------------------------------
# 4. TACH POSITIVE TRIPLES
# ---------------------------------------------------------------------------

def extract_positive_triples(documents):
    """Tra ve list dict: subject, relation, object, subject_type, object_type,
    schema_relation, source_doc
    Bo qua cac relation khong co trong RELATION_SCHEMA_MAP (chua duoc anh xa).
    """
    positives = []
    for doc in documents:
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

            # thu chieu nguoc lai neu khong tim thay
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
                continue  # relation type chua duoc anh xa, bo qua

            positives.append({
                "subject": mention1,
                "subject_id": e1,
                "subject_type": type1,
                "relation": schema_rel,
                "object": mention2,
                "object_id": e2,
                "object_type": type2,
                "label": "valid",
                "corruption_type": "none",
                "source_doc": doc["pmid"],
                "swapped": swapped,
            })
    return positives


# ---------------------------------------------------------------------------
# 5. SINH NEGATIVE TRIPLES
# ---------------------------------------------------------------------------

def build_entity_pools(positives):
    """Gom cac entity theo type, dung lam pool de thay the (Entity Substitution)."""
    pools = defaultdict(set)
    for p in positives:
        pools[p["subject_type"]].add((p["subject"], p["subject_id"]))
        pools[p["object_type"]].add((p["object"], p["object_id"]))
    return {k: list(v) for k, v in pools.items()}


def build_true_triple_set(positives):
    """Set (subject_id, relation, object_id) de kiem tra trung voi triple thuc."""
    return {(p["subject_id"], p["relation"], p["object_id"]) for p in positives}


def generate_entity_substitution(positives, entity_pools, true_triples, seed=42):
    rng = random.Random(seed)
    negatives = []
    for p in positives:
        candidates = [e for e in entity_pools.get(p["object_type"], [])
                       if e[1] != p["object_id"]]
        rng.shuffle(candidates)
        for cand_mention, cand_id in candidates:
            if (p["subject_id"], p["relation"], cand_id) not in true_triples:
                negatives.append({
                    "subject": p["subject"], "subject_id": p["subject_id"],
                    "subject_type": p["subject_type"],
                    "relation": p["relation"],
                    "object": cand_mention, "object_id": cand_id,
                    "object_type": p["object_type"],
                    "label": "invalid",
                    "corruption_type": "entity_substitution",
                    "source_doc": p["source_doc"],
                    "original_object": p["object"],
                })
                break  # 1 negative per positive cho loai nay
    return negatives


def generate_relation_inversion(positives, inverse_map=INVERSE_RELATION_MAP):
    negatives = []
    for p in positives:
        inv_rel = inverse_map.get(p["relation"])
        if inv_rel is None:
            continue
        negatives.append({
            "subject": p["subject"], "subject_id": p["subject_id"],
            "subject_type": p["subject_type"],
            "relation": inv_rel,
            "object": p["object"], "object_id": p["object_id"],
            "object_type": p["object_type"],
            "label": "invalid",
            "corruption_type": "relation_inversion",
            "source_doc": p["source_doc"],
            "original_relation": p["relation"],
        })
    return negatives


def generate_schema_violation(positives, entity_pools, valid_domain_range=VALID_DOMAIN_RANGE,
                               seed=42):
    rng = random.Random(seed)
    negatives = []
    for p in positives:
        valid_pairs = valid_domain_range.get(p["relation"], set())
        # tim cac object_type KHONG hop le voi (subject_type, relation) nay
        invalid_types = [t for t in entity_pools.keys()
                          if (p["subject_type"], t) not in valid_pairs]
        if not invalid_types:
            continue
        target_type = rng.choice(invalid_types)
        candidates = entity_pools.get(target_type, [])
        if not candidates:
            continue
        cand_mention, cand_id = rng.choice(candidates)
        negatives.append({
            "subject": p["subject"], "subject_id": p["subject_id"],
            "subject_type": p["subject_type"],
            "relation": p["relation"],
            "object": cand_mention, "object_id": cand_id,
            "object_type": target_type,
            "label": "invalid",
            "corruption_type": "schema_violation",
            "source_doc": p["source_doc"],
            "original_object": p["object"],
            "original_object_type": p["object_type"],
        })
    return negatives


# ---------------------------------------------------------------------------
# 6. CAN BANG VA XUAT FILE ANNOTATION
# ---------------------------------------------------------------------------

def balance_and_sample(positives, negatives, n_per_class=None, seed=42):
    rng = random.Random(seed)
    rng.shuffle(positives)
    rng.shuffle(negatives)

    if n_per_class is None:
        n_per_class = min(len(positives), len(negatives))

    pos_sample = positives[:n_per_class]
    neg_sample = negatives[:n_per_class]
    combined = pos_sample + neg_sample
    rng.shuffle(combined)
    return combined


def export_annotation_sheet(triples, outpath):
    """Xuat file CSV cho annotator: an cot label va corruption_type (blind)."""
    df = pd.DataFrame(triples)
    df["triple_id"] = range(1, len(df) + 1)

    blind_cols = ["triple_id", "subject", "relation", "object",
                   "subject_type", "object_type"]
    df_blind = df[blind_cols].copy()
    df_blind["annotator_label"] = ""  # annotator dien: valid / invalid / uncertain
    df_blind["notes"] = ""

    df_blind.to_csv(outpath, index=False, encoding="utf-8-sig")

    # luu ban day du (co ground truth) rieng, KHONG gui cho annotator
    full_path = outpath.parent / ("full_with_groundtruth_" + outpath.name)
    df.to_csv(full_path, index=False, encoding="utf-8-sig")
    return df


# ---------------------------------------------------------------------------
# 7. TINH COHEN'S KAPPA (chay sau khi co annotation)
# ---------------------------------------------------------------------------

def compute_kappa(annotation_csv_1, annotation_csv_2):
    from sklearn.metrics import cohen_kappa_score

    df1 = pd.read_csv(annotation_csv_1)
    df2 = pd.read_csv(annotation_csv_2)

    merged = df1[["triple_id", "annotator_label"]].merge(
        df2[["triple_id", "annotator_label"]], on="triple_id",
        suffixes=("_1", "_2"))

    kappa = cohen_kappa_score(merged["annotator_label_1"],
                               merged["annotator_label_2"])
    agreement = (merged["annotator_label_1"] == merged["annotator_label_2"]).mean()

    print(f"So luong triple: {len(merged)}")
    print(f"Ty le dong thuan tuyet doi: {agreement:.2%}")
    print(f"Cohen's kappa: {kappa:.3f}")

    disagreements = merged[merged["annotator_label_1"] != merged["annotator_label_2"]]
    return kappa, agreement, disagreements


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True,
                         help="Duong dan file BioRED dang PubTator (.txt)")
    parser.add_argument("--outdir", default="output", help="Thu muc xuat ket qua")
    parser.add_argument("--n_per_class", type=int, default=None,
                         help="So luong moi class (valid/invalid) sau khi can bang")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print("[1/6] Doc file PubTator...")
    documents = parse_pubtator(args.input)
    print(f"  -> Tong so document: {len(documents)}")

    print("[2/6] Loc subset Diabetes...")
    diabetes_docs = filter_diabetes_documents(documents)
    print(f"  -> So document lien quan Diabetes: {len(diabetes_docs)}")

    print("[3/6] Tach Positive Triples...")
    positives = extract_positive_triples(diabetes_docs)
    print(f"  -> So Positive Triples: {len(positives)}")

    print("[4/6] Sinh Negative Triples (3 phuong phap)...")
    entity_pools = build_entity_pools(positives)
    true_triples = build_true_triple_set(positives)

    neg_entity_sub = generate_entity_substitution(positives, entity_pools, true_triples)
    neg_rel_inv = generate_relation_inversion(positives)
    neg_schema = generate_schema_violation(positives, entity_pools)

    print(f"  -> Entity Substitution : {len(neg_entity_sub)}")
    print(f"  -> Relation Inversion  : {len(neg_rel_inv)}")
    print(f"  -> Schema Violation    : {len(neg_schema)}")

    all_negatives = neg_entity_sub + neg_rel_inv + neg_schema

    print("[5/6] Can bang va lay mau...")
    final_set = balance_and_sample(positives, all_negatives, n_per_class=args.n_per_class)
    print(f"  -> Tong so triples trong benchmark: {len(final_set)}")

    print("[6/6] Xuat file annotation...")
    df = export_annotation_sheet(final_set, outdir / "annotation_sheet.csv")

    # luu them thong ke
    stats = df["corruption_type"].value_counts().to_dict()
    with open(outdir / "stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print("\nHoan tat. Cac file da tao trong thu muc:", outdir)
    print("  - annotation_sheet.csv          (gui cho annotator 1, copy them ban cho annotator 2)")
    print("  - full_with_groundtruth_annotation_sheet.csv  (luu rieng, KHONG gui annotator)")
    print("  - stats.json                    (thong ke phan bo corruption type)")
    print("\nThong ke:", stats)
    print("\nSau khi co 2 file annotation da dien (vd: annot1.csv, annot2.csv), chay:")
    print("  from biored_triple_pipeline import compute_kappa")
    print("  compute_kappa('annot1.csv', 'annot2.csv')")


if __name__ == "__main__":
    main()
