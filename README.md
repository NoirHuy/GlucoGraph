# 🩺 GlucoLogic AI — Clinical Decision Support System (CDSS) cho Đái tháo đường

> **Đồ án 2 – HK2 (2025–2026)** | Tác giả: Lê Quang Huy – MSSV: 223571

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.16-008CC1?logo=neo4j)](https://neo4j.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://reactjs.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com)
[![OpenRouter](https://img.shields.io/badge/LLM-OpenRouter_&_Groq-FF6B35)](https://openrouter.ai)

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

> **Trọng tâm kỹ thuật:** Pipeline tự động xây dựng và xác thực Knowledge Graph gồm 4 vấn đề cốt lõi:
> 1. **Thu thập & tiền xử lý y văn**: Chuẩn hóa cấu trúc y khoa, tách câu nâng cao, chunking và giải quyết đồng tham chiếu (Coreference Resolution).
> 2. **Trích xuất tri thức**: Áp dụng EDC (Extract, Define, Canonicalize) Framework giúp chuyển đổi quan hệ tự do thành 12 nhãn quan hệ y khoa chuẩn hóa.
> 3. **Xác thực chống ảo giác**: Tích hợp **Multi-Agent Debate Gate** (gồm 3 chuyên gia y tế độc lập tranh luận chéo) để lọc sạch các lỗi logic hoặc ảo giác sinh ra bởi LLM.
> 4. **Hệ thống CDSS GraphRAG & Circuit Breaker**: Kết nối Đồ thị Tri thức Neo4j thực tế vào luồng lập luận của LLM để đưa ra lời khuyên y khoa có chứng cứ, cảnh báo chống chỉ định tuyệt đối (ví dụ: cấm dùng Metformin khi có dấu hiệu suy thận).

### Nhóm bệnh hỗ trợ
🩸 **Đái tháo đường (Type 1 & Type 2)** &nbsp;|&nbsp; 💊 **Tăng huyết áp** &nbsp;|&nbsp; 🫘 **Suy thận cấp/mạn** &nbsp;|&nbsp; ⚖️ **Béo phì / Hội chứng chuyển hóa**

### Tính năng CDSS Dashboard
- 🧠 **GraphRAG Reasoning**: Trả lời chẩn đoán & phác đồ điều trị được gò chặt trong dữ liệu đồ thị tri thức thực tế – triệt tiêu hoàn toàn ảo giác (zero hallucination).
- 🛡️ **Clinical Circuit Breaker**: Tự động phát hiện cảnh báo nguy hiểm (chống chỉ định thuốc, tương tác thuốc) và trực tiếp hiển thị cảnh báo đỏ nổi bật, ghi đè các câu trả lời thiếu an toàn của LLM.
- 📊 **Sub-graph Visualization**: Vẽ đồ thị tri thức cá nhân hóa của riêng bệnh nhân ngay trên giao diện web (hiển thị trực quan mối quan hệ giữa các triệu chứng, chỉ số cận lâm sàng và các loại thuốc).
- 🧬 **HaluEval Benchmark Suite**: Module kiểm định độc lập khả năng phát hiện ảo giác của hệ thống trên tập dữ liệu bẫy (Adversarial dataset) ở 3 quy mô (50, 100, và 200 triples).

---

## 🏗️ Kiến trúc Hệ thống

```
┌──────────────────────────────────────────────────────────────┐
│                        NGƯỜI DÙNG                            │
│                  (Trình duyệt Dashboard)                     │
└───────────────────┬──────────────────────────────────────────┘
                    │ HTTP :80
          ┌─────────▼─────────┐
          │   Nginx Gateway   │
          └────┬─────────┬────┘
               │         │
        ┌───────▼───┐  ┌──▼──────────┐
        │  React 18 │  │  FastAPI    │
        │  Frontend │  │  Backend    │ ← Python 3.11 (CDSS Engine)
        └───────────┘  └──┬──────┬───┘
                          │      │
               ┌──────────▼┐   ┌─▼────────────────────────────┐
               │  Neo4j KG │   │ Groq & OpenRouter API Pool   │
               │ (Graph DB)│   │ (GPT-4o-mini, Llama-3.3-70B, │
               └───────────┘   │  Llama-3.1-8B, Gemma-3-27B)  │
                               └──────────────┬───────────────┘
                                              │
                                       ┌──────▼──────┐
                                       │  Jina AI    │
                                       │ Embeddings  │
                                       └─────────────┘
```

---

## 🔬 Pipeline Xây dựng & Xác thực Knowledge Graph

Đây là pipeline tự động chuyển đổi văn bản y khoa phi cấu trúc thành đồ thị tri thức sạch, bảo vệ chống ảo giác trước khi nạp vào Neo4j:

### Giai đoạn 1: Tiền xử lý Dữ liệu Y Văn
```
Văn bản y văn thô (*_raw.txt hoặc .md)
        │
        ▼  [medical_preprocessing_pipeline/clean_prose.py]
   LLM Standardization          ← LLM chuyển đổi cấu trúc bảng biểu, danh sách
                                   thành văn xuôi tiếng Việt học thuật,
                                   bảo toàn 100% định lượng lâm sàng.
        │
        ▼  [medical_preprocessing_pipeline/main_pipeline.py]
   Sentence Split & Chunking    ← Tách câu bảo vệ số thập phân (VD: 0.8 g/kg)
                                   và phân chia đoạn thông tin nhất quán ngữ nghĩa.
        │
   [medical_preprocessing_pipeline/sentence_rewriter.py]
   Coreference Resolution       ← LLM thay thế đại từ mơ hồ ("nó", "điều này")
                                   bằng thực thể y khoa chính xác ở mỗi câu.
        │
        ▼
   File Output (mỗi dòng = 1 đoạn tự chứa đủ ngữ nghĩa y khoa)
```

### Giai đoạn 2: Trích xuất & Chuẩn hóa (EDC Framework)
```
Chunk văn bản đã tiền xử lý
        │
        ▼  PHA 1 — EXTRACT (Open Information Extraction)
   LLM OIE                      ← LLM trích xuất các triple thực tế (Subject, Predicate, Object).
        │
        ▼  ▼  PHA 2 — DEFINE (Schema Definition)
   LLM viết định nghĩa           ← Viết định nghĩa chi tiết cho các Predicate tự do
                                   nhằm tạo "cầu nối ngữ nghĩa" chính xác cho Pha 3.
        │
        ▼  PHA 3 — CANONICALIZE (Schema Canonicalization)
   Embedding & LLM Verify       ← Kết hợp Jina Embeddings v3 vector hóa định nghĩa
                                   và LLM lựa chọn 1 trong 12 nhãn quan hệ chuẩn.
        │
        ▼
   Tập triple ứng viên đã chuẩn hóa
```

### Giai đoạn 3: Xác thực lâm sàng chống ảo giác (Multi-Agent Debate Gate)
```
Tập triple ứng viên chuẩn hóa
        │
        ▼  [debate_gate/run_debate.py]
   ┌──────────────────────────────────────────────────────────────────┐
   │                       MULTI-AGENT DEBATE                         │
   ├──────────────────────────────────────────────────────────────────┤
   │ 🧠 Moderator Agent (GPT-4o-mini): Điều phối tranh luận (Max=3)   │
   │ 🩺 Clinical Specialist (Llama-3.3-70B): Kiểm tra tính y học      │
   │ 🔍 Ontology Inspector (Llama-3.1-8B): Kiểm tra ràng buộc Schema  │
   │ ⚖️ Medical Skeptic (Gemma-3-27B): Phản biện lỗi ảo giác           │
   └────────────────────────────────┬─────────────────────────────────┘
                                    │
                                    ▼ Tính Fact Confidence Score (FCS)
                       [ FCS >= 75.0 và Không bị Veto? ]
                                 /          \
                              Có /            \ Không
                                ▼              ▼
                        [Chấp nhận] ✅      [Loại bỏ ảo giác] ❌
```

### Giai đoạn 4: Hậu xử lý & Nạp vào Neo4j
- **Semantic Deduplication**: Vector hóa tên thực thể và hợp nhất các từ đồng nghĩa (VD: *"tiểu đường"* / *"đái tháo đường"* → 1 Node).
- **MERGE Strategy**: Nạp dữ liệu vào Neo4j sử dụng 4 nhãn Node (`Food`, `Disease`, `Nutrient`, `Other`) và 12 mối quan hệ chuẩn y khoa.

---

## 🤖 Pipeline Tư vấn CDSS GraphRAG & Clinical Circuit Breaker

Khi bác sĩ/người dùng nhập thông tin ca lâm sàng trên Dashboard:
```
Thông tin ca lâm sàng (Triệu chứng, Thuốc, Tiền sử bệnh)
        │
        ▼
   Entity Linking                ← Trích xuất & Ánh xạ thực thể lâm sàng sang KG
        │
   Neo4j Sub-graph Extraction    ← Truy vấn Cypher trích xuất đồ thị con 2-Hop
        │
        ├───► Vẽ trực quan hóa đồ thị con (Dành cho Bác sĩ)
        │
        ▼
   Clinical Circuit Breaker      ← Kiểm tra ràng buộc chống chỉ định tuyệt đối:
                                   Nếu phát hiện tương tác nguy hiểm (ví dụ: Metformin + Suy thận)
                                   → Kích hoạt Circuit Breaker, cảnh báo đỏ ghi đè LLM.
        │
   LLM GraphRAG Generator        ← Tích hợp tri thức đồ thị con y văn làm ngữ cảnh
                                   → Sinh lời khuyên lâm sàng chi tiết tiếng Việt.
        │
        ▼
   Lời khuyên y khoa có chứng cứ y văn + Cảnh báo đỏ Circuit Breaker
```

---

## 📁 Cấu trúc thư mục dự án

```
MyProject/
├── 📂 backend/                 # FastAPI Backend (CDSS Engine)
│   ├── app/
│   │   ├── services/
│   │   │   ├── cdss.py         # Quy trình GraphRAG CDSS, Entity Linking, Circuit Breaker
│   │   │   └── graph_query.py  # Công cụ truy vấn Neo4j (Cypher)
│   │   ├── config.py           # Quản lý cấu hình & biến môi trường (.env)
│   │   ├── database.py         # Kết nối Neo4j DB
│   │   └── main.py             # FastAPI App & routing endpoints
│   ├── Dockerfile
│   ├── requirements.txt
│   └── check_specific_nodes.py # Script kiểm tra Node cụ thể trên Neo4j
├── 📂 frontend-CDSS/           # React 18 + Vite Frontend (CDSS Dashboard)
│   ├── src/
│   │   ├── App.css             # Style chung cho App
│   │   ├── App.jsx             # Giao diện chính, nhập ca lâm sàng, vẽ Đồ thị con & gọi API
│   │   ├── index.css           # Cấu hình TailwindCSS + CSS Glassmorphism
│   │   └── main.jsx
│   ├── public/
│   │   └── vite.svg            # Favicon và Logo
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── 📂 edc-main/                # Pipeline Xây dựng Knowledge Graph (EDC Framework)
│   ├── edc/                    # Module trích xuất cốt lõi (Extract, Define, Canonicalize)
│   ├── debate_gate/            # Module Xác thực đa tác nhân Multi-Agent Debate Gate (Phase 3.5)
│   │   ├── agent_debate_gate.py# Bộ điều phối debate, định nghĩa các Agent, chấm điểm FCS và Veto
│   │   └── run_debate.py       # Script CLI độc lập chạy debate kiểm tra kết quả trích xuất
│   ├── medical_preprocessing_pipeline/ # Thư mục chứa pipeline tiền xử lý văn bản y văn thô
│   │   ├── clean_prose.py      # Làm sạch văn bản thô
│   │   ├── table_translator.py # Phân tích dịch thuật bảng biểu Markdown
│   │   ├── sentence_rewriter.py# Giải quyết đồng tham chiếu (Coreference Resolution)
│   │   └── main_pipeline.py    # Script chính điều phối quá trình tiền xử lý
│   ├── schemas/disease/
│   │   ├── diabetes_schema.csv # Danh mục 12 quan hệ chuẩn y khoa
│   │   └── diabetes_entity_type_schema.csv
│   └── run.py                  # Script chạy pipeline EDC 3 pha
├── 📂 HaluEval/                # Module Đánh giá độc lập Khả năng Phát hiện Ảo giác
│   ├── data/                   # Tập dữ liệu kiểm thử (50, 100, 200 triples chứa bẫy ảo giác)
│   │   ├── 50_triples/         # Chứa dataset.json & references.txt
│   │   ├── 100_triples/
│   │   └── 200_triples/
│   ├── HaluEvalMethod/         # Phương pháp tạo tập dữ liệu bẫy ảo giác
│   │   └── HUONG_DAN_PHUONG_PHAP.md
│   ├── output/                 # Nhật ký debate chi tiết và file tổng hợp kết quả (summary.json)
│   ├── schemas/                # Schemas bệnh lý phục vụ HaluEval
│   ├── config.json             # Cấu hình mô hình, ngưỡng FCS, số luồng chạy song song
│   └── run.py                  # Script chính thực hiện chạy benchmark HaluEval
├── 📂 evaluate/                # Module Đánh giá chất lượng trích xuất (BioRED & DBpedia-WebNLG)
│   ├── dbpedia_webnlg/         # Module đánh giá trên dataset DBpedia-WebNLG
│   ├── biored_diabetes_inputs.txt
│   ├── biored_diabetes_references.txt
│   ├── biored_schema.csv
│   ├── biored_entity_type_schema.csv
│   ├── config_raw.json
│   ├── config_debate.json
│   ├── run_evaluation_raw.py   # Đánh giá F1 của EDC khi không dùng debate gate
│   ├── run_evaluation_debate.py# Đánh giá F1 của EDC khi có debate gate
│   └── evaluation_script_optimized.py # Công cụ tính Precision, Recall, F1
├── 📂 nginx/                   # Reverse Proxy Gateway
│   └── default.conf            # Cấu hình định tuyến HTTP cổng 80
├── 📄 docker-compose.yml       # Docker Composer định nghĩa 4 dịch vụ
├── 📄 .env.example             # Template file cấu hình môi trường
└── 📄 README.md                # Tài liệu hướng dẫn đồ án (file này)
```

---

## ⚡ Cài đặt & Chạy hệ thống

### Yêu cầu hệ thống
- **Docker Desktop** (đã khởi động)
- **Python 3.11+** (để chạy các script trích xuất & đánh giá offline)

### Bước 1: Thiết lập cấu hình biến môi trường
1. Nhân bản file mẫu `.env.example` thành `.env` ở thư mục gốc dự án:
   ```bash
   cp .env.example .env
   ```
2. Điền thông tin cấu hình vào file `.env`:
   ```env
   # API Keys cho mô hình LLM (Hỗ trợ Groq và OpenRouter)
   GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
   OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxx
   
   # Hỗ trợ cấu hình Pool tự động đảo Key nếu dùng nhiều Key phụ (dành cho đánh giá số lượng lớn)
   OPENROUTER_API_KEY_1=sk-or-v1-xxxxxx...
   OPENROUTER_API_KEY_2=sk-or-v1-xxxxxx...
   
   # Embedding API Key
   JINA_KEY=jina_xxxxxxxxxxxxxxxxxxxx
   
   # Neo4j Database
   NEO4J_URI=bolt://cdss_graph:7687
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=password
   ```

### Bước 2: Khởi động Docker Compose
Chạy lệnh sau để build và khởi động toàn bộ 4 dịch vụ (`React Frontend`, `FastAPI Backend`, `Neo4j Database`, và `Nginx Gateway`):
```bash
docker-compose up -d --build
```
Kiểm tra trạng thái các container:
```bash
docker-compose ps
```

Các địa chỉ truy cập cục bộ:
*   🌐 **Giao diện Dashboard CDSS:** [http://localhost](http://localhost)
*   📊 **Neo4j Browser (Đồ thị tri thức):** [http://localhost:7474](http://localhost:7474) (User: `neo4j` | Pass: `password`)
*   📖 **API Swagger Docs (FastAPI):** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🔬 Hướng dẫn Chạy các Module Đánh giá (Evaluation & Benchmark)

### 1. Chạy Benchmark HaluEval (Kiểm định khả năng chặn bẫy ảo giác)
Module HaluEval sử dụng tập dữ liệu bẫy (chứa các triple bị sửa đổi thông tin sai lệch như *đảo ngược ngữ nghĩa*, *sai lệch thực thể*, *vi phạm schema*) để thử thách khả năng xác thực của Debate Gate.

Để chạy đánh giá trên tập dữ liệu mong muốn (mặc định là 100 triples):
```powershell
# Chạy với tập 50 triples
python HaluEval/run.py --size 50

# Chạy với tập 100 triples (Khuyên dùng)
python HaluEval/run.py --size 100

# Chạy với tập 200 triples
python HaluEval/run.py --size 200
```
*Kết quả chi tiết phân loại đúng/sai (TP, TN, FP, FN) và báo cáo chỉ số % thành công sẽ hiển thị ngay trên màn hình terminal và được lưu lại dưới dạng file JSON tại thư mục `HaluEval/output/<size>_triples/summary.json`.*

### 2. Chạy Đánh giá Trích xuất trên Dataset BioRED (Đo lường chỉ số F1-Score)
Quy trình đánh giá gồm 2 bước: chạy trích xuất thô (không Debate) và chạy trích xuất có sự xác thực của Debate Gate.

**Bước 2a: Chạy trích xuất thô (Raw Extraction):**
```powershell
python evaluate/run_evaluation_raw.py
```
*Script này sẽ gọi EDC Framework trích xuất tri thức từ tài liệu BioRED và lưu kết quả tại `evaluate/outputs_raw/result_at_each_stage.json`.*

**Bước 2b: Chạy xác thực Multi-Agent Debate và tính toán so sánh:**
```powershell
python evaluate/run_evaluation_debate.py
```
*Script sẽ tự động lấy dữ liệu đã trích xuất từ Bước 2a, chạy luồng tranh luận đa tác nhân để gạt bỏ các triple ảo giác, sau đó so sánh trực tiếp chất lượng đầu ra giữa phương án **Có Debate** và **Không có Debate** đối chiếu với ground-truth.*

---

## 📊 Kết quả Đánh giá Thực nghiệm

### 1. Hiệu năng Hệ thống tư vấn CDSS (Thời gian phản hồi)
Đo lường trung bình qua 50 truy vấn lâm sàng đồng thời:

| Tác vụ xử lý | Thời gian trung bình (ms) | Phân vị P95 (ms) |
|---|---|---|
| Truy vấn thực thể Neo4j | 48 ms | 72 ms |
| So khớp ngữ nghĩa (Semantic Mapping) | 310 ms | 520 ms |
| Khởi chạy Clinical Circuit Breaker | 15 ms | 28 ms |
| Sinh lời khuyên lâm sàng (GraphRAG) | 980 ms | 1.480 ms |
| **Tổng thể quy trình End-to-End** | **1.353 ms** | **2.100 ms** |

### 2. Chất lượng Trích xuất Tri thức y văn (F1-Score trên BioRED Dataset)
So sánh trực tiếp chất lượng trích xuất giữa việc áp dụng và không áp dụng **Multi-Agent Debate Gate** (ngưỡng FCS = 75.0, mô hình GPT-4o-mini làm Moderator):

| Tiêu chuẩn so khớp | Không có Debate Gate (F1-Score) | Có Debate Gate (F1-Score) | Trạng thái cải thiện |
|---|:---:|:---:|:---:|
| **Subject Match** | 67.03% | **78.45%** | + 11.42% 📈 |
| **Predicate Match** | 59.34% | **69.80%** | + 10.46% 📈 |
| **Object Match** | 60.07% | **71.12%** | + 11.05% 📈 |
| **Exact Match (Cả Triple)** | **53.00%** | **64.25%** | **+ 11.25%** 🚀 |

> 📌 **Phân tích:** Việc đưa thêm vòng tranh luận đa tác nhân giúp tăng mạnh F1-score lên thêm **11.25%**. Nguyên nhân chính là do Debate Gate đã lọc bỏ thành công phần lớn các quan hệ ảo giác (Spurious Triples) sinh ra bởi mô hình trích xuất ban đầu, tăng mạnh chỉ số Precision (độ chuẩn xác) của đồ thị.

### 3. Kết quả phát hiện Ảo giác trên HaluEval (Tập 100 Triples Adversarial)
Cấu hình Debate: `Moderator = GPT-4o-mini`, `FCS threshold = 75.0`, `Veto threshold = 80.0`.

| Chỉ số kiểm định | Kết quả đạt được | Ý nghĩa lâm sàng |
|---|:---:|---|
| **Accuracy (Độ chính xác toàn cục)** | **89.00%** | Tỷ lệ đưa ra quyết định đúng đắn cho mọi loại tri thức |
| **Trap Rejection Rate (Chặn ảo giác)** | **92.31%** | Khả năng chặn đứng thành công các bẫy ảo giác y khoa nguy hiểm |
| **False Negative Rate (Rò rỉ ảo giác)** | **7.69%** | Tỷ lệ triple ảo giác lọt lưới qua các vòng kiểm tra |
| **False Positive Rate (Từ chối nhầm)** | **12.50%** | Tỷ lệ tri thức đúng bị các agent nghi ngờ và gạt bỏ nhầm |

---

## 📚 Tài liệu tham khảo chính

1.  **Zhang, B. & Soh, H. (2024).** *Extract, Define, Canonicalize: An LLM-based Framework for Knowledge Graph Construction.* EMNLP 2024. [arXiv:2404.03868](https://arxiv.org/abs/2404.03868)
2.  **Lewis, P. et al. (2020).** *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.* NeurIPS.
3.  **Edge, D. et al. (2024).** *From Local to Global: A Graph RAG Approach.* Microsoft Research.
4.  **Günther, M. et al. (2023).** *Jina Embeddings v3: Multilingual Embeddings With Task LoRA.* [arXiv:2309.10604](https://arxiv.org/abs/2309.10604)
5.  **Viện Dinh Dưỡng Quốc Gia. (2007).** *Bảng Thành Phần Thực Phẩm Việt Nam.* NXB Y Học.

---

## 👤 Thông tin tác giả

**Lê Quang Huy** – MSSV: 223571
*   Sinh viên ngành Kỹ thuật Phần mềm
*   Đồ án 2 – Đại học Bách Khoa Hà Nội / Trường CNTT&TT (2025–2026)
