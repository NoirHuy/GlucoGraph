| TRƯỜNG ĐẠI HỌC NAM CẦN THƠ, KHOA CÔNG NGHỆ THÔNG TIN | CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM Độc lập - Tự do - Hạnh phúc |
| :--- | :--- |
| | Cần Thơ, ngày tháng năm |

# ĐỀ CƯƠNG CHI TIẾT KHOÁ LUẬN TỐT NGHIỆP

* **Tên đề tài:** Ứng dụng LLM xây dựng đồ thị tri thức chuẩn đoán bệnh tiểu đường
* **Sinh viên thực hiện:** Lê Quang Huy, 223571, DH22KPM01, Khoa Công Nghệ Thông Tin, K10, 0916510595
* **Giảng viên hướng dẫn:** Ths: Trần Văn Thiện

---

### 1. Lý do chọn đề tài/tính cấp thiết của đề tài
Trong xã hội hiện đại, đái tháo đường (tiểu đường) đang là một gánh nặng lớn cho hệ thống y tế, đòi hỏi quá trình quản lý, theo dõi và đưa ra quyết định lâm sàng hết sức chặt chẽ. Tại Đồ án chuyên ngành 2, việc ứng dụng framework EDC (Extract - Define - Canonicalize) đã cho thấy tiềm năng lớn trong việc tự động hóa trích xuất tri thức y khoa vào đồ thị tri thức [1]. Tuy nhiên, để phát triển thành một hệ thống có khả năng hỗ trợ chẩn đoán chuyên sâu riêng cho bệnh tiểu đường, cần phải giải quyết hai thách thức lớn:
* **Thứ nhất:** Dữ liệu y văn lâm sàng về tiểu đường chứa rất nhiều định dạng phi cấu trúc và bảng biểu phức tạp. Nếu chỉ phân đoạn (chunking) thông thường sẽ dễ dẫn đến mất mát ngữ cảnh y khoa.
* **Thứ hai:** Quá trình trích xuất thông tin mở (OIE) dễ sinh ra lỗi thiếu sót hoặc dư thừa nếu mô hình ngôn ngữ lớn (LLM) thiếu các định hướng về Schema trong ngữ cảnh rộng.

Do đó, đề tài này được thực hiện nhằm xây dựng đồ thị tri thức chẩn đoán chuyên biệt cho bệnh tiểu đường, ứng dụng kỹ thuật sinh ngôn ngữ tự nhiên (NLG) để tiền xử lý văn bản thô thành văn xuôi và kết hợp lớp Schema Retriever nhằm tăng cường độ chính xác khi LLM trích xuất [2].

### 2. Nội dung và phạm vi nghiên cứu
* **Đối tượng nghiên cứu:** Các mô hình ngôn ngữ lớn (LLM), Đồ thị tri thức (Knowledge Graph), kỹ thuật tiền xử lý bằng NLG và framework trích xuất kết hợp Schema Retriever (EDC+R).
* **Phạm vi nghiên cứu:** Toàn bộ dữ liệu, quan hệ và kiến thức lâm sàng được thu thập, xử lý và xây dựng giới hạn chuyên sâu cho bệnh tiểu đường.
* **Nội dung thực hiện:**
    * **Thu thập và tiền xử lý dữ liệu y văn về bệnh tiểu đường:** Sử dụng các kỹ thuật Text-to-Text NLG để biến đổi các hướng dẫn điều trị, bảng biểu y khoa phi cấu trúc về bệnh tiểu đường thành các đoạn văn xuôi tự nhiên, đảm bảo toàn vẹn dữ liệu định lượng.
    * **Trích xuất thực thể và quan hệ bằng LLM:** Phát triển lớp Schema Retriever dựa trên vector nhúng (Embedding) để tìm kiếm các quan hệ tiềm năng, sau đó đưa vào prompt để định hướng cho LLM trích xuất chính xác các thực thể và quan hệ bệnh lý.
    * **Xây dựng và chuẩn hóa đồ thị tri thức:** Chuẩn hóa các quan hệ, khử trùng lặp ngữ nghĩa và nạp dữ liệu để hình thành đồ thị tri thức hoàn chỉnh về bệnh tiểu đường.

### 3. Nghiên cứu tổng quan
Các nghiên cứu gần đây (5 năm) liên quan đến nội dung đề tài: Trong những năm gần đây, ứng dụng LLM trong tự động hóa xây dựng đồ thị tri thức (KGC) phát triển mạnh. Nổi bật là framework EDC [2] giải quyết tốt bài toán chuẩn hóa quan hệ thông qua độ tương đồng vector. Bên cạnh đó, theo đánh giá tổng quan của Lyu et al. [3], phương pháp Text-to-Text Generation (thuộc NLG) đang trở thành tiêu chuẩn vàng để tự động hóa tài liệu y tế và chuẩn hóa dữ liệu lâm sàng.

Tuy nhiên, khi áp dụng trực tiếp framework này vào hệ thống y tế chuyên sâu, nghiên cứu đã bộc lộ một số khoảng trống lớn cần khắc phục:
* **Chi phí vận hành và tài nguyên hạ tầng:** Framework EDC hiện tại đòi hỏi phải triển khai các LLM cục bộ (Local LLM như Mistral-7b) trên máy trạm có cấu hình rất cao (nhiều GPU).
* **Thiếu module tiền xử lý dữ liệu thông minh (NLG):** Ở phiên bản gốc, EDC [2] chỉ sử dụng kỹ thuật phân đoạn văn bản (chunking) cơ bản trên dữ liệu đầu vào. Khuyết điểm này rất rủi ro với tài liệu y văn lâm sàng, bởi hệ thống chưa có phần Natural Language Generation (NLG) để tiền xử lý các dữ liệu phi cấu trúc phức tạp hay các bảng biểu thành dạng văn xuôi liền mạch, dễ dẫn đến việc mô hình AI bị mất ngữ cảnh và bỏ sót thông tin định lượng quan trọng.
* **Hiệu suất (F1 Score) hiện tại:** Ở phiên bản gốc của EDC [2] và kết quả từ Đồ án 2[1], điểm F1 cho một bộ ba hoàn chỉnh (Full Triple) chỉ dừng ở mức 53.00% [1], [2]. Các phương pháp SOTA khác như GenIE, CodeKGC, ChatIE cũng bộc lộ điểm nghẽn với điểm số F1 thấp [2].

> Bảng: Kết quả đầy đủ của EDC và EDC+R trên bộ dữ liệu Wiki-NRE khi so sánh với mô hình baseline GenIE (Precision, Recall, F1 theo các tiêu chí “Partial”, “Strict” và “Exact”). EDC+R chỉ thực hiện 1 vòng lặp tinh chỉnh (refinement). Các kết quả tốt nhất được in đậm. Nguyên nhân lớn là do hệ thống (1) thiếu module NLG để làm sạch văn bản y khoa thô và (2) hệ thống trích xuất theo hướng zero-parameter tuning, thiếu cơ chế tinh chỉnh thu hồi (Retriever) cho các đặc điểm nhân quả phức tạp đặc thù của bệnh lý y khoa.

**Đề xuất giải pháp mới:** Chính từ những hạn chế trên, đề tài khóa luận này sẽ lấp đầy khoảng trống bằng cách:
* Bổ sung kỹ thuật NLG vào khâu tiền xử lý để làm sạch và định dạng lại tài liệu y khoa tiểu đường trước khi trích xuất.
* Tích hợp lớp Schema Retriever nhằm tạo cơ chế tinh chỉnh lặp (Iterative Refinement), giúp cung cấp các "gợi ý có hướng dẫn" cho mô hình, từ đó khắc phục nhược điểm của zero-parameter tuning và kỳ vọng nâng cao điểm F1 vượt mức 53% hiện tại.

### 4. Cơ sở khoa học và thực tiễn
* **Nền tảng kế thừa:** Kế thừa thành quả công nghệ cốt lõi của Đồ án chuyên ngành 2 [1] nhưng tập trung giải quyết bài toán hẹp và sâu hơn là chẩn đoán bệnh tiểu đường.
* **Giải pháp công nghệ:**
    * Kỹ thuật NLG xử lý dữ liệu thô [3].
    * Kiến trúc EDC+R với mô hình LLM (Llama 3.3/4) và Embedding Model (Jina).
    * Cơ sở dữ liệu đồ thị Neo4j cùng kỹ thuật GraphRAG kết hợp cơ chế Circuit Breaker nhằm ngăn ngừa ảo giác AI (Hallucination) trong y tế?

### 5. Thời gian thực hiện
* **Giai đoạn 1:** Thu thập dữ liệu y văn chuyên sâu về tiểu đường. Ứng dụng NLG để xử lý, chuyển hóa dữ liệu phi cấu trúc thành văn xuôi.
* **Giai đoạn 2:** Lập trình lớp Schema Retriever và cập nhật hệ thống prompt để trích xuất thực thể và quan hệ bằng LLM.
* **Giai đoạn 3:** Chạy hệ thống để xây dựng và chuẩn hóa Đồ thị tri thức, Import vào CSDL Neo4j.
* **Giai đoạn 4:** Xây dựng giao diện phần mềm web hỗ trợ ra quyết định lâm sàng (CDSS), kiểm thử đánh giá bằng điểm F1 và hoàn thiện báo cáo Khóa luận.

### 6. Sản phẩm của đề tài
* **Dữ liệu:** Các tệp (file) dữ liệu y văn bệnh tiểu đường đã được chuẩn hóa thành văn xuôi bởi NLG.
* **Cơ sở dữ liệu:** Đồ thị tri thức chuyên sâu về bệnh tiểu đường lưu trên Neo4j.
* **Phần mềm:** Hệ thống Web hỗ trợ ra quyết định lâm sàng (tích hợp GraphRAG có khả năng truy vấn dựa trên đồ thị).
* **Tài liệu:** Cuốn Báo cáo Khóa luận tốt nghiệp chi tiết, bao gồm số liệu so sánh Benchmark.

### 7. Tài liệu tham khảo
* [1] L. Q. Huy, "Báo cáo Đồ án chuyên ngành 2: Xây dựng Đồ thị tri thức dinh dưỡng bệnh nhân," Báo cáo Đồ án, Khoa Công Nghệ Thông Tin, Trường Đại học Nam Cần Thơ, Cần Thơ, Việt Nam, 2026.
* [2] B. Zhang and H. Soh, "Extract, Define, Canonicalize: An LLM-based Framework for Knowledge Graph Construction," in Proc. 2024 Conf. on Empirical Methods in Natural Language Processing (EMNLP 2024), Nov. 2024, pp. 1-18.
* [3] M. Lyu, X. Li, Z. Chen, J. Pan, C. Peng, S. Talankar, and Y. Wu, "Natural Language Generation in Healthcare: A Review of Methods and Applications," J. Biomed. Inform., vol. 176, p. 104997, Apr. 2026.
* [4] Viện Dinh dưỡng Quốc gia, Bảng Thành phần Thực phẩm Việt Nam. Hà Nội, Việt Nam: NXB Y Học, 2007.

---

| Giảng viên hướng dẫn | Sinh viên thực hiện |
| :--- | :--- |
| (Ký và ghi rõ họ tên) | (Ký và ghi rõ họ tên) |