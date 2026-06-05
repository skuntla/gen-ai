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

## The key constraint: same model for index and query

This is the most common RAG mistake. If you embed your documents with `text-embedding-3-small` and then embed your query with `all-MiniLM-L6-v2`, the vectors are in completely different spaces. Similarity scores will be meaningless.

**Lock the embedding model at the start and never change it without rebuilding the entire index.**
