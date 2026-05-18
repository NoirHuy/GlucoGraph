"""
fetch_all_relations.py
Gọi trực tiếp UMLS API để lấy TẤT CẢ các loại quan hệ của CUI C0011849
(Diabetes Mellitus) không qua bộ lọc nào.

Output: output/all_relation_types.json
"""

import json
import time
import os
from pathlib import Path

import requests

# ── Cấu hình ────────────────────────────────────────────────────────────────
API_KEY   = os.environ.get("UMLS_API_KEY", "")
BASE_URL  = "https://uts-ws.nlm.nih.gov/rest"
VERSION   = "current"
CUI       = "C0011849"           # Diabetes Mellitus
PAGE_SIZE = 25
SLEEP     = 0.3                  # giây nghỉ giữa các request

OUTPUT_FILE = Path("output/all_relation_types.json")

# ── Helpers ──────────────────────────────────────────────────────────────────

def get(url: str, params: dict) -> dict | None:
    params["apiKey"] = API_KEY
    time.sleep(SLEEP)
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def paginate(url: str, extra_params: dict | None = None):
    """Yield từng item từ endpoint phân trang."""
    params = dict(extra_params or {})
    params["pageSize"] = PAGE_SIZE
    page = 1
    while True:
        params["pageNumber"] = page
        data = get(url, params)
        if data is None:
            break

        result_node = data.get("result")
        if isinstance(result_node, list):
            results = result_node
        elif isinstance(result_node, dict):
            results = result_node.get("results") or []
        else:
            break

        if not results:
            break

        yield from results

        if len(results) < PAGE_SIZE:
            break
        page += 1


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not API_KEY:
        raise SystemExit("ERROR: chua set UMLS_API_KEY.\n"
                         "Chay: $env:UMLS_API_KEY='your_key'")

    url = f"{BASE_URL}/content/{VERSION}/CUI/{CUI}/relations"
    print(f"Dang lay tat ca quan he cho {CUI} (Diabetes Mellitus)...")

    # Tập hợp: (relationLabel, additionalRelationLabel)
    relation_set: set[tuple[str, str]] = set()
    total = 0

    for rel in paginate(url):
        total += 1
        label     = rel.get("relationLabel", "").strip()
        add_label = rel.get("additionalRelationLabel", "").strip()
        relation_set.add((label, add_label))

    print(f"Tong so ban ghi quan he: {total}")
    print(f"So loai quan he duy nhat: {len(relation_set)}")

    # Sắp xếp để dễ đọc
    relations_sorted = sorted(relation_set, key=lambda x: (x[0], x[1]))

    # Định dạng output
    output = {
        "cui": CUI,
        "name": "Diabetes Mellitus",
        "total_relation_records": total,
        "unique_relation_types": [
            {
                "relation_label": label,
                "additional_relation_label": add_label,
            }
            for label, add_label in relations_sorted
        ],
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nDa luu vao {OUTPUT_FILE}\n")
    print("--- Danh sach cac quan he ---")
    for label, add_label in relations_sorted:
        line = f"  [{label}]"
        if add_label:
            line += f"  =>  {add_label}"
        print(line)


if __name__ == "__main__":
    main()
