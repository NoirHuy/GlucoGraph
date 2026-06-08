import sys
import os
import json

project_root = r"E:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject"
sys.path.append(os.path.join(project_root, "edc-main"))

# Load .env
env_path = os.path.join(project_root, ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip().strip('"').strip("'")
    if "GROQ_API_KEY" in os.environ and "GROQ_KEY" not in os.environ:
        os.environ["GROQ_KEY"] = os.environ["GROQ_API_KEY"]

# Import
from edc.schema_definition import SchemaDefiner
import edc.utils.llm_utils as llm_utils

# Sample input from result_at_each_stage.json
text = "Absence of PKC-alpha attenuates lithium-induced nephrogenic diabetes insipidus. Lithium, an effective antipsychotic, induces nephrogenic diabetes insipidus (NDI) in 40% of patients. The decreased capacity to concentrate urine is likely due to lithium acutely disrupting the cAMP pathway and chronically reducing urea transporter (UT-A1) and water channel (AQP2) expression in the inner medulla. Targeting an alternative signaling pathway, such as PKC-mediated signaling, may be an effective method of treating lithium-induced polyuria. PKC-alpha null mice (PKCa KO) and strain-matched wild type (WT) controls were treated with lithium for 0, 3 or 5 days. WT mice had increased urine output and lowered urine osmolality after 3 and 5 days of treatment whereas PKCa KO mice had no change in urine output or concentration. Western blot analysis revealed that AQP2 expression in medullary tissues was lowered after 3 and 5 days in WT mice; however, AQP2 was unchanged in PKCa KO. Similar results were observed with UT-A1 expression. Animals were also treated with lithium for 6 weeks. Lithium-treated WT mice had 19-fold increased urine output whereas treated PKCa KO animals had a 4-fold increase in output. AQP2 and UT-A1 expression was lowered in 6 week lithium-treated WT animals whereas in treated PKCa KO mice, AQP2 was only reduced by 2-fold and UT-A1 expression was unaffected. Urinary sodium, potassium and calcium were elevated in lithium-fed WT but not in lithium-fed PKCa KO mice. Our data show that ablation of PKCa preserves AQP2 and UT-A1 protein expression and localization in lithium-induced NDI, and prevents the development of the severe polyuria associated with lithium therapy."

oie_triplets = [
    ["Lithium", "induces", "NDI"],
    ["Lithium", "disrupts", "cAMP"],
    ["Lithium", "reduces", "UT-A1"],
    ["Lithium", "reduces", "AQP2"],
    ["PKCa", "attenuates", "NDI"],
    ["PKCa", "have no change in urine output", "lithium"],
    ["PKCa", "have no change in urine concentration", "lithium"],
    ["UT-A1", "is lowered", "lithium"],
    ["UT-A1", "is unchanged", "PKCa"],
    ["Lithium", "have increased urine output", "of"],
    ["PKCa", "have reduced urine output", "of"],
    ["sodium", "is elevated", "lithium"],
    ["potassium", "is elevated", "lithium"],
    ["calcium", "is elevated", "lithium"],
    ["PKCa", "preserves", "UT-A1"],
    ["PKCa", "prevents", "polyuria"]
]

# Read prompt template & few shots
sd_template_path = os.path.join(project_root, "edc-main", "prompt_templates", "diabetic", "sd_template_with_entities.txt")
sd_few_shot_path = os.path.join(project_root, "edc-main", "few_shot_examples", "diabetic", "sd_few_shot_examples_with_entities.txt")

with open(sd_template_path, "r", encoding="utf-8") as f:
    template_str = f.read()
with open(sd_few_shot_path, "r", encoding="utf-8") as f:
    few_shot_str = f.read()

# Instantiate SchemaDefiner
definer = SchemaDefiner(
    openai_model="meta-llama/llama-3.3-70b-instruct",
    use_entity_types=True,
    allowed_entity_types=[
        "DiseaseOrPhenotypicFeature", "ChemicalEntity", "SequenceVariant",
        "GeneOrGeneProduct", "CellLine", "OrganismTaxon"
    ]
)

# Build filled prompt and call api directly to see raw output
types_str = ", ".join(definer.allowed_entity_types)
filled_prompt = template_str.format_map(
    {
        "text":                 text,
        "few_shot_examples":    few_shot_str,
        "relations":            set(t[1] for t in oie_triplets),
        "triples":              oie_triplets,
        "allowed_entity_types": types_str,
    }
)
messages = [{"role": "user", "content": filled_prompt}]

print("Calling OpenRouter with meta-llama/llama-3.3-70b-instruct...")
completion = llm_utils.api_chat_completion("meta-llama/llama-3.3-70b-instruct", None, messages, max_tokens=4096)
print("\n=== RAW COMPLETION ===")
print(completion)
print("======================\n")

# Try to parse
from edc.schema_definition import parse_sd_json_output
parsed = parse_sd_json_output(completion)
print("Parsed entries length:", len(parsed))
if parsed:
    print("First entry:", parsed[0])
else:
    print("FAILED to parse.")
