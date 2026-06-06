# Chunking Guide — Document Types and Strategies

Real-world documents are not plain text. Before you can chunk, you have to understand what your document contains, because different content types need completely different handling.

---

## What a document can contain

| Content type | Examples | Chunking challenge |
|---|---|---|
| Plain prose | Articles, blog posts, emails | Easiest — sentences and paragraphs are natural boundaries |
| Structured text | Reports with headings, legal contracts | Section boundaries matter — don't split across them |
| Tables | Financial statements, comparison tables | A table row means nothing without the column headers |
| Images | Charts, diagrams, photos, logos | Text extractors can't read images — they get silently dropped |
| Charts / graphs | Bar charts, pie charts embedded in PDF | Same as images — invisible to text extraction |
| Footnotes | Annual reports, research papers | Often separated from the text they reference |
| Headers / footers | Page numbers, company name repeated on every page | Adds noise — should be stripped before chunking |
| Mixed content | A PDF page with a paragraph, then a table, then a chart | Most common in real documents — requires the most care |
| Code | Technical docs, developer manuals | Functions and blocks should not be split mid-logic |
| Lists and bullets | Requirements, feature lists | Items lose meaning if separated from their parent heading |

---

## Content type → recommended approach

### 1. Plain prose (articles, emails, notes)

**What it looks like:**
```
"The company was founded in 1981 in Pune, India. It started with 7 engineers
and a capital of $250. Today it employs over 300,000 people worldwide."
```

**Best chunking strategy:** Recursive → Semantic (if quality matters)
**Why:** Natural sentence and paragraph boundaries exist. Recursive respects them. Semantic gives the best quality.
**Watch out for:** Very long paragraphs that should be split but look like one chunk.

---

### 2. Structured text with headings (reports, contracts, manuals)

**What it looks like:**
```
## Revenue Performance

Total revenue for FY2024 was ₹1,47,000 crore, an increase of 14.4% over FY2023.

## Operating Margin

Operating margin improved to 21.3%, up 120 basis points year on year.
```

**Best chunking strategy:** Section-aware chunking — split on heading boundaries first, then recursively within each section.
**Why:** "Operating margin improved to 21.3%" has no meaning without knowing it's under "Operating Margin". Splitting across sections destroys context.
**Implementation:**
```
1. Detect headings (##, bold, ALL CAPS lines, etc.)
2. Create one chunk per section (heading + content below it)
3. If a section is too long, split recursively within it
4. Always prepend the section heading to every sub-chunk
```

**Example of what NOT to do:**
```
BAD Chunk: "...an increase of 14.4% over FY2023. Operating margin improved to 21.3%..."
```
This mixes revenue and margin — if someone asks "What was the operating margin?", the retrieved chunk gives two unrelated numbers.

---

### 3. Tables

This is the hardest content type. Tables are the most common thing that breaks basic RAG.

**What it looks like in an annual report:**
```
┌──────────────┬────────────┬────────────┬──────────┐
│ Metric       │ FY2024     │ FY2023     │ Change   │
├──────────────┼────────────┼────────────┼──────────┤
│ Revenue      │ ₹1,47,000 cr│ ₹1,28,600 cr│ +14.4%  │
│ Net Profit   │ ₹26,248 cr │ ₹24,095 cr │ +8.9%   │
│ Op. Margin   │ 21.3%      │ 20.1%      │ +120 bps │
└──────────────┴────────────┴────────────┴──────────┘
```

**The problem with naive chunking:**

If you extract the table as text and apply fixed-size or recursive chunking, you might get:

```
Chunk A: "Metric FY2024 FY2023 Change Revenue ₹1,47,000 cr"
Chunk B: "₹1,28,600 cr +14.4% Net Profit ₹26,248 cr ₹24,095"
```

Row 1 is split across two chunks. Neither chunk alone can answer "What was FY2024 revenue?"

**The right approaches:**

**Option A: One chunk per row, with headers prepended**
```
Chunk: "Metric: Revenue | FY2024: ₹1,47,000 cr | FY2023: ₹1,28,600 cr | Change: +14.4%"
Chunk: "Metric: Net Profit | FY2024: ₹26,248 cr | FY2023: ₹24,095 cr | Change: +8.9%"
Chunk: "Metric: Operating Margin | FY2024: 21.3% | FY2023: 20.1% | Change: +120 bps"
```
Each chunk is self-contained and answerable.

**Option B: Convert the whole table to a descriptive paragraph first**
```
"In FY2024, Infosys reported revenue of ₹1,47,000 crore (up 14.4% from FY2023),
net profit of ₹26,248 crore (up 8.9%), and an operating margin of 21.3%
(up 120 basis points from 20.1% in FY2023)."
```
Then chunk this paragraph normally. This works well for small tables but loses nuance in large ones.

**Option C: Leave the table as-is as one chunk (if it fits in context)**
If the entire table fits in ~500–800 tokens, keep it as a single chunk. Don't split a table at all.

**Libraries for table extraction:**
- `pdfplumber` — extracts tables as Python list-of-lists, preserving structure
- `camelot` — better for complex tables with merged cells
- `tabula-py` — wraps Java, good for well-formatted PDFs

---

### 4. Images (photos, logos, illustrations)

**The hard truth:** Standard text extraction tools (`pdfplumber`, `pypdf`, `pdfminer`) **cannot read images**. They are silently dropped. If your document has a photo of a factory or a logo, it simply doesn't exist in your extracted text.

**What to do:**

**Option A: Ignore images** — acceptable if images are decorative (logos, photos)

**Option B: Use OCR** — extract text from images using Tesseract or AWS Textract
```python
# Using pytesseract
from PIL import Image
import pytesseract

image = Image.open("page_5.png")
text = pytesseract.image_to_string(image)
```
Works well for scanned PDFs where the entire page is an image.

**Option C: Use a multimodal model** — send the image to GPT-4o or Claude (which can see images) and ask it to describe the content in text, then chunk that description.
```
Image: a bar chart showing quarterly revenue 2021–2024
→ GPT-4o: "This chart shows quarterly revenue growing from ₹28,000 cr in Q1 FY2021
           to ₹38,000 cr in Q4 FY2024, with consistent year-on-year growth."
→ chunk this description as plain text
```
This is the best approach for charts and diagrams that contain data.

---

### 5. Charts and graphs embedded in PDFs

Charts are images — the same rules apply. But charts contain **quantitative data** that images of people or logos don't.

**What gets lost without special handling:**
```
Document contains: [Bar chart showing Infosys revenue by quarter FY2021–FY2024]
Text extraction: [blank — nothing extracted]
User asks: "Show me the revenue trend over the last 3 years"
RAG result: no relevant chunks found
```

**The right approach:** Multimodal extraction. Send each chart image to a vision model, get a structured description or the underlying data as text, then index that.

For this project (Phase 02): skip chart extraction initially. In Phase 05 (Observability) you'll see which queries fail, and chart extraction becomes an obvious improvement to make.

---

### 6. Footnotes and endnotes

**The problem:**
```
Page 12 text: "...operating margin improved significantly¹..."
Page 47 footnote: "¹ Operating margin excludes one-time restructuring charge of ₹240 cr"
```

If you chunk page 12 and page 47 separately, the footnote is never connected to the text it annotates.

**Approach:** Use a PDF library that preserves footnote associations (`pdfplumber` gives you page-level text — footnotes on the same page stay together). For cross-page footnotes, it's very hard to handle automatically — either ignore them or resolve them manually before indexing.

---

### 7. Headers and footers (page noise)

**What they look like in extracted text:**
```
"INFOSYS LIMITED | ANNUAL REPORT FY2024                               Page 34
...actual content here...
INFOSYS LIMITED | ANNUAL REPORT FY2024                               Page 35"
```

Headers and footers repeat on every page. They add noise to every chunk and make retrieval slightly worse.

**Fix:** Strip them before chunking using regex or `pdfplumber`'s bounding box extraction (exclude top and bottom N pixels of each page).

---

### 8. Mixed content pages (most common in real documents)

A typical annual report page looks like:

```
[Section heading]
[2 paragraphs of prose]
[1 table with 5 rows]
[1 footnote]
[1 chart image]
[Page header/footer]
```

**The recommended pipeline for mixed documents:**

```
1. Extract the PDF page-by-page
2. For each page:
   a. Strip headers and footers
   b. Detect tables → extract separately → format as "Header: Value" rows
   c. Detect images/charts → send to vision model if data-bearing, else skip
   d. Extract remaining prose text
   e. Combine: [section heading] + [prose chunks] + [table chunks]
3. Apply recursive chunking to prose sections
4. Keep each table row as its own chunk (with headers)
5. Add source metadata: filename, page number, section name
```

---

## Decision table — document type → strategy

| Document type | Extraction tool | Chunking strategy | Special handling |
|---|---|---|---|
| Plain text / markdown | Read directly | Recursive or Semantic | None |
| Well-structured PDF (prose) | `pdfplumber` | Recursive | Strip headers/footers |
| PDF with headings | `pdfplumber` | Section-aware → recursive | Prepend heading to sub-chunks |
| PDF with tables | `pdfplumber` / `camelot` | One row per chunk + headers | Never split a table row |
| Scanned PDF (image-based) | `pytesseract` / AWS Textract | Recursive after OCR | OCR quality varies |
| PDF with charts/graphs | Vision model (GPT-4o, Claude) | Chunk the text description | Extract data as text first |
| PDF with footnotes | `pdfplumber` (same-page) | Recursive | Cross-page footnotes: manual |
| Code / technical docs | Read directly | Split on function/class boundaries | Never split mid-function |
| HTML pages | `BeautifulSoup` | Split on `<p>`, `<h>` tags | Strip nav, ads, boilerplate |
| Word documents (.docx) | `python-docx` | Section-aware | Preserve heading hierarchy |

---

## For this project (Stock Research Assistant)

The corpus is BSE/NSE annual report PDFs. These are mixed-content documents with:
- Prose sections (MD&A, strategy, risk factors) → recursive chunking
- Financial statement tables (P&L, balance sheet, cash flow) → row-per-chunk with headers
- Charts (usually not data-bearing in text form) → skip in Phase 02, add vision extraction later
- Headers/footers → strip before indexing

**Phase 02 scope:** Handle prose + tables. Skip images and charts for now — Phase 05 (Observability) will reveal what's being missed.
