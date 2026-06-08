import os
import json

base_dir = r"e:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject\edc-main\output"

matches = []

for root, dirs, files in os.walk(base_dir):
    for file in files:
        if file == "debate_log_all.json":
            log_path = os.path.join(root, file)
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                results = data.get("results", [])
                folder_name = os.path.basename(os.path.dirname(root))
                
                for idx, entry in enumerate(results):
                    triple = entry.get("triple", [])
                    triple_str = " ".join([str(x) for x in triple]).lower()
                    
                    if "exercise" in triple_str:
                        matches.append((folder_name, idx, entry))
            except Exception as e:
                print(f"Error reading {log_path}: {e}")

print(f"\nFound {len(matches)} matching debate entries for 'exercise':")
for folder, idx, entry in matches:
    print(f"\n==================================================")
    print(f"Sub-project: {folder}")
    print(f"Entry Index in results: {idx}")
    triple = entry.get("triple")
    print(f"TRIPLE: {triple[0]} -[{triple[1]}]-> {triple[2]}")
    print(f"Accepted: {entry.get('accepted')} (FCS Score: {entry.get('fcs_score')})")
    print(f"Vetoed: {entry.get('vetoed')}")
    print(f"Rounds: {entry.get('rounds_completed')}")
    
    agent_responses = entry.get("agent_responses", [])
    print(f"Debate Details ({len(agent_responses)} responses):")
    for resp in agent_responses:
        print(f"\n  Agent: {resp.get('agent')} (Round: {resp.get('round')})")
        print(f"  Verdict: {resp.get('verdict')}")
        print(f"  Confidence: {resp.get('confidence')}")
        print(f"  Justification: {resp.get('justification')}")
