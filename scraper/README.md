# JusticeCongo AI Scraper Module

This module is responsible for Phase 1 of the JusticeCongo AI RAG pipeline: discovering, downloading, extracting, and cleaning legal texts from the LEGANET.CD corpus.

It produces clean, UTF-8 encoded Markdown files with YAML frontmatter, alongside PostgreSQL metadata, which feed directly into the downstream RAG embedding process.

## Prerequisites

### 1. System Dependencies (Ubuntu/Debian)
You must install the following system packages for PDF extraction and Optical Character Recognition (OCR):

```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-fra poppler-utils
```

*(Note for Mac users: `brew install tesseract tesseract-lang poppler`)*

### 2. PostgreSQL
The scraper requires a running PostgreSQL database. 
Ensure you have created the `justicecongo` database and updated the connection string in `config.py` if your credentials differ from the default:
```python
DB_CONNECTION_STRING = "postgresql://user:password@localhost/justicecongo"
```

### 3. Python Environment
Activate your virtual environment and install the required dependencies:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

*(Note: The scraper explicitly requires `pdf2image`, `pytesseract`, `python-slugify`, `beautifulsoup4`, `pdfplumber`, and `psycopg2-binary`).*

## How to Run

The scraper is designed to be fully automated and idempotent. You can stop it at any time, and when restarted, it will resume from where it left off by checking the database for already scraped URLs.

Run the orchestration pipeline from the **root of the project**:

```bash
python -m scraper.pipeline
```

### Re-scraping All Documents
If you want to ignore the database of already scraped URLs and force the scraper to re-process everything:

```bash
python -m scraper.pipeline --no-resume
```

## Architecture & Workflow

The pipeline executes the following workflow for each document:
1. **Discovery (`crawler.py`)**: Crawls index pages (e.g., `/legislation.htm`) to discover all document URLs and infers their domain and type.
2. **Extraction (`extractor.py`)**: 
   - **HTML**: Cleans HTML elements and extracts text.
   - **PDF (Text Layer)**: Uses `pdfplumber` to extract text natively.
   - **PDF (Scanned)**: Uses `pdf2image` and `pytesseract` to perform OCR (with French language models).
3. **Cleaning (`cleaner.py`)**: Normalizes whitespace, removes decorative artifacts, and fixes common OCR mistakes (e.g., broken French elisions like `l'`).
4. **Storage (`storage.py`)**: 
   - Writes the cleaned text to the `scraped_corpus/` directory as a `.md` file with YAML frontmatter.
   - Upserts document metadata (title, url, quality, word count) to the PostgreSQL `legal_documents` table.

## Outputs

### 1. The Corpus Directory
The scraper organizes downloaded documents by legal domain:
```
scraped_corpus/
├── droit_civil/
├── droit_penal/
├── droit_commercial/
...
```
Each file is an `.md` document containing rich YAML frontmatter (URL, date enacted, OCR status, quality score) followed by the raw cleaned text.

### 2. Logs and Error Handling
- **`scraper.log`**: A detailed runtime log of the crawler's progress, extraction times, and any connection errors.
- **`failed_ocr.log`**: A file generated if any OCR attempts yield less than 50 words, allowing for manual review of difficult documents.

The scraper includes automatic HTTP retries and rate-limiting (2 seconds between requests) to remain respectful of the leganet.cd server resources.
