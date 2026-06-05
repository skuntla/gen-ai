# Embeddings — A Deep Dive

## Where embeddings came from

Embeddings were not invented for LLMs. The foundational idea came from **Word2Vec**, published by a team at Google led by Tomas Mikolov in **2013**.

The observation was simple but profound: if you train a neural network to predict surrounding words in a sentence, the internal number representations it learns for each word carry **semantic meaning**.

```
king  - man  + woman  ≈  queen
paris - france + italy ≈  rome
```

The arithmetic worked because the network had learned that "king" and "queen" differ along a "gender" axis, and "paris" and "rome" are both capitals of countries.

This was the moment the field realised: **meaning can be encoded as numbers**.

From Word2Vec, the idea evolved:
- 2017: Transformer architecture (Google's "Attention is All You Need" paper)
- 2018: BERT — whole sentences embedded, not just words
- 2019+: Dedicated embedding models trained specifically for semantic similarity
- Today: Models like OpenAI `text-embedding-3-small` embed entire paragraphs with 1536 numbers

---

## What a vector actually is

A vector is just a list of numbers. Each number is a coordinate in multi-dimensional space.

### Simple 2D example

Imagine you described every company with just two numbers:
- Dimension 1: how technology-focused they are (0 = not at all, 1 = entirely)
- Dimension 2: how large they are (0 = small, 1 = very large)

```
Infosys  → [0.9, 0.8]   (very tech, large)
TCS      → [0.9, 0.9]   (very tech, larger)
Zomato   → [0.7, 0.5]   (tech-ish, mid-size)
Reliance → [0.3, 1.0]   (diversified, very large)
```

Plotted on a graph, Infosys and TCS would be close together. Reliance would be far from both.

```
Large  ↑  Reliance
       │
       │        TCS • Infosys
       │
       │              Zomato
Small  └──────────────────────→
      Not tech         Very tech
```

**Retrieval** = "find the companies closest to this point."

### Real embeddings: 1536 dimensions

Instead of 2 manually chosen dimensions, a real embedding model has **1536 dimensions** — each one learned automatically by the neural network during training. You never see labels like "technology-focus" or "company-size." The model learns its own abstract axes that capture meaning.

Some dimensions might loosely correspond to:
- Is this about finance?
- Is this positive or negative in tone?
- Does this mention a specific company?
- Is this a question or a statement?

But most dimensions have no human-interpretable meaning — they're abstract features the network found useful for predicting relationships between texts.

---

## More concrete examples

### Example 1: Same meaning, different words

```
"Infosys revenue increased 14% year on year"
"Infosys annual sales grew by 14 percent"
"The IT firm reported 14% YoY top-line growth"
```

All three produce vectors that are close together — same meaning, different words.

A keyword search would miss the third one entirely. Semantic search finds all three.

---

### Example 2: Topic clusters

```
Financial texts:
"Operating margin improved to 21.3%"       → near other margin/profit sentences
"EBITDA grew from ₹4,200 cr to ₹5,100 cr"  → near other earnings sentences

News texts:
"CEO steps down amid board disagreement"    → near other management/governance sentences
"Company acquires rival for $2 billion"     → near other M&A sentences

Unrelated:
"The monsoon arrived early this year"       → far from all of the above
```

When you ask "What is the operating margin?", your question vector lands near the first cluster — and FAISS retrieves those chunks.

---

### Example 3: Dimensions in action (simplified)

Suppose we could see 5 of the 1536 dimensions and label them:

| Text | profit-related | company-specific | negative-tone | question | financial |
|---|---|---|---|---|---|
| "Infosys margin 21.3%" | 0.9 | 0.8 | 0.1 | 0.0 | 0.9 |
| "TCS profit rose 12%" | 0.9 | 0.7 | 0.1 | 0.0 | 0.9 |
| "What is the margin?" | 0.7 | 0.2 | 0.1 | 0.9 | 0.8 |
| "CEO resigned today" | 0.1 | 0.6 | 0.6 | 0.0 | 0.3 |

The query "What is the margin?" is most similar to the first two rows — and that's what gets retrieved.

---

## How similarity is measured: cosine similarity

Two vectors are compared by their **angle**, not their distance.

```
cos(θ) = 1.0   → identical meaning (same direction)
cos(θ) = 0.0   → unrelated (perpendicular)
cos(θ) = -1.0  → opposite meaning (opposite direction)
```

Why angle and not distance? Because the absolute magnitude of a vector (how long it is) can vary based on text length. Angle normalises for that.

---

## Embedding models — options and costs

### Cloud (API-based)

| Model | Provider | Dimensions | Input cost | Notes |
|---|---|---|---|---|
| `text-embedding-3-small` | OpenAI | 1536 | $0.02/MTok | Best value, recommended default |
| `text-embedding-3-large` | OpenAI | 3072 | $0.13/MTok | Higher quality, 6x cost |
| `text-embedding-ada-002` | OpenAI | 1536 | $0.10/MTok | Older, use 3-small instead |
| `embed-english-v3.0` | Cohere | 1024 | $0.10/MTok | Strong for English |
| `voyage-3` | Voyage AI | 1024 | $0.06/MTok | Good for financial/legal text |
| `gemini-embedding-004` | Google | 3072 | Free (rate limited) | New, strong quality |

**MTok = per million tokens**

### Local (free, no API call)

| Model | Library | Dimensions | Notes |
|---|---|---|---|
| `all-MiniLM-L6-v2` | `sentence-transformers` | 384 | Fast, small, good for short texts |
| `all-mpnet-base-v2` | `sentence-transformers` | 768 | Better quality, slightly slower |
| `nomic-embed-text` | Ollama | 768 | Run locally via Ollama, no API |
| `mxbai-embed-large` | Ollama | 1024 | Strong local option |

---

## Cost reality check

For this project (10–50 documents, ~500 char chunks):

- 50 documents × 5 chunks each = 250 chunks
- 250 chunks × 500 chars ÷ 4 chars/token = ~31,000 tokens to embed
- At $0.02/MTok: **$0.0006** (less than a tenth of a cent)

You will spend essentially nothing on embeddings for the entire learning path even on paid models.

---

## Strategy for this project

**Index time (one-off):** `text-embedding-3-small` via OpenAI API — cheap, fast, excellent quality.

**Query time (every search):** same model — must use the same embedding model for index and query, otherwise the vectors are in incompatible spaces.

**Alternative if you want zero cost:** `nomic-embed-text` via Ollama — pull it once, run locally forever.

```bash
ollama pull nomic-embed-text
```

---

---

## End-to-end retrieval: a detailed walkthrough

This traces exactly what happens from document ingestion to returning a chunk for a user query.

### Step 1 — Documents are chunked and embedded at index time

You have three chunks from an Infosys annual report:

```
Chunk A: "Infosys reported an operating margin of 21.3% in FY2024, up from 20.1% in FY2023."
Chunk B: "The board approved a final dividend of ₹20 per share for FY2024."
Chunk C: "Revenue from North America grew 8.2% year on year, contributing 61% of total revenue."
```

Each chunk is sent to the embedding model (e.g. `text-embedding-3-small`). The model returns a vector for each:

```
Chunk A → [0.82, 0.11, -0.43, 0.67, 0.29, ...]   # 1536 numbers
Chunk B → [0.21, 0.74, 0.09, -0.31, 0.55, ...]   # 1536 numbers
Chunk C → [0.44, 0.18, -0.12, 0.51, 0.33, ...]   # 1536 numbers
```

FAISS stores all three vectors in an index (a file on disk). The original chunk text is stored separately alongside, keyed by position.

---

### Step 2 — User asks a question

```
User: "What was Infosys's operating margin in FY2024?"
```

This question is sent to the **same embedding model**:

```
Question → [0.79, 0.14, -0.39, 0.71, 0.31, ...]   # 1536 numbers
```

---

### Step 3 — FAISS computes similarity scores

FAISS compares the question vector against every stored chunk vector using cosine similarity:

```
similarity(Question, Chunk A) = 0.94   ← very similar (both about operating margin/FY2024)
similarity(Question, Chunk B) = 0.31   ← not similar (dividend, unrelated)
similarity(Question, Chunk C) = 0.58   ← somewhat similar (also about FY2024 financials)
```

**Why is Chunk A the closest?**
Because both the question and Chunk A contain concepts around "operating margin", "Infosys", and "FY2024". The embedding model learned during training that these concepts belong together — so their vectors point in similar directions in the 1536-dimensional space.

FAISS sorts by score and returns the top-K (e.g. K=2):
```
1st: Chunk A (score 0.94)
2nd: Chunk C (score 0.58)
```

---

### Step 4 — Retrieved chunks are passed to the LLM

The system builds this prompt:

```
CONTEXT:
[Chunk A] Infosys reported an operating margin of 21.3% in FY2024, up from 20.1% in FY2023.
[Chunk C] Revenue from North America grew 8.2% year on year, contributing 61% of total revenue.

QUESTION:
What was Infosys's operating margin in FY2024?

Answer based only on the context above. If the answer is not in the context, say so.
```

The LLM reads the context and responds:

```
Infosys's operating margin in FY2024 was 21.3%, an improvement from 20.1% in FY2023.
Source: Chunk A (Infosys Annual Report FY2024)
```

---

### Who does what — responsibility map

| Step | Who does it | What they do |
|---|---|---|
| Chunk documents | Your code (`rag.py`) | Splits text into ~500 char pieces |
| Embed chunks | Embedding model API | Text → vector (1536 numbers) |
| Store vectors | FAISS | Saves all vectors to an in-memory index |
| Embed query | Same embedding model API | User question → vector |
| Find nearest vectors | FAISS | Computes cosine similarity, returns top-K |
| Generate answer | LLM (Groq/Anthropic) | Reads chunks + question, produces grounded answer |

The embedding model and the LLM never talk to each other directly. Your code (`rag.py`) orchestrates the whole flow — call embedding model, get vector, ask FAISS, get chunks, build prompt, call LLM.

---

### What if FAISS returns the wrong chunk?

This is the most common RAG quality problem. It happens when:

1. **Chunk is too large** — the relevant sentence is buried in a big block of irrelevant text
2. **Chunk is too small** — it's missing the context needed to answer
3. **Wrong embedding model** — a model not trained on financial text may not understand that "margin" and "profitability" are related
4. **K is too low** — the right answer is in chunk #6 but you only retrieved top-3

This is exactly why Phase 03 (Eval) exists — to measure whether retrieved chunks actually match the questions you care about.

---

## The key constraint: same model for index and query

This is the most common RAG mistake. If you embed your documents with `text-embedding-3-small` and then embed your query with `all-MiniLM-L6-v2`, the vectors are in completely different spaces. Similarity scores will be meaningless.

**Lock the embedding model at the start and never change it without rebuilding the entire index.**
