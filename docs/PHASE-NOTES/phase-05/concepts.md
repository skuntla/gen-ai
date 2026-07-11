# Core Concepts — Phase 05

## The problem Phase 04 leaves unsolved

Phase 04 gave us a working agent — 10/10 routing tests. But every insight about its behavior came from **watching `--verbose` output in a terminal**:

| Question we had | How we answered it in Phase 04 | Problem |
|---|---|---|
| "Which tool did it call?" | Re-run with `--verbose`, read stdout | Not reproducible after the fact |
| "Why was the margin wrong?" | Manually re-ask, guess the layer | No record of the original failing request |
| "How slow is a news question?" | Stopwatch feeling | No p95, no per-tool breakdown |
| "What does a request cost?" | Unknown | No token/cost aggregation across the loop |
| "Did Groq recovery fire?" | Only if you happened to be watching | No error-rate metric |

`--verbose` is **debugging**; Phase 05 builds **observability** — the same information, but persistent, structured, queryable, and aggregated.

---

## Observability vs traceability (interview-precise definitions)

| Term | Definition |
|---|---|
| **Observability** | The ability to understand a system's internal behavior from its outputs — without redeploying or adding print statements. Built from three pillars: **logs, metrics, traces**. |
| **Traceability / tracing** | One pillar of observability: following a **single request** end-to-end through every component it touched, in order, with timing. |

**Analogy:** Observability is the hospital's whole monitoring station. A trace is one patient's chart — every event on a timeline.

For LLM apps, "tracing" usually means **request-level traces of the agent loop**: every LLM call, every tool call, nested and timed.

---

## Traces, spans, generations

The vocabulary comes from distributed tracing (OpenTelemetry), adapted for LLM apps:

| Concept | Meaning | Phase 05 example |
|---|---|---|
| **Trace** | One end-to-end request | "What is YoY revenue growth FY2024→FY2025?" |
| **Span** | One timed unit of work inside a trace | `run_sql` execution (5ms) |
| **Generation** | A span that is specifically an **LLM call** — carries model, prompt, completion, tokens, cost | Groq call, iteration 1 (420ms, 1.2k tokens) |
| **Nesting** | Spans have parents — a tree, not a flat list | `search_docs` span contains an embedding span + a generation span |

A Phase 05 trace for the YoY question looks like:

```
Trace: "YoY revenue growth FY2024 to FY2025?"           total 1.7s, $0.0004
├── Generation: groq.chat (iteration 1)                  650ms, 1.4k in / 60 out
│     └── decided: run_sql
├── Span: tool.run_sql                                   5ms
│     └── output: 2 rows (153656, 165641)
├── Generation: groq.chat (iteration 2)                  520ms, 1.6k in / 45 out
│     └── decided: calculate
├── Span: tool.calculate                                 0ms
│     └── output: 7.7998
└── Generation: groq.chat (iteration 3)                  480ms, 1.7k in / 30 out
      └── final: "The YoY revenue growth is 7.80%."
```

This is the `--verbose` output you already know — made **permanent, clickable, and aggregatable**.

---

## The three pillars, mapped to this project

| Pillar | Generic meaning | Phase 05 concrete |
|---|---|---|
| **Traces** | Request timelines | Agent loop spans in Langfuse UI |
| **Metrics** | Aggregates over many requests | p95 latency, $/request, tools/request in `traces.ipynb` |
| **Logs** | Discrete events | Tool errors, `tool_use_failed` recoveries (attached to spans) |

Phase 05 deliberately does **not** build a separate logging stack — span metadata carries the events we care about.

---

## Why averages lie: p50 / p95 / p99

Agent latency is **multi-modal** — a calculate-only question takes ~1s; a news question with Tavily takes 10s+.

| Metric | Meaning |
|---|---|
| **p50** (median) | Half of requests are faster |
| **p95** | 95% are faster — the "bad day" a regular user hits weekly |
| **p99** | Worst 1% — timeout and support-ticket territory |

**Example:** 90 requests at 1.5s + 10 requests at 12s → average 2.5s (looks fine), p95 = 12s (users complain). SLAs and dashboards use percentiles, not means.

---

## Token economics: where the money goes

One agent request is **not one LLM call**. Cost drivers, largest first:

1. **Input tokens × iterations** — the entire message history is re-sent on *every* loop turn. A 3-iteration request pays for the system prompt and tool schemas three times.
2. **Tool result size** — a 100-row SQL result or 5 long web snippets inflate every subsequent turn.
3. **RAG context** — `search_docs` internally embeds the query and stuffs top-K chunks into another LLM call.
4. **Output tokens** — usually the smallest share for this agent.

This is why the classic optimizations work:

| Optimization | Attacks |
|---|---|
| Trim retrieval `top_k` (5 → 3) | RAG context tokens |
| Prompt caching (provider-side) | Repeated system prompt + tool schemas |
| Route simple questions to a smaller model | Cost per token |
| Truncate tool results | History growth across iterations |

Phase 05 requires **one** optimization with before/after numbers — measured, not assumed.

---

## What enterprises actually use

| Layer | Common choices |
|---|---|
| **LLM-native tracing** | **Langfuse**, LangSmith (LangChain shops), Arize Phoenix, W&B Weave, Braintrust |
| **Instrumentation standard** | **OpenTelemetry** — vendors ingest OTel spans |
| **Platform APM** | Datadog, New Relic, Grafana/Tempo — the org-wide dashboards |
| **Gateways with logging** | Helicone, Portkey, LiteLLM proxy |

Typical corporate stack: **OTel instrumentation → LLM-native backend (Langfuse/LangSmith) for prompt-level detail + platform APM for org-wide SLAs.**

### Why Langfuse for this project

- **SDK v3 is OpenTelemetry-based** — the skill transfers to any OTel backend
- **Free Hobby tier** (50k units/month, 30-day retention) — enough for learning
- **Framework-agnostic** — works with our raw Groq SDK; no LangChain required
- **Open source (MIT)** — can self-host later if data must stay local
- Widely adopted in production LLM teams — the tool you're most likely to meet at work

Phoenix (local, Docker) is the documented alternative if traces must never leave the machine.

---

## How instrumentation works (Langfuse SDK v3)

Two mechanisms, both used in Phase 05:

**1. `@observe` decorator** — wrap a function; inputs, outputs, timing, and errors are captured automatically:

```python
from langfuse import observe

@observe(name="agent-request")
def run_agent(user_message, ...):
    ...
```

**2. Context managers** — explicit spans/generations for code inside a function:

```python
langfuse = get_client()

with langfuse.start_as_current_observation(
    as_type="generation", name="groq.chat", model=model, input=messages,
) as gen:
    response = client.chat.completions.create(...)
    gen.update(output=..., usage_details={"input": ..., "output": ...})
```

Nesting is automatic via OpenTelemetry context propagation: a span opened inside another span becomes its child. That is how the trace tree builds itself.

**Key operational detail:** Langfuse batches and sends spans in the background. Short-lived scripts (like our CLI) must call `langfuse.flush()` before exit or traces are silently lost.

---

## Observability is not eval (and not guardrails)

| | Phase 03 Eval | Phase 05 Observability | Phase 06 Guardrails |
|---|---|---|---|
| **When** | Before deploy (offline) | During/after every request | During every request |
| **Question** | "Is quality ≥ baseline?" | "What happened, how fast, how much?" | "Should this request/answer be blocked?" |
| **Data** | Fixed test set | Real traffic | Real traffic |
| **Action** | Gate the release | Debug + optimize | Refuse / redact |

They compose: eval catches regressions pre-release, traces explain production failures, guardrails stop the harmful ones. Phase 09 closes the loop by turning trace patterns into CI trajectory tests.

---

## The debugging ladder, upgraded

Phase 04's "wrong margin" debug ladder required re-running with `--verbose`. With traces, the same ladder runs on the **original failing request**:

| Step | Phase 04 (terminal) | Phase 05 (trace) |
|---|---|---|
| Which tool fired? | Re-run `--verbose` | Click the trace — spans are right there |
| What SQL was written? | Hope it reproduces | Span input, recorded at the time |
| What did the tool return? | stdout scroll | Span output |
| Was it synthesis? | Compare by eye | Generation input (tool JSON) vs output (final text), side by side |

Acceptance criterion: this walk takes **< 2 minutes** in the Langfuse UI.

---

## What Phase 05 does and does not do

| Phase 05 does | Phase 05 does not |
|---|---|
| Trace every LLM + tool call | Change agent behavior or routing |
| Compute p95 latency, $/request | Build a full Datadog-style APM |
| One measured optimization | Optimize everything |
| Attach errors/recoveries to spans | Alerting / paging (production concern) |
| Use Langfuse Cloud free tier | Self-host infra (documented as option) |

---

## Mental model

```
Phase 04:  User → agent loop → answer          (a black box that works)
Phase 05:  User → agent loop → answer
                     │
                     └── every step emits a span → Langfuse
                                                       │
                                        traces.ipynb ──┴── p95, $/req, tool mix
```

Same agent. Now it leaves evidence.

---

## Key terms

| Term | Meaning |
|---|---|
| Trace | One request's full timeline |
| Span | Timed unit of work within a trace (tool call, function) |
| Generation | LLM-call span with model/tokens/cost attached |
| OpenTelemetry (OTel) | Vendor-neutral standard for emitting spans |
| p95 latency | 95% of requests finish faster than this |
| Flush | Force buffered spans to the backend before process exit |
| Prompt caching | Provider reuses repeated prompt prefix at discount |
| Unit (Langfuse billing) | Ingested observation — spans/generations count against the 50k/month free quota |
