# Day 14 — Exercises

## AI Evaluation & Benchmarking · Lab Worksheet

**Thời gian làm bài:** 09:15–12:00

**Domain:** Northstar University Student Services

Điền trực tiếp câu trả lời vào file này. Golden dataset 20 QA được viết một lần
duy nhất trong `golden_dataset.json`, không chép lại toàn bộ vào Markdown.

---

Từ 09:15–09:30, cài môi trường và chạy baseline tests theo `guide_lab.md`.

---

## Part 1 — Warm-up (09:30–09:45)

### Exercise 1.1 — RAGAS Metric Thresholds

Theo bài giảng:

- 0.8–1.0: Good — monitor, maintain.
- 0.6–0.8: Needs work — analyze failures, iterate.
- Dưới 0.6: Significant issues — investigate.

Với từng metric, xác định khi nào score thấp có thể chấp nhận và khi nào là
critical.

| Metric | Acceptable Low Score Scenario | Critical Low Score Scenario | Action Required |
|---|---|---|---|
| Faithfulness | Câu trả lời ngắn có dùng cách diễn đạt hoặc thuật ngữ tương đương nhưng ít trùng từ với context; cần human review xác nhận nội dung vẫn được hỗ trợ. | Câu trả lời chứa ngày, số tiền, điều kiện hoặc ngoại lệ không có trong tài liệu nguồn, đặc biệt với học phí, học bổng, quyền riêng tư và khiếu nại. | Kiểm tra retrieved context và trace; bổ sung grounding guardrail, yêu cầu nêu rõ khi corpus thiếu thông tin và chặn deploy nếu lỗi có thể gây hại. |
| Answer Relevance | Câu trả lời đúng chính sách nhưng có thêm một ít hướng dẫn liên quan, ví dụ nhắc văn phòng chịu trách nhiệm. | Câu trả lời không giải quyết ý định chính, trả lời sai loại thủ tục hoặc chuyển sang chủ đề ngoài câu hỏi. | Rà soát intent/routing và prompt; thêm test phân biệt các quy trình dễ nhầm như grade appeal với service complaint. |
| Context Recall | Câu hỏi chỉ cần một fact đơn giản và chunk lấy được đã chứa đủ fact đó dù không bao phủ toàn bộ cách viết của expected answer. | Retriever bỏ sót deadline, mức phí, điều kiện bắt buộc hoặc ngoại lệ cần thiết để trả lời chính xác. | Cải thiện query, chunking và top-k; thêm metadata/effective-date filtering rồi chạy lại benchmark. |
| Context Precision | Recall vẫn cao và generator có thể bỏ qua vài chunk nhiễu không gây sai answer. | Evidence đúng bị xếp sau nhiều chunk không liên quan, làm generator dùng nhầm policy hoặc vượt context window. | Thêm reranking, lọc metadata và đo lại Average Precision@K; theo dõi cả Recall để tránh loại mất evidence. |
| Completeness | Người dùng chỉ hỏi một fact hẹp và answer bỏ qua chi tiết phụ không cần thiết cho hành động tiếp theo. | Answer thiếu điều kiện, deadline, ngoại lệ hoặc bước escalation khiến sinh viên thực hiện sai quy trình. | Bổ sung checklist theo loại intent, few-shot answer đầy đủ và test coverage cho các claim bắt buộc. |

### Exercise 1.2 — Bias trong LLM-as-a-Judge

Ba bias thường gặp:

- Position bias: judge ưu tiên answer xuất hiện trước.
- Verbosity bias: judge ưu tiên answer dài hơn.
- Self-preference: judge ưu tiên output giống chính model đó.

**Câu 1: Thiết kế experiment phát hiện position bias với ít nhất hai conditions.**

> *Câu trả lời:*

Tạo một tập các cặp câu trả lời A/B có chất lượng tương đương và chấm trong ít
nhất hai conditions: condition 1 đặt A trước B, condition 2 đảo B trước A nhưng
giữ nguyên question, rubric và tham số judge. Có thể thêm condition 3 đổi nhãn
A/B thành Response X/Y để loại ảnh hưởng của tên nhãn. Chạy nhiều cặp và nhiều
lần với thứ tự được randomize; nếu cùng một nội dung nhận điểm cao hơn hoặc được
chọn thường xuyên hơn khi đứng đầu, chênh lệch có ý nghĩa và lặp lại qua các
cặp, đó là bằng chứng của position bias.

**Câu 2: Làm thế nào giảm verbosity bias bằng rubric design?**

> *Câu trả lời:*

Rubric phải chấm theo các claim bắt buộc, độ chính xác, evidence, actionability
và safety/privacy thay vì độ dài. Nêu rõ câu trả lời ngắn nhưng đủ và đúng vẫn
có thể đạt mức 5; nội dung lặp lại, lan man hoặc thêm claim không được hỗ trợ
không được cộng điểm và có thể bị trừ điểm. Judge cũng nên nhận answer đã ẩn
thông tin về độ dài/nguồn model khi có thể.

**Câu 3: Tại sao cần calibrate LLM judge với human labels?**

> *Câu trả lời:*

Human labels tạo mốc chuẩn để biết judge có hiểu rubric giống người đánh giá
hay không, đồng thời phát hiện systematic bias như quá dễ, quá nghiêm hoặc ưu
tiên văn phong giống chính model judge. Việc calibration trên một tập đại diện,
đặc biệt gồm deadline, ngoại lệ và privacy failures, giúp chọn threshold phù
hợp và đo inter-rater agreement trước khi dùng judge làm quality gate.

### Exercise 1.3 — Evaluation trong CI/CD

**Câu 1: Chọn threshold để block deployment.**

| Metric | Threshold | Lý do |
|---|---:|---|
| Faithfulness | 0.80 | Student Services có nhiều thông tin nhạy cảm như deadline, phí và eligibility; claim không grounded có thể khiến sinh viên hành động sai. Mọi privacy/safety hallucination phải block dù average vẫn đạt ngưỡng. |
| Answer Relevance | 0.75 | Answer phải giải quyết đúng intent, nhưng word-overlap có thể đánh giá thấp paraphrase hợp lệ nên ngưỡng thấp hơn Faithfulness và cần xem failure theo case. |
| Completeness | 0.80 | Việc bỏ sót điều kiện hoặc ngoại lệ quan trọng có thể làm hướng dẫn đúng một phần nhưng không sử dụng được; các critical-field omissions phải block riêng. |

**Câu 2: Khi nào dùng offline evaluation, online evaluation và human review?**

> *Câu trả lời:*

Dùng offline evaluation cho mọi thay đổi code, prompt, retriever, model hoặc
corpus trước merge/release; chạy golden dataset cố định để so với baseline và
phát hiện regression. Dùng online evaluation sau deploy để theo dõi traffic
thật, drift, latency, cost, feedback và các intent mới nhưng phải bảo vệ dữ liệu
cá nhân. Dùng human review để hiệu chuẩn LLM judge, xử lý case high-stakes hoặc
mơ hồ, xem xét privacy/safety failures và audit định kỳ các mẫu online. Ba hình
thức bổ trợ nhau: offline là quality gate, online phát hiện vấn đề thực tế, còn
human review cung cấp chuẩn và quyết định cho trường hợp rủi ro cao.

---

## Part 2 — Core Coding (09:45–10:40)

Hoàn thiện các TODO bắt buộc trong `template.py`.

### Task 1 — Data Models

- `QAPair`: question, expected answer, gold context, metadata và retrieved contexts.
- `EvalResult`: answer-side scores, optional retrieval scores, pass/failure fields.
- `overall_score()`: trung bình Faithfulness, Relevance và Completeness.

### Task 2 — RAGASEvaluator

Answer-side:

- `evaluate_faithfulness(answer, context)`
- `evaluate_relevance(answer, question)`
- `evaluate_completeness(answer, expected)`

Retrieval-side:

- `evaluate_context_recall(contexts, expected)`
- `evaluate_context_precision(contexts, expected)`

Full pipeline:

- `run_full_eval(..., contexts=None)` luôn tính ba answer metrics.
- Nếu có `contexts`, tính và lưu thêm Context Recall và Context Precision.
- Retrieval scores không làm thay đổi `overall_score()` và pass rule gốc.

### Task 3 — LLMJudge

- `score_response(question, answer, rubric)`
- `detect_bias(scores_batch)`

### Task 4 — BenchmarkRunner

- `run(qa_pairs, agent_fn, evaluator)`
- `generate_report(results)`
- `run_regression(new_results, baseline_results)`
- `identify_failures(results, threshold)`

`BenchmarkRunner.run()` phải truyền `pair.retrieved_contexts` vào
`run_full_eval()`. Report phải có average của hai retrieval metrics.

### Task 5 — FailureAnalyzer

- `categorize_failures(failures)`
- `find_root_cause(failure)`
- `generate_improvement_suggestions(failures)`
- `generate_improvement_log(failures, suggestions)`

Kiểm tra:

```bash
pytest tests/ -v
```

`rerank_by_overlap()` là TODO bonus của Exercise 3.5. Test tương ứng được skip
nếu bạn chưa làm bonus.

---

## Part 3 — Golden Dataset & Real Benchmark (10:40–11:35)

### Exercise 3.1 — Build the Golden Dataset

Thiết kế và validate dataset theo Mục 5–6 trong `guide_lab.md`. Nội dung 20 QA
được điền trực tiếp trong `golden_dataset.json`; phần dưới chỉ ghi lại kết quả
và quyết định thiết kế, không chép lại toàn bộ QA.

**Kết quả dataset**

| Hạng mục | Kết quả |
|---|---|
| Tổng số records | ____ / 20 |
| Easy | ____ / 5 |
| Medium | ____ / 7 |
| Hard | ____ / 5 |
| Adversarial | ____ / 3 |
| Source documents được sử dụng | ____ / 10 |
| Validator status | PASS / FAIL |

**Ba case đại diện cho quyết định thiết kế**

| ID | Difficulty | Source document(s) | Vì sao case phù hợp với difficulty/attack type? |
|---|---|---|---|
| | | | |
| | | | |
| | | | |

**Điểm khó nhất khi xây dựng expected answer hoặc evidence là gì?**

> *Câu trả lời:*

**Xác nhận:**

- [ ] Mọi claim trong expected answer đều có evidence hỗ trợ.
- [ ] Không có questions trùng ý và không dùng kiến thức ngoài corpus.
- [ ] `python validate_golden_dataset.py` báo `PASS`.

### Exercise 3.2 — Benchmark Run

Chạy:

```bash
python domain_assistant.py
python evaluate_answers.py
```

Copy bảng terminal vào đây hoặc điền từ `artifacts/benchmark_results.json`.

| ID | Question (short) | Ctx Recall | Ctx Precision | Faithfulness | Relevance | Completeness | Overall | Passed? | Failure Type |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| E01 | | | | | | | | | |
| E02 | | | | | | | | | |
| E03 | | | | | | | | | |
| E04 | | | | | | | | | |
| E05 | | | | | | | | | |
| M01 | | | | | | | | | |
| M02 | | | | | | | | | |
| M03 | | | | | | | | | |
| M04 | | | | | | | | | |
| M05 | | | | | | | | | |
| M06 | | | | | | | | | |
| M07 | | | | | | | | | |
| H01 | | | | | | | | | |
| H02 | | | | | | | | | |
| H03 | | | | | | | | | |
| H04 | | | | | | | | | |
| H05 | | | | | | | | | |
| A01 | | | | | | | | | |
| A02 | | | | | | | | | |
| A03 | | | | | | | | | |

**Aggregate Report**

- Overall pass rate: ____%
- Avg Context Recall: ____
- Avg Context Precision: ____
- Avg Faithfulness: ____
- Avg Relevance: ____
- Avg Completeness: ____
- Failure type distribution: ____

**Ba cases có Overall Score thấp nhất**

1. ID: ____ | Score: ____ | Failure type: ____
2. ID: ____ | Score: ____ | Failure type: ____
3. ID: ____ | Score: ____ | Failure type: ____

**Nhận xét ngắn:** Metric nào yếu nhất? Kết quả gợi ý vấn đề nằm ở retrieval
hay generation?

> *Câu trả lời:*

### Exercise 3.3 — LLM-as-a-Judge Rubric Design

Thiết kế rubric domain-specific cho Student Services. Mỗi mức phải đủ cụ thể để
hai người chấm độc lập có thể hiểu giống nhau.

Chọn 3–5 dimensions:

- [ ] Correctness
- [ ] Completeness
- [ ] Relevance
- [ ] Evidence/citation
- [ ] Actionability
- [ ] Safety/privacy
- [ ] Tone/clarity
- [ ] Dimension khác: __________

| Score | Tiêu chí domain-specific | Ví dụ response |
|---:|---|---|
| 5 | | |
| 4 | | |
| 3 | | |
| 2 | | |
| 1 | | |

**Ba edge cases khó chấm**

| Edge Case | Tại sao khó chấm? | Rubric xử lý thế nào? |
|---|---|---|
| | | |
| | | |
| | | |

**Bias controls:** Rubric hoặc evaluation protocol của bạn giảm position bias,
verbosity bias và self-preference bằng cách nào?

> *Câu trả lời:*

### Exercise 3.4 — Framework Comparison (Bonus +10)

Chỉ làm sau khi hoàn thành 3.1–3.3. Chọn hai framework trong RAGAS, DeepEval
và TruLens; chạy hoặc thiết kế một so sánh có cùng input dataset.

| Tiêu chí | Framework 1: ____ | Framework 2: ____ |
|---|---|---|
| Setup complexity | | |
| Metrics available | | |
| CI/CD integration | | |
| Kết quả trên cùng dataset | | |
| Insight rút ra | | |

- Scores có nhất quán không?
- Framework nào strict hơn và vì sao?
- Hai framework có tìm ra cùng failure cases không?

> *Phân tích:*

### Exercise 3.5 — Retrieval Reranking (Bonus +5)

Mục tiêu: kiểm tra việc đổi thứ tự chunks có tăng Context Precision mà không
thay đổi Context Recall hay không.

1. Chọn ít nhất 5 cases từ `artifacts/actual_answers.json`.
2. Tính Context Recall và Context Precision trước rerank.
3. Implement `rerank_by_overlap()` hoặc một reranker khác.
4. Rerank cùng tập chunks, không thêm hoặc xóa chunk.
5. Tính lại hai metrics và giải thích kết quả.

| ID | Recall before | Recall after | Precision before | Precision after | Delta Precision |
|---|---:|---:|---:|---:|---:|
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| **Avg** | | | | | |

**Tại sao Recall dự kiến không đổi?**

> *Câu trả lời:*

**Khi nào reranking không đủ và cần sửa retriever/query/chunking?**

> *Câu trả lời:*

---

## Part 4 — Reflection (11:35–11:50)

Hoàn thành `reflection.md` bằng kết quả thật từ Exercise 3.2.

---

## Completion Checklist

Hoàn thành kiểm tra cuối trong khoảng 11:50–12:00.

- [ ] Tất cả required tests pass.
- [ ] `golden_dataset.json` validate thành công.
- [ ] Exercise 3.1 hoàn thành trong file JSON và bảng kết quả phía trên.
- [ ] Exercise 3.2 có năm metrics, aggregate report và ba cases thấp nhất.
- [ ] Exercise 3.3 có rubric 1–5 và bias controls.
- [ ] `reflection.md` có ba failure analyses và regression strategy.
- [ ] Đã copy `template.py` thành `solution/solution.py`.
- [ ] Exercise 3.4 và 3.5 chỉ làm nếu chọn bonus.
