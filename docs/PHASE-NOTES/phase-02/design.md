# Design — Phase 02

## What we built

`src/rag.py` — a RAG pipeline that indexes financial documents and answers questions from them with citations.

```bash
# Build the index from all PDFs in data/corpus/
python src/rag.py --index

# Query the index
python src/rag.py "What was Infosys's operating margin in FY2024?"
```

---

## Folder structure

```
src/
└── rag.py

data/
├── corpus/           ← put your PDF documents here
│   ├── infosys_ar_2024.pdf
│   ├── tcs_ar_2024.pdf
│   └── infosys_q4_transcript.pdf
└── index/            ← generated at index time, never committed to git
    ├── faiss.index
    └── chunks.json
```

---

## Libraries

| Library | Purpose |
|---|---|
| `pdfplumber` | Extract text from PDFs, page by page, preserving structure |
| `faiss-cpu` | In-memory vector store — build index, save to disk, nearest-neighbour search |
| `numpy` | Vector math — normalising embeddings for cosine similarity |
| `requests` | HTTP calls to Ollama embedding API |

`rag.py` imports `chat()` from `src/llm_chat.py` for generation. No LLM SDK imported directly here.

---

## Public function signatures

```python
def build_index(corpus_dir: str, index_dir: str) -> dict:
    # Returns: {"chunks": 318, "documents": 3, "time_seconds": 12.4}

def query(
    question: str,
    index_dir: str = "data/index",
    top_k: int = 5,
    provider: str = None,
    model: str = None,
) -> dict:
    # Returns:
    # {
    #   "answer":        "Infosys operating margin was 21.3% in FY2024...",
    #   "sources": [
    #       {"text": "...", "source": "infosys_ar_2024.pdf", "page": 87, "score": 0.94},
    #       {"text": "...", "source": "infosys_ar_2024.pdf", "page": 88, "score": 0.81},
    #   ],
    #   "input_tokens":  1240,
    #   "output_tokens": 84,
    #   "cost_usd":      0.0,
    #   "latency_ms":    1823,
    # }
```

---

## Internal structure

```
rag.py
│
├── _load_pdfs(corpus_dir) -> list[dict]
│     └── pdfplumber: extract text page by page with source + page metadata
│
├── _chunk_documents(documents) -> list[dict]
│     ├── _fixed_size_chunk(text, size=500, overlap=50)
│     └── _recursive_chunk(text, size=500, overlap=50)   ← default
│
├── _embed_text(text) -> np.ndarray
│     └── POST to Ollama nomic-embed-text → 768-dim vector
│
├── _embed_chunks(texts) -> np.ndarray
│     └── batched calls to _embed_text → shape (n_chunks, 768)
│
├── _format_context(retrieved_chunks) -> str
│     └── formats chunks with [Source: filename, Page: N] labels
│
├── _rag_system_prompt(context) -> str
│     └── "answer from context only" instruction + formatted context
│
├── build_index(corpus_dir, index_dir) -> dict    [PUBLIC]
│     └── load → chunk → embed → FAISS index → save to disk
│
├── query(question, ...) -> dict                  [PUBLIC]
│     └── load index → embed query → FAISS search → chat() → return
│
└── if __name__ == "__main__":
      └── --index flag → build_index, else → query
```

---

## Key design decisions

### `query()` calls `chat()` from `llm_chat.py`, not the LLM directly

`chat()` already handles provider routing, token counting, cost logging, and error handling. If `query()` called the LLM directly, all of that would need to be duplicated.

By calling `chat()`, `rag.py` gets everything for free. When the provider switches in Phase 03, `rag.py` does not change at all.

**Principle: don't duplicate logic. Reuse the abstraction.**

### Index is built once and saved to disk

Embedding 300 chunks takes ~5–10 seconds and consumes API/compute resources. A query must complete in under 2 seconds. Loading a saved FAISS index takes ~50 milliseconds.

Building the index on every query would make the system unusable.

This is the **offline indexing vs online serving** pattern — do the expensive work once offline, serve cheaply online. The same principle behind search engines, recommendation systems, and most production ML systems.

### Same embedding model must be used for index and query

When you index documents with `nomic-embed-text`, every chunk is converted to a point in `nomic-embed-text`'s vector space — a coordinate system it learned during training.

When you query, the question must be converted to a point in **the same coordinate system**. If you use a different embedding model for the query, the query vector lands at a random, meaningless position relative to the index vectors — even if both models produce 768-dimensional vectors.

This is called **incompatible vector spaces**. The result is retrieval failure: FAISS returns random chunks, the LLM answers from garbage context.

**Rule: lock the embedding model when you build the index. Never change it without rebuilding the entire index.**

### The RAG system prompt enforces grounding

The LLM is instructed to answer **only** from the provided context and to cite sources. Without this instruction, the LLM falls back to training data — which defeats the entire purpose of RAG.

```
"Answer using ONLY the context below.
If the answer is not in the context, say: 'I don't have enough information
in the provided documents to answer this.'
Do NOT use your training knowledge. Cite which source you drew from."
```

### `data/index/` is gitignored

The FAISS index and chunks.json are generated artifacts — they can be rebuilt any time from the corpus. Committing binary index files to git is wasteful and causes merge conflicts. The corpus PDFs in `data/corpus/` are also gitignored (large binary files). Both are documented in `.env.example` as things the user must provide locally.

---

## Acceptance criteria

- [x] `python src/rag.py --index` builds the index from all PDFs in `data/corpus/`
- [x] Index can be rebuilt from corpus without manual steps
- [x] Answers cite which chunks were retrieved (source filename + page)
- [x] Pipeline answers questions not in model training data (verified with a recent filing)
- [x] At least 2 chunking strategies implemented and testable via config
- [x] `rag.py` exposes a callable `query()` function usable as an agent tool in Phase 04
