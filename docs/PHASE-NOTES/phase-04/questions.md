# Interview Prep — Phase 04 (Agent)

Full question bank with detailed model answers from the Phase 04 interview walkthrough. Use this as a **reference sheet** before enterprise interviews.

Pair with [concepts.md](concepts.md) and [code-walkthrough.md](code-walkthrough.md).

**How to use:** Read the question, answer in your own words, then check **Model answer** and **Interview tip**.

---

## Quick reference — three lines to memorize

1. *"LLM proposes; Python executes with guards."*
2. *"RAG eval tests search quality; routing tests test the dispatcher."*
3. *"We don't claim no hallucinations — we claim auditable grounding for numbers."*

---

## Concept clarifications (read once)

### Tool `description` vs Python docstring

| | Tool `description` | Python docstring |
|---|---|---|
| What | String in `TOOLS` JSON schema | `"""..."""` on a function |
| Who reads it | **The LLM** (every API call) | Developers, IDEs |
| Purpose | **Routing prompt** — when to use tool, schema hints | Document code for humans |

In Phase 04 we hand-write descriptions in `TOOL_*` dicts. Frameworks (LangChain, Strands) may auto-copy docstrings — same intent, different wiring.

### The LLM does not execute tools

```
LLM → outputs tool_call (name + args)
  → Groq API parses it (or tool_use_failed)
  → Your Python execute_tool() runs the real code
  → JSON result back to LLM in role: tool message
```

The model **requests**; your application **executes**.

### Synthesis (debugging term)

| Layer | What | Example failure |
|---|---|---|
| Routing | Wrong tool chosen | `search_docs` for FY2025 margin |
| Tool args | Wrong SQL/parameters | `fiscal_year = 2025` |
| Tool output | Empty rows, DB error | 0 rows returned |
| **Synthesis** | Tool was right; **final answer wrong** | Tool: 21.1%, answer: "23%" |

### P95 / P99 latency

Percentile latency — tail behavior, not average.

- **p95 = 4s** → 95% of requests finish in ≤ 4s; 5% are slower.
- Averages hide outliers: 90 fast requests + 10 slow multi-tool requests look "fine" on average but hurt p95.
- Agent requests are multi-step (2–3 LLM calls + RAG + Tavily) — track **p95 end-to-end** and **per-tool spans**.

### Failure taxonomy

| Type | Example | Retry? |
|---|---|---|
| Tool-call syntax | `tool_use_failed`, XML-like tags | Parse `failed_generation` or retry Groq |
| Bad tool args | Wrong `fiscal_year` format | Model may fix next loop iteration |
| Tool execution | SQLite error, missing index | Fix data/code; retry if transient |
| Provider API | Groq 429, Tavily timeout | Backoff, quota |
| Synthesis | Correct JSON, wrong final text | Output validation (Phase 06), not tool retry |

---

# Easy (Questions 1–6)

## Q1. What is an AI agent, in one sentence? How is it different from a chatbot that always calls RAG?

**Model answer:**

An AI agent is an LLM that **decides which actions to take** — calling tools in a loop until it has enough grounded information to answer. A RAG-only chatbot always runs the same pipeline: embed → retrieve → generate. An agent might call RAG for narrative, SQL for structured metrics, a calculator for math, or web search for news — **depending on the question**, not a fixed rule in code.

**Interview tip:** Don't say "agent = list of tools." Say **LLM + loop + tool choice**.

**Weak answer to avoid:** "An agent is a collection of tools."

---

## Q2. Describe the agent loop in four steps. When does it stop?

**Model answer:**

1. **Think** — LLM reads user question, system prompt, prior tool results; decides next move.
2. **Act** — LLM requests a tool call (name + arguments).
3. **Observe** — Python executes the tool; JSON result appended to conversation.
4. **Repeat or finish** — LLM thinks again: another tool, or final plain-text answer.

**Stops when:**
- Model returns **final message with no `tool_calls`** (happy path), or
- **`MAX_ITERATIONS`** (e.g. 10) is reached (circuit breaker).

**Interview tip:** This is **ReAct**: Reason → Act → Observe → loop.

---

## Q3. Who decides which tool to use? What three things influence that decision?

**Model answer:**

**The LLM decides.** Python does not contain `if "CEO" in question: use search_docs`.

**Three influences:**
1. **System prompt** — high-level routing ("margins → SQL", "news → web_search", Infosys-only scope).
2. **Tool descriptions** — per-tool when-to-use / when-not-to-use + schema hints.
3. **User question** — model maps intent to a tool.

Python **registers** tools and **executes** what the model requests.

---

## Q4. Name the four tools and one example question each.

| Tool | Example question |
|---|---|
| `search_docs` | "Who is the CEO of Infosys?" / "What did the chairman say about AI?" |
| `run_sql` | "What was Infosys revenue in FY2025?" |
| `calculate` | "What is 17% of 842?" |
| `web_search` | "What are the latest Infosys news headlines?" |

**Multi-tool example:** "What is 50% of Infosys quarterly revenue?" → `run_sql` (fetch revenue) → `calculate` (`revenue * 0.5`).

---

## Q5. Why do tools return JSON strings instead of the LLM querying the DB/PDF directly?

**Model answer:**

1. **Chat API contract** — tool results are `role: tool` message **text**; JSON is structured text the LLM can parse and cite.
2. **Separation of concerns** — LLM chooses; **your code executes** with validation, limits, and auditability.
3. **Security** — model never gets raw DB credentials or arbitrary SQL execution; `validate_sql()` enforces SELECT-only.
4. **Cost** — RAG/embeddings run only when `search_docs` is called, not on every turn.

**Interview tip:** The LLM does not "dynamically build code." It emits a **tool call**; predefined Python functions run.

---

## Q6. What does `MAX_ITERATIONS = 10` protect you from?

**Model answer:**

| Risk | How cap helps |
|---|---|
| **Infinite tool loops** | Model keeps calling tools without answering |
| **Runaway cost** | Each iteration = another LLM bill (+ tools) |
| **Hung sessions** | User waits forever — bad SLA |
| **Bad UX / tail latency** | Multi-tool chains without termination |

**Interview tip:** Call it a **circuit breaker** — guarantees the session ends.

---

# Medium (Questions 7–13)

## Q7. "Tool descriptions are secretly another prompt." What does that mean? Give a real example.

**Model answer:**

The `description` field in each tool schema is sent to the LLM on **every** API call. It is **routing instructions disguised as API metadata** — not just documentation for developers.

**Real example (this project):**
- Before: `run_sql` description didn't specify `fiscal_year` format.
- Model wrote `fiscal_year = 2025` → **0 rows**.
- After: added `fiscal_year is TEXT like 'FY2025'` → correct SQL → **21.1% margin**.

Same DB, same code — only the description changed behavior.

---

## Q8. How does the LLM know the database schema? What if the hint is wrong?

**Model answer:**

From the **`run_sql` tool description** (tables, columns, formats) — **not** from `PRAGMA table_info` or opening SQLite.

**When hints are wrong or incomplete:**

| Failure | LLM sees | Behavior |
|---|---|---|
| Wrong format | `{"rows": [], "row_count": 0}` | Retry or "not available" |
| Wrong column | `{"error": "no such column: foo"}` | May fix SQL next iteration |
| Blocked SQL | `{"error": "Only SELECT..."}` | Should not repeat attack |

**Two sources of truth:** `seed_sample_db.py` (ground truth) vs tool description (what LLM sees). Drift = silent bugs.

**Production upgrade:** read-only `get_schema()` tool; sync descriptions from DDL.

---

## Q9. Why two tools for "YoY revenue growth FY2024 to FY2025"?

**Model answer:**

| Step | Tool | Guarantees |
|---|---|---|
| 1 | `run_sql` | Grounded facts: FY2024 `153656`, FY2025 `165641` crore |
| 2 | `calculate` | Deterministic math: `(165641 - 153656) / 153656 * 100` → **7.80%** |

**Why not one tool or mental math?**
- LLM mental math uses training memory — wrong revenue, wrong %, not auditable.
- Two tools = inspectable trajectory: SQL rows → expression → result.

---

## Q10. Why is `run_sql` SELECT-only? What incidents does it prevent?

**Model answer:**

**Code-level enforcement** in `validate_sql()` — not prompt-only. Defense in depth: prompt says SELECT + Python blocks bad SQL.

**Prevents:**
- `DELETE FROM financials` — data wipe
- `INSERT` — data poisoning
- `DROP TABLE` — schema destruction
- `SELECT 1; DROP TABLE ...` — multi-statement injection (also blocked)

Plus: max 100 rows, forbidden keywords, no multi-statement.

**Interview tip:** "Users can prompt-inject; tool-level guards are mandatory for any agent with DB access."

---

## Q11. Why a dedicated `calculate` tool instead of LLM mental math?

**Model answer:**

| Reason | Detail |
|---|---|
| **Determinism** | `842 * 17 / 100` always `143.14` via `ast` eval |
| **Auditability** | `--verbose` shows exact expression after SQL rows |
| **Separation** | `run_sql` = facts; `calculate` = math |
| **Safety** | Whitelisted `ast` nodes — not open `eval()` |

LLMs are unreliable calculators — critical for finance use cases.

---

## Q12. User asks "What is TCS revenue?" — correct behavior?

**Model answer:**

| Do | Don't |
|---|---|
| Politely refuse — Infosys-only scope | Call `run_sql` hoping TCS exists |
| **No tool calls** | `web_search` and present unsourced number |
| Explain data limit | Invent TCS revenue from training memory |

Enforced via **system prompt** now; **input guardrails** in Phase 06.

**Why model tried `run_sql` initially:** DB exists; model wants to help — scope must be explicit.

---

## Q13. Why does `web_search` return a stub when no API key is set?

**Model answer:**

**Graceful degradation** — enterprise pattern:

| Benefit | Why |
|---|---|
| Loop continues | Other tools still work |
| Tool stays registered | Routing to `web_search` still testable/teachable |
| Dev/staging | Not every env needs Tavily day one |
| Clear ops signal | `stub: true` → set `TAVILY_API_KEY` |

**vs crash:** one missing key kills entire agent.  
**vs remove tool:** model can't learn news → web_search routing.

---

# Difficult (Questions 14–19)

## Q14. PM wants fixed pipeline: always SQL → calculate → answer. Agent or workflow?

**Model answer:**

| Choose **workflow** | Choose **agent** |
|---|---|
| Same steps every time (nightly report) | Mixed intents: CEO, margin, news, math |
| Compliance needs fixed audit path | Exploratory analyst chat |
| One question type (always YoY) | User phrasing varies |
| Minimize LLM calls / cost | Tool count depends on question |

**Hybrid:** agent for routing + workflow templates for known report types.

**Interview line:** "If 90% of traffic is one report shape, workflow it. If users ask anything, agent it."

---

## Q15. Stakeholder: "Wrong margin." No verbose logs. Debug order?

**Model answer — 7-step ladder:**

| Order | Layer | Question |
|---|---|---|
| 1 | Reproduce | Same question + `--verbose` |
| 2 | Routing | Wrong tool? (`search_docs` vs `run_sql`) |
| 3 | Tool args | SQL correct? (`FY2025` vs `2025`) |
| 4 | Tool output | Empty rows? Error JSON ignored? |
| 5 | Ground truth | Seed/DB actually has 21.1%? |
| 6 | Synthesis | Tool said 21.1, answer said 23? |
| 7 | Prompts | System prompt / tool description misleading? |

Most bugs are **layers 3–4**, not "retrain the model." Phase 05 adds traces so this ladder runs in production.

---

## Q16. Why keep Phase 03 RAG eval AND Phase 04 routing tests?

**Model answer:**

| | Phase 03 (`query()`) | Phase 04 (agent routing) |
|---|---|---|
| Tests | Chunking, retrieval, RAG answer quality | Tool choice, loop, orchestration |
| Catches | Bad chunks, Retail failure, citations | CEO→`search_docs`, margin→`run_sql`, TCS refuse |
| Misses | Wrong tool (always RAG) | Bad RAG *if* agent correctly chose `search_docs` |

**Examples:**
- Agent routes CEO to `search_docs` ✓ but RAG wrong page ✗ → **only Phase 03 catches**
- RAG excellent ✓ but agent uses `run_sql` for CEO ✗ → **only Phase 04 catches**

Phase 09 automates agent trajectory eval in CI.

---

## Q17. Groq `tool_use_failed` — whose problem? Defensive agent design?

**Model answer:**

Model emits malformed tool syntax (e.g. `<function=search_docs{...}</function>`). Groq API rejects it → `tool_use_failed` with `failed_generation`.

| Bucket | Verdict |
|---|---|
| Model | Bad format |
| API | Strict parser; gives recovery hint |
| **Your app** | **Must handle it** |

**Defensive design:**
1. Parse `failed_generation` and execute tool (what we do)
2. `parallel_tool_calls=False`
3. `MAX_ITERATIONS` circuit breaker
4. Retry Groq with backoff on 429/5xx (separate from syntax)
5. Log recovery rate (Phase 05)
6. Don't assume one provider — tool-calling quality varies

**Interview line:** "Hosted tool-calling isn't reliably contractible — recover, degrade, measure."

---

## Q18. What metrics to track (Phase 05) before optimizing routing?

**Model answer — minimum set:**

| Metric | Why |
|---|---|
| **Iterations per request** | Loop depth |
| **Tokens in/out per LLM turn** | Cost driver |
| **Cost / $ per successful request** | Unit economics |
| **End-to-end latency (p50, p95, p99)** | User SLA; tail matters |
| **Per-tool latency** | LLM vs RAG embed vs SQL vs Tavily |
| **Tool error / recovery rate** | `tool_use_failed`, empty SQL, stubs |
| **Tools per request** | Routing efficiency |

Optimize what traces **prove** is expensive.

---

## Q19. Bank pitch: "How do we know it won't hallucinate revenue?"

**Model answer:**

**Lead with provenance, not prompts:**

| Today | Claim |
|---|---|
| Routing | Revenue questions → `run_sql`, not `search_docs` or memory |
| Grounding | `financials.revenue_cr` from curated seed — auditable SQLite rows |
| Math | `calculate` on fetched values — not mental math |
| Scope | Infosys-only; refuse out-of-scope without tools |
| Safety | SELECT-only SQL |
| Audit | Trace: tool → SQL → rows → final text (catch synthesis bugs) |
| Testing | Phase 03 RAG eval + Phase 04 routing 10/10 |

**Honest limits (builds trust):**

| Not yet | Phase |
|---|---|
| Production trace dashboard | 05 |
| Automated groundedness judge every answer | 06 |
| CI trajectory eval | 09 |
| Synthesis can misread correct tool output | Mitigate with traces + output validation |

**Closer:**

> "We don't promise zero hallucination — we promise **verifiable provenance** for numbers: SQL you can replay and rows you can inspect. Prompts reduce routing errors; tools and audit trails reduce fabricated revenue. LLM-as-judge is a second line of defense, not the first."

---

# Appendix — Tool reference

| Tool | Grounds in | Returns |
|---|---|---|
| `search_docs` | FAISS + PDF (`rag.query`) | `{answer, sources, latency_ms}` |
| `run_sql` | `data/sample.db` | `{columns, rows}` or `{error}` |
| `calculate` | Deterministic `ast` eval | `{result, expression}` or `{error}` |
| `web_search` | Tavily API | `{results, answer}` or `{stub: true}` |

---

# Appendix — Routing test suite (10 questions)

| # | Question | Expected tool(s) |
|---|---|---|
| 1 | Who is the CEO of Infosys? | `search_docs` |
| 2 | Infosys revenue FY2025 (₹ crore)? | `run_sql` |
| 3 | Operating margin FY2025? | `run_sql` |
| 4 | INFY close on 2026-06-05? | `run_sql` |
| 5 | What is 17% of 842? | `calculate` |
| 6 | YoY revenue growth FY2024→FY2025? | `run_sql` + `calculate` |
| 7 | Latest Infosys news headlines? | `web_search` |
| 8 | Chairman on AI strategy? | `search_docs` |
| 9 | What is TCS revenue? | refuse (no tools) |
| 10 | Promoter holding latest quarter? | `run_sql` |

**Pass criteria:** ≥ 8/10 correct primary tool + reasonable answer + loop terminates. **Verified: 10/10.**

---

# Self-score rubric (from interview practice)

| Tier | Focus areas to improve |
|---|---|
| Easy | Define agent as LLM + loop + choice; exit conditions for loop |
| Medium | Code vs prompt guardrails; complete multi-part answers |
| Difficult | Bank pitch = provenance first; workflow vs agent decision table; p95 tail latency |

**Practice command:**

```bash
python src/agent.py --verbose "Your question here"
```

See [setup.md](setup.md) for full environment and troubleshooting.
