# Báo cáo cá nhân - Lab 14

**Họ tên:** Lê Thành Long  
**MSSV:** 2A202600105

---

## 1. Tôi đã làm gì

Trong lab này, tôi phụ trách **Giai đoạn 4: Tối ưu hóa Agent & Hoàn thiện báo cáo phân tích**.

Nhiệm vụ của tôi là biến các kết quả từ quá trình benchmark thành hành động cụ thể để nâng cấp hệ thống và tổng hợp các bài học kinh nghiệm vào báo cáo cuối cùng.

Công việc cụ thể:
- **Tối ưu hóa Agent (Generative RAG Implementation):** Trực tiếp chuyển đổi cơ chế phản hồi từ V1 (nối chuỗi thô) sang V2 (sử dụng LLM). Tôi đã tinh chỉnh `RAG_SYSTEM_PROMPT` trong [agent/main_agent.py](agent/main_agent.py) để LLM có thể tổng hợp kiến thức từ ngữ cảnh một cách thông minh, khắc phục lỗi chỉ trả về tiêu đề (Heading-only).
- **Sửa lỗi kỹ thuật (Hotfix & Compatibility):** Xử lý lỗi API tham số bằng cách chuyển `max_tokens` thành `max_completion_tokens`. Đây là bước then chốt để phục hồi Pipeline benchmark khi chuyển sang các model LLM thế hệ mới.
- **Hoàn thiện báo cáo Failure Analysis:** Viết phần **4. Kế hoạch cải tiến (Action Plan)** trong [analysis/failure_analysis.md](analysis/failure_analysis.md). Tôi đã đề xuất các giải pháp ngắn hạn (sửa lỗi tham số, tối ưu Prompt) và dài hạn (tích hợp Reranking, Cross-document synthesis) để cải thiện điểm số Relevancy và Faithfulness.
- **Kiểm chuẩn cuối cùng:** Sử dụng [check_lab.py](check_lab.py) để rà soát toàn bộ định dạng báo cáo của nhóm, đảm bảo tính nhất quán giữa các phần phân tích kỹ thuật và kết quả thực tế trong `benchmark_results.json`.

---

## 2. Kiến thức học được

**Sức mạnh của Generative RAG:** Hiểu sâu về cách LLM đóng vai trò là bộ não tổng hợp thông tin. Thay vì chỉ là một máy tìm kiếm (Retrieval), Agent giờ đây đã có khả năng suy luận trên ngữ cảnh để đưa ra câu trả lời có cấu trúc và đúng trọng tâm hơn hẳn phiên bản V1.

**Quy trình Phân tích và Cải tiến (Actionable Insights):** Tôi học được cách chuyển hóa các con số khô khan từ benchmark (điểm Judge, điểm RAGAS) thành các hành động cải tiến cụ thể trong mã nguồn. Việc này giúp quy trình phát triển AI trở nên có định hướng thay vì chỉ thử sai ngẫu nhiên.

**Xử lý tham số Model động:** Hiểu được sự khác biệt về đặc tính kỹ thuật giữa các dòng model (OpenAI vs. Compatible Providers). Kỹ năng xử lý các lỗi như `unsupported_parameter` giúp tôi linh hoạt hơn khi triển khai hệ thống trên nhiều nền tảng khác nhau.

**Tư duy MLOps/LLMOps:** Học cách thiết lập các "chốt chặn" chất lượng (Validation Gate) thông qua báo cáo phân tích thất bại và script kiểm tra tự động trước khi quyết định release một phiên bản Agent mới.

---

## 3. Vấn đề gặp phải

**Khó khăn khi tối ưu Prompt:** Việc viết Prompt để LLM vừa trả lời đầy đủ vừa không bị dài dòng hay lặp lại thông tin là một quá trình thử thách. Tôi đã phải thử nghiệm nhiều lần với các từ khóa chỉ định trích xuất nội dung chi tiết để khắc phục lỗi CL_01 (chỉ trích xuất đầu mục).

**Lỗi không tương thích Model:** Trong quá trình tối ưu lên V2, hệ thống gặp lỗi 400 do tham số `max_tokens` không còn được hỗ trợ ở một số model mới. Tôi đã phải thực hiện nghiên cứu tài liệu API để nhanh chóng đổi sang `max_completion_tokens`, giúp khôi phục khả năng phản hồi của Agent.

**Đảm bảo tính đồng nhất của báo cáo:** Do báo cáo Failure Analysis có nhiều phần do các thành viên khác nhau đảm nhiệm, việc kết nối phần phân tích 5 Whys với Kế hoạch cải tiến của tôi đòi hỏi sự trao đổi liên tục để đảm bảo các Action Plan thực sự giải quyết được nguyên nhân gốc rễ đã tìm ra.
