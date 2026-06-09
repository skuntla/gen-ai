# Core Concepts — Phase 04

## The problem Phase 03 leaves unsolved

Phase 03 measured **RAG quality** on `query()` — 33/60 passes (55%), known failures on chart numbers and some adversarial cases.

But the Stock Research Assistant is not "only RAG over one PDF." A real research question needs **different sources**:

| Question type | Right capability | Wrong default |
|---|---|---|
| "Who is the Infosys CEO?" (in AR) | Document search | Raw LLM memory |
| "Operating margin FY2025?" | Structured SQL | RAG over chart text |
| "YoY revenue growth FY24→FY25?" | SQL + calculator | LLM mental math |
| "Latest Infosys news?" | Web search | Stale annual report |
| "What did the chairman say about AI?" | RAG | SQL |

Phase 04 adds an **agent** — an LLM that chooses **tools** instead of answering everything from one pipeline.

---

## End goal: scorecard needs multiple capabilities

The project targets a **Buy / Hold / Avoid scorecard** from a ticker. No single tool covers all dimensions:

| Scorecard dimension | Primary tool (Phase 04) |
|---|---|
| Narrative, risks, governance (filings) | `search_docs` → `query()` |
| Profitability, growth, debt (numbers) | `text_to_sql` → `sample.db` |
| Derived percentages | `calculator` |
| Recent news / sentiment | `web_search` |

Phase 04 does **not** build the full scorecard yet. It builds **routing + loop** so those capabilities can be orchestrated in later phases.

---

## Workflow vs agent

**Workflow (you decide the steps):**

```
if "price" in question: run SQL
elif "news" in question: run web
else: run RAG
```

Brittle — language is messy; rules multiply.

**Agent (LLM decides):**

```
User question
    → LLM reads tool descriptions
    → LLM emits tool call (or final answer)
    → run tool → return result to LLM
    → repeat until done
```

Phase 04 implements the **agent** pattern with a small tool set and a max-iteration cap.

---

## The agent loop (ReAct-style)

```
┌─────────────────────────────────────────────────────────┐
│  1. User message                                         │
│  2. LLM → tool_call OR final text                        │
│  3. If tool_call → execute tool → append result to history│
│  4. Go to 2 (until final answer or max iterations)       │
└─────────────────────────────────────────────────────────┘
```

Each cycle:

- **Think** — model reasons about what it needs (often implicit in the tool call)
- **Act** — one tool invocation with arguments
- **Observe** — tool result appended to conversation for the next turn

**Max iterations (~10):** prevents infinite tool loops; production agents always cap this.

---

## Function calling / tool use

Modern LLMs expose **structured tool calls** — not free-text "Action: search_docs(...)" parsing.

You register tools with:

- **name** — e.g. `search_docs`
- **description** — natural language; **this is part of the prompt**
- **parameters** — JSON schema (query string, SQL string, expression, etc.)

The model returns either:

- **Assistant message** (done), or
- **Tool call** — `{name, arguments}`

Your code executes the tool and sends the result back as a **tool result message**.

Phase 04 uses raw SDK tool-use (Groq / Anthropic) — no LangChain.

---

## The four tools

### 1. `search_docs` — wraps Phase 02 RAG

```text
question → rag.query() → answer + sources
```

**Use when:** Question is about content in indexed PDFs (Infosys annual report).

**Do not use when:** Question needs live prices, latest news, or rows already in SQLite.

Phase 03 eval still tests `query()` directly. Phase 04 tests whether the **agent calls** this tool when appropriate.

---

### 2. `text_to_sql` — read-only SQL over `sample.db`

```text
question → LLM writes SELECT → execute (read-only) → rows as JSON/text
```

**Use when:** Precise numeric facts by period — margins, revenue, ROE, debt ratios, OHLC by date.

**Critical rule:** The agent **never writes** to the database. Only SELECT (or approved read paths).

**Who fills the database?** Not the LLM. Offline **seed script** (`scripts/seed_sample_db.py`) loads CSV / yfinance into SQLite — same pattern as `rag.py --index` for vectors.

| Pipeline | Fills | Query time |
|---|---|---|
| RAG index | PDF → chunks + FAISS | `search_docs` |
| SQL DB | CSV / API → seed script | `text_to_sql` |

---

### 3. `calculator` — safe math

```text
expression → ast-limited eval → number
```

**Use when:** Percentages, growth rates, weighted sums — arithmetic that must be exact.

**Do not use when:** The raw numbers are not yet fetched (call SQL or RAG first).

---

### 4. `web_search` — external current information

```text
query → Brave / Tavily API → snippets + URLs
```

**Use when:** Recent news, events after the annual report, sentiment headlines.

**Do not use when:** Answer is in the indexed AR or in `sample.db`.

Optional API key in Phase 04 — can stub or skip until key is available.

---

## Tool descriptions are secretly prompts

Routing quality depends more on **tool docstrings / descriptions** than on the user question.

Bad:

```text
search_docs: searches documents
```

Good:

```text
search_docs: Search Infosys annual report PDFs indexed by RAG.
Use for CEO, board, business description, risks, and narrative from filings.
Do NOT use for stock prices, latest news, or structured financial tables.
```

Wrong descriptions → wrong tool → right code, wrong behaviour. Phase 09 agent evals will test trajectories; Phase 04 tests manually with ~10 routing questions.

---

## What goes in `sample.db`

**Center of gravity: fundamental metrics** (what RAG handles poorly):

- Revenue, operating margin, net margin, ROE, debt/equity by fiscal year
- Optional: promoter holding by quarter
- Optional secondary table: **daily OHLC** for price/volume questions (via seed script + yfinance)

**Not the whole market** — Phase 04 uses Infosys-focused sample data for learning.

**Seeding approach:**

1. `data/seeds/infosys_financials.csv` — hand-curated from annual report / Screener
2. `scripts/seed_sample_db.py` — creates tables, loads CSV, optional yfinance for prices
3. Run once: `python scripts/seed_sample_db.py` before using the agent

---

## How Phase 04 connects to the rest of the project

```
Phase 01  llm_chat.chat()     generation inside agent loop
Phase 02  rag.query()         search_docs tool
Phase 03  RAG eval             keep — tests foundation, not routing
Phase 04  agent.py              tool routing + loop
Phase 05  traces                instrument every tool call
Phase 06  guardrails            block bad tickers, off-scope
Phase 07  memory                past INFY research sessions
Phase 08  MCP                   SQL tool extracted to portable server
Phase 09  agent_evals           "must call search_docs for CEO question"
Phase 10  swarm                 planner + researcher + writer agents
```

**Keep Phase 03 RAG eval.** Add agent behaviour tests later — different layer (see Phase 03 reflection).

---

## Three layers of behaviour (eval mindset)

| Layer | Question |
|---|---|
| Tool selection | Did it pick search_docs vs SQL vs web? |
| Tool execution | Did the tool return correct data? |
| Final answer | Did the user get a good synthesis? |

Phase 03 tested layer 3 on `query()` alone. Phase 04 focuses on **layer 1** manually; Phase 09 automates layers 1–3 on the full agent.

---

## What Phase 04 does and does not do

| Phase 04 does | Phase 04 does not |
|---|---|
| Route questions to four tools | Produce Buy/Hold/Avoid scorecard |
| Wrap `query()` as `search_docs` | Replace RAG eval |
| Read-only SQL on seeded DB | Live NSE feed or LLM-filled tables |
| Cap agent iterations | Full guardrails (Phase 06) |
| Interactive terminal chat | Multi-agent team (Phase 10) |

---

## Mental model

```
User: "What was Infosys operating margin in FY2025 and any recent news?"
        │
        ▼
   agent loop
        │
        ├── tool: text_to_sql  → SELECT margin FROM financials ...
        ├── tool: web_search   → recent Infosys headlines
        └── synthesise final answer with both
        │
        ▼
   Assistant message (citing tool results, not training memory)
```

---

## Implementation order (completed)

1. [design.md](design.md) — tool JSON schemas, DB schema, 10 routing test questions
2. [scripts/seed_sample_db.py](../../../scripts/seed_sample_db.py) + `data/seeds/*.csv` — `sample.db`
3. [src/agent.py](../../../src/agent.py) — four tools, agent loop, Groq recovery
4. [setup.md](setup.md) — Groq tool-use, Tavily key, routing tests
5. [code-walkthrough.md](code-walkthrough.md) + [teaching-guide.md](teaching-guide.md) — workshop docs
6. [reflection.md](reflection.md) + [questions.md](questions.md) — wrap-up and interview prep

**Verified:** 10/10 routing tests. See [README.md](README.md).

For production framework options later, see **Future: Strands migration** in [design.md](design.md).

---

## Key terms

| Term | Meaning |
|---|---|
| Tool / function | Callable capability the LLM can request |
| Tool description | Routing prompt — tells model when to use tool |
| Agent loop | Repeat: LLM → tool → result → LLM until done |
| Trajectory | Sequence of tool calls taken (evaluated in Phase 09) |
| Seed script | Offline job that fills SQLite — not part of agent runtime |
