import json

packed_path = r"e:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject\edc-main\output\Medication_for_Diabetes_Mellitus_Treatment\debated_results\canon_kg_debated_packed.json"

with open(packed_path, "r", encoding="utf-8") as f:
    graph = json.load(f)

nodes = graph.get("nodes", [])

for n in nodes:
    if "euglycemic" in n.get("id").lower() or "euglycemic" in str(n.get("properties", {})):
        print(n)
