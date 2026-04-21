# Báo cáo cá nhân - Lab 14

**Họ tên:** Trương Anh Long  
**MSSV:** 2A202600327

---

## 1. Tôi đã làm gì

Trong lab này tôi phụ trách phần **xây dựng core project và thu thập dữ liệu nền (`data/docs`)** cho toàn bộ pipeline.

Về core project, tôi tập trung dựng bộ khung kỹ thuật ban đầu để nhóm có thể phát triển theo từng giai đoạn mà không bị chồng chéo. Tôi chuẩn hóa cấu trúc thư mục, tách rõ các khu vực `data/`, `engine/`, `reports/`, `analysis/`, đồng thời thiết lập luồng chạy chính để các thành viên có thể tích hợp module của mình vào cùng một project thống nhất. Nhờ vậy, các phần Retrieval, Judge và Benchmark về sau có nền tảng chung để kết nối, kiểm thử và so sánh kết quả.

Về dữ liệu, tôi trực tiếp thu thập và chuẩn bị các tài liệu nguồn trong `data/docs/` để làm knowledge base cho hệ RAG. Tôi chọn tài liệu theo tiêu chí có tính nghiệp vụ thực tế (IT helpdesk, chính sách nội bộ, quy định vận hành), đảm bảo nội dung đủ đa dạng để kiểm thử cả câu hỏi fact-check lẫn reasoning. Ngoài việc tập hợp tài liệu, tôi cũng rà soát định dạng và tính nhất quán nội dung để các bước tạo golden set và đánh giá retrieval có đầu vào ổn định.

Kết quả chính tôi hoàn thiện:

- Có **core project** với cấu trúc rõ ràng, giúp các thành viên triển khai theo module mà vẫn đồng bộ.
- Có bộ tài liệu nguồn trong **`data/docs/`** phục vụ trực tiếp cho tạo test cases, retrieval evaluation và failure analysis.
- Có nền tảng dữ liệu đủ tốt để nhóm xây dựng được `golden_set.jsonl` và chạy benchmark end-to-end.

---

## 2. Kiến thức học được

**Tư duy kiến trúc project từ đầu:** Tôi học được rằng một core project tốt cần ưu tiên tính mở rộng và khả năng tích hợp, không chỉ chạy được ở thời điểm hiện tại. Cấu trúc thư mục rõ ràng ngay từ đầu giúp giảm rất nhiều chi phí sửa về sau.

**Chất lượng dữ liệu quyết định chất lượng benchmark:** Qua quá trình thu thập `data/docs`, tôi nhận ra evaluator mạnh đến đâu cũng không bù được đầu vào kém. Nếu tài liệu nguồn thiếu nhất quán hoặc không đủ coverage, kết quả đo sẽ thiếu tin cậy.

**Mối liên hệ giữa dữ liệu và MRR/Hit Rate:** Tôi hiểu rõ hơn rằng MRR và Hit Rate không chỉ phụ thuộc thuật toán retrieval mà còn phụ thuộc cách chuẩn bị tài liệu: mức độ đầy đủ, rõ ràng tiêu đề, độ tách biệt chủ đề giữa các doc.

**Chuẩn hóa dữ liệu để giảm nhiễu:** Việc làm sạch định dạng tài liệu trước khi đưa vào pipeline giúp giảm lỗi truy xuất sai ngữ cảnh, từ đó giúp các chỉ số faithfulness/relevancy phản ánh đúng chất lượng hệ thống hơn.

---

## 3. Vấn đề gặp phải

**Khó khăn trong việc chọn phạm vi tài liệu:** Ban đầu nguồn tài liệu khá rộng, có nhiều nội dung trùng ý hoặc ít giá trị kiểm thử. Tôi phải lọc lại theo tiêu chí "liên quan trực tiếp đến nghiệp vụ hỏi đáp" để tránh làm knowledge base bị nhiễu.

**Định dạng tài liệu chưa đồng nhất:** Một số tài liệu có cấu trúc heading, bullet và đoạn văn không thống nhất, gây khó khăn cho bước chia chunk và mapping ground truth. Tôi đã xử lý bằng cách rà soát, chuẩn hóa trước khi đưa vào pipeline.

**Cân bằng giữa độ đa dạng và khả năng kiểm soát:** Nếu dữ liệu quá đa dạng thì khó đánh giá chính xác, nhưng nếu quá hẹp thì benchmark không phản ánh tình huống thực tế. Tôi rút kinh nghiệm cần giữ mức đa dạng vừa đủ để vừa test được năng lực hệ thống vừa giữ khả năng đo lường ổn định.