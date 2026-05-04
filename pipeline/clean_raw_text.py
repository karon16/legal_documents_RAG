import re
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from html.parser import HTMLParser
import html
from dotenv import load_dotenv
import os

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

DB_CONN = os.getenv("DATABASE_URL")

# ─── Known leganet.cd HTML navigation artifacts ───────────────────────────────
# These appear because BeautifulSoup didn't fully strip the site's
# FrontPage/mstheme navigation blocks before storing raw_text.
NOISE_PATTERNS = [
    r'html\s+PUBLIC\s+"[^"]*"[^\n]*\n?',     # DOCTYPE declaration
    r'<[^>]+>',                                # Any remaining HTML tags
    r'mstheme\s*',                             # FrontPage theme artifact
    r'msnavigation\s*',                        # FrontPage navigation artifact
    r'LEGANET\.CD\s*',                         # Repeated site branding
    r'DROITCONGOLAIS\.BE\s*',                  # Partner site branding
    r'&[a-zA-Z]+;',                            # HTML entities (&nbsp; etc.)
    r'&#\d+;',                                 # Numeric HTML entities
]

COMPILED_NOISE = [re.compile(p, re.IGNORECASE) for p in NOISE_PATTERNS]


def clean_text(raw: str) -> str:
    """
    Strips HTML artifacts from raw_text stored by the scraper.
    Preserves the actual legal content.
    """
    # 1. Decode HTML entities first (converts &amp; → &, &eacute; → é etc.)
    text = html.unescape(raw)

    # 2. Remove all noise patterns
    for pattern in COMPILED_NOISE:
        text = pattern.sub(' ', text)

    # 3. Normalize whitespace
    text = re.sub(r'[ \t]+', ' ', text)        # Collapse horizontal space
    text = re.sub(r'\n{3,}', '\n\n', text)     # Max 2 consecutive newlines
    text = '\n'.join(
        line.strip() for line in text.splitlines()
    )

    # 4. Remove lines that are purely decorative or empty after cleaning
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        # Skip lines that are only punctuation, dashes, or very short artifacts
        if stripped and not re.fullmatch(r'[-_=*#.]{3,}', stripped):
            lines.append(stripped)

    return '\n'.join(lines).strip()


def needs_cleaning(raw: str) -> bool:
    """Returns True if the text contains HTML artifacts."""
    indicators = ['msnavigation', 'mstheme', 'DOCTYPE', 'LEGANET.CD']
    return any(ind in raw for ind in indicators)


def run():
    conn = psycopg2.connect(DB_CONN)

    # Fetch all contaminated documents
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, title, domain, raw_text
            FROM legal_documents
            WHERE raw_text LIKE '%msnavigation%'
               OR raw_text LIKE '%DOCTYPE%'
               OR raw_text LIKE '%mstheme%'
            ORDER BY domain, doc_type
        """)
        dirty_docs = [dict(row) for row in cur.fetchall()]

    logger.info(f"Found {len(dirty_docs)} documents to clean")

    cleaned_count = 0
    failed_count  = 0

    for doc in dirty_docs:
        try:
            cleaned = clean_text(doc['raw_text'])

            # Sanity check: cleaned text must have meaningful content
            word_count = len(cleaned.split())
            if word_count < 20:
                logger.warning(
                    f"SKIP (too short after cleaning): "
                    f"{doc['title'][:60]} → {word_count} words"
                )
                failed_count += 1
                continue

            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE legal_documents
                    SET raw_text   = %s,
                        word_count = %s,
                        status     = 'scraped',
                        updated_at = NOW()
                    WHERE id = %s
                """, (cleaned, word_count, doc['id']))
            conn.commit()

            # Also delete existing chunks for this document so the
            # chunker re-processes it with clean text
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM document_chunks WHERE document_id = %s",
                    (doc['id'],)
                )
            conn.commit()

            cleaned_count += 1
            logger.info(
                f"[{cleaned_count}/{len(dirty_docs)}] "
                f"{doc['domain']} | {doc['title'][:50]} "
                f"→ {word_count} words"
            )

        except Exception as e:
            logger.error(f"FAILED: {doc['id']} — {doc['title'][:50]}: {e}")
            failed_count += 1
            continue

    logger.info(f"Done. Cleaned: {cleaned_count} | Failed/skipped: {failed_count}")
    conn.close()


if __name__ == "__main__":
    run()