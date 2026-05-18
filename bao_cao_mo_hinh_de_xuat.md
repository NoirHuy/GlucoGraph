# BÁO CÁO MÔ HÌNH ĐỀ XUẤT

| TRƯỜNG ĐẠI HỌC NAM CẦN THƠ – KHOA CÔNG NGHỆ THÔNG TIN | CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM |
|:---|:---|
| | Độc lập – Tự do – Hạnh phúc |

**Tên đề tài:** Ứng dụng LLM xây dựng đồ thị tri thức chẩn đoán bệnh tiểu đường
**Sinh viên:** Lê Quang Huy – MSSV: 223571 – Lớp: DH22KPM01
**Giảng viên hướng dẫn:** ThS. Trần Văn Thiện
**Khoa:** Công Nghệ Thông Tin – Trường Đại học Nam Cần Thơ

---

## 1. LÝ DO CHỌN ĐỀ TÀI

Đái tháo đường (tiểu đường) là một trong những gánh nặng lớn nhất của hệ thống y tế hiện đại, đòi hỏi quá trình quản lý, theo dõi và ra quyết định lâm sàng hết sức chặt chẽ.

Tại **Đồ án chuyên ngành 2**, việc ứng dụng framework **EDC (Extract–Define–Canonicalize)** đã cho thấy tiềm năng lớn trong tự động hóa trích xuất tri thức y khoa vào đồ thị tri thức với phạm vi dinh dưỡng tổng quát cho 5 bệnh (tiểu đường, cao huyết áp, gút, béo phì, suy thận). Tuy nhiên, để phát triển thành một hệ thống **hỗ trợ chẩn đoán chuyên sâu riêng cho bệnh tiểu đường**, cần giải quyết hai thách thức lớn:

- **Thách thức 1:** Dữ liệu y văn lâm sàng về tiểu đường chứa rất nhiều định dạng phi cấu trúc và bảng biểu phức tạp. Nếu chỉ phân đoạn (chunking) thông thường sẽ dễ dẫn đến **mất mát ngữ cảnh y khoa**.
- **Thách thức 2:** Quá trình trích xuất thông tin mở (OIE) dễ sinh ra lỗi thiếu sót hoặc dư thừa nếu LLM **thiếu định hướng về Schema** trong ngữ cảnh rộng.

Ngoài ra, kết quả từ Đồ án 2 và EDC gốc cho thấy điểm **F1 Full Triple chỉ đạt 53%** – cần phải cải thiện đáng kể để ứng dụng thực tiễn trong y tế.

**Do đó,** đề tài Khóa luận này tập trung xây dựng đồ thị tri thức chẩn đoán chuyên biệt cho bệnh tiểu đường, bổ sung kỹ thuật **NLG (Natural Language Generation)** vào tiền xử lý và tích hợp **Schema Retriever** để tăng độ chính xác trích xuất.

---

## 2. PHẠM VI VÀ NỘI DUNG NGHIÊN CỨU

### 2.1 Đối tượng và phạm vi

- **Đối tượng nghiên cứu:** Các mô hình ngôn ngữ lớn (LLM), Đồ thị tri thức (Knowledge Graph), kỹ thuật tiền xử lý NLG và framework EDC+R.
- **Phạm vi:** Toàn bộ dữ liệu, quan hệ và kiến thức lâm sàng **giới hạn chuyên sâu cho bệnh tiểu đường**.

### 2.2 Nội dung thực hiện

| # | Nội dung | Công nghệ |
|---|---|---|
| 1 | Thu thập và tiền xử lý dữ liệu y văn tiểu đường | NLG – Text-to-Text Generation |
| 2 | Trích xuất thực thể và quan hệ bằng LLM | EDC+R, Schema Retriever, Embedding |
| 3 | Chuẩn hóa và xây dựng đồ thị tri thức | Neo4j, Cypher |
| 4 | Xây dựng hệ thống CDSS và đánh giá | GraphRAG, Circuit Breaker, F1 Score |

---

## 3. TỔNG QUAN NGHIÊN CỨU

### 3.1 Các công trình liên quan

| Công trình | Đóng góp | Hạn chế |
|---|---|---|
| EDC – Zhang & Soh (EMNLP 2024) [2] | Framework OIE+SC tự động hóa KGC | F1 Full Triple chỉ 53%, không có NLG |
| GenIE, CodeKGC, ChatIE | Các baseline KGC với LLM | F1 thấp, thiếu Schema Retriever |
| Lyu et al. (2026) [3] | NLG chuẩn hóa dữ liệu y tế | Chưa tích hợp vào pipeline KGC |
| Đồ án 2 – Lê Quang Huy (2026) [1] | Thử nghiệm EDC cho dinh dưỡng đa bệnh | F1=53%, phạm vi rộng, chưa chuyên sâu |

### 3.2 Khoảng trống nghiên cứu

EDC gốc có **3 điểm nghẽn** khi áp dụng vào y tế chuyên sâu:

1. **Thiếu NLG tiền xử lý:** Tài liệu y văn có bảng biểu, số liệu phức tạp → mất ngữ cảnh khi chunking thô.
2. **Chi phí hạ tầng cao:** Yêu cầu Local LLM (Mistral-7B) trên GPU mạnh.
3. **Zero-parameter tuning:** Không có cơ chế tinh chỉnh lặp dựa trên Schema → bỏ sót quan hệ y khoa phức tạp.

### 3.3 Giải pháp đề xuất

> **Bổ sung NLG vào tiền xử lý + Tích hợp Schema Retriever vào EDC+R**, hướng đến nâng F1 vượt mức 53% hiện tại trong lĩnh vực chẩn đoán tiểu đường.

---

## 4. MÔ HÌNH ĐỀ XUẤT

### 4.1 Kiến trúc tổng quan

```
┌─────────────────────────────────────────────────────┐
│              NGUỒN DỮ LIỆU Y VĂN                   │
│  Hướng dẫn điều trị │ Bảng biểu lâm sàng │ Y văn   │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│  [MỚI] TIỀN XỬ LÝ NLG (Text-to-Text Generation)    │
│  Bảng biểu → Văn xuôi │ Phi cấu trúc → Có cấu trúc │
└─────────────────────┬───────────────────────────────┘
                      │ Văn bản sạch
                      ▼
┌─────────────────────────────────────────────────────┐
│  GIAI ĐOẠN 1: Trích xuất Mở (OIE)                  │
│  LLM: Llama 3.3/4 hoặc GPT-4o                       │
│  Few-shot Prompting + Schema hints                   │
└─────────────────────┬───────────────────────────────┘
                      │ Bộ ba thô (S, R, O)
                      ▼
┌─────────────────────────────────────────────────────┐
│  GIAI ĐOẠN 2: Định nghĩa Lược đồ (SD)              │
│  LLM tự định nghĩa ngữ nghĩa quan hệ theo ngữ cảnh │
└─────────────────────┬───────────────────────────────┘
                      │ {quan hệ → định nghĩa}
                      ▼
┌─────────────────────────────────────────────────────┐
│  GIAI ĐOẠN 3: Chuẩn hóa Lược đồ (SC)              │
│  Embedding: jina-embeddings-v3 (Jina AI API)        │
│  Retrieval top-k → LLM xác minh → Canonical triple  │
└─────────────────────┬───────────────────────────────┘
                      │ Bộ ba chuẩn hóa
                      ▼
┌─────────────────────────────────────────────────────┐
│  [MỚI] GIAI ĐOẠN 4: Tinh chỉnh EDC+R              │
│  Schema Retriever + Entity Extraction/Merging       │
│  → Iterative Refinement (lặp để tăng F1)            │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│  ĐỒ THỊ TRI THỨC – Neo4j                           │
│  Node: Triệu chứng, Xét nghiệm, Thuốc, Biến chứng  │
│  Edge: Quan hệ lâm sàng tiểu đường                  │
└─────────────────────┬───────────────────────────────┘
                      │ GraphRAG + Circuit Breaker
                      ▼
┌─────────────────────────────────────────────────────┐
│  HỆ THỐNG CDSS – Web hỗ trợ ra quyết định lâm sàng │
└─────────────────────────────────────────────────────┘
```

### 4.2 Chi tiết các giai đoạn

#### [MỚI] Tiền xử lý NLG

**Vấn đề:** Tài liệu y văn tiểu đường thường gồm bảng biểu chỉ số (HbA1c, glucose huyết tương, BMI...), danh sách thuốc phức tạp, sơ đồ điều trị – nếu đưa trực tiếp vào LLM sẽ mất ngữ cảnh.

**Giải pháp:** Sử dụng kỹ thuật **Text-to-Text NLG** để:
- Chuyển bảng biểu → đoạn văn xuôi có ngữ nghĩa đầy đủ.
- Chuẩn hóa thuật ngữ y khoa về dạng thống nhất.
- Đảm bảo toàn vẹn các giá trị định lượng quan trọng.

---

#### Giai đoạn 1 – Trích xuất Mở (OIE)

**Đầu vào:** Văn bản y văn đã qua NLG.

**Kỹ thuật:** Few-shot Prompting với các ví dụ lâm sàng tiểu đường + gợi ý Schema từ Schema Retriever.

**Đầu ra mẫu:**
```
("HbA1c > 6.5%",   "là tiêu chí chẩn đoán",  "Đái tháo đường type 2")
("Metformin",       "là thuốc đầu tay",         "Đái tháo đường type 2")
("Béo phì",         "là yếu tố nguy cơ",        "Kháng Insulin")
("Glucose lúc đói", "ngưỡng chẩn đoán",         "≥ 126 mg/dL")
```

---

#### Giai đoạn 2 – Định nghĩa Lược đồ (SD)

LLM nhận bộ ba + đoạn văn gốc → tự sinh định nghĩa ngữ nghĩa cho từng quan hệ.

**Ví dụ:** `"là tiêu chí chẩn đoán"` → *"Quan hệ mô tả một chỉ số xét nghiệm hoặc triệu chứng lâm sàng được dùng để xác định chính thức sự hiện diện của bệnh."*

---

#### Giai đoạn 3 – Chuẩn hóa Lược đồ (SC)

**Lược đồ quan hệ mục tiêu cho tiểu đường:**

| Quan hệ chuẩn | Ý nghĩa |
|---|---|
| `chẩn_đoán_bởi` | Bệnh được xác định qua chỉ số/xét nghiệm |
| `là_yếu_tố_nguy_cơ` | Yếu tố làm tăng khả năng mắc bệnh |
| `gây_ra_biến_chứng` | Bệnh/tình trạng dẫn đến biến chứng |
| `điều_trị_bằng` | Phác đồ/thuốc được dùng điều trị |
| `cần_theo_dõi` | Chỉ số cần kiểm tra định kỳ |
| `chống_chỉ_định_khi` | Thuốc/can thiệp không dùng trong tình huống nhất định |
| `tương_tác_với` | Tương tác thuốc-thuốc hoặc thuốc-thực phẩm |
| `cải_thiện_bởi` | Triệu chứng/chỉ số được cải thiện qua can thiệp |

**Quy trình 2 bước:**
1. **Embedding Retrieval:** Mã hóa định nghĩa quan hệ thô → cosine similarity → top-5 ứng viên.
2. **LLM Verification:** LLM chọn 1 ứng viên phù hợp hoặc khai báo "None of the above".

---

#### [MỚI] Giai đoạn 4 – Tinh chỉnh EDC+R

**Schema Retriever:** Dựa trên vector embedding (Jina v3), truy xuất các quan hệ tiềm năng từ lược đồ để đưa vào prompt OIE của vòng lặp tiếp theo.

**Entity Extraction + Merging:** Trích xuất thực thể lâm sàng, hợp nhất thực thể trùng lặp ngữ nghĩa (ví dụ: "ĐTĐ type 2" ≡ "Đái tháo đường type 2").

**Iterative Refinement:** Kết quả vòng trước làm gợi ý (hint) cho vòng sau → kỳ vọng nâng F1 vượt 53%.

---

### 4.3 Công nghệ sử dụng

| Thành phần | Công nghệ | Vai trò |
|---|---|---|
| LLM chính | Llama 3.3 / 4 hoặc GPT-4o | OIE, SD, SC Verify |
| Embedding | jina-embeddings-v3 (API) | Schema Retrieval, SC |
| Tiền xử lý | NLG – Text-to-Text | Chuẩn hóa y văn |
| Cơ sở dữ liệu | Neo4j | Lưu trữ đồ thị tri thức |
| Truy vấn | GraphRAG + Circuit Breaker | Chống ảo giác AI (Hallucination) |
| Đánh giá | Precision / Recall / F1 | Benchmark so sánh |

---

## 5. CƠ SỞ KHOA HỌC VÀ TÍNH KẾ THỪA

| Nền tảng | Nguồn | Đóng góp mới |
|---|---|---|
| Framework EDC gốc [2] | Zhang & Soh, EMNLP 2024 | Bổ sung NLG + Schema Retriever |
| Đồ án 2 – dinh dưỡng [1] | Lê Quang Huy, 2026 | Thu hẹp miền, tăng chiều sâu chẩn đoán |
| NLG y tế [3] | Lyu et al., 2026 | Áp dụng vào tiền xử lý pipeline |
| Embedding API | Jina AI v3 | Thay thế Local LLM nặng |

**Tính mới của đề tài:**
1. Đề xuất pipeline **NLG → EDC+R** chuyên biệt cho y văn tiểu đường.
2. Tích hợp **Circuit Breaker** ngăn Hallucination trong hệ thống CDSS y tế.
3. So sánh benchmark đa mô hình (Llama 3.3/4, GPT-4o) trên cùng dữ liệu lâm sàng.

---

## 6. KẾ HOẠCH THỰC HIỆN

| Giai đoạn | Nội dung | Đầu ra |
|---|---|---|
| **Giai đoạn 1** | Thu thập y văn tiểu đường, ứng dụng NLG tiền xử lý | Bộ dữ liệu văn xuôi chuẩn hóa |
| **Giai đoạn 2** | Lập trình Schema Retriever, cập nhật prompt hệ thống | Module trích xuất cải tiến |
| **Giai đoạn 3** | Chạy EDC+R, xây dựng và chuẩn hóa đồ thị, import Neo4j | Knowledge Graph tiểu đường |
| **Giai đoạn 4** | Xây dựng Web CDSS, kiểm thử F1, hoàn thiện báo cáo | Hệ thống CDSS + Báo cáo |

---

## 7. SẢN PHẨM CỦA ĐỀ TÀI

| Loại | Mô tả |
|---|---|
| **Dữ liệu** | Bộ y văn tiểu đường đã chuẩn hóa thành văn xuôi bởi NLG |
| **Cơ sở dữ liệu** | Đồ thị tri thức chuyên sâu bệnh tiểu đường trên Neo4j |
| **Phần mềm** | Hệ thống Web CDSS tích hợp GraphRAG + Circuit Breaker |
| **Tài liệu** | Báo cáo Khóa luận với số liệu Benchmark F1 so sánh |

---

## 8. ĐÁNH GIÁ VÀ TIÊU CHÍ THÀNH CÔNG

### 8.1 Chỉ số đánh giá

| Chỉ số | Mục tiêu | Ghi chú |
|---|---|---|
| F1 Full Triple | **> 53%** (vượt baseline EDC) | So sánh trên Wiki-NRE + dữ liệu lâm sàng |
| Precision | ≥ 60% | Bộ ba sinh ra phải chính xác |
| Recall | ≥ 55% | Không bỏ sót quan hệ quan trọng |
| KB Node (thực thể) | ≥ 200 thực thể y khoa | Triệu chứng, thuốc, xét nghiệm, biến chứng |
| Relation types | ≥ 8 loại quan hệ chuẩn | Đủ phủ lâm sàng tiểu đường |
| QA Hit Rate@5 | ≥ 80% | Câu hỏi hỗ trợ ra quyết định |

### 8.2 So sánh với EDC gốc

| Tiêu chí | EDC gốc [2] | Đồ án 2 [1] | **Đề xuất (KL)** |
|---|---|---|---|
| Miền | Tổng quát | Dinh dưỡng đa bệnh | **Tiểu đường chuyên sâu** |
| NLG tiền xử lý | Không | Không | **Có** |
| Schema Retriever | Cơ bản | Cơ bản | **Cải tiến + Iterative** |
| F1 Full Triple | 53% | ~53% | **Mục tiêu > 53%** |
| Ứng dụng đầu ra | Không | KB dinh dưỡng | **Web CDSS + GraphRAG** |
| Chống Hallucination | Không | Không | **Circuit Breaker** |

---

## 9. TÀI LIỆU THAM KHẢO

[1] L. Q. Huy, "Báo cáo Đồ án chuyên ngành 2: Xây dựng Đồ thị tri thức dinh dưỡng bệnh nhân," Báo cáo Đồ án, Khoa CNTT, Trường ĐH Nam Cần Thơ, 2026.

[2] B. Zhang and H. Soh, "Extract, Define, Canonicalize: An LLM-based Framework for Knowledge Graph Construction," in *Proc. EMNLP 2024*, Nov. 2024, pp. 1–18.

[3] M. Lyu et al., "Natural Language Generation in Healthcare: A Review of Methods and Applications," *J. Biomed. Inform.*, vol. 176, p. 104997, Apr. 2026.

[4] Viện Dinh dưỡng Quốc gia, *Bảng Thành phần Thực phẩm Việt Nam*. Hà Nội: NXB Y Học, 2007.

---

| Giảng viên hướng dẫn | Sinh viên thực hiện |
|:---|:---|
| ThS. Trần Văn Thiện | Lê Quang Huy |
| *(Ký và ghi rõ họ tên)* | *(Ký và ghi rõ họ tên)* |

---
*Phiên bản: 2.0 | Cập nhật: 05/05/2026 – Nâng cấp từ Đồ án 2 lên Khóa luận tốt nghiệp*
