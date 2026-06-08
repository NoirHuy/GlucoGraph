import json
import os

cache_path = r"e:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject\edc-main\output\umls_cache.json"

def check():
    if not os.path.exists(cache_path):
        print(f"Cache file not found at {cache_path}")
        return

    with open(cache_path, "r", encoding="utf-8") as f:
        cache = json.load(f)

    keys = [
        "plasma glucose levels",
        "plasma fasting glucose measurement",
        "fasting plasma glucose",
        "blood glucose",
        "glucose level",
        "exercise"
    ]

    print("=== CACHED UMLS MAPPINGS ===")
    for k in keys:
        val = cache.get(k)
        if val:
            print(f"Key: '{k}'")
            print(f"  CUI: {val.get('cui')}")
            print(f"  Canonical: {val.get('canonical')}")
            print(f"  Semantic Type: {val.get('semantic_type')}")
        else:
            # Check for partial match
            print(f"Key: '{k}' -> NOT FOUND EXACTLY")
            matches = [ck for ck in cache.keys() if k in ck]
            if matches:
                print(f"  Partial matches: {matches[:3]}")

if __name__ == "__main__":
    check()
