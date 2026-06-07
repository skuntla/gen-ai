# Production Tooling — Phase 03

What enterprises actually use for LLM/RAG evaluation, compared to what we built in `evals/`. Use this when teaching or when someone asks: *"Do companies really use Promptfoo? How is eval done in production?"*

For eval concepts (offline testing, regression baselines, three layers), see [concepts.md](concepts.md). For Promptfoo mechanics and assertion types, see [promptfoo-details.md](promptfoo-details.md).

---

## The eval problem: same everywhere

Every production LLM/RAG team eventually needs the same things Phase 03 builds:

| Need | Why |
|---|---|
| **Golden test set** | Fixed questions with expected behaviour — not ad-hoc manual queries |
| **Offline runs** | Catch regressions before users do |
| **Config comparison** | Model A vs B, top_k 5 vs 10 — objective, not gut feel |
| **Layered checks** | Retrieval quality, grounding, refusal, adversarial cases |
| **Baseline + CI gate** | Block deploys when pass rate drops |

The **discipline** is universal. The **tool** varies by team, stack, and cloud vendor.

---

## Our Phase 03 choice: Promptfoo

We use [Promptfoo](https://github.com/promptfoo/promptfoo) with a custom Python provider (`evals/rag_provider.py`) because it is:

- **Framework-agnostic** — wraps `query()` directly; no LangChain dependency (consistent with Phases 01–02)
- **Config-as-code** — `test_cases.yaml` + `promptfooconfig.yaml` live in git, reviewable in PRs
- **Multi-config grids** — same 20 tests × 3 providers in one run (`promptfoo view`)
- **Flexible assertions** — `icontains`, `regex`, `llm-rubric`, `javascript`, RAG-specific metrics
- **Good for teaching** — visual pass/fail grid, latency and token counts per cell

Run via `./evals/run_eval.sh` (sets `PROMPTFOO_PYTHON` to the project venv).

Promptfoo is **not the only enterprise option** — it is a popular open-source orchestrator for the pattern we teach.

---

## What enterprises use in practice

Teams rarely use one tool for everything. Production eval is usually a **stack**:

```
Golden dataset  →  Eval orchestrator  →  RAG-specific metrics  →  CI gate  →  Production monitoring
     │                    │                      │                    │              │
  YAML/JSON/DB      Promptfoo, LangSmith,    RAGAS, DeepEval,    GitHub Actions,  LangSmith,
                    Braintrust, custom pytest  TruLens             block on regression  Arize, W&B
```

### Tier 1 — Eval orchestrators (run tests, compare configs, pass/fail grid)

Pick based on existing stack and whether you need LangChain integration.

| Tool | Best for | Notes |
|---|---|---|
| **[Promptfoo](https://github.com/promptfoo/promptfoo)** | Config-as-code eval, model/prompt comparison, custom Python providers | What we use in Phase 03; strong YAML workflow |
| **[LangSmith](https://smith.langchain.com/)** | Teams already on LangChain/LangGraph | Datasets, eval runs, tracing in one place; less attractive if you avoid LangChain |
| **[Braintrust](https://www.braintrust.dev/)** | Product teams wanting eval + experiment tracking | Hosted; good UX for non-engineers reviewing results |
| **[Arize Phoenix](https://phoenix.arize.com/)** | Open-source eval + observability | Traces, evals, drift; common in ML platform teams |
| **[Weights & Biases Weave](https://wandb.ai/site/weave)** | Teams already on W&B for ML | Eval experiments alongside model training runs |
| **Custom pytest + golden YAML/JSON** | Large eng orgs with mature CI | Same pattern as Phase 03, hand-rolled; full control, more maintenance |

Typical Promptfoo swap in a LangChain shop — same test cases, different runner:

```python
# LangSmith: dataset + evaluator functions in Python
# Promptfoo: test_cases.yaml + file://rag_provider.py
# Both call the same query() under the hood
```

### Tier 2 — RAG-specific metric libraries

These measure retrieval and grounding quality with standard scores — often **combined with** an orchestrator, not instead of it.

| Library | Metrics | Typical use |
|---|---|---|
| **[RAGAS](https://github.com/explodinggradients/ragas)** | Faithfulness, answer relevancy, context precision/recall | RAG pipeline quality scoring |
| **[DeepEval](https://github.com/confident-ai/deepeval)** | Hallucination, G-Eval, RAG metrics | pytest-style test cases with LLM judges |
| **[TruLens](https://github.com/truera/truera-agents-langchain)** | Feedback functions on RAG apps | Often paired with LangChain apps |

Phase 03 uses simple `icontains` / `not-icontains` assertions first. Production suites typically add RAGAS or `llm-rubric` / `context-faithfulness` for fuzzy grounding checks (see [promptfoo-details.md](promptfoo-details.md)).

### Tier 3 — Cloud-native eval (platform lock-in)

Teams fully on one cloud often use built-in eval rather than a separate OSS tool.

| Platform | Eval capability |
|---|---|
| **Azure AI Evaluation SDK** | Safety, quality, RAG evaluators; integrates with Azure AI Foundry |
| **AWS Bedrock** | Model evaluation jobs, knowledge base testing |
| **Google Vertex AI** | Evaluation pipelines for generative models |

Same golden-set idea — different API and UI. Harder to port if you change cloud.

### Tier 4 — Production monitoring (post-ship, not a replacement for offline eval)

Offline eval (Phase 03) runs **before** deploy. Monitoring runs **after**.

| Tool | What it catches |
|---|---|
| LangSmith / Arize / Braintrust (prod mode) | Real user queries, latency spikes, error rates |
| Human review queues | High-stakes answers (legal, medical, investment advice) |
| Thumbs up/down + escalation | Drift over time, new failure modes not in golden set |

**Both are needed.** Offline eval gives known ground truth; monitoring catches unknown unknowns in production.

---

## Assertion strategies: learning vs production

| | Phase 03 (learning) | Typical enterprise |
|---|---|---|
| **Factual checks** | `icontains` / `not-icontains` | Same + `regex` for numbers |
| **Grounding** | System prompt + manual source inspection | `context-faithfulness`, RAGAS faithfulness, `llm-rubric` |
| **Retrieval quality** | Sources appended in provider output | Layer 1 asserts on `sources[].page`, RAGAS context recall |
| **Adversarial** | Refusal + `not-icontains` on leaked names | Same + dedicated red-team datasets, safety classifiers (Phase 06) |
| **Human review** | Eyeball `promptfoo view` | Sampled human eval for high-risk categories |

Recommended production mix (from [promptfoo-details.md](promptfoo-details.md)):

- ~40% keyword / regex assertions
- ~30% context-faithfulness or RAGAS
- ~20% LLM-as-judge (`llm-rubric`)
- ~10% adversarial `not-icontains`

---

## Phase 03 vs typical production

| | Our `evals/` (Phase 03) | Typical enterprise |
|---|---|---|
| **Orchestrator** | Promptfoo | Promptfoo, LangSmith, Braintrust, or custom CI |
| **Golden set size** | 20 tests | 50–500+; grows with every production bug |
| **Layers tested** | Layer 3 end-to-end on `query()` | Layer 1 + 2 + 3; separate retrieval-only evals |
| **Assertions** | Mostly `icontains` / `not-icontains` | Mixed: regex, RAGAS, LLM judge, javascript |
| **Config comparison** | 3 providers in one grid | Dozens of configs; automated winner selection |
| **Baseline** | Documented in `design.md` (55%) | CI gate: fail build if pass rate drops below threshold |
| **CI integration** | Manual `./evals/run_eval.sh` | GitHub Actions / Jenkins on every PR |
| **Agent eval** | Not yet (Phase 04+) | Separate suite on agent + keep RAG suite |
| **Production monitoring** | Not yet | LangSmith, Arize, or custom logging |

The **concepts are identical** — golden set, offline regression, config comparison, layered eval. Production adds scale, RAG-specific metrics, CI gates, and monitoring on top.

---

## How eval connects to Phase 02 production tooling

Phase 02 [production-tooling.md](../phase-02/production-tooling.md) covers extraction and chunking. Phase 03 eval **measures when those choices fail**:

| Phase 02 limitation | How Phase 03 catches it |
|---|---|
| `pdfplumber` garbles chart text | Retail segment test fails (`not-icontains: 11.7`) |
| Text-only extraction, no table parser | Precise number tests fail or marked `expected_result: fail` |
| Single chunk strategy for all PDFs | Multi-chunk and margin tests expose retrieval gaps |

Eval results **inform** Phase 02 tooling upgrades (move to Unstructured, cloud Document AI) — they do not fix them automatically.

---

## Learning path: why Promptfoo first, alternatives later

| Phase | Tooling choice | Reason |
|---|---|---|
| **Phase 03 (now)** | Promptfoo + YAML test cases + `rag_provider.py` | Understand eval mechanics without LangChain lock-in |
| **Phase 04+** | Add agent provider alongside RAG provider | Same orchestrator, different unit under test |
| **Phase 06** | Adversarial cases from Phase 03 inform guardrails | Eval defines what to block |
| **Production** | Promptfoo or LangSmith + RAGAS + CI gate + monitoring | Scale, RAG metrics, automated regression block |

When teaching, show both layers:

1. **Under the hood** — walk through [code-walkthrough.md](code-walkthrough.md): `run_eval.sh` → `call_api` → `query()` → assertions
2. **In production** — "here is the LangSmith / RAGAS equivalent and when you'd reach for it"

The skill is **eval discipline** (golden set, baseline, regression). The orchestrator is interchangeable.

---

## CI integration pattern (production)

Phase 03 runs manually. Production wires the same script into CI:

```yaml
# Example: .github/workflows/rag-eval.yml (not implemented yet)
- name: Run RAG eval
  run: ./evals/run_eval.sh --no-cache
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}

- name: Check pass rate
  run: |
    # Parse promptfoo output or use promptfoo eval --output results.json
    # Fail if pass_rate < 0.90 * BASELINE_PASS_RATE
```

Typical gates:

- **Hard fail** — pass rate drops below ~90% of baseline
- **Soft warn** — latency or cost regression without quality change
- **Scheduled nightly** — full 500-case suite; PR runs a smoke subset (20–50 cases)

---

## Quick reference: when to use what

| Situation | Recommendation |
|---|---|
| Learning eval, no LangChain | Promptfoo + custom Python provider (Phase 03) |
| Already on LangChain/LangGraph | LangSmith datasets + evaluators |
| Need RAG faithfulness scores | RAGAS or DeepEval alongside orchestrator |
| Fully on Azure / AWS / GCP | Cloud-native eval SDK + golden set in your repo |
| Large eng org, existing pytest CI | Custom pytest + golden YAML; same pattern, more control |
| Comparing 10+ model configs | Promptfoo or Braintrust — grid comparison is the core workflow |
| Post-ship drift and real user queries | Production monitoring (LangSmith, Arize) — not a substitute for offline eval |
| High-stakes domain (legal, medical) | Offline eval + mandatory human review sample |
| Agent with tools (Phase 04+) | Keep RAG eval on `query()`; add separate agent eval on `agent.run()` |

---

## Mental model for teaching

When someone asks *"Do enterprises use Promptfoo?"*:

> **Enterprises use offline golden-set eval with regression baselines. Promptfoo is one popular open-source way to orchestrate that. LangSmith, RAGAS, and custom pytest CI are equally common depending on the stack. The pattern you learned in Phase 03 is what matters.**

```
What you built                    What enterprises add
──────────────                    ────────────────────
test_cases.yaml          →        500+ cases, curated from prod failures
promptfooconfig.yaml     →        Same, or LangSmith / Braintrust project
rag_provider.py          →        Same wrapper pattern on internal APIs
design.md baseline       →        CI gate blocking merge on regression
promptfoo view           →        + RAGAS scores + monitoring dashboards
```

---

## Related docs

| Topic | File |
|---|---|
| Phase 03 eval concepts | [concepts.md](concepts.md) |
| Promptfoo overview and assertions | [promptfoo-details.md](promptfoo-details.md) |
| Line-by-line eval walkthrough | [code-walkthrough.md](code-walkthrough.md) |
| Baseline results | [design.md](design.md) |
| Interview questions (incl. enterprise eval) | [questions.md](questions.md) |
| Phase 02 extraction/chunking production tooling | [../phase-02/production-tooling.md](../phase-02/production-tooling.md) |
| Enterprise chunking process | [../phase-02/enterprise-chunking.md](../phase-02/enterprise-chunking.md) |
