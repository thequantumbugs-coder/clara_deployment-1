"""
Ingest college_knowledge.txt into ChromaDB: chunk, embed, and store.
Run once after cloning or when college_knowledge.txt is updated.

Usage (from project root): python -m backend.ingest_college_knowledge
Or from backend dir: python ingest_college_knowledge.py
"""

import re
import sys
from pathlib import Path

# Ensure backend is on path when run as script or -m
_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_DB_PATH,
    COLLEGE_KNOWLEDGE_PATH,
)

# Chunking
MAX_CHUNK_CHARS = 700
OVERLAP_CHARS = 80
SECTION_SEP = "________________________________________"


def _strip_comments(content: str) -> str:
    """Remove leading comment lines (# or <!-- ... -->)."""
    lines = []
    in_comment = False
    for line in content.splitlines():
        s = line.strip()
        if s.startswith("<!--"):
            in_comment = True
        if in_comment:
            if "-->" in s:
                in_comment = False
            continue
        if s.startswith("#") and not s.startswith("# "):
            continue
        lines.append(line)
    return "\n".join(lines)


def _split_into_chunks(text: str) -> list[str]:
    """
    Split text into chunks: first by section separator, then by size with overlap.
    Preserves meaningful boundaries (paragraphs) where possible.
    """
    # Normalize separator and split into major sections
    normalized = text.replace("\r\n", "\n").strip()
    sections = re.split(re.escape(SECTION_SEP), normalized)
    sections = [s.strip() for s in sections if s.strip()]

    chunks = []
    for section in sections:
        # Split section by double newline (paragraphs)
        parts = re.split(r"\n\s*\n", section)
        current = []
        current_len = 0
        for part in parts:
            part = part.strip()
            if not part:
                continue
            part_len = len(part) + (2 if current else 0)  # +2 for "\n\n"
            if current_len + part_len <= MAX_CHUNK_CHARS and current:
                current.append(part)
                current_len += part_len
            else:
                if current:
                    chunk_text = "\n\n".join(current)
                    chunks.append(chunk_text)
                    # Overlap: keep last OVERLAP_CHARS of chunk as start of next
                    if len(chunk_text) > OVERLAP_CHARS:
                        overlap = chunk_text[-OVERLAP_CHARS:].split("\n", 1)[-1]
                        current = [overlap.strip()] if overlap.strip() else []
                        current_len = len(current[0]) if current else 0
                    else:
                        current = []
                        current_len = 0
                # Add the part that triggered the flush (or start fresh)
                if current:
                    current.append(part)
                    current_len = len("\n\n".join(current))
                else:
                    current = [part]
                    current_len = len(part)
        if current:
            chunks.append("\n\n".join(current))
    return [c for c in chunks if c.strip()]


def main() -> None:
    path = Path(COLLEGE_KNOWLEDGE_PATH)
    if not path.is_file():
        print(f"Error: College knowledge file not found: {path}")
        sys.exit(1)

    content = path.read_text(encoding="utf-8")
    content = _strip_comments(content)
    chunks = _split_into_chunks(content)
    if not chunks:
        print("Error: No chunks produced. Check file content.")
        sys.exit(1)

    import chromadb

    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    # Replace existing collection so re-run is idempotent
    try:
        client.delete_collection(name=CHROMA_COLLECTION_NAME)
    except Exception:
        pass
    collection = client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)

    ids = [f"college_{i}" for i in range(len(chunks))]
    collection.add(documents=chunks, ids=ids)
    print(f"Ingested {len(chunks)} chunks from {path} into ChromaDB collection '{CHROMA_COLLECTION_NAME}'.")
    print(f"ChromaDB path: {CHROMA_DB_PATH}")


if __name__ == "__main__":
    main()
