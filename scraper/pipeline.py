import os
import sys
import logging
import argparse
import psycopg2

from scraper import config
from scraper import crawler
from scraper import extractor
from scraper import cleaner
from scraper import storage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("scraper.log")
    ]
)
logger = logging.getLogger(__name__)

def run_pipeline(resume: bool = True) -> None:
    """
    Main orchestration function.
    """
    conn = None
    try:
        conn = psycopg2.connect(config.DB_CONNECTION_STRING)
        conn.autocommit = False
    except psycopg2.Error as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        return

    # The table is expected to be created by the db/init scripts now.
    # We no longer manually create it here to prevent schema conflicts.

    scraped_urls = set()
    if resume:
        try:
            scraped_urls = storage.load_scraped_urls(conn)
            conn.commit()
        except psycopg2.Error as e:
            logger.error(f"Failed to load scraped URLs: {e}")
            conn.rollback()

    all_urls = crawler.discover_document_urls()
    
    remaining_urls = []
    if resume:
        remaining_urls = [info for info in all_urls if info["url"] not in scraped_urls]
    else:
        remaining_urls = all_urls

    logger.info(f"Found {len(all_urls)} total documents, {len(scraped_urls)} already scraped, {len(remaining_urls)} remaining")

    good_count = 0
    low_quality_count = 0
    ocr_failed_count = 0

    for idx, url_info in enumerate(remaining_urls, start=1):
        url = url_info["url"]
        logger.info(f"Processing [{idx}/{len(remaining_urls)}]: {url}")
        
        try:
            raw_text, was_ocr, html_title = extractor.extract_document(url_info)
            if html_title:
                url_info['html_title'] = html_title
            
            if not raw_text or not raw_text.strip():
                logger.warning(f"SKIP: empty extraction for {url}")
                continue
                
            if was_ocr:
                cleaned_text = cleaner.clean_ocr_text(raw_text)
            else:
                cleaned_text = cleaner.clean_html_text(raw_text)
                
            metadata = storage.save_as_markdown(cleaned_text, url_info, was_ocr, config.OUTPUT_DIR)
            
            try:
                storage.save_metadata_to_db(metadata, conn)
                conn.commit()
            except psycopg2.Error as e:
                logger.error(f"Failed to save metadata to DB for {url}: {e}")
                conn.rollback()
                try:
                    conn = psycopg2.connect(config.DB_CONNECTION_STRING)
                    conn.autocommit = False
                except psycopg2.Error as e2:
                    logger.critical(f"Failed to reconnect to DB: {e2}")
                    break
                continue
                
            quality = metadata["quality"]
            if quality == "good":
                good_count += 1
            elif quality == "low":
                low_quality_count += 1
                logger.warning(f"WARNING: quality={quality} for {url}")
            elif quality == "ocr_failed":
                ocr_failed_count += 1
                logger.warning(f"WARNING: quality={quality} for {url}")
                with open("failed_ocr.log", "a", encoding="utf-8") as f:
                    f.write(f"{url}\n")
                    
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            continue

    logger.info(f"Scraping complete. Good: {good_count}, Low quality: {low_quality_count}, OCR failed: {ocr_failed_count}")
    
    if conn:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-resume", action="store_true",
                        help="Re-scrape all documents even if already in DB")
    args = parser.parse_args()
    
    # Temporarily limit for quick validation if needed by changing remaining_urls in code
    run_pipeline(resume=not args.no_resume)
