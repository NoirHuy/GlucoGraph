# Hướng dẫn xây dựng Triple Validity Benchmark từ BioRED
## (Thay thế cho "HaluEval tự xây dựng" trong bài GlucoGraph)

---

## TỔNG QUAN QUY TRÌNH

```
BioRED (raw) 
   → Lọc subset Diabetes 
   → Tách Positive Triples (ground truth)
   → Sinh Negative Triples (3 phương pháp corruption)
   → Cân bằng & lấy mẫu
   → Annotation thủ công (2 người) + Cohen's kappa
   → Bộ dữ liệu cuối (CSV/JSON) → đưa vào P2P Debate Gate
   → Tính TRR, FPR, FNR, F1 theo từng loại corruption
```

---

## BƯỚC 1 — Tải dữ liệu BioRED

BioRED được công bố công khai tại:
- NCBI FTP: `https://ftp.ncbi.nlm.nih.gov/pub/lu/BioRED/`
- Hoặc PubTator3 / Hugging Face: `bigbio/biored`

Dataset có 3 file: `Train.BioC.XML`, `Dev.BioC.XML`, `Test.BioC.XML` (hoặc dạng PubTator `.txt`).

Mỗi document gồm:
- **Passages**: title + abstract
- **Annotations (entities)**: mỗi entity có `type` (GeneOrGeneProduct, DiseaseOrPhenotypicFeature, ChemicalEntity, SequenceVariant, OrganismTaxon, CellLine) và `identifier` (MeSH ID / NCBI Gene ID)
- **Relations**: cặp `(entity1_id, entity2_id, relation_type, novelty)`

8 loại relation trong BioRED: `Positive_Correlation`, `Negative_Correlation`, `Association`, `Bind`, `Comparison`, `Cotreatment`, `Drug_Interaction`, `Conversion`.

> ⚠️ Lưu ý: môi trường sandbox của tôi không truy cập được NCBI FTP / HuggingFace. Bạn cần tải file này trên máy cá nhân, sau đó dùng script ở Bước 4 để xử lý.

---

## BƯỚC 2 — Lọc subset liên quan Diabetes

Lọc các document/relation có chứa các MeSH ID liên quan đái tháo đường:

| MeSH ID | Khái niệm |
|---|---|
| D003920 | Diabetes Mellitus |
| D003922 | Diabetes Mellitus, Type 1 |
| D003924 | Diabetes Mellitus, Type 2 |
| D003925 | Diabetes, Gestational |
| D007328 | Insulin |
| D008687 | Metformin |
| D003923 | Diabetic Nephropathies |
| D003929 | Diabetic Retinopathy |

Có thể mở rộng danh sách bằng UMLS hoặc MeSH tree hierarchy (lấy tất cả con của `C18.452.394` - Diabetes Mellitus branch).

**Kết quả mong đợi**: một subset gồm vài chục document, mỗi document có entity list + relation list — đây chính là **Positive Triples (ground truth)** của bạn.

---

## BƯỚC 3 — Ánh xạ Relation Type của BioRED sang Schema KG của bạn

BioRED dùng 8 relation type chung, trong khi GlucoGraph dùng các relation cụ thể (TREATS, CAUSES, ASSOCIATED_WITH...). Bảng ánh xạ gợi ý:

| BioRED Relation | Entity pair | → GlucoGraph Relation |
|---|---|---|
| Positive_Correlation | Chemical–Disease | INCREASES_RISK_OF |
| Negative_Correlation | Chemical–Disease | TREATS / REDUCES_RISK_OF |
| Positive_Correlation | Gene–Disease | ASSOCIATED_WITH (risk factor) |
| Association | (any pair) | ASSOCIATED_WITH |
| Drug_Interaction | Chemical–Chemical | INTERACTS_WITH |
| Cotreatment | Chemical–Chemical | COADMINISTERED_WITH |
| Bind | Gene–Chemical | BINDS_TO |
| Comparison | Chemical–Chemical | COMPARED_WITH |

Bạn nên đưa bảng này vào Appendix của bài báo — nó cho thấy quy trình ánh xạ có hệ thống, không phải tùy tiện.

---

## BƯỚC 4 — Sinh Negative Triples: 3 phương pháp Corruption

### 4.1. Entity Substitution (thay thế thực thể)
Giữ nguyên `(Subject, Relation)`, thay `Object` bằng một entity **khác cùng semantic type** nhưng KHÔNG xuất hiện trong bất kỳ relation thật nào với Subject đó.

> Ví dụ: `(Metformin, TREATS, Type 2 Diabetes)` → `(Metformin, TREATS, Diabetic Retinopathy)` — sai vì Metformin không điều trị biến chứng võng mạc.

### 4.2. Relation Inversion (đảo quan hệ)
Giữ nguyên `(Subject, Object)`, đổi `Relation` thành quan hệ **đối nghịch về mặt y học** (dựa trên ma trận tương thích bạn tự định nghĩa).

> Ví dụ: `(Metformin, TREATS, Type 2 Diabetes)` → `(Metformin, CAUSES, Type 2 Diabetes)` — đảo ngược hoàn toàn ý nghĩa lâm sàng.

### 4.3. Schema/Domain-Range Violation (vi phạm ràng buộc schema)
Tạo triple trong đó cặp `(Subject_type, Object_type)` **không hợp lệ** với Relation đó theo schema KG.

> Ví dụ: `(Insulin, BINDS_TO, Type 2 Diabetes)` — relation `BINDS_TO` chỉ hợp lệ cho cặp Gene–Chemical, không hợp lệ cho Chemical–Disease.

### Lưu ý quan trọng: tránh "false negative"
Một corrupted triple có thể **vô tình đúng** trong thực tế (ví dụ thuốc A thật sự cũng điều trị bệnh B nhưng BioRED không ghi). Để giảm rủi ro:
- Loại bỏ candidate nếu nó xuất hiện trong **bất kỳ** relation thật nào của toàn bộ BioRED (không chỉ subset diabetes)
- Annotator có quyền gắn nhãn "Uncertain" thay vì ép Valid/Invalid

---

## BƯỚC 5 — Cân bằng và lấy mẫu

- Tỷ lệ khuyến nghị: **1:1** Positive : Negative
- Trong phần Negative, chia đều 3 loại corruption (ví dụ mỗi loại ~33%)
- Kích thước mẫu: nếu BioRED diabetes subset cho ra ~80-120 positive triples, bạn có thể tạo 80-120 negative tương ứng → tổng **160-240 triples**, lớn hơn đáng kể so với 100 mẫu tự tạo trước đây.

---

## BƯỚC 6 — Annotation Protocol (để báo cáo Cohen's kappa)

1. **2 annotator độc lập** (có thể là 2 thành viên nhóm nghiên cứu, ưu tiên 1 người có background y khoa/dược)
2. Mỗi annotator nhận file CSV **không có cột label gốc và corruption_type** (blind annotation)
3. Mỗi triple gán nhãn: `Valid` / `Invalid` / `Uncertain`
4. Annotator được cung cấp **annotation guideline** (xem mẫu trong script `annotation_guideline.md`)
5. Sau khi cả 2 hoàn thành, tính **Cohen's kappa**
6. Các case bất đồng → annotator thứ 3 (hoặc đồng thuận thảo luận) phân xử

**Diễn giải kappa** (Landis & Koch):
- κ ≥ 0.81: Almost perfect
- 0.61–0.80: Substantial
- 0.41–0.60: Moderate

Báo cáo κ ≥ 0.75 là đủ thuyết phục cho reviewer.

---

## BƯỚC 7 — Đưa vào P2P Debate Gate và tính metrics

Với mỗi triple trong bộ dữ liệu cuối (đã có ground truth label `valid`/`invalid`):
1. Đưa triple qua pipeline 3-agent debate như input thực tế từ extraction module
2. Ghi lại quyết định của hệ thống: `Accept` (đẩy vào Neo4j) hoặc `Reject`
3. So khớp với ground truth:

| | System: Accept | System: Reject |
|---|---|---|
| Ground truth: Valid | True Positive | False Negative |
| Ground truth: Invalid | False Positive | True Negative |

Từ đó tính:
- **TRR** (Triple Retention Rate) = TP / (TP+FN) — trên các triple Valid
- **FPR** = FP / (FP+TN) — trên các triple Invalid (đây chính là hallucination lọt qua)
- **F1** chung

**Quan trọng**: báo cáo riêng FPR theo từng loại corruption (Entity Substitution / Relation Inversion / Schema Violation) — đây là phần phân tích sâu mà bài cũ đang thiếu, và sẽ là điểm cộng lớn.

---

## CÁCH VIẾT LẠI TRONG METHODOLOGY SECTION

Gợi ý đoạn văn mẫu (paraphrase theo văn phong của bạn):

> "To construct a triple-level hallucination benchmark, we derived a Diabetes-related subset from BioRED [ref], a human-curated biomedical relation extraction corpus. Ground-truth relations within this subset (N=XX) served as positive (valid) triples. Negative (hallucinated) triples were systematically generated via three corruption strategies: (1) entity substitution, replacing the object entity with another entity of identical semantic type absent from any true relation; (2) relation inversion, replacing the predicate with a clinically contradictory relation type; and (3) schema violation, pairing entities whose types violate the domain/range constraints of the target relation. The resulting dataset (N=YY, balanced 1:1) was independently annotated by two reviewers, achieving a Cohen's kappa of ZZ, with disagreements resolved through adjudication."

---

## CHECKLIST FILES CẦN TẠO

1. `biored_diabetes_subset.json` — positive triples đã lọc
2. `negative_triples.json` — negative triples theo 3 loại
3. `annotation_sheet.csv` — file blind cho 2 annotator
4. `final_benchmark.csv` — bộ dữ liệu cuối có label đã thống nhất
5. `results_by_corruption_type.csv` — kết quả P2P Debate Gate theo từng loại
