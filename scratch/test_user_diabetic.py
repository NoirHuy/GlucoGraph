import sys
import os
import json

# Reconfigure stdout/stderr to UTF-8 for Windows console encoding safety
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add backend directory to sys.path so we can import app.*
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

# Let's set env vars so that app.config settings are populated
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USER"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "password"

# Read keys from .env if present
try:
    with open(os.path.join(os.path.dirname(__file__), '../.env'), 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                os.environ[k] = v.strip('"').strip("'")
except Exception as e:
    print("Warning loading .env:", e)

from app.services.cdss import generate_medical_decision

clinical_text = (
    "Một bệnh nhân nam 56 tuổi đến khám vì tiểu nhiều lần trong ngày, đặc biệt về đêm, kèm theo khát nước liên tục trong khoảng 3 tháng gần đây. "
    "Bệnh nhân cho biết thường xuyên cảm thấy mệt mỏi, giảm khả năng tập trung trong công việc và gần đây xuất hiện tình trạng nhìn mờ. "
    "Tiền sử gia đình ghi nhận cha ruột mắc đái tháo đường type 2. Bệnh nhân có BMI 31 kg/m². Kết quả xét nghiệm cho thấy đường huyết lúc đói là 156 mg/dL, "
    "HbA1c 8,2% và đường huyết ngẫu nhiên 245 mg/dL."
)

print("Running generate_medical_decision...")
res = generate_medical_decision(clinical_text, "test_patient_diabetic")
print("\n--- RESULTS ---")
print(json.dumps(res, indent=2, ensure_ascii=False))
