import httpx
import time
import json

payload = {
    "clinical_text": "Một bệnh nhân nam 56 tuổi đến khám vì tiểu nhiều lần trong ngày, đặc biệt về đêm, kèm theo khát nước liên tục trong khoảng 3 tháng gần đây. Bệnh nhân cho biết thường xuyên cảm thấy mệt mỏi, giảm khả năng tập trung trong công việc và gần đây xuất hiện tình trạng nhìn mờ. Tiền sử gia đình ghi nhận cha ruột mắc đái tháo đường type 2. Bệnh nhân có BMI 31 kg/m². Kết quả xét nghiệm cho thấy đường huyết lúc đói là 156 mg/dL, HbA1c 8,2% và đường huyết ngẫu nhiên 245 mg/dL.",
    "patient_id": "user_patient"
}

print("Sending request to CDSS API for User Case...")
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
            print(json.dumps(res_data.get("differential_diagnosis"), indent=2, ensure_ascii=True))
            print("\nAlert:")
            print(json.dumps(res_data.get("alert"), indent=2, ensure_ascii=True))
        else:
            print(f"Error: {r.text}")
except Exception as e:
    print(f"Request failed: {e}")
