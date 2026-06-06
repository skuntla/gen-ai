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

## Step-by-step walkthrough with code

This section shows exactly what happens at each step with illustrative code.
This is not the final implementation — it is written to make each concept visible.

### Step 1 — Load PDFs and attach metadata

```python
import pdfplumber

def _load_pdfs(corpus_dir):
    documents = []
    for pdf_path in Path(corpus_dir).glob("*.pdf"):
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    documents.append({
                        "text":   text,
                        "source": pdf_path.name,   # "infosys_ar_2024.pdf"
                        "page":   page_num,        # 87
                    })
    return documents
```

Each `document` is a dict with the raw page text plus where it came from.
Metadata (`source`, `page`) is preserved so the final answer can cite its sources.

---

### Step 2 — Chunk documents

```python
def _recursive_chunk(text, size=500, overlap=50):
    # Try splitting on paragraph first, then sentence, then word
    separators = ["\n\n", "\n", ". ", " "]
    chunks = []
    current = text

    for sep in separators:
        if len(current) <= size:
            break
        parts = current.split(sep)
        chunk = ""
        for part in parts:
            if len(chunk) + len(part) <= size:
                chunk += part + sep
            else:
                if chunk:
                    chunks.append(chunk.strip())
                # Start next chunk with overlap from the end of the last chunk
                chunk = chunk[-overlap:] + part + sep
        if chunk:
            chunks.append(chunk.strip())

    return chunks if chunks else [text]
```

Each chunk also carries the same `source` and `page` as the original document it came from — the metadata travels with the chunk through every step.

```python
# What a chunk looks like after Step 2
{
    "text":   "Operating profit for FY2024 stood at ₹29,490 crore, reflecting a
               margin of 21.3%. This was achieved despite headwinds from wage
               hikes implemented in Q1FY24 and softness in the BFSI vertical.",
    "source": "infosys_ar_2024.pdf",
    "page":   87,
}
```

---

### Step 3 — Embed each chunk

```python
import requests
import numpy as np

OLLAMA_URL = "http://localhost:11434/api/embeddings"

def _embed_text(text):
    response = requests.post(OLLAMA_URL, json={
        "model":  "nomic-embed-text",
        "prompt": text,
    })
    vector = response.json()["embedding"]      # list of 768 floats
    vector = np.array(vector, dtype="float32")

    # Normalise so that dot product == cosine similarity
    vector = vector / np.linalg.norm(vector)
    return vector
```

After this step, the chunk above becomes:

```
text   → "Operating profit for FY2024 stood at ₹29,490 crore..."
vector → [ 0.021, -0.143,  0.087,  0.312, -0.056, ... ]   # 768 numbers
```

The numbers have no human-readable meaning individually.
What matters is that chunks about operating margins cluster together in this 768-dimensional space.

---

### Step 4 — Build the FAISS index and save to disk

```python
import faiss
import json

def build_index(corpus_dir, index_dir):
    documents = _load_pdfs(corpus_dir)
    chunks    = _chunk_documents(documents)    # list of dicts

    texts   = [c["text"] for c in chunks]
    vectors = np.array([_embed_text(t) for t in texts])  # shape: (318, 768)

    # Inner product on normalised vectors == cosine similarity
    index = faiss.IndexFlatIP(768)
    index.add(vectors)                         # all 318 vectors loaded in

    # Save index (binary) and chunk metadata (JSON) side by side
    Path(index_dir).mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, f"{index_dir}/faiss.index")
    with open(f"{index_dir}/chunks.json", "w") as f:
        json.dump(chunks, f)

    return {"chunks": len(chunks), "documents": len(documents)}
```

After this, `data/index/faiss.index` holds all 318 vectors in a searchable structure.
`data/index/chunks.json` holds the original text and metadata so we can retrieve it after search.

The index file is binary — FAISS's own format. You cannot open it in a text editor.
The chunks file is plain JSON — you can inspect it to verify what was indexed.

---

### Step 5 — Embed the query and search

```python
def query(question, index_dir="data/index", top_k=5, ...):

    # Load the saved index and chunks
    index  = faiss.read_index(f"{index_dir}/faiss.index")   # ~50ms
    with open(f"{index_dir}/chunks.json") as f:
        chunks = json.load(f)

    # Embed the question using the SAME model used at index time
    q_vector = _embed_text(question)                         # shape: (768,)
    q_vector = q_vector.reshape(1, -1)                       # FAISS expects (1, 768)

    # Find the top_k most similar chunks
    scores, indices = index.search(q_vector, top_k)
    # scores  → [[0.94, 0.81, 0.76, 0.71, 0.65]]
    # indices → [[112,  113,  89,   201,  45 ]]

    retrieved = []
    for score, idx in zip(scores[0], indices[0]):
        chunk = chunks[idx]
        retrieved.append({
            "text":   chunk["text"],
            "source": chunk["source"],
            "page":   chunk["page"],
            "score":  round(float(score), 2),
        })
```

FAISS returns `indices` — positions in the array — not the text itself.
We use those indices to look up the original text in `chunks.json`.

---

### Step 6 — Build the system prompt and call the LLM

```python
    # Format the retrieved chunks into readable context
    context_lines = []
    for r in retrieved:
        context_lines.append(
            f"[Source: {r['source']}, Page: {r['page']}]\n{r['text']}"
        )
    context = "\n\n---\n\n".join(context_lines)

    system_prompt = f"""You are a financial analyst assistant specialising in Indian equities.

Answer using ONLY the context below.
If the answer is not in the context, say: "I don't have enough information in the provided documents to answer this."
Do NOT use your training knowledge. Cite which source you drew from.

CONTEXT:
{context}
"""

    # chat() is imported from llm_chat.py — it handles provider routing
    result = chat(
        user_message=question,
        system=system_prompt,
        provider=provider,
        model=model,
    )

    return {
        "answer":        result["content"],
        "sources":       retrieved,
        "input_tokens":  result["input_tokens"],
        "output_tokens": result["output_tokens"],
        "cost_usd":      result["cost_usd"],
        "latency_ms":    result["latency_ms"],
    }
```

The LLM never sees the raw FAISS scores or indices.
It only sees a formatted block of text and an instruction to answer from it.

---

### Complete data flow end to end

```
INDEX TIME (once)
─────────────────────────────────────────────────────────
PDF files
   → pdfplumber → raw pages with {text, source, page}
   → _recursive_chunk → smaller pieces, same metadata
   → _embed_text (nomic-embed-text) → 768-dim vectors
   → faiss.IndexFlatIP → searchable index
   → saved to disk: faiss.index + chunks.json


QUERY TIME (every question)
─────────────────────────────────────────────────────────
"What was Infosys operating margin FY2024?"
   → _embed_text (same model) → 768-dim query vector
   → faiss.search → top-5 indices + similarity scores
   → chunks[idx] → retrieved text with source/page
   → _format_context → readable context block
   → _rag_system_prompt → "answer from context only" + context
   → chat() in llm_chat.py → LLM answer with citations
   → return {answer, sources, tokens, cost, latency}
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

The system prompt also handles the case where the answer is not in the documents — it instructs the LLM to say so explicitly rather than fabricate an answer.

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
