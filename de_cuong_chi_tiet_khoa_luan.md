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
  Về đánh giá và xác thực: Quy trình đánh giá chéo bằng mô hình Đa tác nhân (Multi-Agent Debate) kết hợp RAG [6] cung cấp cơ chế xác thực độ tin cậy vượt trội cho đồ thị tiểu đường mà không cần phụ thuộc vào nguồn nhân lực chuyên gia y khoa thủ công đắt đỏ.

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
  - **Dữ liệu thực nghiệm:** Phác đồ điều trị tiểu đường ADA/AACE và bộ dữ liệu bệnh án điện tử UCI Diabetes 130-US Hospitals.
  - **Giới hạn:** Giao diện CDSS và tính năng ngắt mạch an toàn hỗ trợ chẩn đoán tiểu đường dừng lại ở mức mô hình thực nghiệm giả lập trong môi trường Lab.

- **Phương pháp nghiên cứu**
  Để giải quyết các mục tiêu nghiên cứu của đề tài, nhóm thực hiện áp dụng kết hợp các phương pháp nghiên cứu khoa học sau:
  - **Phương pháp nghiên cứu lý thuyết:**
    - *Nghiên cứu tài liệu và phân tích tổng hợp:* Khảo sát các công trình khoa học y văn chuyên ngành đái tháo đường (ADA, AACE), tài liệu chuẩn hóa siêu từ điển y sinh UMLS để định hình lược đồ (schema) và xây dựng nền tảng lý thuyết cho đồ thị tri thức.
    - *Nghiên cứu lý thuyết mô hình hóa tri thức:* Tìm hiểu lý thuyết về Đồ thị tri thức (KG), các mô hình học máy y sinh chuyên dụng (BioBERT, Qwen-embedding), kiến trúc sinh văn bản tăng cường đồ thị (GraphRAG) và cơ chế tranh luận đa tác nhân (Multi-Agent Debate).
  - **Phương pháp nghiên cứu thực nghiệm (Xây dựng hệ thống):**
    - *Phương pháp thu thập và tiền xử lý dữ liệu:* Thu thập dữ liệu từ phác đồ điều trị ADA dạng PDF và tập dữ liệu bệnh án điện tử UCI Diabetes dạng dữ liệu bảng (EHR); áp dụng kỹ thuật bóc tách nhận thức cấu trúc (Layout-aware parsing) và kỹ thuật đối khớp ngữ nghĩa để chuẩn hóa các từ đồng nghĩa về mã UMLS CUI duy nhất.
    - *Phương pháp thiết kế hệ thống và thực nghiệm phần mềm:* Áp dụng quy trình kỹ nghệ phần mềm để thiết kế kiến trúc CDSS (FastAPI kết hợp ReactJS), xây dựng cơ sở dữ liệu đồ thị Neo4j và lập trình tích hợp module ngắt mạch an toàn lâm sàng (Circuit Breaker).
  - **Phương pháp đánh giá và kiểm chứng khoa học:**
    - *Phương pháp chuyên gia giả lập (LLM-as-a-judge):* Thiết lập mô hình Đa tác nhân (Multi-Agent Debate) đóng vai trò hội đồng y khoa tự động để phản biện chéo, đánh giá và thống nhất độ tin cậy của các bộ ba tri thức tiểu đường được trích xuất.
    - *Phương pháp thống kê định lượng và kiểm thử lâm sàng:* Sử dụng các độ đo khoa học tiêu chuẩn (Precision, Recall, F1-Score) để đánh giá chất lượng đồ thị; thực hiện chạy giả lập các ca lâm sàng thực tế để kiểm thử độ nhạy và tính chính xác của cơ chế cảnh báo ngắt mạch an toàn.

- **Nội dung chủ yếu của đề tài (Trọng tâm nghiên cứu & Mô hình xử lý chi tiết)**
  *Để đáp ứng định hướng tập trung sâu vào nội dung chuyên môn thực tiễn, toàn bộ các giải pháp công nghệ, thuật toán cốt lõi và các mô hình xử lý hệ thống chi tiết (bao gồm quy trình EDC và kiến trúc vận hành CDSS) được tích hợp trực tiếp và trình bày toàn diện ngay trong các phần nội dung dưới đây:*
  - **_Nội dung 1: Khảo sát lý thuyết (Đồ thị tri thức - KG, GraphRAG, Multi-Agent, UMLS), tổng quan về các phương pháp trích xuất Đồ thị tri thức và các hệ thống CDSS hiện tại._**
    - **Nghiên cứu cơ sở lý thuyết về Đồ thị tri thức (Knowledge Graph - KG):** Tìm hiểu định nghĩa về Đồ thị tri thức, cấu trúc biểu diễn tri thức dưới dạng mạng lưới ngữ nghĩa liên kết với ba thành phần cốt lõi: Thực thể (Entities/Nodes - như bệnh tiểu đường, thuốc Metformin, chỉ số eGFR), Mối quan hệ (Relations/Edges - như điều trị, chống chỉ định) và các Thuộc tính ngữ cảnh (Properties). Nghiên cứu vai trò của Bản thể luận (Ontology) và Lược đồ đồ thị (Graph Schema) trong việc định hình cấu trúc dữ liệu. Phân tích tầm quan trọng sống còn của Đồ thị tri thức y sinh học chuyên miền (Biomedical Knowledge Graph) trong việc cung cấp tri thức minh bạch, hỗ trợ khả năng lập luận lâm sàng có thể giải thích (Explainable Reasoning) cho hệ thống AI.
    - **Nghiên cứu cơ sở lý thuyết về GraphRAG và Multi-Agent:** Nghiên cứu sâu cơ chế hoạt động của kiến trúc Graph Retrieval-Augmented Generation (GraphRAG), phân tích cách kết hợp cơ sở dữ liệu đồ thị tri thức với mô hình ngôn ngữ lớn (LLM) để tối ưu hóa quá trình truy xuất ngữ cảnh y khoa, khắc phục hạn chế mất mát thông tin của RAG vector truyền thống. Đồng thời, nghiên cứu cơ chế đàm thoại, phản biện và đồng thuận giữa các tác nhân thông minh y khoa (Multi-Agent Debate Paradigm) để nâng cao độ chính xác của các quyết định lâm sàng.
    - **Khảo sát lý thuyết quy trình xây dựng Đồ thị tri thức và tổng quan các phương pháp trích xuất:**
      - *Quy trình lý thuyết xây dựng Đồ thị tri thức (KG Construction Pipeline):* Khảo sát các cấu phần cốt lõi của quy trình bao gồm: Thu thập dữ liệu thô, Trích xuất tri thức (Knowledge Extraction - bao gồm trích xuất thực thể NER, trích xuất quan hệ RE, trích xuất thuộc tính), Đồng hóa tri thức (Knowledge Fusion - bao gồm giải quyết đồng tham chiếu, liên kết thực thể Entity Linking/Alignment để khử trùng lặp), và Lưu trữ/Truy vấn tri thức trên cơ sở dữ liệu đồ thị.
      - *Tổng quan các phương pháp trích xuất tri thức:* Khảo sát và so sánh các trường phái tiếp cận từ truyền thống đến hiện đại: (1) Phương pháp dựa trên tập luật và mẫu (Rule-based, Pattern-matching); (2) Phương pháp học máy truyền thống và học sâu (Supervised/Semi-supervised Learning, BiLSTM-CRF, Transformer-BERT); (3) Phương pháp trích xuất dựa trên Mô hình ngôn ngữ lớn (LLM-based) thông qua kỹ thuật Prompt Engineering nâng cao (Few-shot prompting, Chain-of-Thought) dưới dạng trích xuất mở (Open IE) kết hợp trích xuất có ràng buộc lược đồ (Schema-constrained Extraction) để tối ưu hóa độ chính xác trong miền y văn phức tạp.
    - **Tìm hiểu hệ thống từ vựng y học thống nhất UMLS:** Khảo sát chi tiết mô hình dữ liệu y văn chuẩn hóa của UMLS (Unified Medical Language System), bao gồm mạng ngữ nghĩa (Semantic Network) và siêu từ điển khái niệm (Metathesaurus). Trọng tâm là phân tích cấu trúc định danh khái niệm duy nhất CUI (Concept Unique Identifier), các kiểu thực thể ngữ nghĩa (Semantic Types) và hệ thống các mối quan hệ ngữ nghĩa (Semantic Relations) đặc thù trong y sinh để thiết lập bộ quy tắc ràng buộc miền và dải (Domain/Range Constraints) cho đồ thị.
    - **Đánh giá các hệ thống hỗ trợ ra quyết định lâm sàng (CDSS) hiện tại:** Nghiên cứu lịch sử phát triển, ưu điểm và hạn chế của các hệ thống hỗ trợ ra quyết định lâm sàng (Clinical Decision Support Systems - CDSS) hiện nay. Phân tích hiện tượng ảo giác y khoa (hallucination) ở các LLM phổ thông khi xử lý phác đồ điều trị tiểu đường phức tạp, từ đó chứng minh sự cần thiết và tính đột phá của việc xây dựng đồ thị tri thức y khoa chuẩn hóa UMLS.
  - **_Nội dung 2: Thiết kế pipeline tự động tiền xử lý dữ liệu từ phác đồ PDF (ADA) và tập dữ liệu dạng CSV (UCI EHR)._**
    - **Xây dựng luồng bóc tách tài liệu nhận thức bố cục (Layout-aware Parsing):** Thiết kế và cài đặt pipeline tự động sử dụng công nghệ phân tích bố cục trang nâng cao (LlamaParse phối hợp mô hình OCR chuyên dụng) nhằm bóc tách cấu trúc phác đồ điều trị của Hiệp hội Đái tháo đường Hoa Kỳ (ADA) và các tài liệu chuyên ngành của AACE. Luồng xử lý cam kết bảo tồn cấu trúc thứ bậc, tránh hiện tượng đứt gãy ngữ nghĩa hoặc mất mát thông tin khi thực hiện Semantic Chunking (phân đoạn ngữ nghĩa tự động).
    - **Mềm hóa cấu trúc phi văn bản bằng Tác nhân NLG (Natural Language Generation Agents):** Xây dựng các tác nhân tạo sinh ngôn ngữ tự nhiên chuyên biệt thực thi việc phân tích và chuyển hóa các bảng lâm sàng phức tạp (như bảng dược động học của thuốc tiểu đường, bảng liều lượng insulin) và lưu đồ thuật toán chẩn đoán thành văn bản phẳng (narrative text) trôi chảy, logic, giúp mô hình ngôn ngữ hiểu được toàn diện ngữ cảnh định lượng mà không cần xử lý định dạng cấu trúc phức tạp.
    - **Tiền xử lý tập dữ liệu bệnh án điện tử EHR (UCI Diabetes Dataset):** Lập trình bộ công cụ chuyển đổi dữ liệu dạng bảng (CSV) của bệnh án điện tử UCI Diabetes 130-US Hospitals thành các đoạn mô tả hành trình lâm sàng của bệnh nhân dưới dạng văn bản tự nhiên. Áp dụng kỹ thuật giải quyết đồng tham chiếu (co-reference resolution) để làm sạch dữ liệu, đưa các danh từ chung và đại từ lâm sàng về đúng thực thể gốc, tối ưu hóa độ sạch cho quá trình trích xuất tiếp theo.
  - **_Nội dung 3: Xây dựng module trích xuất tự động dựa trên EDC framework, chuẩn hóa và thiết lập cơ sở dữ liệu Neo4j._**
    - **Hiện thực hóa quy trình EDC (Extract-Define-Canonicalize) chuyên sâu cho bệnh tiểu đường:**
      - **Phase 1 (Extract):** Tối ưu hóa các Few-shot Prompt để LLM thực hiện trích xuất mở (Open Information Extraction - Open IE) trên các hồ sơ lâm sàng bệnh nhân tiểu đường để thu thập các bộ ba thô dạng `(Subject - Relation - Object)` (ví dụ: `Metformin - treats - Diabetes Type 2`).
      - **Phase 1.5 (Semantic Validation):** Triển khai lớp kiểm chứng ngữ nghĩa (**Semantic Validator**) để rà soát và thanh lọc các bộ ba thô ngay sau giai đoạn trích xuất qua hai nhánh xử lý song song:
            - *Lexical Anchoring (Neo từ khóa):* Đối chiếu thực tế các thực thể được trích xuất với văn bản gốc (ADA/EHR), đảm bảo tính xác thực từ vựng và loại bỏ các đối tượng ảo giác lâm sàng do mô hình tự suy diễn.
            - *Redundancy Filter (Lọc trùng lặp):* Loại bỏ các bộ ba dư thừa hoặc trùng lặp ngữ nghĩa. Đồng thời, sử dụng độ tương đồng vector (STS) từ mô hình nhúng y sinh chuyên dụng (như `qwen3-embedding-8b`) để phát hiện các lỗi sai hướng quan hệ (directionality error), triệt tiêu các tri thức đái tháo đường ảo giác và chuẩn hóa hướng bộ ba trước khi chuyển tiếp.
      - **Phase 2 (Define):** Gọi LLM tạo sinh các định nghĩa ngữ nghĩa (definitions) rõ ràng cho các thực thể và mối quan hệ dựa trên ngữ cảnh xuất hiện của chúng trong phác đồ tiểu đường ADA/AACE gốc.
      - **Phase 3 (Canonicalize - Chuẩn hóa Lược đồ):** Áp dụng mô hình nhúng (Embeddings) kết hợp Verify LLM để chuẩn hóa đồng thời ở hai phân hệ độc lập: 
        - *Phase 3a (Relation Canonicalization):* Chuẩn hóa các quan hệ tự do về các quan hệ chuẩn mực quy định trong lược đồ đái tháo đường (`diabetes_schema.csv`).
        - *Phase 3b (Entity-Type Canonicalization):* Áp dụng thuật toán tìm kiếm độ tương đồng Cosine để ánh xạ các thực thể tự do về các kiểu thực thể chuẩn UMLS trong lược đồ thực thể (`diabetes_entity_type_schema.csv`).
    - **Mô hình xử lý và Luồng chuyển đổi dữ liệu của EDC Pipeline:**
      ```mermaid
      graph TB
          %% Invisible subgraphs to enforce two parallel horizontal tracks
          subgraph Top [" "]
              direction LR
              Docs["Tài liệu Y khoa & EHR<br><i>(Clinical Docs & EHR)</i>"]:::nodeDoc -->|"Dữ liệu Y văn & Bệnh án<br><i>(Clinical Texts)</i>"| EDC("Quy trình trích xuất EDC<br><i>(Extract-Define-Canonicalize)</i>"):::nodeWhite
              EDC -->|"Thực thể & Quan hệ<br><i>(Entities & Relations)</i>"| Neo4j[("Neo4j Graph DB<br><i>(UMLS Knowledge Graph)</i>")]:::nodeDB
              Neo4j <--|"Truy vấn Đồ thị Cypher<br><i>(Cypher & Vector Search)</i>"| Query["<b>Graph Query</b>"]:::textNode
          end

          subgraph Bottom [" "]
              direction LR
              Prompt["<b>Doctor's Prompt</b><br>&lt;/&gt;<br><i>(Nhập triệu chứng)</i>"]:::textNode --> PromptContext("Prompt + Ngữ cảnh Đồ thị<br><i>(Combined Clinical Context)</i>"):::nodeWhite
              PromptContext --> LLM("LLM (Groq Llama-3.3)<br><i>(Clinical Reasoning)</i>"):::nodeWhite
              LLM --> Result["Chẩn đoán & Toa thuốc<br><i>(Clinical Diagnosis)</i>"]:::nodeDoc
          end

          %% Vertical link between tracks
          Neo4j -->|"Đường đi tri thức & Quan hệ liên đới (Graph Context)<br><i>(Most relevant clinical paths & relations)</i>"| PromptContext

          %% Style definitions for whiteboard aesthetic
          classDef nodeWhite fill:#ffffff,stroke:#333333,stroke-width:2px;
          classDef nodeDoc fill:#ffffff,stroke:#333333,stroke-width:2px;
          classDef nodeDB fill:#ffffff,stroke:#333333,stroke-width:3px;
          classDef textNode fill:none,stroke:none,color:#333333;
          
          style Top fill:none,stroke:none;
          style Bottom fill:none,stroke:none;
          
          %% Clean line stroke configuration
          linkStyle default stroke:#333333,stroke-width:2px;
      ```
    - **Đồng hóa thực thể và nạp dữ liệu vào cơ sở dữ liệu đồ thị Neo4j (Entity Resolution & Neo4j Loading):** Áp dụng thuật toán đối sánh thực thể ngữ nghĩa sau bước EDC để giải quyết bài toán đồng tham chiếu và khử trùng lặp (Entity Resolution). Hệ thống tự động truy vấn siêu từ điển UMLS để hợp nhất các danh từ đồng nghĩa, biệt dược hoặc từ viết tắt về tiểu đường (như "T2D", "Diabetes Type 2", "DM2"...) về cùng một thực thể duy nhất được định danh bằng mã UMLS CUI chuẩn (ví dụ: `C0011860`). Chuyển đổi các thực thể và mối quan hệ đã đồng hóa thành các truy vấn Cypher tối ưu hóa để khởi tạo các nút (Nodes), cạnh (Edges) và các thuộc tính liên quan trên Neo4j.
  - **_Nội dung 4: Triển khai hệ thống đánh giá bằng Multi-Agent (LLM-as-a-judge) để tính toán điểm tin cậy._**
    - **Thiết kế kiến trúc Hội đồng tranh luận Đa tác nhân (Multi-Agent Debate Framework):** Hiện thực hóa hệ thống đánh giá tự động dựa trên triết lý "LLM-as-a-Judge" gồm ba AI Agent thực hiện các vai trò độc lập:
      - **Extractor Agent (Tác nhân trích xuất):** Nhiệm vụ đọc văn bản lâm sàng bệnh nhân tiểu đường đầu vào và đề xuất các bộ ba tri thức.
      - **Critic Agent (Tác nhân phản biện):** Đối chiếu các đề xuất với y văn gốc của ADA/AACE (chuyên ngành tiểu đường) và lược đồ UMLS để chỉ ra các điểm phi logic, lỗi hướng quan hệ hoặc ảo giác thực thể tiểu đường.
      - **Judge Agent (Tác nhân trọng tài):** Phân tích các luận điểm phản biện, đưa ra quyết định đồng thuận cuối cùng để chấp nhận, loại bỏ hoặc hiệu chỉnh các bộ ba tri thức tiểu đường.
    - **Xây dựng bộ công cụ đo lường hiệu năng tự động:** Viết mã nguồn tính toán các chỉ số Precision, Recall và F1-Score tự động dựa trên ba cấp độ so khớp chặt chẽ: Exact Match (khớp chính xác cả tên thực thể và mối quan hệ), Strict Match (khớp đúng phân loại kiểu thực thể ngữ nghĩa) và Partial Match (khớp một phần thực thể). Kết xuất các báo cáo và biểu đồ benchmark chi tiết nhằm kiểm định khách quan chất lượng của đồ thị tri thức tiểu đường.
  - **_Nội dung 5: Thiết kế UI/UX và phát triển ứng dụng Web CDSS tương tác, tích hợp chức năng chẩn đoán phân biệt và cảnh báo ngắt mạch._**
    - **Phát triển Backend CDSS và luồng xử lý GraphRAG tiểu đường:** Xây dựng máy chủ dịch vụ API bằng FastAPI để xử lý luồng nghiệp vụ. Thiết lập cơ chế GraphRAG lai (hybrid): khi bác sĩ nhập câu hỏi lâm sàng về tiểu đường, hệ thống sẽ thực hiện truy vấn vector ngữ nghĩa song song với việc gọi các câu lệnh Cypher đến cơ sở dữ liệu Neo4j để lấy ra các đường đi tri thức (knowledge paths) liên quan nhất về bệnh tiểu đường, sau đó nhúng chúng vào Prompt để LLM (`llama-3.3-70b-versatile` qua Groq) tạo ra câu trả lời tư vấn lâm sàng về tiểu đường có độ tin cậy và kiểm chứng cao.
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
    - **Cài đặt thuật toán chẩn đoán phân biệt và Bộ ngắt mạch y khoa (Circuit Breaker):** Triển khai các thuật toán tìm đường (Pathfinding) trên đồ thị tri thức Neo4j để phát hiện các triệu chứng y khoa liên đới phục vụ chẩn đoán phân biệt tiểu đường. Xây dựng module "Circuit Breaker" lâm sàng hoạt động theo thời gian thực: liên tục quét hồ sơ điều trị hiện tại của bệnh nhân tiểu đường, đối chiếu với các mối quan hệ chống chỉ định thuốc điều trị tiểu đường (`has_contraindicated_drug`) và bệnh kèm (`associated_condition_of`) trên đồ thị tri thức Neo4j để phát tín hiệu cảnh báo đỏ và ngăn chặn tức thời hành vi kê đơn thuốc tiểu đường có nguy cơ tương tác cao.
    - **Thiết kế và lập trình giao diện Web CDSS cao cấp:** Giao diện trực quan bao gồm: Khung chat tư vấn GraphRAG tiểu đường thời gian thực, bảng hồ sơ và chỉ số lâm sàng của bệnh nhân tiểu đường, sơ đồ biểu diễn đồ thị tri thức Neo4j tương tác, và khu vực hiển thị cảnh báo đỏ nổi bật của Circuit Breaker khi phát hiện rủi ro tương tác thuốc nguy hiểm.

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
| 2      | Lưu An Thuận  | Thư ký        | Thu thập phác đồ điều trị ADA/AACE và tập dữ liệu bệnh án điện tử UCI EHR; Xây dựng pipeline tiền xử lý dữ liệu (Layout-aware parsing, Chunking); Thiết lập và quản trị CSDL đồ thị Neo4j cùng các truy vấn Cypher.                                            | 5                               |
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

| **Trưởng khoa/Viện/Trung tâm**<br><br>_(chữ ký, họ tên)_ | **Chủ nhiệm đề tài**<br><br>_(chữ ký, họ tên)_ |
| -------------------------------------------------------- | ---------------------------------------------- |