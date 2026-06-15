# Hướng dẫn xây dựng Triple Validity Benchmark tự động từ BioRED
## (Phương pháp Gán nhãn Thuật toán tự động - Algorithmic Ground Truth)

---

## TỔNG QUAN QUY TRÌNH TỰ ĐỘNG HÓA

```
BioRED (raw) 
   → Lọc subset Diabetes 
   → Tách Positive Triples ( ground truth - tự động thừa nhận )
   → Sinh thuật toán & Kiểm duyệt chéo bằng Code (3 kỹ thuật Corruption)
   → Bộ dữ liệu cuối (CSV/JSON - nhãn Valid/Invalid xác định bởi thuật toán)
   → Chạy thử qua P2P Debate Gate
   → Tính TRR, FPR, FNR, F1 theo từng loại corruption tự động
```

Quy trình này loại bỏ hoàn toàn việc gán nhãn thủ công của con người (Manual Annotation), thay vào đó sử dụng tính chuẩn hóa của dataset gốc (BioRED) làm tập đúng và các thuật toán ràng buộc ngữ nghĩa y học/lược đồ làm tập bẫy ảo giác.

---

## BƯỚC 1 — Tải dữ liệu BioRED

Dữ liệu BioRED gốc gồm 3 file: `Train.BioC.XML`, `Dev.BioC.XML`, `Test.BioC.XML` (hoặc định dạng PubTator `.txt`), chứa các thông tin thực thể y sinh và quan hệ giữa chúng đã được chuyên gia của NCBI gán nhãn thủ công.

Mỗi document gồm:
- **Passages**: Tiêu đề và tóm tắt nghiên cứu (Title + Abstract).
- **Annotations (Entities)**: Mỗi thực thể có `type` (Gene, Chemical, Disease...) và `identifier` (MeSH ID).
- **Relations**: Cặp quan hệ thực tế `(entity1_id, entity2_id, relation_type)`.

---

## BƯỚC 2 — Lọc subset liên quan Diabetes (Tập Positive)

Lọc các tài liệu và bộ ba quan hệ y sinh thực tế có chứa các MeSH ID liên quan đến bệnh tiểu đường trong BioRED:

| MeSH ID | Khái niệm y sinh |
|---|---|
| D003920 | Diabetes Mellitus |
| D003922 | Diabetes Mellitus, Type 1 |
| D003924 | Diabetes Mellitus, Type 2 |
| D003925 | Diabetes, Gestational |
| D007328 | Insulin |
| D008687 | Metformin |
| D003923 | Diabetic Nephropathies |
| D003929 | Diabetic Retinopathy |

Tập bộ ba trích xuất được từ bước này được tự động gán nhãn là **`Valid` (Ground Truth - Đúng)** vì chúng kế thừa trực tiếp từ dữ liệu thực tế do NCBI công bố.

---

## BƯỚC 3 — Ánh xạ Quan hệ (Relation Mapping)

Ánh xạ các kiểu quan hệ khái quát của BioRED sang các kiểu quan hệ chuyên sâu của hệ thống **GlucoGraph**:

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

---

## BƯỚC 4 — Thuật toán Sinh và Kiểm duyệt Bộ ba Ảo giác (Tập Negative)

Thuật toán Python sẽ sinh ra các bộ ba ảo giác (Negative) và kiểm duyệt tự động để gán nhãn là **`Invalid` (Sai)** theo 3 cơ chế lỗi:

### 4.1. Entity Substitution (Thuật toán Thay thế Thực thể)
* **Quy trình:** Giữ nguyên `(Subject, Relation)`, tìm kiếm ngẫu nhiên một thực thể `Object_Candidate` có **cùng loại thực thể** (semantic type) với Object gốc nhưng KHÔNG xuất hiện trong bất kỳ quan hệ nào với Subject đó trong toàn bộ dữ liệu BioRED.
* **Kiểm duyệt tự động:** Kiểm tra chéo (Cross-reference) bộ ba mới tạo ra. Nếu bộ ba đó hoàn toàn không tồn tại trong tập dữ liệu BioRED hoặc y văn Merck Manuals, thuật toán sẽ tự động gán nhãn bộ ba này là **`Invalid`**.
* *Ví dụ:* `(Metformin, TREATS, Type 2 Diabetes)` $\rightarrow$ `(Metformin, TREATS, Diabetic Retinopathy)` (Tự động gán nhãn `Invalid` vì Metformin không điều trị võng mạc).

### 4.2. Relation Inversion (Thuật toán Đảo ngược Quan hệ)
* **Quy trình:** Giữ nguyên `(Subject, Object)`, thay thế quan hệ y học gốc bằng một quan hệ **đối nghịch lâm sàng** (dựa trên ma trận nghịch đảo).
* **Kiểm duyệt tự động:** Ví dụ quan hệ nghịch đảo của `TREATS` là `CAUSES` hoặc `INCREASES_RISK_OF` đối với cặp thực thể Drug–Disease. Bộ ba đảo ngược sau khi tạo ra sẽ được gán nhãn **`Invalid`**.
* *Ví dụ:* `(Metformin, TREATS, Type 2 Diabetes)` $\rightarrow$ `(Metformin, CAUSES, Type 2 Diabetes)` (Thuật toán gán nhãn `Invalid` do đảo nghịch ý nghĩa y học lâm sàng).

### 4.3. Schema/Domain-Range Violation (Thuật toán Vi phạm Lược đồ)
* **Quy trình:** Tạo bộ ba trong đó kiểu thực thể của Subject hoặc Object **vi phạm trực tiếp** quy định Domain/Range của quan hệ đó.
* **Kiểm duyệt tự động:** Thuật toán đọc file lược đồ `diabetes_schema.csv`. Ví dụ quan hệ `BINDS_TO` bắt buộc phải là Gene–Chemical. Nếu bộ ba có thực thể đích là Disease, code sẽ tự động phát hiện vi phạm và gắn nhãn **`Invalid`**.
* *Ví dụ:* `(Insulin, BINDS_TO, Type 2 Diabetes)` (Thuật toán gán nhãn `Invalid` do vi phạm domain/range của lược đồ định sẵn).

---

## BƯỚC 5 — Tự động Cân bằng và Xuất dữ liệu

Mã nguồn Python sẽ thực hiện:
1. Lấy mẫu $N$ bộ ba đúng (Valid) từ subset BioRED.
2. Sinh thuật toán $N$ bộ ba sai (Invalid) chia đều cho 3 loại lỗi trên (~33% mỗi loại).
3. Trộn ngẫu nhiên (Shuffle) và xuất trực tiếp ra file dẹt `final_benchmark.json`.
4. **Đồng thời tự động chuyển đổi định dạng và xuất** thành 2 tập tin đầu vào y học cho HaluEval (`dataset.json` và `references.txt`) lưu vào thư mục:
   `HaluEval/data/<size>_triples/` (Ví dụ: `HaluEval/data/200_triples/`).

Không cần bất kỳ sự tham gia nào của chuyên gia hay quá trình gán nhãn thủ công tốn thời gian.

---

## BƯỚC 6 — Chạy Đánh giá qua P2P Debate Gate và Tính Metrics

Sau khi sinh dữ liệu ở Bước 5, bạn chạy lệnh đánh giá tích hợp:
```powershell
.venv\Scripts\python HaluEval/run.py --size <kích_thước>
```
*(Ví dụ: `--size 200`)*

Hệ thống sẽ tự động thực hiện:
1. Đọc từng bộ ba từ tập dữ liệu `dataset.json` tương ứng và đưa vào P2P Debate Gate.
2. Lấy quyết định của hệ thống: `Accept` (Chấp nhận) hoặc `Reject` (Từ chối).
3. So khớp chéo với nhãn chuẩn trong file `references.txt`.
4. Tính toán các chỉ số tự động và hiển thị báo cáo:
   * **Accuracy (Độ chính xác):** Tỷ lệ phân loại đúng trên tổng số bộ ba.
   * **False Negative Rate (FNR - Rò rỉ):** Tỷ lệ bẫy ảo giác bị chấp nhận lọt lưới.
   * **False Positive Rate (FPR - Từ chối nhầm):** Tỷ lệ bộ ba y học đúng bị từ chối.
   * **Trap Rejection Rate (TRR - Chặn bẫy thành công):** Tỷ lệ chặn đứng thành công các bẫy ảo giác.
5. Xuất báo cáo kết quả chi tiết kèm phân tích danh sách bộ ba bị lỗi ra thư mục `HaluEval/output/<size>_triples/summary.json`.

---

## MẪU GIẢI TRÌNH PHƯƠNG PHÁP TRONG BÀI BÁO (ACADEMIC WRITING)

Khi viết bài báo khoa học, bạn sử dụng đoạn văn sau để giải trình tính khoa học của phương pháp gán nhãn tự động này:

> *"To establish a rigorous, reproducible, and objective triple-level hallucination benchmark without subjective human annotation bias, we proposed an algorithmic ground-truth validation pipeline derived from the expert-curated BioRED dataset. Ground-truth relations within the diabetes subset of BioRED served as valid (positive) triples. Corrupted (negative) triples were programmatically generated using three distinct strategies: entity substitution, relation inversion, and schema violation. To ensure validity, a corrupted triple was algorithmically labeled as 'Invalid' only if it strictly violated the domain/range constraints of the reference ontology, or was cross-referenced to ensure zero occurrence in both the BioRED corpus and the Merck Manuals. This programmatic framework yields a deterministic evaluation set suited for benchmarking multi-agent debate performance."*
