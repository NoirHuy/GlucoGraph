import json
import os

biored_dir = r"E:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject\BioRED"
files = ["Train.BioC.JSON", "Dev.BioC.JSON", "Test.BioC.JSON"]

# Expanded diabetes/insulin related MeSH IDs and NCBI Gene ID for insulin
diabetes_related_identifiers = {
    # Diabetes Mellitus & subtypes
    "D003920", "D003922", "D003924", "D016640", "D011226", "D003921", "D003925",
    # Diabetic complications
    "D003928", "D003929", "D003930", "D048909", "D003927",
    # Insulin gene/protein
    "3630", # NCBI Gene ID for human INS (insulin)
}

diabetes_keywords = [
    "diabetes", "diabetic", "insulin", "hyperglycemia", "hypoglycemia", 
    "blood glucose", "glycemic", "glycaemic", "hba1c"
]

all_diabetes_docs = []

for fname in files:
    filepath = os.path.join(biored_dir, fname)
    if not os.path.exists(filepath):
        continue
        
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    for doc in data.get("documents", []):
        doc_id = doc.get("id")
        has_mesh = False
        has_keyword = False
        
        # Check annotations for MeSH IDs
        for passage in doc.get("passages", []):
            for annotation in passage.get("annotations", []):
                ident = annotation.get("infons", {}).get("identifier", "")
                if ident:
                    # check if exact match or starts with D00392/D00393
                    if ident in diabetes_related_identifiers or ident.startswith("D00392") or ident.startswith("D00393"):
                        has_mesh = True
                        break
            if has_mesh:
                break
                
        # Check text content for keywords
        text_content = " ".join([p.get("text", "") for p in doc.get("passages", [])]).lower()
        if any(kw in text_content for kw in diabetes_keywords):
            has_keyword = True
            
        if has_mesh or has_keyword:
            all_diabetes_docs.append({
                "source_file": fname,
                "doc_id": doc_id,
                "has_mesh": has_mesh,
                "has_keyword": has_keyword,
                "doc_data": doc
            })

print(f"Total diabetes-related documents found across all files: {len(all_diabetes_docs)}")
print(f"By split:")
splits = {}
for doc in all_diabetes_docs:
    splits[doc["source_file"]] = splits.get(doc["source_file"], 0) + 1
for split, count in splits.items():
    print(f" - {split}: {count}")

# Check how many relations they have in total
total_relations = sum(len(d["doc_data"].get("relations", [])) for d in all_diabetes_docs)
print(f"Total relations in these documents: {total_relations}")
