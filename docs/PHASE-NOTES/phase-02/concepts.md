# Core Concepts — Phase 02

## The problem RAG solves

In Phase 01, the LLM answered from its training data — knowledge frozen at a point in time, general and sometimes outdated. For a stock research assistant this is a real problem:

- Q3 2025 earnings? The model may not know
- A specific annual report figure? It might hallucinate
- A recent management change? Not in training data

RAG (Retrieval-Augmented Generation) solves this: retrieve the relevant information first, then pass it to the model as context. The model answers from your documents, not from memory.

---

## The RAG pipeline — 6 steps

```
Your documents
      │
      ▼
1. CHUNK     — split documents into small pieces (~500 chars each)
      │
      ▼
2. EMBED     — convert each chunk into a vector (list of numbers)
      │
      ▼
3. STORE     — save all vectors in a vector store (FAISS)
      │
      ▼
                         (at query time)
User question
      │
      ▼
4. EMBED     — convert the question into a vector (same model)
      │
      ▼
5. RETRIEVE  — find the top-K chunks whose vectors are closest to the question vector
      │
      ▼
6. GENERATE  — pass retrieved chunks + question to the LLM → answer
```

Steps 1–3 happen **once** (index time). Steps 4–6 happen **on every query**.

---

## What is an embedding?

An embedding is the model's way of converting text into meaning as a point in space.

```
"Infosys revenue grew 14% YoY"           →  [0.23, -0.41, 0.87, 0.12, ...]  (1536 numbers)
"TCS posted strong quarterly results"     →  [0.21, -0.38, 0.91, 0.09, ...]
"The recipe calls for two eggs"           →  [-0.67, 0.83, -0.12, 0.55, ...]
```

The first two vectors are **close together** in 1536-dimensional space because they're semantically similar. The recipe vector is far away.

Retrieval = "find the chunks whose vectors are closest to my question vector." No keyword matching — pure semantic similarity.

### Why embeddings are separate from the LLM

The LLM generates text. The embedding model converts text to vectors. These are two different models with two different jobs:
- Embedding model: `text → vector` (used at index time and query time)
- LLM: `text → text` (used only at generation time)

You can mix and match: Groq for generation, OpenAI for embeddings.

---

## What is a vector store?

A database optimised for one operation: **given a vector, find the N most similar vectors fast**.

FAISS (Facebook AI Similarity Search) does this in memory — no server, no setup, just a file on disk. For 10–50 documents it's instant.

The similarity metric is typically **cosine similarity** — the angle between two vectors. Vectors pointing in the same direction = similar meaning.

---

## Chunking — the biggest quality lever

### Why chunk at all?

- Embeddings work best on short, focused pieces of text
- The context window has limits — you can't pass 50 full documents to the LLM
- Smaller chunks = more precise retrieval
- Larger context passed to LLM = better answer completeness

The trade-off: too small → loses context. Too large → retrieval is imprecise.

### Three strategies

| Strategy | How | Trade-off |
|---|---|---|
| Fixed-size | Split every N characters | Simple, fast, loses sentence boundaries |
| Recursive | Split on paragraphs → sentences → words | Respects natural text structure, better quality |
| Semantic | Group sentences by meaning similarity | Best quality, most expensive to compute |

We start with fixed-size (simplest to understand), then recursive (better quality), then optionally semantic.

### Chunk size and overlap

```
chunk_size    = 500 chars    # how big each chunk is
chunk_overlap = 50 chars     # how much consecutive chunks share

chunk 1: [0   → 500]
chunk 2: [450 → 950]   ← 50 chars of overlap with chunk 1
chunk 3: [900 → 1400]  ← 50 chars of overlap with chunk 2
```

Overlap ensures a sentence split at a boundary still appears in full in at least one chunk.

---

## Retrieval — top-K search

After embedding the query, FAISS finds the K most similar chunks. Typical values:
- `top_k = 3` — focused, less noise, may miss relevant context
- `top_k = 5` — good default
- `top_k = 10` — more context, but more noise, higher token cost

The retrieved chunks are then assembled into a prompt context block and passed to the LLM.

---

## Grounding and citations

A grounded answer includes which chunks it drew from:

```
Answer: Infosys reported an operating margin of 21.3% in FY2024.

Sources:
- infosys_annual_report_2024.pdf, chunk 42 (page 87)
- infosys_q4_earnings.pdf, chunk 7 (page 3)
```

This makes the answer verifiable and builds trust. Phase 03 (Eval) will check whether the citations are actually relevant.

---

## In the context of the Stock Research Assistant

The corpus consists of real public financial documents:
- Annual reports (PDFs) from BSE/NSE filings
- Earnings call transcripts
- Recent news articles per company

Example query flow:
> "What was Infosys's operating margin in FY2024?"

1. Query embedded → vector
2. FAISS finds top-5 chunks from the Infosys annual report
3. Chunks + query sent to LLM
4. LLM answers: "21.3%, per the FY2024 Annual Report (page 87)"
