# Enterprise Chunking Strategy — At Scale

## The problem

A small project has 10–50 documents. You can open each one, understand its structure, and pick the right chunking strategy manually.

An enterprise has:
- Thousands of PDFs uploaded daily
- Dozens of document types (invoices, contracts, reports, manuals, emails, filings)
- New document formats appearing over time
- No human who can review each one before indexing

Nobody looks at each document manually. The pipeline has to figure out the right strategy automatically.

---

## How enterprises actually solve this

### Level 1: Document classification first

Before chunking, classify what kind of document it is. The document type determines the chunking strategy.

```
Incoming document
       │
       ▼
┌─────────────────────────────┐
│  Document Classifier        │
│  (rule-based or ML model)   │
└─────────────────────────────┘
       │
       ├──→ annual_report    → section-aware + table extractor
       ├──→ earnings_call    → recursive (transcript prose)
       ├──→ news_article     → recursive
       ├──→ invoice          → structured field extractor
       ├──→ legal_contract   → section-aware + clause extractor
       └──→ unknown          → recursive (safe fallback)
```

The classifier can be:
- **Rule-based** — filename patterns (`*_annual_report_*.pdf`), keywords on page 1, metadata from the document management system
- **ML classifier** — a small model trained to identify document types from the first page
- **LLM-based** — send page 1 to an LLM and ask "what type of document is this?"

---

### Level 2: Content detection within each document

Even within a single document type, content varies. A robust pipeline detects what's on each page:

```
For each page:
  ├── Has tables?    → extract with pdfplumber/camelot
  ├── Has images?    → send to vision model OR skip
  ├── Is a heading?  → mark as section boundary
  ├── Is a footer?   → strip
  └── Is prose?      → chunk with recursive/semantic
```

This is done **automatically** using heuristics:
- Tables: detected by line patterns, bounding boxes, or `pdfplumber`'s `.extract_tables()`
- Images: detected by checking if a PDF page contains image objects (non-text elements)
- Headings: detected by font size, bold formatting, or regex patterns (ALL CAPS, numbered sections)
- Footers: detected by Y-coordinate position (bottom 5% of page) and repetition across pages

---

### Level 3: Sampling and quality validation

Before rolling out a new document type to production:

1. **Sample 20–30 documents** from the new type
2. **Run the proposed chunking pipeline** on them
3. **Write 10–15 test questions** whose answers are known
4. **Measure retrieval accuracy** — did the right chunk come back for each question?
5. **Tune the strategy** until retrieval accuracy is acceptable (target: >80%)
6. **Lock the strategy** for that document type

This is Phase 03 (Eval) applied at the pipeline level, not the model level.

---

### Level 4: Metadata as a safety net

Every chunk gets rich metadata attached at index time:

```python
{
  "text": "Operating margin improved to 21.3%...",
  "source": "infosys_annual_report_2024.pdf",
  "page": 87,
  "section": "Financial Performance",
  "document_type": "annual_report",
  "company": "Infosys",
  "fiscal_year": "FY2024",
  "chunk_strategy": "recursive",
  "chunk_index": 42,
  "total_chunks": 318,
  "extraction_date": "2024-06-01"
}
```

This metadata serves two purposes:
1. **Filtered retrieval** — "only search chunks from Infosys FY2024 annual reports"
2. **Debugging** — when a query returns a wrong answer, you can trace exactly which chunk caused it, from which document, extracted how

---

### Level 5: Tiered strategies by content type

Enterprise pipelines usually define a strategy tier for each content type:

| Tier | Content | Strategy | Tools |
|---|---|---|---|
| Tier 1 | Pure prose (articles, transcripts) | Recursive or Semantic | `pdfplumber` |
| Tier 2 | Structured with headings | Section-aware + recursive | `pdfplumber` + heading detection |
| Tier 3 | Heavy tables (financial statements) | Table extraction + row-per-chunk | `pdfplumber` or `camelot` |
| Tier 4 | Image-heavy (scanned docs) | OCR first, then recursive | `pytesseract` or AWS Textract |
| Tier 5 | Charts/infographics | Vision model description | GPT-4o or Claude vision |
| Fallback | Unknown / mixed | Recursive (safe default) | `pdfplumber` |

---

## The multi-strategy pipeline (what production looks like)

```
Incoming PDF
     │
     ▼
[1. Parse] pdfplumber extracts text, tables, images separately per page
     │
     ▼
[2. Classify] document type → assign tier
     │
     ▼
[3. Pre-process]
     ├── Strip headers/footers
     ├── Resolve footnotes
     └── Normalize whitespace
     │
     ▼
[4. Content-type routing per page element]
     ├── Prose text → recursive/semantic chunking
     ├── Tables → row-per-chunk with headers
     └── Images → vision model OR skip
     │
     ▼
[5. Metadata enrichment]
     Each chunk gets: source, page, section, doc_type, company, date, strategy
     │
     ▼
[6. Embed]
     All chunks → embedding model → vectors
     │
     ▼
[7. Store]
     Vectors + metadata → vector store (FAISS / Chroma / Pinecone)
     │
     ▼
[8. Validate]
     Run sample questions → check retrieval accuracy → alert if below threshold
```

---

## What happens when a document type is new or unknown

Three approaches:

**A. Fallback to recursive** — safe default, works reasonably well on most prose documents. Accept slightly lower quality until the new type is profiled.

**B. Human-in-the-loop sampling** — route new document types to a queue. A human reviews 5 examples, configures the strategy, and approves it for automation. After that, the pipeline handles all future documents of that type automatically.

**C. LLM-assisted strategy selection** — send the first 2 pages to an LLM with the question: "What type of document is this? What content does it contain (tables, images, plain prose)?" Use the answer to select a strategy. Costs ~$0.001 per document — negligible.

---

## The honest reality at enterprise scale

Even with all of the above, some documents will be chunked badly. The key insight is:

> **Perfect chunking is not the goal. Measurable, improvable chunking is.**

The enterprise approach is:
1. Get something working (recursive fallback)
2. Measure retrieval quality per document type (Phase 03 — Eval)
3. Identify which document types have the worst retrieval
4. Fix those specifically
5. Repeat

A 90% correct retrieval on a 10,000-document corpus is a better outcome than spending 3 months designing a perfect pipeline before indexing anything.

---

## For this project (Stock Research Assistant)

Our corpus is small enough (10–50 documents) that we can manually profile each document type once:

| Our document types | Strategy |
|---|---|
| Annual reports (BSE/NSE PDFs) | Section-aware + table row-per-chunk |
| Earnings call transcripts | Recursive (pure prose/dialogue) |
| News articles | Recursive |
| Quarterly results (PDFs) | Table extraction dominant |

This manual profiling is done once. The code then handles all future documents of the same type automatically.
