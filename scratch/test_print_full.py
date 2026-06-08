import httpx
import json

payload = {
    "clinical_text": "Bệnh nhân nam, 65 tuổi, có biểu hiện khát nhiều, tiểu nhiều. Đường huyết đói bình thường.",
    "patient_id": "user_patient"
}

try:
    with httpx.Client(timeout=120.0) as client:
        r = client.post("http://localhost/api/cdss/analyze", json=payload)
        if r.status_code == 200:
            res_data = r.json()
            print("\n--- FULL RESULT ---")
            print("Graph Path:")
            print(json.dumps(res_data.get("graph_path"), indent=2, ensure_ascii=False))
            print("\nEvidence Triples:")
            print(json.dumps(res_data.get("evidence_triples"), indent=2, ensure_ascii=False))
        else:
            print(f"Error: {r.text}")
except Exception as e:
    print(f"Request failed: {e}")
