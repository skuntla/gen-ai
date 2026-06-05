# Phase 01 — Talk to an LLM

## Core concept

Every LLM provider exposes their model as an HTTP API. You send a JSON payload, you get a JSON response back. There is no magic — the intelligence lives on their servers. You are making web requests.

Everything else in this learning path — RAG, agents, memory, multi-agent — is just clever ways to construct the messages array that gets sent in that request.

---

## The messages format

Every LLM API uses the same structure:

**You send:**
- `system` — sets the persona and rules. Invisible to the user, always processed first.
- `user` — the actual question or prompt
- Prior `assistant` + `user` turns (optional) — this is how you simulate conversation history

**You get back:**
- `assistant` — the model's response
- Token counts — input tokens consumed + output tokens generated

```python
messages = [
    {"role": "system", "content": "You are a concise assistant."},
    {"role": "user",   "content": "What is RAG?"},
]
```

This structure is universal. Anthropic, OpenAI, and most other providers use it.

---

## The three knobs

### 1. Model selection — the biggest lever

| Model tier | Examples | Use when |
|---|---|---|
| Frontier | Claude Sonnet, GPT-4o | Complex reasoning, nuanced writing |
| Small / fast | Claude Haiku, GPT-4o-mini | Simple tasks, high volume, cost-sensitive |

Same prompt on different models → wildly different quality, speed, and cost.
Rule: use the smallest model that gets the job done.

### 2. System prompt — the second biggest lever

- Controls tone, format, persona, constraints
- "Respond only in bullet points" genuinely changes output
- Most production issues trace back to a poorly written system prompt
- This is a first-class engineering artifact, not an afterthought

### 3. Temperature

#### What's actually happening

The model doesn't write a sentence — it predicts **one token at a time**. After each token it produces a probability distribution over its entire vocabulary. Temperature controls how that distribution is used to pick the next token.

After "The sky is":
```
"blue"      → 42%
"clear"     → 18%
"dark"      → 11%
"beautiful" → 8%
"grey"      → 6%
```

- **Temperature = 0.0** — always picks the highest probability token. Fully deterministic.
- **Temperature < 1.0** — distribution is sharpened. High-probability tokens dominate even more.
- **Temperature = 1.0** — use the distribution as-is.
- **Temperature > 1.0** — distribution is flattened. Unlikely tokens become competitive. Outputs get unpredictable.

#### When to use each range

| Range | Use case |
|---|---|
| `0.0` | SQL, JSON extraction, code, structured output |
| `0.1–0.3` | Q&A, summarization, factual tasks |
| `0.4–0.7` | Explanations, writing assistance, chat |
| `0.8–1.0` | Brainstorming, generating options, creative writing |
| `> 1.0` | Rarely useful — outputs become incoherent quickly |

#### The common misconception

Higher temperature ≠ smarter or more creative. It means **more random**. On a hard reasoning task, temperature 1.0 makes the model *worse* because it introduces randomness into token choices that should be deterministic. Reach for higher temperature only when variety is the explicit goal.

#### top_p (nucleus sampling)

Temperature has a sibling: `top_p`. Instead of scaling the whole distribution, it cuts off the tail — only tokens that together account for the top P% of probability are considered.

- `top_p=1.0` → all tokens considered (default)
- `top_p=0.9` → only the tokens making up the top 90% of probability mass

**Don't tune both at the same time.** Pick one and leave the other at its default. Adjusting both simultaneously makes it impossible to reason about what's causing output changes.

---

## Tokens

Tokens are not words. They are chunks of characters — roughly 3–4 characters, ~0.75 words each.

- You pay per token (input + output separately)
- The model's context window is measured in tokens
- Cost formula: `(input_tokens × input_price) + (output_tokens × output_price)`
- Log tokens on every call from Phase 01 onward — this becomes critical in Phase 05

---

## Why LLMs are stateless

Each API call is completely independent. The model has no memory of previous calls unless you explicitly include prior messages in the `messages` array. This is a fundamental constraint that drives the design of Phases 07 (memory) and beyond.

---

## What we built

`src/llm_chat.py` — a CLI tool and reusable module:

```bash
python src/llm_chat.py "What is RAG?"
python src/llm_chat.py "What is RAG?" --model claude-haiku-4-5
python src/llm_chat.py "What is RAG?" --system "Reply in one sentence" --temperature 0.2
```

### Libraries used

| Library | Purpose |
|---|---|
| `anthropic` | Official Anthropic SDK — handles auth, retries, response parsing |
| `python-dotenv` | Loads `.env` into environment variables |
| `argparse` | Parses CLI flags |

No frameworks. Raw SDK calls only — so every layer is visible.

### Design decision: module, not just a script

`llm_chat.py` exposes a callable function, not only a `__main__` block. Phase 04 imports it directly as a dependency. This forces clean separation between the interface and the logic from day one.

---

## Acceptance criteria

- [ ] `python src/llm_chat.py "What is RAG?"` returns a response
- [ ] Same prompt on Haiku vs Sonnet shows measurable quality/latency/cost difference
- [ ] System prompt visibly changes tone and format
- [ ] API keys loaded from `.env`, not hardcoded
- [ ] Token usage and estimated cost printed on every call
- [ ] Module is importable by later phases

---

## Reflection

*(Fill in after implementation)*

1.
2.
3.
4.
5.
