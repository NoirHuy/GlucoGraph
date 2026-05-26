import os
import csv
import shutil
from openai import OpenAI
from tqdm import tqdm

# Initialize client using OpenRouter
openrouter_key = os.environ.get("OPENROUTER_KEY", os.environ.get("OPENROUTER_API_KEY", ""))
if not openrouter_key:
    # If not found in current process environment, we will prompt user or fallback
    print("WARNING: OPENROUTER_KEY environment variable is empty. Make sure it is set before running.")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_key
)

# 1. Processing Relations (diabetes_schema.csv)
relation_file = "schemas/disease/diabetes_schema.csv"
relation_backup = "schemas/disease/diabetes_schema_backup.csv"

# Backup original
if os.path.exists(relation_file):
    shutil.copyfile(relation_file, relation_backup)

relations_to_define = [
    "is_a", "has_anatomic_site", "cause_of", "has_finding", "has_biomarker",
    "co_occurs_with", "treated_by", "has_adverse_effect", "contraindicated_with",
    "preferred_over", "has_evaluation", "has_titration_rule"
]

print("Generating relation definitions using meta-llama/Llama-3.1-8B-Instruct...")
new_relation_rows = []
for rel in tqdm(relations_to_define):
    clean_relation = rel.replace("_", " ")
    
    prompt = f"""You are an expert clinical ontologist and knowledge graph designer.
Write a precise, professional one-sentence medical/clinical definition for the relationship '{clean_relation}' in the context of a diabetes mellitus knowledge graph.
The definition must clearly explain how the subject and the object are linked. Start with a definition and then provide a concrete example in parentheses using diabetes concepts.
CRITICAL: Do NOT use underscores (like 'is_a', 'treated_by', 'caused_by', etc.) in the definition text or in the examples; write them as natural English words with spaces (e.g. use 'is a', 'treated by', 'caused by').

Provide ONLY the definition text. Do not use quotes, markdown, or any introductory text.
Example format: Indicates that the subject is treated or managed by the object therapeutic drug (e.g., Type 2 Diabetes is treated by Metformin)."""

    response = client.chat.completions.create(
        model="meta-llama/Llama-3.1-8B-Instruct",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=180
    )
    
    definition = response.choices[0].message.content.strip().strip('"\'')
    definition = definition.replace("_", " ") # Strict replacement to strip any remaining underscores
    new_relation_rows.append([clean_relation, definition])

# Save relations with header
with open(relation_file, "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["relation", "definition"])
    writer.writerows(new_relation_rows)

print(f"Saved {len(new_relation_rows)} relations to {relation_file}")


# 2. Processing Entity Types (diabetes_entity_type_schema.csv)
entity_file = "schemas/disease/diabetes_entity_type_schema.csv"
entity_backup = "schemas/disease/diabetes_entity_type_schema_backup.csv"

# Backup original
if os.path.exists(entity_file):
    shutil.copyfile(entity_file, entity_backup)

entity_types_to_define = [
    "Disease", "Drug", "Symptom", "Clinical Metric", 
    "Anatomical Site", "Treatment Procedure", "Dosage Value"
]

print("Generating entity type definitions using meta-llama/Llama-3.1-8B-Instruct...")
new_entity_rows = []
for etype in tqdm(entity_types_to_define):
    prompt = f"""You are an expert clinical ontologist and knowledge graph designer.
Write a precise, professional one-sentence definition for the clinical entity category '{etype}' in the context of structured clinical knowledge graphs for diabetes.
The definition should clearly explain what kinds of clinical concepts fall under this category.
CRITICAL: Do NOT use underscores anywhere in the definition text.

Provide ONLY the definition text. Do not use quotes, markdown, or any introductory text."""

    response = client.chat.completions.create(
        model="meta-llama/Llama-3.1-8B-Instruct",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=150
    )
    
    definition = response.choices[0].message.content.strip().strip('"\'')
    definition = definition.replace("_", " ") # Strict replacement to strip any remaining underscores
    new_entity_rows.append([etype, definition])

# Save entity types without header (matching original format)
with open(entity_file, "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(new_entity_rows)

print(f"Saved {len(new_entity_rows)} entity types to {entity_file}")
print("All schemas rewritten successfully!")
