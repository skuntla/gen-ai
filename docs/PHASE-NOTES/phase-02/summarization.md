# Summarization vs RAG — Phase 02

## The core difference

These two patterns are commonly confused. They solve different problems.

| Pattern | Question type | What you need from the document |
|---|---|---|
| RAG | "What was Infosys's operating margin in FY2024?" | The right 2-3 chunks out of 300 |
| Summarization | "Summarise this annual report" | All 300 chunks, nothing missing |

**RAG** uses FAISS similarity search to find the most relevant pieces. It is designed to ignore most of the document and surface the specific answer.

**Summarization** needs to process the entire document. FAISS is useless here — "give me everything" is not a similarity search problem.

Trying to use RAG for summarization is a common mistake. If you retrieve the top-5 chunks by similarity and ask "summarise the document," you get a summary of 5 loosely related paragraphs, not a summary of the document.

---

## Approach 1 — Full document in context (simplest)

If the entire document fits within the model's context window, pass it all in one call:

```python
with open("infosys_ar_2024.txt") as f:
    document = f.read()

result = chat(
    user_message="Summarise this annual report. Focus on revenue, margins, and management outlook.",
    system=f"You are a financial analyst. Here is the document:\n\n{document}",
)
```

The LLM reads the entire document in a single pass and generates a summary.

**When to use:** Most single filings fit here with modern models.
- Claude (Anthropic): 200K token context ≈ 150,000 words ≈ a 500-page book
- Groq (llama-3.3-70b): 128K token context ≈ 96,000 words ≈ most annual reports
- Ollama (local): depends on the model — typically 4K to 32K tokens

**Trade-off:** None for documents that fit. The moment the document exceeds the context window, this breaks completely — the API returns an error or silently truncates.

---

## Approach 2 — Map-Reduce (large documents)

When the document is too large for a single context window, split it into chunks and run two passes.

### Pass 1 — Map: summarise each chunk independently

```python
chunk_summaries = []
for chunk in chunks:                   # e.g. 15 chunks of 20 pages each
    summary = chat(
        user_message=f"Summarise this section of an annual report:\n\n{chunk['text']}",
        system="You are a financial analyst. Be concise. 3-5 sentences.",
    )
    chunk_summaries.append(summary["content"])
```

Each chunk is small enough to fit in the context window. Each gets its own focused summary.

```
Chunk 1 (pages 1–20)   → "Revenue grew 12% YoY to ₹1,53,670 crore. Operating margin expanded..."
Chunk 2 (pages 21–40)  → "Management highlighted softness in BFSI vertical. Deal wins of $3.8B..."
Chunk 3 (pages 41–60)  → "Risk factors include INR/USD volatility, visa restrictions in the US..."
```

### Pass 2 — Reduce: combine the chunk summaries

```python
combined = "\n\n".join(chunk_summaries)

final_summary = chat(
    user_message=f"Combine these partial summaries into one coherent summary:\n\n{combined}",
    system="You are a financial analyst. Produce a structured summary: financials, outlook, risks.",
)
```

The chunk summaries are much shorter than the original text — they all fit together in one pass.

**Trade-off:** Information that spans a chunk boundary can be missed. If a key insight starts on page 20 and concludes on page 21, and you split at page 20, neither chunk summary captures it fully. Overlap helps but does not eliminate this.

---

## Approach 3 — Refine (rolling summary)

Instead of summarising chunks independently, maintain a running summary and update it with each new chunk.

```python
running_summary = ""

for i, chunk in enumerate(chunks):
    if i == 0:
        prompt = f"Summarise this section:\n\n{chunk['text']}"
    else:
        prompt = f"""You have a running summary of a document so far:

{running_summary}

Now incorporate the new information from the next section. Update and refine the summary:

{chunk['text']}"""

    result = chat(user_message=prompt, system="You are a financial analyst.")
    running_summary = result["content"]

final_summary = running_summary
```

Each LLM call receives: the current running summary + one new chunk. The summary evolves as it reads more of the document.

**Trade-off:** Requires one LLM call per chunk — more expensive and slower than Map-Reduce. Also, early sections can get diluted: if chapter 1 contained something important but chapters 8–10 dominated the final pass, chapter 1 may be underrepresented.

---

## Comparison

| | Full context | Map-Reduce | Refine |
|---|---|---|---|
| LLM calls | 1 | chunks + 1 | chunks |
| Accuracy | Highest | Can miss cross-boundary info | Early info may dilute |
| Cost | Low | Medium | Highest |
| Best for | Fits in context | Large docs, speed matters | Large docs, accuracy matters |

---

## How this maps to the stock research assistant

The assistant will need summarization for specific use cases:

**Earnings call transcripts** — typically 20–30 pages. Approach 1 (full context) is the right choice. Modern models handle this easily.

```
"Summarise the Q4FY2024 earnings call for Infosys"
→ load transcript text
→ pass full text in one chat() call
→ return structured summary: revenue, margin, guidance, management tone
```

**Annual reports** — typically 150–300 pages. Borderline for large context models. Use Approach 1 if it fits; fall back to Map-Reduce if it exceeds the context window.

**Summarising across multiple documents** — "Compare the FY2024 outlook of Infosys, TCS, and Wipro." This is neither pure RAG nor pure summarization. It requires:
1. Summarise each company's filing separately (summarization)
2. Pass all three summaries to one final LLM call for comparison (reduce step)

This is a Phase 05+ pattern — agents deciding which tool to use and chaining them.

---

## Where summarization fits in the architecture

```
User query
    │
    ▼
Is the question about a specific fact?
    │ Yes → RAG pipeline (rag.py)
    │         embed query → FAISS search → retrieve top-K → chat()
    │
    └── No, asking for a full summary?
            │
            ▼
        Does document fit in context window?
            │ Yes → pass full document → chat()
            │
            └── No → Map-Reduce or Refine
                      chunk → summarise each → combine → chat()
```

In Phase 04 (tool use), the agent will decide which path to take based on the question. The user does not need to specify — the agent routes internally.
