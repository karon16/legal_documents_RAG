import time
import logging
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

from scraper import config

logger = logging.getLogger(__name__)

def fetch_with_retry(url: str) -> requests.Response | None:
    """
    Fetch a URL with retries, rate limiting, and proper encoding.
    """
    for attempt in range(config.MAX_RETRIES):
        time.sleep(config.RATE_LIMIT_SECONDS)
        try:
            response = requests.get(
                url, 
                headers=config.HEADERS, 
                timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            response.encoding = 'iso-8859-1'
            return response
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt + 1}/{config.MAX_RETRIES} failed for {url}: {e}")
            if attempt == config.MAX_RETRIES - 1:
                logger.error(f"Failed to fetch {url} after {config.MAX_RETRIES} attempts.")
                return None
    return None

def discover_document_urls() -> list[dict]:
    """
    Crawl index pages to discover all document URLs.
    """
    discovered_urls = []
    seen_urls = set()
    
    # 1. Queue internal company pages directly
    for path in config.COMPANY_PAGES:
        full_url = urljoin(config.BASE_URL, path)
        if full_url not in seen_urls:
            seen_urls.add(full_url)
            discovered_urls.append({
                "url": full_url,
                "domain": "company",
                "doc_type": "document",
                "is_pdf": False
            })

    # 2. Fetch the thematic sub-menus from the legislation entry page
    dynamic_index_pages = list(config.INDEX_PAGES)
    thematic_url = urljoin(config.BASE_URL, config.THEMATIC_ENTRY_PAGE)
    logger.info(f"Fetching thematic entry page: {thematic_url}")
    response = fetch_with_retry(thematic_url)
    
    if response:
        soup = BeautifulSoup(response.text, 'html.parser')
        # Find all thematic links
        for a_tag in soup.find_all('a'):
            href = a_tag.get('href')
            if href and '/Legislation/Tables/' in href:
                dynamic_index_pages.append(href)
                
    # Deduplicate dynamic index pages
    dynamic_index_pages = list(set(dynamic_index_pages))

    # 3. Crawl all index pages to discover document links
    for index_path in dynamic_index_pages:
        index_url = urljoin(config.BASE_URL, index_path)
        logger.info(f"Crawling index page: {index_url}")
        response = fetch_with_retry(index_url)
        
        if not response:
            continue
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Infer domain from the parent index_url
        domain = "general"
        for key, val in config.DOMAIN_MAP.items():
            if key.lower() in index_url.lower():
                domain = val
                break
        
        for a_tag in soup.find_all('a'):
            href = a_tag.get('href')
            text = a_tag.get_text(strip=True)
            
            if not href:
                continue
                
            href_lower = href.lower()
            
            # Match condition: text is "Texte" or "[Texte]" OR href ends in .htm, .html, .pdf
            is_texte_link = text in ("Texte", "[Texte]")
            is_doc_ext = href_lower.endswith(('.htm', '.html', '.pdf'))
            
            if not (is_texte_link or is_doc_ext):
                continue
                
            # Exclude known index pages to avoid recursive crawling
            if any(href_lower.endswith(idx.lower().split('/')[-1]) for idx in dynamic_index_pages + [config.THEMATIC_ENTRY_PAGE]):
                continue
                
            full_url = urljoin(index_url, href)
            
            if full_url in seen_urls:
                continue
                
            seen_urls.add(full_url)
                    
            # Infer doc_type
            doc_type = "document"
            url_path_lower = full_url.lower()
            if "loi" in url_path_lower:
                doc_type = "loi"
            elif any(k in url_path_lower for k in ("decret", "d%c3%a9cret")):
                doc_type = "decret"
            elif any(k in url_path_lower for k in ("arrete", "arr%c3%aat")):
                doc_type = "arrete"
            elif "ordonnance" in url_path_lower:
                doc_type = "ordonnance"
            elif "jurisprudence" in url_path_lower:
                doc_type = "jurisprudence"
            elif "modele" in url_path_lower or "modeles" in url_path_lower:
                doc_type = "modele"
            elif "jo" in url_path_lower or "jos" in url_path_lower:
                doc_type = "journal_officiel"
                
            # Infer is_pdf
            is_pdf = full_url.lower().endswith('.pdf')
            
            discovered_urls.append({
                "url": full_url,
                "domain": domain,
                "doc_type": doc_type,
                "is_pdf": is_pdf
            })
            
    return discovered_urls
