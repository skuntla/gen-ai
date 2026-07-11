# Phase 05 — Observability: See What's Happening

**Goal:** Instrument the agent so you can debug and optimize it with data, not guesses.

**Artifact:** `traces.ipynb` + instrumented `src/agent.py`

**Backend:** Langfuse Cloud (free Hobby tier) — chosen for corporate relevance and zero-infra setup.

---

## Contents

| File | What's in it |
|---|---|
| [concepts.md](concepts.md) | Observability vs traceability, traces/spans/generations, token economics, enterprise stacks |
| [design.md](design.md) | Instrumentation plan for `agent.py`, span hierarchy, metrics, notebook design, optimization targets |
| setup.md | Langfuse account, keys, SDK install *(pending)* |
| code-walkthrough.md | Line-by-line guide for instrumentation *(pending)* |
| teaching-guide.md | Workshop flow *(pending)* |
| questions.md | Interview prep *(pending)* |
| reflection.md | Post-implementation notes *(pending)* |

---

## Where we are in the arc

```
Phase 01  chat()           — talk to an LLM
Phase 02  query()          — RAG over your PDFs
Phase 03  eval suite       — measure query() quality (55% baseline)
Phase 04  agent.py         — route questions to the right tool (10/10)
Phase 05  traces           — see every LLM + tool call            ← you are here
Phase 06  guardrails       — block bad inputs/outputs
```

---

## Planned deliverables

| File | Purpose | Status |
|---|---|---|
| `src/agent.py` (instrumented) | Spans for LLM calls + tools; no behavior change | Pending |
| `traces.ipynb` | Aggregate metrics: p95 latency, tokens, $/request | Pending |
| `.env` Langfuse keys | Cloud Hobby account | Pending |

---

## Acceptance criteria (from REQUIREMENTS)

- [ ] Every agent request produces a visible trace with LLM + tool spans
- [ ] Can answer "why did it answer wrong?" by clicking through a trace in < 2 minutes
- [ ] Aggregate $/request and p95 latency are computed
- [ ] At least one optimization applied with before/after numbers (target: 30–50% cost or latency reduction)
