# Model Selection and Cost Strategy

## Free options

### Google AI Studio — best free starting point
- **Gemini 2.0 Flash** is free up to generous rate limits (1,500 requests/day)
- No credit card required to start
- Follows the same messages format — concepts transfer directly
- Limitation: switch to Anthropic for Phase 08 (MCP), since that protocol originated at Anthropic

### Groq — free tier, extremely fast
- Runs open-source models (Llama 3, Mixtral) on custom hardware
- Free tier with rate limits — sufficient for learning and experimentation
- Fast inference, good for iterating quickly
- Limitation: open-source models are noticeably weaker on tool-use (matters from Phase 04 onward)

### Ollama — local, completely free
- Runs on your own machine — no API calls, no cost ever
- Models: Llama 3.2, Mistral, Phi-3, etc.
- Limitation: needs ~8GB RAM minimum for a decent model; quality drops significantly vs frontier models on complex reasoning tasks

---

## Paid options — cost comparison

| Model | Input cost | Output cost | Sweet spot |
|---|---|---|---|
| Gemini 2.0 Flash | ~$0.075/MTok | ~$0.30/MTok | Phases 01–06, high volume |
| GPT-4o-mini | ~$0.15/MTok | ~$0.60/MTok | Good all-rounder |
| Claude Haiku 3.5 | ~$0.80/MTok | ~$4/MTok | Best tool-use quality at low cost |
| Claude Sonnet | ~$3/MTok | ~$15/MTok | Complex reasoning, use sparingly |
| GPT-4o | ~$2.50/MTok | ~$10/MTok | Complex reasoning, use sparingly |

**MTok = per million tokens**

For context: a typical learning session with 50–100 API calls costs **less than $0.10** on small models. The entire 11-phase learning path on small models costs roughly $5–10 total.

---

## Rule: use the smallest model that gets the job done

Reserve frontier models (Sonnet, GPT-4o) for:
- The explicit comparison exercise in Phase 01 acceptance criteria
- Tasks where small models demonstrably fail
- Nothing else

---

## Strategy for this learning path

**Phases 01–02:** Groq free tier (Llama 3.3 70B) + Ollama local (Llama 3.1 8B). Zero cost.
- Google AI Studio free tier is an alternative but has regional restrictions — Groq is more reliable
- Ollama on Apple Silicon (M1/M2/M3/M4) is fast enough for iteration and exploration

**Phase 03 onward:** Anthropic. Add $10 to your account — it will last the entire path.

Why Anthropic from Phase 03:
- MCP (Phase 08) originated at Anthropic — their SDK and docs are the reference implementation
- Claude is measurably better at tool-use (Phase 04)
- Haiku is cheap enough that $10 covers hundreds of sessions
- The consistency of using one primary provider makes debugging easier

**Never use a frontier model for routine calls during learning.** Only switch up when a phase explicitly requires comparing models.
