# Code Walkthrough — `src/rag.py`

Line-by-line guide to reading and teaching `rag.py`. Use this as a workshop script when walking someone through the Phase 02 implementation.

For architecture and design decisions, see [design.md](design.md). For theory (embeddings, chunking strategies, vector stores), see the linked docs in each section — this file focuses on **how the code works**.

**Verified run (Infosys annual report):** 382 pages → 2,697 chunks → ~44s to index.

---

## How to read this file

Each step follows the same structure:

1. Where it sits in the pipeline
2. The code (from the real file)
3. Line-by-line explanation
4. What this step does **not** do
5. Mental model

Work through one step at a time. Run the commands yourself between steps where noted.

---

## Big picture

```
INDEX TIME  (python src/rag.py --index)
────────────────────────────────────────────────────────────
PDF files in data/corpus/
  → _load_pdfs()           Step 1 — extract text + metadata per page
  → _chunk_documents()     Step 2 — split pages into smaller pieces
  → _embed_batch()         Step 3 — convert text to vectors (OpenAI)
  → build_index()          Step 4 — FAISS index + save to disk


QUERY TIME  (python src/rag.py "your question")
────────────────────────────────────────────────────────────
Question string
  → query()                Step 5 — load index, embed question, FAISS search
  → system prompt + chat() Step 6 — grounded answer via Phase 01
  → CLI                    Step 7 — print result
```

Two APIs, two jobs:

| API | Used for | Function |
|---|---|---|
| OpenAI | Embeddings only | `_embed_text`, `_embed_batch` |
| Groq (via `chat()`) | Answer generation | `query()` → `llm_chat.chat()` |

---

## Step 0 — Setup: imports, config, singleton client

### Where it sits

Everything above the pipeline functions. Runs once when the module loads.

### The code

```python
import argparse
import json
import os
import sys
import time
from pathlib import Path

import faiss
import numpy as np
import pdfplumber
from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent))
from llm_chat import chat

load_dotenv()

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = 1536

_openai_client = None

def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY is not set in your .env file.")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client
```

### Line-by-line

| Import | Role |
|---|---|
| `argparse` | CLI — `--index` flag and question string |
| `json` | Read/write `chunks.json` (chunk metadata) |
| `Path` | Find PDFs, read/write index files |
| `pdfplumber` | Extract text from PDF pages |
| `faiss` | Vector store — nearest-neighbour search |
| `numpy` | Vector math — normalising embeddings |
| `OpenAI` | Embedding API (not used for chat in this file) |
| `chat` from `llm_chat` | Answer generation — reuses Phase 01 |

**`sys.path.insert(0, ...)`** — When you run `python src/rag.py` from the project root, Python does not automatically include `src/` on the import path. This line adds it so `llm_chat.py` can be imported as a sibling module.

**`load_dotenv()`** — Reads `.env` (API keys, model names).

**`EMBEDDING_MODEL`** — Which embedding model to use. Default: `text-embedding-3-small`.

**`EMBEDDING_DIM = 1536`** — Hardcoded because FAISS needs to know vector size when building the index. If you change the embedding model, update both `EMBEDDING_MODEL` and `EMBEDDING_DIM`, then rebuild the index.

### Singleton client (`_get_openai_client`)

Pattern: create the OpenAI client **once**, reuse it for every embedding call.

```
1st call  → _openai_client is None → create client → store it
2nd call  → _openai_client exists  → reuse
...
27th call → reuse (during indexing, ~27 batches of 100 chunks)
```

- `_openai_client = None` — module-level storage, starts empty
- `global _openai_client` — assignment inside the function updates the module variable, not a local copy
- Lazy initialization — client is created on first use, not at import time

This is not a singleton class; it is a function-based singleton, which is common in Python scripts. Scope is **one client per Python process** (one run of the command).

### What Step 0 does not do

- Does not read PDFs
- Does not call any API yet
- Does not build or load the FAISS index

### Mental model

```
rag.py loads
  → read .env
  → set EMBEDDING_MODEL, EMBEDDING_DIM
  → OpenAI client = not created yet (waits for first embed call)
  → chat() import ready from Phase 01
```

---

## Step 1 — `_load_pdfs()`: extract text from PDFs

### Where it sits

First step inside `build_index()`. Input: folder path. Output: list of page dicts.

### The code

```47:65:src/rag.py
def _load_pdfs(corpus_dir: str) -> list[dict]:
    """Extract text from every PDF in corpus_dir, one entry per page."""
    pdf_files = list(Path(corpus_dir).glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in '{corpus_dir}'.")

    documents = []
    for pdf_path in pdf_files:
        print(f"  Loading {pdf_path.name} ...", flush=True)
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text and text.strip():
                    documents.append({
                        "text":   text.strip(),
                        "source": pdf_path.name,
                        "page":   page_num,
                    })
    return documents
```

### Line-by-line

1. **`Path(corpus_dir).glob("*.pdf")`** — Find every `.pdf` in `data/corpus/`. Adding more PDFs requires no code change.

2. **Empty folder check** — Fail fast with a clear error instead of building an empty index.

3. **`pdfplumber.open(pdf_path)`** — Opens the PDF. The `with` block ensures the file is closed when done.

4. **`enumerate(pdf.pages, start=1)`** — Page numbers start at 1 to match what you see in a PDF reader (important for citations).

5. **`page.extract_text()`** — Reads the text layer of the page as a plain string. Works well for prose. For chart-heavy pages, numbers and labels are extracted but **spatial layout is lost** — see [reflection.md](reflection.md) and [chunking-guide.md](chunking-guide.md).

6. **`if text and text.strip()`** — Skip blank or image-only pages.

7. **The page dict** — Three fields, attached at the earliest possible point:

   ```python
   {
       "text":   "Revenue for the year stood at ₹1,78,650 crore...",
       "source": "infosys-ar-26.pdf",
       "page":   16,
   }
   ```

   Every chunk derived from this page inherits the same `source` and `page` through to the final citation.

### Verified output

```
Loading PDFs from 'data/corpus' ...
  Loading infosys-ar-26.pdf ...
  382 pages from 1 document(s).
```

382 non-blank pages from one PDF.

### What Step 1 does not do

| Does | Does not |
|---|---|
| Read PDFs from disk | Chunk text |
| Extract text per page | Embed anything |
| Attach source + page metadata | Call any LLM or API |
| Skip blank pages | Build the FAISS index |

### Mental model

```
data/corpus/infosys-ar-26.pdf
  → pdfplumber: page 1, page 2, ... page 382
  → list of 382 dicts {text, source, page}
  → passed to _chunk_documents()
```

---

## Step 2 — `_chunk_documents()` and `_recursive_chunk()`: split pages into pieces

### Where it sits

Second step in `build_index()`. Takes the page list from Step 1. Produces a longer list of smaller chunk dicts.

Theory: [vector-store.md](vector-store.md) (chunk size, overlap, strategies).

### Why chunk at all

1. **Context window** — You cannot pass 382 full pages to the LLM on every query.
2. **Retrieval precision** — One vector per 50-page document averages all topics. One vector per paragraph is focused and retrieves precisely.

For Infosys: 382 pages → **2,697 chunks** (roughly 7 chunks per page on average).

### `_recursive_chunk()` — the splitter

```72:111:src/rag.py
def _recursive_chunk(text: str, size: int = 600, overlap: int = 60) -> list[str]:
    ...
    for sep in ["\n\n", "\n", ". ", " "]:
        ...
```

**Defaults:** `size=600` characters, `overlap=60` characters.

**Algorithm:**

1. If text fits in `size`, return it as one chunk.
2. Try separators in order: paragraph (`\n\n`) → line (`\n`) → sentence (`. `) → word (` `).
3. Accumulate parts into `current` until adding the next part would exceed `size`.
4. When full, save the chunk, then start the next chunk with the **last 60 characters** of the previous chunk (overlap).
5. If no separator works, hard-split every `size - overlap` characters.

**Overlap example:**

```
Chunk 1 ends:  "...operating margin expanded to 21.3% in FY2026."
Chunk 2 starts: "21.3% in FY2026. Management commentary noted..."
               ↑ same 60 chars copied from end of Chunk 1
```

A sentence split at a chunk boundary still appears in full in at least one chunk.

### `_chunk_documents()` — apply to all pages, keep metadata

```114:130:src/rag.py
def _chunk_documents(
    documents: list[dict],
    size: int = 600,
    overlap: int = 60,
    min_len: int = 50,
) -> list[dict]:
    ...
```

For each page dict:

1. Call `_recursive_chunk(doc["text"])`.
2. Drop chunks shorter than 50 characters (`min_len`) — noise like page numbers or headers alone.
3. Copy `source` and `page` from the parent page into every chunk.

Output chunk dict:

```python
{
    "text":   "Operating profit for FY2026 stood at ₹29,490 crore...",
    "source": "infosys-ar-26.pdf",
    "page":   87,
}
```

Same shape as a page dict, but `text` is a smaller piece.

### What Step 2 does not do

| Does | Does not |
|---|---|
| Split text at natural boundaries | Embed text |
| Apply overlap at chunk boundaries | Call OpenAI |
| Carry metadata into every chunk | Write to disk |

### Mental model

```
382 page dicts
  → _recursive_chunk per page
  → filter out chunks < 50 chars
  → 2,697 chunk dicts (text + source + page)
  → passed to _embed_batch()
```

---

## Step 3 — `_embed_text()` and `_embed_batch()`: text to vectors

### Where it sits

Third step in `build_index()`. Also used at query time to embed the question. Theory: [embeddings.md](embeddings.md).

### `_normalise()` — prepare for cosine similarity

```137:139:src/rag.py
def _normalise(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    return vector / norm if norm > 0 else vector
```

Divides the vector by its length so it has unit magnitude (length = 1).

Why: FAISS uses **inner product** (`IndexFlatIP`). On normalised vectors, inner product equals **cosine similarity**. Same ranking, simpler math.

### `_embed_text()` — single string

```142:146:src/rag.py
def _embed_text(text: str) -> np.ndarray:
    client = _get_openai_client()
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return _normalise(np.array(response.data[0].embedding, dtype="float32"))
```

1. Get the singleton OpenAI client.
2. Call `embeddings.create` with `text-embedding-3-small`.
3. Receive 1,536 floats.
4. Convert to `numpy` array, normalise, return.

Example:

```
"Operating profit for FY2026 stood at ₹29,490 crore..."
  → [0.021, -0.143, 0.087, 0.312, ...]   # 1,536 numbers
```

Individual numbers have no human-readable meaning. Chunks about the same topic land close together in this 1,536-dimensional space.

### `_embed_batch()` — many strings efficiently

```149:166:src/rag.py
def _embed_batch(texts: list[str], batch_size: int = 100) -> np.ndarray:
    ...
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        ...
    return np.array(all_vectors, dtype="float32")
```

- Sends up to 100 texts per API call instead of one call per chunk.
- 2,697 chunks → 27 API calls.
- Returns a 2D array: shape `(2697, 1536)` — one row per chunk.

Progress output during indexing:

```
Embedded 100/2697 chunks ...
Embedded 200/2697 chunks ...
...
Embedded 2697/2697 chunks ...
```

### Same model at index and query time

Both `_embed_batch()` (index) and `_embed_text()` inside `query()` (question) use `EMBEDDING_MODEL`. Changing the model without rebuilding the index breaks retrieval — see [questions.md](questions.md).

### What Step 3 does not do

| Does | Does not |
|---|---|
| Convert text to vectors | Store vectors in FAISS |
| Normalise for cosine similarity | Generate LLM answers |
| Batch API calls for efficiency | Save anything to disk |

### Mental model

```
2,697 chunk texts
  → OpenAI embeddings API (27 batches)
  → numpy array shape (2697, 1536)
  → passed to faiss.IndexFlatIP.add()
```

---

## Step 4 — `build_index()`: tie index time together and save to disk

### Where it sits

Public function called by `python src/rag.py --index`. Orchestrates Steps 1–3 and writes output files.

### The code

```173:207:src/rag.py
def build_index(
    corpus_dir: str = "data/corpus",
    index_dir: str = "data/index",
) -> dict:
    ...
    documents = _load_pdfs(corpus_dir)
    chunks = _chunk_documents(documents)
    vectors = _embed_batch([c["text"] for c in chunks])

    index = faiss.IndexFlatIP(EMBEDDING_DIM)
    index.add(vectors)

    faiss.write_index(index, f"{index_dir}/faiss.index")
    with open(f"{index_dir}/chunks.json", "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    ...
```

### Line-by-line

1. **`_load_pdfs`** → 382 page dicts
2. **`_chunk_documents`** → 2,697 chunk dicts
3. **`_embed_batch`** → `(2697, 1536)` numpy array
4. **`faiss.IndexFlatIP(1536)`** — Create an empty index. `IP` = inner product. On normalised vectors, this is cosine similarity.
5. **`index.add(vectors)`** — Insert all 2,697 vectors. FAISS assigns each a position (0, 1, 2, ... 2696).
6. **Save two files:**

   | File | Contents | Format |
   |---|---|---|
   | `faiss.index` | All vectors in searchable structure | Binary — not human-readable |
   | `chunks.json` | Original text + source + page for each position | JSON — inspectable |

   FAISS returns **indices** (positions), not text. You need `chunks.json` to look up what each index points to.

7. **Return stats:** `{"chunks": 2697, "documents": 1, "time_seconds": 44.5}`

### Offline indexing pattern

Embedding 2,697 chunks takes ~44 seconds. Loading a saved index takes ~50 milliseconds. Build once, query many times. See [design.md](design.md).

### What Step 4 does not do

| Does | Does not |
|---|---|
| Run the full index pipeline | Answer questions |
| Save index + metadata to disk | Call `chat()` |

### Mental model

```
build_index()
  PDF → pages → chunks → vectors → FAISS
  write faiss.index + chunks.json to data/index/
```

---

## Step 5 — `query()` part 1: load index, embed question, retrieve chunks

### Where it sits

First half of `query()`. Runs on every question. Loads work done at index time.

### The code

```234:259:src/rag.py
    index_path  = Path(index_dir) / "faiss.index"
    chunks_path = Path(index_dir) / "chunks.json"

    if not index_path.exists():
        raise FileNotFoundError(...)

    index = faiss.read_index(str(index_path))
    with open(chunks_path, encoding="utf-8") as f:
        chunks = json.load(f)

    q_vector = _embed_text(question).reshape(1, -1)
    scores, indices = index.search(q_vector, top_k)

    retrieved: list[dict] = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        c = chunks[idx]
        retrieved.append({...})
```

### Line-by-line

1. **Check index exists** — If you forgot `--index`, fail with a helpful message.

2. **Load from disk** — `faiss.read_index` (~50ms). `json.load` for chunk metadata.

3. **Embed the question** — Same `_embed_text()`, same `EMBEDDING_MODEL` as index time. Question becomes a point in the same vector space as the chunks.

4. **`.reshape(1, -1)`** — FAISS expects shape `(1, 1536)` (one query vector), not `(1536,)`. Without reshape, search fails or returns wrong results.

5. **`index.search(q_vector, top_k=5)`** — Find the 5 nearest vectors by cosine similarity.

   Returns two arrays:
   ```
   scores  → [0.712, 0.698, 0.677, 0.651, 0.643]
   indices → [  11,    14,    12,   143,   294]
   ```

   `indices` are **positions** in the chunk array, not page numbers.

6. **Look up chunk text** — `chunks[idx]` gets the original text + metadata for each index.

7. **Build `retrieved` list** — Each entry has `text`, `source`, `page`, `score`.

Example from a real query ("Who is the CEO of Infosys?"):

```
[0.712]  infosys-ar-26.pdf  p.12   ← highest similarity
[0.698]  infosys-ar-26.pdf  p.15
```

### What Step 5 does not do

| Does | Does not |
|---|---|
| Load saved index | Call the LLM yet |
| Embed the question | Format the system prompt |
| Return top-K similar chunks | Generate the final answer |

### Mental model

```
"Who is the CEO of Infosys?"
  → embed question → vector
  → FAISS search → top 5 indices
  → chunks.json lookup → 5 text blocks with source/page
```

---

## Step 6 — `query()` part 2: system prompt, `chat()`, return result

### Where it sits

Second half of `query()`. Takes retrieved chunks, grounds the LLM, returns the final answer dict.

### The code

```261:291:src/rag.py
    context = "\n\n---\n\n".join(
        f"[Source: {r['source']}, Page: {r['page']}]\n{r['text']}"
        for r in retrieved
    )

    system_prompt = (
        "You are a financial analyst assistant specialising in Indian equities.\n\n"
        "Answer using ONLY the context below.\n"
        ...
        f"CONTEXT:\n{context}"
    )

    result = chat(
        prompt=question,
        system=system_prompt,
        provider=provider,
        model=model,
    )

    return {
        "answer":        result["response"],
        "sources":       retrieved,
        ...
    }
```

### Line-by-line

1. **Format context** — Each chunk labelled with source and page, separated by `---`:

   ```
   [Source: infosys-ar-26.pdf, Page: 12]
   Salil Parekh is the Chief Executive Officer...

   ---

   [Source: infosys-ar-26.pdf, Page: 15]
   ...
   ```

2. **System prompt** — Three rules for the LLM:
   - Answer **only** from the context
   - Say "I don't have enough information..." if the answer is not there
   - Cite source filename and page

   Without this, the LLM falls back to training data and RAG loses its purpose.

3. **`chat()` from Phase 01** — Not the OpenAI SDK directly. `chat()` handles provider routing (Groq by default), token counting, cost, and latency. When the provider changes in Phase 03+, `rag.py` does not need to change.

   Note: `chat()` returns `result["response"]`, not `"content"`.

4. **Return dict** — Answer + sources + token/cost/latency stats. Structured so Phase 04 can call `query()` as an agent tool.

### Grounding in practice

| Query | Result |
|---|---|
| "Who is the CEO?" | Correct — Salil Parekh, page 12 cited |
| "What is revenue?" | Partial — revenue found, net profit honestly missing |
| "Retail segment revenue?" | Wrong — chart numbers misread (extraction limit from Step 1) |

Honest "I don't know" is correct behaviour. Confident wrong answers (charts) are the failure mode to watch — addressed in Phase 03 (eval) and via structured data sources later.

### What Step 6 does not do

| Does | Does not |
|---|---|
| Ground the LLM in retrieved text | Re-embed or re-index |
| Call `chat()` for generation | Modify the FAISS index |

### Mental model

```
5 retrieved chunks
  → format as labelled context block
  → system prompt: "answer from context only"
  → chat(question, system=context+rules)
  → {answer, sources, tokens, cost, latency}
```

---

## Step 7 — CLI: `if __name__ == "__main__"`

### Where it sits

Entry point when you run `python src/rag.py` from the command line. Not used when another module imports `build_index` or `query` directly.

### The code

```298:331:src/rag.py
if __name__ == "__main__":
    parser = argparse.ArgumentParser(...)
    parser.add_argument("question",    nargs="?", ...)
    parser.add_argument("--index",     action="store_true", ...)
    parser.add_argument("--corpus",    default="data/corpus", ...)
    parser.add_argument("--index-dir", default="data/index", ...)
    parser.add_argument("--top-k",     type=int, default=5, ...)
    parser.add_argument("--provider",  default=None, ...)
    parser.add_argument("--model",     default=None, ...)
    args = parser.parse_args()

    if args.index:
        build_index(...)
    elif args.question:
        result = query(...)
        print(...)
    else:
        parser.print_help()
```

### Three branches

| Command | Branch | Action |
|---|---|---|
| `python src/rag.py --index` | `args.index` | Build index |
| `python src/rag.py "question"` | `args.question` | Query and print result |
| `python src/rag.py` | neither | Print help |

### Useful flags

```bash
# Custom corpus or index location
python src/rag.py --index --corpus data/corpus --index-dir data/index

# Retrieve more chunks
python src/rag.py "your question" --top-k 10

# Override LLM provider for this query
python src/rag.py "your question" --provider groq --model llama-3.3-70b-versatile
```

Embedding model is **not** overridable from CLI — it comes from `EMBEDDING_MODEL` in `.env` and must match what was used at index time.

### Query output format

```
Answer:
Salil Parekh is the Chief Executive Officer...

Sources:
  [0.712]  infosys-ar-26.pdf  p.12
  [0.698]  infosys-ar-26.pdf  p.15

Tokens  : 903 in / 27 out
Cost    : $0.000000
Latency : 375 ms
```

- **Answer** — LLM response grounded in context
- **Sources** — Which chunks were retrieved (similarity score, file, page)
- **Tokens / Cost / Latency** — From `chat()` via Phase 01

### What Step 7 does not do

The CLI is a thin wrapper. All logic lives in `build_index()` and `query()`. Phase 04 will import those functions directly — no CLI involved.

---

## End-to-end: one query traced through the file

```
python src/rag.py "Who is the CEO of Infosys?"

CLI (Step 7)
  → query("Who is the CEO of Infosys?")

query() — retrieval (Step 5)
  → load faiss.index + chunks.json from disk
  → _embed_text(question)           # OpenAI, same model as index
  → index.search(q_vector, top_k=5) # FAISS cosine similarity
  → chunks[11], chunks[14], ...     # look up text by index

query() — generation (Step 6)
  → format 5 chunks with [Source, Page] labels
  → system prompt: answer from context only
  → chat(question, system=prompt)   # Groq via Phase 01
  → return {answer, sources, tokens, cost, latency}

CLI (Step 7)
  → print answer, sources, stats
```

Index time (already done):

```
python src/rag.py --index

build_index() (Step 4)
  → _load_pdfs()        # 382 pages
  → _chunk_documents()  # 2,697 chunks
  → _embed_batch()      # (2697, 1536) vectors
  → faiss.index + chunks.json saved to data/index/
```

---

## Related docs

| Topic | File |
|---|---|
| Architecture and design decisions | [design.md](design.md) |
| Embeddings theory | [embeddings.md](embeddings.md) |
| Chunking strategies | [vector-store.md](vector-store.md), [chunking-guide.md](chunking-guide.md) |
| Summarization vs RAG | [summarization.md](summarization.md) |
| Q&A for interviews | [questions.md](questions.md) |
| Known limitations (charts, etc.) | [reflection.md](reflection.md) |
