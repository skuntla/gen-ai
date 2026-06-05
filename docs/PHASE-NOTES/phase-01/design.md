# Design — Phase 01

## What we built

`src/llm_chat.py` — a CLI tool and reusable module.

```bash
python src/llm_chat.py "What is RAG?"
python src/llm_chat.py "What is RAG?" --model claude-haiku-4-5
python src/llm_chat.py "What is RAG?" --system "Reply in one sentence" --temperature 0.2
```

---

## Libraries

| Library | Purpose |
|---|---|
| `anthropic` | Official Anthropic SDK — handles auth, retries, response parsing |
| `python-dotenv` | Loads `.env` into environment variables at startup |
| `argparse` | Parses CLI flags (`--model`, `--system`, `--temperature`) |

No frameworks. Raw SDK calls only — every layer is visible and nothing is hidden behind an abstraction.

---

## Key design decisions

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

- [ ] `python src/llm_chat.py "What is RAG?"` returns a response
- [ ] Same prompt on Haiku vs Sonnet shows measurable quality, latency, and cost difference
- [ ] System prompt visibly changes tone and format of output
- [ ] API keys loaded from `.env`, not hardcoded
- [ ] Token usage and estimated cost printed on every call
- [ ] Module is importable by later phases (clean function API, not just a script)
