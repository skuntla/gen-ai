# Design — Phase 05 Observability

**Decision:** Langfuse Cloud (Hobby tier), Python SDK v3, manual instrumentation of `src/agent.py`. No agent behavior changes — if you diff the answers before/after instrumentation, they must be identical.

---

## 1. Backend choice

| Option | Verdict | Why |
|---|---|---|
| **Langfuse Cloud** | **Chosen** | Corporate adoption, free 50k units/month, OTel-based SDK, zero infra |
| Arize Phoenix (local) | Documented fallback | If traces must stay on-machine; requires local server |
| LangSmith | No | Tied to LangChain ecosystem we don't use |
| Raw OTel + Jaeger | No | No LLM-specific views (tokens, cost, prompts) |

Keys go in `.env` (already scaffolded in `.env.example`):

```
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

The SDK reads these env vars automatically — `get_client()` needs no arguments.

---

## 2. Span hierarchy (target trace shape)

One trace per `run_agent()` call:

```
TRACE  agent-request                      input: user question │ output: final answer
│      metadata: model, max_iterations
│
├── GENERATION  groq.chat (iter 1)        model, input=messages, usage, level=DEFAULT
│               metadata: {iteration: 1, recovered: false}
├── SPAN        tool.run_sql              input: {sql}, output: rows JSON
│               metadata: {rows: 2}
├── GENERATION  groq.chat (iter 2)        ...
├── SPAN        tool.calculate            input: {expression}, output: result JSON
└── GENERATION  groq.chat (iter 3)        final answer, no tool calls
```

`search_docs` gets one extra level because it wraps the Phase 02 pipeline:

```
├── SPAN  tool.search_docs
│   └── (rag.query() internals — left uninstrumented in v1; the span captures
│        total RAG time. Instrumenting rag.py is a stretch goal.)
```

### Naming conventions

| Observation | Name | `as_type` |
|---|---|---|
| Root | `agent-request` | span (via `@observe`) |
| Each LLM call | `groq.chat` | `generation` |
| Each tool | `tool.<name>` (e.g. `tool.run_sql`) | span |

Consistent names matter: the notebook aggregates by name (`tool.run_sql` p95, `groq.chat` token totals).

---

## 3. Instrumentation points in `agent.py`

Minimal touch — 4 places:

| Location | Change |
|---|---|
| module top | `from langfuse import get_client, observe` + `langfuse = get_client()` |
| `run_agent()` | Decorate with `@observe(name="agent-request")`; update trace input/output |
| `_request_chat_completion()` | Wrap the Groq call in `start_as_current_observation(as_type="generation")`; record model, messages, `response.usage` tokens |
| `execute_tool()` | Wrap dispatch in `start_as_current_observation(as_type="span", name=f"tool.{name}")`; record args in / JSON out |
| `main()` / `_interactive()` | `langfuse.flush()` before exit (CLI is short-lived; unflushed spans are lost) |

### Error and recovery capture

Two failure modes from Phase 04 become first-class trace data:

1. **`tool_use_failed` recovery** — when `_recover_tool_calls_from_groq_error()` salvages a malformed tool call, mark the generation with `level="WARNING"` and `metadata={"recovered": true}`. The notebook then computes a **recovery rate** — invisible in Phase 04 unless you were watching the terminal.
2. **Tool errors** — `execute_tool` already returns `{"error": ...}` JSON instead of raising. Set `level="ERROR"` on the span when the output contains an error key, so failed tool calls are filterable in the UI.

### Graceful degradation rule

Missing Langfuse keys must **not** break the agent. The SDK already no-ops with a warning when keys are absent; verify this and document it in setup.md. Observability is an add-on, never a dependency.

---

## 4. Cost tracking

Groq returns `usage.prompt_tokens` / `usage.completion_tokens` on every response. We pass these as `usage_details` on each generation; Langfuse computes cost from its model-price table. If `llama-3.3-70b-versatile` isn't priced automatically, we add a model definition in the Langfuse UI (in: $0.59/M, out: $0.79/M — Groq list prices) or pass `cost_details` explicitly.

$/request in the notebook = sum of generation costs per trace.

---

## 5. `traces.ipynb` design

Data source: Langfuse public API via the SDK (`langfuse.api.trace.list(...)`), pulled into pandas.

| Section | Computes | Answers |
|---|---|---|
| 1. Load traces | Fetch last N traces + observations | — |
| 2. Latency | p50 / p95 / p99 total; p95 per span name | "How slow, and which step?" |
| 3. Tokens & cost | Tokens per trace, $/request, cost by iteration count | "Where does the money go?" |
| 4. Tool mix | Calls per tool, tools per trace, iterations histogram | "What does traffic look like?" |
| 5. Errors | Tool error rate, Groq recovery rate | "How often does it wobble?" |
| 6. Before/after | Re-run section 2–3 on post-optimization traces, compare | "Did the optimization pay?" |

To have data to aggregate, we replay the **10 Phase 04 routing questions** (plus repeats) through the instrumented agent — a small `scripts/replay_questions.py` or a shell loop.

---

## 6. Optimization experiment (pick one, measure it)

Candidates, in order of expected impact for this agent:

| Candidate | Mechanism | Expected effect |
|---|---|---|
| **A. Truncate tool results** (cap web snippets / SQL rows fed back into history) | Smaller history → fewer input tokens on every later iteration | 20–40% input-token cut on multi-tool requests |
| B. Trim RAG `top_k` 5→3 in `search_docs` | Smaller synthesis prompt inside RAG | Cost cut on doc questions; must not tank answer quality |
| C. Smaller model for routing-only iterations | `llama-3.1-8b-instant` decides tools, 70B synthesizes | Cheaper + faster, but riskier routing |

**Plan:** run baseline (10 questions × 3 repeats) → apply A → re-run same set → compare $/request and p95 in notebook section 6. Target from REQUIREMENTS: 30–50% reduction in cost or latency. If A alone is not enough, add B.

Quality check: the 10 routing tests must still pass 10/10 after optimization — observability work must not regress Phase 04.

---

## 7. Dependencies

```
langfuse>=3.0.0        # SDK v3 (OTel-based)
pandas                  # already present (notebook aggregation)
```

No OpenInference auto-instrumentation library — we instrument manually. Reason: manual spans teach the mechanics (the point of this phase) and give exact control over names/metadata; auto-instrumentation is noted in concepts.md as the shortcut for production.

---

## 8. Implementation order

1. **Setup** — Langfuse Cloud account, project keys into `.env`, `pip install langfuse`, `auth_check()` smoke test
2. **Instrument generations** — `_request_chat_completion` wrapped; one question → see a trace with LLM spans in the UI
3. **Instrument tools + root** — `execute_tool` spans, `@observe` on `run_agent`, flush on exit; full tree visible
4. **Error/recovery metadata** — WARNING on recoveries, ERROR on tool failures
5. **Replay + notebook** — replay routing questions, build `traces.ipynb` sections 1–5
6. **Optimization** — baseline numbers → apply candidate A → after numbers → notebook section 6
7. **Docs** — setup.md, code-walkthrough.md, reflection.md, questions.md

---

## 9. Acceptance criteria

- [ ] Every `run_agent()` call produces one Langfuse trace: root span + one generation per LLM call + one span per tool call, correctly nested
- [ ] Generations carry model + token usage; cost per trace visible in Langfuse
- [ ] Groq `tool_use_failed` recoveries appear as WARNING with `recovered: true`
- [ ] Agent behavior unchanged: 10/10 routing tests still pass; agent runs fine with no Langfuse keys
- [ ] `traces.ipynb` reports p50/p95/p99 latency, $/request, tool mix, error/recovery rates
- [ ] One optimization applied with before/after evidence; 30–50% cost or latency reduction OR a documented finding of why not

---

## 10. Test plan (manual, like Phase 04 routing tests)

| # | Check | How |
|---|---|---|
| 1 | Trace appears | Ask one question, open Langfuse UI, find trace |
| 2 | Nesting correct | YoY question → 3 generations + 2 tool spans under one trace |
| 3 | Tokens recorded | Generation shows input/output token counts |
| 4 | Tool error visible | Ask a question that triggers invalid SQL → ERROR span |
| 5 | Recovery visible | Reproduce/force a `tool_use_failed` → WARNING generation |
| 6 | No-key degradation | Unset Langfuse keys → agent still answers |
| 7 | Flush works | CLI one-shot question → trace still arrives (not lost at exit) |
