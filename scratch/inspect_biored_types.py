import json
import os

filepath = r"E:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject\BioRED\Test.BioC.JSON"

with open(filepath, "r", encoding="utf-8") as f:
    data = json.load(f)

entity_types = set()
relation_types = set()

for doc in data.get("documents", []):
    for passage in doc.get("passages", []):
        for ann in passage.get("annotations", []):
            etype = ann.get("infons", {}).get("type", "")
            if etype:
                entity_types.add(etype)
                
    for rel in doc.get("relations", []):
        rtype = rel.get("infons", {}).get("type", "")
        if rtype:
            relation_types.add(rtype)

print("Unique Entity Types in BioRED:", list(entity_types))
print("Unique Relation Types in BioRED:", list(relation_types))
