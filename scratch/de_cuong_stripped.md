| BỘ GIÁO DỤC VÀ ĐÀO TẠO<br><br>**TRƯỜNG ĐẠI HỌC NAM CẦN THƠ**<br><br>[IMAGE_PLACEHOLDER] | **CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM**<br><br>**Độc lập - Tự do - Hạnh phúc**<br><br>_Cần Thơ, ngày tháng năm 20…_[IMAGE_PLACEHOLDER] |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |

**ĐỀ CƯƠNG ĐĂNG KÝ ĐỀ TÀI**

**KHOA HỌC VÀ CÔNG NGHỆ CẤP CƠ SỞ**

- **Tên đề tài:** _Ứng dụng LLM xây dựng đồ thị tri thức hỗ trợ chẩn đoán bệnh tiểu đường_
- **Chủ nhiệm đề tài**

- _Họ tên: Lê Quang Huy_
- _Lớp: DH22KPM01_
- _Khóa: 10_
- _GV hướng dẫn: ThS. Đặng Mạnh Huy_

- **Đơn vị chủ quản**

_Trường Công Nghệ Số Và Trí Tuệ Nhân Tạo_

- **Đơn vị phối hợp**

_(Đơn vị phối hợp thực hiện đề tài trong trường, ngoài trường…)._

- **Thời gian (tháng):** _từ tháng 4 năm 2026 đến tháng 6 năm 2026_
- **Thông tin về nhân lực**

| **TT** | **Họ và tên** | **Học hàm, học vị** | **Chuyên môn**      | **Đơn vị công tác**                     | **Chức danh dự kiến trong đề tài (chủ nhiệm, thư ký, chuyên gia,…)** |
| ------ | ------------- | ------------------- | ------------------- | --------------------------------------- | -------------------------------------------------------------------- |
| 1      | Lê Quang Huy  | Sinh viên           | Kỹ thuật phần mềm   | Trường Công Nghệ Số Và Trí Tuệ Nhân Tạo | Chủ Nhiệm                                                            |
| ---    | ---           | ---                 | ---                 | ---                                     | ---                                                                  |
| 2      | Lưu Vỹ Thuận  | Sinh viên           | Kỹ thuật phần mềm   | Trường Công Nghệ Số Và Trí Tuệ Nhân Tạo | Thành Viên                                                           |
| ---    | ---           | ---                 | ---                 | ---                                     | ---                                                                  |
| 3      | Nguyễn Văn Hồ | Sinh viên           | Kỹ thuật phần mềm   | Trường Công Nghệ Số Và Trí Tuệ Nhân Tạo | Thành Viên                                                           |
| ---    | ---           | ---                 | ---                 | ---                                     | ---                                                                  |
| 4      | Lưu An Thuận  | Sinh viên           | Công Nghệ Thông tin | Trường Công Nghệ Số Và Trí Tuệ Nhân Tạo | Thư Ký                                                               |
| ---    | ---           | ---                 | ---                 | ---                                     | ---                                                                  |

- **Tổng quan**
  - **_Nhu cầu thực tiễn_**

Trong kỷ nguyên số hóa y khoa, việc tự động hóa khai thác y văn chuyên sâu để xây dựng Đồ thị tri thức (Knowledge Graph - KG) chuẩn hóa đái tháo đường đòi hỏi độ chính xác tuyệt đối. Tuy nhiên, việc sử dụng các Mô hình Ngôn ngữ Lớn (LLM) độc lập để trích xuất tri thức vẫn vấp phải rào cản chí mạng từ hiện tượng ảo giác tri thức (hallucination) và thiếu minh chứng lâm sàng \[1\]. Nhằm giải quyết triệt để vấn đề này, việc nghiên cứu xây dựng Đồ thị tri thức chuẩn hóa UMLS từ y văn chuyên ngành thông qua mô hình trích xuất có ràng buộc và xác thực chéo đa tác nhân là mục tiêu cốt lõi của đề tài. Lớp tri thức cấu trúc, minh bạch và có thể lập luận giải thích này chính là nền tảng khoa học vững chắc giúp nâng cao độ chính xác chẩn đoán. Để kiểm chứng và minh chứng cho giá trị ứng dụng thực tiễn của đồ thị tri thức đã xây dựng, một hệ thống hỗ trợ ra quyết định lâm sàng (CDSS) tích hợp cơ chế "Ngắt mạch an toàn lâm sàng" (Clinical Circuit Breaker) dựa trên truy vấn đồ thị Neo4j sẽ được phát triển làm mô hình thực nghiệm giả lập minh họa \[4\].

- 1. **_Tổng quan tài liệu công trình nghiên cứu liên quan_**

Xu hướng nghiên cứu y khoa hiện đại đang tập trung mạnh mẽ vào việc kết hợp Mô hình Ngôn ngữ Lớn (LLM) và Đồ thị tri thức (KG) nhằm tận dụng khả năng lập luận ngôn ngữ tự nhiên của LLM và tính chính xác, minh bạch dữ liệu của KG trong môi trường lâm sàng y tế \[1\], \[2\].

Về phương pháp tự động hóa xây dựng KG y sinh: Nhằm thay thế phương pháp xây dựng thủ công tốn kém, các nghiên cứu đã chuyển hướng sang trích xuất tri thức tự động dựa trên Prompt Engineering nâng cao \[3\] và các hệ thống mở rộng tự động như AutoBioKG \[4\]. Đặc biệt, framework trích xuất có ràng buộc lược đồ EDC (Extract-Define-Canonicalize) \[5\] đã giải quyết triệt để bài toán chuẩn hóa thực thể và mối quan hệ ngữ nghĩa theo các tiêu chuẩn siêu từ điển y sinh học, mở ra cơ hội xây dựng đồ thị tri thức y khoa quy mô lớn với độ chính xác cao.

Về phương pháp đánh giá chất lượng Đồ thị tri thức: Thay vì phụ thuộc vào hội đồng chuyên gia y tế tốn kém, các nhà khoa học đã ứng dụng xu hướng đánh giá tự động "LLM-as-a-judge" kết hợp RAG \[6\]. Đồng thời, các nghiên cứu đột phá về Giao thức Tranh luận Đa tác nhân (Multi-Agent Debate) của MIT & Google Brain \[7\] và mô hình đánh giá đồng cấp ChatEval \[8\] đã chứng minh rằng việc cho phép nhiều tác nhân LLM phản biện và hội chẩn chéo qua nhiều vòng sẽ giúp triệt tiêu tối đa hiện tượng hallucination (ảo giác lâm sàng) và nâng cao đáng kể độ tin cậy của tri thức được trích xuất.

Khoảng trống nghiên cứu: Mặc dù các công trình tiền đề đã khẳng định tính hiệu quả của việc kết hợp LLM và KG, việc thiết lập một quy trình tự động hóa xây dựng Đồ thị tri thức chuyên biệt cho bệnh đái tháo đường dựa trên framework EDC có ràng buộc UMLS, phối hợp với cơ chế phản biện hội đồng đa tác nhân đồng cấp (P2P Debate Gate) có tích hợp luật Veto lâm sàng vẫn chưa được nghiên cứu. Đây chính là khoảng trống học thuật mang tính cấp thiết mà đề tài tập trung giải quyết nhằm xây dựng cơ sở khoa học và thực tiễn vững chắc cho các ứng dụng hỗ trợ quyết định chẩn đoán an toàn.

- 1. **_Ý nghĩa khoa học_**

Đề tài đóng góp giá trị khoa học nổi bật vào xu hướng Trí tuệ nhân tạo có thể giải thích (Explainable AI) trong y tế thông qua ba phương diện: (1) Đóng góp phương pháp xây dựng Đồ thị tri thức đái tháo đường chuẩn hóa UMLS tự động dưới các ràng buộc lược đồ nghiêm ngặt giúp triệt tiêu ảo giác ngôn ngữ; (2) Thiết lập quy trình thẩm định chất lượng tri thức tự động dựa trên giao thức tranh luận Đa tác nhân (Multi-Agent Debate) đồng cấp và cơ chế phủ quyết (Veto Rule); và (3) Chứng minh giá trị thực tiễn của đồ thị tri thức thông qua mô hình CDSS thực nghiệm giả lập với tính năng cảnh báo tương tác thuốc ngắt mạch an toàn.

- **Mục tiêu nghiên cứu**

**Mục tiêu chính:** Nghiên cứu ứng dụng LLM tự động hóa xây dựng Đồ thị tri thức (Knowledge Graph) chuẩn hóa UMLS hỗ trợ chẩn đoán đái tháo đường, đồng thời phát triển demo ứng dụng CDSS làm mô hình thực nghiệm kiểm chứng lâm sàng.

**Mục tiêu cụ thể:**
- Xây dựng pipeline tiền xử lý tự động dữ liệu phác đồ điều trị đái tháo đường (ADA/AACE) và bệnh án điện tử UCI EHR.
- Hiện thực hóa quy trình tự động trích xuất tri thức y khoa theo framework EDC và chuẩn hóa lược đồ (UMLS CUI).
- Thiết lập và tối ưu hóa cơ sở dữ liệu đồ thị Neo4j lưu trữ tri thức đái tháo đường.
- Phát triển hệ thống tự động đánh giá chất lượng đồ thị dựa trên giao thức phản biện Đa tác nhân (Multi-Agent Debate).
- Triển khai demo ứng dụng hỗ trợ quyết định lâm sàng (CDSS) tích hợp cảnh báo ngắt mạch an toàn tương tác thuốc.

- **Phạm vi nghiên cứu**

**Đối tượng nghiên cứu:** Quy trình tự động trích xuất, chuẩn hóa tri thức (UMLS) và giao thức tự động hóa thẩm định chất lượng đồ thị bằng Đa tác nhân chuyên ngành đái tháo đường.
**Dữ liệu thực nghiệm:** Phác đồ điều trị đái tháo đường ADA/AACE và bộ dữ liệu bệnh án điện tử UCI Diabetes 130-US Hospitals.
**Giới hạn thực nghiệm:** Giao diện CDSS và tính năng ngắt mạch tương tác thuốc chỉ phát triển ở quy mô demo thực nghiệm giả lập trong phòng Lab để minh chứng cho khả năng ứng dụng thực tế của đồ thị tri thức.

- **Phương pháp nghiên cứu**

**Phương pháp nghiên cứu lý thuyết:** Khảo sát y văn lâm sàng đái tháo đường (ADA/AACE) và tài liệu chuẩn hóa UMLS để thiết kế lược đồ đồ thị (Graph Schema); phân tích lý thuyết biểu diễn đồ thị tri thức (KG), kiến trúc GraphRAG lý thuyết và cơ chế tranh biện đa tác nhân (Multi-Agent Debate).

**Phương pháp thực nghiệm (Xây dựng hệ thống):**
- *Tiền xử lý*: Thu thập dữ liệu phác đồ (áp dụng bóc tách cấu trúc Layout-aware Parsing) và bệnh án CSV; tiền xử lý làm sạch, phân đoạn ngữ nghĩa và giải quyết đồng tham chiếu lâm sàng.
- *Lập trình hệ thống*: Thiết lập cơ sở dữ liệu đồ thị Neo4j và ngôn ngữ truy vấn Cypher; lập trình module trích xuất EDC chuẩn hóa thực thể và quan hệ về UMLS CUI; xây dựng web demo CDSS (FastAPI + ReactJS).

**Phương pháp đánh giá và kiểm chứng khoa học:**
- *Thẩm định tự động*: Thiết lập cơ chế Đa tác nhân đồng cấp (P2P Debate Gate) tự phản biện và đồng thuận chéo (FCS, Veto) làm công cụ tự động hóa đánh giá chất lượng đồ thị.
- *Kiểm thử định lượng*: Sử dụng các chỉ số Precision, Recall, F1-Score để đo lường hiệu năng đồ thị; thực hiện chạy giả lập các ca lâm sàng để kiểm tra tính chính xác và độ nhạy của cơ chế ngắt mạch an toàn.

- **Nội dung chủ yếu của đề tài**

**_Nội dung 1:_** _Khảo sát lý thuyết (Đồ thị tri thức - KG, GraphRAG, Multi-Agent, UMLS), tổng quan về các phương pháp trích xuất Đồ thị tri thức và các hệ thống CDSS hiện tại._

**Nghiên cứu cơ sở lý thuyết về Đồ thị tri thức (Knowledge Graph - KG):** Tìm hiểu định nghĩa về Đồ thị tri thức, cấu trúc biểu diễn tri thức dưới dạng mạng lưới ngữ nghĩa liên kết với ba thành phần cốt lõi: Thực thể (Entities/Nodes - như bệnh tiểu đường, thuốc Metformin, chỉ số eGFR), Mối quan hệ (Relations/Edges - như điều trị, chống chỉ định) và các Thuộc tính ngữ cảnh (Properties). Nghiên Lược đồ đồ thị (Graph Schema) trong việc định hình cấu trúc dữ liệu. Phân tích tầm quan trọng sống còn của Đồ thị tri thức y sinh học chuyên miền (Biomedical Knowledge Graph) trong việc cung cấp tri thức minh bạch, hỗ trợ khả năng lập luận lâm sàng có thể giải thích (Explainable Reasoning) cho hệ thống AI.

**Nghiên cứu cơ sở lý thuyết về GraphRAG và Multi-Agent:** Nghiên cứu cơ chế hoạt động của kiến trúc Graph Retrieval-Augmented Generation (GraphRAG), phân tích cách kết hợp cơ sở dữ liệu đồ thị tri thức với mô hình ngôn ngữ lớn (LLM) để tối ưu hóa quá trình truy xuất ngữ cảnh y khoa, khắc phục hạn chế mất mát thông tin của RAG vector truyền thống. Đồng thời, nghiên cứu cơ chế đàm thoại, phản biện và đồng thuận giữa các tác nhân thông minh y khoa (Multi-Agent Debate Paradigm) để nâng cao độ chính xác của các quyết định lâm sàng.

**_Nội dung 2:_** _Thiết kế pipeline tự động tiền xử lý dữ liệu từ phác đồ PDF (ADA) và tập dữ liệu dạng CSV (UCI EHR)._

**Xây dựng luồng bóc tách tài liệu nhận thức bố cục (Layout-aware Parsing):** Thiết kế và cài đặt pipeline tự động sử dụng công nghệ phân tích bố cục trang nâng cao (LlamaParse phối hợp mô hình OCR chuyên dụng) nhằm bóc tách cấu trúc phác đồ điều trị của Hiệp hội Đái tháo đường Hoa Kỳ (ADA) và các tài liệu chuyên ngành của AACE. Luồng xử lý cam kết bảo tồn cấu trúc thứ bậc, tránh hiện tượng đứt gãy ngữ nghĩa hoặc mất mát thông tin khi thực hiện Semantic Chunking (phân đoạn ngữ nghĩa tự động).

**Mềm hóa cấu trúc phi văn bản bằng Tác nhân NLG (Natural Language Generation Agents):** Xây dựng các tác nhân tạo sinh ngôn ngữ tự nhiên chuyên biệt thực thi việc phân tích và chuyển hóa các bảng lâm sàng phức tạp (như bảng dược động học của thuốc tiểu đường, bảng liều lượng insulin) và lưu đồ thuật toán chẩn đoán thành văn bản phẳng (narrative text) trôi chảy, logic, giúp mô hình ngôn ngữ hiểu được toàn diện ngữ cảnh định lượng mà không cần xử lý định dạng cấu trúc phức tạp.

**Tiền xử lý tập dữ liệu bệnh án điện tử EHR (UCI Diabetes Dataset):** Lập trình bộ công cụ chuyển đổi dữ liệu dạng bảng (CSV) của bệnh án điện tử UCI Diabetes 130-US Hospitals thành các đoạn mô tả hành trình lâm sàng của bệnh nhân dưới dạng văn bản tự nhiên. Áp dụng kỹ thuật giải quyết đồng tham chiếu (co-reference resolution) để làm sạch dữ liệu, đưa các danh từ chung và đại từ lâm sàng về đúng thực thể gốc, tối ưu hóa độ sạch cho quá trình trích xuất tiếp theo.

**_Nội dung 3:_** _Xây dựng module trích xuất tự động dựa trên EDC framework, chuẩn hóa và thiết lập cơ sở dữ liệu Neo4j._

Hiện thực hóa quy trình EDC (Extract-Define-Canonicalize) chuyên sâu cho bệnh tiểu đường \[5\]:

- **Phase 1 (Extract):** Tối ưu hóa các Few-shot Prompt để LLM thực hiện trích xuất mở (Open Information Extraction - Open IE) trên các hồ sơ lâm sàng bệnh nhân tiểu đường để thu thập các bộ ba thô dạng (Subject - Relation - Object) (ví dụ: Metformin - treats - Diabetes Type 2).
- **Phase 2 (Define):** Gọi LLM tạo sinh các định nghĩa ngữ nghĩa (definitions) rõ ràng cho các thực thể và mối quan hệ dựa trên ngữ cảnh xuất hiện của chúng trong phác đồ tiểu đường ADA/AACE gốc để bảo toàn ngữ nghĩa lâm sàng trước khi chuẩn hóa.
- **Phase 3 (Canonicalize - Chuẩn hóa Lược đồ):** Áp dụng mô hình nhúng (Embeddings) kết hợp Verify LLM để chuẩn hóa đồng thời ở hai phân hệ độc lập, đồng thời tích hợp các kiểm chứng ngữ nghĩa chặt chẽ để loại bỏ các mối quan hệ ảo giác:

**Phase 3a (Relation Canonicalization):** Chuẩn hóa các quan hệ tự do về các quan hệ chuẩn mực quy định trong lược đồ đái tháo đường (`diabetes_schema.csv`) dựa trên độ tương đồng ngữ nghĩa.

**Phase 3b (Entity-Type Canonicalization):** Áp dụng thuật toán tìm kiếm độ tương đồng Cosine kết hợp mô hình SentenceTransformer/OpenRouter Embeddings để ánh xạ các thực thể tự do về các kiểu thực thể chuẩn UMLS trong lược đồ thực thể (`diabetes_entity_type_schema.csv`).

**Mô hình xử lý và Luồng chuyển đổi dữ liệu của EDC Pipeline** [IMAGE_PLACEHOLDER]

**_Nội dung 4:_** _Triển khai hệ thống đánh giá bằng Multi-Agent (LLM-as-a-judge) để tính toán điểm tin cậy._

**Thiết kế kiến trúc Hội đồng tranh luận Đa tác nhân đồng cấp (P2P Cognitive Multi-Agent Debate Gate):** Dựa trên các nghiên cứu về việc nâng cao tính chân thực và suy luận của LLM thông qua tranh luận đa tác nhân của MIT & Google Brain \[7\] và mô hình đánh giá tự động ChatEval \[8\], đề tài hiện thực hóa một cổng đánh giá chất lượng bộ ba tri thức (Debate Gate) tự động dưới dạng hội đồng chuyên gia y khoa đồng cấp. Hệ thống thiết lập 3 tác nhân AI chuyên biệt có vai trò độc lập, tương tác chéo qua các vòng tranh luận (Multi-Round Debate) với các trọng số thích ứng:

- **Clinical_Specialist (Chuyên gia Lâm sàng - Trọng số 0.4):** Chuyên khoa Nội tiết & Dược lý lâm sàng với vai trò thẩm định tính chính xác của bộ ba tri thức dựa trên các hướng dẫn lâm sàng (ADA/EASD) và bằng chứng y học thực tế.
- **Ontology_Inspector (Thanh tra Bản thể học - Trọng số 0.3):** Chuyên gia về cấu trúc tri thức y khoa và UMLS Metathesaurus. Tác nhân này đối chiếu động với tệp lược đồ `diabetes_schema.csv` tại thời điểm chạy để kiểm tra tính ràng buộc miền/khoảng (Domain/Range Constraints) của mối quan hệ ngữ nghĩa.
- **Medical_Skeptic (Phản biện Y văn - Trọng số 0.3):** Đóng vai trò kiểm toán viên NLP chuyên biệt, phát hiện các lỗi trích xuất ngược chủ-vị, hallucination (ảo giác lâm sàng) và các thực thể nhiễu.

**Cơ chế đồng thuận toán học FCS và Quyền phủ quyết (Veto):**
- **Final Consensus Score (FCS):** Sau tối đa 3 vòng tranh luận tự động để các tác nhân trao đổi lập luận y khoa và cập nhật xác suất, hệ thống tính toán điểm đồng thuận cuối cùng FCS dựa trên trung bình có trọng số của độ tin cậy tự đánh giá (Confidence Score) từ các tác nhân. Bộ ba tri thức chỉ được tích hợp vào Neo4j khi điểm FCS đạt $\ge 80/100$.
- **Quyền phủ quyết lâm sàng (Veto Rule):** Nhằm bảo đảm an toàn sinh mạng trong y khoa, bất kỳ tác nhân nào trong hội đồng chuyên gia kết luận một bộ ba là sai lệch (`[INCORRECT]` hoặc `[SAI]`) với độ tự tin $> 70\%$ sẽ kích hoạt ngay lập tức cơ chế Veto. Bộ ba này sẽ bị bác bỏ trực tiếp mà không xét đến điểm FCS, đảm bảo tính chặt chẽ y học nghiêm ngặt.

**Xây dựng bộ công cụ đo lường hiệu năng tự động:** Viết mã nguồn tính toán các chỉ số Precision, Recall và F1-Score tự động dựa trên ba cấp độ so khớp chặt chẽ: Exact Match (khớp chính xác cả tên thực thể và mối quan hệ), Strict Match (khớp đúng phân loại kiểu thực thể ngữ nghĩa) và Partial Match (khớp một phần thực thể). Kết xuất các báo cáo và biểu đồ benchmark chi tiết nhằm kiểm định khách quan chất lượng của đồ thị tri thức tiểu đường.

**_Nội dung 5:_** _Thiết kế UI/UX và phát triển ứng dụng Web CDSS tương tác, tích hợp chức năng chẩn đoán phân biệt và cảnh báo ngắt mạch._

**Phát triển Backend CDSS và luồng xử lý GraphRAG tiểu đường:** Xây dựng máy chủ dịch vụ API bằng FastAPI để xử lý luồng nghiệp vụ. Thiết lập cơ chế GraphRAG lai (hybrid): khi bác sĩ nhập câu hỏi lâm sàng về tiểu đường, hệ thống sẽ thực hiện truy vấn vector ngữ nghĩa song song với việc gọi các câu lệnh Cypher đến cơ sở dữ liệu Neo4j để lấy ra các đường đi tri thức (knowledge paths) liên quan nhất về bệnh tiểu đường, sau đó nhúng chúng vào Prompt để LLM (llama-3.3-70b- versatile qua Groq) tạo ra câu trả lời tư vấn lâm sàng về tiểu đường có độ tin cậy và kiểm chứng cao.

**Cài đặt thuật toán chẩn đoán phân biệt và Bộ ngắt mạch y khoa (Circuit Breaker):** Triển khai các thuật toán tìm đường (Pathfinding) trên đồ thị tri thức Neo4j để phát hiện các triệu chứng y khoa liên đới phục vụ chẩn đoán phân biệt tiểu đường. Xây dựng module "Circuit Breaker" lâm liên tục quét hồ sơ điều trị hiện tại của bệnh nhân tiểu đường, đối chiếu với các mối quan hệ chống chỉ định thuốc điều trị tiểu đường (has_contraindicated_drug) và bệnh kèm (associated_condition_of) trên đồ thị tri thức Neo4j để phát tín hiệu cảnh báo đỏ và ngăn chặn các hành vi kê đơn thuốc tiểu đường có nguy cơ tương tác cao.

**Thiết kế và lập trình giao diện Web CDSS:** Giao diện trực quan bao gồm: Khung chat tư vấn GraphRAG tiểu đường, bảng hồ sơ và chỉ số lâm sàng của bệnh nhân tiểu đường, sơ đồ biểu diễn đồ thị tri thức Neo4j tương tác, và khu vực hiển thị cảnh báo đỏ nổi bật của Circuit Breaker khi phát hiện rủi ro tương tác thuốc nguy hiểm.

- **Dự kiến kết quả, sản phẩm nghiên cứu**
  - Sản phẩm: _Một Đồ thị tri thức về bệnh tiểu đường chuẩn UMLS; Web Hệ thống hỗ trợ ra quyết định lâm sàng (CDSS)._
  - Sản phẩm đào tạo: 1-4 _sinh viên tham gia nghiên cứu_
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

| **TT** | **Họ và tên** | **Chức danh** | **Nhiệm vụ được giao**<br><br>**(theo Mục 6)**                                                                                                                                                                                                                                                                                                                                            | **Thời gian thực hiện (tháng)** |
| ------ | ------------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| 1      | Lê Quang Huy  | Chủ nhiệm     | Xây dựng kế hoạch thực hiện; Nghiên cứu và thiết kế các thuật toán và mô hình cốt lõi (Quy trình EDC, GraphRAG); Quản lý tiến độ và tích hợp hệ thống đồ thị tri thức;Thu thập phác đồ điều trị ADA/AACE và tập dữ liệu bệnh án điện tử UCI EHR; Xây dựng pipeline tiền xử lý dữ liệu (Layout-aware parsing, Chunking); Thiết lập và quản trị CSDL đồ thị Neo4j cùng các truy vấn Cypher. | 3                               |
| ---    | ---           | ---           | ---                                                                                                                                                                                                                                                                                                                                                                                       | ---                             |
| 2      | Lưu Vỹ Thuận  | Thành viên    | Nghiên cứu phát triển các Prompt cho LLM và module sinh định nghĩa thực thể ngữ cảnh (NLG/Define); Xây dựng và tích hợp module ngắt mạch an toàn lâm sàng (Circuit Breaker) trên giao diện Web CDSS Dashboard (ReactJS + FastAPI); Tiến hành kiểm thử hệ thống.                                                                                                                           | 2                               |
| ---    | ---           | ---           | ---                                                                                                                                                                                                                                                                                                                                                                                       | ---                             |
| 3      | Nguyễn Văn Hồ | Thành Viên    | Nghiên cứu và triển khai hệ thống đánh giá đa tác nhân (Multi-Agent Debate Framework / LLM-as-a-judge) để chấm điểm tin cậy; Thiết kế và xây dựng bộ công cụ đo lường hiệu năng tự động (Precision, Recall, F1-Score)                                                                                                                                                                     | 2                               |
| ---    | ---           | ---           | ---                                                                                                                                                                                                                                                                                                                                                                                       | ---                             |
| 4      | Lưu An Thuận  | Thư Ký        | Viết báo cáo tổng hợp cho đề tài.                                                                                                                                                                                                                                                                                                                                                         | 2                               |
| ---    | ---           | ---           | ---                                                                                                                                                                                                                                                                                                                                                                                       | ---                             |

- **Dự toán kinh phí**: _(chỉ nêu tổng kinh phí, phần diễn giải tách thành phụ lục riêng,_ _Mẫu C2)._
- **Tiến độ**

_(cần thể hiện rõ các mốc công việc quan trọng giúp cho việc kiểm tra hoạt động thực hiện đề tài). Xem ví dụ như bảng dưới._

| **TT** | **Công việc<sup>1</sup>**                                       | **Bắt đầu** | **Kết thúc** | **Thời gian (tháng)** | **Người chịu trách nhiệm chính<sup>2</sup>** |
| ------ | --------------------------------------------------------------- | ----------- | ------------ | --------------------- | -------------------------------------------- |
| 1      | Tổng quan đề tài                                                | 01/04/2026  | 15/04/2026   | 0,5                   | Chủ nhiệm                                    |
| ---    | ---                                                             | ---         | ---          | ---                   | ---                                          |
| 2      | Thực nghiệm                                                     | 15/04/2026  | 01/06/2026   | 1,5                   | Nhóm                                         |
| ---    | ---                                                             | ---         | ---          | ---                   | ---                                          |
| 3      | Viết báo cáo                                                    | 01/06/2026  | 15/06/2026   | 0,5                   | Nhóm                                         |
| ---    | ---                                                             | ---         | ---          | ---                   | ---                                          |
| 4      | Viết báo, đăng báo, đăng ký dự giải, đăng ký phát triển đề tài… | 15/06/2026  | 30/06/2026   | 0,5                   | Chủ Nhiệm                                    |
| ---    | ---                                                             | ---         | ---          | ---                   | ---                                          |

_Ghi chú: <sup>(1)</sup> Công việc căn cứ theo Mục 14; <sup>(2)</sup> Nếu một nhóm người cùng thực hiện thì ghi tên người chịu trách nhiệm chính._

**Tài liệu tham khảo (IEEE Format)**

_\[1\] H. Xu et al., "medIKAL: Integrating Knowledge Graphs as Assistants of LLMs for Enhanced Clinical Diagnosis on EMRs," in Proceedings of the 31st International Conference on Computational Linguistics (COLING), Jan. 2025._

_\[2\] E. Evangelista et al., "GraphRAG-Enabled Local Large Language Model for Gestational Diabetes Mellitus: Development of a Proof-of-Concept," JMIR Diabetes, vol. 11, e76454, Jan. 2026._

_\[3\] X. Wang et al., "Building an intelligent diabetes Q&A system with knowledge graphs and large language models," Frontiers in Public Health, vol. 13, 2025._

_\[4\] Y. Zheng et al., "Automating Biomedical Knowledge Graph Construction For Context-Aware Scientific Inference," bioRxiv, Jan. 2026._

_\[5\] E. Zhang and H. Soh, "Extract, Define, Canonicalize: An LLM-based Framework for Knowledge Graph Construction," in Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing, Miami, Florida, Nov. 2024, pp. 9548-9562._

_\[6\] J. Wu et al., "Evidence-based Medical Large Language Model via Graph Retrieval-Augmented Generation," in Proceedings of the 63rd Annual Meeting of the Association for Computational Linguistics, 2025, pp. 28443-28467._

_\[7\] Y. Du, S. Li, H. Torralba, J. B. Tenenbaum, and I. Mordatch, "Improving Factuality and Reasoning in Language Models through Multiagent Debate," arXiv preprint arXiv:2305.14325, 2023._

_\[8\] C.-M. Chan et al., "ChatEval: Towards better LLM-based evaluators through multi-agent debate," in Proceedings of the 12th International Conference on Learning Representations (ICLR), May 2024._

| **Trưởng khoa/Viện/Trung tâm**<br><br>_(chữ ký, họ tên)_ | **Chủ nhiệm đề tài**<br><br>_(chữ ký, họ tên)_ |
| -------------------------------------------------------- | ---------------------------------------------- |