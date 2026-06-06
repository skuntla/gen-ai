# Reflection — Phase 02

1. **RAG and summarization are different problems.** Before this phase I assumed both meant "give the LLM a document." RAG retrieves a few relevant chunks by similarity; summarization needs the whole document (or Map-Reduce / Refine). Using RAG to "summarise the report" would only summarise whatever chunks happened to rank highest — not the document.

2. **The embedding model is a contract, not a config knob.** Index and query must use the same model because each model defines its own vector space. Swapping models without rebuilding the index would return plausible-looking but wrong chunks. Lock `EMBEDDING_MODEL` at index time and treat a model change as a full re-index.

3. **Grounding works when the text is actually in the chunks.** Queries like CEO name and total revenue returned correct answers with source and page. When the answer was not in the retrieved text, the system said so instead of inventing a number — that is the behaviour we want. The failure mode to watch is confident wrong answers, not honest "I don't know."

4. **Charts and tables break text-only extraction.** Asking for Retail segment revenue returned COM's percentages (11.7% / 12.2% instead of 13.5% / 12.9%). `pdfplumber` flattens chart pages into a stream of numbers and labels with no spatial link between a bar and its value. Prose RAG is fine for narrative sections; precise numbers from charts need structured data (`yfinance`, Screener.in) or multimodal extraction in a later phase.

5. **Reuse beats duplication.** `query()` delegates to `chat()` from Phase 01 rather than calling an LLM SDK directly. Provider routing, token counts, and cost logging stay in one place. The index is built once and loaded from disk (~50ms) instead of re-embedding on every question. Both decisions keep Phase 02 small and make Phase 04 (agent tools) a thin wrapper over `query()`.
