import os
from datetime import datetime, timezone
import urllib.parse
from pathlib import Path
from slugify import slugify

from scraper import cleaner

def save_as_markdown(text: str, url_info: dict, was_ocr: bool, output_dir: str) -> dict:
    """
    Save extracted text as a Markdown file with YAML frontmatter.
    """
    word_count = len(text.split())
    if word_count > 200:
        quality = "good"
    elif word_count > 50:
        quality = "low"
    else:
        quality = "ocr_failed" if was_ocr else "low"
        
    title = url_info.get("html_title")
    if not title:
        title = cleaner.extract_title(text, url_info["url"])
    
    parsed_url = urllib.parse.urlparse(url_info["url"])
    filename = os.path.basename(parsed_url.path)
    name_without_ext = os.path.splitext(filename)[0]
    
    slugified_name = slugify(name_without_ext)[:80]
    filename_md = f"{slugified_name}.md"
    
    domain_dir = Path(output_dir) / url_info["domain"]
    domain_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = domain_dir / filename_md
    
    # Try to extract date_enacted from title or URL or set to null
    # For now, setting to "null" as requested if not explicitly extracted
    date_enacted = "null" 
    scraped_at = datetime.now(timezone.utc).isoformat()
    
    yaml_frontmatter = f"""---
title: "{title}"
source_url: "{url_info['url']}"
domain: "{url_info['domain']}"
doc_type: "{url_info['doc_type']}"
date_enacted: {date_enacted}
was_ocr: {'true' if was_ocr else 'false'}
quality: "{quality}"
word_count: {word_count}
scraped_at: "{scraped_at}"
encoding_original: "iso-8859-1"
---

"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(yaml_frontmatter)
        f.write(text)
        
    metadata = {
        "source_url": url_info["url"],
        "title": title,
        "domain": url_info["domain"],
        "doc_type": url_info["doc_type"],
        "date_enacted": None, # or extract actual date later
        "file_path": str(output_path),
        "raw_text": text,
        "was_ocr": was_ocr,
        "quality": quality,
        "word_count": word_count,
        "scraped_at": scraped_at
    }
    
    return metadata

def save_metadata_to_db(metadata: dict, conn) -> None:
    """
    Upsert document metadata into PostgreSQL.
    """
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO legal_documents (
                source_url, title, domain, doc_type, date_enacted, file_path, raw_text,
                was_ocr, quality, word_count, scraped_at, status
            ) VALUES (
                %(source_url)s, %(title)s, %(domain)s, %(doc_type)s, %(date_enacted)s, %(file_path)s, %(raw_text)s,
                %(was_ocr)s, %(quality)s, %(word_count)s, %(scraped_at)s, 'scraped'
            )
            ON CONFLICT (source_url) DO UPDATE SET
                title = EXCLUDED.title,
                domain = EXCLUDED.domain,
                doc_type = EXCLUDED.doc_type,
                date_enacted = EXCLUDED.date_enacted,
                file_path = EXCLUDED.file_path,
                raw_text = EXCLUDED.raw_text,
                was_ocr = EXCLUDED.was_ocr,
                quality = EXCLUDED.quality,
                word_count = EXCLUDED.word_count,
                scraped_at = EXCLUDED.scraped_at,
                status = EXCLUDED.status;
        """, metadata)

def load_scraped_urls(conn) -> set[str]:
    """
    Load already scraped URLs from DB.
    """
    with conn.cursor() as cur:
        # Check if the table exists first to avoid crashing if it doesn't
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE  table_name   = 'legal_documents'
            );
        """)
        if not cur.fetchone()[0]:
            return set()
            
        cur.execute("SELECT source_url FROM legal_documents;")
        return {row[0] for row in cur.fetchall()}
