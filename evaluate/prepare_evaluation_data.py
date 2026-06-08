import json
import os
import re
from collections import Counter

# Define paths
bioc_file = r"E:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject\BioRED\Test.BioC.JSON"
output_dir = r"E:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject\evaluate"
input_txt_path = os.path.join(output_dir, "biored_diabetes_inputs.txt")
ref_txt_path = os.path.join(output_dir, "biored_diabetes_references.txt")

# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

# Expanded diabetes/insulin related MeSH IDs and NCBI Gene ID for insulin
diabetes_related_identifiers = {
    # Diabetes Mellitus & subtypes
    "D003920", "D003922", "D003924", "D016640", "D011226", "D003921", "D003925",
    # Diabetic complications
    "D003928", "D003929", "D003930", "D048909", "D003927",
    # NCBI Gene ID for human INS (insulin)
    "3630",
}

diabetes_keywords = [
    "diabetes", "diabetic", "insulin", "hyperglycemia", "hypoglycemia", 
    "blood glucose", "glycemic", "glycaemic", "hba1c"
]

def clean_text(text):
    """Clean text to be a single line without excessive spaces."""
    if not text:
        return ""
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

ABBREVIATION_TO_PROSE = {
    "t2dm": "type 2 diabetes",
    "t2d": "type 2 diabetes",
    "gdm": "gestational diabetes",
    "ndi": "nephrogenic diabetes insipidus",
    "dm": "diabetes mellitus",
    "t1dm": "type 1 diabetes",
    "pkca": "protein kinase c alpha",
    "aqp2": "aquaporin-2",
    "ut-a1": "urea transporter ut-a1",
    "camp": "cyclic amp",
    "scr": "serum creatinine",
}

DIABETES_KEYWORDS = {
    "diabetes", "diabetic", "insulin", "glucose", "glycemic", "glycaemic", 
    "hba1c", "t2dm", "gdm", "ndi", "hyperglycemia", "hypoglycemia"
}

def is_diabetes_related(triple):
    s, r, o = triple
    s_lower = s.lower()
    o_lower = o.lower()
    for kw in DIABETES_KEYWORDS:
        if kw in s_lower or kw in o_lower:
            return True
    return False

def normalize_entity_name(name):
    cleaned = clean_text(name).lower()
    if cleaned in ABBREVIATION_TO_PROSE:
        return ABBREVIATION_TO_PROSE[cleaned]
    return name

def get_canonical_name(text_list):
    """Find the most frequent name, with tie-breakers for shortest and first."""
    if not text_list:
        return ""
    counts = Counter(text_list)
    # Sort by frequency (descending), then by length (ascending)
    sorted_texts = sorted(counts.keys(), key=lambda x: (-counts[x], len(x), text_list.index(x)))
    return clean_text(sorted_texts[0])

def main():
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
    print(f"Reading BioC dataset: {bioc_file}")
    with open(bioc_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    documents = data.get("documents", [])
    print(f"Total documents loaded: {len(documents)}")

    diabetes_docs = []
    for doc in documents:
        doc_id = doc.get("id", "")
        has_mesh = False
        has_keyword = False
        
        # Check annotations for MeSH / Gene IDs
        for passage in doc.get("passages", []):
            for ann in passage.get("annotations", []):
                ident = ann.get("infons", {}).get("identifier", "")
                if ident:
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
            diabetes_docs.append(doc)

    print(f"Filtered {len(diabetes_docs)} diabetes-related documents from Test split.")

    input_lines = []
    ref_lines = []

    for doc in diabetes_docs:
        doc_id = doc.get("id", "")
        
        # 1. Reconstruct full document text
        passage_texts = []
        for passage in doc.get("passages", []):
            text = passage.get("text", "")
            if text:
                passage_texts.append(text)
        full_text = clean_text(" ".join(passage_texts))
        input_lines.append(full_text)
        
        # 2. Build mapping of concept identifier to surface forms
        concept_to_texts = {}
        for passage in doc.get("passages", []):
            for ann in passage.get("annotations", []):
                ident = ann.get("infons", {}).get("identifier", "")
                text = ann.get("text", "").strip()
                if ident and text:
                    # Map the full composite identifier (e.g. '11793,67526')
                    if ident not in concept_to_texts:
                        concept_to_texts[ident] = []
                    concept_to_texts[ident].append(text)
                    
                    # Also map the individual identifiers if it is a list
                    idents = [i.strip() for i in re.split(r'[,;]', ident) if i.strip()]
                    if len(idents) > 1:
                        for single_id in idents:
                            if single_id not in concept_to_texts:
                                concept_to_texts[single_id] = []
                            concept_to_texts[single_id].append(text)
                    
        # Find canonical string name for each concept ID
        concept_to_canonical = {}
        for ident, text_list in concept_to_texts.items():
            concept_to_canonical[ident] = get_canonical_name(text_list)

        # 3. Process relations
        gold_triplets = []
        for rel in doc.get("relations", []):
            infons = rel.get("infons", {})
            e1 = infons.get("entity1", "")
            e2 = infons.get("entity2", "")
            rtype = infons.get("type", "")
            
            # Map identifiers to canonical text
            e1_name = concept_to_canonical.get(e1, "")
            e2_name = concept_to_canonical.get(e2, "")
            
            # Skip if we can't find names (should not happen in clean BioC)
            if not e1_name or not e2_name:
                print(f"Warning: Missing name for concept IDs: {e1} or {e2} in doc {doc_id}")
                continue
            
            # Normalize and translate abbreviation to prose
            e1_norm = normalize_entity_name(e1_name)
            e2_norm = normalize_entity_name(e2_name)
                
            gold_triplets.append([e1_norm, rtype, e2_norm])
            
        # Deduplicate triplets within the same document and filter for diabetes-related ones
        unique_triplets = []
        for trip in gold_triplets:
            if is_diabetes_related(trip):
                if trip not in unique_triplets:
                    unique_triplets.append(trip)
                
        ref_lines.append(unique_triplets)

    # Write input texts file
    with open(input_txt_path, "w", encoding="utf-8") as f:
        for line in input_lines:
            f.write(line + "\n")
    print(f"Wrote input texts to: {input_txt_path}")

    # Write reference triplets file
    with open(ref_txt_path, "w", encoding="utf-8") as f:
        for ref_list in ref_lines:
            f.write(str(ref_list) + "\n")
    print(f"Wrote reference gold triplets to: {ref_txt_path}")

if __name__ == "__main__":
    main()
