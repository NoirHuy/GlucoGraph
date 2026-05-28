# 🩺 GlucoLogic AI — Clinical Decision Support System (CDSS) cho Đái tháo đường

> **Đồ án 2 – HK2 (2025–2026)** | Tác giả: Lê Quang Huy – MSSV: 223571

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.16-008CC1?logo=neo4j)](https://neo4j.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://reactjs.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com)
[![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-FF6B35)](https://groq.com)

---

## 🚀 Demo Live (Giáo viên / Hội đồng truy cập tại đây)

| Dịch vụ | Đường link | Thông tin đăng nhập |
|---|---|---|
| 🌐 **Web App (CDSS Dashboard)** | [glucologic.noirhuy.id.vn](http://glucologic.noirhuy.id.vn) | *(không cần đăng nhập)* |
| 🔬 **Neo4j Browser (CDSS Knowledge Graph)** | [glucologic.noirhuy.id.vn:7474](http://glucologic.noirhuy.id.vn:7474) | Username: `neo4j` / Password: `password` |
| 💻 **IP trực tiếp (dự phòng)** | [103.82.27.129](http://103.82.27.129) | — |

> 💡 **Hướng dẫn nhanh cho Hội đồng:** Vào link Web App → Nhập bệnh án tóm tắt hoặc chọn Bệnh án lâm sàng mẫu (VD: *Robert - Đái tháo đường Type 1 cấp tính*) → Nhấn **Analyze Case** để xem phân tích chẩn đoán, cảnh báo chống chỉ định tương tác thuốc, và luồng suy luận y khoa trực quan trên Đồ thị Tri thức.
>
> Để xem Đồ thị Tri thức trực quan, vào Neo4j Browser → chạy lệnh Cypher: `MATCH (n) RETURN n LIMIT 100`

---

## 📋 Giới thiệu

**Hệ thống Hỗ trợ Ra quyết định Lâm sàng Đái tháo đường (CDSS) - GlucoLogic AI** nghiên cứu và xây dựng một hệ thống tự động trích xuất tri thức y văn đái tháo đường từ văn bản phi cấu trúc thành **Knowledge Graph (Đồ thị Tri thức)** có cấu trúc, kết hợp kiến trúc **GraphRAG** để hỗ trợ bác sĩ chẩn đoán xác định, chẩn đoán phân biệt và đưa ra phác đồ điều trị an toàn cho bệnh nhân.

> **Trọng tâm kỹ thuật:** Pipeline tự động xây dựng Knowledge Graph gồm 3 vấn đề cốt lõi:
> 1. Thu thập và tiền xử lý dữ liệu y văn (Preprocessing + Coreference Resolution)
> 2. Trích xuất thực thể và quan hệ lâm sàng bằng LLM (OIE + Few-shot Prompting)
> 3. Xây dựng và chuẩn hóa đồ thị tri thức (EDC Framework + Multi-Agent Debate Gate)

### Nhóm bệnh hỗ trợ

🩸 **Tiểu đường** &nbsp;|&nbsp; 💊 **Tăng huyết áp** &nbsp;|&nbsp; 🫘 **Suy thận** &nbsp;|&nbsp; ⚖️ **Béo phì**

### Tính năng ứng dụng

| Tính năng | Mô tả |
|---|---|
| 🔍 **Tra cứu dinh dưỡng** | Nhập tên món ăn → Nhận ngay 16 chỉ số vi chất + lời khuyên y khoa |
| 📸 **Nhận diện ảnh** | Chụp/upload ảnh món ăn → Llama 4 Scout tự nhận diện → Tư vấn (Accuracy 86%) |
| 🧠 **GraphRAG** | Trả lời được gò chặt trong dữ liệu thực tế – **không bao giờ bịa đặt** |
| 🛡️ **Circuit Breaker** | Tự động chặn khi món ăn không có trong CSDL – Zero Hallucination |
| 🗣️ **Tiếng Việt** | Hiểu từ lóng, từ địa phương (VD: "trái thơm" → "dứa") |

---

## 🎬 Demo Hệ thống

https://github.com/user-attachments/assets/dd992a1f-8b68-4373-8f4e-ea7b1ab0ef8c

---

## 🏗️ Kiến trúc Hệ thống

```
┌──────────────────────────────────────────────────────────────┐
│                        NGƯỜI DÙNG                            │
│                    (Trình duyệt Web)                         │
└───────────────────┬──────────────────────────────────────────┘
                    │ HTTP :80
          ┌─────────▼─────────┐
          │   Nginx Gateway   │
          └────┬─────────┬────┘
               │         │
       ┌───────▼───┐  ┌──▼──────────┐
       │  React 18 │  │  FastAPI    │
       │  Frontend │  │  Backend    │ ← Python 3.11
       └───────────┘  └──┬──────┬───┘
                         │      │
              ┌──────────▼┐   ┌─▼──────────┐
              │  Neo4j KG │   │  Groq API  │
              │ (Graph DB)│   │ Llama 3.3  │
              └───────────┘   └─────────── ┘
                                     │
                              ┌──────▼──────┐
                              │  Jina AI    │
                              │ Embeddings  │
                              └─────────────┘
```

---

## 🔬 Pipeline Xây dựng Knowledge Graph (Trọng tâm kỹ thuật)

Đây là phần cốt lõi của đề tài — pipeline tự động chuyển đổi văn bản y khoa phi cấu trúc thành đồ thị tri thức có cấu trúc, gồm **2 giai đoạn tiền xử lý** và **3 pha EDC**:

### Giai đoạn 1: Thu thập và Tiền xử lý Dữ liệu Y Văn

```
Văn bản y khoa thô (*_raw.txt)
        │
        ▼  [preprocess_raw_data.py]
   LLM Standardization          ← Llama 3.3 (temperature=0.1) chuyển bảng biểu
   (10 Strict Rules)               và danh sách → văn xuôi prose chuẩn mực,
                                   bảo toàn 100% số liệu định lượng (mg, %, g/ngày)
        │
        ▼  [preprocess_document.py]
   ┌─── Clean & Sentence Split  ← Regex loại bỏ header/số trang, tách câu
   │                               có bảo vệ số thập phân (0.8 g/kg → <DOT>)
   │
   ├─── Chunking (3 câu/chunk)  ← Gom câu thành các đoạn có ngữ nghĩa nhất quán
   │
   └─── Coreference Resolution  ← LLM (temperature=0.0) + Sliding Window
                                   Thay "nó/điều này" → tên thực thể cụ thể
                                   VD: "Điều này tốt cho tiểu đường"
                                     → "Gạo lứt có chất xơ tốt cho tiểu đường"
        │
        ▼
   File chunked.txt (mỗi dòng = 1 chunk tự chứa đủ ngữ nghĩa)
```

### Giai đoạn 2: Trích xuất và Chuẩn hóa Tri thức (EDC Framework)

```
Chunk văn bản (3 câu đã qua Coreference Resolution)
        │
        ▼  PHA 1 — EXTRACT (Open Information Extraction)
   LLM OIE                      ← Llama 3.3-70B + 5 Few-shot Examples
   (Relation tự do)                Định nghĩa tên thực thể SẠCH, không kèm đơn vị
        │
        │  Ví dụ đầu ra:
        │  (natri, "làm co mạch khiến tăng huyết áp", tăng huyết áp)
        │  (natri, "cần hạn chế dưới 2300mg/ngày", bệnh nhân cao huyết áp)
        │
        ▼  PHA 2 — DEFINE (Schema Definition)
   De-duplicate Relations        ← Thu thập tập quan hệ DUY NHẤT (tiết kiệm API)
   LLM viết định nghĩa           ← Mỗi Relation thô → Định nghĩa ngữ nghĩa đầy đủ
   ngữ nghĩa                        (đây là "cầu nối" để Pha 3 so sánh chính xác)
        │
        ▼  PHA 3 — CANONICALIZE (Schema Canonicalization)
   ┌─── Bước 3a: Embedding       ← Jina Embeddings v3 vector hóa định nghĩa quan hệ
   │    Retrieval                   → Cosine Similarity vs 12 nhãn Schema chuẩn
   │                                → Chọn Top-5 ứng viên (tính toán nội bộ, không API)
   │
   └─── Bước 3b: LLM Verify     ← Trắc nghiệm multiple-choice (A/B/C/D/E/F)
        (max_tokens=1)              LLM xác nhận nhãn Schema phù hợp nhất
                                    Nếu F (None) → Triple bị loại bỏ
        │
        ▼
   Triple đã chuẩn hóa: (natri, "làm trầm trọng", tăng huyết áp) ✅
```

### Giai đoạn 3: Hậu xử lý và Import Neo4j

```
Tập Triple đã chuẩn hóa
        │
        ▼  Lớp 1: Rule-based Cleaning
   Lọc 4 loại lỗi:              ← Triple trừu tượng, quan hệ đảo chiều,
                                   tự tham chiếu, entity chứa ký tự rác
        │
        ▼  Lớp 2: Semantic Deduplication
   Jina Embeddings v3            ← Vector hóa tên tất cả thực thể
   + Cosine Similarity > 0.90      Gom nhóm thực thể đồng nghĩa:
                                   "tiểu đường" / "đái tháo đường" → 1 Node
                                   "tăng huyết áp" / "cao huyết áp" → 1 Node
        │
        ▼  Neo4j Import (MERGE strategy)
   4 nhãn Node:  Food | Disease | Nutrient | Other
   12 loại Quan hệ (Schema chuẩn):
     ├─ làm trầm trọng       ├─ cần hạn chế ở      ├─ chống chỉ định với
     ├─ được khuyến nghị cho  ├─ phòng ngừa          ├─ hỗ trợ
     ├─ ảnh hưởng đường huyết ├─ giàu                ├─ ít
     ├─ thiếu hụt gây ra     ├─ tương tác với       └─ là yếu tố nguy cơ của
        │
        ▼
   Knowledge Graph hoàn chỉnh:
   ~800 Nodes | 1.200+ Triple quan hệ y khoa | 16 vi chất/thực phẩm
```

---

## 🤖 Pipeline Tư vấn GraphRAG (Runtime)

```
Người dùng (Tên món / Ảnh + Bệnh lý)
        │
        ▼ Vision AI (nếu có ảnh)     ← Llama 4 Scout 17B nhận diện tên món
        │
        ▼ Neo4j Exact Lookup          ← Cypher Query: tìm node Food + quan hệ bệnh lý
        │
        ▼ Semantic Mapping (Fallback) ← Llama 3.3 ánh xạ "trái thơm" → "dứa"
        │
        ▼ Circuit Breaker             ← Nếu không có dữ liệu → CHẶN, hiển thị cảnh báo
        │
        ▼ LLM Response Generation     ← Sinh lời khuyên tiếng Việt từ ngữ cảnh KG
        │
        └──► Lời khuyên y khoa có kiểm chứng + Biểu đồ 16 vi chất
```

---

## 🛠️ Công nghệ sử dụng

| Lớp | Công nghệ | Phiên bản | Mục đích |
|---|---|---|---|
| **Frontend** | React + Vite | React 18 | Giao diện chatbot, upload ảnh, biểu đồ |
| **Backend** | FastAPI + Python | 3.11 | REST API async, điều phối GraphRAG |
| **Database** | Neo4j Graph DB | 5.16 | Lưu trữ Đồ thị Tri thức 12 quan hệ |
| **Gateway** | Nginx | 1.29 | Reverse proxy, routing |
| **LLM – Trích xuất KG** | Llama 3.3 via Groq | 70B-versatile | OIE, Schema Definition, Semantic Mapping |
| **LLM – Vision** | Llama 4 Scout via Groq | 17B-16E | Nhận diện ảnh món ăn |
| **LLM – Chuẩn hóa** | Llama 3.3 via Groq | 70B-versatile | Coreference Resolution, LLM Verify |
| **Embedding** | Jina Embeddings v3 | Cloud API | Schema Canonicalization, Deduplication |
| **KG Framework** | EDC Framework | Custom | Tự động trích xuất tri thức (3 pha) |
| **Container** | Docker Compose | v3 | Đóng gói và triển khai toàn hệ thống |

---

## ⚡ Cài đặt và Chạy

### Yêu cầu

- Docker Desktop (đang chạy)
- Python 3.11+ (cho pipeline EDC offline)
- API Keys: `GROQ_API_KEY`, `JINA_KEY`

### Bước 1: Clone và cấu hình

```bash
git clone <repo-url>
cd MyProject

# Tạo file .env từ mẫu
cp .env.example .env
```

Điền các API key vào file `.env`:

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
JINA_KEY=jina_xxxxxxxxxxxxxxxxxxxx
NEO4J_URI=bolt://nutrition_graph:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
```

### Bước 2: Khởi động hệ thống

```bash
docker-compose up -d
```

Truy cập:
- 🌐 **Giao diện web:** http://localhost
- 📊 **Neo4j Browser:** http://localhost:7474
- 📖 **API Docs (Swagger):** http://localhost:8000/docs

### Bước 3: Import dữ liệu (lần đầu)

```bash
# Import 150+ món ăn từ Excel (16 vi chất/món)
docker exec nutrition_backend python import_nutrition_kg.py

# Hoặc chạy pipeline EDC để trích xuất từ tài liệu y khoa mới
cd edc-main

# Bước tiền xử lý (nếu tài liệu thô có bảng biểu)
python preprocess_raw_data.py --input_file your_raw.txt --output_file your.txt

# Bước chunking + Coreference Resolution
python preprocess_document.py --input_file your.txt --output_file your_chunked.txt \
    --sentences_per_chunk 3 --context_window 1

# Chạy EDC Framework (3 pha: Extract → Define → Canonicalize)
python run.py --input your_chunked.txt --sc_embedder jina-embeddings-v3
```

---

## 📁 Cấu trúc thư mục

```
MyProject/
├── 📂 backend/                 # FastAPI Backend
│   ├── app/
│   │   ├── services/
│   │   │   ├── cdss.py         # GraphRAG CDSS Decision Support
│   │   │   └── graph_query.py  # Truy vấn Neo4j (Cypher)
│   │   ├── config.py           # Quản lý biến môi trường (.env)
│   │   └── main.py             # Khởi động FastAPI + CORS
│   └── Dockerfile
├── 📂 frontend-CDSS/           # React 18 + Vite Frontend (CDSS Dashboard)
├── 📂 edc-main/                # Pipeline Xây dựng Knowledge Graph
│   ├── edc/                    # Core: extract.py | schema_definition.py | schema_canonicalization.py
│   ├── few_shot_examples/      # 5 ví dụ mẫu OIE cho 5 nhóm bệnh lý
│   ├── schemas/disease/        # disease_schema.csv (12 quan hệ chuẩn)
│   ├── datasets/               # Văn bản y khoa thô và đã xử lý
│   ├── preprocess_raw_data.py  # Bước 1: LLM chuẩn hóa bảng biểu → văn xuôi
│   ├── preprocess_document.py  # Bước 2: Clean → Chunk → Coreference Resolution
│   └── run.py                  # Khởi chạy pipeline EDC 3 pha
├── 📂 nginx/                   # Cấu hình Nginx reverse proxy
├── 📂 baocao/                  # Báo cáo đồ án (PDF/DOCX)
├── 📄 docker-compose.yml       # Định nghĩa 4 services
├── 📄 benchmark_latency.py     # Script đo hiệu năng API (50 iterations)
└── 📄 .env                     # ⚠️ Biến môi trường (KHÔNG commit lên GitHub!)
```

---

## 📊 Kết quả đánh giá

### Hiệu năng hệ thống tư vấn (50 lần đo)

| Bước xử lý | Trung bình | P95 |
|---|---|---|
| Truy vấn Neo4j (Cypher) | 48 ms | 72 ms |
| Semantic Mapping (Groq LLM) | 310 ms | 520 ms |
| Nhận diện ảnh – Vision AI | 890 ms | 1.350 ms |
| Sinh lời khuyên – LLM Generation | 980 ms | 1.480 ms |
| **End-to-End (toàn bộ quy trình)** | **5.410 ms\*** | 16.595 ms |

> \* Thời gian trung bình cao do ảnh hưởng Rate Limit gói API Free của Groq. Trong điều kiện lý tưởng (không queue), thời gian phản hồi đạt 1.5–2 giây.

### Độ chính xác các tính năng

| Tiêu chí | Kết quả |
|---|---|
| Vision AI Accuracy (100 ảnh) | **86%** (Món chính VN: 92.5%) |
| Semantic Mapping Rate (100 truy vấn) | **88%** |
| Circuit Breaker (chặn hallucination) | **100%** |

### 🔬 Benchmark Pipeline Trích xuất KG (EDC Framework)

Đánh giá khách quan trên tập dữ liệu chuẩn học thuật **wiki-nre** (25 câu, 201 Triple) theo tiêu chuẩn SemEval, không fine-tune mô hình:

| Thành phần | Correct | Missed | Spurious | **F1** |
|---|---|---|---|---|
| Subject (Chủ thể) | 61/67 | 6 | 24 | **67.03%** |
| Predicate (Quan hệ) | 54/67 | 13 | 32 | **59.34%** |
| Object (Đối tượng) | 55/67 | 12 | 32 | **60.07%** |
| **Exact Match (Tổng hợp)** | **170/201** | **31** | **88** | **62.27%** |
| **Full Triple (Khắt khe nhất)** | — | — | — | **53.00%** |

*Kết quả F1 = 53% (Full Triple, Zero-shot) — ngang ngửa với các hệ thống supervised learning truyền thống, không cần fine-tune bất kỳ tham số mô hình nào.*

| | |
|:---:|:---:|
| ![Biểu đồ F1-Score theo từng thành phần](docs/benchmark_f1_score.png) | ![Phân bố các loại kết quả trích xuất](docs/benchmark_distribution.png) |
| *Hình 1: F1-Score theo từng thành phần* | *Hình 2: Phân bố kết quả trích xuất* |

---

## 📚 Tài liệu tham khảo

1. Zhang, B. & Soh, H. (2024). *Extract, Define, Canonicalize: An LLM-based Framework for Knowledge Graph Construction.* EMNLP 2024. [arXiv:2404.03868](https://arxiv.org/abs/2404.03868)
2. Lewis, P. et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.* NeurIPS.
3. Edge, D. et al. (2024). *From Local to Global: A Graph RAG Approach.* Microsoft Research.
4. Günther, M. et al. (2023). *Jina Embeddings v3: Multilingual Embeddings With Task LoRA.* [arXiv:2309.10604](https://arxiv.org/abs/2309.10604)
5. Viện Dinh Dưỡng Quốc Gia. (2007). *Bảng Thành Phần Thực Phẩm Việt Nam.* NXB Y Học.

---

## 📄 Báo cáo đồ án

| File | Mô tả |
|---|---|
| [`BaoCaoDoAn2_LeQuangHuy_223571.pdf`](baocao/BaoCaoDoAn2_LeQuangHuy_223571.pdf) | Báo cáo đồ án 2 – PDF |
| [`BaoCaoDoAn2_LeQuangHuy_223571.docx`](baocao/BaoCaoDoAn2_LeQuangHuy_223571.docx) | Báo cáo đồ án 2 – DOCX |

---

## 👤 Tác giả

**Lê Quang Huy** – MSSV: 223571  
Đồ án 2 – Ngành Kỹ thuật Phần mềm  
HK2, Năm học 2025–2026

---
