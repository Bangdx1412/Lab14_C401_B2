# Báo cáo cá nhân - Lab 14

**Họ tên:** Đỗ Việt Anh  
**MSSV:** 2A202600043

---

## 1. Tôi đã làm gì

Trong lab này tôi phụ trách phần **Benchmark & Phân tích lỗi (Failure Analysis)** — Giai đoạn 3.

Công việc cụ thể là vận hành toàn bộ pipeline đánh giá trên 60 test cases đã được xây dựng. Tôi đã giám sát quá trình chạy của Multi-Judge để thu thập các chỉ số định lượng (Hit Rate, MRR, RAGAS, Agreement Rate) và thực hiện phân tích định tính cho các trường hợp thất bại.

Kết quả công việc:
- **Phân cụm lỗi (Failure Clustering):** Tôi đã trực tiếp phân loại 19 trường hợp lỗi thành 3 nhóm đặc trưng:
    - `CL_01` — Heading-only: Agent chỉ lấy được tiêu đề mà bỏ sót nội dung câu trả lời.
    - `CL_02` — Low Relevancy: Phản hồi bị cắt cụt do giới hạn token hoặc trích xuất không trọn vẹn.
    - `CL_03` — Safety Rejection: Lỗi từ chối nhầm do trigger bộ lọc an toàn của model.
- **Phân tích 5 Whys:** Thực hiện phân tích sâu cho 3 case lỗi tiêu biểu để tìm ra nguyên nhân gốc rễ nằm ở logic trích xuất (Regex) và cấu trúc tài liệu FAQ lồng nhau, từ đó đề xuất **Action Plan** để nhóm cải thiện Agent V2.
- **Phân tích Regression:** So sánh kết quả giữa V1 và V2 để đưa ra quyết định **Approve Release** khi điểm số cải thiện được +0.0772.

---

## 2. Kiến thức học được

**MRR (Mean Reciprocal Rank):** Một chỉ số quan trọng để đánh giá Retrieval. Tôi hiểu rằng Hit Rate 1.0 (tìm thấy tài liệu) là chưa đủ; MRR giúp đo lường xem tài liệu đúng có nằm ngay vị trí đầu tiên hay không để giảm nhiễu cho Agent.

**Cohen's Kappa:** Công cụ để đo mức độ đồng thuận thực sự giữa hai Judge (GPT-4o và MiniMax). Nó giúp tôi loại trừ được các trường hợp hai model vô tình cho điểm giống nhau do ngẫu nhiên, giúp báo cáo benchmark có độ tin cậy khoa học cao hơn.

**Position Bias & Thẩm định Judge:** Hiểu được hiện tượng LLM Judge có thể bị "thiên kiến vị trí" khi ưu tiên các câu trả lời đứng ở đầu. Việc triển khai `check_position_bias` giúp nhóm chọn lọc được những Judge công tâm hơn cho hệ thống.

**Phân tích Delta:** Học cách sử dụng Delta Score để xây dựng các "Release Gate" tự động. Đây là quy chuẩn quan trọng trong MLOps/LLMOps để quyết định một bản cập nhật Agent có đủ điều kiện để triển khai lên Production hay không.

**Trade-off giữa Chi phí và Chất lượng:** Qua thực tế triển khai, tôi hiểu được sự đánh đổi khi sử dụng nhiều Judge model. Việc kết hợp một model mạnh (GPT-4o) và một model nhẹ hơn (MiniMax) giúp duy trì chi phí thấp ($0.004) mà vẫn đảm bảo độ tin cậy của kết quả thông qua chỉ số Agreement Rate > 85%.

---

## 3. Vấn đề gặp phải

**Sự cố CPU quá tải do Fallback Embeddings:** Khi chạy benchmark nhưng quên chưa set `JINA_API_KEY`, hệ thống tự động fallback về dùng mô hình cục bộ (`SentenceTransformer`). Do tài nguyên máy lab hạn chế, việc này gây ra tình trạng CPU spikes (100% load), làm treo toàn bộ pipeline. Tôi đã xử lý bằng cách cấu hình lại môi trường JINA_API_KEY.

**Lỗi hiển thị trên Windows Terminal:** Trong quá trình xuất kết quả, hệ thống gặp lỗi `UnicodeEncodeError` vì Terminal Windows không hỗ trợ tốt Emoji và ký tự UTF-8. Tôi đã khắc phục bằng cách reconfigure encoding cho `sys.stdout`, giúp các bảng số liệu hiển thị chuẩn xác và chuyên nghiệp.

**Thời gian phản hồi của Judge:** Việc chạy Multi-Judge (2 model song song) tốn khá nhiều thời gian. Nhóm đã phải sử dụng cơ chế `Semaphore` để giới hạn số lượng request đồng thời, vừa đảm bảo tốc độ vừa tránh bị Rate Limit từ phía API providers.
