# Code Walkthrough — Phase 03 Eval Harness

Line-by-line guide to the eval pipeline: from `./evals/run_eval.sh` through Promptfoo to `rag.query()` and assertions. Use this as a workshop script when teaching Phase 03.

For theory (offline eval, regression testing), see [concepts.md](concepts.md). For assertion types in detail, see [promptfoo-details.md](promptfoo-details.md). For architecture and baseline numbers, see [design.md](design.md).

**Verified run:** 20 tests × 3 providers = 60 cells | 33 pass (55%) | ~3m 46s

---

## How to read this file

Each step follows the same structure:

1. Where it sits in the pipeline
2. The code (from the real files)
3. Line-by-line explanation
4. What this step does **not** do
5. Mental model

Work through one step at a time. Run `./evals/run_eval.sh` and `promptfoo view` between steps where noted.

---

## Big picture

```
You type:  ./evals/run_eval.sh
                │
                ▼
         run_eval.sh          Step 1 — set Python, start Promptfoo
                │
                ▼
         promptfoo eval        Step 2 — read config, build 60-cell grid
         (Node.js)
                │
                ▼
         rag_provider.py       Step 3 — call_api() for each cell
                │
                ▼
         rag.query()            Phase 02 — full RAG pipeline
                │
                ▼
         assertions             Step 4 — pass/fail on output
                │
                ▼
         promptfoo view        results grid
```

Two processes, one eval:

| Process | Language | Role |
|---|---|---|
| Promptfoo | Node.js | Orchestration, grid, assertions, UI |
| Python worker | Python | `call_api()` → `query()` per cell |

---

## Step 1 — `run_eval.sh`: start Promptfoo with the right Python

### The code

```1:7:evals/run_eval.sh
#!/usr/bin/env bash
# Run Phase 03 RAG evals with the project venv Python.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PROMPTFOO_PYTHON="${ROOT}/.venv/bin/python"
cd "$ROOT"
exec promptfoo eval -c evals/promptfooconfig.yaml "$@"
```

### Line by line

| Line | Purpose |
|---|---|
| `#!/usr/bin/env bash` | Run with bash when you execute `./evals/run_eval.sh` |
| `set -euo pipefail` | Exit on error; fail on undefined vars; pipeline errors propagate |
| `ROOT=...` | Resolve project root (`genai-learning-path/`) regardless of cwd |
| `export PROMPTFOO_PYTHON=...` | Tell Promptfoo which Python has `faiss`, `groq`, `openai`, etc. |
| `cd "$ROOT"` | So relative paths like `data/index/` resolve correctly |
| `exec promptfoo eval ...` | Replace shell with Promptfoo; `"$@"` forwards flags like `--no-cache` |

### Why `PROMPTFOO_PYTHON` matters

Promptfoo is Node.js. When it runs `rag_provider.py`, it spawns a Python subprocess. Without this variable, it may use system Python and fail with `ModuleNotFoundError`.

Always run evals via:

```bash
./evals/run_eval.sh
```

Do not run bare `promptfoo eval` unless you export `PROMPTFOO_PYTHON` yourself.

### What Step 1 does not do

| Does | Does not |
|---|---|
| Set venv Python | Call `call_api` or `query()` |
| Change to project root | Load test cases |
| Start Promptfoo with config path | Run assertions |

### Mental model

```
./evals/run_eval.sh [--no-cache]
  → PROMPTFOO_PYTHON=.venv/bin/python
  → cd project root
  → exec promptfoo eval -c evals/promptfooconfig.yaml
  → shell exits; Promptfoo owns the process
```

---

## Step 2 — `promptfooconfig.yaml`: the eval blueprint

### The code

```1:27:evals/promptfooconfig.yaml
description: Infosys AR FY2026 — RAG pipeline eval (Phase 03)

prompts:
  - "{{question}}"

providers:
  - id: file://rag_provider.py
    label: rag-top5-70b
    config:
      top_k: 5
  ...

defaultTest:
  assertThreshold: 1

tests: file://test_cases.yaml
```

### Section: `prompts`

```yaml
prompts:
  - "{{question}}"
```

Template filled from each test's `vars.question`. Example:

```
vars.question: "Who is the CEO of Infosys?"
  → prompt: "Who is the CEO of Infosys?"
```

### Section: `providers` (three RAG configs)

| Label | `config` | Effect |
|---|---|---|
| `rag-top5-70b` | `top_k: 5` | Default LLM from `.env` |
| `rag-top10-70b` | `top_k: 10` | Default LLM from `.env` |
| `rag-top5-8b` | `top_k: 5`, `model: llama-3.1-8b-instant` | Overrides generation model |

- `id: file://rag_provider.py` — Promptfoo imports this file and calls `call_api()` (see Step 3).
- `file://` paths resolve relative to the config directory (`evals/`).

### Section: `tests`

```yaml
tests: file://test_cases.yaml
```

Loads 20 test cases. Each has `vars`, `assert`, and optional `metadata`.

### Section: `defaultTest`

```yaml
assertThreshold: 1
```

All assertions in a test must pass for the cell to PASS. One failed assert → whole cell FAIL.

### The 60-cell grid

```
20 tests × 3 providers = 60 runs
Up to 4 cells run concurrently (Promptfoo default)
```

### What Step 2 does not do

| Does | Does not |
|---|---|
| Define prompt template and providers | Execute Python |
| Point to test file | Call APIs |
| Set assert threshold | Import `rag.py` |

---

## Step 3 — How Promptfoo calls `call_api` (not `__main__`)

### Two ways to run `rag_provider.py`

**A) Eval (normal path):**

```bash
./evals/run_eval.sh
```

1. Promptfoo starts Python worker using `PROMPTFOO_PYTHON`
2. Python **imports** `evals/rag_provider.py` as a module
3. Top-level code runs once: `load_dotenv`, `from rag import query`
4. For each of 60 cells, Promptfoo invokes **`call_api(prompt, options, context)`**
5. `if __name__ == "__main__"` block is **skipped** (`__name__` is `"rag_provider"`, not `"__main__"`)

**B) Manual smoke test:**

```bash
python evals/rag_provider.py
```

Runs the sample `call_api()` at the bottom of the file. Promptfoo is not involved.

### The function name contract

By default Promptfoo looks for **`call_api`**. Alternative:

```yaml
providers:
  - id: file://rag_provider.py:my_custom_function
```

Other Python provider entry points: `call_embedding_api`, `call_classification_api`. For RAG eval, only `call_api` is needed.

### What Promptfoo passes to each call

| Argument | Example (CEO test, rag-top5-70b) |
|---|---|
| `prompt` | `"Who is the CEO of Infosys?"` |
| `options` | `{ "config": { "top_k": 5 } }` |
| `context` | `{ "vars": { "question": "..." }, "test": { ... } }` |

Must return a dict with at least `"output"` (string assertions run against this).

---

## Step 4 — Where the LLM is configured

Three layers — only the middle differs per Promptfoo provider.

### Layer 1 — `promptfooconfig.yaml`

```yaml
config:
  top_k: 5
  model: llama-3.1-8b-instant   # only on rag-top5-8b
  # provider: groq              # optional — not set today
```

### Layer 2 — `rag_provider.py`

```python
provider = config.get("provider")   # None unless set in YAML
model = config.get("model")         # None or override

result = query(..., provider=provider, model=model)
```

### Layer 3 — `llm_chat.chat()` defaults

```python
provider = provider or os.getenv("LLM_PROVIDER", "groq")
model    = model    or os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
```

| Provider label | Generation LLM |
|---|---|
| `rag-top5-70b` | `.env` → `LLM_MODEL` (e.g. llama-3.3-70b) |
| `rag-top10-70b` | `.env` → `LLM_MODEL` |
| `rag-top5-8b` | YAML `model: llama-3.1-8b-instant` |

**Not configured per provider:** embedding model (`EMBEDDING_MODEL` in `.env`), FAISS index path (shared).

---

## Step 5 — `rag_provider.py`: the Promptfoo ↔ RAG bridge

### Module setup (runs once)

```14:22:evals/rag_provider.py
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env")
from rag import query
```

### `call_api()` flow

```python
def call_api(prompt, options, context):
    question = context["vars"].get("question") or prompt
    top_k = int(config.get("top_k", 5))
    provider = config.get("provider")
    model = config.get("model")

    result = query(
        question=question,
        index_dir=str(ROOT / "data/index"),
        top_k=top_k,
        provider=provider,
        model=model,
    )

    output = result["answer"] + "\n\n--- sources ---\n" + source summary
    return {
        "output": output,
        "tokenUsage": {...},
        "cost": ...,
        "latencyMs": ...,
    }
```

| Step | Action |
|---|---|
| Extract question | From `context.vars` or `prompt` |
| Read config | `top_k`, optional `model` / `provider` from YAML |
| Call RAG | One full `query()` — embed, FAISS, `chat()` |
| Format output | Answer + source lines for visibility in UI |
| Return dict | Promptfoo uses `output` for asserts; tracks tokens/cost/latency |

On exception: `return {"error": str(exc)}` → cell marked ERROR in Promptfoo.

### What Step 5 does not do

| Does | Does not |
|---|---|
| Bridge Promptfoo to `query()` | Define tests or assertions |
| Pass provider config through | Choose embedding model per provider |

---

## Step 6 — One full cell end to end (PASS example)

**Cell:** CEO test × `rag-top5-70b`

### 6.1 Test case loaded

```yaml
vars:
  question: "Who is the CEO of Infosys?"
assert:
  - type: icontains
    value: "Salil Parekh"
  - type: icontains
    value: "infosys-ar-26.pdf"
```

### 6.2 `call_api` → `query()`

Inside `query()` (Phase 02):

1. Load `faiss.index` + `chunks.json`
2. Embed question (OpenAI `text-embedding-3-small`)
3. FAISS top-5 search → indices e.g. `[11, 14, 12, 143, 294]`
4. Build system prompt with 5 labelled chunks
5. `chat()` → Groq llama-3.3-70b

Typical answer:

```
The CEO of Infosys is Salil Parekh. [Source: infosys-ar-26.pdf, Page: 12]
```

Top source: page 12, score 0.712.

### 6.3 Return to Promptfoo

```python
{
  "output": "The CEO of Infosys is Salil Parekh... \n\n--- sources ---\n[0.712] infosys-ar-26.pdf p.12\n...",
  "tokenUsage": {"total": 930, "prompt": 903, "completion": 27},
  "cost": 0.0,
  "latencyMs": ~400-500,
}
```

### 6.4 Assertions

| Assert | Check | Result |
|---|---|---|
| `icontains "Salil Parekh"` | Name in output | ✓ |
| `icontains "infosys-ar-26.pdf"` | Citation in output | ✓ |

All pass + `assertThreshold: 1` → **PASS** (green in `promptfoo view`).

---

## Step 7 — One full cell end to end (FAIL example)

**Cell:** Retail segment revenue × `rag-top5-70b`

### Assertions

```yaml
assert:
  - type: icontains
    value: "12.9"
  - type: not-icontains
    value: "12.2"
```

### Typical output

Wrong segment values from chart text extraction (COM instead of Retail):

```
... 11.7% ... 12.2% ...
```

| Assert | Result |
|---|---|
| `icontains "12.9"` | ✗ correct Retail FY2026 value missing |
| `not-icontains "12.2"` | ✗ COM value present |

One failure → cell **FAIL**. Same pipeline as PASS cell; assertions surface the regression.

This test has `metadata.expected_result: fail` — documents a known Phase 02 limitation, not a broken eval harness.

---

## Complete flow diagram

```
./evals/run_eval.sh
    │
    ▼
promptfooconfig.yaml
    ├── prompts: "{{question}}"
    ├── providers: rag-top5-70b | rag-top10-70b | rag-top5-8b
    ├── tests: test_cases.yaml (20)
    └── assertThreshold: 1
    │
    ▼
For each of 60 cells (parallel ×4):
    │
    ├── Render prompt from vars.question
    ├── call_api(prompt, options.config, context)
    │       │
    │       ├── query() → embed → FAISS → chat()
    │       └── return { output, tokenUsage, cost, latencyMs }
    │
    ├── Run assert list on output
    └── PASS | FAIL | ERROR
    │
    ▼
promptfoo view  — grid + stats
```

---

## Quick reference

| Question | Answer |
|---|---|
| Who calls `call_api`? | Promptfoo Python worker, 60 times per run |
| Is `__main__` used in eval? | No — only for `python evals/rag_provider.py` |
| Required function name? | `call_api` (unless `file://script.py:other_fn`) |
| Where is LLM set? | YAML `config.model` → `query()` → `chat()` → else `.env` |
| Where is embedding model set? | `.env` `EMBEDDING_MODEL` only — shared by all providers |
| What do asserts check? | The `output` string from `call_api` |
| How to run? | `./evals/run_eval.sh` then `promptfoo view` |

---

## Related docs

| Topic | File |
|---|---|
| Eval concepts | [concepts.md](concepts.md) |
| Install and troubleshoot | [setup.md](setup.md) |
| Baseline and architecture | [design.md](design.md) |
| Assertion types (`icontains`, `llm-rubric`, etc.) | [promptfoo-details.md](promptfoo-details.md) |
| RAG pipeline (Phase 02) | [../phase-02/code-walkthrough.md](../phase-02/code-walkthrough.md) |
