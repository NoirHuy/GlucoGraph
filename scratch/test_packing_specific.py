import sys
import os
import json

# Add edc-main to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "edc-main")))

from post_processing.property_packer import pack_properties

# Setup dummy record based on Record 1258
record_1258 = {
    "index": 1258,
    "input_text": "patients with type 2 diabetes may be able to avoid or cease treatment with medications if they maintain plasma glucose levels. exercise is a method to maintain plasma glucose levels.",
    "schema_definition": {
        "_entries": [
            {
                "subject": "plasma glucose levels",
                "subject_type": "Clinical Metric",
                "relation": "treated by",
                "object": "exercise",
                "object_type": "Treatment Procedure"
            }
        ]
    },
    "schema_canonicalizaiton": [
        [
            "plasma glucose levels",
            "treated by",
            "exercise"
        ]
    ]
}

# Run packing
api_key = os.environ.get("UMLS_API_KEY", "880ba42c-e5c0-47e0-8776-bb8f30350183")
packed_graph = pack_properties(
    [record_1258],
    umls_api_key=api_key,
    umls_cache_path="./edc-main/output/umls_cache.json"
)

print("\n--- TEST PACKING OUTPUT ---")
print("NODES:")
for node in packed_graph["nodes"]:
    print(f"- Node ID: {node['id']}")
    print(f"  Labels: {node['labels']}")
    print(f"  UMLS CUI: {node['properties'].get('umls_cui')}")
    print(f"  UMLS Canonical: {node['properties'].get('umls_canonical')}")
    print(f"  Semantic Type: {node['properties'].get('umls_semantic_type')}")
    print(f"  Aliases: {node['properties'].get('aliases')}")

print("\nRELATIONSHIPS:")
for rel in packed_graph["relationships"]:
    print(f"- Relationship: ({rel['start']}) -[:{rel['type']}]-> ({rel['end']})")
    print(f"  Properties: {rel['properties']}")
