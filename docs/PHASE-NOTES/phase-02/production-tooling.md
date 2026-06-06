# Production Tooling — Phase 02

What enterprises actually use for PDF extraction and chunking, compared to what we built in `src/rag.py`. Use this when teaching or when someone asks: *"Do companies really write this themselves? Is pdfplumber enough?"*

For enterprise chunking **process** (classification, sampling, multi-strategy pipelines), see [enterprise-chunking.md](enterprise-chunking.md). For document-type handling (tables, charts, images), see [chunking-guide.md](chunking-guide.md).

---

## PDF extraction: what we use vs what enterprises use

### Our Phase 02 choice: `pdfplumber`

We use `pdfplumber` in `_load_pdfs()` because it is:

- Pure Python, easy to install
- Good for **digital PDFs with a text layer** (selectable text — like most annual reports)
- Sufficient for learning the RAG pipeline end to end

It is a common choice in prototypes, internal tools, and small-to-medium RAG projects.

### What enterprises use in practice

Enterprises rarely rely on a single extractor for all documents. They use a **tiered stack** — pick the tool based on document complexity and accuracy requirements.

| Tier | Tools | When used |
|---|---|---|
| **1 — Simple text PDFs** | `pdfplumber`, PyMuPDF, `pypdf`, `pdfminer.six` | Clean digital PDFs, fast, low cost |
| **2 — Layout-aware parsing** | [Unstructured](https://github.com/Unstructured-IO/unstructured), Docling, LayoutParser | Mixed layouts, columns, headers, section structure |
| **3 — Cloud document AI** | Azure Document Intelligence, AWS Textract, Google Document AI | Production scale, SLAs, OCR for scanned docs, table extraction |
| **4 — Specialised parsers** | LlamaParse, Adobe PDF Extract | Complex financial filings, heavy tables and charts |

**pdfplumber is not wrong for Phase 02** — it is the simplest tier. For Infosys-style annual reports at enterprise scale, teams often move to Tier 2 or 3 precisely because of failures like the Retail segment chart query: numbers extracted without spatial context (see [reflection.md](reflection.md)).

---

## Chunking: hand-written vs libraries vs platforms

Chunking is universal in every RAG system. The difference is **who maintains the splitter code**.

### Option 1 — Hand-written (what we did)

Our `_recursive_chunk()` in `rag.py` splits text by trying `\n\n` → `\n` → `. ` → ` ` in order, with overlap at boundaries.

This is intentionally hand-written for Phase 02 so you understand exactly what happens before relying on a library.

It is essentially the same algorithm as LangChain's `RecursiveCharacterTextSplitter` — if you read their source, the logic is very similar.

### Option 2 — Open-source libraries (most common in production code)

Most teams use a splitter from an existing framework rather than maintaining their own:

| Library | Splitter | Notes |
|---|---|---|
| **LangChain** | `RecursiveCharacterTextSplitter` | Same recursive-boundary idea as our code |
| **LangChain** | `SemanticChunker` | Splits by embedding similarity between sentences |
| **LlamaIndex** | `SentenceSplitter` | Sentence-aware boundaries |
| **LlamaIndex** | `SemanticSplitterNodeParser` | Topic-shift detection via embeddings |
| **Haystack** | `DocumentSplitter` | Configurable strategy per pipeline |
| **Unstructured** | `chunk_by_title`, `chunk_elements` | Chunks after layout-aware parsing; keeps section headers |

Typical swap — replace `_recursive_chunk()` with LangChain in a few lines:

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=600,
    chunk_overlap=60,
    separators=["\n\n", "\n", ". ", " "],
)
chunks = splitter.split_text(page_text)
```

Same behaviour. Maintained by the library, not your team.

### Option 3 — Managed platforms (common at scale)

Some teams never write chunking code. The ingestion platform handles parse + chunk + embed + store:

| Platform | What you configure |
|---|---|
| Azure AI Search | Chunk size, overlap, skillset for document cracking |
| AWS Bedrock Knowledge Bases | Auto-chunks on S3 upload |
| Databricks Vector Search | Ingestion job with parsing + chunking |
| Pinecone / Weaviate + LangChain | Ingest pipeline as code, but splitter comes from library |

You set chunk size and overlap. You do not maintain `_recursive_chunk()`.

### Option 4 — Custom chunking (domain-specific)

Teams write custom logic when generic splitters fail for their domain:

| Domain | Custom strategy |
|---|---|
| Legal | Split by clause number (`Section 4.2`, `Article VII`) |
| Financial | One chunk per table row with column headers prepended |
| Medical | Split by clinical note sections or ICD structure |
| Code documentation | Split by function/class, not character count |

See [enterprise-chunking.md](enterprise-chunking.md) for how firms route document types to different strategies automatically.

---

## Phase 02 vs typical production

| | Our `rag.py` (Phase 02) | Typical enterprise |
|---|---|---|
| **PDF extraction** | `pdfplumber` only | Tiered: pdfplumber / Unstructured / cloud AI |
| **Chunking** | Hand-written `_recursive_chunk()` | LangChain, LlamaIndex, or Unstructured |
| **Strategy count** | One strategy for all PDFs | Multiple strategies per document type |
| **Metadata** | `source` + `page` | Section title, doc type, date, table flag, etc. |
| **Table/chart handling** | None (text-only) | Dedicated table extractor or vision model |
| **Indexing** | Manual `python src/rag.py --index` | Scheduled ingestion job on document upload |
| **Quality check** | Manual query testing | Golden test set + retrieval metrics (Phase 03) |
| **Validation** | Eyeball results | Automated eval harness |

The **concepts are identical** — chunk, embed, store, retrieve, generate. Production adds tooling, metadata, and measurement on top.

---

## Learning path: why hand-written first, libraries later

| Phase | Tooling choice | Reason |
|---|---|---|
| **Phase 02 (now)** | Hand-written chunking + pdfplumber | Understand what libraries do under the hood |
| **Phase 03 (Eval)** | Same code + test harness | Measure when chunking fails (e.g. Retail chart query) |
| **Phase 04+** | Swap to LangChain splitter or Unstructured | Same logic, less code to maintain |
| **Production** | Tiered extraction + library splitters + eval | Accuracy and scale requirements |

When teaching, show both layers:

1. **Under the hood** — walk through `_recursive_chunk()` in [code-walkthrough.md](code-walkthrough.md)
2. **In production** — "here is the library equivalent and when you'd reach for it"

That way trainees understand the mechanism, not just the API.

---

## Quick reference: when to use what

| Situation | Recommendation |
|---|---|
| Learning RAG, clean text PDFs | `pdfplumber` + hand-written recursive chunk (Phase 02) |
| Prototype with less code | LangChain `RecursiveCharacterTextSplitter` |
| Mixed layouts, section headers | Unstructured parse + chunk |
| Scanned PDFs or heavy OCR | Cloud document AI (Textract, Document Intelligence) |
| Financial tables as precise numbers | Structured data API (`yfinance`, Screener.in) — not PDF RAG |
| Charts and images in PDFs | Vision model or multimodal extraction (later phase) |
| Thousands of docs, no custom code | Managed platform (Azure AI Search, Bedrock KB) |
| Legal/clinical/domain-specific structure | Custom chunker keyed to document schema |

---

## Related docs

| Topic | File |
|---|---|
| Line-by-line `rag.py` walkthrough | [code-walkthrough.md](code-walkthrough.md) |
| Enterprise chunking process at scale | [enterprise-chunking.md](enterprise-chunking.md) |
| Per document-type chunking (tables, charts) | [chunking-guide.md](chunking-guide.md) |
| Chunking strategies and semantic splitting | [vector-store.md](vector-store.md) |
| Known limitations from our Infosys run | [reflection.md](reflection.md) |
