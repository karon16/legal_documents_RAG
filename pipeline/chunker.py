import re # imported for regex operations such as splitting the document into chunks
import logging # imported for logging info messages
from dataclasses import dataclass, field # imported from the dataclasses module for metadata rich chunks


logger = logging.getLogger(__name__) # this is for logging info messages

# article pattern to capture articles of the document
ARTICLE_PATTERN = re.compile(
    r'(?:^|\n)\s*'
    r'(?:ARTICLE|Article|ART\.|Art\.)\s+'
    r'(premier|PREMIER|unique|UNIQUE|1er|1ère|\d+|[IVXLCDM\|]{1,6})'
    r'(?:\s*[.:\-\—\s])',
    re.MULTILINE | re.IGNORECASE
)

# chapter pattern to capture chapters of the document
CHAPTER_PATTERN = re.compile(
    r'(?:^|\n)\s*'
    r'(?:CHAPITRE|Chapitre|TITRE|Titre|PARTIE|Partie|LIVRE|Livre)\s+'
    r'([IVXLCDMivxlcdm\|]{1,6}|1ère|1er|premier|unique|\d+)'
    r'(?:\s*[.:\-\—])?\s*(.{0,80})',
    re.MULTILINE | re.IGNORECASE
)

# section pattern to capture sections of the document
SECTION_PATTERN = re.compile(
    r'(?:^|\n)\s*'
    r'(?:SECTION|Section|Paragraphe|PARAGRAPHE)\s+'
    r'([IVXLCDMivxlcdm\|]{1,6}|1ère|1er|premier|unique|\d+)'
    r'(?:\s*[.:\-\—])?\s*(.{0,80})',
    re.MULTILINE | re.IGNORECASE
)

PAGE_PATTERN = re.compile(r'<!-- Page (\d+) -->', re.IGNORECASE)

MAX_CHUNK_TOKENS = 500
OVELAP_TOKENS = 80
MIN_CHUNK_WORDS = 10

@dataclass
class Chunk:
    document_id:     str
    chunk_index:     int
    text:            str
    article_number:  str | None
    chapter_heading: str | None
    section_heading: str | None
    page_number:     int | None
    token_count:     int
    metadata:        dict = field(default_factory=dict)


#token counting function
def count_tokens(text: str) -> int:
    """Approximates token count for French text. 
    A rough heuristic: ~1.3 tokens per word for French.
    """
    words = len(text.split())
    return int(words * 1.3)


# Structure detection
def extract_structure(text: str) -> dict:
    """
    Extracts structural elements from text using regex.
    Returns article, chapter, and section boundaries.
    """
    article_positions = []

    for match in ARTICLE_PATTERN.finditer(text):
        article_positions.append({
            "match": match,
            "number": match.group(1),
            "start": match.start(),
            "end": match.end()
        })
    
    chapter_positions = []
    for match in CHAPTER_PATTERN.finditer(text):
        number = match.group(1)
        heading = match.group(2).strip()
        full = f"CHAPITRE {number}" + (f" - {heading}" if heading else "")
        chapter_positions.append({
            'heading': full,
            'start': match.start()
        })
    
    section_positions = []
    for match in SECTION_PATTERN.finditer(text):
        number  = match.group(1)
        heading = match.group(2).strip()
        full    = f"Section {number}" + (f" — {heading}" if heading else "")
        section_positions.append({
            "heading": full,
            "start":   match.start(),
        })
        
    page_positions = []
    for match in PAGE_PATTERN.finditer(text):
        page_positions.append({
            "number": int(match.group(1)),
            "start": match.start()
        })
    
    return {
        "article_positions": article_positions,
        "chapter_positions": chapter_positions,
        "section_positions": section_positions,
        "page_positions": page_positions,
        "has_article_structure": len(article_positions) >= 2
    }


# contet prefix builder
def build_context_prefix(prev_chunk_text: str | None) -> str:
    if prev_chunk_text is None:
        return ""
    
    # Extract last sentence of previous chunk
    sentences = re.split(r'(?<=[.!?;])\s+', prev_chunk_text.strip())

    last_sentences = [s for s in sentences if s.strip()][-2:]

    if not last_sentences:
        return ""
    
    context = ' '.join(last_sentences)
    return f"[Contexte: {context}]\n\n"


# fixed-size fallback splitter
def split_by_tokens(
    text: str,
    max_tokens: int = MAX_CHUNK_TOKENS,
    overlap: int = OVELAP_TOKENS,

) -> list[str]:

    words  = text.split() # convert the text into a list of words
    max_words = int(max_tokens / 1.3)  # max words per chunk
    overlap_words = int(overlap / 1.3) # overlap in words

    if(len(words) <= max_words):
        return [text]
    
    chunks = []
    start = 0

    while start < len(words):
        end = min(start + max_words, len(words))
        chunks.append(' '.join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap_words  # Step back by overlap

    return chunks


def chunk_document(document_id: str,
    raw_text: str,
    domain: str | None = None,
    doc_type: str | None = None,
    
) -> list[Chunk]:
    """
    Splits a document into article-based chunks with overlap and context.
    """
    if not raw_text or not raw_text.strip():
        logger.warning(f"Document {document_id} has empty raw_text - skipping.")
        return []

    
    structure = extract_structure(raw_text)
    chunks: list[Chunk] = []
    chunk_idx = 0
    prev_text = None

    if structure["has_article_structure"]:
        article_positions = structure["article_positions"]

        for i, article in enumerate(article_positions):
            art_start = article["start"]   
            art_end   = (article_positions[i + 1]["start"]
                         if i + 1 < len(article_positions)
                         else len(raw_text))
            article_text = raw_text[art_start:art_end].strip()

            chapter_heading = None
            for chapter in reversed(structure["chapter_positions"]):
                if chapter["start"] <= art_start:
                    chapter_heading = chapter["heading"]
                    break
            
            section_heading = None
            for section in reversed(structure["section_positions"]):
                if section["start"] <= art_start:
                    section_heading = section["heading"]
                    break
                    
            page_number = None
            for page in reversed(structure["page_positions"]):
                if page["start"] <= art_start:
                    page_number = page["number"]
                    break
            
            base_meta = {
                "domain" : domain,
                "doc_type": doc_type,
            }

            if count_tokens(article_text) <= MAX_CHUNK_TOKENS:
                prefix = build_context_prefix(prev_text)
                final_text = prefix + article_text

                if len(final_text.split()) < MIN_CHUNK_WORDS:
                    logger.debug(f"skipping shor chunk: {final_text[:60]!r}")
                    continue

                chunks.append(Chunk(
                    document_id     = document_id,
                    chunk_index     = chunk_idx,
                    text            = final_text,
                    article_number  = article["number"],
                    chapter_heading = chapter_heading,
                    section_heading = section_heading,
                    page_number     = page_number,
                    token_count     = count_tokens(article_text),
                    metadata        = {
                        **base_meta,
                        "has_context_prefix": prev_text is not None,
                    }
                ))
                chunk_idx += 1
            else:
                sub_texts = split_by_tokens(article_text)
                for j, sub in enumerate(sub_texts):
                    prefix     = build_context_prefix(
                        prev_text if j == 0 else sub_texts[j - 1]
                    )
                    final_text = prefix + sub

                    if len(final_text.split()) < MIN_CHUNK_WORDS:
                        continue

                    chunks.append(Chunk(
                        document_id     = document_id,
                        chunk_index     = chunk_idx,
                        text            = final_text,
                        article_number  = f"{article['number']}.{j + 1}",
                        chapter_heading = chapter_heading,
                        section_heading = section_heading,
                        page_number     = page_number,
                        token_count     = count_tokens(sub),
                        metadata        = {
                            **base_meta,
                            "has_context_prefix": True,
                            "is_split":           True,
                            "split_index":        j,
                        }
                    ))
                    chunk_idx += 1

            prev_text = article_text
        # ── PATH B: No article structure — fixed-size fallback ────────────────────
    else:
        logger.info(f"Document {document_id} has no article structure — using fixed-size chunking")
        sub_texts = split_by_tokens(raw_text)

        for j, sub in enumerate(sub_texts):
            if len(sub.split()) < MIN_CHUNK_WORDS:
                continue
                
            sub_start = raw_text.find(sub)
            if sub_start == -1: sub_start = 0
            
            chapter_heading = None
            for chapter in reversed(structure["chapter_positions"]):
                if chapter["start"] <= sub_start:
                    chapter_heading = chapter["heading"]
                    break
                    
            section_heading = None
            for section in reversed(structure["section_positions"]):
                if section["start"] <= sub_start:
                    section_heading = section["heading"]
                    break
                    
            page_number = None
            for page in reversed(structure["page_positions"]):
                if page["start"] <= sub_start:
                    page_number = page["number"]
                    break

            chunks.append(Chunk(
                document_id     = document_id,
                chunk_index     = chunk_idx,
                text            = sub,
                article_number  = None,
                chapter_heading = chapter_heading,
                section_heading = section_heading,
                page_number     = page_number,
                token_count     = count_tokens(sub),
                metadata        = {
                    "domain":              domain,
                    "doc_type":            doc_type,
                    "no_article_structure": True,
                }
            ))
            chunk_idx += 1

    logger.info(
        f"Document {document_id}: {len(chunks)} chunks "
        f"({'article-level' if structure['has_article_structure'] else 'fixed-size'})"
    )
    return chunks

