import os
import csv
from openai import OpenAI
from tqdm import tqdm

# Initialize OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_KEY")
)

input_schema = "schemas/disease/diabetes_schema.csv"
output_schema = "schemas/disease/diabetes_schema.csv"
backup_schema = "schemas/disease/diabetes_schema_backup.csv"

# Backup original
import shutil
shutil.copyfile(input_schema, backup_schema)

rows = []
with open(input_schema, "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    header = next(reader)
    for row in reader:
        if len(row) >= 2:
            rows.append(row)

new_rows = []
print("Rewriting schema definitions using cohere/command-r7b-12-2024...")
for row in tqdm(rows):
    original_relation = row[0]
    original_definition = row[1]
    
    # Remove underscores
    clean_relation = original_relation.replace("_", " ")
    
    prompt = f"""You are an expert in medical ontologies and knowledge graphs.
Please rewrite the definition for the relation '{clean_relation}'.
Make the definition clear, natural, and concise. It should explain how the subject and object are related in the context of diabetes or medicine.

Original definition: {original_definition}

Provide ONLY the rewritten definition text. Do not use quotes, markdown, or add any introductory text."""

    response = client.chat.completions.create(
        model="cohere/command-r7b-12-2024",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=150
    )
    
    new_definition = response.choices[0].message.content.strip().strip('"\'')
    new_rows.append([clean_relation, new_definition])

with open(output_schema, "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(new_rows)

print(f"Successfully rewritten {len(new_rows)} relations and saved to {output_schema}")
