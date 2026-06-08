"""
constants.py — Shared constants for the post_processing package.

Single source of truth for:
  - LOCAL_MEDICAL_ABBREVIATIONS: Clinical acronym expansion table
  - MEDICAL_STOPWORDS: Stopwords removed during deduplication normalization
  - MEDICAL_SAFE_TUIS: Valid UMLS Semantic Type Identifiers for clinical domain
  - CACHE_VERSION: Version tag for cache invalidation on schema changes

Previously these were duplicated across umls_normalizer.py and property_packer.py.
"""

from typing import Dict

# ─────────────────────────────────────────────────────────────────────────────
# Cache versioning — bump this when the cache schema changes
# (e.g. new fields added to UMLS query results, TUI list expanded, etc.)
# Caches with a different version will be automatically invalidated.
# ─────────────────────────────────────────────────────────────────────────────
CACHE_VERSION: str = "2.0"

# ─────────────────────────────────────────────────────────────────────────────
# Semantic Types: Danh sách TUI hợp lệ cho miền y khoa lâm sàng
# Được mở rộng từ 4 lên 17 loại để bao phủ đầy đủ:
#   thuốc (T121, T200, T116, T125, T109, T123),
#   bệnh/triệu chứng (T047, T184, T033, T037),
#   thủ thuật/xét nghiệm (T061, T059, T060),
#   giải phẫu (T023, T029),
#   chỉ số lâm sàng (T034, T081)
# ─────────────────────────────────────────────────────────────────────────────
MEDICAL_SAFE_TUIS: frozenset = frozenset({
    # Bệnh lý & triệu chứng
    "T047",  # Disease or Syndrome
    "T184",  # Sign or Symptom
    "T033",  # Finding
    "T037",  # Injury or Poisoning
    # Thuốc & hoạt chất
    "T121",  # Pharmacologic Substance (metformin, glipizide...)
    "T200",  # Clinical Drug — biệt dược thương mại (Lantus, Januvia...)
    "T116",  # Amino Acid, Peptide, or Protein (insulin là một protein)
    "T125",  # Hormone (glucagon, insulin thuộc nhóm hormone)
    "T109",  # Organic Chemical (nhiều thuốc tổng hợp hữu cơ)
    "T123",  # Biologically Active Substance
    # Thủ thuật & xét nghiệm
    "T061",  # Therapeutic or Preventive Procedure
    "T059",  # Laboratory Procedure (HbA1c test, fasting glucose)
    "T060",  # Diagnostic Procedure
    # Giải phẫu
    "T023",  # Body Part, Organ, or Organ Component (pancreas, kidney...)
    "T029",  # Body Location or Region
    # Chỉ số & kết quả lâm sàng
    "T034",  # Laboratory or Test Result
    "T081",  # Quantitative Concept (HbA1c threshold value)
})

# ─────────────────────────────────────────────────────────────────────────────
# Medical Abbreviation Expansion Table
# Maps common clinical abbreviations / aliases → canonical lowercase form.
# Used in normalize_entity_for_dedup() and _expand_abbreviations().
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
    # Anatomy / conditions
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
MEDICAL_STOPWORDS: frozenset = frozenset({
    "the", "a", "an", "of", "with", "in", "and", "or", "to", "for",
    "mellitus", "syndrome", "disease", "disorder", "condition",
    "associated", "related", "induced", "dependent", "independent",
})

# ─────────────────────────────────────────────────────────────────────────────
# Protected medical terms — words that should NOT be stemmed because removing
# common suffixes would destroy their meaning (e.g. "glucose" → "glucoe")
# ─────────────────────────────────────────────────────────────────────────────
STEM_PROTECTED_TERMS: frozenset = frozenset({
    "glucose", "dextrose", "fructose", "lactose", "sucrose", "maltose",
    "galactose", "trehalose", "ribose",
    "lipase", "amylase", "protease", "kinase",
    "diabetes", "prediabetes",
    "diagnosis", "prognosis",
    "acidosis", "ketoacidosis", "alkalosis",
    "fibrosis", "sclerosis", "stenosis", "thrombosis", "necrosis",
    "hypoxia", "anoxia",
    "anemia",
    "plus", "nexus", "bolus", "corpus", "sinus", "fetus", "stimulus",
})
