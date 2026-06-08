import httpx
import time
import json
import sys

payload = {
    "clinical_text": "Bệnh nhân Robert Smith, 60 tuổi, tiền sử đái tháo đường típ 2 đang dùng metformin, có biểu hiện suy thận mạn tính...",
    "patient_id": "robert"
}

print("Sending request to CDSS API for Robert (Diabetes)...")
start = time.time()
try:
    with httpx.Client(timeout=120.0) as client:
        r = client.post("http://localhost/api/cdss/analyze", json=payload)
        elapsed = time.time() - start
        print(f"Status Code: {r.status_code}")
        print(f"Elapsed Time: {elapsed:.2f} seconds")
        if r.status_code == 200:
            res_data = r.json()
            print("\nResponse Logs:")
            for log in res_data.get("logs", []):
                print(log.encode('ascii', 'replace').decode('ascii'))
            print("\nDifferential Diagnosis:")
            # Use ascii=True to avoid encoding issues in print
            print(json.dumps(res_data.get("differential_diagnosis"), indent=2, ensure_ascii=True))
            print("\nAlert:")
            print(json.dumps(res_data.get("alert"), indent=2, ensure_ascii=True))
        else:
            print(f"Error: {r.text}")
except Exception as e:
    print(f"Request failed: {e}")
