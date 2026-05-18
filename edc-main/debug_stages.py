import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "./output/aacac_mimo/iter0/result_at_each_stage.json"
indices = list(map(int, sys.argv[2:])) if len(sys.argv) > 2 else None

with open(path, encoding="utf-8") as f:
    data = json.load(f)

print(f"Total entries: {len(data)}")
print("=" * 70)

for item in data:
    idx = item["index"]
    if indices and idx not in indices:
        continue
    oie = item.get("oie", [])
    sc = item.get("schema_canonicalizaiton", [])
    sd = item.get("schema_definition", {})
    cands = item.get("canonicalization_candidates", "[]")
    text = item["input_text"].strip()

    print(f"\n--- Index {idx} ---")
    print(f"  TEXT: {text}")
    print(f"  OIE ({len(oie)} triples): {oie}")
    print(f"  SD relations: {list(sd.keys())}")
    print(f"  Candidates: {cands[:200]}")
    print(f"  Final SC ({len(sc)}): {sc}")
