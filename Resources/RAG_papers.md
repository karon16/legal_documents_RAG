# Retrieval-Augmented Generation (RAG) Resources

This document is a curated summary of research papers, articles, and documentation focused on improving and understanding RAG systems.

## Core RAG Innovations

* **[OpenRAG: Optimizing RAG End-to-End via In-Context Retrieval Learning](https://arxiv.org/html/2503.08398v1)**
  Analyzes how learned relevance for IR can be inconsistent for RAG, and introduces OpenRAG, a framework optimized end-to-end by tuning the retriever to capture in-context relevance.

* **[Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection](https://arxiv.org/abs/2310.11511)**
  Introduces Self-RAG, a framework that trains an LM to adaptively retrieve passages on-demand, and generate and reflect on retrieved passages and its own generations using special reflection tokens.

* **[Corrective Retrieval Augmented Generation (CRAG)](https://arxiv.org/abs/2401.15884)**
  Proposes CRAG to improve robustness by using a lightweight retrieval evaluator to assess the quality of retrieved documents, triggering different retrieval actions (like web search) and decomposing/recomposing documents to filter out irrelevant info.

## Context Quality & Retrieval Analysis

* **[Sufficient Context: A New Lens on Retrieval Augmented Generation Systems](https://arxiv.org/abs/2411.06037)**
  Investigates whether errors in RAG systems stem from LLMs failing to use context or the context being insufficient. Categorizes errors and shows that larger models excel with sufficient context but struggle when it's lacking, while smaller models hallucinate even with good context.
  * *See also: [Google Research Blog: Deeper insights into retrieval augmented generation](https://research.google/blog/deeper-insights-into-retrieval-augmented-generation-the-role-of-sufficient-context/)*

* **[Toward Optimal Search and Retrieval for RAG](https://arxiv.org/abs/2411.07396)**
  Explores the relationship between retrieval and RAG performance on QA tasks, showing insights such as lowering search accuracy having minor implications for RAG performance while increasing speed and efficiency.

## Efficiency & Adaptive Retrieval

* **[Retrieval as a Decision: Training-Free Adaptive Gating for Efficient RAG (TARG)](https://arxiv.org/abs/2511.09803)**
  Proposes a training-free adaptive policy that decides when to retrieve using uncertainty scores from a no-context draft prefix, cutting retrieval by 70-90% without sacrificing accuracy.

* **[LIR³AG: A Lightweight Rerank Reasoning Strategy Framework for RAG](https://arxiv.org/abs/2512.18329)**
  Studies reasoning strategies in multi-hop QA and proposes a framework to transfer reasoning strategies to non-reasoning models by restructuring retrieved evidence into coherent reasoning chains, significantly reducing token overhead and inference time.

## Practical Techniques & Guides

* **[Improving RAG accuracy: 10 techniques that actually work (Redis Blog)](https://redis.io/blog/10-techniques-to-improve-rag-accuracy/)**
  A practical guide to boosting RAG accuracy using techniques like hybrid search, semantic caching, and pipeline improvements.

* **[Hypothetical Document Embeddings (HyDE) (Haystack Docs)](https://docs.haystack.deepset.ai/docs/hypothetical-document-embeddings-hyde)**
  Documentation on implementing HyDE in Haystack—a technique that generates a mock-up hypothetical document for an initial query to improve retrieval in unseen domains.