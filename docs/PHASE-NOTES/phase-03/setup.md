# Setup — Phase 03

## Prerequisites

- Phase 02 complete: `data/index/` built from `infosys-ar-26.pdf`
- `.env` with `OPENAI_API_KEY`, `GROQ_API_KEY`, `EMBEDDING_MODEL`, `LLM_PROVIDER`, `LLM_MODEL`
- Node.js 18+ (for Promptfoo)

## Install Promptfoo

```bash
npm install -g promptfoo
```

Verify:

```bash
promptfoo --version
```

## Run the eval suite

From the project root:

```bash
./evals/run_eval.sh
```

`run_eval.sh` sets `PROMPTFOO_PYTHON` to the project `.venv` so Promptfoo uses the same dependencies as `rag.py`.

Options:

```bash
# Skip cache (force fresh API calls)
./evals/run_eval.sh --no-cache

# Open results in browser
promptfoo view
```

## Files

| File | Purpose |
|---|---|
| `evals/test_cases.yaml` | 20 test questions and assertions |
| `evals/rag_provider.py` | Promptfoo Python provider — calls `query()` |
| `evals/promptfooconfig.yaml` | Providers, prompts, test file reference |
| `evals/run_eval.sh` | Wrapper — sets venv Python and runs eval |

## Provider configurations

Three configs run against the same 20 tests:

| Label | top_k | LLM model |
|---|---|---|
| `rag-top5-70b` | 5 | `LLM_MODEL` from `.env` (default: llama-3.3-70b) |
| `rag-top10-70b` | 10 | same |
| `rag-top5-8b` | 5 | `llama-3.1-8b-instant` |

## Troubleshooting

**`Python 3 not found`**

Run via `./evals/run_eval.sh` — do not call `promptfoo eval` directly unless you export:

```bash
export PROMPTFOO_PYTHON="/path/to/genai-learning-path/.venv/bin/python"
```

**`Index not found`**

Rebuild the index:

```bash
source .venv/bin/activate
python src/rag.py --index
```

**Rate limits**

Promptfoo runs up to 4 tests concurrently. Each test = 1 embedding call + 1 Groq call. If Groq rate-limits, reduce concurrency in `promptfooconfig.yaml` (Promptfoo `evaluateOptions.maxConcurrency`).
