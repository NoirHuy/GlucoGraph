import json
import os

filepath = r"E:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject\BioRED\Test.BioC.JSON"

with open(filepath, "r", encoding="utf-8") as f:
    data = json.load(f)

print("Source:", data.get("source"))
print("Date:", data.get("date"))
print("Total documents:", len(data.get("documents", [])))

if data.get("documents"):
    doc = data["documents"][0]
    print("\nKeys in a document:", list(doc.keys()))
    print("Passages count:", len(doc.get("passages", [])))
    print("Relations count:", len(doc.get("relations", [])))
    if doc.get("relations"):
        print("Example relation:", doc["relations"][0])

# Let's count how many documents have diabetes terms or annotations
diabetes_mesh_prefixes = ["D00392", "D003920", "D003922", "D003924", "D003925"]
diabetes_docs_mesh = []
diabetes_docs_text = []

for idx, doc in enumerate(data.get("documents", [])):
    has_mesh = False
    has_text = False
    
    # Check annotations
    for passage in doc.get("passages", []):
        for annotation in passage.get("annotations", []):
            ident = annotation.get("infons", {}).get("identifier", "")
            if ident and any(ident.startswith(prefix) for prefix in diabetes_mesh_prefixes):
                has_mesh = True
                break
        if has_mesh:
            break
            
    # Check text keywords
    text_content = ""
    for passage in doc.get("passages", []):
        text_content += " " + passage.get("text", "")
    text_content_lower = text_content.lower()
    if "diabetes" in text_content_lower or "diabetic" in text_content_lower or "insulin" in text_content_lower:
        has_text = True
        
    if has_mesh:
        diabetes_docs_mesh.append(idx)
    if has_text:
        diabetes_docs_text.append(idx)

print(f"\nDocuments with diabetes MeSH ID: {len(diabetes_docs_mesh)}")
print(f"Documents with diabetes keywords in text: {len(diabetes_docs_text)}")
print(f"Overlap: {len(set(diabetes_docs_mesh) & set(diabetes_docs_text))}")
