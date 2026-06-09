# Teaching Guide — Phase 04 (Agent)

A sequenced workshop plan for teaching Phase 04 end to end. Use this as the **master flow**; drill into linked docs for depth.

**Audience:** Learners who completed Phases 01–03 (chat, RAG, eval baseline 55%).  
**Artifact:** `src/agent.py`  
**Verified:** 10/10 routing tests | four tools | Groq `llama-3.3-70b-versatile`

---

## Learning outcomes

By the end, learners can:

1. Explain the agent loop: think → act (tool) → observe → repeat
2. Distinguish workflow (you code the steps) from agent (LLM picks tools)
3. Read tool descriptions as routing prompts, not just API metadata
4. Trace a question through `run_agent()` — messages, Groq calls, tool JSON, final answer
5. Implement and safety-check `run_sql` (SELECT-only) and `calculate` (ast eval)
6. Explain why schema hints live in tool descriptions, not DB introspection
7. Handle Groq `tool_use_failed` and why recovery exists
8. Run the 10 routing acceptance tests and interpret `--verbose` output
9. Explain why Phase 03 RAG eval stays when the agent ships

---

## Session map (suggested ~4–6 hours)

| Block | Part | Topic | Time |
|---|---|---|---|
| 1 | Concepts | Agent loop vs one-shot RAG | 25 min |
| 2 | Concepts | Tool descriptions = routing prompts | 30 min |
| 3 | Concepts | ReAct mental model; message types | 25 min |
| 4 | Setup | Seed DB, env keys, first run | 20 min |
| 5 | Implementation | Walk Steps 1–2: prompt + `search_docs` | 40 min |
| 6 | Implementation | Walk Step 2: `run_sql` + schema hints | 45 min |
| 7 | Implementation | Walk Step 3: `calculate` + multi-tool chain | 35 min |
| 8 | Implementation | Walk Step 4: `web_search` + stub pattern | 25 min |
| 9 | Live lab | Routing tests 1–6 with `--verbose` | 45 min |
| 10 | Live lab | Routing tests 7–10 + out-of-scope | 30 min |
| 11 | Wrap-up | Reflection, Phase 05 observability | 25 min |

Blocks 1–3 = **Part 1 (Concepts)**. Blocks 4–10 = **Part 2 (Implementation + lab)**.

---

# Part 1 — Concepts (teach before coding)

## Block 1 — Why an agent (25 min)

**Start with Phase 03 pain:** RAG eval tests one capability. Real users ask mixed questions:

| User question | Right capability |
|---|---|
| CEO of Infosys? | RAG (`search_docs`) |
| Revenue FY2025? | SQL (`run_sql`) |
| 17% of 842? | Calculator (`calculate`) |
| Latest news? | Web (`web_search`) |

**Talking point:** Phase 02 `query()` always runs RAG. Phase 04 lets the **LLM choose** the capability.

**Demo:** Same codebase, four question types — show `--verbose` tool names change.

---

## Block 2 — Tool descriptions (30 min)

**Exercise:** Read `TOOL_RUN_SQL` description aloud. Ask: "How would you write SQL for promoter holding?"

Learners should infer: table `shareholding`, columns `promoter_pct`, `quarter`.

**Key line:** The LLM never runs `PRAGMA table_info`. Your description **is** the schema doc.

**Failure story:** `fiscal_year = 2025` vs `'FY2025'` — fix by improving description, not Python routing.

---

## Block 3 — Message types and ReAct (25 min)

Draw on whiteboard:

```
system → user → assistant(tool_calls) → tool(result) → assistant(text)
```

**ReAct:** Reason (LLM) + Act (tool) + Observe (JSON result) in a loop.

**Contrast with workflow:**

```python
# Workflow — you decide
rows = run_sql("SELECT ...")
answer = calculate(f"({rows[1]}-{rows[0]})/{rows[0]}*100")

# Agent — LLM decides order and expressions
run_agent("YoY revenue growth FY2024 to FY2025?")
```

---

# Part 2 — Implementation + lab

## Block 4 — Setup (20 min)

Follow [setup.md](setup.md):

```bash
pip install -r requirements.txt
python scripts/seed_sample_db.py
python src/agent.py --verbose "Who is the CEO of Infosys?"
```

Checklist: `GROQ_API_KEY`, `data/index/`, `data/sample.db`.

---

## Block 5 — `search_docs` only mental model (40 min)

Use [code-walkthrough.md](code-walkthrough.md) Steps 1–5.

**Live trace:** CEO question — two Groq calls, one `search_docs`.

**Discuss:** Why JSON tool results? LLM needs structured text in `role: tool` messages.

---

## Block 6 — `run_sql` (45 min)

Walk `validate_sql` + `tool_run_sql`.

**Live:**

```bash
python src/agent.py --verbose "What is the operating margin for FY2025?"
```

**Safety demo (optional):** Show that `DELETE FROM financials` would return `{"error": "Only SELECT..."}` if the model tried it.

**Lab:** Learners write the SQL by hand for test #10 (promoter %), then compare to model's query.

---

## Block 7 — `calculate` (35 min)

Walk `safe_calculate` / `ast` — why not `eval()`.

**Live:**

```bash
python src/agent.py --verbose "What is 17% of 842?"
python src/agent.py --verbose "What is YoY revenue growth from FY2024 to FY2025?"
```

Count iterations in `--verbose` output. Expect 2 tools before final answer on #6.

---

## Block 8 — `web_search` (25 min)

**Stub vs live:** Comment out `TAVILY_API_KEY` → stub JSON. Restore key → headlines.

**Point:** Stub keeps the loop teachable without every API key on day one.

---

## Block 9–10 — Routing lab (75 min)

Run all 10 tests from [design.md](design.md) with `--verbose`. Score sheet:

| # | Pass? | Tool(s) seen | Notes |
|---|---|---|---|
| 1 | | | |
| ... | | | |
| 10 | | | |

**Pass criteria:** ≥ 8/10. Discuss failures — usually prompt/schema, not missing `if` statements.

**Test #9 special:** TCS revenue must **refuse without tools**. System prompt scope line is the fix.

---

## Block 11 — Wrap-up (25 min)

**Reflection prompts** (see [reflection.md](reflection.md)):

1. What was hardest to debug without `--verbose`?
2. Where would you add tracing in Phase 05?
3. Why keep `evals/` when the agent exists?

**Preview Phase 05:** Every `[tool N]` line becomes a span in a trace timeline.

**Preview Phase 09:** The 10 manual tests become automated trajectory eval.

---

## Instructor cheat sheet

| Learner question | Point to |
|---|---|
| How does LLM know DB schema? | `TOOL_RUN_SQL` description + [code-walkthrough Step 6](code-walkthrough.md) |
| Why two Groq calls for one answer? | Tool call iteration + [code-walkthrough Step 11](code-walkthrough.md) |
| CEO query crashed earlier | Groq recovery + [reflection #3](reflection.md) |
| Strands vs raw SDK? | [design.md Strands note](design.md) — Phase 10/11 |
| Delete RAG eval? | No — [reflection #7](reflection.md) |

---

## Homework (optional)

1. Add one routing test (e.g. "What was INFY close on lowest volume day?")
2. Break `TOOL_RUN_SQL` description on purpose — watch SQL fail — fix it
3. Run Phase 03 `./evals/run_eval.sh` — confirm RAG baseline unchanged
