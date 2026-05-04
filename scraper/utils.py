import re
import os
import requests
import time
import unicodedata
from typing import Optional
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def get_session():
    """Create a requests session with retries and a headers."""
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        "User-Agent": "JusticeCongo-AI-Bot/1.0 (academic research, contact: ppds@ppds.be)"
    })
    return session

def sanitize_filename(filename: str) -> str:
    """
    Remove accents, apostrophes, and other special characters from filenames.
    Optimized for French law titles.
    """
    # Remove apostrophes
    filename = filename.replace("'", "")
    # Normalize unicode to decompose accents (e.g. é -> e + ´)
    filename = unicodedata.normalize('NFD', filename)
    # Remove combining marks (accents)
    filename = "".join([c for c in filename if unicodedata.category(c) != 'Mn'])
    # Replace spaces and common separators with underscores
    filename = re.sub(r'[\s\./\\]+', '_', filename)
    # Filter to only alphanumeric and underscores
    filename = "".join([c for c in filename if c.isalnum() or c == '_']).strip('_')
    return filename[:200]

def download_file(url: str, dest_path: str, session: requests.Session) -> bool:
    """Download a file (PDF) to the destination path."""
    if os.path.exists(dest_path):
        return True
    
    try:
        response = session.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def get_text_content(url: str, session: requests.Session) -> Optional[str]:
    """Fetch and decode HTML content using the correct encoding."""
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        # The site uses ISO-8859-1 for French characters
        if response.encoding == 'ISO-8859-1' or 'iso-8859-1' in response.headers.get('Content-Type', '').lower():
            response.encoding = 'iso-8859-1'
        else:
            response.encoding = response.apparent_encoding
            
        return response.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None
