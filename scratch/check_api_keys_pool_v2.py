# -*- coding: utf-8 -*-
import os
import sys
import logging

project_root = r"E:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject"
sys.path.append(os.path.join(project_root, "edc-main"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TestKeys")

from edc.utils.llm_utils import global_key_pool
import openai

print("=== LOADED KEYS IN THE POOL ===")
print(f"Total keys loaded: {len(global_key_pool.keys)}")
for idx, k in enumerate(global_key_pool.keys):
    masked = k[:15] + "..." + k[-5:] if len(k) > 20 else k
    print(f"Key #{idx}: {masked}")

print("\n=== TESTING EACH KEY VALIDITY WITH llama-3.1-8b-instruct ===")
for idx, key in enumerate(global_key_pool.keys):
    masked = key[:15] + "..." + key[-5:] if len(key) > 20 else key
    print(f"\nTesting Key #{idx} ({masked}):")
    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=key,
    )
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct",
            messages=[{"role": "user", "content": "say hello"}],
            max_tokens=10,
            timeout=10
        )
        content = response.choices[0].message.content.strip()
        print(f"[OK] Success! Response: {content}")
    except Exception as e:
        print(f"[FAIL] Failed: {e}")
