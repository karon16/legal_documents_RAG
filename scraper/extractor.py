import os
import hashlib
import logging
import requests
import pdfplumber
import pdf2image
import pytesseract
from PIL import ImageEnhance, ImageFilter
from bs4 import BeautifulSoup

from scraper import config
from scraper.crawler import fetch_with_retry

logger = logging.getLogger(__name__)

def has_text_layer(pdf_path: str) -> bool:
    """
    Check if the PDF has a text layer by inspecting the first 3 pages.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages_to_check = pdf.pages[:3]
            for page in pages_to_check:
                text = page.extract_text()
                if text and len(text.strip()) > 50:
                    return True
        return False
    except Exception as e:
        logger.error(f"Error checking text layer for {pdf_path}: {e}")
        return False

def extract_text_pdf(pdf_path: str) -> str:
    """
    Extract text from a PDF that has a text layer.
    """
    extracted_text = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for n, page in enumerate(pdf.pages, start=1):
                text = page.extract_text(x_tolerance=3, y_tolerance=3, layout=True)
                if text:
                    extracted_text.append(text)
                extracted_text.append(f"\n\n<!-- Page {n} -->\n\n")
    except Exception as e:
        logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
    return "".join(extracted_text)

def extract_html(response: requests.Response) -> tuple[str, str | None]:
    """
    Clean and extract text from an HTML response, and also extract the <title>.
    """
    # Parse raw bytes (response.content) instead of response.text
    # so BeautifulSoup's UnicodeDammit can automatically detect the right encoding
    soup = BeautifulSoup(response.content, 'html.parser')
    
    title_tag = soup.find('title')
    html_title = title_tag.get_text(strip=True) if title_tag else None
    
    # Normalize HTML source whitespace (newlines, tabs) inside text nodes into spaces
    # This prevents heavily nested span tags from breaking words onto new lines
    import re
    for text_node in soup.find_all(string=True):
        if text_node.parent.name not in ['script', 'style', 'pre']:
            cleaned_text = re.sub(r'[\r\n\t]+', ' ', text_node)
            text_node.replace_with(cleaned_text)
            
    for br in soup.find_all('br'):
        br.replace_with('\n')
        
    for op in soup.find_all('o:p'):
        op.insert_after('\n')
        op.unwrap()
        
    for p in soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'dl', 'dt', 'dd']):
        p.insert_before('\n\n')
        p.insert_after('\n\n')
        p.unwrap()
        
    for tr in soup.find_all('tr'):
        tr.insert_before('\n')
        tr.insert_after('\n')
        tr.unwrap()
        
    for tag in soup.find_all(['a', 'script', 'style', 'nav', 'header', 'footer']):
        tag.decompose()
        
    return soup.get_text(separator=''), html_title

def extract_scanned_pdf(pdf_path: str) -> str:
    """
    Extract text from a scanned PDF using OCR.
    """
    extracted_text = []
    try:
        images = pdf2image.convert_from_path(pdf_path, dpi=config.OCR_DPI)
        for n, image in enumerate(images, start=1):
            # Preprocess image
            processed_image = image.convert('L')
            processed_image = ImageEnhance.Contrast(processed_image).enhance(2.0)
            processed_image = processed_image.filter(ImageFilter.SHARPEN)
            processed_image = processed_image.point(lambda x: 0 if x < 140 else 255, '1')
            
            # Run Tesseract
            text = pytesseract.image_to_string(
                processed_image,
                lang='fra',
                config='--oem 3 --psm 6 -c preserve_interword_spaces=1'
            )
            extracted_text.append(text)
            extracted_text.append(f"\n\n<!-- Page {n} -->\n\n")
    except Exception as e:
        logger.error(f"Error extracting text via OCR for {pdf_path}: {e}")
    return "".join(extracted_text)

def extract_document(url_info: dict) -> tuple[str, bool, str | None]:
    """
    Smart router to extract text from a document URL.
    Returns (raw_text, was_ocr, html_title).
    """
    url = url_info["url"]
    
    if url_info["is_pdf"]:
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
        temp_pdf_path = f"/tmp/{url_hash}.pdf"
        try:
            response = fetch_with_retry(url)
            if not response:
                return "", False
                
            with open(temp_pdf_path, 'wb') as f:
                f.write(response.content)
                
            if has_text_layer(temp_pdf_path):
                raw_text = extract_text_pdf(temp_pdf_path)
                was_ocr = False
            else:
                raw_text = extract_scanned_pdf(temp_pdf_path)
                was_ocr = True
                
            return raw_text, was_ocr, None
        finally:
            if os.path.exists(temp_pdf_path):
                try:
                    os.remove(temp_pdf_path)
                except OSError as e:
                    logger.warning(f"Failed to remove temp file {temp_pdf_path}: {e}")
    else:
        response = fetch_with_retry(url)
        if not response:
            return "", False, None
        raw_text, html_title = extract_html(response)
        return raw_text, False, html_title
