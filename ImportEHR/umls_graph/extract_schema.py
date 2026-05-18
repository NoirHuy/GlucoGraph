"""
extract_schema.py
Trích xuất từ knowledge_graph.json:
  1. Danh sách các tên quan hệ (relation labels) - dùng làm Relation Schema
  2. Danh sách thực thể bệnh + định nghĩa    - dùng làm Entity Schema
Output: output/kg_schema.json
"""

import json
from pathlib import Path

INPUT_FILE  = Path("output/knowledge_graph.json")
OUTPUT_FILE = Path("output/kg_schema.json")


def main():
    with INPUT_FILE.open(encoding="utf-8") as f:
        kg = json.load(f)

    # ── 1. Relation labels (unique, sorted) ───────────────────────────────
    relation_names: set[str] = set()
    for edge in kg.get("edges", []):
        label = edge.get("relation", "").strip()
        if label:
            relation_names.add(label)

    # ── 2. Entity definitions (chỉ Disease có definition) ────────────────
    entity_definitions: list[dict] = []
    for node in kg.get("nodes", []):
        definition = node.get("definition", "").strip()
        if not definition:            # bỏ qua node không có định nghĩa
            continue
        entity_definitions.append({
            "name":       node.get("name", ""),
            "type":       node.get("type", ""),
            "definition": definition,
        })

    # ── 3. Ghi file schema ───────────────────────────────────────────────
    schema = {
        "relation_types": sorted(relation_names),
        "entities":       entity_definitions,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False, indent=2)

    print(f"[OK] Da ghi {len(entity_definitions)} thuc the va "
          f"{len(relation_names)} loai quan he vao {OUTPUT_FILE}")
    print("\n[Relations found]:")
    for r in sorted(relation_names):
        print(f"   - {r}")


if __name__ == "__main__":
    main()
