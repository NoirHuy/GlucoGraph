"""
build_diabetes_schema.py
========================
Pipeline 2 bước:
  STEP 1 — Gọi UMLS API, lấy TẤT CẢ quan hệ + định nghĩa liên quan
           đến CUI C0011849 (Diabetes Mellitus), lưu vào raw_relations.json
  STEP 2 — Lọc các quan hệ có giá trị lâm sàng, tạo file
           diabetes_schema.csv theo chuẩn edc-main (2 cột: relation, definition)

Usage:
    $env:UMLS_API_KEY="your_key"
    python build_diabetes_schema.py
"""

import csv
import json
import os
import time
from pathlib import Path

import requests

# ── Cấu hình ─────────────────────────────────────────────────────────────────
API_KEY  = os.environ.get("UMLS_API_KEY", "")
BASE_URL = "https://uts-ws.nlm.nih.gov/rest"
VERSION  = "current"
SEED_CUI = "C0011849"   # Diabetes Mellitus
PAGE_SIZE = 25
SLEEP     = 0.25        # giây giữa các request

OUTPUT_DIR   = Path("output")
RAW_FILE     = OUTPUT_DIR / "raw_relations.json"

# Đường dẫn đến thư mục schemas của edc-main (điều chỉnh nếu cần)
SCHEMA_DIR   = Path(__file__).parent.parent.parent / "edc-main" / "schemas" / "disease"
SCHEMA_FILE  = SCHEMA_DIR / "diabetes_schema.csv"

# ── Danh sách quan hệ KỸ THUẬT cần loại bỏ ───────────────────────────────────
# (mapping, dịch thuật, hành chính — không có giá trị lâm sàng)
EXCLUDED_ADDITIONAL = {
    "mapped_to", "mapped_from", "has_translation", "has_transliterated_form",
    "translation_of", "transliterated_form_of", "has_expanded_form",
    "expanded_form_of", "concept_in_subset", "has_entry_combination",
    "answer_to", "has_seronet_authorized_value",
    "is_seronet_authorized_value_for_variable", "is_value_for_gdc_property",
    "replaces", "possibly_equivalent_to", "same_as", "classifies",
    "classified_as", "used_for", "focus_of", "realization_of",
    "alternative_of", "inverse_was_a",
}

EXCLUDED_LABELS = {"QB", "RL", "SY"}   # Pure synonym / mapping top-level labels

# ── Định nghĩa ngữ nghĩa cho từng quan hệ y khoa ─────────────────────────────
# Chuẩn: "subject ... object." (như wiki-nre_schema.csv và disease_schema.csv)
RELATION_DEFINITIONS = {
    # Phân loại / cấu trúc bệnh
    "isa": (
        "has_subtype",
        "The subject entity is a more specific type or subtype of the object entity. "
        "Example: Type 1 Diabetes Mellitus has_subtype Diabetes Mellitus."
    ),
    "inverse_isa": (
        "is_subtype_of",
        "The subject entity is a specific subtype or variant that falls under the "
        "broader disease category of the object entity. "
        "Example: Diabetic Ketoacidosis is_subtype_of Diabetes Mellitus."
    ),
    "member_of": (
        "member_of",
        "The subject entity is a member of a broader disease group or classification "
        "specified by the object entity. "
        "Example: Diabetes Mellitus member_of Endocrine System Diseases."
    ),
    # Etiologi & nguyên nhân
    "cause_of": (
        "cause_of",
        "The subject entity (a condition, gene, or substance) is a direct cause of "
        "the disease or complication specified by the object entity. "
        "Example: Insulin deficiency cause_of Diabetic Ketoacidosis."
    ),
    # Triệu chứng & biểu hiện lâm sàng
    "manifestation_of": (
        "manifestation_of",
        "The subject entity (a sign, symptom, or complication) is a direct clinical "
        "manifestation of the disease specified by the object entity. "
        "Example: Diabetic Neuropathy manifestation_of Diabetes Mellitus."
    ),
    "may_be_finding_of_disease": (
        "may_be_finding_of_disease",
        "The subject entity (a clinical or laboratory finding) may be observed as a "
        "characteristic finding in patients with the disease specified by the object. "
        "Example: Hyperglycemia may_be_finding_of_disease Diabetes Mellitus."
    ),
    "associated_finding_of": (
        "associated_finding_of",
        "The subject entity is a finding characteristically associated with the "
        "disease or condition specified by the object entity. "
        "Example: Glucosuria associated_finding_of Diabetes Mellitus."
    ),
    # Điều trị & thuốc
    "may_be_treated_by": (
        "may_be_treated_by",
        "The subject disease may be managed, controlled, or treated using the drug, "
        "procedure, or intervention specified by the object entity. "
        "Example: Type 2 Diabetes Mellitus may_be_treated_by Metformin."
    ),
    "has_contraindicated_drug": (
        "has_contraindicated_drug",
        "The subject disease or condition has a drug that is contraindicated — "
        "it should be avoided because it may cause harm in patients with this condition. "
        "Example: Diabetic Ketoacidosis has_contraindicated_drug Metformin."
    ),
    # Giải phẫu
    "has_finding_site": (
        "has_finding_site",
        "The subject disease has its primary pathological finding or lesion located "
        "at the anatomical site specified by the object entity. "
        "Example: Diabetic Retinopathy has_finding_site Retina."
    ),
    "disease_has_associated_anatomic_site": (
        "disease_has_associated_anatomic_site",
        "The subject disease is associated with pathological changes at the anatomical "
        "site or organ specified by the object entity. "
        "Example: Diabetic Nephropathy disease_has_associated_anatomic_site Kidney."
    ),
    "disease_has_primary_anatomic_site": (
        "disease_has_primary_anatomic_site",
        "The subject disease originates from or primarily affects the anatomical site "
        "specified by the object entity. "
        "Example: Diabetes Mellitus disease_has_primary_anatomic_site Pancreas."
    ),
    "disease_has_normal_cell_origin": (
        "disease_has_normal_cell_origin",
        "The subject disease originates from or is associated with the normal cell "
        "type specified by the object entity. "
        "Example: Type 1 Diabetes Mellitus disease_has_normal_cell_origin Beta Cell."
    ),
    "disease_has_normal_tissue_origin": (
        "disease_has_normal_tissue_origin",
        "The subject disease originates from or is associated with the normal tissue "
        "type specified by the object entity. "
        "Example: Diabetes Mellitus disease_has_normal_tissue_origin Pancreatic Islet."
    ),
    # Gene & biomarker
    "disease_has_associated_gene": (
        "disease_has_associated_gene",
        "The subject disease has a known genetic association or is linked to the gene "
        "or genome specified by the object entity. "
        "Example: Type 1 Diabetes Mellitus disease_has_associated_gene INS."
    ),
    "is_marked_by_gene_product": (
        "is_marked_by_gene_product",
        "The subject disease is characterized, diagnosed, or identified by the "
        "presence or altered expression of the gene product or biomarker specified by "
        "the object entity. "
        "Example: Type 1 Diabetes Mellitus is_marked_by_gene_product Insulin."
    ),
    "associated_with_malfunction_of_gene_product": (
        "associated_with_malfunction_of_gene_product",
        "The subject disease is associated with a malfunction, mutation, or "
        "dysfunction of the gene product specified by the object entity. "
        "Example: Diabetes Mellitus associated_with_malfunction_of_gene_product Insulin Receptor."
    ),
    # Mối liên hệ bệnh - bệnh
    "associated_with": (
        "associated_with",
        "The subject disease or condition is clinically or pathologically associated "
        "with the entity specified by the object. "
        "Example: Diabetes Mellitus associated_with Obesity."
    ),
    "associated_condition_of": (
        "associated_condition_of",
        "The subject entity is a known associated condition that commonly co-occurs "
        "with the disease specified by the object entity. "
        "Example: Hypertension associated_condition_of Diabetes Mellitus."
    ),
    "may_be_associated_disease_of_disease": (
        "may_be_associated_disease_of_disease",
        "The subject disease may be epidemiologically or pathophysiologically "
        "associated with the disease specified by the object entity. "
        "Example: Coronary Artery Disease may_be_associated_disease_of_disease Diabetes Mellitus."
    ),
    "clinically_associated_with": (
        "clinically_associated_with",
        "The subject entity has a demonstrated clinical relationship or co-occurrence "
        "with the entity specified by the object in clinical practice. "
        "Example: Insulin Resistance clinically_associated_with Type 2 Diabetes Mellitus."
    ),
    "co-occurs_with": (
        "co-occurs_with",
        "The subject disease or condition tends to appear simultaneously in the same "
        "patient or population as the condition specified by the object entity. "
        "Example: Dyslipidemia co-occurs_with Diabetes Mellitus."
    ),
    "related_to": (
        "related_to",
        "The subject entity has a general medical or biological relationship with the "
        "entity specified by the object. Used when a more specific relation is not defined. "
        "Example: Glucose Intolerance related_to Diabetes Mellitus."
    ),
    "component_of": (
        "component_of",
        "The subject disease or condition is a component or part of the larger disease "
        "complex or syndrome specified by the object entity. "
        "Example: Hyperglycemia component_of Metabolic Syndrome."
    ),
    # Chẩn đoán phân biệt
    "ddx": (
        "differential_diagnosis_of",
        "The subject disease should be considered in the differential diagnosis when "
        "the disease specified by the object is suspected, as they share overlapping features. "
        "Example: Diabetes Insipidus differential_diagnosis_of Diabetes Mellitus."
    ),
    # Đánh giá
    "has_evaluation": (
        "has_evaluation",
        "The subject disease is assessed or monitored using the clinical evaluation, "
        "test, or measurement specified by the object entity. "
        "Example: Diabetes Mellitus has_evaluation HbA1c Test."
    ),
    # Phân loại
    "isa_rq": (
        "is_classified_as",
        "The subject entity is formally classified or categorized under the broader "
        "category or system specified by the object entity. "
        "Example: Diabetes Mellitus is_classified_as Metabolic Disease."
    ),
}


# ═════════════════════════════════════════════════════════════════════════════
# STEP 1: Lấy dữ liệu từ UMLS
# ═════════════════════════════════════════════════════════════════════════════

def api_get(url: str, params: dict) -> dict | None:
    params = dict(params)
    params["apiKey"] = API_KEY
    time.sleep(SLEEP)
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def paginate(url: str, extra: dict | None = None):
    params = dict(extra or {})
    params["pageSize"] = PAGE_SIZE
    page = 1
    while True:
        params["pageNumber"] = page
        data = api_get(url, params)
        if data is None:
            break
        node = data.get("result")
        if isinstance(node, list):
            items = node
        elif isinstance(node, dict):
            items = node.get("results") or []
        else:
            break
        if not items:
            break
        yield from items
        if len(items) < PAGE_SIZE:
            break
        page += 1


def fetch_raw_relations(cui: str) -> list[dict]:
    """Lấy tất cả bản ghi quan hệ của một CUI từ UMLS API."""
    url = f"{BASE_URL}/content/{VERSION}/CUI/{cui}/relations"
    records = []
    for rel in paginate(url):
        records.append({
            "relation_label":            rel.get("relationLabel", "").strip(),
            "additional_relation_label": rel.get("additionalRelationLabel", "").strip(),
            "related_id":               rel.get("relatedId", ""),
            "related_id_name":          rel.get("relatedIdName", "").strip(),
        })
    return records


def fetch_definition(cui: str) -> str:
    """Lấy định nghĩa UMLS của một CUI."""
    url = f"{BASE_URL}/content/{VERSION}/CUI/{cui}/definitions"
    preferred = {"NCI", "MSH", "SNOMEDCT_US", "HPO"}
    defs = list(paginate(url))
    if not defs:
        return ""
    for d in defs:
        if d.get("rootSource", "") in preferred:
            return d.get("value", "").strip()
    return defs[0].get("value", "").strip()


def step1_fetch(cui: str) -> dict:
    print(f"[STEP 1] Fetching all relations for {cui} from UMLS...")
    records = fetch_raw_relations(cui)
    print(f"         -> {len(records)} relation records retrieved.")

    # Gom unique relation types với tên liên kết
    seen: set[tuple] = set()
    unique_relations = []
    for r in records:
        key = (r["relation_label"], r["additional_relation_label"])
        if key not in seen:
            seen.add(key)
            unique_relations.append({
                "relation_label":            r["relation_label"],
                "additional_relation_label": r["additional_relation_label"],
            })

    print(f"         -> {len(unique_relations)} unique relation types found.")

    # Lấy định nghĩa của bệnh gốc
    definition = fetch_definition(cui)

    result = {
        "cui":                   cui,
        "name":                  "Diabetes Mellitus",
        "definition":            definition,
        "total_relation_records": len(records),
        "unique_relation_types": sorted(
            unique_relations,
            key=lambda x: (x["relation_label"], x["additional_relation_label"])
        ),
    }

    OUTPUT_DIR.mkdir(exist_ok=True)
    with RAW_FILE.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"         -> Saved to {RAW_FILE}")
    return result


# ═════════════════════════════════════════════════════════════════════════════
# STEP 2: Lọc & tạo file schema CSV
# ═════════════════════════════════════════════════════════════════════════════

def step2_build_schema(raw: dict):
    print("\n[STEP 2] Filtering and building diabetes_schema.csv...")

    rows: list[tuple[str, str]] = []
    seen_relations: set[str] = set()

    for entry in raw["unique_relation_types"]:
        top   = entry["relation_label"]
        extra = entry["additional_relation_label"]

        # Loại top-level labels không có giá trị lâm sàng
        if top in EXCLUDED_LABELS:
            continue
        # Loại additional labels kỹ thuật
        if extra in EXCLUDED_ADDITIONAL:
            continue

        # Xác định key tra cứu định nghĩa
        lookup_key = extra if extra else top.lower()

        # Trường hợp đặc biệt: RQ + isa
        if top == "RQ" and extra == "isa":
            lookup_key = "isa_rq"

        if lookup_key not in RELATION_DEFINITIONS:
            continue

        relation_name, definition = RELATION_DEFINITIONS[lookup_key]

        # Tránh trùng lặp tên quan hệ
        if relation_name in seen_relations:
            continue
        seen_relations.add(relation_name)

        rows.append((relation_name, definition))

    # Sắp xếp theo nhóm (dựa vào thứ tự trong RELATION_DEFINITIONS)
    order = list(RELATION_DEFINITIONS.keys())
    key_to_rel = {v[0]: k for k, v in RELATION_DEFINITIONS.items()}
    rows.sort(key=lambda r: order.index(key_to_rel.get(r[0], r[0]))
              if key_to_rel.get(r[0], r[0]) in order else 999)

    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    with SCHEMA_FILE.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(["relation", "definition"])
        writer.writerows(rows)

    print(f"         -> {len(rows)} relations written to {SCHEMA_FILE}")
    print("\n[Relations included in schema]:")
    for name, _ in rows:
        print(f"   - {name}")


# ═════════════════════════════════════════════════════════════════════════════
# Main
# ═════════════════════════════════════════════════════════════════════════════

def main():
    if not API_KEY:
        raise SystemExit(
            "ERROR: UMLS_API_KEY is not set.\n"
            "Run: $env:UMLS_API_KEY='your_api_key'"
        )

    raw = step1_fetch(SEED_CUI)
    step2_build_schema(raw)
    print(f"\nDone! Schema saved to: {SCHEMA_FILE.resolve()}")


if __name__ == "__main__":
    main()
