import json
import os

filepath = r"E:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject\BioRED\Test.BioC.JSON"

with open(filepath, "r", encoding="utf-8") as f:
    data = json.load(f)

doc_id = "27464336"
target_doc = None
for doc in data.get("documents", []):
    if doc.get("id") == doc_id:
        target_doc = doc
        break

if target_doc:
    print(f"--- Document {doc_id} ---")
    
    # Print all annotations and their identifiers
    print("Annotations:")
    annotations_set = set()
    for passage in target_doc.get("passages", []):
        for ann in passage.get("annotations", []):
            ident = ann.get("infons", {}).get("identifier", "")
            text = ann.get("text", "")
            print(f"  ID: {ann.get('id')} | Ident: {ident} | Text: {text}")
            if ident:
                annotations_set.add(ident)
                
    print("\nRelations:")
    for rel in target_doc.get("relations", []):
        infons = rel.get("infons", {})
        e1 = infons.get("entity1", "")
        e2 = infons.get("entity2", "")
        rtype = infons.get("type", "")
        print(f"  entity1: {e1} (in annotations: {e1 in annotations_set}) | entity2: {e2} (in annotations: {e2 in annotations_set}) | type: {rtype}")
else:
    print(f"Document {doc_id} not found.")
