import sys
import os

# Add edc-main to path
sys.path.append(os.path.abspath('.'))

from edc.semantic_validator import SemanticValidator
import csv

schema_path = './schemas/disease/diabetes_schema.csv'
entity_type_schema_path = './schemas/disease/diabetes_entity_type_schema.csv'

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
    oie_few_shot_file_path='./few_shot_examples/diabetic/oie_few_shot_examples.txt',
    sd_few_shot_file_path='./few_shot_examples/diabetic/sd_few_shot_examples_with_entities.txt'
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
import json
from edc.umls_normalizer import UMLSNormalizer

# Create a normalizer with a mock/temp cache file
temp_cache_path = "./output/test_umls_cache.json"
if os.path.exists(temp_cache_path):
    os.remove(temp_cache_path)

# Let's mock requests.get to return a mock search response and a mock detail response
import requests
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

    # Mock search
    if "search/current" in url:
        query_string = kwargs.get("params", {}).get("string", "")
        if "diabetes" in query_string.lower():
            return MockResponse({
                "result": {
                    "results": [
                        {"ui": "C0011849", "name": "Diabetes Mellitus"}
                    ]
                }
            })
        elif "insulin" in query_string.lower():
            return MockResponse({
                "result": {
                    "results": [
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

    return MockResponse({}, 404)

requests.get = mock_get

# Instantiate the normalizer with a dummy API key so it tries to query
normalizer = UMLSNormalizer(api_key="mock_key", cache_path=temp_cache_path)

# Query "diabetes" and "insulin"
res_diabetes = normalizer.query_term("diabetes")
print(f"Mapped 'diabetes': {res_diabetes}")
assert res_diabetes["cui"] == "C0011849"
assert res_diabetes["canonical"] == "Diabetes Mellitus"
assert "T047" in res_diabetes["semantic_type"]

res_insulin = normalizer.query_term("insulin")
print(f"Mapped 'insulin': {res_insulin}")
assert res_insulin["cui"] == "C0021641"
assert "T121" in res_insulin["semantic_type"]

# Verify that the cache saved correctly
assert os.path.exists(temp_cache_path), "Cache file was not saved!"
with open(temp_cache_path, "r", encoding="utf-8") as f:
    cache_content = json.load(f)
assert "diabetes" in cache_content, "Cache does not contain 'diabetes'!"
print("On-disk cache save verified successfully!")

# Test normalizing a full file
temp_input_path = "./output/test_canon_kg.txt"
temp_output_json = "./output/test_canon_kg_umls.json"
temp_output_txt = "./output/test_canon_kg_umls.txt"

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

# Clean up
requests.get = original_get
if os.path.exists(temp_cache_path): os.remove(temp_cache_path)
if os.path.exists(temp_input_path): os.remove(temp_input_path)
if os.path.exists(temp_output_json): os.remove(temp_output_json)
if os.path.exists(temp_output_txt): os.remove(temp_output_txt)

print("UMLSNormalizer Verification completed successfully!")


