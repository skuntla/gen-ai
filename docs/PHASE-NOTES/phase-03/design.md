# Design — Phase 03

## What we built

An offline eval harness around `rag.query()` using Promptfoo.

```bash
./evals/run_eval.sh
promptfoo view
```

---

## Architecture

```
evals/test_cases.yaml          20 questions + assertions
        │
        ▼
evals/promptfooconfig.yaml     3 provider configs × 1 prompt template
        │
        ▼
evals/rag_provider.py          call_api() → rag.query()
        │
        ├── OpenAI embeddings (query time)
        └── Groq generation via llm_chat.chat()
        │
        ▼
Promptfoo                      pass/fail grid, latency, token counts
```

The eval tests **end-to-end Layer 3** behaviour (see [concepts.md](concepts.md)). It does not separately score retrieval vs generation yet.

---

## Provider wrapper

`rag_provider.py` implements Promptfoo's `call_api(prompt, options, context)`:

- Reads `question` from `context["vars"]`
- Passes `top_k` and optional `model` from provider config
- Returns `output` (answer + source summary), `tokenUsage`, `cost`, `latencyMs`

---

## Test suite (20 cases)

| Category | Count |
|---|---|
| factual_easy | 5 |
| factual_precise | 5 |
| multi_chunk | 2 |
| out_of_scope | 3 |
| adversarial | 4 |
| citation duplicate | 1 (CEO + citation check) |

Tests marked `metadata.expected_result: fail` document known Phase 02 limits (chart extraction, margin retrieval). They still run — passing later indicates improvement.

---

## Baseline — first run (2026-06-06)

Corpus: `infosys-ar-26.pdf` | Index: 2,697 chunks | Duration: ~3m 46s

| Metric | Value |
|---|---|
| Total runs | 60 (20 tests × 3 providers) |
| Passed | 33 (55%) |
| Failed | 27 (45%) |
| Errors | 0 |

All three providers scored identically on pass/fail for this baseline — differences were latency and token usage, not assertion outcomes.

### Expected failure clusters

| Test area | Why it fails |
|---|---|
| Retail segment % | Chart text extraction — COM values returned instead of Retail |
| Operating margin | Value not in top-k retrieved chunks |
| Some adversarial | Model answers from training data instead of refusing |
| Capital of India / Cricket WC | Occasional grounding breach |

### Expected pass clusters

| Test area | Why it passes |
|---|---|
| CEO, Chairman, company name | Clear prose in retrieved chunks |
| FY2026 revenue | Prominent in business highlights |
| Employee count (consolidated) | In Board's report text |
| TCS out of scope | Honest refusal |
| Multi-chunk CEO + revenue | Both facts retrievable separately |

---

## Default configuration — written justification

**Winner: `rag-top5-70b`** (default RAG config for this project)

### Selection criteria

Promptfoo guidance: pick by **pass rate × cost × latency**. All three providers were evaluated on the same 20 tests.

| Provider | Pass/fail (baseline) | top_k | LLM | Notes |
|---|---|---|---|---|
| `rag-top5-70b` | 11/20 pass (identical) | 5 | `LLM_MODEL` from `.env` (70b) | **Selected default** |
| `rag-top10-70b` | 11/20 pass (identical) | 10 | same 70b model | More input tokens per query, no assertion gain |
| `rag-top5-8b` | 11/20 pass (identical) | 5 | `llama-3.1-8b-instant` | Valid cost-optimized alternative; kept as comparison column |

### Why not `rag-top10-70b`?

Baseline failures (Retail chart, operating margin, some adversarial) are **corpus and extraction limits** — wrong or missing values in chunk text — not "retrieved too few chunks." Doubling `top_k` sends more context to the LLM (higher token cost, higher latency) without changing pass/fail on this suite.

### Why `rag-top5-70b` over `rag-top5-8b`?

Pass/fail tied on the baseline suite. **`rag-top5-8b` is the cost/latency winner** when quality is equal — use it for high-volume runs or when Groq 70b rate-limits. **`rag-top5-70b` remains the documented default** because it matches `.env` `LLM_MODEL`, preserves headroom on harder generation (multi-chunk synthesis, citation formatting), and avoids maintaining a separate "eval model" vs "production model" split at this stage.

### Practical rule

- **Default dev / teaching:** `top_k=5`, 70b from `.env`
- **Cost-sensitive or rate-limited:** switch provider label to `rag-top5-8b` or set `model: llama-3.1-8b-instant` in config
- **Never assume top_k=10 is better** without a pass-rate delta on the golden set

---

## Regression protocol

1. Record baseline pass rate after any index rebuild (currently **33/60 = 55%** on the first clean run, 2026-06-06).
2. Re-run `./evals/run_eval.sh` after prompt, model, chunking, or embedding changes.
3. Treat a drop **below ~90% of baseline** (~30/60) as a regression worth investigating.
4. Tests marked `metadata.expected_result: fail` document known Phase 02 limits — when they flip to PASS, that is improvement without lowering `assertThreshold`.

Note: later re-runs may differ slightly (API non-determinism, Groq rate limits). Use the first error-free run as the canonical baseline; investigate errors before comparing pass rates.

---

## Acceptance criteria

- [x] At least 10 test cases (20 implemented)
- [x] At least 3 provider configurations compared
- [x] Web UI available via `promptfoo view`
- [x] Baseline documented above
- [x] Written justification for winning config (`rag-top5-70b` — see above)

---

## Next improvements (post-Phase 03)

- Layer 1 assertions: check `sources[].page` in javascript asserts
- `llm-rubric` for grounding quality
- Separate expected-fail tests in report filtering
- Re-run after chunking or extraction improvements to measure delta
