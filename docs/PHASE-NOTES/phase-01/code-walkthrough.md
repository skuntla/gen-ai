# Code Walkthrough — `src/llm_chat.py`

Line-by-line guide to reading and teaching `llm_chat.py`. Use this as a workshop script when walking someone through the Phase 01 implementation.

For architecture and design decisions, see [design.md](design.md). For theory (messages format, tokens, temperature), see [concepts.md](concepts.md) and [temperature.md](temperature.md) — this file focuses on **how the code works**.

**Verified run (acceptance criteria):** Groq 70B ~686ms vs Ollama 8B ~12,835ms on same prompt; system prompt "one sentence" → 356 → 28 output tokens.

---

## How to read this file

Each step follows the same structure:

1. Where it sits in the flow
2. The code (from the real file)
3. Line-by-line explanation
4. What this step does **not** do
5. Mental model

Work through one step at a time. Run the commands yourself between steps where noted.

---

## Big picture

```
CLI  (python src/llm_chat.py "your prompt")
────────────────────────────────────────────────────────────
Terminal args
  → argparse                     Step 7 — parse prompt, flags
  → chat()                       Step 5 — public API, provider routing
  → _call_groq | _call_ollama | _call_anthropic   Steps 2–4
  → _cost()                      Step 1 — estimate USD
  → _print_result()              Step 6 — stdout


IMPORT  (from rag.py, agent.py, evals — later phases)
────────────────────────────────────────────────────────────
chat(prompt, system=..., temperature=..., model=..., provider=...)
  → same routing → same return dict
  → __main__ block is NOT executed
```

Two entry points, one function:

| Entry | When | Uses |
|---|---|---|
| `python src/llm_chat.py "..."` | Human / demo | CLI → `chat()` → print |
| `from llm_chat import chat` | Phase 02+ code | `chat()` only |

---

## Step 0 — Module load: imports, `.env`, constants

### Where it sits

Top of file. Runs once when Python imports or executes the module.

### The code

```python
import os
import time
import argparse
from dotenv import load_dotenv

load_dotenv()

PRICING = {
    "llama-3.3-70b-versatile":  {"input": 0.0,    "output": 0.0},
    "llama-3.1-8b-instant":     {"input": 0.0,    "output": 0.0},
    "claude-haiku-4-5":         {"input": 0.0008, "output": 0.004},
    "claude-sonnet-4-5":        {"input": 0.003,  "output": 0.015},
}

DEFAULT_SYSTEM = "You are a helpful financial analyst specialising in Indian equities."
```

### Line-by-line

| Line | Role |
|---|---|
| `load_dotenv()` | Loads `.env` into `os.environ` — API keys, `LLM_PROVIDER`, `LLM_MODEL` |
| `PRICING` | Per-model USD per 1K tokens; Groq free tier = 0.0 |
| `DEFAULT_SYSTEM` | Default persona when caller does not pass `system=` |

**`load_dotenv()` before any API call** — ensures `GROQ_API_KEY` exists when `_call_groq` runs.

### What this step does not do

- Does not validate that keys exist (each `_call_*` fails at request time if missing)
- Does not connect to any provider yet — no network on import

### Mental model

Module load = read config from disk + set defaults. No LLM call yet.

**Try:** `python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('LLM_PROVIDER', 'groq'))"`

---

## Step 1 — `_cost()`: token → dollars

### Where it sits

Called by `_call_groq` and `_call_anthropic` after each API response. Ollama returns `cost_usd: 0.0` directly.

### The code

```python
def _cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = PRICING.get(model, {"input": 0.0, "output": 0.0})
    return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1000
```

### Line-by-line

1. Look up model in `PRICING`; unknown models → free (0.0) — safe default for new Groq models
2. `(input × input_rate + output × output_rate) / 1000` — rates are **per 1K tokens**

### What this step does not do

- Does not call billing APIs — estimate only
- Does not include embedding costs (Phase 02 uses OpenAI separately in `rag.py`)

### Mental model

Every `chat()` return includes `cost_usd` so Phase 05 observability and Phase 03 eval grids can aggregate spend from day one.

---

## Step 2 — `_call_groq()`: Groq SDK (default path)

### Where it sits

Primary provider for Phases 01–02. Invoked when `provider == "groq"`.

### The code

```python
def _call_groq(prompt: str, system: str, temperature: float, model: str) -> dict:
    from groq import Groq

    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    start = time.time()
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
    )
    latency_ms = int((time.time() - start) * 1000)

    input_tokens  = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens

    return {
        "response":      response.choices[0].message.content,
        "input_tokens":  input_tokens,
        "output_tokens": output_tokens,
        "cost_usd":      _cost(model, input_tokens, output_tokens),
        "model":         model,
        "provider":      "groq",
        "latency_ms":    latency_ms,
    }
```

### Line-by-line

| Part | Explanation |
|---|---|
| `from groq import Groq` inside function | Lazy import — module loads even if Groq not installed until first groq call |
| `messages=[system, user]` | Universal chat format — same shape OpenAI uses |
| `response.choices[0].message.content` | First (and usually only) completion |
| `usage.prompt_tokens` / `completion_tokens` | Provider-reported counts — trust these for cost |
| `latency_ms` | Wall-clock round trip — includes network + inference |

### What this step does not do

- Does not stream tokens (full response waited, then returned)
- Does not attach documents or tools — plain text in, text out
- Does not verify facts — answer comes from model weights, not your PDFs

### Mental model

One HTTP round trip: JSON messages in → assistant string + token counts out.

**Try:**

```bash
python src/llm_chat.py "What is RAG in one sentence?"
```

---

## Step 3 — `_call_ollama()`: local models via OpenAI-compatible API

### Where it sits

Optional local path. Invoked when `provider == "ollama"`.

### The code

```python
def _call_ollama(prompt: str, system: str, temperature: float, model: str) -> dict:
    from openai import OpenAI

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    client = OpenAI(api_key="ollama", base_url=base_url)
    # ... same messages shape as Groq ...
    return {
        ...
        "cost_usd":      0.0,
        "provider":      "ollama",
        ...
    }
```

### Line-by-line

- **`OpenAI` SDK with custom `base_url`** — Ollama exposes an OpenAI-compatible `/v1/chat/completions` endpoint; reuse one client pattern
- **`api_key="ollama"`** — dummy key; Ollama does not require a real secret locally
- **`cost_usd: 0.0`** — local inference; electricity not counted here

### What this step does not do

- Does not start `ollama serve` for you — must be running separately
- Does not pull models — `ollama pull llama3.1:8b` is manual

### Mental model

Same `messages` array, different base URL. Provider abstraction hides the difference from callers of `chat()`.

**Try:**

```bash
python src/llm_chat.py "Hello" --provider groq --model llama-3.3-70b-versatile
python src/llm_chat.py "Hello" --provider ollama --model llama3.1:8b
```

Compare `latency_ms` in output.

---

## Step 4 — `_call_anthropic()`: Claude (Phase 03+ default path)

### Where it sits

Paid provider for later phases. Invoked when `provider == "anthropic"`.

### The code

```python
def _call_anthropic(prompt: str, system: str, temperature: float, model: str) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    ...
    return {
        "response": response.content[0].text,
        ...
    }
```

### Line-by-line

| Difference from Groq | Why |
|---|---|
| `system=system` top-level arg | Anthropic API separates system from messages list |
| `messages=[user only]` | System not duplicated inside messages |
| `response.content[0].text` | Anthropic returns content blocks, not `.choices[0].message` |
| `max_tokens=1024` | Required cap on completion length |

### What this step does not do

- Does not use Groq's `chat.completions` shape — hence separate `_call_*` function

### Mental model

`chat()` normalises three different SDK shapes into **one return dict**. Callers never import Anthropic directly.

---

## Step 5 — `chat()`: public API (the contract for all later phases)

### Where it sits

The only function other modules should call.

### The code

```python
def chat(
    prompt: str,
    system: str = DEFAULT_SYSTEM,
    temperature: float = 0.1,
    model: str = None,
    provider: str = None,
) -> dict:
    provider = provider or os.getenv("LLM_PROVIDER", "groq")
    model    = model    or os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

    if provider == "groq":
        return _call_groq(prompt, system, temperature, model)
    elif provider == "ollama":
        return _call_ollama(prompt, system, temperature, model)
    elif provider == "anthropic":
        return _call_anthropic(prompt, system, temperature, model)
    else:
        raise ValueError(f"Unknown provider '{provider}'. Supported: groq, ollama, anthropic")
```

### Line-by-line

1. **Defaults from parameters, then `.env`** — CLI flags and programmatic callers can override without editing env
2. **`temperature=0.1`** — low randomness for financial factual tasks (see [temperature.md](temperature.md))
3. **Router if/elif** — add new provider = new `_call_*` + one branch
4. **Same return shape always** — Phase 02 `rag.py` reads `result["response"]`, token fields, `latency_ms`

### What this step does not do

- Does not retry on rate limits (Promptfoo eval may hit Groq limits — separate concern)
- Does not cache responses
- Does not log to disk — prints only in CLI path

### Mental model

```
chat() = configure (env/args) → route (provider) → normalise (dict)
```

**Phase 02 usage (preview):**

```python
result = chat(prompt=question, system=system_prompt, provider=provider, model=model)
answer = result["response"]
```

---

## Step 6 — `_print_result()`: CLI formatting

### Where it sits

CLI only. Importing `chat()` does not print anything.

### The code

```python
def _print_result(result: dict) -> None:
    print(result["response"])
    print(f"\n[{result['provider']} / {result['model']}]")
    print(f"Tokens : {result['input_tokens']} in / {result['output_tokens']} out")
    print(f"Cost   : ${result['cost_usd']:.6f}  |  Latency: {result['latency_ms']}ms")
```

### Mental model

Human-readable footer on every CLI run — builds token/cost awareness before Phase 05 dashboards.

---

## Step 7 — CLI: `if __name__ == "__main__"`

### Where it sits

Runs only when file is executed as script, not when imported.

### The code

```python
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat with an LLM from the command line.")
    parser.add_argument("prompt",                              help="The prompt to send")
    parser.add_argument("--system",      default=DEFAULT_SYSTEM, help="System prompt")
    parser.add_argument("--temperature", type=float, default=0.1, help="Sampling temperature")
    parser.add_argument("--model",       default=None,         help="Model name (overrides LLM_MODEL env var)")
    parser.add_argument("--provider",    default=None,         help="Provider: groq | anthropic")
    args = parser.parse_args()

    result = chat(args.prompt, args.system, args.temperature, args.model, args.provider)
    _print_result(result)
```

### Line-by-line

| Flag | Effect |
|---|---|
| `prompt` (positional) | User message — required |
| `--system` | Overrides default financial analyst persona |
| `--temperature` | 0.0 = deterministic; higher = more varied |
| `--model` | Overrides `LLM_MODEL` from `.env` |
| `--provider` | Overrides `LLM_PROVIDER` from `.env` |

### What this step does not do

- Does not run during `from llm_chat import chat` — same pattern as `rag_provider.py` in Phase 03

### Mental model

```
__name__ == "__main__"  →  CLI demo / manual testing
__name__ == "llm_chat"  →  library import for pipeline code
```

**Teaching demo — system prompt changes token count:**

```bash
python src/llm_chat.py "Summarise Infosys business highlights." \
  --system "Reply in exactly one sentence."
```

---

## End-to-end trace

One CLI call:

```
python src/llm_chat.py "Who is the CEO of Infosys?" --temperature 0.1
        │
        ▼
argparse → prompt, system=DEFAULT_SYSTEM, temperature=0.1, model=None, provider=None
        │
        ▼
chat() → provider=groq, model=llama-3.3-70b-versatile (from .env defaults)
        │
        ▼
_call_groq() → Groq API
        messages: [system: financial analyst, user: CEO question]
        │
        ▼
return dict { response, input_tokens, output_tokens, cost_usd, model, provider, latency_ms }
        │
        ▼
_print_result() → stdout
```

**Important teaching point:** The CEO answer comes from **training data**, not the Infosys PDF. Phase 02 fixes that with RAG.

---

## Quick reference

| Question | Answer |
|---|---|
| What do later phases import? | `chat()` only |
| Where are API keys? | `.env` via `load_dotenv()` |
| How to switch provider? | Change `LLM_PROVIDER` in `.env` or `--provider` flag |
| Default temperature? | `0.1` — factual tasks |
| Is output deterministic? | Not guaranteed; use `temperature=0.0` for closest repeatability |
| Groq vs Anthropic message format? | Hidden inside `_call_*`; `chat()` return is identical |

---

## Related docs

| Topic | File |
|---|---|
| Teaching session flow | [teaching-guide.md](teaching-guide.md) |
| Design decisions | [design.md](design.md) |
| Setup and API keys | [setup.md](setup.md) |
| Temperature deep dive | [temperature.md](temperature.md) |
| Interview questions | [questions.md](questions.md) |
| Next phase — RAG uses `chat()` | [../phase-02/code-walkthrough.md](../phase-02/code-walkthrough.md) |
