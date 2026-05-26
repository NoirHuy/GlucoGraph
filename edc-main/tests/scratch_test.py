import sys
import os
import csv
import json
import requests

# Add the parent directory (edc-main root) to system paths dynamically
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(base_dir)

from edc.semantic_validator import SemanticValidator

schema_path = os.path.join(base_dir, 'schemas/disease/diabetes_schema.csv')
entity_type_schema_path = os.path.join(base_dir, 'schemas/disease/diabetes_entity_type_schema.csv')

schema = {}
reader = csv.reader(open(schema_path, "r", encoding="utf-8"))
for row in reader:
    if len(row) < 2: continue
    schema[row[0]] = ",".join(row[1:])

entity_type_schema = {}
reader = csv.reader(open(entity_type_schema_path, "r", encoding="utf-8"))
for row in reader:
    if len(row) < 2: continue
    entity_type_schema[row[0]] = ",".join(row[1:])

from sentence_transformers import SentenceTransformer
print("Loading embedder...")
embedder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

print("Initializing validator...")
validator = SemanticValidator(
    relation_schema=schema,
    entity_type_schema=entity_type_schema,
    embedder=embedder,
    oie_few_shot_file_path=os.path.join(base_dir, 'few_shot_examples/diabetic/oie_few_shot_examples.txt'),
    sd_few_shot_file_path=os.path.join(base_dir, 'few_shot_examples/diabetic/sd_few_shot_examples_with_entities.txt')
)

triples = [
    ['weight loss', 'may be treated by', 'increased glycemia'],
    ['weight loss', 'may be treated by', 'dyslipidemia'],
    ['weight loss', 'may be treated by', 'nonalcoholic fatty liver disease'],
    ['weight loss', 'may be treated by', 'osteoarthritis'],
    ['Type 2 Diabetes', 'may be treated by', 'management'],
    ['Type 2 Diabetes', 'may be treated by', 'proposed interventions'],
    ['glycemic targets', 'has evaluation', 'Type 2 Diabetes']
]

for triple in triples:
    subj, rel, obj = triple
    s_type = validator._predict_entity_type(subj)
    o_type = validator._predict_entity_type(obj)
    print(f"\nTriple: {triple}")
    print(f"Predicted Subject Type ({subj}): {s_type}")
    print(f"Predicted Object Type ({obj}): {o_type}")
    validated = validator.validate_triple(triple, "Weight loss improves many of the cardiometabolic and biomechanical components of adiposity-based chronic disease, including increased glycemia, dyslipidemia, elevated blood pressure, cardiovascular disease, nonalcoholic fatty liver disease, sleep apnea, and osteoarthritis.")
    print(f"Validated Triple: {validated}")

print("\n--- Testing Type-Based Swapping ---")
type_triple = ['Metformin', 'may be treated by', 'Type 2 Diabetes']
s_type, o_type = 'Drug', 'Disease'
corrected_triple, c_s, c_o = validator.try_auto_correct_direction_by_type(type_triple, s_type, o_type)
print(f"Original: {type_triple} with types ({s_type}, {o_type})")
print(f"Corrected: {corrected_triple} with types ({c_s}, {c_o})")

print("\n--- Testing SchemaDefiner Leak Prevention Guard ---")
from edc.schema_definition import SchemaDefiner
# Instantiate with dummy OpenAI model to test bypassing of LLM calls
sd = SchemaDefiner(openai_model="dummy-model", use_entity_types=True)
result = sd.define_schema(
    input_text_str="The American Association of Clinical Endocrinology published the first iteration.",
    extracted_triplets_list=[],
    few_shot_examples_str="dummy few-shot",
    prompt_template_str="dummy template {text} {relations} {triples}"
)
print(f"SchemaDefiner Result with Empty Input: {result}")
assert result == {"_entries": []}, "Error: SchemaDefiner did not return empty entries!"
print("SchemaDefiner Leak Prevention Guard successfully verified!")

print("\n--- Testing UMLSNormalizer Caching & API Mapping ---")
from edc.post_processing import UMLSNormalizer

# Create a normalizer with a mock/temp cache file
temp_cache_path = os.path.join(base_dir, "output/test_umls_cache.json")
if os.path.exists(temp_cache_path):
    os.remove(temp_cache_path)

# Let's mock requests.get to return a mock search response and a mock detail response
original_get = requests.get

def mock_get(url, *args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code=200):
            self.json_data = json_data
            self.status_code = status_code
        def json(self):
            return self.json_data
        def raise_for_status(self):
            pass

    # Mock search with multiple candidates to test smart reranking & LOINC / length penalties
    if "search/current" in url:
        query_string = kwargs.get("params", {}).get("string", "")
        query_lower = query_string.lower()
        if "diabetes" in query_lower:
            return MockResponse({
                "result": {
                    "results": [
                        {"ui": "C0011849", "name": "Diabetes Mellitus"}
                    ]
                }
            })
        elif "prandial insulin" in query_lower:
            # Returns LOINC caret string that should be penalized/rejected
            return MockResponse({
                "result": {
                    "results": [
                        {"ui": "C1234567", "name": "Insulin^post meal:SCnc:Pt:Ser/Plas:Qn"}
                    ]
                }
            })
        elif "correction dose" in query_lower:
            # Returns a long questionnaire-like string that should be rejected by word length penalty
            return MockResponse({
                "result": {
                    "results": [
                        {"ui": "C5432109", "name": "Heterogeneity Correction Used in Dose Calculation Question"}
                    ]
                }
            })
        elif "insulin" in query_lower:
            # We return "Insulin measurement" first (to mock UTS default rank)
            # and "Insulin" second. Smart reranking must select "Insulin"!
            return MockResponse({
                "result": {
                    "results": [
                        {"ui": "C0200057", "name": "Insulin measurement"},
                        {"ui": "C0021641", "name": "Insulin"}
                    ]
                }
            })
            
    # Mock content CUI detail
    elif "content/current/CUI/" in url:
        cui = url.split("/")[-1].split("?")[0]
        if cui == "C0011849":
            return MockResponse({
                "result": {
                    "semanticTypes": [
                        {"name": "Disease or Syndrome", "uri": "https://uts-ws.nlm.nih.gov/rest/semantic-network/current/TUI/T047"}
                    ]
                }
            })
        elif cui == "C0021641":
            return MockResponse({
                "result": {
                    "semanticTypes": [
                        {"name": "Pharmacologic Substance", "uri": "https://uts-ws.nlm.nih.gov/rest/semantic-network/current/TUI/T121"}
                    ]
                }
            })
        elif cui == "C0200057":
            return MockResponse({
                "result": {
                    "semanticTypes": [
                        {"name": "Laboratory Procedure", "uri": "https://uts-ws.nlm.nih.gov/rest/semantic-network/current/TUI/T059"}
                    ]
                }
            })

    return MockResponse({}, 404)

requests.get = mock_get

# Instantiate the normalizer with a dummy API key so it queries
normalizer = UMLSNormalizer(api_key="mock_key", cache_path=temp_cache_path)

# Query "diabetes" and "insulin"
res_diabetes = normalizer.query_term("diabetes")
print(f"Mapped 'diabetes': {res_diabetes}")
assert res_diabetes["cui"] == "C0011849"
assert res_diabetes["canonical"] == "Diabetes Mellitus"
assert "T047" in res_diabetes["semantic_type"]

# Query "insulin" to test Smart Reranking (must pick "Insulin" C0021641 over "Insulin measurement")
res_insulin = normalizer.query_term("insulin")
print(f"Mapped 'insulin': {res_insulin}")
assert res_insulin["cui"] == "C0021641", f"Error: Smart reranking failed! Mapped to: {res_insulin}"
assert "T121" in res_insulin["semantic_type"]
print("Smart lexical reranking verified successfully!")

# Query "correction dose" to test word mismatch penalty and rejection
res_corr = normalizer.query_term("correction dose")
print(f"Mapped 'correction dose': {res_corr}")
assert res_corr["cui"] == "NONE", "Error: word mismatch questionnaire concept was not rejected!"
assert res_corr["canonical"] == "correction dose"
print("Low-confidence overly complex questionnaire concept rejection verified successfully!")

# Query "prandial insulin" to test LOINC caret/colon concept rejection
res_prandial = normalizer.query_term("prandial insulin")
print(f"Mapped 'prandial insulin': {res_prandial}")
assert res_prandial["cui"] == "NONE", "Error: LOINC concept with caret was not rejected!"
assert res_prandial["canonical"] == "prandial insulin"
print("LOINC caret concept rejection verified successfully!")

# Verify that the cache saved correctly
assert os.path.exists(temp_cache_path), "Cache file was not saved!"
with open(temp_cache_path, "r", encoding="utf-8") as f:
    cache_content = json.load(f)
assert "diabetes" in cache_content, "Cache does not contain 'diabetes'!"
print("On-disk cache save verified successfully!")

# Test normalizing a full file
temp_input_path = os.path.join(base_dir, "output/test_canon_kg.txt")
temp_output_json = os.path.join(base_dir, "output/test_canon_kg_umls.json")
temp_output_txt = os.path.join(base_dir, "output/test_canon_kg_umls.txt")

with open(temp_input_path, "w", encoding="utf-8") as f:
    f.write("[['diabetes', 'may be treated by', 'insulin']]\n")

normalizer.normalize_file(temp_input_path, temp_output_json, temp_output_txt)

# Read results back
with open(temp_output_txt, "r", encoding="utf-8") as f:
    txt_content = f.read().strip()
print(f"UMLS Plain Text Mapped output: {txt_content}")
assert "Diabetes Mellitus" in txt_content
assert "Insulin" in txt_content

with open(temp_output_json, "r", encoding="utf-8") as f:
    json_content = json.load(f)
print(f"UMLS Structured JSON Mapped output: {json.dumps(json_content, indent=2)}")
assert json_content[0]["umls_mapped_triplets"][0]["subject"]["cui"] == "C0011849"

# 1. Test prefix stripping and atomicity in validator
print("\n--- Testing Atomicity & Prefix Stripping in Validator ---")
raw_inst = ['Instruct the patient and family to take an active role', 'may be treated by', 'metformin']
assert validator.validate_triple(raw_inst, "Instruct the patient and family to take an active role") is None, "Error: Validator did not block non-atomic instruction sentence!"
print("Successfully blocked non-atomic verbose instruction sentence!")

raw_noise = ['RNAx Metformin', 'may be treated by', 'Type 2 Diabetes']
cleaned_noise = validator.validate_triple(raw_noise, "RNAx Metformin may be treated by Type 2 Diabetes")
print(f"Original noise triple: {raw_noise} -> Cleaned: {cleaned_noise}")
assert cleaned_noise == ['Type 2 Diabetes', 'may be treated by', 'Metformin'], "Error: Prefix was not stripped correctly!"
print("Ontology prefix noise successfully stripped from validator!")

# 2. Test ontology stripping in normalizer
res_noise = normalizer.query_term("[RNAx] diabetes")
print(f"Mapped '[RNAx] diabetes': {res_noise}")
assert res_noise["cui"] == "C0011849"
print("UMLSNormalizer successfully stripped prefix noise before API query!")

# 3. Comprehensive Clinical NLP Regression Tests (The 4 Error Categories)
print("\n--- Testing Clinical/NLP Error Regression Cases ---")

# Category 1: The Comparison Trap (durations/time ranges and adjective comparison)
c1_dur1 = ['Regular insulin', 'is a', '30 to 60 minutes']
c1_dur2 = ['Regular insulin', 'is a', '6 to 8 hours']
c1_adj = ['glycemic control', 'has titration rule', 'less predictable']
c1_gen = ['Regular insulin', 'is a', 'any other insulin']

assert validator.validate_triple(c1_dur1) is None, "Error: Did not block duration '30 to 60 minutes'"
assert validator.validate_triple(c1_dur2) is None, "Error: Did not block duration '6 to 8 hours'"
assert validator.validate_triple(c1_adj) is None, "Error: Did not block adjective comparative 'less predictable'"
assert validator.validate_triple(c1_gen) is None, "Error: Did not block generic phrase 'any other insulin'"
print("Category 1 (Comparison Trap - Durations & Comparatives) successfully blocked!")

# Category 2: Logic Reversal & Pathology Hierarchy (Treated-by Drug domain constraint)
c2_rev = ['rapid-acting insulins', 'treated by', 'insulin lispro']
corrected_trip, c_s, c_o = validator.try_auto_correct_direction_by_type(c2_rev, "Drug", "Drug")
assert corrected_trip is None, "Error: Should discard 'treated by' between two drugs"

c2_adv = ['Regular insulin', 'has adverse effect', 'insulin lispro']
corr_adv, c_as, c_ao = validator.try_auto_correct_direction_by_type(c2_adv, "Drug", "Drug")
assert corr_adv is None, "Error: Should discard 'has adverse effect' with a Drug object"

c2_obs = ['obesity', 'treated by', 'higher doses']
# higher doses is a comparative adjective phrase, validator blocks it early:
assert validator.validate_triple(c2_obs) is None, "Error: obesity treated by higher doses was not blocked"
print("Category 2 (Logic Reversal / Type Constraint Violations) successfully blocked/discarded!")

# Category 3: Premixed Insulin / Compound Drugs (Isophane treated by Regular)
c3_prem = ['insulin isophane', 'treated by', 'regular insulin']
corr_prem, c_ps, c_po = validator.try_auto_correct_direction_by_type(c3_prem, "Drug", "Drug")
assert corr_prem is None, "Error: Should discard premixed drug 'treated by' violations"
print("Category 3 (Compound/Premixed drug Treated-by violations) successfully discarded!")

# Category 4: Atomicity & Nursing Process Leakage (Math formulas & verb/procedure objects)
c4_math = ['blood glucose level', 'has titration rule', '1800/total daily dose of insulin']
c4_proc1 = ['rapid-acting insulin', 'has adverse effect', 'periodic pulmonary examinations']
c4_proc2 = ['prandial insulin', 'has titration rule', 'adjusted for anticipated meal content']

# Math formula blocked early:
assert validator.validate_triple(c4_math) is None, "Error: Did not block mathematical formula"
# Verb phrase starting with action word blocked early:
assert validator.validate_triple(c4_proc2) is None, "Error: Did not block clinical workflow action phrase"
# Medical procedure 'periodic pulmonary examinations' violates 'has adverse effect' range:
corr_proc1, c_pr_s, c_pr_o = validator.try_auto_correct_direction_by_type(c4_proc1, "Drug", "Treatment Procedure")
assert corr_proc1 is None, "Error: Should discard Treatment Procedure as adverse effect of drug"
print("Category 4 (Atomicity & Nursing Process Leakage) successfully blocked/discarded!")

# Clean up
requests.get = original_get
if os.path.exists(temp_cache_path): os.remove(temp_cache_path)
if os.path.exists(temp_input_path): os.remove(temp_input_path)
if os.path.exists(temp_output_json): os.remove(temp_output_json)
if os.path.exists(temp_output_txt): os.remove(temp_output_txt)

print("UMLSNormalizer Verification completed successfully!")
