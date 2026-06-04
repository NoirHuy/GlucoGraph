import json
import os

cache_paths = [
    "output/umls_cache.json",
    "output/Medication_for_Diabetes_Mellitus_Treatment/debated_results/umls_cache.json"
]

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

for path in cache_paths:
    if not os.path.exists(path):
        print(f"File not found: {path}")
        continue
        
    with open(path, "r", encoding="utf-8") as f:
        cache = json.load(f)
        
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
