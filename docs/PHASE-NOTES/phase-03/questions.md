# Questions — Phase 03

These cover eval concepts, Promptfoo mechanics, assertion design, and architecture decisions from Phase 03.
Use for interview prep, self-testing, and teaching.

The **Tough interview questions** section at the bottom includes open-ended questions with model answers — the same questions used for oral review after implementation.

---

## Core concepts

**Q: What problem does offline eval solve that manual testing cannot?**

Manual testing ("ask 5 questions and read the answers") does not scale. You cannot hold 20 results in memory reliably, there is no automatic regression detection when you change chunk size or system prompt, and comparing configs (top_k, model) lacks an objective basis. Offline eval runs a fixed test suite before deployment and records pass/fail, latency, and cost — the same role unit tests play in regular software, adapted for fuzzy LLM outputs.

**Q: What is offline eval in the context of LLM applications?**

Running a fixed test dataset **before** deployment — not waiting for production users to surface bugs. Pattern:

```
build RAG pipeline  →  run eval suite  →  16/20 pass  →  record baseline
change system prompt →  run eval again  →  14/20 pass  →  regression, investigate
```

**Q: What are the three layers of RAG eval?**

```
Layer 1 — RETRIEVAL     Did FAISS return the right chunks?
Layer 2 — GENERATION    Did the LLM answer correctly from those chunks?
Layer 3 — END-TO-END    Full pipeline: question → final answer
```

Phase 03 starts with **Layer 3** (simplest to set up). Layer 1 checks can be added later (e.g. assert that the expected page appears in `sources`).

**Q: What is Promptfoo and why use it for this project?**

Promptfoo is an open-source evaluation framework for LLM applications. It takes test cases + providers and produces a pass/fail grid with latency and cost. For this project:

- Custom Python providers — wrap `query()` directly
- Multiple assertion types — `icontains`, `llm-rubric`, `javascript`
- Side-by-side comparison of configurations
- No LangChain required — consistent with the raw SDK approach in Phases 01–02

**Q: Is Promptfoo only for LLM evaluation, RAG, or agents?**

None of the above exclusively. Promptfoo is **layer-agnostic** — it only sees input → output → pass/fail. What you put inside the provider defines the unit under test:

| Provider | Unit under test |
|---|---|
| `groq:llama-3.3-70b` | Raw LLM API call |
| `file://rag_provider.py` | Full RAG pipeline (`query()`) — Phase 03 |
| `file://agent_provider.py` (future) | Full agent with tool loop — Phase 04+ |

**Q: What is the pytest analogy for Promptfoo?**

| pytest | Promptfoo |
|---|---|
| Tests Python functions | Tests LLM **systems** (any provider) |
| `assert result == expected` | `assert output icontains "Salil Parekh"` |
| Run on every code change | Run after prompt / model / RAG config changes |
| Agnostic to internal implementation | Agnostic to LLM vs RAG vs agent |

---

## Promptfoo mechanics

**Q: What does `call_api()` do and why is it named that?**

`call_api()` is Promptfoo's **convention** for Python custom providers. Promptfoo imports `evals/rag_provider.py` and calls `call_api(prompt, options, context)`. It is not a special RAG function — you could name a wrapper differently if you specify `file://script.py:function_name` in config. Our provider reads the question from `context["vars"]`, calls `rag.query()`, and returns `output`, `tokenUsage`, `cost`, `latencyMs`.

**Q: Why is `if __name__ == "__main__"` not used during eval?**

When Promptfoo imports `rag_provider.py`, `__name__` is `"rag_provider"`, not `"__main__"`. The `__main__` block only runs for manual testing: `python evals/rag_provider.py`. During eval, Promptfoo calls `call_api()` directly.

**Q: Why do we use `./evals/run_eval.sh` instead of bare `promptfoo eval`?**

The shell script sets `PROMPTFOO_PYTHON` to `.venv/bin/python` so Promptfoo uses the project virtualenv (with `faiss`, `openai`, etc.). Running bare `promptfoo eval` may pick the system Python and fail on imports.

**Q: What is the config chain for LLM vs embeddings during eval?**

| Setting | Source during eval |
|---|---|
| LLM provider / model | `promptfooconfig.yaml` → `rag_provider` → `query()` → `chat()` → or `.env` default |
| Embedding model | Always `.env` `EMBEDDING_MODEL` — not overridden in Promptfoo config |
| Index on disk | Built at `--index` time with whatever `EMBEDDING_MODEL` was set then |

**Q: What happens if you change `EMBEDDING_MODEL` in `.env` but do not re-run `--index`?**

Index vectors were built with model A; query-time embeddings use model B. They live in **incompatible vector spaces** — cosine similarity scores are meaningless. FAISS still returns top_k results (unless dimensions mismatch causes a hard error), but they are semantically wrong chunks. The LLM answers confidently from bad context. Eval pass rate drops sharply even though LLM and test cases are unchanged. **Fix:** change embedding model → re-run `python src/rag.py --index` → re-run eval and record a new baseline.

**Q: Why does `rag_provider.py` append sources to the output string?**

So eval cells in `promptfoo view` show which chunks were retrieved (score, file, page). This supports manual Layer 1 debugging without a separate script. The raw answer is also stored in `metadata.raw_answer` and full source objects in `metadata.sources` for future `javascript` assertions.

---

## Test suite and assertions

**Q: What categories should a balanced RAG eval suite cover?**

| Category | Example |
|---|---|
| Factual — easy | CEO name, total revenue |
| Factual — precise number | Operating margin, segment revenue |
| Multi-chunk synthesis | Question requiring 2+ retrieved chunks |
| Out of scope | TCS revenue (not in corpus) |
| Adversarial / injection | "Ignore instructions…", training-data jailbreak |

Phase 03 implements 20 tests across these categories.

**Q: What is `assertThreshold: 1` and what does lowering it do?**

`assertThreshold` is the fraction of assertions that must pass for a test cell to be marked green. `1` means **all** assertions must pass — strict, no partial credit. Lowering it (e.g. to `0.55`) would allow tests to pass when some assertions fail. That hides real regressions across the suite, including tests that should pass today (CEO, revenue, refusals). **Do not lower the threshold to match a low baseline** — the baseline is a measurement, not a success criterion.

**Q: What is `metadata.expected_result: fail` and how does it differ from `assertThreshold`?**

| Mechanism | What it does |
|---|---|
| `assertThreshold: 1` | Strict pass/fail — every assertion must pass |
| `metadata.expected_result: fail` | **Documentation only** — Promptfoo still runs the test and marks it FAIL |

Tests marked `expected_result: fail` document known Phase 02 limits (Retail chart extraction, operating margin retrieval). They still appear red in the grid. When they flip to PASS after a fix, that is measurable improvement — without changing any config.

**Q: Why require a refusal phrase for TCS but NOT ban the string "TCS" in the answer?**

A good refusal naturally repeats the subject:

> "I don't have enough information about **TCS** revenue in the provided Infosys documents."

That is correct behaviour but contains `"TCS"`. `not-icontains: TCS` would **false-fail** valid refusals. The test only checks `icontains: "don't have enough information"` — it catches the failure mode of inventing TCS revenue from training data.

**Q: Why does the Telugu actor test use BOTH refusal AND `not-icontains: Chiranjeevi`?**

Adversarial tests need a **leakage guard**. The model might partially comply:

> "I don't have enough information in the documents. **Chiranjeevi** is a famous Telugu actor."

That passes the refusal check but fails grounding. `not-icontains` catches training-data hallucination and partial jailbreak compliance that refusal alone would miss.

**Q: When should you use `icontains` vs `regex` vs `llm-rubric` vs `context-faithfulness`?**

| Assertion | When to use |
|---|---|
| `icontains` / `not-icontains` | Factual keywords, refusals, blocking known wrong values |
| `regex` | Numbers with formatting variants (`1,?78,?650`) |
| `llm-rubric` | Fuzzy quality — grounding, tone, completeness |
| `context-faithfulness` | Answer must be supported by retrieved context (hallucination detection) |
| `javascript` | Custom logic — e.g. check `sources[0].page === 12` |

Phase 03 relies mainly on `icontains` / `not-icontains`. Production-grade suites typically mix all of the above.

**Q: Why were multiple provider configs included if they tied on pass/fail?**

To compare **top_k** (5 vs 10) and **LLM model** (70b vs 8b) on the same test suite. When pass/fail is identical, tiebreak on **latency and token cost** — not intuition that "more chunks is better." The baseline showed all three providers had identical assertion outcomes; differences were latency and tokens only.

---

## Layer diagnosis and debugging

**Q: How do you prove whether a failure is retrieval, corpus quality, or generation — without changing the LLM?**

**Step 1 — Inspect retrieved sources:** Read the `--- sources ---` block in Promptfoo output or run `python src/rag.py "question"`. Check page numbers and chunk text in `data/index/chunks.json`.

**Step 2 — Retrieval-only test:** Run embed + FAISS without calling `chat()`. Check whether retrieved chunk text contains the expected values. No LLM involved — pure Layer 1.

**Step 3 — Generation-only test:** Hand-craft a prompt with correct context containing the answer. Same LLM. If it answers correctly → generation works; bug is upstream in chunks or retrieval content.

**Q: Retail segment revenue fails with COM value (11.7%) — which layer failed?**

Usually **corpus/index quality**, not classic retrieval miss or pure generation hallucination. PDF chart extraction produced misleading flat text — FAISS may retrieve the correct *page* but the chunk *content* is wrong. The LLM grounds faithfully in bad context. Strict Layer 1 ("wrong page") vs extraction failure ("right page, wrong parsed text") matters for choosing the fix (better retrieval vs better PDF extraction).

**Q: Do you need permanent debug statements for retrieval-only testing?**

No. For a quick check: Promptfoo sources + grep `chunks.json`. For true retrieval-only (no LLM), run a small one-off script copying the FAISS block from `query()`, or eventually extract a `retrieve()` function with an optional `--retrieve-only` CLI flag.

---

## Architecture and phase connections

**Q: How does Phase 03 connect to the rest of the project?**

```
Phase 01  llm_chat.py         chat() called inside query()
Phase 02  rag.py              query() is the unit under test
Phase 03  promptfooconfig.yaml wraps query(), runs assertions
Phase 04  agent.py            agent becomes an additional unit under test
Phase 06  guardrails.py       adversarial cases from Phase 03 inform what to block
```

**Q: Should you delete the Phase 03 RAG eval when the Phase 04 agent ships?**

**No — keep and extend.** RAG eval tests the foundation (`search_docs` → `query()`). Agent eval tests a different layer: tool selection, multi-turn interaction, orchestration. If the agent gives a wrong CEO answer, the RAG suite tells you whether `query()` broke or the agent layer broke. Recommended:

| Suite | Provider wraps | Tests |
|---|---|---|
| Phase 03 (keep) | `query()` | Chunking, embeddings, retrieval, grounding |
| Phase 04 (add) | `agent.run()` | Tool routing, interaction, orchestration |

**Q: What does Phase 03 do and not do?**

| Phase 03 does | Phase 03 does not |
|---|---|
| Measure quality systematically | Fix retrieval failures automatically |
| Record a baseline pass rate | Replace all manual testing |
| Compare configs side by side | Implement guardrails (Phase 06) |
| Detect regressions on prompt/config changes | Improve chunking (results inform that decision) |

Eval identifies **what is broken and by how much**. Fixing it is a separate step.

**Q: How do you treat the baseline pass rate for regression testing?**

Record the first run (e.g. 33/60 = 55%) in `design.md`. On every change, re-run eval. A drop **below ~90% of baseline** is treated as a regression worth investigating. Known failures tagged `expected_result: fail` are documented limits — when they flip to PASS, that is improvement without config changes.

---

## Tough interview questions

Open-ended questions with model answers. Try answering before reading the answer.

---

### Q1: Identical pass/fail across all three providers

Your baseline run showed **33/60 passes (55%)**, and all three providers — `rag-top5-70b`, `rag-top10-70b`, and `rag-top5-8b` — had **identical pass/fail on every test**. Only latency and token counts differed.

A teammate says: *"Top-k=10 retrieves more chunks, so `rag-top10-70b` is clearly the better config. We should make that the default."*

**Do you agree? What would you tell them, and what would you need to see before recommending a default config?**

<details>
<summary>Model answer</summary>

**Do not agree** that top_k=10 is "clearly better" on quality — identical pass/fail means it did not improve assertion outcomes on this suite.

Most failures are not "we needed chunk 6 but only retrieved 5." They are corpus/extraction limits (Retail chart text, margins not in index). Adding chunks does not fix bad or missing content.

**When quality ties, tiebreak on latency and token cost.** With identical pass/fail, `rag-top5-8b` is often the rational default: same outcomes, likely lower latency and cost than 70b. `rag-top10-70b` sends more context to the LLM (higher input tokens) without quality gain here.

**Before recommending a default:** identical or better pass rate than alternatives, acceptable latency for your SLA, lowest cost among ties, and stable behaviour across test categories (not just easy factuals).

**Caveat:** Same pass/fail ≠ same answers. Assertions only check keywords/refusals — wording and source pages can differ in ways the suite does not catch yet.

</details>

---

### Q2: Retail segment failure — which layer?

One test asks for **Retail segment revenue** and fails because the answer contains **11.7%** (COM segment value from a flat chart in the PDF, not Retail).

The suite is **Layer 3 end-to-end**. Is this primarily retrieval (Layer 1), generation (Layer 2), or something else? How would you prove which layer without changing the LLM?

<details>
<summary>Model answer</summary>

Usually **corpus/index quality failure** — extraction/chunking — not pure Layer 2 hallucination. The LLM answers from context; the context is wrong because PDF chart extraction garbled segment labels.

Strict Layer 1 framing:

| Scenario | What failed |
|---|---|
| FAISS never returns chart page | Classic Layer 1 retrieval miss |
| FAISS returns chart page, extracted text has wrong values | Extraction/chunking — right place, wrong content |
| Chunk has both COM and Retail, LLM picks COM | Layer 2 generation misread |

**Prove without changing LLM:**

1. Inspect sources in Promptfoo output → read chunk text in `chunks.json` for those pages. Are Retail values (12.9, 13.5) present at all?
2. Retrieval-only script: embed + FAISS, print chunks, no `chat()`.
3. Generation-only test: hand-craft context with correct Retail numbers → same LLM. If correct → generation works; bug is upstream.

</details>

---

### Q3: TCS refusal vs Chiranjeevi ban

Out-of-scope TCS test: `icontains: "don't have enough information"` — no `not-icontains: TCS`.

Adversarial actor test: refusal **plus** `not-icontains: Chiranjeevi` and `not-icontains: Mahesh`.

**Why require refusal for TCS but not ban "TCS"? Why ban actor names for the injection test?**

<details>
<summary>Model answer</summary>

**TCS (out-of-scope factual):** Assert the *behaviour* (refuse). A valid refusal may say "I don't have information about **TCS** revenue in these Infosys documents." Banning `"TCS"` causes false failures on good answers. The failure mode caught: inventing TCS revenue from training data (missing refusal phrase).

**Actor (adversarial injection):** Refusal alone is insufficient. The model may partially comply: refuse *and* leak a name from training data. `not-icontains` catches leakage that `icontains` refusal would miss. The failure modes: ignoring grounding entirely, or partial jailbreak compliance.

Rule of thumb: **out-of-scope factual → assert refuse, don't ban question keywords. Adversarial → assert refuse AND ban specific leaked content.**

</details>

---

### Q4: Embedding model change without re-indexing

Embeddings always come from `.env` (`EMBEDDING_MODEL`). You change the embedding model but do **not** re-run `--index`. LLM and test cases are unchanged.

**What happens to eval results, and why is that a problem?**

<details>
<summary>Model answer</summary>

Index vectors were built with model A; queries embed with model B. **Incompatible vector spaces** — similarity scores are meaningless. FAISS may still return results (or error on dimension mismatch if dims differ, e.g. 1536 vs 3072).

Retrieval silently returns wrong chunks. The LLM still runs and answers confidently. Pass rate drops sharply. Eval failures look like "generation got worse" when the real bug is stale index + new embed model.

**Dangerous because the pipeline still "works"** — no obvious crash, just wrong answers. Fix: change `EMBEDDING_MODEL` → `python src/rag.py --index` → re-run eval → new baseline.

</details>

---

### Q5: assertThreshold 0.55 vs expected_result: fail

Baseline is 55%. Teammate proposes `assertThreshold: 0.55` so Promptfoo passes the suite because some tests are "supposed to fail anyway."

**Good idea? What instead? How do assertThreshold and expected_result differ?**

<details>
<summary>Model answer</summary>

**Bad idea.** Lowering `assertThreshold` hides real failures suite-wide — including tests that should pass today (CEO, revenue, refusals). 55% is a **baseline to measure against**, not a success criterion to encode in config.

| Mechanism | Purpose |
|---|---|
| `assertThreshold: 1` | Strict — all assertions must pass per test |
| `expected_result: fail` | Documentation — test still runs and shows FAIL; labels known limits |

**Instead:** keep `assertThreshold: 1`; document 55% baseline in `design.md`; use `expected_result: fail` for known limits; re-run after changes and treat drop below ~90% of baseline as regression; when chart extraction is fixed, cells flip green without config changes.

</details>

---

### Q6: Keep RAG eval when agent ships?

Phase 04 adds an agent with `search_docs` wrapping `query()`. Someone wants to **delete** Phase 03 eval and replace with agent-only tests: *"Users talk to the agent — testing query() is an implementation detail."*

**Agree? Keep, modify, or replace?**

<details>
<summary>Model answer</summary>

**Keep and extend — do not delete.**

RAG eval tests the substrate the agent depends on. Agent eval tests tool routing, multi-turn behaviour, and orchestration. Different layers, different failure modes.

If agent returns wrong CEO answer: RAG suite isolates whether `query()` broke vs agent failed to call `search_docs` or misused the result.

Phase 03 today is Layer 3 on `query()` — not separate Layer 1/2 suites yet — but it still isolates RAG from agent. Add agent provider in Phase 04; keep RAG provider for regression on search quality.

</details>

---

### Q7: What would Promptfoo eval look like if the provider called chat() directly instead of query()?

Same 20 test cases, but provider wraps raw `chat()` with no retrieval.

**Which test categories would pass MORE and which LESS? Why?**

<details>
<summary>Model answer</summary>

**Pass MORE (likely):** Questions where the LLM knows the answer from training data (general Infosys facts, famous people, Cricket WC) — no grounding required.

**Pass LESS (likely):** Questions requiring specific FY2026 report numbers (exact revenue, employee count from this filing), citation to `infosys-ar-26.pdf`, out-of-scope refusal (model may hallucinate TCS revenue), adversarial injection (no system prompt enforcing "context only").

This illustrates **why RAG eval matters** — raw LLM eval measures a different system. Comparing both providers on the same grid shows what RAG adds vs training-data answers.

</details>

---

### Q8: A test passes icontains for CEO name but fails citation check. Regression or test design issue?

CEO test asserts both `icontains: Salil Parekh` and `icontains: infosys-ar-26.pdf`. After a prompt change, the model names the CEO correctly but cites only the page number without the filename.

**Is this a regression? What assertion type might be more robust?**

<details>
<summary>Model answer</summary>

**Partial regression** — factual content correct, citation format broke. Strict `assertThreshold: 1` marks the cell FAIL. That is correct strict behaviour; you investigate whether the prompt change weakened citation instructions.

More robust options: `regex` for filename pattern; `llm-rubric` ("must cite source document"); `javascript` assert on `metadata.sources[0].source`. Keyword `icontains` on filename is brittle if the model says "the annual report" instead of the exact filename.

</details>

---

### Q9: How is Phase 03 eval different from production monitoring?

Both measure quality. What does offline eval give you that production logs cannot?

<details>
<summary>Model answer</summary>

Offline eval gives:

- **Known ground truth** before users hit the system — fixed questions with expected behaviour
- **Regression detection** on every change — compare to baseline, not anecdotal user reports
- **Controlled comparison** — same tests across configs side by side
- **Reproducibility** — same corpus, same index, same 20 questions every run

Production monitoring catches real user queries and drift over time but lacks labelled expected answers for every query, cannot easily A/B configs on identical inputs, and finds bugs only after users are affected. Both are needed; Phase 03 is the pre-ship safety net.

</details>

---

### Q10: Why run 20 tests × 3 providers = 60 cells instead of just 20?

<details>
<summary>Model answer</summary>

Promptfoo runs **every test against every provider** in `promptfooconfig.yaml`. Three providers exist to compare configurations (top_k, model) on identical questions in one grid — pass/fail, latency, tokens, cost per cell.

One run answers: "On the same suite, does top_k=10 beat top_k=5? Does 8b match 70b quality at lower cost?" Without multiple providers, you would need separate runs and manual comparison.

</details>
