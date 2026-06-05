# Design — Phase 01

## What we built

`src/llm_chat.py` — a CLI tool and reusable module.

In the context of the Stock Research Assistant, Phase 01 is the foundation: a clean way to send any text to an LLM and get a response. Later phases will wrap this to analyse earnings reports, extract financial ratios, and classify news.

```bash
# Default provider from .env
python src/llm_chat.py "What is the promoter holding trend for TCS?"

# Explicitly pick provider and model
python src/llm_chat.py "Is Infosys a good investment?" --provider groq --model llama-3.3-70b-versatile
python src/llm_chat.py "Is Infosys a good investment?" --provider ollama --model llama3.1:8b

# Override system prompt and temperature
python src/llm_chat.py "Summarise Infosys earnings" \
  --system "You are a financial analyst. Be concise." \
  --temperature 0.0
```

---

## Libraries

| Library | Purpose |
|---|---|
| `groq` | Groq SDK — used for cloud inference (Llama 3.3 70B, free tier) |
| `openai` | OpenAI SDK — reused for Ollama's OpenAI-compatible local API |
| `anthropic` | Anthropic SDK — added when switching to Claude (Phase 03+) |
| `python-dotenv` | Loads `.env` into environment variables at startup |
| `argparse` | Parses CLI flags (`--model`, `--system`, `--temperature`, `--provider`) |

No frameworks. Raw SDK calls only — every layer is visible and nothing is hidden behind an abstraction.

---

## Key design decisions

### Model and provider as configuration, not code

Model names and providers are never hardcoded. They are read from environment variables with sensible defaults:

```python
provider = os.getenv("LLM_PROVIDER", "groq")
model    = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
```

To switch from Groq to Anthropic, change `.env` only — no code change required:

```
LLM_PROVIDER=anthropic
LLM_MODEL=claude-haiku-4-5
```

`llm_chat.py` reads the provider and routes to the correct SDK internally. All callers — including Phases 04, 07, and 10 — call the same `chat()` function regardless of which provider is underneath.

### Provider abstraction

A thin routing layer inside `llm_chat.py` maps provider name to SDK call:

```
LLM_PROVIDER=groq       → Groq SDK         (Phases 01–02, cloud, free)
LLM_PROVIDER=ollama     → OpenAI SDK        (local, free, needs ollama serve)
LLM_PROVIDER=anthropic  → Anthropic SDK     (Phase 03+, paid)
```

The public function signature never changes:

```python
def chat(prompt, system=None, temperature=0.1, model=None, provider=None) -> dict:
    # always returns:
    # {"response": "...", "input_tokens": 41, "output_tokens": 24, "cost_usd": 0.0001}
```

This means swapping providers during Phase 03 is a one-line `.env` change — not a refactor.

### Module, not just a script

`llm_chat.py` exposes a callable function in addition to a `__main__` CLI entry point. Phase 04 imports it directly as a dependency. This forces clean separation between the interface and the logic from day one and avoids a refactor later.

```python
# importable by other phases
def chat(prompt, model=..., system=..., temperature=...):
    ...

# CLI entry point
if __name__ == "__main__":
    args = parse_args()
    response = chat(args.prompt, ...)
    print(response)
```

### Log tokens and cost on every call

Token logging is added in Phase 01, not Phase 05. Cost visibility from the first call builds the habit of treating API spend as a first-class concern. It also gives real numbers to compare when switching models in Phase 01 acceptance criteria.

### API key from `.env` only

Keys are loaded via `python-dotenv`. Hardcoding is not an option — it's enforced by the `.gitignore` which excludes `.env` entirely.

---

## Acceptance criteria

- [x] `python src/llm_chat.py "What is the promoter holding trend for TCS?"` returns a response
- [x] Same prompt on Groq 70B (cloud) vs Ollama 8B (local) shows measurable latency difference (686ms vs 12,835ms)
- [x] System prompt visibly changes output — "one sentence" prompt reduced output from 356 to 28 tokens
- [x] API keys loaded from `.env`, not hardcoded
- [x] Token usage and estimated cost printed on every call
- [x] Module is importable by later phases (`from src.llm_chat import chat`)
