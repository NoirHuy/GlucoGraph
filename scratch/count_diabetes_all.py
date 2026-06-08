import json
import os

biored_dir = r"E:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject\BioRED"
files = ["Train.BioC.JSON", "Dev.BioC.JSON", "Test.BioC.JSON"]

diabetes_mesh_prefixes = ["D00392", "D003920", "D003922", "D003924", "D003925"]

for fname in files:
    filepath = os.path.join(biored_dir, fname)
    if not os.path.exists(filepath):
        print(f"File {fname} not found")
        continue
        
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    total_docs = len(data.get("documents", []))
    
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
            diabetes_docs_mesh.append(doc["id"])
        if has_text:
            diabetes_docs_text.append(doc["id"])
            
    print(f"\n--- {fname} ---")
    print(f"Total documents: {total_docs}")
    print(f"Diabetes by MeSH: {len(diabetes_docs_mesh)}")
    print(f"Diabetes by Text Keywords: {len(diabetes_docs_text)}")
    print(f"Overlap: {len(set(diabetes_docs_mesh) & set(diabetes_docs_text))}")
