import json
from app.services.cdss import generate_medical_decision

def run_test():
    clinical_text = "bệnh nhân nam, 22 tuổi thường xuyên khát nước, tiểu đêm"
    patient_id = "user_test"
    
    print(f"Running CDSS analyze for scenario: {clinical_text}...")
    result = generate_medical_decision(clinical_text, patient_id)
    print("\nResult:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    run_test()
