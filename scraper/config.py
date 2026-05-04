import os
from dotenv import load_dotenv

load_dotenv()

"""
Configuration constants for the JusticeCongo AI scraper module.
"""

BASE_URL = "https://www.leganet.cd"

HEADERS = {
    "User-Agent": "JusticeCongo-AI-Bot/1.0 (academic research; contact: ppds@ppds.be)"
}

RATE_LIMIT_SECONDS = 2       # Sleep between every HTTP request
REQUEST_TIMEOUT = 30         # Seconds before giving up on a request
MAX_RETRIES = 3              # Retry failed requests this many times
OCR_DPI = 300                # Minimum DPI for Tesseract; use 400 for old docs

OUTPUT_DIR = "scraped_corpus"

# Maps URL path segments to domain folder names
DOMAIN_MAP = {
    "Civil": "droit_civil",
    "Penal": "droit_penal",
    "fiscal": "droit_fiscal",
    "travail": "droit_du_travail",
    "public": "droit_public",
    "social": "droit_social",
    "company": "company",
    "provinces": "provinces",
    "economique": "droit_economique",
    "administratif": "droit_administratif",
    "judiciaire": "droit_judiciaire",
    "decon": "droit_economique",
    "dfiscal": "droit_fiscal",
    "djud":"droit_judiciaire",
    "dpenal": "droit_penal",
    "dcivil": "droit_civil",
    "jurisprudence": "jurisprudence",
    "doctrine": "doctrine",
    "models": "models", 
    "jo": "journal_officiel"
}

THEMATIC_ENTRY_PAGE = "/legislation.htm"

COMPANY_PAGES = [
    "/index.htm",
    "/Soutien.htm",
    "/contact.htm",
    "/nos_partenaires.htm"
]

# Section index pages to crawl
INDEX_PAGES = [
    "/jurisprudence.htm",
    "/doctrine.htm",
    "/Modeles.htm",
    "/JO.htm",
]

DB_CONNECTION_STRING = os.getenv("DATABASE_URL")
