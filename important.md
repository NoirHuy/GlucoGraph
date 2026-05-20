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

---

## 10. Semantic Overgeneralization & Relation Hallucination (Khái quát hóa quá mức & Ảo giác quan hệ)

> **Dataset kiểm chứng:** `aacac4.txt` — Hướng dẫn lâm sàng quản lý insulin cho bệnh tiểu đường  
> **Model:** Llama-3.1-8B-Instruct + Qwen3-Embedding-8B

- **Vấn đề 1 — Semantic Overgeneralization:** Mô hình gom nhiều mối quan hệ lâm sàng khác nhau vào một số ít relation chung (`may be treated by`, `has evaluation`), làm mất ngữ nghĩa. Ví dụ: câu "analog insulins are preferred over NPH" bị trích xuất thành `[diabetes, has contraindicated drug, NPH]` — nhưng "preferred over" ≠ "contraindicated". NPH vẫn là thuốc hợp lệ, chỉ ít được ưu tiên hơn.
- **Vấn đề 2 — Relation Hallucination:** Mô hình tạo ra quan hệ không tồn tại trong văn bản gốc. Ví dụ: "longer half-life of degludec" → `[insulin degludec, cause of, longer]` — "longer" không phải thực thể lâm sàng. Hoặc "without hypoglycemia" → `[fasting blood glucose, may be treated by, hypoglycemia]` — Metric treated by Symptom là vô nghĩa.
- **Nguyên nhân gốc rễ:** Schema quan hệ (Part 4 trong OIE prompt) chỉ có 11 relation types, thiếu hoàn toàn các relation cho **so sánh/ưu tiên**, **tác dụng phụ**, và **điều chỉnh liều**. LLM 8B buộc phải ép mọi relationship vào các lựa chọn hiện có, dẫn đến hallucination.
- **Giải pháp — Mở rộng Relation Schema (`diabetes_schema.csv`):** Thêm 6 relation types mới:

| Relation mới | Domain → Range | Giải quyết |
|-------------|----------------|-----------|
| `is preferred over` | Drug → Drug | So sánh thuốc (không còn bị ép thành "contraindicated") |
| `has adverse effect` | Drug → Symptom | Tác dụng phụ (không còn bị ép thành "cause of") |
| `has dose adjustment` | Drug → Dosage Value | Quy tắc chỉnh liều |
| `has clinical threshold` | Clinical Metric → Dosage Value | Ngưỡng lâm sàng |
| `may be substituted by` | Drug → Drug | Thuốc thay thế |
| `should be discontinued with` | Drug → Drug | Ngưng thuốc khi bắt đầu thuốc khác |

> **Thảo luận học thuật (Discussion):** Một trong những giới hạn lớn nhất của việc sử dụng các Lược đồ bản thể học chuẩn (như UMLS Semantic Network) là sự thiếu hụt từ vựng để biểu diễn các quy tắc điều trị mang tính thủ tục, định lượng và so sánh. Quá trình thực nghiệm trên tập dữ liệu aacac4 (AACE Guidelines) đã chỉ ra hiện tượng Semantic Overgeneralization (Khái quát hóa quá mức) khi LLM bị ép sử dụng các quan hệ UMLS chuẩn. Để khắc phục, nghiên cứu này đề xuất mở rộng Lược đồ chuẩn bằng việc bổ sung các quan hệ đặc thù cho Hướng dẫn lâm sàng như `has dose adjustment`, `has clinical threshold`, `is preferred over`, giúp Knowledge Graph giữ lại được tính logic điều kiện của phác đồ điều trị mà không bị mất mát thông tin.

## 11. Directionality Error & Ontology Mismatch (Lỗi hướng quan hệ & Sai lệch bản thể học)

- **Vấn đề 1 — Directionality Error:** Subject và object bị đảo ngược ~15% trường hợp, vi phạm hướng bản thể học. Ví dụ: `[basal insulin, may be treated by, diabetes]` (Drug treated by Disease — SAI) thay vì `[diabetes, may be treated by, basal insulin]` (Disease treated by Drug — ĐÚNG). Tương tự: `[prandial insulin, may be treated by, diabetes]`.
- **Vấn đề 2 — Ontology Mismatch:** Thực thể bị đặt sai vị trí domain/range. Ví dụ: `[fasting blood glucose, has finding site, blood glucose]` — Metric "finding site" của chính nó (tautology). Hoặc `[prandial insulin, component of, number of meals]` — "number of meals" không phải thực thể y tế.
- **Nguyên nhân gốc rễ:** OIE prompt đã có Rule 1 quy định hướng, nhưng mô hình 8B không tuân thủ 100%. Không có cơ chế enforcement hậu-OIE.
- **Giải pháp — Module Semantic Validator (`edc/semantic_validator.py`):** Tạo module validation data-driven mới chạy ngay **sau Phase 1 (OIE)** và **trước Phase 2 (Schema Definition)**, tạo thành **Phase 1.5** trong pipeline:

| Kiểm tra | Mô tả | Kết quả test |
|----------|-------|-------------|
| **Directionality Auto-Correction** | Phát hiện Drug → `may be treated by` → Disease → tự động đảo thành Disease → Drug | ✅ `[basal insulin, may be treated by, diabetes]` → `[diabetes, may be treated by, basal insulin]` |
| **Non-Entity Detection** | Loại bỏ triple có object là tính từ trơn (`longer`, `fewer`), từ trừu tượng (`simplicity`, `adherence`) | ✅ `[insulin degludec, cause of, longer]` → Discarded |
| **Tautology Detection** | Loại bỏ triple có subject = object | ✅ Hoạt động |
| **Redundancy Detection** | Loại bỏ triple có object nằm trong subject | ✅ `[fasting blood glucose, has finding site, blood glucose]` → Discarded |

## 12. Thiếu Biểu Diễn Cấu Trúc Điều Kiện / Định Lượng / Procedural Reasoning

- **Vấn đề:** Các dòng 12-17, 21-28 trong aacac4 mô tả quy tắc điều chỉnh liều insulin với điều kiện (IF glucose > X THEN adjust dose by Y%). Schema cũ không có cách biểu diễn, khiến thông tin quan trọng bị mất hoàn toàn hoặc bị ép sai relation.
  - Ví dụ: "increased by 20% if FBG >180 mg/dL" → chỉ sinh được `[Type 2 Diabetes, may be treated by, basal insulin]` — mất hoàn toàn ngưỡng và phần trăm điều chỉnh.
  - Ví dụ: "decreased by 10-20% if FBG <70 mg/dL" → ngưỡng hạ đường huyết và quy tắc điều chỉnh bị mất.
- **Giải pháp — OIE Prompt Rule 7 (MỚI) + Entity Type `Dosage Value`:**
  - **Tách conditional knowledge thành 2 triple riêng biệt:**
    - `[Drug, has dose adjustment, Dosage Value]` — hành động điều chỉnh
    - `[Clinical Metric, has clinical threshold, Dosage Value]` — điều kiện kích hoạt
  - **Thêm entity type `Dosage Value`** vào `diabetes_entity_type_schema.csv` — bao phủ các giá trị định lượng (`20%`, `<110 mg/dL`, `5 units`).
  - Ví dụ đúng: "basal insulin dose increased by 20% if FBG >180 mg/dL" → `[basal insulin, has dose adjustment, increase by 20%]` + `[fasting blood glucose, has clinical threshold, >180 mg/dL]`

## 13. Cải Thiện Few-Shot Examples & Prompt Template

- **OIE Few-Shot Examples (`oie_few_shot_examples.txt`):** Mở rộng từ **16 → 22 examples**, bao gồm ví dụ cho mọi pattern mới:
  - Ex 10-11: `is preferred over` (analog insulins vs NPH, rapid-acting vs regular)
  - Ex 12: `should be discontinued with` (SUs discontinued with basal insulin)
  - Ex 13-15: `has dose adjustment` + `has clinical threshold` (titration rules)
  - Ex 16: `has adverse effect` (premixed insulin → hypoglycemia)
  - Ex 17-18: Combination therapy + prandial insulin dosing
  - Ex 21-22: Premeal glucose titration + hypoglycemia education
- **OIE Prompt Template (`oie_template.txt`):** Thêm Rule 6 (Comparison/Preference) và Rule 7 (Conditional/Titration/Dose). Mở rộng ignore list thêm bare adjectives và abstract non-entities. Mở rộng relational schema Part 4 thêm 6 relation mới.
- **SD Few-Shot Examples (`sd_few_shot_examples_with_entities.txt`):** Mở rộng từ **4 → 7 examples**, thêm ví dụ cho `Dosage Value` entity type và các relation mới.
- **SD Template (`sd_template_with_entities.txt`):** Cập nhật entity type list — thêm `Dosage Value`, bỏ `Clinical Guideline`.

## 14. Tổng Kết Kiến Trúc Pipeline Sau Cải Thiện (v2)

Pipeline sau cải thiện có **4.5 phases** thay vì 4 phases ban đầu:

```
Phase 1 (OIE) → Phase 1.5 (Semantic Validator) → Phase 2 (Schema Definition) → Phase 3a (Relation Canonicalization) → Phase 3b (Entity Type Canonicalization)
```

**Các file thay đổi:**

| # | File | Thay đổi |
|---|------|----------|
| 1 | `schemas/disease/diabetes_schema.csv` | +6 relation types mới |
| 2 | `schemas/disease/diabetes_entity_type_schema.csv` | +1 entity type (Dosage Value) |
| 3 | `prompt_templates/oie_template.txt` | +2 rules, mở rộng schema & ignore list |
| 4 | `few_shot_examples/diabetic/oie_few_shot_examples.txt` | 16→22 examples |
| 5 | `few_shot_examples/diabetic/sd_few_shot_examples_with_entities.txt` | 4→7 examples |
| 6 | `edc/semantic_validator.py` | **Module mới** — post-OIE validation |
| 7 | `edc/edc_framework.py` | Tích hợp validator Phase 1.5, thêm `oie_raw` vào output |
| 8 | `prompt_templates/sd_template_with_entities.txt` | Thêm `Dosage Value` entity type |

**Lệnh chạy pipeline v2:**
```powershell
python run.py `
  --oie_llm meta-llama/Llama-3.1-8B-Instruct `
  --sd_llm meta-llama/Llama-3.1-8B-Instruct `
  --sc_llm meta-llama/Llama-3.1-8B-Instruct `
  --sc_embedder qwen/qwen3-embedding-8b `
  --ee_llm meta-llama/Llama-3.1-8B-Instruct `
  --oie_few_shot_example_file_path ./few_shot_examples/diabetic/oie_few_shot_examples.txt `
  --sd_few_shot_example_file_path ./few_shot_examples/diabetic/sd_few_shot_examples_with_entities.txt `
  --sd_prompt_template_file_path ./prompt_templates/sd_template_with_entities.txt `
  --input_text_file_path ./datasets/disease/diabetes/aacac4.txt `
  --target_schema_path ./schemas/disease/diabetes_schema.csv `
  --target_entity_type_schema_path ./schemas/disease/diabetes_entity_type_schema.csv `
  --output_dir ./output/aacac4_v2_improved
```
