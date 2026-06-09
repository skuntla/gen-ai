# Reflection — Phase 04

1. **The agent loop is just a conversation with extra message types.** `system` + `user` → LLM returns `tool_calls` → Python runs tools → append `assistant` + `tool` messages → LLM again until plain text. No framework magic in Phase 04 — the loop in `run_agent()` is ~60 lines and teachable line-by-line.

2. **Tool descriptions are routing prompts.** The LLM never opens `sample.db` or the FAISS index. It reads `TOOL_RUN_SQL`'s description (table names, column names, `fiscal_year` format) and writes SQL from that text. When we omitted `'FY2025'` format hints, the model used `fiscal_year = 2025` and got zero rows. Schema documentation in tool definitions is as important as the seed script.

3. **Groq + Llama tool-calling is flaky; recovery is production hygiene.** `tool_use_failed` with XML-like `<function=search_docs{...}</function>` crashed early runs. Parsing `failed_generation` and continuing the loop fixed CEO and narrative queries without changing models. `--verbose` shows `[recover N]` when this path fires.

4. **Multi-tool questions need multiple iterations, not one-shot orchestration.** YoY growth runs `run_sql` (two revenue rows) then `calculate` (`(165641 - 153656) / 153656 * 100`). The model chains tools across loop iterations — workflow steps emerge from the LLM, not from hard-coded Python routing.

5. **Out-of-scope needs explicit scope in the system prompt, not just tool absence.** Test #9 (TCS revenue) initially called `run_sql` because the DB exists and the model tried to help. Adding "Infosys only — refuse other companies without tools" fixed routing. Phase 06 guardrails will formalize this; Phase 04 teaches prompt-level scope.

6. **Stub tools keep the loop runnable without every API key.** `web_search` returns clear stub JSON when `TAVILY_API_KEY` is unset so the agent still terminates gracefully. Live Tavily works when configured; routing test #7 validates tool *choice*, not headline quality.

7. **Phase 03 RAG eval stays; Phase 04 adds a different test surface.** `evals/` still tests `query()` directly (retrieval + generation quality). Phase 04 routing tests are manual (10 questions) — trajectory eval automation lands in Phase 09. Deleting RAG eval would hide foundation regressions when the agent ships.

8. **Raw SDK first was the right call.** We see every iteration, every JSON tool result, and every Groq quirk. Strands migration is documented for Phase 10/11 — not a shortcut for learning the loop.
