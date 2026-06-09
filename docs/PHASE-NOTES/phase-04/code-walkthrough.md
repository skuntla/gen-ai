# Code Walkthrough — Phase 04 Agent (`agent.py`)

Line-by-line guide to the tool-using agent: from `python src/agent.py "..."` through the Groq loop to `search_docs`, `run_sql`, `calculate`, and `web_search`. Use this as a workshop script when teaching Phase 04.

For theory (agent loop, ReAct, routing), see [concepts.md](concepts.md). For tool schemas and routing tests, see [design.md](design.md). For setup and env keys, see [setup.md](setup.md).

**Verified:** 10/10 routing tests | `llama-3.3-70b-versatile` | ~700 lines in `src/agent.py`

---

## How to read this file

Each step follows the same structure:

1. Where it sits in the pipeline
2. The code (from the real file)
3. Line-by-line explanation
4. What this step does **not** do
5. Mental model

Run commands between steps where noted:

```bash
python src/agent.py --verbose "Who is the CEO of Infosys?"
python src/agent.py --verbose "What is 17% of 842?"
python src/agent.py --verbose "What is YoY revenue growth from FY2024 to FY2025?"
```

---

## Big picture

```
You type:  python src/agent.py "Operating margin FY2025?"
                │
                ▼
         main() / argparse     Step 1 — CLI entry
                │
                ▼
         run_agent()           Step 2 — build messages, start loop
                │
        ┌───────┴───────┐
        ▼               ▼
  Groq API call    (recovery path)   Step 3 — LLM decides: tool or answer
        │
        ▼
  _run_tool_calls()          Step 4 — execute tools, append results
        │
        ├── search_docs → rag.query()
        ├── run_sql     → sqlite3 + validate_sql
        ├── calculate   → ast safe eval
        └── web_search  → Tavily or stub
        │
        ▼
  Loop until plain text or MAX_ITERATIONS
        │
        ▼
  Print final answer
```

**Key idea:** Python never picks the tool. The LLM reads the system prompt + tool descriptions and emits `tool_calls`. Your code only executes what the model requests.

---

## Step 1 — Bootstrap: paths, constants, imports

### The code

```29:41:src/agent.py
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv(ROOT / ".env")

from rag import query  # noqa: E402

MAX_ITERATIONS = 10
MAX_SQL_ROWS = 100
MAX_WEB_RESULTS = 5
DEFAULT_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
DEFAULT_DB = ROOT / "data" / "sample.db"
```

### Line by line

| Piece | Purpose |
|---|---|
| `ROOT` | Project root (`genai-learning-path/`) — stable paths for `data/` |
| `sys.path.insert` | Import `rag` from `src/` without installing as package |
| `load_dotenv` | Load `GROQ_API_KEY`, `TAVILY_API_KEY`, etc. |
| `from rag import query` | Phase 02 RAG — wrapped by `search_docs` tool |
| `MAX_ITERATIONS = 10` | Safety cap — loop cannot run forever |
| `DEFAULT_DB` | SQLite path for `run_sql` |

### What this does not do

- Does not start the agent or call Groq
- Does not validate that index or DB exist (tools fail gracefully later)

### Mental model

Same bootstrap pattern as `rag.py`: find project root, load `.env`, import Phase 02 capability.

---

## Step 2 — System prompt and tool schemas

### The code

```48:68:src/agent.py
AGENT_SYSTEM_PROMPT = """You are a Stock Research Assistant for Indian equities (Infosys / INFY focus in Phase 04).

You have tools. Use them instead of answering from memory when a tool can provide grounded data.
This assistant only has Infosys data. For other companies (e.g. TCS, Wipro), do NOT call tools — politely refuse and explain the scope limit.

Available tools:
- search_docs — Infosys annual report PDF (narrative, CEO, chairman, risks, business description).
- run_sql — SQLite database (financials by fiscal year, shareholding by quarter, daily_prices OHLC).
- calculate — safe arithmetic on numbers (+ - * / % parentheses).
- web_search — recent Infosys news and headlines from the web (not in the PDF or DB).
...
```

```164:164:src/agent.py
TOOLS = [TOOL_SEARCH_DOCS, TOOL_RUN_SQL, TOOL_CALCULATE, TOOL_WEB_SEARCH]
```

### Line by line

| Piece | Purpose |
|---|---|
| `AGENT_SYSTEM_PROMPT` | Routing rules sent as `role: system` every request |
| Scope line (TCS/Wipro) | Prevents `run_sql` on out-of-scope companies (routing test #9) |
| `TOOL_*` dicts | OpenAI-style function schemas — name, description, parameters |
| `TOOLS` list | Passed to Groq on every `chat.completions.create` |

**Two layers of routing guidance:**

1. **System prompt** — high-level rules ("margins → run_sql", "news → web_search")
2. **Tool `description` fields** — when *not* to use each tool + schema hints (e.g. `fiscal_year` is `'FY2025'`)

### What this does not do

- Does not execute — it is text the model reads
- Does not auto-sync with `seed_sample_db.py` DDL — you maintain both

### Mental model

Tool descriptions are **secretly another prompt**. The model chooses tools from this menu.

---

## Step 3 — Groq client and chat request

### The code

```180:186:src/agent.py
def _get_groq_client():
    from groq import Groq
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY is not set in .env")
    return Groq(api_key=api_key)
```

```267:276:src/agent.py
def _request_chat_completion(client, *, model: str, messages: list[dict]):
    return client.chat.completions.create(
        model=model,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        parallel_tool_calls=False,
        temperature=0.1,
    )
```

### Line by line

| Parameter | Purpose |
|---|---|
| `tools=TOOLS` | Register all four functions with the model |
| `tool_choice="auto"` | Model decides: answer directly or call tool(s) |
| `parallel_tool_calls=False` | One tool at a time — stabler on Groq/Llama |
| `temperature=0.1` | Low randomness for routing consistency |

**Note:** Phase 04 uses Groq SDK **directly** for the agent loop — not `llm_chat.chat()`. RAG inside `search_docs` still uses `chat()` via `query()`.

### Mental model

Each loop iteration = one Groq call with the **entire** `messages` list so far.

---

## Step 4 — Groq `tool_use_failed` recovery

### The code

```197:243:src/agent.py
def _parse_failed_generation(failed: str) -> list[tuple[str, dict]]:
    """
    Recover tool calls when Groq returns tool_use_failed.
    Llama on Groq sometimes emits XML-like tags instead of structured tool_calls:
      <function=search_docs{"question": "..."}</function>
    """
    tag_pattern = re.compile(
        r"<function=(\w+)\s*(\{.*?\})\s*</function>",
        ...
    )
```

### Why it exists

Groq sometimes returns `400 tool_use_failed` with:

```
failed_generation: '<function=search_docs{"question": "Who is the CEO?"}</function>'
```

Without recovery, the agent crashes. `_recover_tool_calls_from_groq_error` parses this, runs the tool anyway, and continues the loop.

### Try it

```bash
python src/agent.py --verbose "Who is the CEO of Infosys?"
# May show: [recover 1] parsed Groq failed_generation → ['search_docs']
```

### Mental model

Defensive coding for hosted LLM API quirks — not part of the "happy path" design, but required for reliable demos.

---

## Step 5 — Tool: `search_docs`

### The code

```279:294:src/agent.py
def tool_search_docs(question: str, *, index_dir: str | None = None) -> str:
    idx = index_dir or str(ROOT / "data" / "index")
    result = query(question=question.strip(), index_dir=idx, top_k=5)
    ...
    return json.dumps({
        "answer": result["answer"],
        "sources": source_lines,
        "latency_ms": result.get("latency_ms", 0),
    }, ensure_ascii=False)
```

### Input → output

| Input | Output |
|---|---|
| `question: "Who is the CEO of Infosys?"` | JSON string with `answer`, `sources`, `latency_ms` |

The JSON string becomes the `content` of a `role: tool` message. The LLM reads it on the **next** iteration.

### What this does not do

- Does not change Phase 02 RAG behavior — same `query()`, same index
- Does not bypass Phase 03 eval — `evals/` still tests `query()` directly

---

## Step 6 — Tool: `run_sql` + validation

### The code

```297:314:src/agent.py
def validate_sql(sql: str) -> tuple[bool, str]:
    ...
    if not statement.upper().startswith("SELECT"):
        return False, "Only SELECT statements are allowed."
    if _FORBIDDEN_SQL.search(statement):
        return False, "Statement contains forbidden keywords."
```

```317:353:src/agent.py
def tool_run_sql(sql: str, *, db_path: Path | None = None) -> str:
    ok, err = validate_sql(sql)
    if not ok:
        return json.dumps({"error": err})
    ...
    cur.execute(statement)
    rows_raw = cur.fetchmany(MAX_SQL_ROWS + 1)
```

### Safety rules

| Rule | Why |
|---|---|
| SELECT only | Read-only agent |
| No `INSERT`, `DROP`, etc. | Block DDL/DML keywords |
| No multi-statement (`;` mid-query) | Prevent injection chains |
| Max 100 rows | Cap runaway queries |

### Schema knowledge

The LLM learns columns from `TOOL_RUN_SQL` description — not from live DB introspection. See [design.md](design.md) for full schema.

### Try it

```bash
python src/agent.py --verbose "What is the operating margin for FY2025?"
# [tool 1] run_sql({'sql': "SELECT ... WHERE fiscal_year = 'FY2025'"})
```

---

## Step 7 — Tool: `calculate` (safe `ast` eval)

### The code

```356:395:src/agent.py
def _eval_ast_node(node: ast.AST) -> float:
    """Evaluate a parsed expression node; numbers and operators only."""
    ...

def safe_calculate(expression: str) -> float:
    tree = ast.parse(text, mode="eval")
    return _eval_ast_node(tree)

def tool_calculate(expression: str) -> str:
    result = safe_calculate(expression)
    return json.dumps({"result": result, "expression": ...})
```

### Why not `eval()`?

`eval()` can execute arbitrary Python (`__import__('os')`). `ast.parse` + whitelist of `BinOp`/`UnaryOp` nodes allows only `+ - * / % **` and numbers.

### Try it

```bash
python src/agent.py --verbose "What is 17% of 842?"
# [tool 1] calculate({'expression': '842 * 17 / 100'})
# → 143.14
```

### Multi-tool chain

```bash
python src/agent.py --verbose "What is YoY revenue growth from FY2024 to FY2025?"
# [tool 1] run_sql — fetch two revenue_cr values
# [tool 2] calculate — (165641 - 153656) / 153656 * 100
# → 7.80%
```

---

## Step 8 — Tool: `web_search` (Tavily or stub)

### The code

```405:463:src/agent.py
def tool_web_search(query: str) -> str:
    api_key = _tavily_api_key()
    if not api_key:
        return json.dumps({"stub": True, "message": "Web search is not configured...", ...})

    client = TavilyClient(api_key=api_key)
    response = client.search(query=text, topic="news", max_results=MAX_WEB_RESULTS, ...)
```

| State | Behavior |
|---|---|
| No `TAVILY_API_KEY` | Stub JSON — loop continues, agent explains key missing |
| Key set | Live news search — `title`, `url`, `snippet` per result |

### Try it

```bash
python src/agent.py --verbose "What are the latest Infosys news headlines?"
# [tool 1] web_search({'query': 'Infosys news 2026'})
```

---

## Step 9 — Dispatcher: `execute_tool`

### The code

```466:481:src/agent.py
def execute_tool(name: str, arguments: dict, *, index_dir, db_path) -> str:
    if name == "search_docs":
        return tool_search_docs(...)
    if name == "run_sql":
        return tool_run_sql(...)
    if name == "calculate":
        return tool_calculate(...)
    if name == "web_search":
        return tool_web_search(...)
    return json.dumps({"error": f"Unknown tool: {name}"})
```

Simple `if/elif` router — no plugin framework. Adding a fifth tool = one `TOOL_*` dict + one branch here.

---

## Step 10 — Append tool results: `_run_tool_calls`

### The code

```501:550:src/agent.py
def _run_tool_calls(tool_calls, *, messages, ...):
    messages.append({"role": "assistant", "content": "", "tool_calls": [...]})
    for tc in tool_calls:
        result = execute_tool(tc["name"], tc["arguments"], ...)
        messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
```

### Message shape after one tool call

```python
[
  {"role": "system", "content": "..."},
  {"role": "user", "content": "Operating margin FY2025?"},
  {"role": "assistant", "tool_calls": [{"name": "run_sql", ...}]},
  {"role": "tool", "tool_call_id": "call_abc", "content": "{\"rows\": [...]}"}
]
```

Next Groq call sees all four messages and composes the final answer.

---

## Step 11 — The agent loop: `run_agent`

### The code

```553:627:src/agent.py
def run_agent(user_message: str, ...) -> str:
    messages = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    for iteration in range(1, MAX_ITERATIONS + 1):
        try:
            response = _request_chat_completion(...)
            msg = response.choices[0].message
        except BadRequestError:
            recovered = _recover_tool_calls_from_groq_error(...)
            _run_tool_calls(recovered, ...)
            continue

        if not msg.tool_calls:
            return (msg.content or "").strip()   # DONE — final answer

        _run_tool_calls(parsed_tool_calls, ...)
    return "Agent stopped: maximum iterations reached..."
```

### Two exit paths

| Outcome | When |
|---|---|
| `return msg.content` | Model responds with plain text (no `tool_calls`) |
| Max iterations message | 10 tool rounds without final text |

### Typical iteration count

| Question type | LLM calls |
|---|---|
| Simple (CEO, margin) | 2 (tool + answer) |
| YoY growth | 3 (sql + calc + answer) |
| Groq recovery | Same, but first call may error-then-recover |

---

## Step 12 — CLI: `main()` and interactive mode

### The code

```661:706:src/agent.py
def main() -> None:
    parser = argparse.ArgumentParser(...)
    parser.add_argument("question", nargs="?", ...)
    parser.add_argument("--verbose", action="store_true", ...)
    parser.add_argument("--index-dir", ...)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, ...)
```

| Mode | Command |
|---|---|
| One-shot | `python src/agent.py "question"` |
| REPL | `python src/agent.py` |
| Debug | add `--verbose` |

---

## End-to-end trace: "Who is the CEO?"

```
1. main() → run_agent("Who is the CEO of Infosys?")
2. messages = [system, user]
3. Groq call #1 → tool_call: search_docs(question=...)
4. tool_search_docs → rag.query() → JSON with Salil Parekh + sources
5. messages += [assistant+tool_calls, tool+result]
6. Groq call #2 → plain text: "The CEO is Salil Parekh..."
7. print answer
```

---

## What Phase 04 deliberately omits

| Omitted | Lands in |
|---|---|
| LangChain / Strands agents | Phase 10/11 (documented migration path) |
| Automated trajectory eval | Phase 09 (`agent_evals/`) |
| Tracing / spans | Phase 05 (`traces.ipynb`) |
| Input/output guardrails | Phase 06 (`guardrails.py`) |
| MCP server for SQL | Phase 08 (`sql_mcp_server/`) |
| `if "CEO" in question: ...` routing | Never — LLM routes via prompts |

---

## Quick reference — inputs and outputs per layer

| Layer | Input | Output |
|---|---|---|
| CLI | question string, flags | printed answer |
| `run_agent` | user message | final string |
| Groq API | messages + TOOLS | `tool_calls` or `content` |
| `execute_tool` | name + args dict | JSON string |
| `search_docs` | question | `{answer, sources, latency_ms}` |
| `run_sql` | SQL string | `{columns, rows}` or `{error}` |
| `calculate` | expression | `{result}` or `{error}` |
| `web_search` | query | `{results}` or `{stub}` |

---

## Next phases

- **Phase 05:** Instrument this loop — trace every Groq call and tool span
- **Phase 09:** Automate the 10 routing tests as trajectory eval in CI
- **Phase 10:** Strands migration — same tools, framework-managed loop

See [reflection.md](reflection.md) for lessons learned and [teaching-guide.md](teaching-guide.md) for workshop flow.
