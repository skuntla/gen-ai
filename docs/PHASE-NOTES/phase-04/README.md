# Phase 04 — Agent: Let the LLM Use Tools

**Goal:** Move from one-shot Q&A to an LLM that decides which capability to use.

**Artifact:** `src/agent.py`

**Status:** Complete — four tools, 10/10 routing tests, interactive CLI.

---

## Contents

| File | What's in it |
|---|---|
| [concepts.md](concepts.md) | Agent loop, tools, routing, scorecard mapping, data seeding |
| [design.md](design.md) | Tool schemas, `sample.db`, routing tests, loop design, Strands migration note |
| [setup.md](setup.md) | API keys, seed DB, CLI, routing tests, troubleshooting |
| [code-walkthrough.md](code-walkthrough.md) | Line-by-line guide for `agent.py` |
| [teaching-guide.md](teaching-guide.md) | Workshop flow (~4–6 hours) |
| [questions.md](questions.md) | Interview prep |
| [reflection.md](reflection.md) | Post-implementation notes |

---

## Where we are in the arc

```
Phase 01  chat()           — talk to an LLM
Phase 02  query()          — RAG over your PDFs
Phase 03  eval suite       — measure query() quality (55% baseline)
Phase 04  agent.py         — route questions to the right tool  ✓ complete
Phase 05  traces.ipynb     — instrument agent.py                 ← next
```

---

## Deliverables (code)

| File | Purpose | Status |
|---|---|---|
| `src/agent.py` | Agent loop + 4 tools + interactive CLI | Done |
| `data/sample.db` | SQLite for `run_sql` (seeded offline) | Seeded locally (gitignored) |
| `scripts/seed_sample_db.py` | Fill DB from CSV + optional yfinance | Done |
| `data/seeds/*.csv` | Curated Infosys fundamentals CSV | Done |

### Tools in `agent.py`

| Tool | Wraps | When to use |
|---|---|---|
| `search_docs` | Phase 02 `rag.query()` | CEO, chairman, narrative, risks |
| `run_sql` | `data/sample.db` (SELECT-only) | Revenue, margins, prices, shareholding |
| `calculate` | `ast` safe eval | Percentages, growth rates after fetching data |
| `web_search` | Tavily API (stub without key) | Latest news, post-filing events |

---

## Quick start

```bash
source .venv/bin/activate
pip install -r requirements.txt
python scripts/seed_sample_db.py
python src/agent.py --verbose "Who is the CEO of Infosys?"
```

See [setup.md](setup.md) for env keys and full routing test list.

---

## Acceptance criteria (from REQUIREMENTS)

- [x] Agent selects the right tool for ≥ 8/10 hand-crafted routing questions (**10/10** verified)
- [x] Loop terminates (max 10 iterations)
- [x] All four tools return structured JSON for the LLM
- [x] Tool descriptions documented in `design.md` and `agent.py`
- [x] Runs interactively from terminal — `python src/agent.py`
- [x] Phase 03 RAG eval unchanged (`query()` still tested directly)

---

## Routing test summary

| # | Question | Expected tool(s) | Verified |
|---|---|---|---|
| 1 | CEO of Infosys? | `search_docs` | ✓ |
| 2 | Revenue FY2025? | `run_sql` | ✓ |
| 3 | Operating margin FY2025? | `run_sql` | ✓ |
| 4 | INFY close 2026-06-05? | `run_sql` | ✓ |
| 5 | 17% of 842? | `calculate` | ✓ |
| 6 | YoY growth FY2024→FY2025? | `run_sql` + `calculate` | ✓ |
| 7 | Latest news headlines? | `web_search` | ✓ |
| 8 | Chairman on AI strategy? | `search_docs` | ✓ |
| 9 | TCS revenue? | refuse (no tools) | ✓ |
| 10 | Promoter holding latest quarter? | `run_sql` | ✓ |

---

## Teaching path

1. Read [concepts.md](concepts.md) — agent loop theory
2. Follow [setup.md](setup.md) — seed DB, run first query
3. Walk [code-walkthrough.md](code-walkthrough.md) — line-by-line `agent.py`
4. Use [teaching-guide.md](teaching-guide.md) — classroom session plan
5. Review [reflection.md](reflection.md) — lessons before Phase 05
