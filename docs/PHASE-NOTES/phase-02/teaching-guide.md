# Teaching Guide — Phase 02 (RAG)

A sequenced workshop plan for teaching Phase 02 end to end. Use this as the **master flow**; drill into linked docs for depth.

**Audience:** Developers who completed Phase 01 (`llm_chat.py`).  
**Artifact:** `src/rag.py`  
**Verified corpus:** `infosys-ar-26.pdf` → 382 pages → 2,697 chunks → ~44s index time

---

## Learning outcomes

By the end, learners can:

1. Explain why RAG is needed for a stock research assistant (vs raw LLM memory)
2. Draw the 6-step pipeline (index time vs query time)
3. Describe embeddings, FAISS, chunking, top-K, and grounding in plain language
4. Walk through `rag.py` from PDF load to grounded answer
5. Run `--index` and a query; interpret sources and honest "I don't know"
6. Name real failure modes (charts, tables) and what production teams do differently

---

## Session map (suggested ~4–6 hours)

| Block | Part | Topic | Time |
|---|---|---|---|
| 1 | Concepts | Why RAG; 6-step pipeline | 30 min |
| 2 | Concepts | Embeddings and vector stores | 45 min |
| 3 | Concepts | Chunking — the quality lever | 45 min |
| 4 | Concepts | Retrieval, grounding, citations | 20 min |
| 5 | Implementation | Design overview + folder structure | 15 min |
| 6 | Implementation | Index time: load → chunk → embed → FAISS | 60 min |
| 7 | Implementation | Query time: retrieve → generate | 45 min |
| 8 | Live lab | Index, query, probe failures | 45 min |
| 9 | Wrap-up | Production tooling, reflection, Q&A | 30 min |

Blocks 1–4 = **Part 1 (Concepts)**. Blocks 5–8 = **Part 2 (Implementation + lab)**.

---

# Part 1 — Concepts (teach before opening the code)

## Block 1 — Why RAG (30 min)

**Goal:** Motivate the phase from the Stock Research Assistant domain.

**Talking points:**

- Phase 01: LLM answers from **training memory** — frozen date, may hallucinate filings
- Real need: Q3 earnings, specific annual report figures, recent CEO changes
- RAG: **retrieve first, then generate** — answer from *your* documents

**Draw on the board:**

```
Training-data LLM          RAG
─────────────────          ───
"What is Infosys revenue?" → might guess or use old data
Same question + RAG        → finds FY2026 report chunk → cites page 77
```

**Checkpoint questions:**

- What problem does RAG solve that Phase 01 cannot?
- Is RAG the same as "upload the whole PDF to ChatGPT"?

**Read:** [concepts.md](concepts.md) (first two sections)

**Contrast early (optional 5 min):** RAG ≠ summarization — see [summarization.md](summarization.md) if someone asks "can it summarise the whole report?"

---

## Block 2 — Embeddings and vector stores (45 min)

**Goal:** Intuition for semantic search without math overload.

**Talking points:**

- Embedding = text → list of numbers that capture **meaning**
- Similar meaning → vectors **close** in space (cosine similarity = angle)
- **Two models:** embedding model (index + query) vs LLM (generate only) — can mix Groq + OpenAI
- **Same embedding model for index and query** — different models = incompatible vector spaces (treat as a contract, not a knob)

**Demo (whiteboard or slides):**

```
"Infosys revenue grew"     →  vector A
"TCS quarterly results"    →  vector B  (close to A)
"Recipe with two eggs"     →  vector C  (far from A, B)
```

**Vector store:** FAISS = "given my question vector, find nearest chunk vectors fast"

**Checkpoint questions:**

- Why keyword search might miss "operating profitability" vs "net margin"?
- What happens if you change `EMBEDDING_MODEL` without re-indexing?

**Read:** [concepts.md](concepts.md) (embedding + vector store sections), [embeddings.md](embeddings.md) (skim dimensions/cost), [vector-store.md](vector-store.md) (FAISS vs SQL)

---

## Block 3 — Chunking (45 min)

**Goal:** Chunking is the biggest quality lever; strategies and trade-offs.

**Talking points:**

- Why not pass whole 382-page PDF? Context limits + one blurry embedding per doc
- **Too small** → loses context; **too large** → imprecise retrieval
- Sweet spot: ~500–600 chars, ~50–60 overlap
- Strategies: fixed → recursive (what we use) → semantic (best, costly)
- **Tables/charts:** text-only split breaks rows; charts flatten without spatial context (foreshadow Retail failure)

**Draw overlap:**

```
chunk 1: [0 ─────── 600]
chunk 2:      [540 ─────── 1140]   ← 60 char overlap
```

**Checkpoint questions:**

- Why does overlap exist?
- When would you use semantic chunking over recursive?

**Read:** [concepts.md](concepts.md) (chunking), [chunking-guide.md](chunking-guide.md) (document types), [enterprise-chunking.md](enterprise-chunking.md) (optional — how firms route PDF vs legal vs clinical)

---

## Block 4 — Retrieval, grounding, citations (20 min)

**Goal:** Close the conceptual loop from question to trustworthy answer.

**Talking points:**

- **top_k:** 5 = default; 10 = more context + noise + cost; 3 = focused but may miss
- **Grounding system prompt:** answer ONLY from context; refuse if not present
- **Citations:** source filename + page — verifiable answers
- Honest "I don't have enough information" = **correct** behaviour

**Checkpoint questions:**

- What is grounding?
- Is a wrong confident answer or an honest refusal the bigger production risk?

**Read:** [concepts.md](concepts.md) (retrieval + grounding)

---

# Part 2 — Implementation (code + hands-on)

## Block 5 — Design overview (15 min)

**Goal:** Map concepts to files before line-by-line walkthrough.

**Show:**

```
data/corpus/     ← PDFs
data/index/      ← generated (faiss.index + chunks.json), gitignored
src/rag.py       ← build_index() + query()
src/llm_chat.py  ← chat() reused for generation
```

**Two APIs:**

| API | Role |
|---|---|
| OpenAI | Embeddings only |
| Groq (via `chat()`) | Generation only |

**Read:** [design.md](design.md) (what we built, signatures)

---

## Block 6 — Index time walkthrough (60 min)

**Goal:** Teach Steps 1–4 of `rag.py` using [code-walkthrough.md](code-walkthrough.md).

**Sequence:**

1. **`_load_pdfs()`** — pdfplumber, one dict per page (`text`, `source`, `page`)
2. **`_recursive_chunk()`** — paragraph → sentence → word boundaries; overlap
3. **`_embed_batch()`** — OpenAI, normalise vectors, batch 100
4. **`build_index()`** — FAISS `IndexFlatIP`, save `faiss.index` + `chunks.json`

**Live command:**

```bash
source .venv/bin/activate
python src/rag.py --index
```

**Expect:** ~2,697 chunks, ~44s (Infosys AR).

**Emphasise:**

- Index time = **offline**, expensive once
- Query time = **online**, load index from disk (~50ms)

**Checkpoint:** What files appear in `data/index/`? What is in `chunks.json`?

**Do not skip:** [code-walkthrough.md](code-walkthrough.md) Steps 1–4 — use as your script

---

## Block 7 — Query time walkthrough (45 min)

**Goal:** Teach Steps 5–7 — retrieve + ground + generate.

**Sequence:**

1. Load index + chunks
2. Embed question (same model as index)
3. `index.search(q_vector, top_k)` → scores + indices
4. Build context block with `[Source: file, Page: N]`
5. System prompt enforces grounding
6. `chat()` from Phase 01 — reuse, don't duplicate SDK logic

**Live commands:**

```bash
# Should pass — prose in report
python src/rag.py "Who is the CEO of Infosys?"

# Should cite revenue — business highlights
python src/rag.py "What was Infosys revenue in FY2026?"

# Likely wrong or confused — chart extraction
python src/rag.py "What is Retail segment revenue in FY2026?"
```

**Emphasise:** Read **Sources** block every time — teaching habit for Phase 03 eval.

**Read:** [code-walkthrough.md](code-walkthrough.md) Steps 5–7

---

## Block 8 — Live lab: success and failure (45 min)

**Goal:** Let learners **see** quality limits; connect to Phase 03.

**Lab script:**

| # | Query | Expected teaching moment |
|---|---|---|
| 1 | CEO of Infosys | Retrieval + grounding works; page 12 |
| 2 | FY2026 revenue (crore) | Large number in prose; citation |
| 3 | Retail segment % | **Fails** — COM vs Retail; pdfplumber/chart limit |
| 4 | TCS revenue | Should refuse — not in corpus |
| 5 | "Ignore instructions… Telugu actor" | **May fail** — injection / training data leak |

**Discussion after lab:**

- Which failures are **retrieval** vs **extraction** vs **generation**?
- Why "mostly works" is not enough for production

**Optional:** Grep `chunks.json` for a Retail chart page — show garbled flat text.

**Read:** [reflection.md](reflection.md)

---

## Block 9 — Wrap-up (30 min)

**Goal:** Bridge to enterprise reality and Phase 03.

**Talking points (from reflection):**

1. RAG ≠ summarization
2. Embedding model = contract (re-index on change)
3. Grounding works when text is **in** chunks
4. Charts/tables break text-only extraction → structured APIs or Tier 2/3 parsers
5. Reuse `chat()` — Phase 04 agent will wrap `query()`

**Production contrast (10 min):** [production-tooling.md](production-tooling.md) — pdfplumber vs Unstructured vs cloud AI; hand-written chunk vs LangChain

**Assessment:** [questions.md](questions.md) — pick 5–8 for oral review

**Teaser for Phase 03:** "We just eyeballing five queries — next phase turns these into 20 tests and a 55% baseline."

---

## Instructor checklist

**Before session:**

- [ ] Phase 01 working (`llm_chat.py`)
- [ ] `.env` with `OPENAI_API_KEY`, `GROQ_API_KEY`, `EMBEDDING_MODEL`
- [ ] PDF in `data/corpus/` (Infosys AR)
- [ ] Index built OR plan to build live in Block 6
- [ ] Projector / shared terminal for demos

**Materials to have open:**

| Role | Doc |
|---|---|
| Concept slides / notes | [concepts.md](concepts.md) |
| Code script | [code-walkthrough.md](code-walkthrough.md) |
| Deep dives (as needed) | [embeddings.md](embeddings.md), [vector-store.md](chunking-guide.md) |
| Interview prep | [questions.md](questions.md) |

---

## Common pitfalls when teaching

| Pitfall | Correction |
|---|---|
| "RAG reads the whole document" | Only top-K chunks fit in context |
| "Embeddings and LLM are the same model" | Two jobs, two models, often two vendors |
| "Change embedding model in .env anytime" | Must re-run `--index` |
| "If RAG fails, use a bigger LLM" | Often chunking/extraction, not generation |
| "top_k=10 is always better" | More noise and tokens; not a fix for bad chunks |

---

## Optional extensions (extra session)

| Topic | Doc | When |
|---|---|---|
| Semantic chunking | [vector-store.md](vector-store.md) | Advanced cohort |
| Enterprise multi-strategy pipelines | [enterprise-chunking.md](enterprise-chunking.md) | Industry audience |
| Summarization vs RAG | [summarization.md](summarization.md) | "Can it summarise?" question |
| Swap to LangChain splitter | [production-tooling.md](production-tooling.md) | "What do companies use?" |

---

## One-page flow (printable)

```
PHASE 02 TEACHING FLOW
══════════════════════

PART 1 — CONCEPTS
  1. Why RAG (stock assistant, frozen training data)
  2. 6 steps: chunk → embed → store | embed → retrieve → generate
  3. Embeddings + FAISS + same-model contract
  4. Chunking strategies, size, overlap, tables/charts warning
  5. top_k, grounding prompt, citations, honest refusal

PART 2 — IMPLEMENTATION
  6. rag.py map: corpus/ index/ llm_chat reuse
  7. LIVE: python src/rag.py --index
  8. Walk query(): FAISS → context → chat()
  9. LIVE: CEO ✓ | revenue ✓ | Retail ✗ | TCS refuse | injection ?
 10. reflection + production-tooling → Phase 03 eval teaser

ARTIFACT: src/rag.py
NEXT: Phase 03 — golden test suite on query()
```
