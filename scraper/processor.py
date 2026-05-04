from fpdf import FPDF
from bs4 import BeautifulSoup
import os
import re

class LawPDF(FPDF):
    def header(self):
        # We can add a simple header if needed
        self.set_font('helvetica', 'B', 8)
        self.cell(0, 10, 'JusticeCongo AI - Legal Corpus (leganet.cd)', 0, 1, 'C')

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def convert_html_to_pdf(html_content: str, title: str, dest_path: str):
    """
    Cleans HTML content and saves it as a PDF.
    This handles common layout elements of leganet.cd law pages.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Try to find the main content. On many leganet pages, it's inside a table or specific div
    # But often it's just the body text excluded the navigation.
    # We strip scripts, styles, and navigation elements.
    for element in soup(["script", "style", "nav", "footer", "header"]):
        element.decompose()

    # Generic cleaning: remove sidebars if they have specific classes or IDs
    # Based on the user's provided HTML snippets, we see 'subnav-box' etc.
    for sidebar in soup.find_all(class_=re.compile("subnav|menu|sidebar", re.I)):
        sidebar.decompose()

    # Get the title if not provided
    if not title:
        title_tag = soup.find('title')
        title = title_tag.get_text().strip() if title_tag else "Document"

    # Get the text content
    text = soup.get_text(separator='\n')
    
    # Simple normalization: remove excessive newlines
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    clean_text = '\n'.join(lines)

    # Generate PDF
    pdf = LawPDF()
    pdf.add_page()
    
    # Add title
    pdf.set_font("helvetica", "B", 16)
    # Handle unicode by replacing common latin-1 characters or using a core font that handles basic latin
    # fpdf2 handles most of this automatically if we use standard fonts, 
    # but we should ensure we don't crash on truly exotic chars.
    pdf.multi_cell(0, 10, title.encode('latin-1', 'replace').decode('latin-1'))
    pdf.ln(10)

    # Add content
    pdf.set_font("helvetica", "", 12)
    # Process text in chunks to avoid layout issues with massive multi_cell
    pdf.multi_cell(0, 6, clean_text.encode('latin-1', 'replace').decode('latin-1'))

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    pdf.output(dest_path)
    return True
