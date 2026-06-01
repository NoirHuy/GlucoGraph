import sys
import os

# Add edc-main to system path to import UMLSNormalizer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "edc-main"))

from edc.post_processing.umls_normalizer import UMLSNormalizer

def test_umls():
    # Retrieve UMLS API Key from environment or manual input
    api_key = os.environ.get("UMLS_API_KEY", "")
    
    if not api_key:
        print("⚠️ Không tìm thấy UMLS_API_KEY trong file .env!")
        api_key = input("👉 Hãy dán UMLS API Key của bạn vào đây để chạy test: ").strip()
        
    if not api_key:
        print("❌ Hủy kiểm thử vì không có API Key.")
        return
        
    print(f"\n🔌 Đang khởi tạo kết nối đến API UTS của NIH (https://uts-ws.nlm.nih.gov/rest)...")
    
    # Initialize the official online normalizer
    normalizer = UMLSNormalizer(api_key=api_key, cache_path="./output/umls_test_cache.json")
    
    test_terms = ["sulfonylureas", "pancreatitis", "fever", "nausea", "insulin resistance", "diarrhea"]
    
    print("\n🔍 KẾT QUẢ TRA CỨU TRỰC TIẾP TỪ HỆ THỐNG UMLS UTS API:")
    print("-" * 80)
    for term in test_terms:
        print(f"🔎 Đang gửi request tra cứu: '{term}'...")
        # This will call the NIH REST API under searchType='exact'/'normalizedString'/'words'
        res = normalizer.query_term(term)
        print(f"   - Mã CUI định danh: {res.get('cui')}")
        print(f"   - Tên chuẩn hóa (Canonical): {res.get('canonical')}")
        print(f"   - Loại ngữ nghĩa (Semantic Type): {res.get('semantic_type')}")
        print(f"   - Điểm tin cậy (Confidence Score): {res.get('score')}")
        print("-" * 80)

if __name__ == "__main__":
    test_umls()
