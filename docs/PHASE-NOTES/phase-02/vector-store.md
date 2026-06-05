# Vector Stores — How to Think About Them

## Is it like a database table?

Yes and no. Think of it as a table with a superpower.

A regular database table for storing text chunks might look like:

```
┌────┬──────────┬─────────────────────────────────────────────────┐
│ id │ source   │ text                                            │
├────┼──────────┼─────────────────────────────────────────────────┤
│ 1  │ doc_a.pdf│ "The cat sat on the mat near the window"        │
│ 2  │ doc_a.pdf│ "It was a warm sunny afternoon in the garden"   │
│ 3  │ doc_b.pdf│ "Dogs are loyal and friendly animals"           │
│ 4  │ doc_b.pdf│ "The weather was cold and the wind was strong"  │
└────┴──────────┴─────────────────────────────────────────────────┘
```

A vector store adds one more column — the embedding:

```
┌────┬──────────┬───────────────────────────────────┬────────────────────────────┐
│ id │ source   │ text                              │ vector (1536 numbers)      │
├────┼──────────┼───────────────────────────────────┼────────────────────────────┤
│ 1  │ doc_a.pdf│ "The cat sat on the mat..."       │ [0.23, -0.41, 0.87, ...]   │
│ 2  │ doc_a.pdf│ "It was a warm sunny afternoon"   │ [0.11, 0.62, -0.33, ...]   │
│ 3  │ doc_b.pdf│ "Dogs are loyal and friendly"     │ [0.21, -0.38, 0.91, ...]   │
│ 4  │ doc_b.pdf│ "The weather was cold..."         │ [0.08, 0.59, -0.29, ...]   │
└────┴──────────┴───────────────────────────────────┴────────────────────────────┘
```

The difference is in how you query it:

| Regular DB | Vector Store |
|---|---|
| `WHERE text LIKE '%cat%'` | "find rows whose vector is similar to this vector" |
| Exact / keyword match | Semantic / meaning match |
| Fast for structured data | Fast for unstructured text |
| SQL | Nearest-neighbour search |

---

## How FAISS stores vectors internally

FAISS doesn't store rows in a table the way a SQL database does. Under the hood it builds a specialised data structure (an index) optimised for one operation: **find the N vectors most similar to this query vector, fast**.

Think of it like a spatial index (similar to how Google Maps finds the 5 nearest coffee shops to your location) — but in 1536 dimensions instead of 2.

```
Disk layout of a FAISS index:

faiss_index.bin          ← the vector index (binary, not human-readable)
faiss_metadata.json      ← the text chunks and source filenames

When you query:
1. Load faiss_index.bin into RAM
2. Send query vector → FAISS scans the index structure
3. Returns row IDs of the top-K closest vectors
4. Look up those IDs in faiss_metadata.json → get the text chunks back
```

FAISS is **in-memory**. The entire index lives in RAM during use. For 10–50 documents this is instant and uses very little memory. For millions of documents you'd use a server-based vector DB like Pinecone or Chroma.

---

## Vector store options

| Store | Type | Best for |
|---|---|---|
| **FAISS** | In-memory, file-backed | Learning, small corpora, no server needed |
| **Chroma** | Local server | Medium projects, easy to query and inspect |
| **Pinecone** | Cloud service | Production, large scale, managed |
| **Weaviate** | Self-hosted or cloud | Production, rich filtering alongside vectors |
| **pgvector** | PostgreSQL extension | Already using Postgres, add vector search to it |

For this project: FAISS for Phases 02–08, move to Chroma if the corpus grows significantly.

---

# Chunking Strategies — Detailed Guide

Chunking is splitting a long document into smaller pieces before embedding.
The goal: each chunk should be **self-contained enough to answer a question on its own**.

---

## Why chunking matters more than people expect

Imagine you have a 50-page book and someone asks: "What did the author say about courage?"

If you embed the whole book as one vector, the answer to "courage" gets drowned out by everything else in the book.

If you embed each paragraph separately, the paragraphs about courage will have vectors that closely match your question — and those get retrieved.

**Smaller, focused chunks = more precise retrieval.**
But too small and a chunk loses the context it needs to make sense.

---

## Strategy 1: Fixed-size chunking

Cut the text every N characters, regardless of where sentences or paragraphs end.

### Input text:
```
The quick brown fox jumped over the lazy dog. It was a beautiful morning.
The sun was shining brightly. The fox ran through the meadow with great speed.
Birds were singing in the trees nearby.
```

### Parameters: chunk_size=60, chunk_overlap=10

```
Chunk 1: "The quick brown fox jumped over the lazy dog. It was a"
Chunk 2: "a beautiful morning. The sun was shining brightly. The"
Chunk 3: "The fox ran through the meadow with great speed. Birds"
Chunk 4: "Birds were singing in the trees nearby."
```

### What you notice:
- Chunk 1 ends mid-sentence ("It was a")
- Chunk 2 starts with "a" — the second half of that sentence
- The overlap (10 chars) means "It was a" appears in both Chunk 1 and Chunk 2

### When to use:
- Quick prototyping
- When documents have no natural paragraph structure (e.g. raw scraped text)

### Trade-offs:
| Pro | Con |
|---|---|
| Simple, fast | Cuts across sentence boundaries |
| Predictable chunk sizes | Context can be split awkwardly |
| Easy to reason about | Lower retrieval quality on long answers |

---

## Strategy 2: Recursive chunking

Try to split on natural boundaries first — paragraphs, then sentences, then words, then characters. Only split smaller if the chunk is still too large.

### The splitting hierarchy:
```
1. Try splitting on:  "\n\n"  (paragraph breaks)
2. If still too big:  "\n"    (line breaks)
3. If still too big:  ". "    (sentence ends)
4. If still too big:  " "     (word boundaries)
5. If still too big:  ""      (individual characters — last resort)
```

### Input text:
```
The fox was clever and fast.

It had lived in the forest for many years.
It knew every path and hiding spot.

One day a hunter arrived.
```

### Parameters: chunk_size=60, chunk_overlap=10

```
Chunk 1: "The fox was clever and fast."           ← split on \n\n (paragraph)
Chunk 2: "It had lived in the forest for many years."    ← split on \n
Chunk 3: "It knew every path and hiding spot."     ← split on \n
Chunk 4: "One day a hunter arrived."              ← split on \n\n
```

### Compare with fixed-size on the same text:
```
Fixed:     "The fox was clever and fast.\n\nIt had lived in"  ← crosses paragraph boundary
Recursive: "The fox was clever and fast."                     ← respects paragraph boundary
```

### When to use:
- Most real documents (PDFs, articles, reports)
- **Default choice for this project**

### Trade-offs:
| Pro | Con |
|---|---|
| Respects natural text boundaries | Chunks can vary in size |
| Higher retrieval quality | Slightly more complex to implement |
| Reads naturally when shown to LLM | Large paragraphs still get split |

---

## Strategy 3: Semantic chunking

Instead of splitting by character count or punctuation, group sentences that are **about the same topic** together into one chunk. When the topic shifts, start a new chunk.

### How it works:
1. Split the text into individual sentences
2. Embed each sentence
3. Calculate similarity between consecutive sentences
4. When similarity drops sharply → topic has changed → start a new chunk

### Input text:
```
Sentence 1: "The fox was known for its speed."
Sentence 2: "It could outrun almost any predator."
Sentence 3: "One morning the fox discovered a beautiful garden."
Sentence 4: "The garden had roses, tulips, and sunflowers."
Sentence 5: "The fox had never seen so many colours."
```

### Similarity between consecutive sentences:
```
S1 → S2: 0.91  (both about fox's speed)
S2 → S3: 0.31  ← BIG DROP — topic shifts from speed to garden
S3 → S4: 0.88  (both about the garden)
S4 → S5: 0.85  (both about the garden's appearance)
```

### Result:
```
Chunk 1: "The fox was known for its speed. It could outrun almost any predator."
Chunk 2: "One morning the fox discovered a beautiful garden. The garden had roses,
          tulips, and sunflowers. The fox had never seen so many colours."
```

Each chunk is a coherent topic, not an arbitrary slice of text.

### When to use:
- High-quality RAG where retrieval accuracy matters most
- Long documents with many distinct topics (annual reports, research papers)

### Trade-offs:
| Pro | Con |
|---|---|
| Best retrieval quality | Requires embedding every sentence (slower + costs more) |
| Chunks match how humans think about topics | Chunks vary widely in size |
| Fewer "broken context" problems | Overkill for short, well-structured documents |

---

## Side-by-side comparison

```
Original: "The fox was fast. It ran daily. One day it found a garden. The garden had flowers."

Fixed-size (40 chars):
  "The fox was fast. It ran daily. One day"
  "ay it found a garden. The garden had fl"
  "flowers."

Recursive:
  "The fox was fast. It ran daily."
  "One day it found a garden."
  "The garden had flowers."

Semantic:
  "The fox was fast. It ran daily."         ← topic: the fox
  "One day it found a garden. The garden    ← topic: the garden
   had flowers."
```

---

## Which to use when

| Situation | Recommended strategy |
|---|---|
| Quick prototype, first pass | Fixed-size |
| Most real documents | Recursive (default) |
| Long documents, mixed topics | Semantic |
| Poor retrieval quality after recursive | Try semantic |
