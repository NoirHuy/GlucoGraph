import os
import sys
import logging

project_root = r"E:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject"
sys.path.append(os.path.join(project_root, "edc-main"))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TestOIE")

# Load env variables
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

from edc.utils.llm_utils import api_chat_completion, parse_raw_triplets, global_key_pool

input_text = "Absence of PKC-alpha attenuates lithium-induced nephrogenic diabetes insipidus. Lithium, an effective antipsychotic, induces nephrogenic diabetes insipidus (NDI) in 40% of patients. The decreased capacity to concentrate urine is likely due to lithium acutely disrupting the cAMP pathway and chronically reducing urea transporter (UT-A1) and water channel (AQP2) expression in the inner medulla. Targeting an alternative signaling pathway, such as PKC-mediated signaling, may be an effective method of treating lithium-induced polyuria. PKC-alpha null mice (PKCa KO) and strain-matched wild type (WT) controls were treated with lithium for 0, 3 or 5 days. WT mice had increased urine output and lowered urine osmolality after 3 and 5 days of treatment whereas PKCa KO mice had no change in urine output or concentration. Western blot analysis revealed that AQP2 expression in medullary tissues was lowered after 3 and 5 days in WT mice; however, AQP2 was unchanged in PKCa KO. Similar results were observed with UT-A1 expression. Animals were also treated with lithium for 6 weeks. Lithium-treated WT mice had 19-fold increased urine output whereas treated PKCa KO animals had a 4-fold increase in output. AQP2 and UT-A1 expression was lowered in 6 week lithium-treated WT animals whereas in treated PKCa KO mice, AQP2 was only reduced by 2-fold and UT-A1 expression was unaffected. Urinary sodium, potassium and calcium were elevated in lithium-fed WT but not in lithium-fed PKCa KO mice. Our data show that ablation of PKCa preserves AQP2 and UT-A1 protein expression and localization in lithium-induced NDI, and prevents the development of the severe polyuria associated with lithium therapy."

# 1. Test with the non-clinical WebNLG examples
webnlg_template_path = os.path.join(project_root, "edc-main", "prompt_templates", "diabetic", "oie_template.txt")
webnlg_few_shot_path = os.path.join(project_root, "edc-main", "few_shot_examples", "example", "oie_few_shot_examples.txt")

with open(webnlg_template_path, "r", encoding="utf-8") as f:
    template_str = f.read()
with open(webnlg_few_shot_path, "r", encoding="utf-8") as f:
    few_shot_str = f.read()

filled_prompt = template_str.format_map({
    "few_shot_examples": few_shot_str,
    "input_text": input_text,
    "entities_hint": "",
    "relations_hint": "",
})

messages = [{"role": "user", "content": filled_prompt}]
model_name = "meta-llama/llama-3.3-70b-instruct"

logger.info(f"Using OpenRouter Key: {global_key_pool.get_active_key()[:15]}...")
logger.info("Calling OpenRouter with WebNLG few-shot examples...")
completion_webnlg = api_chat_completion(model_name, None, messages, max_tokens=1024)
print("\n=== RAW COMPLETION (WebNLG few-shot examples) ===")
print(completion_webnlg)

parsed_webnlg = parse_raw_triplets(completion_webnlg)
print("\n=== PARSED TRIPLETS ===")
print(parsed_webnlg)

# 2. Test with the clinical Diabetic examples
diabetic_few_shot_path = os.path.join(project_root, "edc-main", "few_shot_examples", "diabetic", "oie_few_shot_examples.txt")
with open(diabetic_few_shot_path, "r", encoding="utf-8") as f:
    few_shot_diabetic_str = f.read()

filled_prompt_diabetic = template_str.format_map({
    "few_shot_examples": few_shot_diabetic_str,
    "input_text": input_text,
    "entities_hint": "",
    "relations_hint": "",
})

messages_diabetic = [{"role": "user", "content": filled_prompt_diabetic}]
logger.info("Calling OpenRouter with Diabetic clinical few-shot examples...")
completion_diabetic = api_chat_completion(model_name, None, messages_diabetic, max_tokens=1024)
print("\n=== RAW COMPLETION (Diabetic few-shot examples) ===")
print(completion_diabetic)

parsed_diabetic = parse_raw_triplets(completion_diabetic)
print("\n=== PARSED TRIPLETS ===")
print(parsed_diabetic)
