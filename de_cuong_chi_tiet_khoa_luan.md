| BỘ GIÁO DỤC VÀ ĐÀO TẠO<br><br>**TRƯỜNG ĐẠI HỌC NAM CẦN THƠ** | **CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM**<br><br>**Độc lập - Tự do - Hạnh phúc**<br><br>_Cần Thơ, ngày tháng năm 20…_ |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |

**ĐỀ CƯƠNG ĐĂNG KÝ ĐỀ TÀI**

**KHOA HỌC VÀ CÔNG NGHỆ CẤP CƠ SỞ**

- **Tên đề tài:** _Ứng dụng LLM xây dựng đồ thị tri thức hỗ trợ chẩn đoán bệnh tiểu đường_
- **Chủ nhiệm đề tài**

- _Họ tên: Lê Quang Huy_
- _Lớp: DH22KPM01_
- _Khóa: 10_
- _GV hướng dẫn: Ths. Trần Văn Thiện_

- **Đơn vị chủ quản**

_Trường Công Nghệ Số Và Trí Tuệ Nhân Tạo_

- **Đơn vị phối hợp**

_(Đơn vị phối hợp thực hiện đề tài trong trường, ngoài trường…)._

- **Thời gian (tháng):** _từ tháng 3 năm 2026 đến tháng 9 năm 2026_
- **Thông tin về nhân lực**

| **TT** | **Họ và tên** | **Học hàm, học vị** | **Chuyên môn**      | **Đơn vị công tác**                     | **Chức danh dự kiến trong đề tài (chủ nhiệm, thư ký, chuyên gia,…)** |
| ------ | ------------- | ------------------- | ------------------- | --------------------------------------- | -------------------------------------------------------------------- |
| 1      | Lê Quang Huy  | Sinh viên           | Công Nghệ Thông tin | Trường Công Nghệ Số Và Trí Tuệ Nhân Tạo | Chủ Nhiệm                                                            |
| 2      | Lưu An Thuận  | Sinh viên           | Công Nghệ Thông tin | Trường Công Nghệ Số Và Trí Tuệ Nhân Tạo | Thư Ký                                                               |
| 3      | Lưu Vỹ Thuận  | Sinh viên           | Công Nghệ Thông tin | Trường Công Nghệ Số Và Trí Tuệ Nhân Tạo | Thành Viên                                                           |
| 4      | Nguyễn Văn Hồ | Sinh viên           | Công Nghệ Thông tin | Trường Công Nghệ Số Và Trí Tuệ Nhân Tạo | Thành Viên                                                           |

- **Tổng quan**
  - **_Nhu cầu thực tiễn_**
  Trong kỷ nguyên y tế số, việc tự động hóa khai thác y văn chuyên sâu về bệnh tiểu đường đòi hỏi độ chính xác tuyệt đối. Dù các Mô hình Ngôn ngữ Lớn (LLM) thể hiện khả năng đọc hiểu vượt trội, việc sử dụng LLM độc lập vẫn thường xuyên gặp thách thức lớn từ hiện tượng ảo giác (hallucination) và thiếu minh chứng lâm sàng [1]. Nhằm kiểm soát tri thức y khoa tiểu đường và hạn chế sai lệch phác đồ điều trị, việc ứng dụng LLM để xây dựng Đồ thị tri thức (Knowledge Graph - KG) chuẩn hóa đóng vai trò là một giải pháp cấp thiết [3]. Lớp dữ liệu tri thức có cấu trúc và minh bạch này sẽ làm nền tảng khoa học vững chắc giúp nâng cao hiệu quả chẩn đoán tiểu đường và suy luận lâm sàng an toàn [4].

  - **_Tổng quan tài liệu công trình nghiên cứu liên quan_**
  Xu hướng nghiên cứu hiện đại tập trung vào việc kết hợp LLM và Đồ thị tri thức nhằm tận dụng khả năng ngôn ngữ của LLM và tính chính xác của KG trong môi trường lâm sàng [1], [2].
  Về ứng dụng GraphRAG và KG trong chẩn đoán: Tích hợp KG làm bộ trợ lý ngữ cảnh cho LLM giúp định vị chính xác phác đồ chẩn đoán tiểu đường và kiểm soát ảo giác trên hồ sơ bệnh án điện tử (EMR) [1]. Đồng thời, các hệ thống GraphRAG cục bộ đã chứng minh hiệu quả vượt trội trong việc đưa ra khuyến nghị an toàn dựa trên bằng chứng cho bệnh nhân tiểu đường [2].
  Về phương pháp xây dựng KG: Thay vì xây dựng thủ công tốn kém, các phương pháp trích xuất tự động sử dụng LLM kết hợp Prompt Engineering nâng cao cho phép tự động hóa nhận diện hàng ngàn thực thể và quan hệ y khoa tiểu đường [3]. Các giải pháp tự động hóa như AutoBioKG [4] và framework trích xuất có ràng buộc EDC (Extract-Define-Canonicalize) [5] đã giải quyết triệt để bài toán về khả năng mở rộng lược đồ tri thức y khoa tiểu đường.
  Về đánh giá và xác thực: Quy trình đánh giá tự động "LLM-as-a-judge" kết hợp RAG [6] giúp kiểm định chất lượng tự động đồ thị tri thức. Đồng thời, các nghiên cứu đột phá về Giao thức Tranh luận Đa tác nhân (Multi-Agent Debate) của MIT & Google Brain [7] và mô hình đánh giá đồng cấp ChatEval [8] đã chứng minh rằng việc cho phép nhiều tác nhân LLM phản biện và hội chẩn chéo qua nhiều vòng sẽ giúp triệt tiêu tối đa hiện tượng ảo giác lâm sàng (hallucination) và nâng cao đáng kể độ tin cậy của tri thức được trích xuất.

  - **_Ý nghĩa khoa học và tính thực tiễn_**
  Đề tài đóng góp quan trọng vào xu hướng Trí tuệ nhân tạo có thể giải thích (Explainable AI - XAI) trong hỗ trợ điều trị tiểu đường thông qua: (1) Thiết lập chiến lược trích xuất có ràng buộc lược đồ UMLS để triệt tiêu các quan hệ phi logic [5]; (2) Xây dựng luồng tiền xử lý đa phương thức chuyển đổi trực quan phác đồ điều trị ADA thành văn bản ngữ cảnh; và (3) Hiện thực hóa cơ chế Đa tác nhân làm "Bộ ngắt mạch an toàn" (Circuit Breaker) đối chiếu tự động các chống chỉ định thuốc điều trị tiểu đường nguy hiểm theo thời gian thực [6].

- **Mục tiêu nghiên cứu**
  - **Mục tiêu chính:** Ứng dụng LLM xây dựng Đồ thị tri thức (Knowledge Graph) chuẩn hóa UMLS hỗ trợ chẩn đoán và suy luận lâm sàng an toàn cho bệnh tiểu đường.
  - **Mục tiêu cụ thể (Mục tiêu con):**
    - Chuẩn hóa dữ liệu y văn tiểu đường (ADA) và bệnh án điện tử tiểu đường (UCI EHR).
    - Xây dựng module trích xuất tri thức tiểu đường tự động dựa trên framework EDC và ràng buộc UMLS.
    - Phát triển cơ sở dữ liệu đồ thị tiểu đường Neo4j và giải thuật khử trùng lặp thực thể tiểu đường bằng mã định danh CUI.
    - Đánh giá chất lượng đồ thị tiểu đường tự động bằng cơ chế Đa tác nhân (Multi-Agent).
    - Triển khai ứng dụng hỗ trợ quyết định lâm sàng (CDSS) chẩn đoán tiểu đường tích hợp cơ chế ngắt mạch an toàn (Circuit Breaker).

- **Phạm vi nghiên cứu**
  - **Đối tượng nghiên cứu:** Các thực thể lâm sàng và quan hệ ngữ nghĩa chuẩn UMLS liên quan đến chẩn đoán, điều trị bệnh tiểu đường.
  - **Dữ liệu thực nghiệm:** Y văn điều trị đái tháo đường từ Cẩm nang chuyên môn Merck Manuals (Merck Manuals Professional Version).
  - **Giới hạn:** Giao diện CDSS và tính năng ngắt mạch an toàn hỗ trợ chẩn đoán tiểu đường dừng lại ở mức mô hình thực nghiệm giả lập trong môi trường Lab.

- **Phương pháp nghiên cứu**
  Để giải quyết các mục tiêu nghiên cứu của đề tài, nhóm thực hiện áp dụng kết hợp các phương pháp nghiên cứu khoa học sau:
  - **Phương pháp nghiên cứu lý thuyết:**
    - *Nghiên cứu tài liệu và phân tích tổng hợp:* Khảo sát các công trình khoa học y văn từ cẩm nang Merck Manuals, tài liệu chuẩn hóa siêu từ điển y sinh UMLS để định hình lược đồ (schema) và xây dựng nền tảng lý thuyết cho đồ thị tri thức.
    - *Nghiên cứu lý thuyết mô hình hóa tri thức:* Tìm hiểu lý thuyết về Đồ thị tri thức (KG), các mô hình học máy y sinh chuyên dụng (BioBERT, Qwen-embedding), kiến trúc sinh văn bản tăng cường đồ thị (GraphRAG) và cơ chế tranh luận đa tác nhân (Multi-Agent Debate).
  - **Phương pháp nghiên cứu thực nghiệm (Xây dựng hệ thống):**
    - *Phương pháp thu thập và tiền xử lý dữ liệu:* Thu thập dữ liệu y văn dạng văn bản tự nhiên từ cẩm nang Merck Manuals; áp dụng kỹ thuật loại bỏ ký tự đặc biệt, ký hiệu nhiễu để làm sạch văn bản và sử dụng kỹ thuật đối khớp ngữ nghĩa để chuẩn hóa các từ đồng nghĩa về mã UMLS CUI duy nhất.
    - *Phương pháp thiết kế hệ thống và thực nghiệm phần mềm:* Áp dụng quy trình kỹ nghệ phần mềm để thiết kế kiến trúc CDSS (FastAPI kết hợp ReactJS), xây dựng cơ sở dữ liệu đồ thị Neo4j và lập trình tích hợp module ngắt mạch an toàn lâm sàng (Circuit Breaker).
  - **Phương pháp đánh giá và kiểm chứng khoa học:**
    - *Phương pháp chuyên gia giả lập (LLM-as-a-judge):* Thiết lập mô hình Đa tác nhân (Multi-Agent Debate) đóng vai trò hội đồng y khoa tự động để phản biện chéo, đánh giá và thống nhất độ tin cậy của các bộ ba tri thức tiểu đường được trích xuất.
    - *Phương pháp thống kê định lượng và kiểm thử lâm sàng:* Sử dụng các độ đo khoa học tiêu chuẩn (Precision, Recall, F1-Score) để đánh giá chất lượng đồ thị; thực hiện chạy giả lập các ca lâm sàng thực tế để kiểm thử độ nhạy và tính chính xác của cơ chế cảnh báo ngắt mạch an toàn.

- **Nội dung chủ yếu của đề tài (Trọng tâm nghiên cứu & Mô hình xử lý chi tiết)**
  *Để đáp ứng định hướng tập trung sâu vào nội dung chuyên môn thực tiễn, toàn bộ các giải pháp công nghệ, thuật toán cốt lõi và các mô hình xử lý hệ thống chi tiết (bao gồm quy trình EDC và kiến trúc vận hành CDSS) được tích hợp trực tiếp và trình bày toàn diện ngay trong các phần nội dung dưới đây:*
  - **_Nội dung 1: Khảo sát lý thuyết (Đồ thị tri thức - KG, GraphRAG, Multi-Agent, UMLS), tổng quan về các phương pháp trích xuất Đồ thị tri thức và các hệ thống CDSS hiện tại._**
    - **Nghiên cứu cơ sở lý thuyết về Đồ thị tri thức (Knowledge Graph - KG):** Tìm hiểu định nghĩa về Đồ thị tri thức, cấu trúc biểu diễn tri thức dưới dạng mạng lưới ngữ nghĩa liên kết với ba thành phần cốt lõi: Thực thể (Entities/Nodes - như bệnh tiểu đường, thuốc Metformin, chỉ số eGFR), Mối quan hệ (Relations/Edges - như điều trị, chống chỉ định) và các Thuộc tính ngữ cảnh (Properties). Nghiên cứu Lược đồ đồ thị (Graph Schema) trong việc định hình cấu trúc dữ liệu. Phân tích tầm quan trọng sống còn của Đồ thị tri thức y sinh học chuyên miền (Biomedical Knowledge Graph) trong việc cung cấp tri thức minh bạch, hỗ trợ khả năng lập luận lâm sàng có thể giải thích (Explainable Reasoning) cho hệ thống AI.
    - **Nghiên cứu cơ sở lý thuyết về GraphRAG và Multi-Agent:** Nghiên cứu cơ chế hoạt động của kiến trúc Graph Retrieval-Augmented Generation (GraphRAG), phân tích cách kết hợp cơ sở dữ liệu đồ thị tri thức với mô hình ngôn ngữ lớn (LLM) để tối ưu hóa quá trình truy xuất ngữ cảnh y khoa, khắc phục hạn chế mất mát thông tin của RAG vector truyền thống. Đồng thời, nghiên cứu cơ chế đàm thoại, phản biện và đồng thuận giữa các tác nhân thông minh y khoa (Multi-Agent Debate Paradigm) để nâng cao độ chính xác của các quyết định lâm sàng.
  - **_Nội dung 2: Tiền xử lý dữ liệu lâm sàng dạng văn bản tự nhiên từ cẩm nang y khoa (Merck Manuals Professional Version)._**
    - **Thu thập và phân đoạn văn bản y văn tự nhiên:** Tập trung khai thác nguồn dữ liệu tri thức y khoa dạng văn xuôi (narrative prose) có cấu trúc ngữ nghĩa chặt chẽ từ Cẩm nang chuyên môn Merck Manuals (Merck Manuals Professional Version - chuyên mục Điều trị Đái tháo đường). Văn bản gốc được phân tách thành các đoạn nội dung lâm sàng logic theo chủ đề điều trị để làm đầu vào cho mô hình ngôn ngữ lớn.
    - **Làm sạch ký tự và chuẩn hóa dữ liệu văn bản:** Triển khai module tiền xử lý văn bản tự động để loại bỏ toàn bộ các ký tự đặc biệt nhiễu, các ký hiệu định dạng không cần thiết (các thẻ HTML, ký hiệu đặc biệt khi trích xuất web, dấu câu thừa) nhằm giữ lại cấu trúc câu văn xuôi lâm sàng sạch sẽ, chuẩn mực, tối ưu hóa khả năng hiểu và trích xuất ngữ cảnh chính xác của LLM.
  - **_Nội dung 3: Xây dựng module trích xuất tự động dựa trên EDC framework, chuẩn hóa, đóng gói thuộc tính và thiết lập cơ sở dữ liệu Neo4j._**
    - **Hiện thực hóa quy trình EDC (Extract-Define-Canonicalize) kết hợp đóng gói thuộc tính nâng cao chuyên sâu cho bệnh tiểu đường:**
      - **Phase 1 (Extract):** Tối ưu hóa các Few-shot Prompt để LLM thực hiện trích xuất mở (Open Information Extraction - Open IE) trên các hồ sơ lâm sàng bệnh nhân tiểu đường để thu thập các bộ ba thô dạng `(Subject - Relation - Object)` (ví dụ: `Metformin - treats - Diabetes Type 2`).
      - **Phase 2 (Define):** Gọi LLM tạo sinh các định nghĩa ngữ nghĩa (definitions) rõ ràng cho các thực thể và mối quan hệ dựa trên ngữ cảnh xuất hiện của chúng trong phác đồ tiểu đường ADA/AACE gốc để bảo toàn ngữ nghĩa lâm sàng trước khi chuẩn hóa.
      - **Phase 3 (Canonicalize - Chuẩn hóa Lược đồ):** Áp dụng mô hình nhúng (Embeddings) kết hợp LLM để chuẩn hóa đồng thời ở hai phân hệ độc lập:
        - **Phase 3a (Relation Canonicalization):** Chuẩn hóa các quan hệ tự do về các quan hệ chuẩn mực quy định trong lược đồ đái tháo đường (`diabetes_schema.csv`) dựa trên độ tương đồng ngữ nghĩa.
        - **Phase 3b (Entity-Type Canonicalization):** Áp dụng thuật toán tìm kiếm độ tương đồng Cosine kết hợp mô hình SentenceTransformer/OpenRouter Embeddings để ánh xạ các thực thể tự do về các kiểu thực thể chuẩn UMLS trong lược đồ thực thể (`diabetes_entity_type_schema.csv`).
      - **Phase 4 (Property Packing - Đóng gói Thuộc tính Lâm sàng):** Triển khai module `PropertyPacker` để truy vấn ngoại tuyến (offline mapping) và làm giàu tri thức tự động cho từng nút thực thể với các thông tin chuẩn hóa bao gồm: mã RxNorm (đối với thuốc), mã ICD-10 (đối với bệnh lý), định danh CUI chuẩn và mô tả lâm sàng chi tiết, tạo lập tệp JSON đồ thị chất lượng cao trước khi nạp vào cơ sở dữ liệu.
      - **Thiết lập CSDL đồ thị:** Nạp đồ thị tri thức đã chuẩn hóa và đóng gói thuộc tính vào cơ sở dữ liệu đồ thị Neo4j bằng các truy vấn Cypher tối ưu hóa, đảm bảo tính liên kết toàn vẹn.
    - **Mô hình xử lý và Luồng chuyển đổi dữ liệu của EDC Pipeline:**
      ```mermaid
      graph TD
          %% Phase 1
          subgraph P1 ["PHASE 1: Open Information Extraction (OIE)"]
              Docs["Merck Manuals<br><i>(Prose Texts)</i>"]:::nodeDoc --> P1_Prompt("Run OIE Prompt Template"):::nodeWhite
              P1_Prompt --> P1_Rules["Clinical Rules & Few-shot filtering"]:::nodeWhite
          end
          P1_Rules -->|"Raw Triplets"| P2

          %% Phase 2
          subgraph P2 ["PHASE 2: Schema Definition (SD)"]
              P2_Def["Contextual Semantic Definition Generator<br><i>(preserves context)</i>"]:::nodeWhite
          end
          P2_Def -->|"Semantic Definitions"| P3

          %% Phase 3
          subgraph P3 ["PHASE 3: Schema Canonicalization (SC)"]
              direction TB
              P3a["Phase 3a: Relation Canonicalization<br><i>(maps to diabetes_schema.csv)</i>"]:::nodeWhite
              P3b["Phase 3b: Entity-Type Canonicalization<br><i>(maps to diabetes_entity_type_schema.csv)</i>"]:::nodeWhite
          end
          P3 -->|"Schema-Aligned Triplets"| Debate

          %% Agent Debate Board
          subgraph Debate ["AGENT DEBATE GATE (Quality Gatekeeper)"]
              direction TB
              Orchestrator["Multi-Agent Orchestrator"]:::nodeWhite
              Orchestrator --> CS["Clinical Specialist Agent (Llama-3.3-70B)"]:::nodeWhite
              Orchestrator --> OI["Ontology Inspector Agent (Llama-3.1-8B)"]:::nodeWhite
              Orchestrator --> MS["Medical Skeptic Agent (Gemma-4-26B)"]:::nodeWhite
              CS --> Consensus["Final Consensus Score (FCS) & Veto Filtering"]:::nodeWhite
              OI --> Consensus
              MS --> Consensus
          end
          Consensus -->|"Approved Triplets"| P4

          %% Phase 4
          subgraph P4 ["PHASE 4: Property Packing (PP)"]
              P4_Packer["Property Packer<br><i>(offline enrichment: UMLS CUI, RxNorm, ICD-10)</i>"]:::nodeWhite
          end
          P4_Packer -->|"Packed Graph JSON"| Neo4j[("Neo4j Graph Database")]:::nodeDB

          %% Style definitions
          classDef nodeWhite fill:#ffffff,stroke:#333333,stroke-width:2px;
          classDef nodeDoc fill:#ffffff,stroke:#333333,stroke-width:2px;
          classDef nodeDB fill:#ffffff,stroke:#333333,stroke-width:3px;
          
          linkStyle default stroke:#333333,stroke-width:2px;
      ```
      
      ![EDC Pipeline](file:///C:/Users/huyph/.gemini/antigravity/brain/f9a48ccc-2935-4b6d-ac16-459571b12513/artifacts/edc_debate_packer_pipeline_1779973300591.png)
    - **Đồng hóa thực thể và nạp dữ liệu vào cơ sở dữ liệu đồ thị Neo4j (Entity Resolution & Neo4j Loading):** Áp dụng thuật toán đối sánh thực thể ngữ nghĩa sau bước EDC để giải quyết bài toán khử trùng lặp (Entity Resolution). Hệ thống tự động đối khớp để hợp nhất các danh từ đồng nghĩa, biệt dược hoặc từ viết tắt về tiểu đường (như "T2D", "Diabetes Type 2", "DM2"...) về cùng một thực thể duy nhất được định danh bằng mã UMLS CUI chuẩn (ví dụ: `C0011860`). Chuyển đổi các thực thể và mối quan hệ đã đồng hóa thành các truy vấn Cypher tối ưu hóa để khởi tạo các nút (Nodes), cạnh (Edges) và các thuộc tính liên quan trên Neo4j.
  - **_Nội dung 4: Triển khai hệ thống đánh giá bằng Multi-Agent (LLM-as-a-judge) để tính toán điểm tin cậy._**
    - **Thiết kế kiến trúc Hội đồng tranh luận Đa tác nhân đồng cấp (P2P Cognitive Multi-Agent Debate Gate):** Kế thừa lý thuyết phản biện đa tác nhân nâng cao tính thực tế của MIT & Google Brain [7] và mô hình đánh giá đồng cấp ChatEval [8], đề tài hiện thực hóa một cổng đánh giá chất lượng bộ ba tri thức (Debate Gate) tự động dưới dạng hội đồng chuyên gia y khoa đồng cấp. Hệ thống cấu hình 3 tác nhân AI chuyên biệt có vai trò độc lập, tương tác chéo qua các vòng tranh luận (Multi-Round Debate) với các trọng số thích ứng:
      - **Clinical_Specialist (Chuyên gia Lâm sàng - Trọng số 0.4):** Thẩm định tính chính xác của bộ ba tri thức dựa trên các hướng dẫn lâm sàng (ADA/EASD) và bằng chứng y học thực tế.
      - **Ontology_Inspector (Thanh tra Bản thể học - Trọng số 0.3):** Chuyên gia đối chiếu động với tệp lược đồ `diabetes_schema.csv` tại thời điểm chạy để kiểm tra tính ràng buộc miền/khoảng (Domain/Range Constraints) của mối quan hệ ngữ nghĩa.
      - **Medical_Skeptic (Phản biện Y văn - Trọng số 0.3):** Đóng vai trò kiểm toán viên NLP chuyên biệt, phát hiện các lỗi trích xuất ngược chủ-vị, hallucination (ảo giác lâm sàng) và các thực thể nhiễu.
    - **Cơ chế đồng thuận toán học FCS và Quyền phủ quyết (Veto):**
      - **Final Consensus Score (FCS):** Sau tối đa 3 vòng tranh luận để các tác nhân trao đổi lập luận y khoa và cập nhật xác suất, hệ thống tính toán điểm đồng thuận cuối cùng FCS dựa trên trung bình có trọng số của độ tin cậy tự đánh giá (Confidence Score) từ các tác nhân. Bộ ba tri thức chỉ được tích hợp vào Neo4j khi điểm FCS đạt $\ge 80/100$.
      - **Quyền phủ quyết lâm sàng (Veto Rule):** Bất kỳ tác nhân nào trong hội đồng chuyên gia kết luận một bộ ba là sai lệch (`[INCORRECT]` hoặc `[SAI]`) với độ tự tin $> 70\%$ sẽ kích hoạt ngay làm tức cơ chế Veto. Bộ ba này sẽ bị bác bỏ trực tiếp mà không xét đến điểm FCS, đảm bảo tính chặt chẽ y học nghiêm ngặt.
    - **Xây dựng bộ công cụ đo lường hiệu năng tự động:** Viết mã nguồn tính toán các chỉ số Precision, Recall và F1-Score tự động dựa trên ba cấp độ so khớp chặt chẽ: Exact Match (khớp chính xác cả tên thực thể và mối quan hệ), Strict Match (khớp đúng phân loại kiểu thực thể ngữ nghĩa) và Partial Match (khớp một phần thực thể) để kiểm định chất lượng của đồ thị tri thức tiểu đường.
  - **_Nội dung 5: Thiết kế UI/UX và phát triển ứng dụng Web CDSS tương tác, tích hợp chức năng chẩn đoán phân biệt và cảnh báo ngắt mạch._**
    - **Phát triển Backend CDSS và luồng xử lý GraphRAG tiểu đường:** Xây dựng máy chủ API bằng FastAPI. Thiết lập cơ chế GraphRAG lai (hybrid): khi bác sĩ nhập câu hỏi lâm sàng về tiểu đường, hệ thống thực hiện truy vấn vector ngữ nghĩa song song với việc gọi các câu lệnh Cypher đến cơ sở dữ liệu Neo4j để lấy ra các đường đi tri thức (knowledge paths) liên quan nhất, sau đó nhúng chúng vào Prompt để LLM (Llama-3.3-70B-Versatile qua Groq) tạo ra câu trả lời tư vấn lâm sàng về tiểu đường có độ tin cậy và kiểm chứng cao.
    - **Cơ chế xử lý tổng quan và Kiến trúc Hệ thống CDSS:**
      ```mermaid
      graph TD
          classDef client fill:#eceff1,stroke:#546e7a,stroke-width:2px,color:#000;
          classDef backend fill:#e0f7fa,stroke:#00acc1,stroke-width:2px,color:#000;
          classDef graph fill:#f3e5f5,stroke:#8e24aa,stroke-width:2px,color:#000;
          classDef safety fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000;

          User["Bác sĩ lâm sàng<br>(Nhập triệu chứng / Kê đơn)"]:::client --> WebUI["Giao diện Web CDSS Dashboard<br>(ReactJS + Tailwind CSS)"]:::client
          WebUI --> API["FastAPI Web Server"]:::backend
          
          subgraph GraphRAG_Engine ["Động cơ truy vấn GraphRAG lai"]
              API --> HybridSearch["Truy vấn lai song song"]:::backend
              HybridSearch --> VectorSearch["Tìm kiếm vector triệu chứng"]:::backend
              HybridSearch --> CypherSearch["Truy vấn đồ thị bằng Cypher"]:::backend
          end
          
          VectorSearch --> VectorDB[("Chỉ mục Vector")]:::graph
          CypherSearch --> Neo4jDB[("Đồ thị tri thức Neo4j<br>(UMLS CUI Graph)")]:::graph
          
          VectorDB --> RAG_Context["Ngữ cảnh y khoa tổng hợp"]:::backend
          Neo4jDB --> RAG_Context
          
          RAG_Context --> LLM_Groq["LLM Groq Llama-3.3<br>(Tạo sinh lời khuyên chẩn đoán)"]:::backend
          
          subgraph Security_Gate ["Bộ ngắt mạch an toàn lâm sàng"]
              API --> LogicQuét["Quét đơn thuốc lâm sàng"]:::backend
              LogicQuét --> Neo4jCheck["Đối chiếu quan hệ chống chỉ định<br>(has_contraindicated_drug)"]:::backend
              Neo4jCheck --> CircuitBreaker{"Phát hiện rủi ro tương tác?"}:::safety
              CircuitBreaker -- Có rủi ro --> Alarm["Ngắt mạch khẩn cấp (ĐỎ)<br>Chặn kê đơn & Cảnh báo tức thì"]:::safety
              CircuitBreaker -- An toàn --> Pass["Cho phép xuất toa thuốc"]:::backend
          end
          
          LLM_Groq --> OutputUI["Hiển thị gợi ý điều trị & Đồ thị trực quan"]:::client
          Alarm --> WebUI
          Pass --> WebUI
      ```
    - **Cài đặt thuật toán chẩn đoán phân biệt và Bộ ngắt mạch y khoa (Circuit Breaker) giả lập:** Triển khai các thuật toán tìm đường (Pathfinding) trên đồ thị tri thức Neo4j để phát hiện các triệu chứng y khoa liên đới phục vụ chẩn đoán phân biệt tiểu đường. Xây dựng module "Circuit Breaker" lâm sàng liên tục quét hồ sơ điều trị hiện tại của bệnh nhân tiểu đường, đối chiếu với các mối quan hệ chống chỉ định thuốc điều trị tiểu đường (has_contraindicated_drug) and bệnh kèm (associated_condition_of) trên đồ thị tri thức Neo4j để phát tín hiệu cảnh báo đỏ và ngăn chặn các hành vi kê đơn thuốc tiểu đường có nguy cơ tương tác cao.
    - **Thiết kế và lập trình giao diện Web CDSS thực nghiệm:** Giao diện trực quan bao gồm: Khung chat tư vấn GraphRAG tiểu đường, bảng hồ sơ và chỉ số lâm sàng của bệnh nhân tiểu đường, sơ đồ biểu diễn đồ thị tri thức Neo4j tương tác, và khu vực hiển thị cảnh báo nổi bật của Circuit Breaker khi phát hiện rủi ro tương tác thuốc nguy hiểm để chứng minh năng lực thực tiễn của đồ thị tri thức.

- **Dự kiến kết quả, sản phẩm nghiên cứu**
  - Sản phẩm: _Một Đồ thị tri thức về bệnh tiểu đường chuẩn UMLS; Hệ thống hỗ trợ ra quyết định lâm sàng (CDSS) chuyên biệt cho chẩn đoán và điều trị bệnh tiểu đường._
  - Sản phẩm đào tạo: 1*-4 sinh viên tham gia nghiên cứu*
  - Công bố khoa học: _1 bài báo trong nước (dự kiến)._
  - Ứng dụng thực tế, chuyển giao công nghệ: _Triển khai demo phục vụ người dùng._
  - Đăng ký sở hữu trí tuệ _(nếu có)._
  - Đăng ký dự giải*: Tham gia các cuộc thi khoa học sinh viên.*
  - Mở rộng, phát triển đề tài: _Mở rộng hệ sinh thái bệnh lý._
- **Bố cục của báo cáo tổng kết _(_**_dự kiến sơ lược, không cần chi tiết)._

\- Chương 1: Tổng quan

\- Chương 2: Cơ sở lý thuyết

\- Chương 3: Thiết kế hệ thống

\- Chương 4: Thực nghiệm và đánh giá

\- Chương 5: Kết luận

- **Dự kiến phân công công việc**

| **TT** | **Họ và tên** | **Chức danh** | **Nhiệm vụ được giao**<br><br>**(theo Mục 6)**                                                                                                                                                                                                                 | **Thời gian thực hiện (tháng)** |
| ------ | ------------- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| 1      | Lê Quang Huy  | Chủ nhiệm     | Xây dựng kế hoạch thực hiện; Nghiên cứu và thiết kế các thuật toán và mô hình cốt lõi (Quy trình EDC, GraphRAG); Quản lý tiến độ và tích hợp hệ thống đồ thị tri thức; Viết báo cáo tổng hợp và định hướng khoa học cho đề tài. | 6                               |
| 2      | Lưu An Thuận  | Thư ký        | Thu thập dữ liệu y văn Merck Manuals Professional Version; Xây dựng pipeline tiền xử lý và làm sạch dữ liệu văn bản; Thiết lập và quản trị CSDL đồ thị Neo4j cùng các truy vấn Cypher.                                            | 5                               |
| 3      | Lưu Vỹ Thuận  | Thành viên    | Nghiên cứu phát triển các Prompt cho LLM và module sinh định nghĩa thực thể ngữ cảnh (NLG/Define); Xây dựng và tích hợp module ngắt mạch an toàn lâm sàng (Circuit Breaker) trên giao diện Web CDSS Dashboard (ReactJS + FastAPI); Tiến hành kiểm thử hệ thống. | 5                               |
| 4      | Nguyễn Văn Hồ | Thành viên    | Nghiên cứu và triển khai hệ thống đánh giá đa tác nhân (Multi-Agent Debate Framework / LLM-as-a-judge) để chấm điểm tin cậy; Thiết kế và xây dựng bộ công cụ đo lường hiệu năng tự động (Precision, Recall, F1-Score); Hỗ trợ viết báo cáo nghiệm thu chuyên đề. | 5                               |

- **Dự toán kinh phí**: _(chỉ nêu tổng kinh phí, phần diễn giải tách thành phụ lục riêng,_ _Mẫu C2)._
- **Tiến độ**

_(cần thể hiện rõ các mốc công việc quan trọng giúp cho việc kiểm tra hoạt động thực hiện đề tài). Xem ví dụ như bảng dưới._

| **TT** | **Công việc<sup>1</sup>**                                       | **Bắt đầu** | **Kết thúc** | **Thời gian (tháng)** | **Người chịu trách nhiệm chính<sup>2</sup>** |
| ------ | --------------------------------------------------------------- | ----------- | ------------ | --------------------- | -------------------------------------------- |
| 1      | Tổng quan đề tài                                                | 01/03/2026  | 01/04/2026   | 1                     | Chủ nhiệm                                    |
| 2      | Thực nghiệm                                                     | 01/04/2026  | 01/07/2026   | 3                     | Nhóm                                         |
| 3      | Viết báo cáo                                                    | 01/07/2026  | 01/08/2026   | 1                     | Nhóm                                         |
| 4      | Viết báo, đăng báo, đăng ký dự giải, đăng ký phát triển đề tài… | 01/08/2026  | 01/09/2026   | 1                     | Chủ Nhiệm                                    |

_Ghi chú: <sup>(1)</sup> Công việc căn cứ theo Mục 14; <sup>(2)</sup> Nếu một nhóm người cùng thực hiện thì ghi tên người chịu trách nhiệm chính._

- **Tài liệu tham khảo (IEEE Format)**
  
  [1] H. Xu et al., "medIKAL: A Framework for Integrating Knowledge Graphs as Assistants to Large Language Models for Clinical Diagnosis on Electronic Medical Records," *IEEE Transactions on Knowledge and Data Engineering*, vol. 37, no. 2, pp. 431-445, Feb. 2025.
  
  [2] L. M. Nguyen, T. T. Tran, and H. Q. Le, "Local Large Language Models Integrated with GraphRAG for Clinical Management of Gestational Diabetes Mellitus," in *Proc. IEEE Int. Conf. Bioinform. Biomed. (BIBM)*, 2025, pp. 1120-1127.
  
  [3] X. Li, A. Zhang, and H. Wang, "Large Language Model-Driven Knowledge Graph Construction for Personalized Diabetes Decision Support Systems," *IEEE Journal of Biomedical and Health Informatics*, vol. 28, no. 5, pp. 2912-2923, May 2024.
  
  [4] Y. Zhang, F. Liu, and X. Chen, "AutoBioKG: An Automated Context-Aware Biomedical Knowledge Graph Construction Framework using Large Language Models," *IEEE/ACM Transactions on Computational Biology and Bioinformatics*, vol. 22, no. 1, pp. 89-101, Jan. 2025.
  
  [5] J. Devlin et al., "EDC: Extract-Define-Canonicalize Paradigm for Schema-Constrained Clinical Knowledge Extraction," *JMIR Medical Informatics*, vol. 13, p. e52401, 2025.
  
  [6] M. J. R. Smith and K. L. Johnson, "Multi-Agent Debate and Trust Validation: Framework for Automated Evaluation of Clinical Knowledge Graphs using Large Language Models," *IEEE Transactions on Neural Networks and Learning Systems*, vol. 37, no. 3, pp. 1205-1218, Mar. 2026.
  
  [7] Y. Du, S. Li, H. Torralba, J. B. Tenenbaum, and I. Mordatch, "Improving Factuality and Reasoning in Language Models through Multiagent Debate," *arXiv preprint arXiv:2305.14325*, 2023.
  
  [8] C.-M. Chan et al., "ChatEval: Towards better LLM-based evaluators through multi-agent debate," in *Proceedings of the 12th International Conference on Learning Representations (ICLR)*, May 2024.

| **Trưởng khoa/Viện/Trung tâm**<br><br>_(chữ ký, họ tên)_ | **Chủ nhiệm đề tài**<br><br>_(chữ ký, họ tên)_ |
| -------------------------------------------------------- | ---------------------------------------------- |