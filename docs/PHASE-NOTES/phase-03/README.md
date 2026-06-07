# Phase 03 — Eval: Stop Guessing If It Works

**Goal:** Measure RAG quality systematically instead of eyeballing outputs.

**Artifact:** `evals/promptfooconfig.yaml`

---

## Contents

| File | What's in it |
|---|---|
| [concepts.md](concepts.md) | Offline eval, regression testing, Promptfoo, assertions, three eval layers |
| [setup.md](setup.md) | Promptfoo install, run_eval.sh, troubleshooting |
| [design.md](design.md) | Provider wrapper, test suite, baseline results |
| [code-walkthrough.md](code-walkthrough.md) | Line-by-line teaching guide: run_eval.sh → Promptfoo → call_api → assertions |
| [teaching-guide.md](teaching-guide.md) | **Master teaching flow** — Part 1 concepts, Part 2 implementation, lab script, checklist |
| [promptfoo-details.md](promptfoo-details.md) | What Promptfoo is, LLM vs RAG vs agent eval, assertion types |
| [production-tooling.md](production-tooling.md) | Enterprise eval stack: Promptfoo vs LangSmith, RAGAS, CI, monitoring |
| [questions.md](questions.md) | Interview questions, tough oral-review Q&A with model answers |
| [reflection.md](reflection.md) | Post-implementation observations and lessons learned |
