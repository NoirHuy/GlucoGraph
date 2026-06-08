import json
import os

# Search recursively in the output directory for all umls_cache.json files
cache_files = []
for root, dirs, files in os.walk("output"):
    for file in files:
        if file == "umls_cache.json":
            cache_files.append(os.path.join(root, file))

# Also add the main cache at output/umls_cache.json if it exists
main_cache = os.path.join("output", "umls_cache.json")
if main_cache not in cache_files and os.path.exists(main_cache):
    cache_files.append(main_cache)

print(f"Found {len(cache_files)} cache files to check:")
for f in cache_files:
    print(f" - {f}")

czech_keywords = [
    "pankreat", "diabetu", "inzulin", "porucha", "nemoc", "způsob", 
    "Wikiskripta", "slovniky.cz", "lékarský", "který", "charakterizovaný",
    "často", "vyskyt", "vzniká", "důsledku", "nedostatku", "kombinací",
    "obojího", "hraniční", "nález", "orálním", "obézních", "vyžaduje",
    "cukrovka", "těhotenství", "mizí", "činnosti", "mozku", "vedoucí",
    "příznaky", "slabost", "hlad", "třes", "studený", "zmatenost", "bezvědomí",
    "odumření", "myokardu", "přerušením", "krevního", "zásobení"
]

czech_chars = "áčďéěíňóřšťúůýž"

for path in cache_files:
    with open(path, "r", encoding="utf-8") as f:
        try:
            cache = json.load(f)
        except json.JSONDecodeError:
            print(f"Skipping malformed JSON file: {path}")
            continue
        
    cleaned_count = 0
    for key, val in cache.items():
        if isinstance(val, dict):
            desc = val.get("definition", "")
            has_cz_keyword = any(k in desc for k in czech_keywords)
            has_cz_char = any(c in desc for c in czech_chars)
            
            if has_cz_keyword or has_cz_char:
                val["definition"] = ""
                cleaned_count += 1
                
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=4, ensure_ascii=False)
        
    print(f"[OK] Cleaned {cleaned_count} non-English definitions in: {path}")
