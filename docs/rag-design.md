# Hybrid RAG Design

## Scope

Stage 4 retrieves evidence from approved restaurant documents. It does not generate final answers, access live reservation availability, call LangGraph, or maintain conversation memory. ChromaDB and BM25 contain document knowledge only; PostgreSQL remains authoritative for reservations.

## Ingestion architecture

```text
Markdown / text / PDF
        |
   validated loader
        |
 heading-aware deterministic chunker
        |
 selected embedding provider
        |
 replace source in persistent Chroma
        |
 rebuild in-memory BM25 from Chroma chunks
```

Files are accepted only by extension (`.md`, `.txt`, `.pdf`). Markdown and text use UTF-8. PDF text is extracted with pypdf; OCR and web scraping are deliberately excluded. Empty documents and unsupported formats fail with safe application errors. Upload filenames are reduced to a basename and the API never accepts arbitrary paths.

Source replacement deletes that source's existing chunks and upserts the new stable IDs. This makes repeated ingestion deterministic and prevents duplicate chunks. The default directory is not ingested automatically at startup.

## Chunking method

Markdown headings define sections when available. Text within each section is split on paragraph boundaries until the configured character budget is reached. Oversized paragraphs use deterministic sliding windows. A configurable tail overlap preserves local context between adjacent chunks.

Chunk IDs are SHA-256 hashes of the source, section, position, and exact chunk text. Every chunk retains its source, document title, section, document type, and JSON-serializable metadata. Empty chunks are discarded.

## Embedding provider architecture

```text
Settings (EMBEDDING_PROVIDER)
              |
       Provider factory
       /      |       \
   Google   OpenAI    Local
       \      |       /
      EmbeddingProvider
              |
          RAG service
```

The abstract provider exposes async `embed_documents()` and `embed_query()` methods. The RAG service knows only this interface. The factory selects `google` by default, `openai`, or `local` from validated settings.

- Google uses the official `google-genai` async embedding API, retrieval task types, a 30-second timeout, and bounded retries for transient HTTP status codes.
- OpenAI preserves the existing direct async SDK behavior.
- Local uses `sentence-transformers` in a worker thread, requires no key, normalizes vectors, and lazily downloads/loads its model on first use.

Remote providers validate their own key only when called, so API startup and knowledge statistics remain available without credentials. All providers verify vector counts and convert initialization/request failures to safe application errors. Keys and provider payloads are never logged. Tests inject deterministic fakes and test factory selection without network calls.

## Vector and BM25 indexes

One persistent Chroma client and collection are created lazily per application. Chroma stores stable IDs, document text, source metadata, and caller-supplied embeddings. It supports source replacement, deletion, cosine search, counts, and full chunk reads used to rebuild BM25. The collection is not recreated for each request.

BM25 is an in-memory lexical index built from all chunks currently stored in Chroma. Tokenization lowercases Unicode word tokens and intentionally avoids complex language-specific preprocessing. The index is rebuilt after ingestion and deletion and hydrated from Chroma when the service is constructed. An empty index safely returns no matches.

## Hybrid fusion

For a query:

1. The selected provider creates one query embedding.
2. Chroma returns semantic candidates and cosine-derived similarity scores.
3. BM25 returns lexical candidates.
4. Each list is independently min-max normalized to 0–1. A non-zero single-score list receives 1.0.
5. Candidates are deduplicated by stable chunk ID.
6. Scores are combined as `vector_weight × vector_score + bm25_weight × bm25_score`, after weights are normalized to sum to one.
7. Results below the threshold are removed, sorted by hybrid score, and limited to top K.
8. The default no-op reranker preserves that order.

This balances semantic paraphrases with exact menu names, allergens, times, and policy terms. If either retriever has no results, the available retriever can still contribute. Score breakdowns remain visible for evaluation.

## Reranking extension

The `Reranker` protocol and `NoOpReranker` allow a future cross-encoder or hosted reranker after fusion without changing ingestion or candidate retrieval. Stage 4 adds no transformer model or external reranking call.

## Context and citations

Retrieved context uses markers such as:

```text
[Source: menu.md | Section: Main Course]
<retrieved chunk text>
```

Each result exposes source, title, section, chunk ID, score breakdown, and a bounded excerpt. Citations are created only from returned chunks. When thresholding removes every result, context and citations are empty and `evidence_found` is false.

## Error handling

- Unsupported types and empty documents return client validation errors.
- Missing embedding configuration returns a clear service-unavailable error.
- Provider, Chroma, and retrieval failures become safe service errors with internal logging.
- Missing source deletion returns not found.
- Blank queries and invalid top K values are rejected by Pydantic.

Errors do not expose API keys, provider responses, document bodies, or internal paths.

## Evaluation ideas

- Build English, Hindi, and Gujarati question sets for every knowledge category.
- Track recall@K, mean reciprocal rank, citation correctness, and no-evidence precision.
- Include exact terms, paraphrases, misspellings, and unrelated questions.
- Tune chunk size, overlap, weights, threshold, and candidate count on held-out questions.
- Verify that availability questions never imply live database state.
- Add regression cases whenever approved documents change.

## Limitations

- Multilingual semantic quality depends on the selected provider and model.
- BM25 has no stemming, transliteration, or spelling correction.
- BM25 is process-local; every worker must rebuild it from Chroma.
- Source replacement is not a distributed transaction with the embedding provider.
- PDF OCR, tables, images, web pages, final answer generation, medical assurance, and live availability are excluded.
- Relevance settings require evaluation against realistic restaurant questions.
- Providers produce different vector dimensions; switching requires reingesting into an empty or separately named Chroma collection.
