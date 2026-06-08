import json
import os
import sys

# Reconfigure encoding to avoid UnicodeEncodeError on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

output_dir = r"e:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject\edc-main\output"

def check():
    path = r"e:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject\edc-main\output\Type_2_Diabetes_Mellitus\debated_results\canon_kg_debated_packed.json"
    if not os.path.exists(path):
        print("File not found")
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("=== NODES IN PACKED JSON ===")
    for n in data.get("nodes", []):
        nid = n.get("id", "")
        if "glucose" in nid.lower() or "exercise" in nid.lower():
            print(f"Node: {nid} | Labels: {n.get('labels')} | CUI: {n.get('properties', {}).get('umls_cui')} | Canonical: {n.get('properties', {}).get('umls_canonical')}")

    print("\n=== RELATIONSHIPS IN PACKED JSON ===")
    for r in data.get("relationships", []):
        start = r.get("start", "")
        end = r.get("end", "")
        rtype = r.get("type", "")
        if ("glucose" in start.lower() or "glucose" in end.lower()) and ("exercise" in start.lower() or "exercise" in end.lower()):
            print(f"Relation: [{start}] -[{rtype}]-> [{end}]")

if __name__ == "__main__":
    check()
