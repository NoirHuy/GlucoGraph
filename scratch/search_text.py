import os
import json
import sys

# Configure stdout to use UTF-8
sys.stdout.reconfigure(encoding='utf-8')

log_path = r"C:\Users\huyph\.gemini\antigravity\brain\f9a48ccc-2935-4b6d-ac16-459571b12513\.system_generated\logs\transcript.jsonl"
if os.path.exists(log_path):
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            step = obj.get("step_index")
            if step == 9572:
                print("--- STEP 9572 ---")
                print(obj.get("content"))
                print("-----------------")
                break
else:
    print("Log file NOT found.")
