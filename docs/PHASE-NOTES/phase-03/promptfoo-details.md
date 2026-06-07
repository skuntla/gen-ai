# Promptfoo — What It Is and How We Use It

Promptfoo is a **general-purpose LLM evaluation framework**. It is not built only for RAG, only for agents, or only for comparing raw LLM models — it supports all of those depending on what you put inside the **provider**.

For the eval code flow (`run_eval.sh` → `call_api` → `query()`), see [code-walkthrough.md](code-walkthrough.md). For eval concepts (offline testing, regression baselines), see [concepts.md](concepts.md).

---

## The mental model

Promptfoo answers one question:

> For a fixed set of inputs, does this system produce acceptable outputs — and how do variants compare?

Every eval run combines four pieces:

```
prompt template  +  provider (system under test)  +  test cases  +  assertions
```

Promptfoo does not care what happens inside the provider. It only sees **input → output → pass/fail**.

| Provider type | What you are evaluating |
|---|---|
| `groq:llama-3.3-70b` | Raw LLM API call |
| `openai:gpt-4o` | Raw LLM (different vendor) |
| `file://rag_provider.py` | Full RAG pipeline (`query()`) — **Phase 03** |
| `file://agent_provider.py` (future) | Full agent with tool loop — **Phase 04+** |

The same test suite can compare raw LLM vs RAG vs agent by swapping the provider — without changing Promptfoo itself.

---

## LLM eval vs RAG eval vs agent eval

Think in **layers**. Promptfoo can sit at any layer; you choose what the provider calls:

```
Layer 3 — Agent     Did it pick the right tool and complete the task?
Layer 2 — RAG       Did retrieval + generation produce a grounded answer?  ← Phase 03
Layer 1 — LLM       Does the model follow instructions / format / safety?
```

| Phase | Unit under test | Provider calls |
|---|---|---|
| Phase 01 | Raw LLM | `chat()` directly |
| Phase 03 | RAG pipeline | `query()` via `rag_provider.py` |
| Phase 04+ | Agent | `agent.run()` or equivalent |
| Phase 09 | Full agent + tools | End-to-end agent |

Same tool, different **unit under test**.

---

## What Promptfoo is good at

1. **Comparing LLM models** — same prompts and tests, Groq vs OpenAI vs Anthropic in one grid
2. **Comparing prompts** — same model, different system prompts or templates
3. **Comparing configurations** — same pipeline, different `top_k`, chunk size, temperature
4. **Regression testing** — re-run after a change; did pass rate drop below baseline?
5. **Reporting** — `promptfoo view` grid with pass/fail, latency, tokens, cost per cell

---

## How this project uses Promptfoo (Phase 03)

We use Promptfoo for **RAG evaluation** by wrapping the pipeline in a Python provider:

```
Promptfoo
    └── rag_provider.call_api()
            └── rag.query()    ← embed → FAISS → chat()
```

Our three provider labels are **three configs of the same RAG pipeline**, not three built-in Promptfoo models:

| Label | What varies |
|---|---|
| `rag-top5-70b` | `top_k: 5`, default LLM from `.env` |
| `rag-top10-70b` | `top_k: 10`, default LLM from `.env` |
| `rag-top5-8b` | `top_k: 5`, `model: llama-3.1-8b-instant` |

20 tests × 3 providers = **60 cells** per `./evals/run_eval.sh`.

A fourth provider could call `chat()` without RAG to compare **LLM-only vs RAG** on the same questions in one grid.

---

## Analogy: pytest for LLM systems

| pytest | Promptfoo |
|---|---|
| Tests Python functions | Tests LLM **systems** (any provider) |
| `assert result == expected` | `assert output icontains "Salil Parekh"` |
| Run on every code change | Run after prompt / model / RAG config changes |
| Agnostic to internal implementation | Agnostic to LLM vs RAG vs agent |

---

## Short reference

| Question | Answer |
|---|---|
| Is Promptfoo for LLM evaluation? | Yes — core use case |
| For RAG evaluation? | Yes — when the provider wraps RAG (our setup) |
| For agent evaluation? | Yes — when the provider wraps the agent (later phases) |
| How to run our suite? | `./evals/run_eval.sh` then `promptfoo view` |
| Default Python entry point? | `call_api()` in `rag_provider.py` |

---

# Assertion types

In Promptfoo, the `assert` section defines **how the response should be evaluated**. The test suite uses a subset of assertion types; Promptfoo supports many more.

## 1. `icontains` (Case-insensitive contains)

Checks whether the response contains a string regardless of case.

```yaml
assert:
  - type: icontains
    value: "Salil Parekh"
```

### Pass

Response:

```text
The CEO of Infosys is Salil Parekh.
```

### Pass

Response:

```text
The CEO is salil parekh.
```

### Fail

Response:

```text
The CEO is Nandan Nilekani.
```

---

## 2. `not-icontains`

Checks that a string does **not** appear.

```yaml
assert:
  - type: not-icontains
    value: "Chiranjeevi"
```

Useful for:

- Preventing hallucinations
- Blocking jailbreak responses
- Ensuring wrong values are not returned

### Pass

```text
I don't have enough information in the provided documents.
```

### Fail

```text
A famous Telugu actor is Chiranjeevi.
```

---

## 3. Multiple assertions = AND condition

```yaml
assert:
  - type: icontains
    value: "Salil Parekh"
  - type: icontains
    value: "178650"
```

Both must pass.

Response:

```text
Infosys CEO is Salil Parekh and FY2026 revenue was 178650 crore.
```

✅ Pass

Response:

```text
Infosys CEO is Salil Parekh.
```

❌ Fail (missing revenue)

---

# Other useful Promptfoo assertion types

For RAG systems, these assertion types are especially useful.

---

## 4. `contains`

Case-sensitive contains.

```yaml
assert:
  - type: contains
    value: "Infosys"
```

Less commonly used.

Usually `icontains` is safer.

---

## 5. `equals`

Exact match.

```yaml
assert:
  - type: equals
    value: "Salil Parekh"
```

### Pass

```text
Salil Parekh
```

### Fail

```text
The CEO is Salil Parekh
```

Too strict for LLMs.

Not recommended for RAG.

---

## 6. `regex`

Useful for numbers, citations, page references.

```yaml
assert:
  - type: regex
    value: "1,?78,?650"
```

Matches:

```text
178650
1,78,650
```

Very useful.

I would replace many revenue checks with regex.

---

## 7. `not-regex`

```yaml
assert:
  - type: not-regex
    value: "11\\.7|12\\.2"
```

Ensures COM percentages don't appear.

Useful for known extraction bugs.

---

## 8. `similar`

Semantic similarity.

```yaml
assert:
  - type: similar
    value: "The CEO of Infosys is Salil Parekh."
```

Uses embeddings.

Good when wording varies.

---

## 9. `llm-rubric` — strong fit for RAG

This is the most flexible option for fuzzy quality checks.

Instead of matching text:

```yaml
assert:
  - type: llm-rubric
    value: |
      Response must:
      - identify Salil Parekh as CEO
      - cite the document
      - not introduce unsupported facts
```

Promptfoo uses another LLM as a judge.

Much more realistic.

---

## 10. `answer-relevance`

Checks whether answer actually addresses question.

```yaml
assert:
  - type: answer-relevance
```

Example:

Question:

```text
Who is the CEO?
```

Response:

```text
Infosys is an Indian IT company.
```

❌ Low relevance

---

## 11. `context-faithfulness` — critical for RAG

Checks if answer is grounded in retrieved context.

```yaml
assert:
  - type: context-faithfulness
```

Detects hallucinations.

Example:

Retrieved chunks:

```text
CEO: Salil Parekh
```

Response:

```text
Infosys was founded by Narayana Murthy in 1981.
```

❌ Not supported by context

---

## 12. `context-recall`

Checks whether retrieval actually returned information needed to answer.

Useful for evaluating:

- chunking
- embedding quality
- top-k retrieval

---

## 13. `javascript`

Custom logic.

```yaml
assert:
  - type: javascript
    value: |
      return output.includes("Salil Parekh")
          && output.includes("infosys-ar-26.pdf");
```

Very powerful.

---

# Assertion strategy for the Infosys RAG project

Recommended categorization:

### Factual

```yaml
assert:
  - type: icontains
    value: "Salil Parekh"
```

### Numbers

```yaml
assert:
  - type: regex
    value: "1,?78,?650"
```

### Citation checking

```yaml
assert:
  - type: icontains
    value: "infosys-ar-26.pdf"
```

### Hallucination prevention

```yaml
assert:
  - type: context-faithfulness
```

### Prompt injection

```yaml
assert:
  - type: icontains
    value: "don't have enough information"
  - type: not-icontains
    value: "Chiranjeevi"
```

### End-to-end quality

```yaml
assert:
  - type: llm-rubric
    value: |
      The answer must:
      - answer only from provided document
      - cite evidence
      - refuse unsupported questions
```

For a production-grade RAG evaluation suite, use a mix of:

- 40% `icontains` / `regex`
- 30% `context-faithfulness`
- 20% `llm-rubric`
- 10% adversarial `not-icontains`

That combination catches both retrieval failures and hallucinations.

---

## Related docs

| Topic | File |
|---|---|
| Eval code flow | [code-walkthrough.md](code-walkthrough.md) |
| Eval concepts | [concepts.md](concepts.md) |
| Setup and run | [setup.md](setup.md) |
| Baseline results | [design.md](design.md) |
| Enterprise eval tooling | [production-tooling.md](production-tooling.md) |