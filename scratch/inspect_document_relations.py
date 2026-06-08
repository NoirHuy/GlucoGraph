import json
import os

filepath = r"E:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject\BioRED\Test.BioC.JSON"

with open(filepath, "r", encoding="utf-8") as f:
    data = json.load(f)

# Find first document that has relations
for doc in data.get("documents", []):
    if doc.get("relations"):
        print(f"Document ID: {doc['id']}")
        
        # Build mapping from identifier/annotation-id to text
        id_to_text = {}
        concept_to_texts = {}
        for passage in doc.get("passages", []):
            for ann in passage.get("annotations", []):
                ident = ann.get("infons", {}).get("identifier", "")
                text = ann.get("text", "")
                ann_id = ann.get("id", "")
                id_to_text[ann_id] = text
                if ident:
                    if ident not in concept_to_texts:
                        concept_to_texts[ident] = set()
                    concept_to_texts[ident].add(text)
                    
        print("\nSome entity mappings (concept ID to texts):")
        for k, v in list(concept_to_texts.items())[:5]:
            print(f"  {k} -> {list(v)}")
            
        print("\nRelations:")
        for rel in doc.get("relations", [])[:5]:
            infons = rel.get("infons", {})
            e1 = infons.get("entity1", "")
            e2 = infons.get("entity2", "")
            rtype = infons.get("type", "")
            
            # Map identifiers to text
            e1_texts = list(concept_to_texts.get(e1, [e1]))
            e2_texts = list(concept_to_texts.get(e2, [e2]))
            
            print(f"  Raw: entity1={e1}, entity2={e2}, type={rtype}")
            print(f"  Mapped text combination(s):")
            for t1 in e1_texts:
                for t2 in e2_texts:
                    print(f"    ({t1}, {rtype}, {t2})")
        break
