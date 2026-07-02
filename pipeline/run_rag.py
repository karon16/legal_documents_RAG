import argparse
import logging
from pipeline.rag import ask

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test the JusticeCongo AI RAG pipeline"
    )
    parser.add_argument(
        "question",
        help="Legal question in French"
    )
    parser.add_argument(
        "--domain",
        help="Filter by domain e.g. droit_civil, droit_penal",
        default=None
    )
    parser.add_argument(
        "--doc-type",
        help="Filter by doc type e.g. loi, decret",
        default=None
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Skip logging to database"
    )
    args = parser.parse_args()

    result = ask(
        question         = args.question,
        domain_filters   = [args.domain] if args.domain else None,
        doc_type_filters = [args.doc_type] if args.doc_type else None,
        log_to_db        = not args.no_log,
    )

    print("\n" + "=" * 65)
    print("QUESTION:", result.question)
    print("=" * 65)
    print(result.answer)
    print("=" * 65)
    print(f"\nSources ({result.retrieved_count} chunks retrieved):")
    for i, s in enumerate(result.sources, 1):
        print(
            f"  {i}. Art.{s['article_number']} | "
            f"{str(s['document_title'])[:50]} | "
            f"score={s['rrf_score']}"
        )
    print(
        f"\nTiming: retrieval={result.retrieval_ms}ms | "
        f"generation={result.generation_ms}ms"
    )
    print(
        f"Citations: {result.had_citations} | "
        f"Grounded: {result.was_grounded} | "
        f"QA log ID: {result.qa_log_id}"
    )
