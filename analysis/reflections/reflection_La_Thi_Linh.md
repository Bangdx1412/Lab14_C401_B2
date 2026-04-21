# Báo cáo cá nhân - Lab 14

**Họ tên:** Lã Thị Linh  
**MSSV:** 2A202600089

---

## 1. Tôi đã làm gì

Trong lab này tôi phụ trách phần **Phát triển Eval Engine (RAGAS, Custom Judge) và Async Runner** - Giai đoạn 2.

Công việc chính của tôi tập trung vào 4 module:

- `engine/retrieval_eval.py`: xây dựng bộ đo cho Retrieval và Answer Quality. Module này tính `Hit Rate`, `MRR`, `faithfulness`, `relevancy`, đồng thời chuẩn hóa mapping giữa `source` và `ground_truth_id` để có thể chấm đúng các test case có tài liệu tham chiếu.
- `engine/llm_judge.py`: triển khai cơ chế **Multi-Judge consensus** với 2 model chấm độc lập. Tôi thiết kế 2 vai trò Judge riêng cho `accuracy` và `groundedness`, chuẩn hóa JSON output, tính `agreement_rate` và thêm logic giải quyết xung đột điểm số bằng `mean_consensus` hoặc `weighted_consensus`.
- `engine/runner.py`: xây dựng **Async Benchmark Runner** để chạy nhiều test case song song. Runner dùng `asyncio`, `Semaphore`, `create_task` và `gather` để tăng tốc toàn pipeline, đồng thời chuẩn hóa output của từng case gồm latency, score, retrieval info, token usage và error handling.
- `main.py`: tích hợp evaluator, multi-judge và runner vào một pipeline benchmark hoàn chỉnh; sinh `reports/summary.json`, `reports/benchmark_results.json` và tính delta giữa V1 với V2 để phục vụ regression testing.

Kết quả kỹ thuật mà tôi hoàn thiện được trong Giai đoạn 2:

- Có bộ **Retrieval Evaluator** tách riêng khỏi agent logic, có thể chấm theo từng case hoặc theo batch.
- Có **Custom LLM Judge** dùng 2 model gpt-4o-mini và MiniMax-M2.5 khác nhau thay vì phụ thuộc vào một judge duy nhất.
- Có cơ chế đo **Agreement Rate** và xử lý conflict tự động khi 2 judge lệch điểm quá nhiều.
- Có **Benchmark Runner bất đồng bộ** giúp chạy benchmark hàng loạt thay vì xử lý tuần tự từng câu hỏi.
- Có phần tổng hợp metrics cuối cùng gồm `avg_score`, `pass_rate`, `hit_rate`, `mrr`, `agreement_rate`, `avg_faithfulness`, `avg_relevancy`, `avg_latency`, `total_tokens`, `estimated_cost`.

Phần việc này bám trực tiếp vào yêu cầu của lab ở Giai đoạn 2: xây dựng một Eval Engine có thể đo Retrieval, chấm Generation bằng nhiều Judge, và chạy toàn bộ benchmark theo cơ chế async.

---

## 2. Kiến thức học được

**MRR (Mean Reciprocal Rank):** Tôi hiểu rõ hơn rằng Hit Rate chỉ cho biết tài liệu đúng có xuất hiện hay không, còn MRR mới phản ánh chất lượng xếp hạng của Retrieval. Nếu đúng tài liệu nhưng luôn nằm ở vị trí thấp thì Generation vẫn dễ bị nhiễu.

**Faithfulness và Relevancy:** Khi chấm câu trả lời, không thể chỉ nhìn final answer có giống expected answer hay không. Faithfulness giúp kiểm tra mức độ bám vào context đã retrieve, còn relevancy đo xem câu trả lời có thực sự bám đúng câu hỏi và ground truth không.

**Multi-Judge Consensus:** Một Judge duy nhất dễ tạo ra thiên lệch. Khi triển khai 2 judge độc lập cho `accuracy` và `groundedness`, tôi hiểu rõ hơn cách tách tiêu chí chấm điểm, sau đó mới hợp nhất lại bằng consensus logic để tăng độ tin cậy cho benchmark.

**Agreement Rate và Cohen's Kappa:** Trong code hiện tại nhóm dùng `agreement_rate` để đo độ gần nhau giữa 2 Judge theo thang điểm liên tục. Qua quá trình làm, tôi cũng hiểu thêm rằng nếu cần đánh giá sâu hơn về độ đồng thuận thực sự thì có thể mở rộng sang Cohen's Kappa để loại bớt phần trùng hợp ngẫu nhiên.

**Position Bias:** Khi xây dựng phần `check_position_bias`, tôi học được rằng LLM Judge có thể thiên vị đáp án xuất hiện trước hoặc sau. Đây là một rủi ro thực tế trong hệ thống evaluation và không nên bỏ qua nếu muốn benchmark đáng tin cậy.

**Trade-off giữa tốc độ, chi phí và độ tin cậy:** Async runner giúp benchmark nhanh hơn, nhưng gọi nhiều judge song song cũng làm tăng nguy cơ rate limit, lỗi mạng và chi phí API. Vì vậy hệ thống cần vừa tối ưu concurrency vừa giữ khả năng kiểm soát lỗi.

---

## 3. Vấn đề gặp phải

**Khó khăn khi chuẩn hóa đầu vào để chấm Retrieval:** Dữ liệu retrieve có thể đi ra dưới nhiều dạng khác nhau như `retrieved_ids`, `sources`, hoặc `chunks[].metadata.doc_id`. Tôi phải viết logic gom và chuẩn hóa lại để evaluator không bị lệ thuộc vào một format duy nhất.

**Đầu ra từ LLM Judge không ổn định hoàn toàn:** Judge model không phải lúc nào cũng trả về JSON sạch. Vì vậy tôi phải bổ sung cơ chế `_extract_json` để bóc JSON từ raw text, fenced block hoặc chuỗi có kèm giải thích ngoài lề.

**Xử lý xung đột giữa 2 Judge:** Không phải lúc nào hai judge cũng chấm gần nhau. Tôi phải xác định một rule rõ ràng: nếu chênh lệch nhỏ thì lấy trung bình, còn nếu lệch lớn thì dùng weighted consensus để giảm rủi ro một judge kéo score đi quá xa.

**Lỗi cấu hình môi trường và lỗi kết nối API:** Trong quá trình chạy thực tế, benchmark từng gặp lỗi do `JUDGE_1_MODEL` và `JUDGE_2_MODEL` bị điền tên provider thay vì model ID thật, hoặc lỗi `Connection error` khi gọi judge API. Từ đó tôi rút ra rằng Eval Engine ngoài phần chấm điểm còn phải có validation cấu hình và error handling tốt để report không bị gây hiểu nhầm.

**Giới hạn đồng thời khi chạy async:** Chạy toàn bộ case song song là nhanh nhưng dễ đụng rate limit hoặc làm pipeline thiếu ổn định. Tôi dùng `Semaphore` để giới hạn concurrency, cân bằng giữa tốc độ benchmark và độ an toàn khi gọi nhiều dịch vụ cùng lúc.

**Khó khăn trong việc tách lỗi hệ thống khỏi lỗi chất lượng agent:** Khi benchmark thất bại do cấu hình hoặc mạng, điểm số có thể không phản ánh đúng chất lượng V1 và V2. Đây là lý do tôi đánh giá việc phân loại `status: pass/fail/error` và giữ báo cáo lỗi minh bạch là rất quan trọng trong một hệ thống eval chuyên nghiệp.
