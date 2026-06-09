# Phase 02 — RAG: Give the LLM Your Data

**Goal:** Answer questions over documents the model was never trained on.

**Artifact:** `src/rag.py`

---

## Contents

| File | What's in it |
|---|---|
| [concepts.md](concepts.md) | The RAG problem, the 6-step pipeline, embeddings, vector stores, chunking |
| [embeddings.md](embeddings.md) | Deep dive: history, how vectors work, dimensions, model options, costs |
| [vector-store.md](vector-store.md) | Vector stores vs regular DBs, FAISS internals, chunking strategies with examples |
| [chunking-guide.md](chunking-guide.md) | In-depth guide: all document types (tables, images, charts, mixed), strategy per type |
| [enterprise-chunking.md](enterprise-chunking.md) | How enterprises handle chunking at scale: classification, sampling, multi-strategy pipelines |
| [production-tooling.md](production-tooling.md) | PDF extractors and chunking libraries vs our Phase 02 code; managed platforms |
| [summarization.md](summarization.md) | Summarization vs RAG: full context, Map-Reduce, Refine — when to use each |
| [design.md](design.md) | What we built, libraries, design decisions, acceptance criteria |
| [code-walkthrough.md](code-walkthrough.md) | Line-by-line teaching guide for `src/rag.py` (workshop script) |
| [teaching-guide.md](teaching-guide.md) | **Master teaching flow** — Part 1 concepts, Part 2 implementation, lab script, checklist |
| [questions.md](questions.md) | Project-specific interview Q&A |
| [INTERVIEW-QUESTIONS-DOCUMENT.md](../INTERVIEW-QUESTIONS-DOCUMENT.md) | Generic challenging interview bank (Phases 01–03) |
| [reflection.md](reflection.md) | Observations after implementation |
