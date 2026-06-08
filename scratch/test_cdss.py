import requests
import json

url = "http://localhost:8000/api/cdss/analyze"
payload = {
    "clinical_text": "Một bệnh nhân nam 56 tuổi đến khám vì tiểu nhiều lần trong ngày, đặc biệt về đêm, kèm theo khát nước liên tục trong khoảng 3 tháng gần đây. Bệnh nhân cho biết thường xuyên cảm thấy mệt mỏi, giảm khả năng tập trung trong công việc và gần đây xuất hiện tình trạng nhìn mờ. Tiền sử gia đình ghi nhận cha ruột mắc đái tháo đường type 2. Bệnh nhân có BMI 31 kg/m². Kết quả xét nghiệm cho thấy đường huyết lúc đói là 156 mg/dL, HbA1c 8,2% và đường huyết ngẫu nhiên 245 mg/dL.",
    "patient_id": "test_patient_t2d"
}

headers = {
    "Content-Type": "application/json"
}

try:
    print("Sending request to CDSS API...")
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    print("Status Code:", r.status_code)
    
    with open("scratch/cdss_response.json", "w", encoding="utf-8") as f:
        json.dump(r.json(), f, indent=2, ensure_ascii=False)
    print("Saved response to scratch/cdss_response.json")
except Exception as e:
    print("Error:", e)
