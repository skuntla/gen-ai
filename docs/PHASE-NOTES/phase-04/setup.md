# Setup — Phase 04

## Prerequisites

- **Phase 02:** FAISS index built — `data/index/` from `infosys-ar-26.pdf`
- **Phase 03:** RAG eval suite still passes (agent wraps `query()`, does not replace it)
- **Python venv** with project dependencies installed

## Environment variables

Copy `.env.example` → `.env` if needed. Required and optional keys:

| Variable | Required | Purpose |
|---|---|---|
| `GROQ_API_KEY` | Yes | Agent loop LLM (tool-use) |
| `OPENAI_API_KEY` | Yes | Embeddings inside `rag.query()` |
| `EMBEDDING_MODEL` | Yes | Must match index (`text-embedding-3-small`) |
| `LLM_MODEL` | No | Default `llama-3.3-70b-versatile` |
| `TAVILY_API_KEY` | No | Live `web_search`; stub message if missing |

```bash
# Minimum for agent (search_docs + run_sql + calculate)
GROQ_API_KEY=...
OPENAI_API_KEY=...
EMBEDDING_MODEL=text-embedding-3-small

# Optional — live news headlines
TAVILY_API_KEY=tvly-...
```

Get a free Tavily key at [tavily.com](https://tavily.com).

## Install dependencies

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Phase 04 adds `tavily-python` and (from seed pipeline) `yfinance`.

## Seed the SQLite database

`data/sample.db` is gitignored — regenerate after clone:

```bash
# Full seed: CSV fundamentals + shareholding + yfinance OHLC
python scripts/seed_sample_db.py

# Offline only (skip Yahoo Finance)
python scripts/seed_sample_db.py --no-prices
```

Verify:

```bash
sqlite3 data/sample.db "SELECT fiscal_year, revenue_cr FROM financials WHERE fiscal_year='FY2025';"
# FY2025|165641.0
```

## Run the agent

**One-shot:**

```bash
python src/agent.py "Who is the CEO of Infosys?"
python src/agent.py --verbose "What is YoY revenue growth from FY2024 to FY2025?"
```

**Interactive REPL:**

```bash
python src/agent.py
# Type questions; quit / exit / Ctrl-D to leave
```

**CLI flags:**

| Flag | Default | Purpose |
|---|---|---|
| `--verbose` | off | Print tool calls and raw JSON results |
| `--model` | `LLM_MODEL` from `.env` | Groq model for tool-use |
| `--index-dir` | `data/index` | FAISS path for `search_docs` |
| `--db` | `data/sample.db` | SQLite path for `run_sql` |

## Routing acceptance tests (10 questions)

Manual suite from [design.md](design.md). Run with `--verbose` to confirm tool choice.

| # | Question | Expected tool(s) |
|---|---|---|
| 1 | Who is the CEO of Infosys? | `search_docs` |
| 2 | What was Infosys revenue in FY2025 (₹ crore)? | `run_sql` |
| 3 | What is the operating margin for FY2025? | `run_sql` |
| 4 | What was INFY closing price on 2026-06-05? | `run_sql` |
| 5 | What is 17% of 842? | `calculate` |
| 6 | YoY revenue growth FY2024 to FY2025? | `run_sql` + `calculate` |
| 7 | Latest Infosys news headlines? | `web_search` |
| 8 | What did the chairman say about AI strategy? | `search_docs` |
| 9 | What is TCS revenue? | refuse (no tools) |
| 10 | Promoter holding percentage latest quarter? | `run_sql` |

**Pass criteria:** ≥ 8/10 correct primary tool + reasonable answer + loop terminates.

**Verified run:** 10/10 (June 2026) with `llama-3.3-70b-versatile`, live Tavily key.

## Troubleshooting

**`GROQ_API_KEY is not set`**

Add key to `.env` and ensure `load_dotenv` runs (it does in `agent.py`).

**`Database not found at data/sample.db`**

Run `python scripts/seed_sample_db.py`.

**`Index not found` / RAG errors in `search_docs`**

Rebuild index:

```bash
python src/rag.py --index
```

**`tool_use_failed` from Groq**

Llama on Groq sometimes emits malformed tool-call XML. `agent.py` recovers from `failed_generation` automatically. Use `--verbose` — you may see `[recover 1]`.

**`fiscal_year = 2025` returns 0 rows**

Schema uses TEXT like `'FY2025'`, not integer `2025`. Tool description documents this; model usually learns after one empty result.

**`Rate limit reached` (429)**

Groq free tier has daily token caps. Wait or reduce batch testing. Routing tests make ~15–25 API calls total.

**Web search stub**

If `TAVILY_API_KEY` is missing or placeholder, `web_search` returns a stub JSON and the agent tells the user to configure the key. Routing test #7 still passes on tool *choice*.

**SQL safety**

Only `SELECT` allowed. `DELETE`, `DROP`, multi-statement SQL are rejected before execution.
