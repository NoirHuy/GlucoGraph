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
embedder = SentenceTransformer('qwen/qwen3-embedding-8b', trust_remote_code=True)

print("Initializing validator...")
validator = SemanticValidator(
    relation_schema=schema,
    entity_type_schema=entity_type_schema,
    embedder=embedder
)

triples = [
    ['weight loss', 'may be treated by', 'increased glycemia'],
    ['weight loss', 'may be treated by', 'dyslipidemia'],
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
