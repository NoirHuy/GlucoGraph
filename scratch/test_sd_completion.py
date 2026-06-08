import os
import sys
import logging

project_root = r"E:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject"
sys.path.append(os.path.join(project_root, "edc-main"))

# Load env
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

from edc.edc_framework import EDC

# Prepare single document input
input_text = "Absence of PKC-alpha attenuates lithium-induced nephrogenic diabetes insipidus. Lithium, an effective antipsychotic, induces nephrogenic diabetes insipidus (NDI) in 40% of patients. The decreased capacity to concentrate urine is likely due to lithium acutely disrupting the cAMP pathway and chronically reducing urea transporter (UT-A1) and water channel (AQP2) expression in the inner medulla. Targeting an alternative signaling pathway, such as PKC-mediated signaling, may be an effective method of treating lithium-induced polyuria."
oie_triplets = [
    ["Lithium", "induces", "nephrogenic_diabetes_insipidus"],
    ["Lithium", "disrupts", "cAMP_pathway"]
]

# Set working directory to edc-main
os.chdir(os.path.join(project_root, "edc-main"))

edc_config = {
    "oie_llm": "meta-llama/llama-3.1-8b-instruct",
    "oie_prompt_template_file_path": "./prompt_templates/diabetic/oie_template.txt",
    "oie_few_shot_example_file_path": "./few_shot_examples/example/oie_few_shot_examples.txt",
    "sd_llm": "meta-llama/llama-3.1-8b-instruct",
    "sd_prompt_template_file_path": "./prompt_templates/example/sd_template.txt",
    "sd_few_shot_example_file_path": "./few_shot_examples/example/sd_few_shot_examples.txt",
    "sc_llm": "meta-llama/llama-3.1-8b-instruct",
    "sc_embedder": "qwen/qwen3-embedding-8b",
    "sc_prompt_template_file_path": "./prompt_templates/diabetic/sc_template.txt",
    "target_schema_path": os.path.join(project_root, "evaluate", "biored_schema.csv"),
    "target_entity_type_schema_path": os.path.join(project_root, "evaluate", "biored_entity_type_schema.csv"),
    "enrich_schema": False,
    "umls_api_key": "",
    "run_umls_normalization": False,
    "output_dir": None,
    "loglevel": logging.INFO
}

edc = EDC(**edc_config)

# Run SD manually to capture raw output
sd_template_path = edc._sd_template_with_entities
sd_few_shot_path = edc._sd_few_shot_with_entities
sd_template_str = open(sd_template_path, encoding="utf-8").read()
sd_few_shot_str = open(sd_few_shot_path, encoding="utf-8").read()

relations_present = set(t[1] for t in oie_triplets)
types_str = ", ".join(list(edc.entity_type_schema.keys()))
filled_prompt = sd_template_str.format_map({
    "text": input_text,
    "few_shot_examples": sd_few_shot_str,
    "relations": relations_present,
    "triples": oie_triplets,
    "allowed_entity_types": types_str,
})
messages = [{"role": "user", "content": filled_prompt}]

import edc.utils.llm_utils as llm_utils
print("Calling API for SD...")
completion = llm_utils.api_chat_completion(edc.sd_llm_name, None, messages, max_tokens=2048)
print("\n--- RAW SD COMPLETION ---")
print(completion)
print("-------------------------\n")

try:
    start = completion.index("[")
    end = completion.rindex("]") + 1
    json_str = completion[start:end]
    import json
    result = json.loads(json_str)
    print("Successfully parsed JSON array with length:", len(result))
except Exception as e:
    print("JSON parsing failed with error:", e)
