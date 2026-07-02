import logging
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Optional

import ollama
import psycopg2
from pgvector.psycopg2 import register_vector

from pipeline.retriever import retrieve, RetrievedChunk

logger = logging.getLogger(__name__)

MODEL        = "llama3.1"  # A 8B model perfect for Mac M4 with 16GB RAM
MAX_TOKENS   = 1024
TOP_K_CHUNKS = 5

import os
from dotenv import load_dotenv

load_dotenv()
DB_CONN = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/justicecongo")


@dataclass
class RAGResponse:
    question:        str
    answer:          str
    sources:         list[dict]
    retrieved_count: int
    retrieval_ms:    int
    generation_ms:   int
    had_citations:   bool
    was_grounded:    bool = False
    qa_log_id:       Optional[str] = None


SYSTEM_PROMPT = """Tu es l'assistant juridique de JusticeCongo AI, conçu pour aider les citoyens congolais à comprendre leurs lois.

Tes instructions strictes sont les suivantes :

1. Tu dois répondre UNIQUEMENT à partir des extraits de loi fournis. N'utilise jamais tes connaissances générales.
2. Tu dois toujours citer l'article exact et le document source. Exemple de format : "Selon l'Article 5 du Décret du 24 avril 2009..."
3. Si la réponse ne se trouve pas dans les extraits, dis exactement : "Cette information ne figure pas dans les textes disponibles sur LEGANET.CD." N'essaie jamais de répondre quand même.
4. Ta réponse doit être en français clair et accessible. Évite le jargon juridique complexe car l'utilisateur peut être un citoyen ordinaire.
"""


HYDE_PROMPT = """Tu es un expert en droit congolais. 
Rédige un extrait formel et hypothétique d'un texte de loi, de jurisprudence ou de doctrine qui répond directement à la question suivante. 
Ne donne pas d'explications, rédige uniquement l'extrait tel qu'il apparaîtrait dans un document officiel congolais.

Question : {question}
"""


def generate_hyde_document(question: str) -> Optional[str]:
    """
    Generates a hypothetical legal document answering the user's question.
    Used for HyDE (Hypothetical Document Embeddings) to improve semantic search.
    """
    prompt = HYDE_PROMPT.format(question=question)
    try:
        response = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": 300}  # Keep it short
        )
        return response['message']['content']
    except Exception as e:
        logger.error(f"HyDE generation failed: {e}")
        return None


def build_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "Aucun extrait pertinent n'a été trouvé."

    formatted_chunks = []
    for i, chunk in enumerate(chunks, 1):
        label_parts = [f"Source {i}"]
        if chunk.article_number:
            label_parts.append(f"Article {chunk.article_number}")
        if chunk.document_title:
            title = chunk.document_title[:80] + ("..." if len(chunk.document_title) > 80 else "")
            label_parts.append(title)
        if chunk.date_enacted:
            label_parts.append(f"({chunk.date_enacted})")
        
        label = " | ".join(label_parts)
        formatted_chunks.append(f"[{label}]\n{chunk.text}")
        
    return "\n\n---\n\n".join(formatted_chunks)


def build_messages(question: str, chunks: list[RetrievedChunk]) -> list[dict]:
    context = build_context(chunks)
    user_message = (
        "Voici les extraits de loi pertinents tirés de LEGANET.CD :\n\n"
        f"{context}\n\n"
        "---\n\n"
        f"Question : {question}"
    )
    return [{"role": "user", "content": user_message}]


def validate_answer(answer: str) -> dict:
    ans_lower = answer.lower()
    
    citation_keywords = ["article", "source", "décret", "decret", "loi", "ordonnance"]
    has_citation = any(keyword in ans_lower for keyword in citation_keywords)
    
    not_too_short = len(answer.split()) > 15
    
    ignorance_keywords = ["ne figure pas", "pas dans les textes", "pas disponible", "non disponible"]
    admits_ignorance = any(keyword in ans_lower for keyword in ignorance_keywords)
    
    is_valid = has_citation or admits_ignorance
    
    return {
        "has_citation": has_citation,
        "not_too_short": not_too_short,
        "admits_ignorance": admits_ignorance,
        "is_valid": is_valid,
    }


def log_qa(
    conn,
    question:       str,
    answer:         str,
    chunks:         list[RetrievedChunk],
    retrieval_ms:   int,
    generation_ms:  int,
    had_citations:  bool,
    domain_filters: Optional[list[str]] = None,
) -> Optional[str]:
    try:
        domain_str = ",".join(domain_filters) if domain_filters else None
        question_hash = hashlib.md5(question.strip().lower().encode()).hexdigest()
        
        sources_list = []
        for chunk in chunks:
            sources_list.append({
                "chunk_id": chunk.chunk_id,
                "article_number": chunk.article_number,
                "document_title": chunk.document_title,
                "domain": chunk.domain,
                "doc_type": chunk.doc_type,
                "rrf_score": round(chunk.rrf_score, 4) if chunk.rrf_score else None,
                "excerpt": chunk.text[:200]
            })
            
        sources_json = json.dumps(sources_list)
        
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO qa_logs (
                    question, question_hash, answer, sources,
                    domain_filter, retrieval_count,
                    retrieval_ms, generation_ms, had_citations, model_used
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s
                ) RETURNING id
            """, (
                question, question_hash, answer, sources_json,
                domain_str, len(chunks),
                retrieval_ms, generation_ms, had_citations, MODEL
            ))
            log_id = cur.fetchone()[0]
            
        conn.commit()
        return str(log_id)
    except Exception as e:
        logger.error(f"Failed to log QA: {e}")
        return None


def ask(
    question:        str,
    domain_filters:   Optional[list[str]] = None,
    doc_type_filters: Optional[list[str]] = None,
    top_k:           int = TOP_K_CHUNKS,
    log_to_db:       bool = True,
) -> RAGResponse:
    
    # STEP 0 — Input validation
    if not question or not question.strip():
        return RAGResponse(
            question=question, answer="Veuillez poser une question.",
            sources=[], retrieved_count=0, retrieval_ms=0,
            generation_ms=0, had_citations=False, was_grounded=False,
            qa_log_id=None
        )

    question_hash = hashlib.sha256(question.strip().lower().encode('utf-8')).hexdigest()

    # STEP 1 — Open DB connection
    conn = psycopg2.connect(DB_CONN)
    register_vector(conn)

    # STEP 1.2 - Check Cache
    if log_to_db:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, answer, sources, retrieval_count, retrieval_ms, generation_ms, had_citations 
                FROM qa_logs 
                WHERE question_hash = %s 
                ORDER BY created_at DESC LIMIT 1
            """, (question_hash,))
            row = cur.fetchone()
            
            if row:
                logger.info(f"Cache hit for question: {question}")
                
                # Log a new entry to track the cache hit
                cur.execute("""
                    INSERT INTO qa_logs (
                        question, question_hash, answer, sources,
                        domain_filter, retrieval_count, was_cache_hit,
                        retrieval_ms, generation_ms, had_citations, model_used
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s
                    ) RETURNING id
                """, (
                    question, question_hash, row[1], json.dumps(row[2]),
                    ",".join(domain_filters) if domain_filters else None, row[3], True,
                    0, 0, row[6], MODEL
                ))
                new_log_id = cur.fetchone()[0]
                conn.commit()
                conn.close()
                
                return RAGResponse(
                    question=question,
                    answer=row[1],
                    sources=row[2],
                    retrieved_count=row[3],
                    retrieval_ms=0,
                    generation_ms=0,
                    had_citations=row[6],
                    was_grounded=True,
                    qa_log_id=str(new_log_id)
                )

    t0 = time.time()

    # STEP 1.5 - HyDE (Hypothetical Document Embeddings)
    hyde_document = generate_hyde_document(question)

    # STEP 2 — Retrieve
    chunks = retrieve(
        conn            = conn,
        question        = question,
        top_k           = top_k,
        domain_filters   = domain_filters,
        doc_type_filters = doc_type_filters,
        hyde_document   = hyde_document,
    )
    retrieval_ms = int((time.time() - t0) * 1000)

    # STEP 3 — Handle empty retrieval
    if not chunks:
        no_result_answer = (
            "Aucun texte de loi pertinent n'a été trouvé dans la base "
            "de données LEGANET.CD pour cette question. "
            "Essayez de reformuler votre question avec des termes "
            "juridiques plus précis, ou consultez directement "
            "leganet.cd."
        )
        conn.close()
        return RAGResponse(
            question=question, answer=no_result_answer,
            sources=[], retrieved_count=0, retrieval_ms=retrieval_ms,
            generation_ms=0, had_citations=False, was_grounded=False,
            qa_log_id=None
        )

    # STEP 4 — Generate
    messages = build_messages(question, chunks)
    
    # Prepend the system prompt as the first message for Ollama
    ollama_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    t1 = time.time()

    try:
        response = ollama.chat(
            model=MODEL,
            messages=ollama_messages,
            options={
                "num_predict": MAX_TOKENS
            }
        )
        answer = response['message']['content']
    except Exception as e:
        logger.error(f"Ollama API Error: {e}")
        answer = (
            "Une erreur technique s'est produite avec le modèle local. "
            "Veuillez réessayer dans quelques instants."
        )

    generation_ms = int((time.time() - t1) * 1000)

    # STEP 5 — Validate
    validation = validate_answer(answer)
    had_citations = validation["has_citation"]

    # STEP 6 — Build sources list
    sources = []
    for chunk in chunks:
        sources.append({
            "article_number": chunk.article_number,
            "document_title": chunk.document_title,
            "domain": chunk.domain,
            "doc_type": chunk.doc_type,
            "date_enacted": chunk.date_enacted,
            "source_url": chunk.source_url,
            "rrf_score": round(chunk.rrf_score, 4) if chunk.rrf_score else None,
            "excerpt": chunk.text[:300]
        })

    # STEP 7 — Log to DB
    if log_to_db:
        qa_id = log_qa(conn, question, answer, chunks,
                       retrieval_ms, generation_ms,
                       had_citations, domain_filters)
    else:
        qa_id = None

    # STEP 8 — Close and return
    conn.close()

    logger.info(
        f"RAG complete | retrieval={retrieval_ms}ms | "
        f"generation={generation_ms}ms | "
        f"chunks={len(chunks)} | citations={had_citations}"
    )

    return RAGResponse(
        question=question,
        answer=answer,
        sources=sources,
        retrieved_count=len(chunks),
        retrieval_ms=retrieval_ms,
        generation_ms=generation_ms,
        had_citations=had_citations,
        was_grounded=True,
        qa_log_id=qa_id,
    )