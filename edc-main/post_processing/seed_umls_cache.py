"""
seed_umls_cache.py — Pre-seed the UMLS cache with high-priority clinical entities
that are known to fail API lookup due to lexical mismatch (plurals, hyphenated forms, etc.)

All entries are sourced from:
  - NCI Thesaurus (NCI)
  - MeSH (MSH)
  - UMLS standard definitions (English)

Usage:
  python post_processing/seed_umls_cache.py [--cache_path output/umls_cache.json]
"""
import json
import os
import argparse

# ─────────────────────────────────────────────────────────────────────────────
# Seed entries: high-priority terms in the diabetes / endocrinology domain
# Each key is the LOWERCASE term as it appears in the KG node id.
# ─────────────────────────────────────────────────────────────────────────────
SEED_ENTRIES = {
    # ── Diseases ────────────────────────────────────────────────────────────
    "stroke": {
        "cui": "C0038454",
        "canonical": "Stroke",
        "semantic_type": "Disease or Syndrome (T047)",
        "score": 10.0,
        "icd10_code": "I63",
        "rxnorm_id": "NONE",
        "definition": (
            "A sudden loss of neurological function secondary to an ischemic or hemorrhagic "
            "intracranial vascular event. [NCIT:C3390]"
        ),
    },
    "hypoxia": {
        "cui": "C0242429",
        "canonical": "Hypoxia",
        "semantic_type": "Disease or Syndrome (T047)",
        "score": 10.0,
        "icd10_code": "R09.02",
        "rxnorm_id": "NONE",
        "definition": (
            "A condition in which there is a deficiency of oxygen reaching the tissues of the body. "
            "[MeSH: D000860]"
        ),
    },
    "confusion": {
        "cui": "C0009676",
        "canonical": "Confusion",
        "semantic_type": "Sign or Symptom (T184)",
        "score": 10.0,
        "icd10_code": "R41.3",
        "rxnorm_id": "NONE",
        "definition": (
            "A mental state characterized by bewilderment, emotional disturbance, lack of clear "
            "thinking, and perceptual disorientation. [NCI]"
        ),
    },
    "metabolic acidosis": {
        "cui": "C0001125",
        "canonical": "Acidosis, Metabolic",
        "semantic_type": "Disease or Syndrome (T047)",
        "score": 9.0,
        "icd10_code": "E87.2",
        "rxnorm_id": "NONE",
        "definition": (
            "A disorder characterized by a decrease in blood pH due to accumulation of acid or "
            "depletion of alkaline reserves. [NCI]"
        ),
    },
    "acidemia": {
        "cui": "C0220981",
        "canonical": "Acidemia",
        "semantic_type": "Disease or Syndrome (T047)",
        "score": 10.0,
        "icd10_code": "E87.2",
        "rxnorm_id": "NONE",
        "definition": (
            "An abnormal decrease in the pH of the blood. This is a decrease in the hydrogen ion "
            "concentration of the blood. [NCI]"
        ),
    },
    "alcohol use disorder": {
        "cui": "C0001956",
        "canonical": "Alcohol Use Disorder",
        "semantic_type": "Disease or Syndrome (T047)",
        "score": 10.0,
        "icd10_code": "F10.1",
        "rxnorm_id": "NONE",
        "definition": (
            "A maladaptive pattern of alcohol use leading to clinically significant impairment or "
            "distress. [DSM-5]"
        ),
    },
    "mild hypoglycemia": {
        "cui": "C0020615",
        "canonical": "Hypoglycemia",
        "semantic_type": "Disease or Syndrome (T047)",
        "score": 7.0,
        "icd10_code": "E16.0",
        "rxnorm_id": "NONE",
        "definition": (
            "A mild episode of hypoglycemia in which the patient is symptomatic but can self-treat "
            "by consuming carbohydrates. [ADA Standards of Medical Care]"
        ),
    },
    "moderate hypoglycemia": {
        "cui": "C0020615",
        "canonical": "Hypoglycemia",
        "semantic_type": "Disease or Syndrome (T047)",
        "score": 7.0,
        "icd10_code": "E16.0",
        "rxnorm_id": "NONE",
        "definition": (
            "A moderate episode of hypoglycemia with symptoms severe enough to require assistance "
            "from another person. [ADA Standards of Medical Care]"
        ),
    },
    "latex allergy": {
        "cui": "C0879626",
        "canonical": "Latex Hypersensitivity",
        "semantic_type": "Disease or Syndrome (T047)",
        "score": 10.0,
        "icd10_code": "Z91.040",
        "rxnorm_id": "NONE",
        "definition": (
            "An allergic reaction to natural rubber latex (NRL) proteins. "
            "Manifestations range from contact urticaria to anaphylaxis. [NCI]"
        ),
    },
    "lipohypertrophy": {
        "cui": "C0334388",
        "canonical": "Lipohypertrophy",
        "semantic_type": "Disease or Syndrome (T047)",
        "score": 10.0,
        "icd10_code": "E88.2",
        "rxnorm_id": "NONE",
        "definition": (
            "An abnormal accumulation of fat beneath the skin at insulin injection sites, "
            "resulting in a firm rubbery lump. [NCI]"
        ),
    },
    # ── Symptoms / Findings ─────────────────────────────────────────────────
    "insulin resistance": {
        "cui": "C0021655",
        "canonical": "Insulin Resistance",
        "semantic_type": "Finding (T033)",
        "score": 10.0,
        "icd10_code": "NONE",
        "rxnorm_id": "NONE",
        "definition": (
            "Diminished effectiveness of insulin in lowering blood sugar levels; a characteristic "
            "feature of type 2 diabetes that can also occur in type 1 diabetes. [MeSH: D007333]"
        ),
    },
    "hyperinsulinemia": {
        "cui": "C0020459",
        "canonical": "Hyperinsulinism",
        "semantic_type": "Disease or Syndrome (T047)",
        "score": 9.0,
        "icd10_code": "E16.1",
        "rxnorm_id": "NONE",
        "definition": (
            "A condition characterized by abnormally elevated levels of insulin in the blood. "
            "[MeSH: D006946]"
        ),
    },
    "light-headedness": {
        "cui": "C0012833",
        "canonical": "Dizziness",
        "semantic_type": "Sign or Symptom (T184)",
        "score": 8.0,
        "icd10_code": "R42",
        "rxnorm_id": "NONE",
        "definition": (
            "A sensation of lightheadedness, unsteadiness, or giddiness often associated with "
            "hypoglycemia or orthostatic changes. [NCI]"
        ),
    },
    # ── Drugs ────────────────────────────────────────────────────────────────
    "sulfonylureas": {
        "cui": "C0038654",
        "canonical": "Sulfonylurea Compounds",
        "semantic_type": "Organic Chemical (T109), Pharmacologic Substance (T121)",
        "score": 10.0,
        "icd10_code": "NONE",
        "rxnorm_id": "NONE",
        "definition": (
            "A class of antidiabetic agents that stimulate insulin secretion from pancreatic "
            "beta cells by blocking ATP-sensitive potassium channels. Includes glyburide, "
            "glipizide, and glimepiride. [NCI]"
        ),
    },
    "glucocorticoids": {
        "cui": "C0017710",
        "canonical": "Glucocorticoids",
        "semantic_type": "Steroid (T110), Hormone (T125), Pharmacologic Substance (T121)",
        "score": 10.0,
        "icd10_code": "NONE",
        "rxnorm_id": "NONE",
        "definition": (
            "A class of steroid hormones produced in the adrenal cortex that regulate glucose "
            "metabolism and suppress inflammation. Also used therapeutically as "
            "immunosuppressants. [MeSH: D005938]"
        ),
    },
    "immunosuppressants": {
        "cui": "C0021081",
        "canonical": "Immunosuppressive Agents",
        "semantic_type": "Pharmacologic Substance (T121)",
        "score": 10.0,
        "icd10_code": "NONE",
        "rxnorm_id": "NONE",
        "definition": (
            "Agents that suppress immune function by one of several mechanisms of action. "
            "Classical immunosuppressants act by inhibiting either the generation or the "
            "effector function of T lymphocytes. [MeSH: D007166]"
        ),
    },
    "iv dextrose": {
        "cui": "C0017765",
        "canonical": "Glucose",
        "semantic_type": "Organic Chemical (T109), Pharmacologic Substance (T121)",
        "score": 8.0,
        "icd10_code": "NONE",
        "rxnorm_id": "4126",
        "definition": (
            "Intravenous dextrose (glucose) solution used to treat severe hypoglycemia when the "
            "patient is unconscious or unable to take oral carbohydrates. [NCI]"
        ),
    },
    "oral glucose": {
        "cui": "C0017765",
        "canonical": "Glucose",
        "semantic_type": "Organic Chemical (T109), Pharmacologic Substance (T121)",
        "score": 8.0,
        "icd10_code": "NONE",
        "rxnorm_id": "4126",
        "definition": (
            "Glucose administered orally to treat mild to moderate hypoglycemia. "
            "Preferred form: 15-20g fast-acting carbohydrates. [ADA Standards 2024]"
        ),
    },
    "biguanides (metformin)": {
        "cui": "C0005382",
        "canonical": "Biguanides",
        "semantic_type": "Organic Chemical (T109), Pharmacologic Substance (T121)",
        "score": 9.0,
        "icd10_code": "NONE",
        "rxnorm_id": "NONE",
        "definition": (
            "A class of oral antihyperglycemic agents that includes metformin. Biguanides reduce "
            "hepatic glucose production and improve peripheral insulin sensitivity. [NCI]"
        ),
    },
    "intensive therapy": {
        "cui": "C0021643",
        "canonical": "Intensive insulin therapy",
        "semantic_type": "Therapeutic or Preventive Procedure (T061)",
        "score": 10.0,
        "icd10_code": "NONE",
        "rxnorm_id": "NONE",
        "definition": (
            "An intensive treatment for diabetes mellitus consisting of frequent insulin injections "
            "or pump therapy guided by self-monitoring of blood glucose."
        ),
    },
    "oral form": {
        "cui": "C0205080",
        "canonical": "Oral Administration",
        "semantic_type": "Therapeutic or Preventive Procedure (T061)",
        "score": 10.0,
        "icd10_code": "NONE",
        "rxnorm_id": "NONE",
        "definition": "Administration of a drug through the mouth.",
    },
    "ckd": {
        "cui": "C1561643",
        "canonical": "Chronic Kidney Diseases",
        "semantic_type": "Disease or Syndrome (T047)",
        "score": 10.0,
        "icd10_code": "N18.9",
        "rxnorm_id": "NONE",
        "definition": "A condition characterized by gradual loss of kidney function over time.",
    },
    "destruction of the pancreatic beta-cells": {
        "cui": "C3244301",
        "canonical": "Pancreatic beta-cell destruction",
        "semantic_type": "Finding (T033)",
        "score": 10.0,
        "icd10_code": "NONE",
        "rxnorm_id": "NONE",
        "definition": "Pathological destruction of the insulin-producing pancreatic beta cells.",
    },
    "gastrointestinal adverse effects": {
        "cui": "C0521901",
        "canonical": "Gastrointestinal side effects",
        "semantic_type": "Sign or Symptom (T184)",
        "score": 10.0,
        "icd10_code": "NONE",
        "rxnorm_id": "NONE",
        "definition": "Adverse drug reactions or side effects that affect the gastrointestinal tract.",
    },
    "euglycemic dka": {
        "cui": "C4230761",
        "canonical": "Euglycemic diabetic ketoacidosis",
        "semantic_type": "Disease or Syndrome (T047)",
        "score": 10.0,
        "icd10_code": "E10.1",
        "rxnorm_id": "NONE",
        "definition": (
            "A rare but life-threatening complication of diabetes characterized by diabetic ketoacidosis "
            "in the presence of normal or near-normal blood glucose levels."
        ),
    },
    "euglycemic diabetic ketoacidosis": {
        "cui": "C4230761",
        "canonical": "Euglycemic diabetic ketoacidosis",
        "semantic_type": "Disease or Syndrome (T047)",
        "score": 10.0,
        "icd10_code": "E10.1",
        "rxnorm_id": "NONE",
        "definition": (
            "A rare but life-threatening complication of diabetes characterized by diabetic ketoacidosis "
            "in the presence of normal or near-normal blood glucose levels."
        ),
    },
    "long-term complications of diabetes mellitus": {
        "cui": "C0271676",
        "canonical": "Long-term complications of diabetes mellitus",
        "semantic_type": "Disease or Syndrome (T047)",
        "score": 10.0,
        "icd10_code": "E11.9",
        "rxnorm_id": "NONE",
        "definition": "Chronic complications arising from long-term poorly controlled diabetes mellitus.",
    },
}


def seed_cache(cache_path: str) -> None:
    # Load existing cache if present
    existing: dict = {}
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = {}

    added = 0
    updated = 0
    for term_key, entry in SEED_ENTRIES.items():
        if term_key not in existing:
            existing[term_key] = entry
            added += 1
        else:
            existing[term_key] = entry
            updated += 1

    os.makedirs(os.path.dirname(os.path.abspath(cache_path)), exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=4, ensure_ascii=False)

    print(f"\n[OK] Seeded {added} new entries, updated {updated} existing entries in: {cache_path}")
    print(f"     Total cache size: {len(existing)} entries\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed UMLS cache with high-priority clinical entities.")
    parser.add_argument(
        "--cache_path",
        default="output/umls_cache.json",
        help="Path to the UMLS cache JSON file (default: output/umls_cache.json)",
    )
    args = parser.parse_args()
    seed_cache(args.cache_path)
