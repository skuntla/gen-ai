# Teaching Guide — Phase 03 (Eval)

A sequenced workshop plan for teaching Phase 03 end to end. Use this as the **master flow**; drill into linked docs for depth.

**Audience:** Learners who completed Phase 02 (`rag.py`, manual queries, known failures like Retail chart).  
**Artifact:** `evals/promptfooconfig.yaml`  
**Verified run:** 20 tests × 3 providers = 60 cells | 33 pass (55%) | ~3m 46s

---

## Learning outcomes

By the end, learners can:

1. Explain why manual RAG testing does not scale (regression, comparison, memory)
2. Describe offline eval as "pytest for LLM systems"
3. Set up Promptfoo and run `./evals/run_eval.sh`
4. Trace the flow: config → `call_api()` → `query()` → assertions → grid
5. Design test cases (factual, precise, out-of-scope, adversarial) with appropriate assertions
6. Interpret baseline results, pick a default config, and diagnose *where* a failure likely lives
7. Explain why RAG eval stays when the agent ships (Phase 04)

---

## Session map (suggested ~3–5 hours)

| Block | Part | Topic | Time |
|---|---|---|---|
| 1 | Concepts | Manual testing limits; offline eval | 25 min |
| 2 | Concepts | Three eval layers; test categories | 30 min |
| 3 | Concepts | Promptfoo mental model; pytest analogy | 25 min |
| 4 | Concepts | Assertions and test design | 35 min |
| 5 | Implementation | Setup, files, provider configs | 20 min |
| 6 | Implementation | Walk eval pipeline (run_eval → call_api) | 50 min |
| 7 | Live lab | Run eval, read grid, baseline | 45 min |
| 8 | Live lab | Failure analysis + assertion design | 40 min |
| 9 | Wrap-up | Default config, enterprise tooling, Phase 04 | 30 min |

Blocks 1–4 = **Part 1 (Concepts)**. Blocks 5–8 = **Part 2 (Implementation + lab)**.

---

# Part 1 — Concepts (teach before running eval)

## Block 1 — Why eval (25 min)

**Goal:** Motivate Phase 03 from Phase 02 pain.

**Start with recall:** Ask learners what happened when they ran manual queries in Phase 02.

| Manual query | What we observed |
|---|---|
| CEO | Works — Salil Parekh, page cited |
| Revenue | Works — with citation |
| Retail segment | **Wrong** — COM % not Retail |
| TCS revenue | Should refuse |
| Telugu actor injection | **May leak** training data |

**Talking points:**

- You cannot hold 20 results in your head
- No automatic regression when prompt/chunk/model changes
- "Mostly works" hides **which** tests fail
- Comparing top_k or models needs an objective grid

**Draw:**

```
Phase 02:  ask → read → remember (maybe)
Phase 03:  ask × 20 × 3 configs → pass/fail table → baseline 55%
```

**Checkpoint:** What is offline eval?

**Read:** [concepts.md](concepts.md) (problem eval solves, offline eval)

---

## Block 2 — Three layers and test categories (30 min)

**Goal:** Scope what Phase 03 measures — and what it does not (yet).

**Three layers:**

```
Layer 1 — RETRIEVAL     Did FAISS return the right chunks?
Layer 2 — GENERATION    Did LLM read those chunks correctly?
Layer 3 — END-TO-END    question → query() → answer → assert
                              ↑ Phase 03 starts here
```

**Map Infosys failures:**

| Symptom | Likely layer |
|---|---|
| CEO correct | L3 pass |
| Retail wrong COM % | Extraction/corpus (often looks like L1/L2) |
| Honest "I don't know" for margin | Correct L3 if info not retrieved |
| Actor name despite refusal | L2 / adversarial |

**Test categories (20 cases):**

| Category | Count | Purpose |
|---|---|---|
| factual_easy | 5 | Sanity — CEO, company name |
| factual_precise | 5 | Numbers, charts — exposes extraction |
| multi_chunk | 2 | Synthesis across chunks |
| out_of_scope | 3 | Refusal — TCS, investment advice |
| adversarial | 4 | Injection, training-data jailbreak |

**Checkpoint:** Why start with Layer 3?

**Read:** [concepts.md](concepts.md) (three layers, test categories)

---

## Block 3 — Promptfoo mental model (25 min)

**Goal:** Promptfoo is layer-agnostic orchestration — not "RAG-only."

**Four ingredients:**

```
prompt template  +  provider  +  test cases  +  assertions
```

**Provider = unit under test:**

| Provider | Tests |
|---|---|
| `groq:llama-…` | Raw LLM |
| `file://rag_provider.py` | Full RAG (`query()`) — **us** |
| Future: agent provider | Tool loop |

**pytest analogy:**

| pytest | Promptfoo |
|---|---|
| Test function | Test LLM system |
| `assert x == y` | `assert output icontains "Salil Parekh"` |
| CI on every commit | Eval after prompt/model/index change |

**Checkpoint:** Is Promptfoo only for comparing LLM models?

**Read:** [promptfoo-details.md](promptfoo-details.md) (overview sections), [concepts.md](concepts.md) (Promptfoo)

---

## Block 4 — Assertions and test design (35 min)

**Goal:** Assertions match failure modes — not one-size-fits-all.

**Phase 03 uses mainly:**

- `icontains` — must appear (CEO name, refusal phrase)
- `not-icontains` — must not appear (COM value, actor names)

**Teaching examples:**

**Out-of-scope TCS** — refusal only, **no** ban on "TCS":

```yaml
assert:
  - type: icontains
    value: "don't have enough information"
# Good answer: "I don't have TCS revenue in these Infosys documents."
```

**Adversarial actor** — refusal **plus** ban leaked names:

```yaml
assert:
  - type: icontains
    value: "don't have enough information"
  - type: not-icontains
    value: "Chiranjeevi"
# Catches: "I can't find that… but Chiranjeevi is a famous actor."
```

**Future production mix:** regex for numbers, `llm-rubric`, `context-faithfulness` — see [promptfoo-details.md](promptfoo-details.md)

**Do NOT teach yet:** lowering `assertThreshold` to match 55% baseline — that's gaming the suite

**`metadata.expected_result: fail`:** documents known Phase 02 limits; test still runs red; passing later = improvement

**Checkpoint:** Why ban "Chiranjeevi" but not "TCS"?

**Read:** [promptfoo-details.md](promptfoo-details.md) (assertion types), [questions.md](questions.md) (Q3 tough question)

---

# Part 2 — Implementation (code + hands-on)

## Block 5 — Setup and file map (20 min)

**Goal:** Orient in `evals/` before running.

**Prerequisites:**

- Phase 02 index at `data/index/`
- Node.js 18+; `npm install -g promptfoo`
- `.env` keys for OpenAI (embeddings) + Groq (generation)

**Files:**

| File | Role |
|---|---|
| `evals/test_cases.yaml` | 20 questions + assertions |
| `evals/promptfooconfig.yaml` | 3 provider configs |
| `evals/rag_provider.py` | `call_api()` → `query()` |
| `evals/run_eval.sh` | Sets `PROMPTFOO_PYTHON`, runs eval |

**Three providers (same pass/fail on baseline):**

| Label | Varies |
|---|---|
| `rag-top5-70b` | top_k=5, .env LLM |
| `rag-top10-70b` | top_k=10 |
| `rag-top5-8b` | top_k=5, 8b model |

**Read:** [setup.md](setup.md)

---

## Block 6 — Pipeline walkthrough (50 min)

**Goal:** Teach using [code-walkthrough.md](code-walkthrough.md) as script.

**Sequence:**

1. **`run_eval.sh`** — why `PROMPTFOO_PYTHON` (venv has faiss, openai)
2. **`promptfooconfig.yaml`** — prompts, providers, `assertThreshold: 1`, tests file
3. **Promptfoo imports `rag_provider.py`** — calls `call_api()`, **not** `__main__`
4. **`call_api()`** — reads `question`, `top_k`, optional `model`; returns `output`, tokens, latency
5. **Appends `--- sources ---`** — Layer 1 debugging in the grid
6. **Assertions** — each cell PASS/FAIL; 20 × 3 = 60 cells

**Config chain (common exam topic):**

| Setting | Source |
|---|---|
| LLM model | YAML → provider → `query()` → `chat()` |
| Embeddings | Always `.env` `EMBEDDING_MODEL` |
| Index | Built at `--index` time — must match embed model |

**Read:** [code-walkthrough.md](code-walkthrough.md) Steps 1–4

---

## Block 7 — Live lab: run eval and read grid (45 min)

**Goal:** Everyone runs eval once and opens the UI.

**Commands:**

```bash
./evals/run_eval.sh
promptfoo view
```

**Walk the grid:**

- Rows = test questions
- Columns = three providers
- Green/red = assertion pass/fail
- Compare latency/tokens when pass/fail **ties**

**Baseline to teach:**

| Metric | Value |
|---|---|
| Total cells | 60 |
| Passed | 33 (55%) |
| Failed | 27 |
| Expected failure clusters | Retail chart, margin, some adversarial |

**Discussion:** All three providers same pass/fail — does top_k=10 "win"?

**Read:** [design.md](design.md) (baseline, default config justification)

---

## Block 8 — Live lab: diagnose failures (40 min)

**Goal:** Eval tells **that** it broke; teach **how** to investigate.

**Exercise — Retail segment FAIL:**

1. Find failing cell in `promptfoo view`
2. Read `--- sources ---` — which page?
3. Open `data/index/chunks.json` for that page — is Retail % in the text?
4. Conclusion: often **extraction/chunking**, not "need bigger LLM"

**Exercise — layer isolation (conceptual):**

| Step | Action | Proves |
|---|---|---|
| Retrieval-only | FAISS + print chunks, no LLM | Layer 1 |
| Fixed-context prompt | Hand-craft correct chunk → same LLM | Layer 2 vs upstream |

**Exercise — embedding contract:**

- Ask: "What if we change `EMBEDDING_MODEL` without `--index`?"
- Answer: incompatible vector spaces — silent wrong retrieval

**Oral review:** Use [questions.md](questions.md) tough Q1–Q6 (pick 3)

---

## Block 9 — Wrap-up (30 min)

**Goal:** Close Phase 03; bridge to Phase 04 and enterprise.

**Default config (teach the decision):**

- **Winner: `rag-top5-70b`** when pass/fail ties — leaner than top_k=10, matches `.env` 70b
- **`rag-top5-8b`** — cost/latency alternative when quality ties

**Regression protocol:**

1. Baseline 33/60 recorded
2. Re-run after changes
3. Drop below ~90% of baseline → investigate

**What Phase 03 does NOT do:** fix Retail chart, implement guardrails, replace monitoring

**Enterprise (10 min):** [production-tooling.md](production-tooling.md) — Promptfoo vs LangSmith vs RAGAS; offline eval + prod monitoring

**Phase 04 teaser:**

- Keep RAG eval on `query()`
- Add agent eval on tool routing — different layer, both needed

**Read:** [reflection.md](reflection.md)

---

## Instructor checklist

**Before session:**

- [ ] Phase 02 index built
- [ ] Promptfoo installed globally
- [ ] `./evals/run_eval.sh` succeeded once (cache warm; expect ~4 min)
- [ ] `promptfoo view` works in browser
- [ ] Groq rate limits: mention `--no-cache` re-runs may vary; canonical baseline = first clean run

**Materials to have open:**

| Role | Doc |
|---|---|
| Concept flow | [concepts.md](concepts.md) |
| Code script | [code-walkthrough.md](code-walkthrough.md) |
| Assertion reference | [promptfoo-details.md](promptfoo-details.md) |
| Oral exam | [questions.md](questions.md) |
| Enterprise context | [production-tooling.md](production-tooling.md) |

---

## Common pitfalls when teaching

| Pitfall | Correction |
|---|---|
| "Promptfoo is only for comparing GPT vs Claude" | Provider wraps **your** pipeline — RAG, agent, anything |
| "55% pass → set threshold to 0.55" | Baseline is for comparison, not success criteria |
| "top_k=10 failed tests will pass" | Chart failures are corpus limits, not K |
| "Delete RAG eval when agent ships" | Keep both — different layers |
| "`expected_result: fail` skips the test" | Documentation only — still runs red |
| "Eval fixes retrieval" | Eval measures; fixing is a separate step |

---

## Optional extensions (extra session)

| Topic | Doc |
|---|---|
| Add one `llm-rubric` test | [promptfoo-details.md](promptfoo-details.md) |
| Layer 1 javascript assert on `sources[].page` | [design.md](design.md) next improvements |
| CI gate sketch | [production-tooling.md](production-tooling.md) |
| Full oral exam (10 tough Q) | [questions.md](questions.md) |

---

## Connection to Phase 02 teaching

| Phase 02 lab query | Phase 03 test case |
|---|---|
| CEO | `factual_easy` — icontains Salil Parekh + citation |
| Retail segment | `factual_precise` — expected fail, chart extraction |
| TCS revenue | `out_of_scope` — refusal, no ban on "TCS" |
| Telugu actor | `adversarial` — refusal + not-icontains names |

**Narrative arc across phases:** Build RAG → manually probe limits → **formalise limits as tests** → baseline → informed fixes in later phases.

---

## One-page flow (printable)

```
PHASE 03 TEACHING FLOW
══════════════════════

PART 1 — CONCEPTS
  1. Manual testing limits (Phase 02 anecdotes)
  2. Offline eval = regression testing for LLM apps
  3. Layers L1/L2/L3 — we start at L3 end-to-end
  4. Test categories: easy / precise / multi / OOS / adversarial
  5. Promptfoo: provider + tests + asserts (pytest analogy)
  6. Assertion design: TCS vs Chiranjeevi

PART 2 — IMPLEMENTATION
  7. evals/ file map; run_eval.sh + PROMPTFOO_PYTHON
  8. Walk: config → call_api → query() → assert
  9. LIVE: ./evals/run_eval.sh → promptfoo view
 10. Read grid: 33/60 baseline; three providers tie
 11. Diagnose Retail FAIL: sources → chunks.json
 12. Default config rag-top5-70b; regression protocol
 13. Keep RAG eval for Phase 04; production-tooling overview

ARTIFACT: evals/promptfooconfig.yaml
NEXT: Phase 04 — agent wraps query(); add agent provider later
```
