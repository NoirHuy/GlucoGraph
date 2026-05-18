# Sổ Tay Những Ghi Chú Quan Trọng Cho Báo Cáo Luận Văn

Dưới đây là tổng hợp các phát hiện kỹ thuật, điểm yếu của hệ thống và các giải pháp đã được áp dụng trong quá trình thực nghiệm. Các ý này có thể được dùng trực tiếp để viết phần Đánh giá / Thảo luận (Discussion) trong luận văn.

## 1. Lựa chọn Mô hình Ngôn ngữ (LLM Selection)
- **Vấn đề của các mô hình Chat-aligned:** Các mô hình được tối ưu quá nhiều cho việc trò chuyện (như Xiaomi MiMo) thường có xu hướng "dài dòng", hay giải thích thừa và không tuân thủ nghiêm ngặt định dạng đầu ra (JSON/List). Điều này dẫn đến các lỗi Parse dữ liệu liên tục làm đứt gãy luồng Pipeline tự động.
- **Giải pháp:** Đối với bài toán Trích xuất thông tin có cấu trúc (Information Extraction), bắt buộc phải sử dụng các mô hình hệ Instruct / Coding-aligned (như Llama-3.3-70B, Cohere Command-R) để đảm bảo tính kỷ luật trong đầu ra. Đặc biệt, Command-R cho thấy sự ưu việt rất lớn khi xử lý các tác vụ Retrieval / RAG.

## 2. Nút Thắt Cổ Chai (Bottleneck) Ở Mô hình Nhúng (Embedding)
- **Vấn đề:** Trong kiến trúc Retrieve-then-Extract (EDC+R), điểm F1 sụt giảm không hẳn do LLM yếu, mà do bước Schema Retriever cung cấp "gợi ý rác". Việc dùng các mô hình nhúng bị nén (ví dụ `v5-small` - 384 chiều) làm mất không gian biểu diễn, khiến nó bốc nhầm các quan hệ không liên quan. Việc LLM bị mớm "nhiễu" (noise) vào Prompt sẽ khiến LLM bị định hướng sai.
- **Giải pháp:** Sử dụng các mô hình nhúng cấp cao, chuyên sâu cho Retrieval như `jina-embeddings-v3` (tích hợp Task-specific LoRA) hoặc `BAAI/bge-m3` (đứng top Leaderboard). Khả năng bắt ngữ nghĩa ẩn tốt giúp bơm đúng Target Schema cho LLM.

## 3. Lỗi O(N!) Trong Thuật Toán Đánh Giá (Evaluation Script Bug)
- **Vấn đề:** Thuật toán chấm điểm gốc từ WebNLG sử dụng phương pháp hoán vị vét cạn (Permutations - N!) để bắt cặp các ứng viên sinh ra (Candidate) và đáp án gốc (Reference). Khi LLM bị ảo giác (Hallucination) và sinh ra một lượng lớn các bộ ba rác (ví dụ 15 triplets cho 1 câu), hàm hoán vị sẽ tạo ra hàng nghìn tỷ phép toán (15!), gây tràn RAM (MemoryError) và sập script.
- **Giải pháp kỹ thuật (Hotfix):** Cắt tỉa (Truncate) và chỉ lấy tối đa Top-8 bộ ba đầu tiên.
- **Lập luận khoa học cho việc cắt tỉa:** LLM sinh văn bản tuần tự, những thông tin nó chắc chắn nhất sẽ được sinh ra đầu tiên. Những bộ ba được sinh ra ở phần đuôi (tail-end) thường là hệ quả của ảo giác (Spurious/Hallucination). Việc cắt bớt phần đuôi vừa chặn đứng lỗi sập RAM, vừa mô phỏng sát nhất độ tin cậy giảm dần của LLM.

## 4. Sức Mạnh Kép Của Schema Canonicalization (Nhịp Retriever - Verifier)
Cơ chế biến đổi quan hệ tự do (Open Relation) thành quan hệ chuẩn (Target Schema) dựa vào sự kết hợp giữa **Toán học** và **Suy luận**:
- **Nhịp 1 (Toán học - Jina V3):** Dựa vào khoảng cách Vector, trích xuất Top-K quan hệ từ Lược đồ có khoảng cách gần nhất. Hạn chế: Retriever rất máy móc, nếu câu văn khác hoàn toàn lĩnh vực, nó vẫn sẽ ép lấy Top 5 sai lệch.
- **Nhịp 2 (Suy luận - LLM):** Đóng vai trò Giám khảo (Verifier) giải bài toán trắc nghiệm A, B, C, D. Sức mạnh thực sự nằm ở đáp án **"None of the above"**. Nếu Top-K do Retriever đưa lên quá vô lý, LLM sẽ chặn lại và vứt bỏ quan hệ đó. Đây là lớp khiên vững chắc nhất bảo vệ Knowledge Graph khỏi dữ liệu rác.

## 5. Tính Chống Chịu Của Hệ Thống (Robustness in API Integration)
- **Vấn đề:** Khi gọi LLM qua các cổng trung gian (OpenRouter, Azure), các bộ lọc bảo mật ngầm (ví dụ: Azure yêu cầu `max_tokens >= 16`) hoặc các sự cố nghẽn mạng (Rate Limit) khiến API trả về giá trị rỗng (`NoneType`). Nếu code không bắt lỗi ngầm (Exception Handling), hệ thống sẽ bị nổ (Crash) khi đang xử lý hàng loạt văn bản.
- **Giải pháp:** Xây dựng cơ chế kiểm tra tính hợp lệ của gói tin trả về. Quy đổi các lỗi kết nối mạng thành hành vi an toàn của LLM (Tương đương việc LLM chọn *"None of the above"*), giúp Pipeline không bao giờ bị đứt gãy giữa chừng.

## 6. Ảo Giác Ngữ Nghĩa (Semantic Hallucination) Trong Trích Xuất Y Văn

- **Vấn đề phát hiện:** Khi chạy pipeline EDC trên dữ liệu hướng dẫn lâm sàng tiểu đường (AACE Guidelines), mô hình OIE liên tục phân loại các thực thể **phi lâm sàng** vào đồ thị tri thức — ví dụ: tên tác giả, tên trường đại học, bệnh viện, ngày xuất bản, chữ viết tắt đứng độc lập. Gây ra các bộ ba vô nghĩa như `[ACE, referred to as, American College of Endocrinology]` hoặc `[Susan Samson MD, is a, Chair]`.
- **Nguyên nhân gốc rễ:** Prompt OIE gốc của EDC được thiết kế cho tập dữ liệu Wikipedia (wiki-nre) — không chứa metadata hành chính. Khi chuyển sang tài liệu y văn, phần mở đầu (danh sách tác giả, thông tin liên kết) bị xử lý như dữ liệu nội dung bình thường.
- **Giải pháp đa lớp (Multi-layer — Defense in Depth):**
  1. **Lớp 1 — Prompt-level (Phòng ngừa):** Tiêm vào `oie_template.txt` danh sách entity type được phép (Disease, Medication, Symptom, Clinical Metric, Anatomical Site) và **STRICT IGNORE LIST** (tên người, bệnh viện, đại học, chữ viết tắt, vai trò hành chính).
  2. **Lớp 2 — Code-level Filter (Chặn lọc):** Xây dựng hàm `filter_clinical_triples()` trong `edc_framework.py` chạy **ngay sau bước OIE**, dùng Regex bắt và loại bỏ triple vi phạm trước khi truyền xuống Schema Definition. Đây là **safety net** đảm bảo tính toàn vẹn bất kể LLM có tuân thủ prompt hay không.
- **Bài học:** Trong Biomedical KG Extraction, không nên chỉ phụ thuộc vào một lớp bảo vệ duy nhất.

## 7. Sự Cố Định Dạng Đầu Ra Của Cohere Command-R (Output Format Bug)

- **Vấn đề:** Model `cohere/command-r7b-12-2024` có xu hướng bổ sung ký tự Markdown (`**`, `_`) vào đầu ra dù được yêu cầu không làm vậy. Gây ra hai lỗi tầng (cascading failures):
  1. **Lỗi tầng 1 (Bước SD):** Hàm `parse_relation_definition()` cắt ra được `**relation_name**` thay vì `relation_name` → Key trong dictionary sai → Toàn bộ bước Canonicalization không match → `canon_kg.txt` hoàn toàn rỗng.
  2. **Lỗi tầng 2 (Bước SC):** Cohere trả về câu dài thay vì 1 chữ cái (A/B/C) cho bài trắc nghiệm → `verification_result[0]` không hợp lệ → Tất cả triplet bị bỏ qua.
- **Hotfix:**
  1. `llm_utils.py` → `parse_relation_definition()`: Thêm `relation = relation.strip("*_\`\"' ")`.
  2. `schema_canonicalization.py` → `llm_verify()`: Tăng `max_tokens=5`; thay `result[0]` bằng vòng lặp quét response tìm ký tự hợp lệ đầu tiên.
- **Lưu ý thiết kế:** Khi tích hợp LLM mới vào pipeline có output cấu trúc nghiêm ngặt, **Output Sanitization** là bắt buộc, không phải tùy chọn.

## 8. Hiệu Chỉnh Schema Cho Phù Hợp Với Ngôn Ngữ Tự Nhiên Của LLM

- **Vấn đề:** Schema gốc dùng `has_subtype`, `may_be_treated_by` (có dấu `_`). OIE trích xuất quan hệ dạng tự nhiên `has subtype`, `may be treated by`. Sự bất đồng định dạng khiến embedding similarity bị giảm hiệu quả.
- **Giải pháp:**
  1. Xóa hết dấu `_` ở cột tên quan hệ trong `diabetes_schema.csv`.
  2. Dùng chính `cohere/command-r7b-12-2024` viết lại 27 định nghĩa — đảm bảo ngôn ngữ phù hợp nhất với cách model encode văn bản.
- **Lợi ích kép:** (1) Cosine similarity OIE↔Schema tăng lên → Canonicalization chính xác hơn. (2) Verifier đọc định nghĩa quen thuộc → suy luận trắc nghiệm tốt hơn.
- **File gốc backup tại:** `schemas/disease/diabetes_schema_backup.csv`.

## 9. Ràng Buộc Miền Ngữ Nghĩa UMLS (Domain/Range Constraints)

- **Vấn đề:** EDC gốc không kiểm tra tính hợp lệ cấu trúc của triplet. Quan hệ `associated condition of` lý ra chỉ nối `[Disease] → [Disease]`, nhưng pipeline không có bộ lọc nên xuất hiện các bộ ba vô nghĩa.
- **Giải pháp:** Tiêm **RELATIONAL CONSTRAINT RULES** dạng `Domain → Range` vào System Prompt OIE. Ví dụ:
  - `[Disease] → may be treated by → [Medication/Therapy]`
  - `[Disease] → has finding site → [Anatomical Site]`
  - `[Symptom] → may be finding of disease → [Disease]`
- **Kết hợp với Code Filter:** `filter_clinical_triples()` kiểm tra vi phạm cấu trúc **trước khi đến Schema Definition**, tránh tốn API call cho triplet sẽ bị loại sau cùng.
- **Tham chiếu lý thuyết:** Áp dụng **Typed Entity Constraints** từ UMLS Semantic Network vào kiến trúc LLM-based KG Extraction — hướng nghiên cứu đang nổi bật trong Biomedical NLP.
