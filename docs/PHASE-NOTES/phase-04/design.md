# Design — Phase 04

## What we will build

`src/agent.py` — an interactive terminal agent that routes Stock Research Assistant questions to four tools via a capped agent loop.

Supporting artifacts:

```bash
python scripts/seed_sample_db.py          # offline — fill SQLite
python src/agent.py                       # interactive REPL
python src/agent.py "one-shot question"   # single turn (optional)
```

---

## Architecture

```
User question
      │
      ▼
agent.py — agent loop (max 10 iterations)
      │
      ├── LLM with tool definitions (Groq tool use — see Provider)
      │
      ├── search_docs(question)     → rag.query()
      ├── run_sql(sql)              → sample.db (SELECT only)
      ├── calculate(expression)     → safe math eval
      └── web_search(query)         → Tavily API (optional key)
      │
      ▼
Final assistant message
```

**Important:** Phase 04 agent loop calls the **Groq SDK with `tools=`** directly. `llm_chat.chat()` remains the generation path inside `rag.query()` — we do not extend `chat()` with tool-use in Phase 04 (keeps Phase 01–03 stable).

---

## Provider choice (Phase 04)

| Setting | Value |
|---|---|
| Default | Groq `llama-3.3-70b-versatile` (supports tool / function calling) |
| Fallback | Anthropic Claude via SDK if `LLM_PROVIDER=anthropic` (Phase 03+ path) |
| Not for agent loop | Ollama — skip for Phase 04 routing tests (tool-use support varies) |

Embeddings unchanged — OpenAI via `rag.query()` only inside `search_docs`.

---

## Agent loop (raw SDK)

```python
MAX_ITERATIONS = 10

messages = [
    {"role": "system", "content": AGENT_SYSTEM_PROMPT},
    {"role": "user", "content": user_question},
]

for _ in range(MAX_ITERATIONS):
    response = groq_client.chat.completions.create(
        model=model,
        messages=messages,
        tools=TOOL_DEFINITIONS,
        tool_choice="auto",
    )
    msg = response.choices[0].message

    if not msg.tool_calls:
        return msg.content   # done

    messages.append(msg)     # assistant message with tool_calls
    for tc in msg.tool_calls:
        result = execute_tool(tc.function.name, json.loads(tc.function.arguments))
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": result,
        })

return "Agent stopped: max iterations reached."
```

Log each tool name + args + latency for Phase 05 traces.

---

## Tool definitions

Tools are registered as JSON schemas passed to the LLM. **Descriptions are routing prompts** — write them carefully.

### 1. `search_docs`

**Purpose:** Grounded Q&A over indexed Infosys annual report (Phase 02 RAG).

**When the model should use it:** CEO, chairman, business description, risks, narrative from `infosys-ar-26.pdf`.

**When not:** Stock prices, structured FY tables, latest news, math.

```python
{
    "type": "function",
    "function": {
        "name": "search_docs",
        "description": (
            "Search the Infosys FY2026 annual report PDF indexed by RAG. "
            "Use for management names, business segments, risks, and prose from filings. "
            "Do NOT use for live stock prices, latest news, or precise tabular metrics "
            "that belong in the financials database."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Natural language question to run against the document index.",
                }
            },
            "required": ["question"],
        },
    },
}
```

**Implementation:**

```python
def search_docs(question: str) -> str:
    result = query(question=question, top_k=5)
    # Return JSON or formatted text: answer + sources for LLM synthesis
```

---

### 2. `run_sql`

**Purpose:** Read-only queries on `data/sample.db`.

**When:** Operating margin, revenue, ROE, D/E, promoter %, OHLC by date — structured Infosys metrics.

**When not:** Narrative from PDF, news, pure math without DB rows.

```python
{
    "type": "function",
    "function": {
        "name": "run_sql",
        "description": (
            "Run a read-only SQL SELECT against the Infosys financial SQLite database. "
            "Use for numeric metrics by fiscal year or quarter, shareholding, and daily OHLC prices. "
            "Tables: financials, shareholding, daily_prices. "
            "Do NOT use for narrative text from the annual report or current news."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "A single SELECT statement. No INSERT, UPDATE, DELETE, or DDL.",
                }
            },
            "required": ["sql"],
        },
    },
}
```

**Safety (required):**

- Reject unless SQL strip-uppercase starts with `SELECT`
- Reject if contains `;` followed by another statement (no multi-statement)
- Optional: `LIMIT` enforced (e.g. max 100 rows)
- Return rows as JSON string or markdown table

**Note:** Tool name `run_sql` in design; LLM writes SQL. Alternative pattern: `text_to_sql` with natural language handled inside tool — Phase 04 keeps SQL visible for teaching.

---

### 3. `calculate`

**Purpose:** Deterministic arithmetic.

```python
{
    "type": "function",
    "function": {
        "name": "calculate",
        "description": (
            "Evaluate a safe arithmetic expression (numbers, + - * / % parentheses). "
            "Use after fetching values from run_sql when computing growth rates, ratios, or percentages. "
            "Do NOT use to look up facts — use run_sql or search_docs first."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Math expression e.g. '(178650 - 163000) / 163000 * 100'",
                }
            },
            "required": ["expression"],
        },
    },
}
```

**Implementation:** `ast`-based safe eval (numbers and operators only) — no `eval()`.

---

### 4. `web_search`

**Purpose:** Recent external information.

```python
{
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the web for recent Infosys news, events, and headlines not in the annual report. "
            "Use when the user asks about latest news, recent announcements, or post-filing events. "
            "Do NOT use for facts inside the indexed PDF or financials database."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query, e.g. 'Infosys news 2026'.",
                }
            },
            "required": ["query"],
        },
    },
}
```

**Implementation:** Tavily API if `TAVILY_API_KEY` set; otherwise return a clear stub message so agent loop still runs without key.

---

## Agent system prompt (sketch)

```text
You are a Stock Research Assistant for Indian equities (Infosys focus in Phase 04).

Use tools — do not answer from memory when a tool can provide grounded data.
- Filings and narrative → search_docs
- Structured numbers and prices in DB → run_sql
- Arithmetic on known numbers → calculate
- Recent news → web_search

Cite which tool you used. If tools cannot answer, say so clearly.
```

---

## SQLite schema — `data/sample.db`

Single symbol focus: **INFY** (Infosys). Populated offline by `scripts/seed_sample_db.py`.

### Table: `financials`

Annual / key metrics — **scorecard core** (numbers RAG often gets wrong).

| Column | Type | Example |
|---|---|---|
| `symbol` | TEXT | `INFY` |
| `fiscal_year` | TEXT | `FY2025` |
| `revenue_cr` | REAL | `178650` |
| `operating_margin_pct` | REAL | `21.1` |
| `net_margin_pct` | REAL | `16.8` |
| `roe_pct` | REAL | `32.1` |
| `debt_to_equity` | REAL | `0.05` |

Primary key: `(symbol, fiscal_year)`.

### Table: `shareholding`

| Column | Type | Example |
|---|---|---|
| `symbol` | TEXT | `INFY` |
| `quarter` | TEXT | `Q4 FY2025` |
| `promoter_pct` | REAL | `14.6` |
| `fii_pct` | REAL | `31.2` |

### Table: `daily_prices` (optional, via yfinance in seed script)

| Column | Type | Example |
|---|---|---|
| `symbol` | TEXT | `INFY` |
| `trade_date` | TEXT | `2025-06-01` |
| `open` | REAL | |
| `high` | REAL | |
| `low` | REAL | |
| `close` | REAL | |
| `volume` | INTEGER | |

Last ~252 trading days for `INFY.NS` — enough for routing tests, not a full history warehouse.

---

## Data seeding (who fills the DB)

**The agent never writes data.** Offline seed only:

```
data/seeds/infosys_financials.csv   ← hand-curated from AR / Screener
data/seeds/infosys_shareholding.csv
        │
        ▼
scripts/seed_sample_db.py
        ├── load CSV → financials, shareholding
        ├── optional: yfinance → daily_prices
        └── write data/sample.db
```

Run before agent tests:

```bash
python scripts/seed_sample_db.py           # CSV + yfinance OHLC (~252 days)
python scripts/seed_sample_db.py --no-prices # CSV only, no network
```

Commit **CSV seeds** to git; `sample.db` is gitignored — regenerate locally after clone.

**Status:** Implemented — `scripts/seed_sample_db.py`, `data/seeds/*.csv`

---

## Folder structure (Phase 04 additions)

```
src/
└── agent.py

scripts/
└── seed_sample_db.py

data/
├── seeds/
│   ├── infosys_financials.csv
│   └── infosys_shareholding.csv
└── sample.db              ← generated
```

---

## Routing test suite (10 questions)

Manual acceptance tests — expected **primary** tool(s). Some questions need two tools in one turn or across iterations.

| # | Question | Expected tool(s) | Notes |
|---|---|---|---|
| 1 | Who is the CEO of Infosys? | `search_docs` | Prose in AR; not SQL |
| 2 | What was Infosys revenue in FY2025 (₹ crore)? | `run_sql` | From `financials` |
| 3 | What is the operating margin for FY2025? | `run_sql` | RAG weak on chart numbers |
| 4 | What was INFY closing price on {recent date}? | `run_sql` | `daily_prices` |
| 5 | What is 17% of 842? | `calculate` | No DB/RAG needed |
| 6 | YoY revenue growth FY2024 to FY2025? | `run_sql` + `calculate` | Fetch two rows, then math |
| 7 | Latest Infosys news headlines? | `web_search` | Not in PDF |
| 8 | What did the chairman say about AI strategy? | `search_docs` | Narrative |
| 9 | What is TCS revenue? | None / refuse | Out of scope — no tool should invent |
| 10 | Promoter holding percentage latest quarter? | `run_sql` | `shareholding` table |

**Pass criteria:** ≥ 8/10 correct primary tool choice + reasonable final answer + loop terminates.

---

## Implementation order (code)

| Step | Deliverable | Status |
|---|---|---|
| 1 | `agent.py` loop + `search_docs` only | Done |
| 2 | Add `run_sql` + SQL guard | Done |
| 3 | Add `calculate` | Done |
| 4 | Add `web_search` | Done |
| 5 | Full 10 routing tests | Done (10/10) |

---

## Dependencies

Add to `requirements.txt` when implementing:

| Package | Purpose |
|---|---|
| (existing) `groq`, `openai`, `python-dotenv` | LLM + embeddings path |
| `yfinance` | Optional OHLC seed |
| `tavily-python` or `httpx` | Web search (pick one in setup.md) |

---

## Acceptance criteria

- [x] `scripts/seed_sample_db.py` creates populated `data/sample.db`
- [x] Four tools implemented with descriptions above (web may stub without key)
- [x] Agent loop caps at 10 iterations
- [x] SQL tool rejects non-SELECT
- [x] ≥ 8/10 routing questions use correct primary tool (**10/10** verified June 2026)
- [x] Interactive terminal session works
- [x] Phase 03 RAG eval unchanged (`query()` still tested directly)
- [x] Groq `tool_use_failed` recovery for malformed Llama tool calls
- [x] Out-of-scope routing (TCS) via system prompt scope limit

---

## Future: Strands migration (Phase 10 / 11)

A colleague recommended **[AWS Strands Agents SDK](https://strandsagents.com/)** for production agent development. That aligns with this project's Phase 10 (multi-agent) and Phase 11 (harness comparison) — **not a replacement for Phase 04's raw SDK implementation.**

### Why raw SDK first (Phase 04)

- See every loop iteration: LLM → tool call → tool result → LLM
- Understand tool descriptions as routing prompts before `@tool` abstraction
- Match Phases 01–03: minimal dependencies, full walkthrough teachable line-by-line
- Groq + existing `query()` integration without new framework coupling

### What Strands would replace later

| Phase 04 (hand-rolled) | Strands equivalent |
|---|---|
| Manual `for` loop + `MAX_ITERATIONS` | `Agent` event loop with built-in cap / retries |
| Hand-written JSON `TOOL_DEFINITIONS` | `@tool` on Python functions — docstrings → schema |
| `execute_tool()` dispatch | Strands tool registry |
| Ad-hoc logging | OpenTelemetry / Strands observability |
| Phase 08 SQL as Python function | Same logic as `@tool` or **MCP server** (Strands-native) |

### Planned migration path

```
Phase 04   src/agent.py              raw Groq tool loop (this design)
Phase 08   mcp/sql_mcp_server/       SQL access as MCP tool
Phase 10   src/strands_agent.py      optional parallel impl:
                                       Agent(tools=[search_docs, run_sql, ...])
Phase 11   harness.md                feature matrix:
                                       our loop vs LangGraph vs Strands
```

### Example — same tool after migration

```python
from strands import Agent, tool
from rag import query

@tool
def search_docs(question: str) -> str:
    """Search Infosys FY2026 annual report (RAG). Use for filing narrative, not prices or news."""
    r = query(question=question)
    return r["answer"]

agent = Agent(tools=[search_docs, run_sql, calculate, web_search])
agent("Who is the CEO of Infosys?")
```

**Business logic unchanged** — only the harness around it.

### When to prefer Strands in production

- Standardizing on **Amazon Bedrock** or heavy **Claude** tool use
- Need **MCP**, multi-agent (A2A), retries, tracing out of the box
- Team velocity over pedagogical visibility

**Decision for this repo:** Implement Phase 04 as designed; revisit Strands in Phase 10 with a side-by-side routing benchmark on the same 10 questions.

---

## Related docs

| Topic | File |
|---|---|
| Concepts | [concepts.md](concepts.md) |
| Setup (next) | setup.md *(pending)* |
| Phase 03 RAG eval | [../phase-03/design.md](../phase-03/design.md) |
| REQUIREMENTS Phase 10–11 | [../../REQUIREMENTS.md](../../REQUIREMENTS.md) |
