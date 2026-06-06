# Questions — Phase 02

These cover concepts, design decisions, and implementation details from Phase 02.
Use for interview prep, self-testing, and teaching.

---

## Core concepts

**Q: What problem does RAG solve?**
LLMs are trained on data up to a cutoff date. They cannot know about recent filings, private documents, or proprietary data. RAG retrieves relevant information from your own documents first and passes it to the LLM as context — so the model answers from your data, not from its frozen training memory.

**Q: What are the two phases of a RAG pipeline?**
Index time (offline): chunk → embed → store. This happens once.
Query time (online): embed query → retrieve top-K chunks → generate answer. This happens on every question.

**Q: What is an embedding?**
A vector — a list of numbers that represents the meaning of a piece of text. Texts with similar meaning produce vectors that are close together in the embedding model's vector space. The model converts text to a point in high-dimensional space (e.g. 768 or 1536 dimensions).

**Q: Why must you use the same embedding model for indexing and querying?**
Each embedding model learns its own coordinate system during training. If you index with model A and query with model B, the query vector lands at a random, meaningless position in model A's space — even if both models produce the same number of dimensions. This is called **incompatible vector spaces**. The result is retrieval failure: FAISS returns random chunks, not relevant ones.

**Q: What is cosine similarity and why is it used for retrieval?**
Cosine similarity measures the angle between two vectors. Vectors pointing in the same direction (angle ≈ 0) have similarity ≈ 1.0. Vectors pointing in opposite directions have similarity ≈ -1.0. It's preferred over Euclidean distance because it ignores the magnitude of vectors — only the direction (meaning) matters, not how "long" the vector is.

**Q: What is a vector store?**
A database optimised for nearest-neighbour search: given a query vector, find the N most similar vectors fast. FAISS is an in-memory vector store. Unlike a regular database where you query by exact match or keyword, a vector store queries by semantic similarity.

---

## Chunking

**Q: Why do we chunk documents instead of passing the entire document to the LLM?**
Two reasons: (1) Context windows have token limits — you cannot fit 50 full documents into one prompt. (2) Retrieval precision — embedding a 50-page document produces one blurry vector that averages all topics. Embedding a single paragraph produces a focused vector that retrieves precisely.

**Q: What is the trade-off in chunk size?**
Too small: each chunk lacks enough context to be useful on its own. A single sentence may not make sense without the surrounding text.
Too large: the chunk contains multiple topics, the embedding is diluted, and retrieval is imprecise.
Typical sweet spot: 300–700 characters with 50–100 character overlap.

**Q: What is chunk overlap and why does it exist?**
Overlap means consecutive chunks share N characters at their boundary. This ensures that a sentence split across a chunk boundary still appears in full in at least one chunk — no information is permanently lost at the cut point.

**Q: What are the three chunking strategies and when do you use each?**
- Fixed-size: split every N characters. Simple, fast. Use for prototyping or poorly structured text.
- Recursive: try to split on paragraph → sentence → word boundaries. Respects natural text structure. Default choice for most documents.
- Semantic: embed each sentence, detect topic shifts by similarity drop, group by meaning. Best quality. Use for long documents with many distinct topics, or when recursive gives poor retrieval.

**Q: What is the sliding window approach in semantic chunking?**
Instead of comparing only the current sentence to the previous one, compare it to the average of the last K sentences. This detects gradual topic drift that adjacent-pair comparison misses — where no single step is a dramatic change but the topic has clearly shifted over several sentences.

**Q: How do tables break standard chunking, and how do you fix it?**
Tables become meaningless if split across chunks — a row without its header provides no context. Fix: extract tables separately, format each row as "Header: Value | Header: Value", and index each row as its own self-contained chunk with all column headers prepended.

---

## Design decisions

**Q: Why does `query()` call `chat()` from `llm_chat.py` instead of calling the LLM directly?**
`chat()` already provides provider routing, token counting, cost logging, and error handling. Calling it directly means `rag.py` gets all of that for free without duplicating any logic. When the provider changes in Phase 03, `rag.py` doesn't need to change.
Principle: **don't duplicate logic, reuse the abstraction.**

**Q: Why is the FAISS index saved to disk instead of rebuilt on every query?**
Building the index (embedding all chunks) takes 5–10 seconds. A query must respond in under 2 seconds. Loading a saved FAISS index takes ~50 milliseconds.
This is the **offline indexing vs online serving** pattern: do expensive work once offline, serve cheaply online. The same principle behind search engines, recommendation systems, and most production ML systems.

**Q: Why is `data/index/` gitignored?**
The index is a generated artifact that can be rebuilt any time from the corpus. Binary FAISS files are large, change every time you re-index, and cause merge conflicts. The corpus PDFs are also gitignored — large binary files don't belong in git. Both can be regenerated locally.

**Q: What is grounding and why does the RAG system prompt enforce it?**
Grounding means the answer is supported by specific retrieved text. Without the "answer from context only" instruction, the LLM uses its training knowledge instead of the retrieved chunks — you lose the benefit of RAG and the answer becomes unverifiable. The system prompt is the guardrail that enforces grounding.

**Q: What happens when the answer is not in the retrieved chunks?**
The system prompt instructs the LLM to say "I don't have enough information in the provided documents to answer this." This is the correct behaviour — an honest "I don't know" is far better than a hallucinated answer the user might act on.

---

## Broader / interview-level

**Q: What is the difference between keyword search and semantic search?**
Keyword search finds documents containing the exact words in the query. Semantic search finds documents with the same meaning — different words, same concept. Example: "operating profitability" would not match "net margin" in keyword search but would match in semantic search because their embedding vectors are close.

**Q: What is retrieval failure and how do you detect it?**
Retrieval failure is when FAISS returns chunks that are not relevant to the question — the LLM then answers from irrelevant or misleading context. You detect it by running known questions and checking whether the returned sources actually contain the answer. This is exactly what Phase 03 (Eval) is built to measure.

**Q: What is re-ranking and why might you need it?**
FAISS returns the top-K chunks by vector similarity. But similarity is not the same as relevance — a chunk can be topically similar without actually containing the answer. Re-ranking passes the retrieved chunks through a second, more precise model that scores them by relevance to the specific question and reorders them. Adds latency and cost but significantly improves precision. A Phase 03+ improvement.

**Q: Why does RAG help with hallucination specifically?**
Hallucination happens when an LLM generates plausible-sounding but incorrect information from its training weights. RAG reduces this by providing explicit source text in the prompt — the model is instructed to read and quote from that text rather than recall from training. It doesn't eliminate hallucination entirely (the model can still misread the context) but dramatically reduces it for factual questions about your documents.

**Q: What is the context window bottleneck in RAG?**
Even with RAG, you can only pass K chunks to the LLM before hitting the context window limit. If the answer requires synthesising information from 20 chunks but you can only fit 5 in the prompt, you'll miss it. Solutions: larger context models, better retrieval (so the right 5 chunks are always retrieved), or summarisation before passing to the LLM.
