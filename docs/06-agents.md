# 06 — Agents: Work Assistant & RCA

**Owner:** Phúc · **Tasks Excel:** S2-1, S2-2, S3-5

## 1. Mục tiêu
Hai agent hẹp, mỗi agent một việc, luôn có căn cứ (Constitution Điều 4):
- **Work Assistant** — thợ mới hỏi về bước thao tác tại trạm.
- **RCA Agent** — QC đưa lot hoặc triệu chứng lỗi, nhận giả thuyết nguyên nhân + nháp 5-Why.

## 2. LLM provider
Dùng lại pattern của spec 04: `LLMProvider` protocol (`generate_text`, `generate_json`, `is_cloud`), factory `get_llm_provider(settings)`, `FakeLLM` cho test. Khi provider `is_cloud`, retriever **loại bỏ** mọi passage `factory_confidential` khỏi context và ghi log số passage bị loại.

Vị trí: `core.providers.llm` (cạnh `core.providers.vlm` của spec 04; dùng chung cho agents và các lượt text của spec 04 — lượt C, propose-reasons): `base` (`LLMProvider.generate` là template method: DataGuard → che PII/LeakGuard/audit khi gọi cloud (spec 01 FR-09b) → gọi model → hoàn nguyên token), `registry` + `factory` (cùng tên provider với VLM: `qwen_api`, `local_openai`, `openrouter`, `siliconflow`, `openai_compatible`, `fake`; key trong `.env`), `catalog` (model mặc định: `qwen_api` → `qwen-plus`, `openrouter` → `qwen/qwen-plus`, `local_openai` → server Qwen3-VL-8B tự host; kiểm tra 28/9), `context` (`ContextPassage`, `filter_passages` loại passage confidential khi đích là cloud, `strictest` cho nhãn của prompt). Biến môi trường `KNOWHOW_LLM_*` (spec 01 §4).

## 3. Work Assistant — `agents.work_assistant`
```python
class AskRequest(BaseModel):
    question: str
    process_id: str | None = None


class AssistantAnswer(BaseModel):
    answer: str  # tiếng Việt, có marker [1], [2] ...
    citations: list[Citation]  # index i ứng với marker [i+1]
    confidence: float  # 0..1
    refused: bool
    suggested_contact: str | None  # display_name chuyên gia khi refused
```
Luồng:
1. `HybridRetriever.retrieve(question, process_id)`.
2. Nếu không có passage nào, hoặc điểm cao nhất < `KNOWHOW_ASSIST_MIN_SCORE` (mặc định 0.35) → `refused=True`, trả câu từ chối chuẩn, gợi ý `Expert` có nhiều `CONTRIBUTED` nhất vào process.
3. Gọi LLM với prompt `prompts/assistant.md` (chỉ dùng thông tin trong context, trích marker [n], nêu rõ `reason` nếu có, nêu `exceptions` nếu liên quan, tối đa 180 từ).
4. **Hậu kiểm**: mọi marker [n] phải trỏ tới citation tồn tại; câu trả lời không có marker nào → sinh lại 1 lần; vẫn không có → `refused=True`.
5. `confidence` = trung bình score của các citation được dùng.

## 4. RCA Agent — `agents.rca`
```python
class RcaRequest(BaseModel):
    lot_id: str | None = None
    symptom_text: str | None = None  # ít nhất một trong hai
    process_id: str | None = None


class Hypothesis(BaseModel):
    cause: str
    likelihood: Literal["high", "medium", "low"]
    evidence: list[Citation]
    check_actions: list[str]  # việc cần kiểm tra để xác nhận


class WhyStep(BaseModel):
    why: str
    answer: str
    verified: bool  # False = "cần xác minh tại hiện trường"


class RcaReport(BaseModel):
    lot_id: str | None
    symptom: str
    hypotheses: list[Hypothesis]  # tối đa 3, sắp theo likelihood
    five_why: list[WhyStep]  # 3..5 tầng
    related_lots: list[str]
    prevention_steps: list[str]  # profile_id
    disclaimer: str  # luôn có: đây là giả thuyết, cần xác minh
```
Luồng:
1. Có `lot_id` → `SigmaAdapter.get_lot(lot_id)` + `get_defects(lot_id)` (spec 07) → xác định symptom, process, ca, người vận hành.
2. Graph (spec 05 templates): `root_causes_of_symptom`, `where_symptom_occurred`, `prevention_steps` — **gọi trực tiếp theo tên template, không qua router LLM**. Tham số: có `lot_id` → dùng `defect_code` từ Sigma làm `symptom_id` (tất định); chỉ có `symptom_text` → map sang `symptom_id` bằng hàm khớp symptom của spec 05.
3. `HybridRetriever` với câu hỏi dựng từ symptom để lấy thêm bước/ngoại lệ liên quan.
4. LLM sinh `RcaReport` dạng JSON theo schema. Giả thuyết không có evidence → hạ `likelihood="low"`. WhyStep không truy được về citation → `verified=False`.
5. Lot không tồn tại → lỗi `LotNotFound` (API trả 404).

## 5. Functional Requirements
- **FR-01** `WorkAssistant.ask(AskRequest) -> AssistantAnswer` theo mục 3.
- **FR-02** `RcaAgent.investigate(RcaRequest) -> RcaReport` theo mục 4.
- **FR-03** CLI: `knowhow agent ask "..." --process PACK01`, `knowhow agent rca --lot L-2026-0915-03`.
- **FR-04** Mỗi lần gọi ghi trace JSON (request, context ids, prompt hash, response, latency) vào `data/work/traces/` để debug và làm dữ liệu cho spec 09.
- **FR-05** Prompt nằm trong file `.md` riêng, không hardcode trong code Python.

## 6. Acceptance Criteria
- **AC-01** Context rỗng → `refused=True`, `suggested_contact` khác None khi process có expert.
- **AC-02** FakeLLM trả câu có marker [3] nhưng chỉ có 2 citation → bị bắt ở hậu kiểm, sinh lại; lần 2 vẫn sai → `refused=True`.
- **AC-03** Câu hỏi về bước có `reason` trong graph → câu trả lời chứa nội dung reason và citation tới đúng `profile_id`.
- **AC-04** Provider cloud + context có passage `factory_confidential` → passage đó không xuất hiện trong prompt gửi đi (kiểm tra qua FakeLLM ghi lại prompt).
- **AC-05** RCA với lot mock có defect `D-03` → `hypotheses` không rỗng, mỗi hypothesis `high`/`medium` có ≥ 1 evidence, `disclaimer` không rỗng.
- **AC-06** RCA với `lot_id` không tồn tại → `LotNotFound`.
- **AC-07** `five_why` có 3..5 phần tử; phần tử không có căn cứ → `verified=False`.
- **AC-08** RCA với `lot_id` → router của spec 05 không được gọi (FakeLLM ghi lại prompt, không có prompt router); 3 template được gọi với `symptom_id` = `defect_code` của lot.

## 7. Interface với spec 05 / 07 / 08 (theo code trên `main`, 4/10)
- Model của agent (§3, §4) nằm ở `core.schemas.agents` (import thẳng module này; gốc `core.schemas` export các model API cùng tên của spec 08). `RetrievedContext`, `Template` lấy từ `knowledge_base.retrieval.hybrid` (spec 05); `LotRecord`, `DefectRecord`, `LotNotFound` từ `knowledge_base.sigma.adapter` (spec 07).
- `RetrievedContext.classifications[i]` là nhãn của `passages[i]` (trích bởi `citations[i]`); thiếu nhãn thì coi là `factory_confidential` (fail closed) — AC-04 lọc passage theo nhãn trước khi gọi LLM cloud.
- Agent chỉ phụ thuộc `agents.ports` (Protocol): `Retriever.retrieve(query, process_id, k)`; `GraphTemplates.run_template(template, **params)` + `match_symptom(text)` (row: `fact`, `source_type`, `ref_id`, `data_classification`); `ExpertDirectory.top_contributor(process_id)`; `SigmaSource.get_lot/get_defects`.
- Nối thật (`agents.factory`): Work Assistant dùng `get_hybrid_retriever(settings)` (có router); RCA dùng `HybridRetriever(vector store, Neo4jGraph, router=None)` cho cả retrieve lẫn template — không router (AC-08); Sigma `CsvSigmaAdapter(KNOWHOW_SIGMA_CSV_DIR)`. Chuyên gia gợi ý: `agents.experts.GraphExperts` (Cypher `Expert-CONTRIBUTED->Step<-HAS_STEP-Process`).
- REST (spec 08): router gọi `agents.supervisor.ask` / `agents.rca.investigate` với model API; `agents.api` dịch qua lại (`suggested_contact`→`suggested_expert`, `cause`→`hypothesis`, `evidence`→`evidence_refs`, `five_why`→`five_whys` có `order`, `prevention_steps`→`preventive_actions`). `KNOWHOW_API_AGENTS=mock` (mặc định) giữ câu trả lời demo của router; `live` chạy agent: lot không có → 404, thiếu thành phần/LLM → 503.
- Nhãn dữ liệu của RCA: Sigma `csv` (mock spec 07 §3) = `synthetic`; adapter khác = `factory_confidential` → DataGuard chặn LLM cloud. Fact từ graph mang nhãn theo row.
- Biến mới: `KNOWHOW_ASSIST_MIN_SCORE` (0.35), `KNOWHOW_TRACE_DIR` (`data/work/traces`, mỗi lần gọi 1 dòng JSON: request, context ids, hash prompt, response, latency), `KNOWHOW_API_AGENTS` (`mock`).

## 8. Tasks
- [x] T06-1 `LLMProvider` + `FakeLLM` + lọc confidential (AC-04).
- [x] T06-2 Work Assistant + prompt + hậu kiểm (AC-01..03).
- [x] T06-3 RCA Agent + prompt + gọi template tất định (AC-05..08).
- [x] T06-4 Trace logging + CLI. *(CLI chạy thật khi spec 05/07 có factory ở §8; trước đó báo rõ đang chờ module nào.)*

## Changelog
- v1.0 (23/9): khởi tạo.
- v1.1 (24/9): RCA gọi template Cypher trực tiếp theo tên, không qua router; `lot_id` → `symptom_id` tất định từ Sigma (AC-08).
- v1.2 (27/9): đường dẫn module theo layout mới (bỏ `knowhow.`/`src/knowhow/`, xem spec 01 v1.3).
- v1.3 (28/9, Phúc): T06-1 xong — `core.llm` (registry, OpenAI-compatible + fake, outbound guard, lọc passage confidential); model mặc định kiểm tra ngày 28/9.
- v1.4 (28/9, Phúc): LLM chuyển `core.llm` → `core.providers.llm` (§2), cùng chỗ với VLM `core.providers.vlm`.
- v1.5 (28/9, Phúc): T06-2 Work Assistant, T06-3 RCA Agent, T06-4 trace + CLI `knowhow agent ask|rca` xong; chốt interface với spec 05/07 ở §7 (model trong `core.schemas`, `RetrievedContext` 1-1 passage↔citation + nhãn passage, `route=False` cho RCA, tên factory).
- v1.6 (28/9, Phúc): `agents/` chia package: `work_assistant/`, `rca/` (`agent`, `report` hậu xử lý, `prompts/`), `cli/` (mỗi lệnh 1 module); `ports`, `trace`, `prompting`, `factory` dùng chung.
- v1.7 (4/10, Phúc): nối agent vào code spec 05/07/08 trên `main`: `HybridRetriever.run_template` + `match_symptom`, `RetrievedContext.classifications`, `CsvSigmaAdapter`; adapter REST `agents.api` (`KNOWHOW_API_AGENTS=mock|live`); §7 cập nhật.
