# Báo cáo cá nhân - Lab 14

**Họ tên:** Đỗ Xuân Bằng  
**MSSV:** 2A202600044  

---

## 1. Tôi đã làm gì

Trong lab này tôi phụ trách phần **tạo bộ dữ liệu kiểm thử (Golden Dataset)** — Giai đoạn 1.

Công việc cụ thể là hoàn thiện file `data/synthetic_gen.py`. Script này đọc nội dung từ 5 tài liệu IT Helpdesk thực tế trong `data/docs/` rồi tổng hợp thành bộ câu hỏi kiểm thử. Toàn bộ Q&A được soạn thủ công dựa sát nội dung tài liệu, không gọi API ngoài, nên kết quả ổn định và không tốn chi phí. Script dùng `asyncio` để cấu trúc code theo dạng bất đồng bộ, chuẩn bị cho việc tích hợp vào pipeline lớn hơn sau này.

Kết quả chạy `python data/synthetic_gen.py` sinh ra file `data/golden_set.jsonl` với **60 test cases** từ 5 nguồn tài liệu:

- `doc_it_faq` — IT Helpdesk FAQ (tài khoản, VPN, phần mềm...)
- `doc_access_control` — Quy trình cấp quyền hệ thống
- `doc_hr_leave` — Chính sách nghỉ phép HR
- `doc_refund` — Chính sách hoàn tiền
- `doc_sla` — Quy định xử lý sự cố theo SLA

Ngoài ra còn có 10 **adversarial cases** gồm các tình huống: jailbreak, prompt injection, ambiguous, out-of-context, conflicting intent — để kiểm tra xem Agent có xử lý an toàn không.

Thống kê kết quả thực tế:

```
Total cases: 60
Types    : fact-check: 34, reasoning: 16, adversarial: 2,
           out-of-context: 2, ambiguous: 2, conflicting intent: 2, jailbreak: 2
Difficulty: easy: 20, medium: 24, hard: 16
Has ground_truth_id: 50 / 60
```

---

## 2. Kiến thức học được

**MRR (Mean Reciprocal Rank):** Đo xem Vector DB có lấy đúng tài liệu không. Với mỗi câu hỏi, nếu tài liệu đúng nằm ở vị trí 1 thì điểm là 1.0, vị trí 2 là 0.5, không có là 0. Đó là lý do dataset cần có trường `ground_truth_id` — để hệ thống biết tài liệu nào là đúng khi tính điểm.

**Cohen's Kappa:** Đo mức đồng thuận thực sự giữa 2 Judge model, loại trừ phần trùng hợp ngẫu nhiên. Chỉ dùng tỷ lệ đồng ý thông thường thì chưa đủ vì 2 model có thể tình cờ cho điểm giống nhau mà không phản ánh sự nhất trí thực sự.

**Position Bias:** Hiện tượng LLM Judge ưu tiên câu trả lời đứng đầu hoặc cuối hơn là đánh giá nội dung thực sự. Cách phát hiện: đổi thứ tự A-B rồi chạy lại — nếu điểm thay đổi nhiều là có bias.

**Trade-off chi phí:** Nhóm chọn sinh dữ liệu bằng cách viết tay (offline/deterministic) thay vì gọi LLM. Cách này tuy mất công soạn ban đầu nhưng không tốn chi phí API, kết quả ổn định và kiểm soát được hoàn toàn — phù hợp với giai đoạn xây dựng nền tảng.

---

## 3. Vấn đề gặp phải

**Phân bổ độ khó mất cân bằng ban đầu:** Lúc đầu câu hỏi hard quá nhiều so với easy và medium. Phải điều chỉnh lại số lượng từng mức khi soạn thủ công để đạt được phân bổ easy/medium/hard hợp lý hơn (20/24/16).

**Adversarial cases khó thiết kế:** Các tình huống như "conflicting intent" hay "ambiguous" cần suy nghĩ kỹ để `expected_answer` phản ánh đúng cách Agent nên xử lý — không phải trả lời nội dung câu hỏi mà phải từ chối hoặc hỏi lại.

**Định dạng `ground_truth_id`:** Với adversarial cases, tài liệu tham chiếu là `null` vì câu hỏi không dựa vào tài liệu nào — cần xử lý đặc biệt khi tính Hit Rate để tránh bị tính sai.
