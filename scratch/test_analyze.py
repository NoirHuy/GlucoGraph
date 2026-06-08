import httpx
import time
import json

payload = {
    "clinical_text": "Bệnh nhân nam, 45 tuổi, sưng đau dữ dội khớp bàn ngón chân cái bên phải khởi phát cấp tính sau bữa ăn nhiều hải sản. Tiền sử loét dạ dày tá tràng.",
    "patient_id": "john"
}

print("Sending request to CDSS API for John (Gout)...")
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
                # Safe print to avoid charmap encode errors
                print(log.encode('ascii', 'replace').decode('ascii'))
            print("\nDifferential Diagnosis:")
            print(json.dumps(res_data.get("differential_diagnosis"), indent=2, ensure_ascii=True))
            print("\nAlert:")
            print(json.dumps(res_data.get("alert"), indent=2, ensure_ascii=True))
        else:
            print(f"Error: {r.text}")
except Exception as e:
    print(f"Request failed: {e}")
