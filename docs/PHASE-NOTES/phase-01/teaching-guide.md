# Teaching Guide — Phase 01 (Talk to an LLM)

A sequenced workshop plan for teaching Phase 01 end to end. Use this as the **master flow**; drill into linked docs for depth.

**Audience:** Developers new to LLM APIs (basic Python required).  
**Artifact:** `src/llm_chat.py`  
**Project context:** Foundation of the **Stock Research Assistant** — all later phases call `chat()`.

---

## Learning outcomes

By the end, learners can:

1. Describe an LLM as an HTTP API with a `messages` array — not magic
2. Explain system vs user roles, tokens, and statelessness
3. Run `llm_chat.py` from the CLI and interpret token/cost/latency output
4. Change behaviour with system prompt and temperature (with predictable effects)
5. Switch providers via `.env` without changing caller code
6. Explain why `chat()` is a module — not just a script — for Phases 02–04

---

## Session map (suggested ~3–4 hours)

| Block | Part | Topic | Time |
|---|---|---|---|
| 1 | Concepts | Project context; LLM as HTTP API | 20 min |
| 2 | Concepts | Messages format; system prompt | 30 min |
| 3 | Concepts | Tokens, cost, statelessness | 30 min |
| 4 | Concepts | Temperature and model choice | 25 min |
| 5 | Setup | API keys, `.env`, first call | 25 min |
| 6 | Implementation | `llm_chat.py` structure and `chat()` | 45 min |
| 7 | Live lab | CLI experiments | 40 min |
| 8 | Wrap-up | Provider abstraction, Phase 02 teaser | 20 min |

Blocks 1–4 = **Part 1 (Concepts)**. Blocks 5–8 = **Part 2 (Setup + implementation + lab)**.

---

# Part 1 — Concepts (teach before coding)

## Block 1 — Project context and LLM as API (20 min)

**Goal:** Frame Phase 01 inside the 11-phase arc; demystify LLMs.

**Talking points:**

- End goal: stock ticker → research → Buy/Hold/Avoid scorecard
- Phase 01: **simplest possible thing** — send financial text, get text back
- No RAG, no tools, no memory — just the API
- Engineering view: **HTTP request → JSON in, JSON out**; intelligence is on provider servers

**Draw:**

```
Your code  ──HTTP──▶  Groq / Anthropic / Ollama  ──▶  model weights (their servers)
         ◀── JSON response (assistant message + token counts)
```

**Checkpoint:** Is the LLM "remembering" your last call?

**Read:** [concepts.md](concepts.md) (project context, engineering perspective)

---

## Block 2 — Messages format and system prompt (30 min)

**Goal:** Universal structure used in every later phase.

**Talking points:**

```python
messages = [
    {"role": "system", "content": "You are a financial analyst..."},
    {"role": "user",   "content": "What is Infosys's business?"},
]
```

- **system** — persona, rules, format; processed first; user doesn't see it
- **user** — the question
- **assistant** (in history) — prior turns you re-send for "conversation"
- Same shape for Anthropic, OpenAI, Groq — only SDK wrapper differs

**Live thought experiment (no code):**

- System: "Answer in exactly one sentence." vs default analyst prompt
- Same user question → visibly different output length and shape

**Checkpoint:** What is the difference between system and user messages?

**Read:** [concepts.md](concepts.md) (messages format, system prompt)

---

## Block 3 — Tokens, cost, statelessness (30 min)

**Goal:** Build habits that matter in Phase 05 (observability).

**Talking points:**

- **Token** ≈ 3–4 characters, ~0.75 words — billing unit, not words
- Bill **input** and **output** separately
- **Context window** = max tokens model can see at once (shapes RAG in Phase 02)
- **Stateless:** each call is independent — no memory unless you resend history
- Phase 07 (Memory) exists because of this constraint

**Formula (whiteboard):**

```
cost = (input_tokens × input_price + output_tokens × output_price) / 1000
```

**Checkpoint:** Why log tokens from Phase 01, not Phase 05?

**Read:** [concepts.md](concepts.md) (tokens, statelessness), [model-cost.md](model-cost.md)

---

## Block 4 — Temperature and model choice (25 min)

**Goal:** Three knobs — model, system prompt, temperature.

**Talking points:**

- **Temperature 0.0–0.2** — factual, extraction, finance (our default ~0.1)
- **Higher temperature** — more random, **not** smarter; bad for precise answers
- **top_p** — alternative to temperature; don't tune both aggressively
- **Model trade-off:** quality vs latency vs cost (70B cloud vs 8B local)

**Checkpoint:** Higher temperature = better reasoning — true or false?

**Read:** [temperature.md](temperature.md), [model-cost.md](model-cost.md)

**Optional:** [local-models.md](local-models.md) if cohort wants Ollama demo

---

# Part 2 — Setup, code, and hands-on

## Block 5 — Setup (25 min)

**Goal:** Everyone has a working API key and `.env`.

**Recommended path:** Groq (free, no card) — [setup.md](setup.md)

```bash
cp .env.example .env
# Add GROQ_API_KEY=...
pip install -r requirements.txt
```

**Verify:**

```bash
python src/llm_chat.py "Say hello in one sentence."
```

**Expect:** response + token line + latency + cost ($0 on Groq free tier)

**Emphasise:** `.env` is gitignored — never commit keys

**Read:** [setup.md](setup.md)

---

## Block 6 — Walk through `llm_chat.py` (45 min)

**Goal:** Map concepts to code; teach module design for reuse.

**Use as script:** [code-walkthrough.md](code-walkthrough.md) Steps 0–7

**File structure to cover:**

```
llm_chat.py
├── PRICING + DEFAULT_SYSTEM
├── _call_groq / _call_ollama / _call_anthropic   ← provider-specific SDK
├── chat()                                         ← public API (all phases use this)
├── _print_result()
└── if __name__ == "__main__"                      ← CLI only
```

**Design decisions (teach explicitly):**

| Decision | Why |
|---|---|
| Provider from `.env` | Switch Groq → Anthropic without code change |
| `chat()` returns dict | `response`, tokens, cost, latency — same shape always |
| Module + CLI | Phase 02 `rag.py` imports `chat()` — no subprocess |
| Token logging day one | Observability habit before Phase 05 |
| Raw SDKs, no LangChain | Every layer visible |

**Walk `chat()` routing:**

```
provider = groq | ollama | anthropic
    → matching _call_*()
    → uniform return dict
```

**Read:** [code-walkthrough.md](code-walkthrough.md), [design.md](design.md)

---

## Block 7 — Live lab (40 min)

**Goal:** Learners **feel** the knobs; collect numbers for discussion.

**Exercise 1 — Baseline financial prompt:**

```bash
python src/llm_chat.py "What is the promoter holding trend for TCS?"
```

Note: tokens, latency — answer may be from **training data**, not live filings (tease Phase 02)

**Exercise 2 — System prompt changes output:**

```bash
python src/llm_chat.py "Summarise Infosys's latest business highlights." \
  --system "You are a financial analyst. Reply in exactly one sentence."

python src/llm_chat.py "Summarise Infosys's latest business highlights."
```

Compare **output tokens** (design.md: 356 → 28 in acceptance run)

**Exercise 3 — Temperature:**

```bash
python src/llm_chat.py "List three risks for Infosys." --temperature 0.0
python src/llm_chat.py "List three risks for Infosys." --temperature 0.9
```

Same prompt — discuss consistency vs variety

**Exercise 4 — Model / provider (optional):**

```bash
python src/llm_chat.py "Is Infosys a good investment?" --provider groq --model llama-3.3-70b-versatile
python src/llm_chat.py "Is Infosys a good investment?" --provider groq --model llama-3.1-8b-instant
```

Compare latency and answer quality

**Exercise 5 — Import from Python (Phase 02 preview):**

```bash
python -c "
from dotenv import load_dotenv; load_dotenv()
import sys; sys.path.insert(0, 'src')
from llm_chat import chat
r = chat('Who is the CEO of Infosys?')
print(r['response'][:200])
print(r['input_tokens'], r['output_tokens'], r['latency_ms'])
"
```

**Discussion:** Why might "CEO of Infosys" be wrong or outdated without documents?

---

## Block 8 — Wrap-up (20 min)

**Goal:** Close Phase 01; motivate Phase 02.

**Key lessons to land:**

1. LLM = API + messages + tokens — everything later is message construction
2. System prompt is engineering, not fluff
3. Stateless — you own conversation history until Phase 07
4. `chat()` is the shared dependency — protect its interface
5. Training-data answers are unverifiable for **your** documents → need RAG

**Assessment:** [questions.md](questions.md) — pick 5–8 concepts + temperature section

**Phase 02 teaser:** "Next: give the LLM *your* Infosys PDF instead of training memory."

**Note:** [reflection.md](reflection.md) is a template — encourage learners to fill five bullets after lab

---

## Instructor checklist

**Before session:**

- [ ] Python 3.10+ and venv ready
- [ ] `.env.example` copied; Groq keys working
- [ ] `pip install -r requirements.txt` done
- [ ] One demo run of `llm_chat.py` tested
- [ ] (Optional) Ollama running if demonstrating local models

**Materials to have open:**

| Role | Doc |
|---|---|
| Concept flow | [concepts.md](concepts.md) |
| Code script | [code-walkthrough.md](code-walkthrough.md) |
| Design decisions | [design.md](design.md) |
| Setup troubleshooting | [setup.md](setup.md) |
| Temperature deep dive | [temperature.md](temperature.md) |
| Oral review | [questions.md](questions.md) |

---

## Common pitfalls when teaching

| Pitfall | Correction |
|---|---|
| "The model remembers my last question" | Stateless — each call is fresh |
| "More temperature = better answers" | More random; use low T for finance |
| "Tokens = words" | ~0.75 words per token; count matters for cost |
| "We can skip system prompt" | Default system prompt still shapes behaviour |
| "Hardcode the model in code" | Use `.env`; callers use `chat()` unchanged |
| "Phase 01 answers are ground truth for filings" | Training cutoff + hallucination → Phase 02 RAG |

---

## Optional extensions (extra session)

| Topic | Doc |
|---|---|
| Local models with Ollama | [local-models.md](local-models.md) |
| Full model pricing strategy | [model-cost.md](model-cost.md) |
| Anthropic setup for Phase 03+ | [setup.md](setup.md), [model-cost.md](model-cost.md) |

---

## Connection to later phases

| Phase 01 concept | Used later in |
|---|---|
| `chat()` function | Phase 02 `query()`, Phase 04 agent |
| Token/cost/latency dict | Phase 03 eval metrics, Phase 05 observability |
| System prompt | Phase 02 grounding prompt in RAG |
| Provider routing via `.env` | Phase 03 eval provider configs |
| Messages array | Every agent turn in Phase 04+ |

---

## One-page flow (printable)

```
PHASE 01 TEACHING FLOW
══════════════════════

PART 1 — CONCEPTS
  1. Stock Research Assistant arc; Phase 01 = raw API
  2. LLM as HTTP API — JSON messages in/out
  3. system / user / assistant roles; system prompt power
  4. Tokens, cost formula, statelessness
  5. Temperature + model choice (quality/speed/cost)

PART 2 — IMPLEMENTATION
  6. Setup: Groq key, .env, pip install
  7. Walk llm_chat.py: _call_* → chat() → CLI
  8. LIVE: financial prompt + token output
  9. LIVE: system prompt → shorter output
 10. LIVE: temperature 0.0 vs 0.9
 11. LIVE: import chat() from Python
 12. Teaser: training data ≠ your PDFs → Phase 02 RAG

ARTIFACT: src/llm_chat.py
NEXT: Phase 02 — RAG over infosys-ar-26.pdf
```

---

## Related teaching guides

| Phase | Guide |
|---|---|
| Phase 02 — RAG | [../phase-02/teaching-guide.md](../phase-02/teaching-guide.md) |
| Phase 03 — Eval | [../phase-03/teaching-guide.md](../phase-03/teaching-guide.md) |
