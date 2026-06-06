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

### How it works internally — step by step

#### Step 1 — Split into sentences

Take the raw text and split into individual sentences first:

```
Text:
"Dogs are loyal animals. They protect their owners.
Paris is the capital of France. The Eiffel Tower is famous worldwide."

Sentences:
S1: "Dogs are loyal animals."
S2: "They protect their owners."
S3: "Paris is the capital of France."
S4: "The Eiffel Tower is famous worldwide."
```

#### Step 2 — Embed every sentence

Each sentence is sent to the embedding model independently:

```
S1 → [0.82, 0.11, -0.43, ...]   (animals / loyalty)
S2 → [0.79, 0.14, -0.39, ...]   (animals / protection)
S3 → [0.12, 0.71,  0.55, ...]   (geography / France)
S4 → [0.09, 0.68,  0.61, ...]   (geography / landmarks)
```

#### Step 3 — Measure similarity between consecutive sentence pairs

```
similarity(S1, S2) = 0.95  ← very similar (both about dogs)
similarity(S2, S3) = 0.18  ← very different (dogs → Paris)
similarity(S3, S4) = 0.91  ← very similar (both about Paris/France)
```

Plotted as a graph:

```
Similarity
  1.0 │
  0.9 │   ●               ●
  0.8 │
  0.7 │
  0.6 │
  0.5 │  - - - - threshold - - - - -
  0.4 │
  0.3 │
  0.2 │           ●
  0.1 │
      └───────────────────────
         S1→S2   S2→S3   S3→S4
```

#### Step 4 — Find the breakpoints

Any consecutive pair whose similarity drops **below the threshold (e.g. 0.5)** is a topic boundary:

```
S1 "Dogs are loyal animals."        ┐
S2 "They protect their owners."     ┘  → Chunk 1 (topic: dogs)

                                       ← BREAKPOINT (similarity 0.18 < 0.5)

S3 "Paris is the capital of France."┐
S4 "The Eiffel Tower is famous..."  ┘  → Chunk 2 (topic: Paris)
```

#### Step 5 — Output: topic-coherent chunks

```
Chunk 1: "Dogs are loyal animals. They protect their owners."
Chunk 2: "Paris is the capital of France. The Eiffel Tower is famous worldwide."
```

#### Compare to fixed-size on the same text (60-char limit):

```
Fixed Chunk 1: "Dogs are loyal animals. They protect their"   ← cuts mid-sentence
Fixed Chunk 2: "their owners. Paris is the capital of Fran"  ← mixes dogs + Paris!
Fixed Chunk 3: "France. The Eiffel Tower is famous worldwide"
```

Fixed-size chunk 2 mixes two completely unrelated topics in one chunk. When someone asks "What is Paris the capital of?", the retrieved chunk also contains dog content — noise that confuses the LLM. Semantic chunking eliminates that noise.

### How it knows which sentences to group together

The algorithm never compares all possible combinations. It only ever compares **consecutive sentence pairs**, one at a time, left to right — like reading a book and placing a bookmark whenever the topic changes.

```
S1: "Dogs are loyal animals."
S2: "They protect their owners."         compare S1↔S2 → 0.95 (similar) → same chunk
S3: "Dogs also make great companions."   compare S2↔S3 → 0.88 (similar) → same chunk
S4: "Training a dog takes patience."     compare S3↔S4 → 0.82 (similar) → same chunk
S5: "Paris is the capital of France."    compare S4↔S5 → 0.11 (different) → NEW CHUNK ✂
S6: "The Eiffel Tower is iconic."        compare S5↔S6 → 0.93 (similar) → same chunk
S7: "The Seine river runs through it."   compare S6↔S7 → 0.87 (similar) → same chunk
```

Result:
```
Chunk 1: S1 + S2 + S3 + S4   (all about dogs)
Chunk 2: S5 + S6 + S7        (all about Paris)
```

The algorithm never asked "is S1 related to S5?" — it only ever looks one step ahead.

---

### The problem: gradual topic drift

Real documents don't always switch topics suddenly. Sometimes they drift slowly:

```
S1: "Dogs are loyal animals."
S2: "They protect their owners."
S3: "Owners need to train their pets properly."
S4: "Training requires patience and consistency."
S5: "Consistent habits are key to any skill."
S6: "Learning a new language also requires daily practice."
S7: "French is spoken in Paris and across Europe."
```

Pairwise similarities:
```
S1↔S2: 0.92   S2↔S3: 0.75   S3↔S4: 0.81
S4↔S5: 0.61   S5↔S6: 0.52   S6↔S7: 0.58
```

With threshold 0.5, no cut ever happens — everything ends up in one chunk even though S1 and S7 have nothing to do with each other. Adjacent pair comparison fails on gradual drift.

---

### The fix: sliding window average

Instead of comparing the current sentence to just the previous one, compare it to the **average of the last N sentences**:

```
Window size = 3

When evaluating S5:
  Compare S5 to average of [S2, S3, S4] → similarity 0.58  (still ok)

When evaluating S6:
  Compare S6 to average of [S3, S4, S5] → similarity 0.41  ← drops below 0.5
  → BREAKPOINT ✂
```

The window smooths out gradual drift and catches the point where the topic has genuinely moved on — even when no single step was a dramatic drop.

---

### Three comparison approaches

| Approach | Compares | Good for |
|---|---|---|
| Adjacent pairs | S(n) vs S(n-1) | Sharp topic switches |
| Sliding window | S(n) vs average of last K sentences | Gradual topic drift (recommended) |
| All pairs | S(n) vs every other sentence | Too expensive, rarely used |

Most production implementations (including LangChain's `SemanticChunker`) use adjacent pairs by default but let you configure the window size.

---

### The threshold — how strict should the breakpoint be?

```
Low threshold (e.g. 0.3)  → breaks less often → larger chunks, fewer splits
High threshold (e.g. 0.7) → breaks more often → smaller chunks, may over-split related sentences
```

Start at 0.5. Test retrieval on 5 real questions. Adjust if needed.

### The cost trade-off

Semantic chunking embeds every individual sentence to find breakpoints — then discards those sentence-level embeddings and re-embeds the final chunks.

```
Document with 200 sentences:
  Fixed-size:  ~20 embedding API calls (one per final chunk)
  Semantic:    ~200 + 20 = ~220 embedding API calls
```

About 10x more embedding calls at index time. At $0.02/MTok this is still fractions of a cent — negligible cost. But it's slower to build the index.

### When to use:
- High-quality RAG where retrieval accuracy matters most
- Long documents with many distinct topics (annual reports, research papers)
- When fixed or recursive chunking gives poor retrieval results

### Trade-offs:
| Pro | Con |
|---|---|
| Best retrieval quality | Requires embedding every sentence (slower at index time) |
| Chunks match how humans think about topics | Chunks vary widely in size |
| Fewer "broken context" problems | Overkill for short, well-structured documents |
| No arbitrary size limits | ~10x more embedding calls at index time |

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
