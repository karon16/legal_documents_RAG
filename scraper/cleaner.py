import re
import html
import urllib.parse
import os

def clean_html_text(text: str) -> str:
    """
    Clean text extracted from HTML.
    """
    # 1. Decode HTML entities
    text = html.unescape(text)
    
    # 2. Fix common French encoding mojibake
    mojibake_patterns = [
        (re.compile(r'lâ€™'), 'l\''),
        (re.compile(r'Ãª'), 'Ê'),
        (re.compile(r'â'), '\''),
        (re.compile(r'dâ€™'), 'd\''),
        (re.compile(r'lâ€'), 'l\''),
        (re.compile(r'Ã©'), 'é'),
        (re.compile(r'Ã¨'), 'è'),
        (re.compile(r'Ã¢'), 'â'),
        (re.compile(r'Ãª'), 'â'),
        (re.compile(r'Ã»'), 'û'),
        (re.compile(r'Ã®'), 'î'),
        (re.compile(r'ÃŠ'), 'Ê'),
        (re.compile(r'Ã‰'), 'É'),
        (re.compile(r'Ã\s* '), 'à'),
        (re.compile(r'Ã '), 'à'),
        (re.compile(r'dâ€™(?=[a-zA-Z])', re.IGNORECASE), "d'"),
        (re.compile(r'lâ€™(?=[a-zA-Z])', re.IGNORECASE), "l'"),
        (re.compile(r'dâ(?=[a-zA-Z])', re.IGNORECASE), "d'"),
        (re.compile(r'lâ(?=[a-zA-Z])', re.IGNORECASE), "l'"),
    ]
    for pattern, replacement in mojibake_patterns:
        text = pattern.sub(replacement, text)
    
    # 3. Normalize whitespace
    text = text.replace('\t', ' ')
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 3. Strip lines and 4. Remove decorative lines
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append('')
            continue
            
        # Check if line is only decorative characters
        if re.match(r'^[-_=]+$', stripped):
            continue
            
        cleaned_lines.append(stripped)
        
    return '\n'.join(cleaned_lines).strip()

def clean_ocr_text(text: str) -> str:
    """
    Clean OCR text, applying HTML text cleaning first.
    """
    text = clean_html_text(text)
    
    # Compile regexes for performance
    elision_patterns = [
        (re.compile(r"\bl[''´`](?=[A-ZÀ-Ú])"), "l'"),
        (re.compile(r"\bd[''´`](?=[A-ZÀ-Ú])"), "d'"),
        (re.compile(r"\bqu[''´`](?=[a-zà-ú])"), "qu'"),
        (re.compile(r"\bj[''´`](?=[a-zà-ú])"), "j'"),
        (re.compile(r"\bn[''´`](?=[a-zà-ú])"), "n'")
    ]
    
    for pattern, replacement in elision_patterns:
        text = pattern.sub(replacement, text)
        
    line_join_pattern = re.compile(r'(?<![.!?:])\n([a-zà-ùœæ])')
    text = line_join_pattern.sub(r' \1', text)
    
    page_num_patterns = [
        (re.compile(r'\n\s*[-–]\s*\d+\s*[-–]\s*\n'), '\n'),
        (re.compile(r'\n\s*\d+\s*\n(?=[A-Z])'), '\n')
    ]
    for pattern, replacement in page_num_patterns:
        text = pattern.sub(replacement, text)
        
    article_patterns = [
        (re.compile(r'\bArt\s*[.,]\s*(?=\d)'), 'Art. '),
        (re.compile(r'\bARTlCLE\b'), 'ARTICLE')
    ]
    for pattern, replacement in article_patterns:
        text = pattern.sub(replacement, text)
        
    number_format_pattern = re.compile(r'(?<=\d)\.(?=\d{3}\b)')
    text = number_format_pattern.sub('', text)
    
    return text

def extract_title(text: str, url: str) -> str:
    """
    Extract title from text or derive from URL.
    """
    lines = text.split('\n')
    for line in lines:
        stripped = line.strip()
        if len(stripped) > 10 and not stripped.startswith('<!--') and not re.search(r'\bArticle\b', stripped, re.IGNORECASE):
            return stripped
            
    # Fallback to URL
    parsed_url = urllib.parse.urlparse(url)
    filename = os.path.basename(parsed_url.path)
    name_without_ext = os.path.splitext(filename)[0]
    derived_name = name_without_ext.replace('-', ' ').replace('_', ' ').capitalize()
    
    return derived_name if derived_name else "Document sans titre"
