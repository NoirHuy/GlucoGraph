# Annotation Guideline — Triple Validity Benchmark (Diabetes Domain)

## Mục đích
Bạn sẽ nhận một file CSV chứa danh sách các "triple" dạng `(Subject, Relation, Object)`.
Nhiệm vụ: gán nhãn cho mỗi triple là **valid**, **invalid**, hoặc **uncertain**,
dựa trên kiến thức y khoa và/hoặc tìm kiếm nhanh trên PubMed/UpToDate nếu cần.

**Quan trọng**: bạn KHÔNG biết triple nào là "thật" (từ BioRED) hay "giả" (bị corrupt).
Hãy đánh giá hoàn toàn dựa trên tính đúng đắn y khoa của câu phát biểu.

---

## Cách đọc một triple

Một dòng dữ liệu ví dụ:

| subject | relation | object |
|---|---|---|
| Metformin | TREATS | Type 2 Diabetes Mellitus |

Đọc thành câu: **"Metformin TREATS Type 2 Diabetes Mellitus"**
→ "Metformin điều trị Đái tháo đường type 2" → đúng về y khoa → gán **valid**

---

## Định nghĩa các relation trong bộ dữ liệu

| Relation | Ý nghĩa | Ví dụ câu |
|---|---|---|
| TREATS | Chất X được dùng để điều trị bệnh Y | "Insulin TREATS Diabetes Mellitus" |
| INCREASES_RISK_OF | X làm tăng nguy cơ mắc Y | "Obesity INCREASES_RISK_OF Type 2 Diabetes" |
| ASSOCIATED_WITH | X có liên quan (không nhất thiết nhân quả) với Y | "Gene TCF7L2 ASSOCIATED_WITH Type 2 Diabetes" |
| PROTECTS_AGAINST | X làm giảm nguy cơ / bảo vệ chống lại Y | "Gene X PROTECTS_AGAINST Diabetic Nephropathy" |
| INTERACTS_WITH | Hai chất X và Y có tương tác dược lý | "Metformin INTERACTS_WITH Cimetidine" |
| COADMINISTERED_WITH | X và Y thường được dùng phối hợp | "Metformin COADMINISTERED_WITH Sulfonylurea" |
| BINDS_TO | Protein/Gene X liên kết với chất Y | "Insulin Receptor BINDS_TO Insulin" |
| COMPARED_WITH | X và Y được so sánh trong nghiên cứu | "Metformin COMPARED_WITH Sulfonylurea" |
| CONVERTED_TO | X được chuyển hóa thành Y | "Proinsulin CONVERTED_TO Insulin" |

---

## Quy tắc gán nhãn

### → `valid`
Câu phát biểu **đúng về mặt y khoa**, dù chỉ đúng trong một số trường hợp/dưới một số điều kiện
(ví dụ: "Metformin TREATS Type 2 Diabetes" vẫn valid dù không phải bệnh nhân nào cũng dùng).

### → `invalid`
Câu phát biểu **sai về mặt y khoa**, hoặc **không có ý nghĩa lâm sàng** (ví dụ: quan hệ giữa
hai thực thể thuộc loại không tương thích — như một bệnh "BINDS_TO" một bệnh khác).

### → `uncertain`
Bạn **không đủ kiến thức/thông tin để khẳng định**, hoặc tài liệu tham khảo không nhất quán.
Hãy dùng nhãn này một cách hạn chế — chỉ khi thực sự cần.

---

## Một số lưu ý

1. Đánh giá độc lập, không thảo luận với annotator khác trước khi cả hai hoàn thành.
2. Nếu cần, có thể tra cứu nhanh trên PubMed/Google Scholar — ghi chú nguồn vào cột `notes`.
3. Thời gian gợi ý: khoảng 1-2 phút/triple.
4. Sau khi hoàn thành, lưu file với tên `annot_<ten_ban>.csv` (ví dụ `annot_huy.csv`,
   `annot_lan.csv`) và gửi lại cho người tổng hợp.
