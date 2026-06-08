import json

file_path = r"e:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject\edc-main\output\all_results_debated.json"

with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total records: {len(data)}")

matches = []
for idx, record in enumerate(data):
    for field in ["oie_raw", "oie", "schema_canonicalizaiton"]:
        for triple in record.get(field, []):
            if any("plasma glucose levels" in str(x).lower() for x in triple):
                matches.append((idx, field, triple))

print(f"Found {len(matches)} exact occurrences of 'plasma glucose levels':")
for idx, field, triple in matches:
    # safe print
    safe_triple = [str(x).encode("ascii", "replace").decode("ascii") for x in triple]
    print(f"- Record {idx} ({field}): {safe_triple}")
