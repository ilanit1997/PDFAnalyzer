# 💾 PDF Analyzer — README

This project implements a document intelligence system, allowing you to process and analyze business documents (invoices, contracts, reports) using LLMs and serve results through a FastAPI interface.

---

##  Setup Instructions

### 1. 📦 Install dependencies

Create a virtual environment (optional but recommended):

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

Then install requirements:

```bash
pip install -r requirements.txt
```

### 2. 🔑 Set your OpenAI key

Create a `.env` file or set your environment variable:

```bash
export OPENAI_API_KEY=sk-...
```

### 3. 🚀 Run the API

```bash
python api.py
```

Access the Swagger UI at:

> [http://localhost:8000/docs](http://localhost:8000/docs)

Upload a PDF and view the extracted metadata.

---
## 🧠 Approach Overview

This project is organized into two main components:

### ✅ 1. Document Understanding System

This component handles PDF text extraction, document classification, and metadata extraction using GPT-4o-mini.

#### 📌 Label Definitions

```python
label_descriptions = {
    "Invoice": "A bill for goods or services, typically including vendor, amount, due date, and line items.",
    "Contract": "A legal agreement between parties, containing terms, dates, and responsibilities.",
    "Earnings": "A financial or business report summarizing revenue, profits, expenses, and other key metrics.",
    "Other": "Any other type of document that does not fit the above categories."
}
```

#### 🧩 Subcomponents

- **Classification**  
   - **Document loading**: Uses `pdfplumber` to extract text on a per-page basis.
   - **Classifier**: `RunnableGPTLogprobClassifier` applies GPT-4o-mini logprobs to assign one of the four labels (`Invoice`, `Contract`, `Earnings`, or `Other`).

- **Metadata Extraction**  
   - Uses a type-specific `RunnableMetadataExtractor`, which combines:
     - Prompts based on document type
     - Structured parsing with (`pydantic`) 

---

### ✅ 2. API Design (FastAPI)

📄 **[View full API documentation »](api_docs.md)**

---

# 🧠 Testing Approach

We evaluated the pipeline using real-world PDF documents collected from open-source repositories. The `core/main.py` script was used to test multiple files locally. The goal was to validate pipeline performance across diverse document types under realistic conditions.


## 📂 Document Types

### 1. Invoices
- **Source**: [invoice2data test set](https://github.com/invoice-x/invoice2data/tree/master/tests/compare)  
- **Note**: This repository provides invoice samples used for testing invoice parsers. We are not using their codebase—only the PDF files.  
- **Usage**: 11 invoices were selected to test the pipeline.

### 2. Contracts
- **Source**: [CUAD v1 (Contract Understanding Atticus Dataset)](https://zenodo.org/records/4595826)  
- **Note**: Contains numerous contract PDFs. We sampled 8 documents for testing.

### 3. Earnings Reports
- **Source**: Collected via targeted web search for "Earnings report presentation PDF". Several public companies regularly publish earnings summaries in PDF format.  
- **Samples**:
  - [Fujifilm](https://ir.fujifilm.com/en/investors/ir-materials/earnings-presentations/main/01112/teaserItems2/0/linkList/0/link/ff_fy2024q1_001e.pdf)
  - [Meta](https://s21.q4cdn.com/399680738/files/doc_financials/2025/q1/Earnings-Presentation-Q1-2025-FINAL.pdf)
  - [Walmart](https://stock.walmart.com/_assets/_d172a7918f5003c834c91e68d309d655/walmart/db/938/9939/presentation/Earnings+Presentation+%28FY25+Q4%29.pdf)
  - [NVIDIA](https://s201.q4cdn.com/141608511/files/doc_financials/2025/q2/NVDA-F2Q25-Quarterly-Presentation-FINAL.pdf)
  - [Citi](https://www.citigroup.com/rcs/citigpa/akpublic/storage/public/p200114a.pdf)

---

## 🔍 Key Findings

1. **Contract Length**: Contracts tend to be lengthy; the number of pages processed should be optimized for efficiency.

2. **Classification Strategy**: Document classification can be reliably performed using only a subset of pages (e.g., first 3 pages), since the document type is usually evident early on.

3. **Overconfidence in Predictions**: The classifier often returns overly confident predictions (e.g., probabilities near 1.0), which is suboptimal. Confidence calibration should be considered.

4. **"Other" Category Addition**: Introduced an "Other" category to handle outlier documents and to encourage a more realistic distribution of classification probabilities.

5. **Metadata Extraction Observations**:
   - **Due Date (Invoices)**: Needs a more explicit definition to distinguish it clearly from issue dates or payment dates.
   - **Vendor Name (Invoices)**: Ambiguity exists regarding whether this refers to the issuing or receiving company; requires clarification.

6. **Classification Errors**:
   - **Invoice → Other**: Occurred when the document was a payment receipt, not a formal invoice.
   - **Earnings → Other**: Happened when the document was a general investor presentation, although it included earnings data in later pages.

   📌 *Suggestion*: Instead of using a fixed `max_pages`, consider dynamically adjusting the page limit based on a fraction of the document’s total length (e.g., `alpha × total_pages`) to improve classification and extraction performance.


## 🔍 File Overview

```

├── api.py                   # API entrypoint (FastAPI app)
├── core/
│   ├── main.py                  # Script to test multiple files locally
│   ├── document_loader.py       # PDF parsing using pdfplumber
│   ├── document_classification.py  # Classifier with GPT logprobs
│   ├── metadata_extraction.py  # Metadata prompts + extraction runners
│   └── document_pipeline.py     # Manages pipeline: loading pdf -> classification -> extraction (per document)
│   └── action_generator.py     # Suggests next steps based on metadata - e.g. "Schedule payment"
├── documents/              # assignment PDF files for prediction
├── output/                 # output directory for processed files
├── documents-extra/        # additional documents for testing
│   ├── Invoice/              # Sample invoices for testing
│   ├── Contract/             # Sample contracts for testing
│   └── Earning Report/       # Sample earnings reports for testing
├── output-extra/            # output directory for processed additional testing files
│   ├── Invoice/              
│   ├── Contract/             
│   └── Earning Report/             
├── requirements.txt         # Clean dependency list
├── api_docs.md              # Endpoint documentation and examples
├── README.md                # This file
```


## 🤖 Part 3 – AI-Powered Features for Factify

### 🔹 Feature 1: Natural Language Summary of Extracted Metadata

**What**: After extracting structured metadata, the system generates a short, human-readable summary (e.g., “Invoice from Example LLC for $1200, due July 1”).
**Difficulty**: Easy, summarization is a common LLM task.
**How**:
- Use templating or LLM summarization to convert key metadata fields into natural language.
- Triggered post-extraction and cached for fast UI display.

**Business Value**:
- Enables metadata previews in the UI or chatbot responses.
- Makes structured fields more accessible to non-technical users.
- AI value: Makes later AI tasks (like search or Q&A) more effective by providing context.

---

### 🔹 Feature 2: Next-Step Action Suggestion

**What**: The system proposes the next logical action for the document (e.g., “Schedule payment”, “Review contract”, “Flag for renewal”).

**How**:
- Rule-based system identifies actionable metadata like due dates or termination periods.
- Optionally enhanced by an LLM that interprets metadata contextually.
- Served via the `/documents/{id}/actions` endpoint.

**Business Value**:
- Transforms documents into workflow triggers.
- Helps users stay ahead of deadlines, obligations, and business tasks.
- Can power reminders, dashboards, or automated task queues.

## 🏭 Production Considerations

### 🔧 Handling LLM API Failures

- Use retry logic (`tenacity`) for various failures (e.g., rate limits, timeouts, parsing errors).
- If classification or metadata parsing fails after retries, send to human review or log for manual inspection.
- Log all failures with document ID and traceback for audit/debugging.

### 💾 Caching Strategy

- Use a hash of the extracted PDF text (or file hash) as a cache key.
- Store classification + metadata outputs.
- Before calling the LLM, check if a previously processed result exists for this hash.

This ensures exact duplicates (same file content) are only processed once.

_More complicated caching may involve storing the textual content in a vector database for similarity search._


### 💰 Cost Estimate per Document

Assuming usage of `gpt-4o-mini`:

- **Input Pricing**: $0.60 per 1M tokens  
- **Output Pricing**: $2.40 per 1M tokens  

#### 🧾 Breakdown per Document:

- **Classification Prompt**: ~100 input tokens  
- **Metadata Extraction Prompt**: ~700 input tokens  
- **Document Text (Y)**: estimated size of extracted content in tokens  
- **Total Input Tokens**: `2 × Y + 800`  
- **Output Tokens**:
  - Classification: ~1 token  
  - Metadata: ~200 tokens  
  - **Total Output**: ~201 tokens  

If we cut off at page N for classification, the input tokens would be `Y + Y_N + 800` where Y_n is the number of tokens in the first N pages.

#### 💸 Formula:
Total Cost =
((2 × Y + 800) / 1,000,000 × $0.60) +
(201 / 1,000,000 × $2.40)


#### 🧮 Example (Y = 1000 tokens of document content):
Input: 2×1000 + 800 = 2800 tokens → $0.00168
Output: 201 tokens → $0.0004824
Total: ~$0.00216 per document
