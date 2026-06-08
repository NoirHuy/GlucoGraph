import sys
import os
import json
import re

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

# Load .env variables
try:
    with open(os.path.join(os.path.dirname(__file__), '../.env'), 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                os.environ[k] = v.strip('"').strip("'")
except Exception as e:
    print("Warning loading .env:", e)

from app.services.cdss import get_all_cdss_nodes, chunk_match_entities, call_llm_api

clinical_text = (
    "Một bệnh nhân nam 56 tuổi đến khám vì tiểu nhiều lần trong ngày, đặc biệt về đêm, kèm theo khát nước liên tục trong khoảng 3 tháng gần đây. "
    "Bệnh nhân cho biết thường xuyên cảm thấy mệt mỏi, giảm khả năng tập trung trong công việc và gần đây xuất hiện tình trạng nhìn mờ. "
    "Tiền sử gia đình ghi nhận cha ruột mắc đái tháo đường type 2. Bệnh nhân có BMI 31 kg/m². Kết quả xét nghiệm cho thấy đường huyết lúc đói là 156 mg/dL, "
    "HbA1c 8,2% và đường huyết ngẫu nhiên 245 mg/dL."
)

kg_nodes = get_all_cdss_nodes()

# Run Stage 1a extraction
print("--- Running Extraction (Stage 1a) ---")
extraction_prompt = f"""You are a medical translation assistant. Extract all clinical concepts, symptoms, diseases, drugs, and key patient states mentioned in the clinical scenario below and translate them into standard English medical terms.
Clinical scenario: "{clinical_text}"
Return ONLY a valid JSON list of objects representing these English medical terms, each with a "term" and a "type" (which must be either "Disease", "Drug", "Symptom", or "Concept").
"""
raw_extraction = call_llm_api(extraction_prompt, response_format="text", model_size="8b")
bracket_match = re.search(r'\[.*?\]', raw_extraction, re.DOTALL)
extracted_terms = json.loads(bracket_match.group()) if bracket_match else []
print("Extracted Terms:", extracted_terms)

# Trace Candidate Generation (Stage 1b)
print("\n--- Running Candidate Generation (Stage 1b) ---")
candidates = set()
for term in extracted_terms:
    term_str = term.get("term", "") if isinstance(term, dict) else str(term)
    term_lower = term_str.lower().strip()
    term_candidates = []
    # Find any node ID that contains the term, or is contained within the term
    for node in kg_nodes:
        node_lower = node.lower()
        matched_cond = False
        if term_lower in node_lower or node_lower in term_lower:
            candidates.add(node)
            term_candidates.append(node)
            matched_cond = True
        else:
            term_words = set(term_lower.split())
            node_words = set(re.findall(r'\w+', node_lower)) # using word boundary regex to clean punctuation
            overlap = term_words.intersection(node_words)
            overlap = {w for w in overlap if w not in {"disease", "diseases", "mellitus", "type", "in", "of", "and", "or", "patients", "with"}}
            if len(overlap) >= 2:
                candidates.add(node)
                term_candidates.append(node)
                matched_cond = True
    print(f"Term '{term_str}' generated candidates: {term_candidates}")

print("\nTotal candidate count:", len(candidates))
print("Is 'Diabetes Mellitus, Non-Insulin-Dependent' in candidates?", "Diabetes Mellitus, Non-Insulin-Dependent" in candidates)
print("Is 'Diabetes Mellitus, Insulin-Dependent' in candidates?", "Diabetes Mellitus, Insulin-Dependent" in candidates)
print("Is 'Diabetes Mellitus' in candidates?", "Diabetes Mellitus" in candidates)
