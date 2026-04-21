# Báo cáo Phân tích Thất bại (Failure Analysis Report)

## 1. Tổng quan Benchmark
- **Tổng số cases:** 60
- **Tỉ lệ Pass/Fail:** 51 / 9 (Tỉ lệ đạt 85%)
- **Điểm RAGAS trung bình:**
    - Faithfulness (Độ trung thực): 0.82
    - Relevancy (Độ liên quan): 0.39
- **Điểm LLM-Judge trung bình:** 3.58 / 5.0

## 2. Phân nhóm lỗi (Failure Clustering)

| Cluster ID | Kiểu lỗi (Failure Pattern) | Tần suất | Nguyên nhân gốc rễ (Giả thuyết) |
|------------|-----------------|-----------|-------------------------|
| CL_01 | **Chỉ trả về tiêu đề (Heading-only)** | Cao (~40%) | Agent V2 trích xuất tiêu đề mục nhưng bỏ sót nội dung câu trả lời thực tế bên dưới. |
| CL_02 | **Độ liên quan thấp (Low Relevancy)** | Cao (~60%) | Phản hồi quá ngắn hoặc chứa nhiều câu mẫu thừa (ví dụ: "Theo tài liệu nội bộ..."). |
| CL_03 | **Trích xuất thiếu (Incomplete Extraction)** | Trung bình (~15%) | Đối với câu hỏi phức cảp, Agent chỉ trích xuất được phần đầu của văn bản. |

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
- [x] Thay thế các biểu tượng Emoji trong code để tránh lỗi hiển thị trên Windows terminal.
- [ ] Thay đổi chiến lược Chunking từ kích thước cố định sang Semantic Chunking (phân đoạn theo ngữ nghĩa).
- [ ] Cập nhật System Prompt để yêu cầu Agent trích xuất toàn bộ câu trả lời, không chỉ tiêu đề.
- [ ] Bổ sung bước Reranking (tái xếp hạng) vào quy trình Retrieval để lọc context tốt hơn.
