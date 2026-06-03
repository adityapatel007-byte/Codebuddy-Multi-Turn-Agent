"""
RAG (Retrieval-Augmented Generation) Engine

Handles the full RAG pipeline:
1. Parse uploaded files (.py, .md, .txt, .pdf)
2. Split text into overlapping chunks
3. Generate embeddings via OpenAI
4. Search for relevant chunks using cosine similarity
"""

import numpy as np
from openai import OpenAI
from typing import Optional
from PyPDF2 import PdfReader

from src.config import OPENAI_API_KEY, EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP, RAG_TOP_K


class RAGEngine:
    """Manages document indexing and semantic search for CodeBuddy."""

    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.chunks: list[dict] = []       # {"text": ..., "filename": ..., "chunk_id": ...}
        self.embeddings: list[list[float]] = []  # Parallel list of embedding vectors
        self.indexed_files: list[str] = []  # Track which files have been indexed

    # -----------------------------------------
    # Step 1: Parse files into raw text
    # -----------------------------------------

    def parse_file(self, filename: str, content: bytes) -> str:
        """Extract text from an uploaded file based on its extension."""
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

        if ext == "pdf":
            return self._parse_pdf(content)
        elif ext in ("py", "js", "ts", "jsx", "tsx", "java", "cpp", "c", "go", "rs", "rb", "php"):
            return content.decode("utf-8", errors="replace")
        elif ext in ("md", "txt", "csv", "json", "yaml", "yml", "toml", "cfg", "ini", "log"):
            return content.decode("utf-8", errors="replace")
        else:
            # Try to decode as text, fall back gracefully
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                return content.decode("latin-1", errors="replace")

    def _parse_pdf(self, content: bytes) -> str:
        """Extract text from PDF bytes."""
        import io
        reader = PdfReader(io.BytesIO(content))
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n\n".join(text_parts)

    # -----------------------------------------
    # Step 2: Split text into chunks
    # -----------------------------------------

    def chunk_text(self, text: str, filename: str) -> list[dict]:
        """
        Split text into overlapping chunks for embedding.

        Uses a sliding window approach:
        - Each chunk is ~CHUNK_SIZE tokens (approximated by words)
        - Chunks overlap by CHUNK_OVERLAP tokens for context continuity
        - Each chunk stores its source filename for citation
        """
        words = text.split()
        chunks = []
        start = 0

        while start < len(words):
            end = start + CHUNK_SIZE
            chunk_text = " ".join(words[start:end])

            chunks.append({
                "text": chunk_text,
                "filename": filename,
                "chunk_id": len(self.chunks) + len(chunks),
            })

            # Move forward by (chunk_size - overlap)
            start += CHUNK_SIZE - CHUNK_OVERLAP

        return chunks

    # -----------------------------------------
    # Step 3: Generate embeddings
    # -----------------------------------------

    def _get_embedding(self, text: str) -> list[float]:
        """Get embedding vector for a single text string."""
        response = self.client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text,
        )
        return response.data[0].embedding

    def _get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for multiple texts in one API call (cheaper + faster)."""
        response = self.client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts,
        )
        return [item.embedding for item in response.data]

    # -----------------------------------------
    # Step 4: Index a file (parse + chunk + embed)
    # -----------------------------------------

    def index_file(self, filename: str, content: bytes) -> int:
        """
        Full indexing pipeline for one file.
        Returns the number of chunks created.
        """
        # Parse file to text
        text = self.parse_file(filename, content)

        if not text.strip():
            return 0

        # Split into chunks
        new_chunks = self.chunk_text(text, filename)

        if not new_chunks:
            return 0

        # Generate embeddings in batch
        chunk_texts = [c["text"] for c in new_chunks]
        new_embeddings = self._get_embeddings_batch(chunk_texts)

        # Store everything
        self.chunks.extend(new_chunks)
        self.embeddings.extend(new_embeddings)
        self.indexed_files.append(filename)

        return len(new_chunks)

    # -----------------------------------------
    # Step 5: Search for relevant chunks
    # -----------------------------------------

    def search(self, query: str, top_k: int = None) -> list[dict]:
        """
        Find the most relevant chunks for a query using cosine similarity.

        Returns a list of dicts with: text, filename, score
        """
        if not self.chunks:
            return []

        top_k = top_k or RAG_TOP_K

        # Embed the query
        query_embedding = self._get_embedding(query)
        query_vec = np.array(query_embedding)

        # Calculate cosine similarity with all stored chunks
        scores = []
        for i, emb in enumerate(self.embeddings):
            emb_vec = np.array(emb)
            # Cosine similarity = dot product / (magnitude_a * magnitude_b)
            similarity = np.dot(query_vec, emb_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(emb_vec)
            )
            scores.append((i, float(similarity)))

        # Sort by similarity (highest first)
        scores.sort(key=lambda x: x[1], reverse=True)

        # Return top-k results
        results = []
        for idx, score in scores[:top_k]:
            chunk = self.chunks[idx]
            results.append({
                "text": chunk["text"],
                "filename": chunk["filename"],
                "score": round(score, 4),
            })

        return results

    # -----------------------------------------
    # Utilities
    # -----------------------------------------

    def clear(self):
        """Remove all indexed documents."""
        self.chunks = []
        self.embeddings = []
        self.indexed_files = []

    def get_stats(self) -> dict:
        """Return indexing statistics."""
        return {
            "files_indexed": len(self.indexed_files),
            "total_chunks": len(self.chunks),
            "filenames": self.indexed_files,
        }

    def has_documents(self) -> bool:
        """Check if any documents have been indexed."""
        return len(self.chunks) > 0

    def format_context(self, results: list[dict]) -> str:
        """
        Format search results into a context string for the LLM prompt.
        Includes source filenames for citation.
        """
        if not results:
            return ""

        context_parts = []
        for i, r in enumerate(results, 1):
            context_parts.append(
                f"--- Source: {r['filename']} (relevance: {r['score']}) ---\n"
                f"{r['text']}"
            )

        return "\n\n".join(context_parts)
