import os
from edc.utils import llm_utils

# Đảm bảo bạn đã có biến môi trường XIAOMI_API_KEY
input_sentence = "Lyseren is a lake in the municipalities of Enebakk in Akershus county and Spydeberg in Østfold county , Norway ."

# Lấy template từ file few_shot
with open("./few_shot_examples/wiki-nre/oie_few_shot_examples.txt", "r", encoding="utf-8") as f:
    few_shot_examples_str = f.read()

# Tạo prompt y hệt như hệ thống EDC đang làm
prompt_template_str = """You are an advanced information extraction system.
Extract all triplets from the following input text.
{few_shot_examples}

Input Text: {input_text}
Triplets:"""

filled_prompt = prompt_template_str.format_map({
    "few_shot_examples": few_shot_examples_str,
    "input_text": input_sentence,
    "entities_hint": "",
    "relations_hint": ""
})

messages = [{"role": "user", "content": filled_prompt}]

print("Đang gọi API tới Xiaomi MiMo-V2.5-Pro...")
raw_output = llm_utils.api_chat_completion("mimo-v2.5-pro", None, messages)

print("\n" + "="*50)
print("CÂU TRẢ LỜI GỐC (RAW OUTPUT) TỪ XIAOMI MIMO:")
print("="*50)
print(raw_output)
print("="*50)
