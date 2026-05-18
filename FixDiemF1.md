# Báo Cáo Phân Tích: Nghịch Lý Điểm Số Trong EDC+R (Retriever)

> **NOTE**
> Báo cáo này giải thích hiện tượng nghịch lý điểm số khi áp dụng Retrieval-Augmented Generation (RAG) vào mô hình trích xuất đồ thị tri thức EDC, đồng thời đề xuất các hướng giải quyết. Rất phù hợp để đưa vào chương **Đánh giá kết quả** và **Hướng phát triển (Future Works)** trong luận văn.

## 1. Hiện tượng (The Phenomenon)

Khi chạy benchmark so sánh giữa mô hình **EDC Thường (Baseline)** và **EDC+R (Có Retriever)** trên tập dữ liệu `wiki-nre_small`, chúng ta quan sát thấy một sự trái ngược trong các hệ số đánh giá F1:

* **Điểm thành phần (Scores per Tag) TĂNG:** Các thành phần đơn lẻ như Subject, Predicate và Object của EDC+R đều có điểm F1 cao hơn Baseline (ví dụ: Subject tăng từ 0.71 lên 0.72).
* **Điểm tổng hợp (Full Triple Score) GIẢM:** Điểm khi xét toàn bộ một bộ ba hoàn chỉnh (Subject, Predicate, Object phải đi chung chính xác) của EDC+R lại giảm nhẹ so với Baseline (từ 0.56 xuống 0.55).

## 2. Phân tích Nguyên nhân Gốc rễ (Root Cause)

Nguyên nhân của hiện tượng này bắt nguồn từ cơ chế mớm cung cấp Gợi ý (Hint) của Retriever và căn bệnh **"Ghép nối chéo" (Cross-matching Error)** của LLM.

> **WARNING**
> Cơ chế hiện tại đang cung cấp Hint dưới dạng các danh sách rời rạc. LLM bị choáng ngợp bởi quá nhiều từ khóa độc lập dẫn đến việc mất khả năng căn chỉnh ranh giới (Boundary Alignment).

**Diễn giải chi tiết:**

* **Nhờ có Hint, LLM "thuộc bài" tốt hơn:** Retriever đã truy xuất và cung cấp chính xác các Thực thể (Entities) và Quan hệ (Relations) có trong Target Schema. LLM sử dụng hiệu quả các từ khóa này, dẫn đến việc bắt trúng rất nhiều Subject, Predicate, Object. Nhờ đó, *điểm thành phần tăng*.
* **LLM bị loạn khi lắp ráp:** Vì các Hint (Thực thể và Quan hệ) được ném vào Prompt dưới dạng hai khối độc lập, LLM thiếu đi ngữ cảnh về việc "Thực thể nào phải đi với Quan hệ nào". Hậu quả là nó tự ý lấy Subject của bộ ba này, ghép với Predicate của bộ ba khác (mang râu ông nọ cắm cằm bà kia). Do các bộ ba bị ghép sai lệch, số lượng Full Triple khớp hoàn toàn 100% với đáp án bị giảm sút.

## 3. Đề xuất Hướng khắc phục (Mitigation Strategies)

Để giải quyết triệt để nhược điểm này và tối ưu hóa sức mạnh của EDC+R, dưới đây là 3 hướng cải tiến kiến trúc:

### 3.1. Kỹ thuật Kỹ sư Dấu nhắc Chặt chẽ (Strict Prompt Engineering)
Cải tiến trực tiếp file `oie_few_shot_refine_examples.txt` (bước Refinement) bằng cách bổ sung các quy tắc bắt buộc (Constraints) vào System Prompt.

* **Giải pháp:** Thêm chỉ thị: *"Chỉ được phép chuẩn hóa tên Quan hệ (Predicate) cho khớp với Gợi ý. Tuyệt đối không được thay đổi, hoán đổi hoặc tạo mới các cặp Chủ thể (Subject) và Đối tượng (Object) đã có."*
* **Tác dụng:** Đóng băng cấu trúc `(A, ?, B)`, ép LLM chỉ tập trung sửa lỗi thành phần Predicate, ngăn chặn hoàn toàn việc ghép chéo chủ ngữ/vị ngữ.

### 3.2. Chuyển đổi sang Triplet-based Hinting
Thay vì để Retriever truy xuất và trả về hai danh sách Thực thể và Quan hệ rời rạc, hãy cung cấp Hint dưới dạng các **Khuôn mẫu Bộ ba (Triplet Templates)**.

> **TIP**
> *Thay vì gợi ý:* Quan hệ: `[sáng_lập]`
> *Hãy gợi ý:* Khuôn mẫu: `[Tên_Người] -> sáng_lập -> [Tên_Công_Ty]`

* **Tác dụng:** Cung cấp cho LLM ràng buộc về kiểu dữ liệu (Type Constraints) của từng quan hệ. Khi LLM nhìn thấy khuôn mẫu này, nó sẽ tự động nhận thức được rằng quan hệ "sáng lập" chỉ được phép ghép với Subject là "Người" và Object là "Công ty", giảm thiểu tối đa các bộ ba vô nghĩa.

### 3.3. Tích hợp Bước Kiểm duyệt (Verification / Self-Correction Step)
Thêm một luồng Agentic Workflow ngay sau khi Refinement hoàn tất.

* **Giải pháp:** Đưa danh sách các Full Triple vừa được tạo ra cùng với câu văn gốc vào một module LLM đóng vai trò làm Verifier (Người kiểm duyệt). Verifier có nhiệm vụ trả lời câu hỏi dạng Yes/No: *"Trong ngữ cảnh câu văn này, [Subject] có thực sự thực hiện hành động [Predicate] đối với [Object] không?"*.
* **Tác dụng:** Các bộ ba bị ghép chéo sẽ ngay lập tức bị Verifier đánh cờ "No" và loại bỏ khỏi kết quả cuối cùng (Canonicalized Graph). Điều này giúp làm sạch rác (Spurious Triples) và kéo điểm Precision của Full Triple lên mức tối đa.