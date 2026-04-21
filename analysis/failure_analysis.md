# Báo cáo Phân tích Thất bại (Failure Analysis Report)

## 1. Tổng quan Benchmark
Hệ thống Evaluation Factory đã hoàn thành đánh giá trên bộ Golden Dataset gồm 60 test cases.

- **Chỉ số chính:**
    - **Điểm LLM-Judge trung bình:** 3.70 / 5.0
    - **Tỉ lệ Pass/Fail:** 41 / 19 (68.33%)
    - **Điểm RAGAS trung bình:**
        - Faithfulness (Độ trung thực): 0.78
        - Relevancy (Độ liên quan): 0.37
    - **Hit Rate:** 1.00 | **MRR:** 0.9896
    - **Tỉ lệ đồng thuận (Agreement Rate):** 86.38%
- **Kết luận:** **APPROVE RELEASE** (V2 cải thiện 0.0772 điểm so với V1).

- **Chi tiết kỹ thuật (Expert Evidence):**
    - **Multi-Judge:** Kết hợp GPT-4o (Judge 1) và MiniMax-M2.5 (Judge 2) để tăng độ khách quan.
    - **Hiệu năng:** Pipeline Async xử lý 60 cases chỉ mất **17.5s/case** (Tổng ~1.8 phút).
    - **Dataset:** 60 cases được gắn thẻ Ground Truth IDs và bộ Red Teaming đầy đủ.

## 2. Phân nhóm lỗi (Failure Clustering)

| Cluster ID | Kiểu lỗi (Failure Pattern) | Tần suất | Nguyên nhân gốc rễ (Giả thuyết) |
|------------|-----------------|-----------|-------------------------|
| CL_01 | **Chỉ trả về tiêu đề (Heading-only)** | 35% | Agent V2 tối ưu trích xuất nhanh nhưng bỏ sót nội dung chi tiết bên dưới các mục lục. |
| CL_02 | **Độ liên quan thấp (Low Relevancy)** | 45% | Token limit hoặc truncation làm mất các thông tin chi tiết quan trọng trong phản hồi. |
| CL_03 | **Lỗi phản hồi an toàn (Safety Rejection)** | 20% | Các bộ Red Teaming trigger safety filter của model dù câu hỏi mang tính chất kiểm thử hợp lệ. |

## 3. Phân tích 5 Whys (Chọn 3 case tiêu biểu)

### Case #1: Quên mật khẩu (Index 0)
- **Vấn đề**: Agent trả về tiêu đề thư mục thay vì hướng dẫn reset.
- **Why 1**: Agent trích xuất nhầm dòng chứa câu hỏi trong tài liệu.
- **Why 2**: Logic regex trong `main_agent.py` ưu tiên các dòng có dấu hỏi.
- **Why 3**: Prompt của V2 yêu cầu trích xuất "câu trả lời" nhưng không định nghĩa rõ cấu trúc FAQ.
- **Why 4**: Tài liệu FAQ có dạng câu hỏi/trả lời lồng nhau làm Agent bị nhầm.
- **Why 5**: Thiếu bước kiểm chuẩn nội dung (Content Validation) sau khi trích xuất.

### Case #2: Gia hạn license (Index 6)
- **Vấn đề**: Thiếu thông tin về thời gian nhắc nhở 30 ngày.
- **Why 1**: Agent dừng trích xuất ngay sau dòng đầu tiên tìm thấy.
- **Why 2**: Heuristic trích xuất đang giới hạn số lượng câu/dòng.
- **Why 3**: Thông tin quan trọng nằm ở cuối đoạn văn bị cắt bỏ.
- **Why 4**: Keyword "gia hạn" mạnh hơn "nhắc nhở" trong Lexical search.
- **Why 5**: Cơ chế truy xuất Lexical (BM25) chưa đảm bảo tính trọn vẹn của ngữ cảnh (Context integrity).

### Case #3: Quy trình cài phần mềm (Index 5)
- **Vấn đề**: Thiếu tên project Jira "IT-SOFTWARE".
- **Why 1**: Thông tin bị chia tách ở nhiều file khác nhau.
- **Why 2**: Agent chỉ lấy context từ file có độ tương đồng cao nhất.
- **Why 3**: Thiếu khả năng tổng hợp thông tin liên văn bản (Cross-document synthesis).
- **Why 4**: Agent ưu tiên tính "Grounding" (có dẫn chứng) hơn tính "Completeness" (đầy đủ).
- **Why 5**: Kiến trúc hiện tại chỉ chạy 1 lượt (Single-pass), không có bước kiểm soát chất lượng (Quality reflection).

## 4. Kế hoạch cải tiến (Action Plan)

### 4.1. Chuyển đổi sang Kiến trúc Generative RAG (Trọng tâm)
- **Sử dụng LLM làm trung tâm (V2)**: Thay thế hoàn toàn cơ chế "nối chuỗi thô" (V1) bằng việc sử dụng mô hình ngôn ngữ lớn (LLM) để suy luận và tổng hợp câu trả lời từ ngữ cảnh.
- **Tối ưu hóa Synthesis**: Tận dụng khả năng của LLM để trả lời các câu hỏi phức tạp cần sự kết hợp thông tin từ nhiều đoạn văn bản khác nhau, thay vì chỉ lấy 1-2 đoạn đầu tiên như V1.

### 4.2. Tối ưu hóa chất lượng phản hồi của Agent
- **Cải thiện Prompt Engineering**: Cập nhật `RAG_SYSTEM_PROMPT` để định hướng LLM đóng vai chuyên gia hỗ trợ nội bộ chuyên nghiệp, biết cách trích xuất chuẩn xác thông tin chi tiết và từ chối các yêu cầu nằm ngoài dữ liệu được cung cấp.
- **Khắc phục lỗi trích xuất tiêu đề (CL_01)**: Điều chỉnh hướng dẫn trong Prompt để LLM tập trung vào nội dung thực thi (actionable content) thay vì chỉ liệt kê các đầu mục lớn trong tài liệu.

### 4.3. Sửa lỗi kỹ thuật để khôi phục Pipeline
- **Khắc phục tham số mô hình**: Chuyển đổi `max_tokens` thành `max_completion_tokens` trong [agent/main_agent.py](agent/main_agent.py) để LLM có thể hoạt động ổn định và trả về kết quả thay vì thông báo lỗi API (Hotfix).
- **Mở rộng Context Window**: Tăng chỉ số `top_k` để cung cấp cho LLM nhiều dữ liệu nền tảng hơn, giúp tăng điểm **Relevancy** và **Faithfulness**.

### 4.4. Đánh giá và Duy trì chất lượng
- **Giám sát thông qua LLM-Judge**: Sử dụng bộ đôi GPT-4o và MiniMax để đánh giá xem câu trả lời do LLM của Agent tạo ra có thực sự vượt trội hơn cơ chế nối chuỗi của V1 hay không.
- **Phòng ngừa sụt giảm hiệu năng (Regression)**: Thiết lập quy trình chạy benchmark tự động sau mỗi lần tinh chỉnh Prompt để đảm bảo điểm số V2 luôn duy trì ở mức cao.

---
**Người báo cáo:** Lê Thành Long
**Ngày cập nhật:** 21/04/2026
