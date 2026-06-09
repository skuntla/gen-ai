# Interview Prep — Phase 04 (Agent)

Questions you should be able to answer after completing the agent phase. Pair with [concepts.md](concepts.md) and [code-walkthrough.md](code-walkthrough.md).

---

## Agent loop fundamentals

**Q: What is the agent loop in this project?**  
A: `run_agent()` sends `system` + `user` messages to Groq with tool schemas. If the model returns `tool_calls`, Python executes them, appends `assistant` + `tool` messages with JSON results, and calls Groq again until the model returns plain text or `MAX_ITERATIONS` (10) is hit.

**Q: What is ReAct in one sentence?**  
A: The model **Reasons** (decides what to do), **Acts** (calls a tool), and **Observes** (reads tool output) in a loop until it can answer.

**Q: Workflow vs agent — what's the difference?**  
A: In a workflow, *you* code the step order (`sql` then `calculate`). In an agent, the *LLM* chooses which tools to call and in what order based on prompts and tool descriptions.

**Q: Why cap iterations at 10?**  
A: Prevents infinite tool-call loops, runaway cost, and hung sessions if the model never produces a final answer.

---

## Tools and routing

**Q: How does the LLM know which tool to use?**  
A: It reads the system prompt (routing rules), each tool's `description` (when to use / not use), and the user question. There is no Python `if "CEO" in question` router.

**Q: How does the LLM know the database schema?**  
A: From the `run_sql` tool description string (table and column names, `fiscal_year` format). It does not introspect SQLite at runtime.

**Q: Why return JSON strings from tools instead of Python dicts?**  
A: Tool results go into chat `messages` as text `content`. JSON is structured enough for the LLM to parse and cite, and matches the OpenAI tool-result pattern.

**Q: Why separate `search_docs`, `run_sql`, `calculate`, and `web_search`?**  
A: Each capability has different grounding, latency, and failure modes. Splitting tools improves routing accuracy and keeps results auditable (you see which source was used).

**Q: What question should use `calculate` without `run_sql`?**  
A: Pure arithmetic with numbers already in the question — e.g. "What is 17% of 842?"

**Q: What question needs both `run_sql` and `calculate`?**  
A: Derived metrics from DB values — e.g. YoY revenue growth (fetch two `revenue_cr` rows, then compute percentage change).

---

## Safety and reliability

**Q: How is `run_sql` kept read-only?**  
A: `validate_sql()` requires `SELECT`, blocks forbidden keywords (`INSERT`, `DROP`, etc.), rejects multi-statement SQL, and caps rows at 100.

**Q: Why use `ast` for `calculate` instead of `eval()`?**  
A: `eval()` can execute arbitrary Python. `ast.parse` + whitelisted node types allows only numbers and arithmetic operators.

**Q: What is Groq `tool_use_failed` and how did you handle it?**  
A: Groq returns 400 when Llama emits malformed tool syntax (XML-like tags). We parse `failed_generation` from the error, recover the intended tool call, execute it, and continue the loop.

**Q: What is `parallel_tool_calls=False` for?**  
A: Requests one tool per model turn — more stable tool formatting on Groq/Llama.

---

## Scope and stubs

**Q: How do you handle out-of-scope questions (e.g. TCS revenue)?**  
A: System prompt states Infosys-only scope — refuse without calling tools. No TCS data in DB or index.

**Q: What happens when `TAVILY_API_KEY` is missing?**  
A: `web_search` returns stub JSON (`stub: true`). The agent explains web search is not configured; the loop still terminates.

---

## Architecture choices

**Q: Why raw Groq SDK instead of LangChain or Strands in Phase 04?**  
A: Teach the loop explicitly — every message type, every tool result — before framework abstractions. Strands migration is planned for Phase 10/11.

**Q: Why does the agent call Groq directly but RAG uses `llm_chat.chat()`?**  
A: The agent loop needs native `tools` / `tool_calls` on the Groq API. `search_docs` wraps Phase 02 `query()`, which uses the shared chat helper internally.

**Q: Does Phase 04 replace Phase 03 RAG eval?**  
A: No. `evals/` tests `query()` retrieval/generation quality. Phase 04 adds manual routing tests for tool choice. Phase 09 automates agent trajectory eval.

---

## Testing and acceptance

**Q: What are the Phase 04 acceptance tests?**  
A: 10 hand-crafted routing questions in [design.md](design.md). Pass = ≥ 8/10 correct primary tool + reasonable answer + loop terminates. Verified: 10/10.

**Q: How do you debug wrong tool choice?**  
A: Run with `--verbose`, read `[tool N] name(args)`, then improve system prompt or tool `description` — not hard-coded routing.

---

## Design tradeoffs

**Q: Why does the LLM write SQL instead of a `text_to_sql` hidden pipeline?**  
A: Teaching visibility — you see the SQL in `--verbose` and can debug schema misunderstandings directly.

**Q: What would you add in Phase 05 for this agent?**  
A: Traces/spans for each Groq call and tool execution — latency, tokens, errors — to debug routing and multi-step chains.

**Q: What would Phase 09 change about testing?**  
A: Automate the 10 routing cases as trajectory eval in CI — expected tool sequence + final answer assertions.
