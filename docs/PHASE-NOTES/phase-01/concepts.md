# Core Concepts — Phase 01

## Project context

This phase is the starting point of a **Stock Research Assistant** for Indian equities. By the end of all 11 phases, the system will take a stock ticker, research it across multiple dimensions, and produce an investment scorecard (Buy / Hold / Avoid).

Phase 01 is deliberately simple: call the LLM with a raw piece of financial text and observe what it returns. No tools, no retrieval, no schema. Just the API.

---

## What an LLM actually is (from an engineering perspective)

Every LLM provider — Anthropic, OpenAI, Google — exposes their model as an **HTTP API**. You send a JSON payload, you get a JSON response back. The intelligence lives on their servers. You are making web requests.

Everything else in this learning path — RAG, agents, memory, multi-agent — is just clever ways to construct the messages array that gets sent in that request.

---

## The messages format

Every major LLM API uses the same structure:

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

This structure is universal across Anthropic, OpenAI, and most other providers.

---

## The system prompt

- Controls tone, format, persona, and constraints
- "Respond only in bullet points" genuinely changes output
- Most production issues trace back to a poorly written system prompt
- Treat it as a first-class engineering artifact, not an afterthought

---

## Tokens

Tokens are not words. They are chunks of characters — roughly 3–4 characters, ~0.75 words each.

- You pay per token: input tokens and output tokens are billed separately
- The model's context window (how much it can "see" at once) is measured in tokens
- Cost formula: `(input_tokens × input_price) + (output_tokens × output_price)`
- Log token usage on every call from Phase 01 onward — this becomes critical in Phase 05

---

## Why LLMs are stateless

Each API call is completely independent. The model has no memory of previous calls unless you explicitly include prior messages in the `messages` array.

This is a fundamental constraint that shapes every design decision in later phases:
- Phase 07 (Memory) exists entirely because of this
- "Conversation history" is just appending old messages to the next request
- The context window fills up — you eventually have to decide what to keep and what to drop
