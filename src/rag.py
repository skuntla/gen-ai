"""
src/rag.py — Phase 02: RAG pipeline for the Stock Research Assistant.

Index:  python src/rag.py --index [--corpus data/corpus] [--index-dir data/index]
Query:  python src/rag.py "What was Infosys's operating margin in FY2026?"
"""

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

# Allow importing from src/ when run as a script from the project root
sys.path.insert(0, str(Path(__file__).parent))
from llm_chat import chat

load_dotenv()

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = 1536  # text-embedding-3-small always produces 1536 dimensions

_openai_client = None


def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY is not set in your .env file.")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


# ---------------------------------------------------------------------------
# Step 1 — Load PDFs
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Step 2 — Chunk documents
# ---------------------------------------------------------------------------

def _recursive_chunk(text: str, size: int = 600, overlap: int = 60) -> list[str]:
    """
    Split text by trying paragraph → sentence → word boundaries in order.
    Overlap copies the last `overlap` characters of one chunk to the start of
    the next so that sentences cut at a boundary appear in full in at least
    one chunk.
    """
    if len(text) <= size:
        return [text]

    for sep in ["\n\n", "\n", ". ", " "]:
        if sep not in text:
            continue

        parts = text.split(sep)
        chunks: list[str] = []
        current = ""

        for part in parts:
            candidate = current + (sep if current else "") + part
            if len(candidate) <= size:
                current = candidate
            else:
                if current:
                    chunks.append(current.strip())
                    tail = current[-overlap:] if len(current) > overlap else current
                    current = tail + (sep if tail else "") + part
                else:
                    # Single part longer than size — will be handled by the
                    # next separator iteration or the hard-split fallback
                    current = part

        if current:
            chunks.append(current.strip())

        if chunks:
            return [c for c in chunks if c]

    # Hard-split fallback — only reached for very long tokens with no spaces
    return [text[i : i + size] for i in range(0, len(text), size - overlap)]


def _chunk_documents(
    documents: list[dict],
    size: int = 600,
    overlap: int = 60,
    min_len: int = 50,
) -> list[dict]:
    """Chunk all pages and carry source + page metadata into every chunk."""
    chunks: list[dict] = []
    for doc in documents:
        for text in _recursive_chunk(doc["text"], size=size, overlap=overlap):
            if len(text.strip()) >= min_len:
                chunks.append({
                    "text":   text.strip(),
                    "source": doc["source"],
                    "page":   doc["page"],
                })
    return chunks


# ---------------------------------------------------------------------------
# Step 3 — Embed text
# ---------------------------------------------------------------------------

def _normalise(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    return vector / norm if norm > 0 else vector


def _embed_text(text: str) -> np.ndarray:
    """Embed a single string. Returns a normalised (768→1536)-dim float32 array."""
    client = _get_openai_client()
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return _normalise(np.array(response.data[0].embedding, dtype="float32"))


def _embed_batch(texts: list[str], batch_size: int = 100) -> np.ndarray:
    """Embed a list of strings in batches. Returns shape (n, EMBEDDING_DIM)."""
    client = _get_openai_client()
    all_vectors: list[np.ndarray] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        for item in response.data:
            all_vectors.append(
                _normalise(np.array(item.embedding, dtype="float32"))
            )
        print(
            f"  Embedded {min(i + batch_size, len(texts))}/{len(texts)} chunks ...",
            flush=True,
        )

    return np.array(all_vectors, dtype="float32")


# ---------------------------------------------------------------------------
# Step 4 — Build and save the FAISS index
# ---------------------------------------------------------------------------

def build_index(
    corpus_dir: str = "data/corpus",
    index_dir: str = "data/index",
) -> dict:
    """
    Load PDFs → chunk → embed → FAISS index → save to disk.
    Returns {"chunks": int, "documents": int, "time_seconds": float}.
    """
    t0 = time.time()

    print(f"\nLoading PDFs from '{corpus_dir}' ...")
    documents = _load_pdfs(corpus_dir)
    n_docs = len(set(d["source"] for d in documents))
    print(f"  {len(documents)} pages from {n_docs} document(s).")

    print("\nChunking ...")
    chunks = _chunk_documents(documents)
    print(f"  {len(chunks)} chunks created.")

    print(f"\nEmbedding with {EMBEDDING_MODEL} ...")
    vectors = _embed_batch([c["text"] for c in chunks])

    print("\nBuilding FAISS index (IndexFlatIP = cosine similarity on normalised vectors) ...")
    index = faiss.IndexFlatIP(EMBEDDING_DIM)
    index.add(vectors)

    Path(index_dir).mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, f"{index_dir}/faiss.index")
    with open(f"{index_dir}/chunks.json", "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    elapsed = round(time.time() - t0, 1)
    print(f"\nSaved to '{index_dir}/'.")
    print(f"Done — {len(chunks)} chunks, {n_docs} document(s), {elapsed}s.\n")
    return {"chunks": len(chunks), "documents": n_docs, "time_seconds": elapsed}


# ---------------------------------------------------------------------------
# Step 5+6 — Query: embed → retrieve → generate
# ---------------------------------------------------------------------------

def query(
    question: str,
    index_dir: str = "data/index",
    top_k: int = 5,
    provider: str = None,
    model: str = None,
) -> dict:
    """
    Embed the question, retrieve top_k chunks from FAISS, generate a grounded answer.

    Returns:
        {
            "answer":        str,
            "sources":       [{"text", "source", "page", "score"}, ...],
            "input_tokens":  int,
            "output_tokens": int,
            "cost_usd":      float,
            "latency_ms":    int,
        }
    """
    index_path  = Path(index_dir) / "faiss.index"
    chunks_path = Path(index_dir) / "chunks.json"

    if not index_path.exists():
        raise FileNotFoundError(
            f"Index not found at '{index_path}'. Run: python src/rag.py --index"
        )

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
        retrieved.append({
            "text":   c["text"],
            "source": c["source"],
            "page":   c["page"],
            "score":  round(float(score), 3),
        })

    # Build the context block — each chunk labelled with its source + page
    context = "\n\n---\n\n".join(
        f"[Source: {r['source']}, Page: {r['page']}]\n{r['text']}"
        for r in retrieved
    )

    system_prompt = (
        "You are a financial analyst assistant specialising in Indian equities.\n\n"
        "Answer using ONLY the context below.\n"
        "If the answer is not in the context, say: "
        "'I don't have enough information in the provided documents to answer this.'\n"
        "Do NOT use your training knowledge. "
        "Cite the source filename and page number you drew from.\n\n"
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
        "input_tokens":  result.get("input_tokens", 0),
        "output_tokens": result.get("output_tokens", 0),
        "cost_usd":      result.get("cost_usd", 0.0),
        "latency_ms":    result.get("latency_ms", 0),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="RAG pipeline — Stock Research Assistant (Phase 02)"
    )
    parser.add_argument("question",    nargs="?",          help="Question to ask")
    parser.add_argument("--index",     action="store_true", help="Build index from corpus")
    parser.add_argument("--corpus",    default="data/corpus",  help="PDF corpus directory")
    parser.add_argument("--index-dir", default="data/index",   help="Index save/load path")
    parser.add_argument("--top-k",     type=int, default=5,    help="Chunks to retrieve")
    parser.add_argument("--provider",  default=None,           help="LLM provider override")
    parser.add_argument("--model",     default=None,           help="LLM model override")
    args = parser.parse_args()

    if args.index:
        build_index(corpus_dir=args.corpus, index_dir=args.index_dir)

    elif args.question:
        result = query(
            question=args.question,
            index_dir=args.index_dir,
            top_k=args.top_k,
            provider=args.provider,
            model=args.model,
        )
        print(f"\nAnswer:\n{result['answer']}")
        print("\nSources:")
        for s in result["sources"]:
            print(f"  [{s['score']:.3f}]  {s['source']}  p.{s['page']}")
        print(f"\nTokens  : {result['input_tokens']} in / {result['output_tokens']} out")
        print(f"Cost    : ${result['cost_usd']:.6f}")
        print(f"Latency : {result['latency_ms']} ms")

    else:
        parser.print_help()
