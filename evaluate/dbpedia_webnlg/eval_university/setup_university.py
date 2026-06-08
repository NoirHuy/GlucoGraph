import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Paths
base_dir = r"E:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject\evaluate\dbpedia_webnlg"
target_dir = os.path.join(base_dir, "eval_university")
schema_dir = os.path.join(target_dir, "schemas")
data_dir = os.path.join(target_dir, "data")

os.makedirs(schema_dir, exist_ok=True)
os.makedirs(data_dir, exist_ok=True)

# 1. Parse Ontology JSON and write CSV schemas
ontology_path = os.path.join(base_dir, "ontologies", "1_university_ontology.json")
print(f"Reading ontology from: {ontology_path}")
with open(ontology_path, "r", encoding="utf-8") as f:
    ontology = json.load(f)

# Relation Schema CSV
relation_csv_path = os.path.join(schema_dir, "relation_schema.csv")
print(f"Writing relation schema to: {relation_csv_path}")
with open(relation_csv_path, "w", encoding="utf-8") as f:
    f.write("relation,definition\n")
    for rel in ontology.get("relations", []):
        pid = rel.get("pid", "")
        domain = rel.get("domain", "Unknown")
        range_val = rel.get("range", "Unknown")
        # Generate clean definition matching domain and range
        definition = f"Represents the relation '{pid}' between a {domain} and a {range_val}."
        # Quote definition to handle commas
        f.write(f'{pid},"{definition}"\n')

# Entity Type Schema CSV
entity_type_csv_path = os.path.join(schema_dir, "entity_type_schema.csv")
print(f"Writing entity type schema to: {entity_type_csv_path}")
with open(entity_type_csv_path, "w", encoding="utf-8") as f:
    f.write("entity_type,definition\n")
    for concept in ontology.get("concepts", []):
        qid = concept.get("qid", "")
        definition = f"Represents a {concept.get('label', qid)} concept."
        f.write(f'{qid},"{definition}"\n')

# 2. Extract input sentences from test JSONL
test_path = os.path.join(base_dir, "test", "ont_1_university_test.jsonl")
input_txt_path = os.path.join(data_dir, "inputs.txt")
print(f"Reading test inputs from: {test_path}")
print(f"Writing inputs to: {input_txt_path}")

input_lines = []
with open(test_path, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            obj = json.loads(line)
            # Clean text (remove excessive whitespaces)
            sent = obj.get("sent", "").replace("\r", " ").replace("\n", " ").strip()
            sent = re.sub(r"\s+", " ", sent)
            input_lines.append(sent)

with open(input_txt_path, "w", encoding="utf-8") as f:
    for line in input_lines:
        f.write(line + "\n")

# 3. Extract ground truth references
gt_path = os.path.join(base_dir, "ground_truth", "ont_1_university_ground_truth.jsonl")
ref_txt_path = os.path.join(data_dir, "references.txt")
print(f"Reading ground truth from: {gt_path}")
print(f"Writing references to: {ref_txt_path}")

ref_lines = []
with open(gt_path, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            obj = json.loads(line)
            raw_triples = obj.get("triples", [])
            triples_list = []
            for t in raw_triples:
                sub = t.get("sub", "").replace("_", " ").strip()
                rel = t.get("rel", "").strip()
                obj_val = t.get("obj", "").replace("_", " ").strip()
                # Remove quotes from literal objects if present
                obj_val = obj_val.strip('"')
                triples_list.append([sub, rel, obj_val])
            ref_lines.append(triples_list)

with open(ref_txt_path, "w", encoding="utf-8") as f:
    for ref_list in ref_lines:
        f.write(str(ref_list) + "\n")

print("Setup completed successfully!")
