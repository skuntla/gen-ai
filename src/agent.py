"""
src/agent.py — Phase 04: tool-using agent (Steps 1–4: all tools).

Interactive:
  python src/agent.py

One-shot:
  python src/agent.py "Latest Infosys news headlines?"

Requires: data/index (Phase 02), data/sample.db (seed script), GROQ_API_KEY
Optional: TAVILY_API_KEY for web_search
"""

from __future__ import annotations

import argparse
import ast
import json
import operator
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv(ROOT / ".env")

from rag import query  # noqa: E402

MAX_ITERATIONS = 10
MAX_SQL_ROWS = 100
MAX_WEB_RESULTS = 5
DEFAULT_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
DEFAULT_DB = ROOT / "data" / "sample.db"
_TAVILY_PLACEHOLDERS = {"", "your_tavily_api_key_here", "tvly-your_api_key_here"}

_FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|ATTACH|DETACH|PRAGMA|REPLACE|TRUNCATE)\b",
    re.IGNORECASE,
)

AGENT_SYSTEM_PROMPT = """You are a Stock Research Assistant for Indian equities (Infosys / INFY focus in Phase 04).

You have tools. Use them instead of answering from memory when a tool can provide grounded data.
This assistant only has Infosys data. For other companies (e.g. TCS, Wipro), do NOT call tools — politely refuse and explain the scope limit.

Available tools:
- search_docs — Infosys annual report PDF (narrative, CEO, chairman, risks, business description).
- run_sql — SQLite database (financials by fiscal year, shareholding by quarter, daily_prices OHLC).
- calculate — safe arithmetic on numbers (+ - * / % parentheses).
- web_search — recent Infosys news and headlines from the web (not in the PDF or DB).

Routing:
- Structured numbers (revenue, margins, ROE, debt, promoter %, stock close price by date) → run_sql.
- Prose and management commentary from the filing → search_docs.
- Pure math, growth rates, percentages, ratios → calculate (fetch inputs from run_sql first when needed).
- Latest news, recent announcements, post-filing events → web_search.
- Do not use search_docs for metrics that belong in tables financials, shareholding, or daily_prices.
- Do not do mental math — use calculate for arithmetic.
- If web_search returns a stub (no API key), tell the user web search is not configured.

When you respond, cite what the tools returned. Do not invent facts."""

TOOL_SEARCH_DOCS = {
    "type": "function",
    "function": {
        "name": "search_docs",
        "description": (
            "Search the Infosys FY2026 annual report PDF indexed by RAG. "
            "Use for CEO, chairman, business segments, risks, and narrative from filings. "
            "Do NOT use for stock prices, structured database metrics, latest news, or pure math."
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

TOOL_RUN_SQL = {
    "type": "function",
    "function": {
        "name": "run_sql",
        "description": (
            "Run a read-only SQL SELECT against the Infosys financial SQLite database. "
            "Use for numeric metrics by fiscal year or quarter, shareholding, and daily OHLC prices. "
            "Tables: financials (symbol, fiscal_year, revenue_cr, operating_margin_pct, net_margin_pct, "
            "roe_pct, debt_to_equity), shareholding (symbol, quarter, promoter_pct, fii_pct), "
            "daily_prices (symbol, trade_date, open, high, low, close, volume). "
            "fiscal_year is TEXT like 'FY2025' (not integer). quarter is TEXT like 'Q1 FY2026'. "
            "symbol is 'INFY'. "
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

TOOL_CALCULATE = {
    "type": "function",
    "function": {
        "name": "calculate",
        "description": (
            "Evaluate a safe arithmetic expression (numbers, + - * / % parentheses). "
            "Use for percentages, growth rates, and ratios. "
            "Use after run_sql when computing YoY growth or derived metrics from fetched values. "
            "Do NOT use to look up facts — use run_sql or search_docs first."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Math expression e.g. '(165641 - 153656) / 153656 * 100' or '842 * 17 / 100'",
                }
            },
            "required": ["expression"],
        },
    },
}

TOOL_WEB_SEARCH = {
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

TOOLS = [TOOL_SEARCH_DOCS, TOOL_RUN_SQL, TOOL_CALCULATE, TOOL_WEB_SEARCH]

_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}


def _get_groq_client():
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY is not set in .env")
    return Groq(api_key=api_key)


def _groq_error_payload(exc: Exception) -> dict:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        err = body.get("error")
        return err if isinstance(err, dict) else {}
    return {}


def _parse_failed_generation(failed: str) -> list[tuple[str, dict]]:
    """
    Recover tool calls when Groq returns tool_use_failed.

    Llama on Groq sometimes emits XML-like tags instead of structured tool_calls:
      <function=search_docs{"question": "..."}</function>
    """
    if not failed:
        return []

    calls: list[tuple[str, dict]] = []

    tag_pattern = re.compile(
        r"<function=(\w+)\s*(\{.*?\})\s*</function>",
        re.DOTALL | re.IGNORECASE,
    )
    for name, args_str in tag_pattern.findall(failed):
        try:
            calls.append((name, json.loads(args_str)))
        except json.JSONDecodeError:
            continue
    if calls:
        return calls

    # Some failures wrap a partial OpenAI-style tool_calls JSON blob.
    json_match = re.search(r"\{.*\}", failed, re.DOTALL)
    if not json_match:
        return []
    try:
        payload = json.loads(json_match.group(0))
    except json.JSONDecodeError:
        return []

    for entry in payload.get("tool_calls", []):
        fn = entry.get("function") or {}
        name = fn.get("name")
        if not name:
            continue
        raw_args = fn.get("arguments") or fn.get("parameters") or {}
        if isinstance(raw_args, str):
            try:
                raw_args = json.loads(raw_args)
            except json.JSONDecodeError:
                raw_args = {}
        if isinstance(raw_args, dict):
            calls.append((name, raw_args))
    return calls


def _recover_tool_calls_from_groq_error(
    exc: Exception, *, iteration: int
) -> list[dict] | None:
    err = _groq_error_payload(exc)
    if err.get("code") != "tool_use_failed":
        return None

    parsed = _parse_failed_generation(err.get("failed_generation", ""))
    if not parsed:
        return None

    return [
        {
            "id": f"call_recovered_{iteration}_{i}",
            "name": name,
            "arguments": args,
        }
        for i, (name, args) in enumerate(parsed)
    ]


def _request_chat_completion(client, *, model: str, messages: list[dict]):
    """Call Groq chat API; raise on non-recoverable errors."""
    return client.chat.completions.create(
        model=model,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        parallel_tool_calls=False,
        temperature=0.1,
    )


def tool_search_docs(question: str, *, index_dir: str | None = None) -> str:
    """Run Phase 02 RAG query; return JSON for the agent loop."""
    idx = index_dir or str(ROOT / "data" / "index")
    result = query(question=question.strip(), index_dir=idx, top_k=5)
    source_lines = [
        f"[{s['score']:.3f}] {s['source']} p.{s['page']}"
        for s in result.get("sources", [])
    ]
    return json.dumps(
        {
            "answer": result["answer"],
            "sources": source_lines,
            "latency_ms": result.get("latency_ms", 0),
        },
        ensure_ascii=False,
    )


def validate_sql(sql: str) -> tuple[bool, str]:
    """Return (ok, error_message). Only single SELECT allowed."""
    text = sql.strip()
    if not text:
        return False, "Empty SQL statement."

    # Allow one trailing semicolon only
    if ";" in text.rstrip().rstrip(";"):
        return False, "Multi-statement SQL is not allowed."

    statement = text.rstrip(";").strip()
    if not statement.upper().startswith("SELECT"):
        return False, "Only SELECT statements are allowed."

    if _FORBIDDEN_SQL.search(statement):
        return False, "Statement contains forbidden keywords."

    return True, ""


def tool_run_sql(sql: str, *, db_path: Path | None = None) -> str:
    """Execute read-only SELECT; return JSON rows for the agent loop."""
    path = db_path or DEFAULT_DB
    ok, err = validate_sql(sql)
    if not ok:
        return json.dumps({"error": err})

    if not path.exists():
        return json.dumps(
            {
                "error": f"Database not found at {path}. Run: python scripts/seed_sample_db.py"
            }
        )

    statement = sql.strip().rstrip(";").strip()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(statement)
        rows_raw = cur.fetchmany(MAX_SQL_ROWS + 1)
        if len(rows_raw) > MAX_SQL_ROWS:
            return json.dumps(
                {
                    "error": f"Query returned more than {MAX_SQL_ROWS} rows. Add a LIMIT clause."
                }
            )
        columns = [d[0] for d in cur.description] if cur.description else []
        rows = [dict(r) for r in rows_raw]
        return json.dumps(
            {"columns": columns, "rows": rows, "row_count": len(rows)},
            ensure_ascii=False,
        )
    except sqlite3.Error as exc:
        return json.dumps({"error": str(exc)})
    finally:
        conn.close()


def _eval_ast_node(node: ast.AST) -> float:
    """Evaluate a parsed expression node; numbers and operators only."""
    if isinstance(node, ast.Expression):
        return _eval_ast_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError(f"Unsupported constant: {node.value!r}")
    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        return float(op(_eval_ast_node(node.operand)))
    if isinstance(node, ast.BinOp):
        op = _BINARY_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported binary operator: {type(node.op).__name__}")
        return float(op(_eval_ast_node(node.left), _eval_ast_node(node.right)))
    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def safe_calculate(expression: str) -> float:
    """Parse and evaluate a safe arithmetic expression."""
    text = expression.strip()
    if not text:
        raise ValueError("Empty expression.")
    tree = ast.parse(text, mode="eval")
    return _eval_ast_node(tree)


def tool_calculate(expression: str) -> str:
    """Evaluate arithmetic; return JSON for the agent loop."""
    try:
        result = safe_calculate(expression)
        return json.dumps(
            {"result": result, "expression": expression.strip()},
            ensure_ascii=False,
        )
    except (ValueError, SyntaxError, TypeError, ZeroDivisionError) as exc:
        return json.dumps({"error": str(exc)})


def _tavily_api_key() -> str | None:
    key = (os.getenv("TAVILY_API_KEY") or "").strip()
    if not key or key.lower() in _TAVILY_PLACEHOLDERS:
        return None
    return key


def tool_web_search(query: str) -> str:
    """Search the web via Tavily; stub when TAVILY_API_KEY is not configured."""
    text = query.strip()
    if not text:
        return json.dumps({"error": "Empty search query."})

    api_key = _tavily_api_key()
    if not api_key:
        return json.dumps(
            {
                "stub": True,
                "message": (
                    "Web search is not configured. Set TAVILY_API_KEY in .env "
                    "(get a free key at https://tavily.com)."
                ),
                "query": text,
            }
        )

    try:
        from tavily import TavilyClient
    except ImportError:
        return json.dumps(
            {
                "error": "tavily-python is not installed. Run: pip install tavily-python"
            }
        )

    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=text,
            topic="news",
            search_depth="basic",
            max_results=MAX_WEB_RESULTS,
            include_answer=True,
        )
    except Exception as exc:
        return json.dumps({"error": f"Tavily search failed: {exc}"})

    results = []
    for item in response.get("results", []):
        results.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),
            }
        )

    return json.dumps(
        {
            "query": text,
            "answer": response.get("answer", ""),
            "results": results,
            "result_count": len(results),
        },
        ensure_ascii=False,
    )


def execute_tool(
    name: str,
    arguments: dict,
    *,
    index_dir: str | None = None,
    db_path: Path | None = None,
) -> str:
    if name == "search_docs":
        return tool_search_docs(arguments.get("question", ""), index_dir=index_dir)
    if name == "run_sql":
        return tool_run_sql(arguments.get("sql", ""), db_path=db_path)
    if name == "calculate":
        return tool_calculate(arguments.get("expression", ""))
    if name == "web_search":
        return tool_web_search(arguments.get("query", ""))
    return json.dumps({"error": f"Unknown tool: {name}"})


def _assistant_message_dict(msg) -> dict:
    out: dict = {"role": "assistant", "content": msg.content or ""}
    if msg.tool_calls:
        out["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in msg.tool_calls
        ]
    return out


def _run_tool_calls(
    tool_calls: list[dict],
    *,
    messages: list[dict],
    iteration: int,
    verbose: bool,
    index_dir: str | None,
    db_path: Path | None,
) -> None:
    """Append assistant tool_calls + tool results to messages."""
    messages.append(
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": json.dumps(tc["arguments"]),
                    },
                }
                for tc in tool_calls
            ],
        }
    )

    for tc in tool_calls:
        t0 = time.time()
        result = execute_tool(
            tc["name"], tc["arguments"], index_dir=index_dir, db_path=db_path
        )
        elapsed_ms = int((time.time() - t0) * 1000)

        if verbose:
            print(
                f"\n[tool {iteration}] {tc['name']}({tc['arguments']}) — {elapsed_ms}ms",
                flush=True,
            )
            preview = result[:500] + ("..." if len(result) > 500 else "")
            print(preview, flush=True)

        messages.append(
            {
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            }
        )


def run_agent(
    user_message: str,
    *,
    model: str = DEFAULT_MODEL,
    verbose: bool = False,
    index_dir: str | None = None,
    db_path: Path | None = None,
) -> str:
    """
    Run the agent loop until the model returns a final message or max iterations.
    """
    client = _get_groq_client()
    messages: list[dict] = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    for iteration in range(1, MAX_ITERATIONS + 1):
        try:
            response = _request_chat_completion(
                client, model=model, messages=messages
            )
            msg = response.choices[0].message
        except Exception as exc:
            from groq import BadRequestError

            if not isinstance(exc, BadRequestError):
                raise
            recovered = _recover_tool_calls_from_groq_error(
                exc, iteration=iteration
            )
            if not recovered:
                raise
            if verbose:
                print(
                    f"\n[recover {iteration}] parsed Groq failed_generation → "
                    f"{[tc['name'] for tc in recovered]}",
                    flush=True,
                )
            _run_tool_calls(
                recovered,
                messages=messages,
                iteration=iteration,
                verbose=verbose,
                index_dir=index_dir,
                db_path=db_path,
            )
            continue

        if not msg.tool_calls:
            return (msg.content or "").strip()

        tool_calls = []
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": args,
                }
            )
        _run_tool_calls(
            tool_calls,
            messages=messages,
            iteration=iteration,
            verbose=verbose,
            index_dir=index_dir,
            db_path=db_path,
        )

    return "Agent stopped: maximum iterations reached without a final answer."


def _interactive(
    *,
    model: str,
    verbose: bool,
    index_dir: str | None,
    db_path: Path | None,
) -> None:
    print("Stock Research Assistant (Phase 04 — all tools)")
    print("Type a question, or 'quit' / Ctrl-D to exit.\n")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit", "q"}:
            print("Bye.")
            break
        print("\nAssistant:", flush=True)
        answer = run_agent(
            user_input,
            model=model,
            verbose=verbose,
            index_dir=index_dir,
            db_path=db_path,
        )
        print(answer, "\n", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 04 tool-using agent")
    parser.add_argument(
        "question",
        nargs="?",
        help="One-shot question (omit for interactive REPL)",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Groq model for tool use")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print tool calls and raw tool results",
    )
    parser.add_argument(
        "--index-dir",
        default=str(ROOT / "data" / "index"),
        help="FAISS index directory for search_docs",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help="SQLite database for run_sql",
    )
    args = parser.parse_args()

    if args.question:
        answer = run_agent(
            args.question,
            model=args.model,
            verbose=args.verbose,
            index_dir=args.index_dir,
            db_path=args.db,
        )
        print(answer)
    else:
        _interactive(
            model=args.model,
            verbose=args.verbose,
            index_dir=args.index_dir,
            db_path=args.db,
        )


if __name__ == "__main__":
    main()
