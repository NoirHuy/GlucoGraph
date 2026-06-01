import os
import requests
import json

def test_endpoints():
    api_key = os.environ.get("UMLS_API_KEY", "").strip()
    if not api_key:
        print("UMLS_API_KEY not found in env.")
        return

    base_url = "https://uts-ws.nlm.nih.gov/rest"
    
    # 1. Search for metformin
    search_url = f"{base_url}/search/current"
    search_params = {
        "string": "metformin",
        "apiKey": api_key,
        "searchType": "exact",
        "sabs": "RXNORM,SNOMEDCT_US,MSH"
    }
    print("--- Searching 'metformin' with sabs ---")
    r = requests.get(search_url, params=search_params)
    print("Search Status:", r.status_code)
    search_res = r.json()
    print("Search Result (truncated):", json.dumps(search_res, indent=2)[:600])
    
    results = search_res.get("result", {}).get("results", [])
    if not results:
        print("No results found.")
        return
        
    cui = results[0].get("ui")
    print(f"Top CUI: {cui}, Name: {results[0].get('name')}")
    
    # 2. Get CUI concept details
    detail_url = f"{base_url}/content/current/CUI/{cui}"
    r_detail = requests.get(detail_url, params={"apiKey": api_key})
    print("\n--- Concept details status:", r_detail.status_code)
    detail_json = r_detail.json()
    print("Concept semanticTypes:", json.dumps(detail_json.get("result", {}).get("semanticTypes", []), indent=2))
    
    # 3. Get Definitions
    def_url = f"{base_url}/content/current/CUI/{cui}/definitions"
    r_def = requests.get(def_url, params={"apiKey": api_key})
    print("\n--- Definitions status:", r_def.status_code)
    if r_def.status_code == 200:
        def_json = r_def.json()
        print("Definitions (truncated):", json.dumps(def_json, indent=2)[:800])
    else:
        print("Failed to get definitions")
        
    # 4. Get Atoms for RXNORM
    atoms_url = f"{base_url}/content/current/CUI/{cui}/atoms"
    r_atoms = requests.get(atoms_url, params={"apiKey": api_key, "sabs": "RXNORM"})
    print("\n--- RXNORM Atoms status:", r_atoms.status_code)
    if r_atoms.status_code == 200:
        atoms_json = r_atoms.json()
        print("RXNORM Atoms (truncated):", json.dumps(atoms_json, indent=2)[:800])
    else:
        print("Failed to get RXNORM atoms")

    # 5. Search for diabetes to test ICD10CM
    print("\n--- Searching 'type 2 diabetes' with sabs ---")
    search_params["string"] = "type 2 diabetes"
    r = requests.get(search_url, params=search_params)
    results_db = r.json().get("result", {}).get("results", [])
    if results_db:
        cui_db = results_db[0].get("ui")
        print(f"Top CUI for type 2 diabetes: {cui_db}")
        # Get Atoms for ICD10CM
        r_atoms_db = requests.get(f"{base_url}/content/current/CUI/{cui_db}/atoms", params={"apiKey": api_key, "sabs": "ICD10CM"})
        print("ICD10CM Atoms status:", r_atoms_db.status_code)
        if r_atoms_db.status_code == 200:
            print("ICD10CM Atoms (truncated):", json.dumps(r_atoms_db.json(), indent=2)[:800])

if __name__ == "__main__":
    test_endpoints()
