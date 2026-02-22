"""RAG retrieval: ChromaDB client and get_relevant_context for college knowledge."""

import logging
from typing import Optional

from config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_DB_PATH,
    RAG_MAX_TOKENS,
    RAG_TOP_K,
)

logger = logging.getLogger(__name__)

_client: Optional["chromadb.PersistentClient"] = None


def get_chroma_client():
    """Return a persistent ChromaDB client. Reuses a single instance."""
    global _client
    if _client is None:
        import chromadb
        _client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    return _client


def get_collection():
    """Get or create the college_knowledge collection (uses ChromaDB default embedding)."""
    client = get_chroma_client()
    return client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)


def get_relevant_context(
    query: str,
    top_k: int = RAG_TOP_K,
    max_tokens: int = RAG_MAX_TOKENS,
) -> str:
    """
    Retrieve top-k most relevant chunks from ChromaDB for the query.
    Returns concatenated chunk text, trimmed to max_tokens. Empty string on error or empty collection.
    """
    if not (query or query.strip()):
        return ""
    query = query.strip()
    try:
        collection = get_collection()
        result = collection.query(query_texts=[query], n_results=top_k)
        # result["documents"] is list of lists: one list per query, each item is a list of doc strings
        docs = result.get("documents")
        if not docs or not docs[0]:
            logger.debug("RAG: no documents returned for query (collection may be empty or no matches)")
            return ""
        chunks = docs[0]
        combined = "\n\n".join(chunks)
        return _trim_to_tokens(combined, max_tokens)
    except Exception as e:
        logger.warning("RAG retrieval failed: %s", e, exc_info=True)
        return ""


def _trim_to_tokens(text: str, max_tokens: int) -> str:
    """Trim text to at most max_tokens using tiktoken (cl100k_base)."""
    if max_tokens <= 0 or not text:
        return text
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        tokens = enc.encode(text)
        if len(tokens) <= max_tokens:
            return text
        trimmed = enc.decode(tokens[:max_tokens])
        return trimmed
    except Exception as e:
        logger.debug("tiktoken trim failed, returning full text: %s", e)
        return text
