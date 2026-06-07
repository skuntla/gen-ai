# Reflection — Phase 03

1. **Eval replaces eyeballing with a baseline you can defend.** Manual queries in Phase 02 gave useful anecdotes ("CEO works, Retail fails") but no number to compare against. The first Promptfoo run produced **33/60 passes (55%)** — now every chunking, prompt, or model change has a regression reference point. "Mostly works" became "11 of 20 tests fail, and here are which ones."

2. **Identical pass/fail across configs does not mean configs are interchangeable on quality — but it does mean you tiebreak on cost and latency.** All three providers (`rag-top5-70b`, `rag-top10-70b`, `rag-top5-8b`) scored the same on assertions. `top_k=10` did not fix Retail or margin failures because those are corpus/extraction limits, not "missed chunk 6." When quality ties, pick the leaner config: **`rag-top5-70b`** (see [design.md](design.md)).

3. **End-to-end eval (Layer 3) tells you *that* something broke, not always *where*.** A failing Retail test could be bad retrieval, garbled chart extraction, or the LLM misreading good context. Inspecting `--- sources ---` in Promptfoo output and reading `chunks.json` for those pages is the next step — eval is the alarm, layer isolation is the diagnosis.

4. **Assertion design matters as much as the pipeline.** Out-of-scope TCS tests check for refusal but do not ban the string "TCS" — a good answer may say "I don't have TCS revenue in these Infosys documents." Adversarial actor tests add `not-icontains` on names because the model may refuse *and still leak* training data ("…but Chiranjeevi is a famous actor"). Different failure modes, different asserts.

5. **Promptfoo is the orchestrator; the skill is eval discipline.** Enterprises use the same pattern with LangSmith, RAGAS, or custom pytest CI — golden set, offline run, config comparison, regression gate. Phase 03 eval stays relevant when the agent ships in Phase 04: test `query()` for search quality, test the agent separately for tool routing. Deleting the RAG suite would hide failures in the foundation layer.
