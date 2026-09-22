"""Embed documents and questions with the same cached model."""
from functools import lru_cache
from threading import RLock

from src.chunk import Chunk
from src.vectordb import document_prefix, get_vector_db


class Embed:
    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer('BAAI/bge-small-en-v1.5')
        self.chunk = Chunk()
        self.lock = RLock()

    def embed(self, filename: str, contents: bytes, user_id: str):
        chunks = self.chunk.get_chunks_file(contents, filename)
        if not chunks:
            raise ValueError('The document has no text to index.')
        with self.lock:
            embeddings = self.model.encode([chunk.page_content for chunk in chunks])
            vectors = [
                {'id': f'{document_prefix(filename)}{i}', 'values': embedding.tolist(),
                 'metadata': {**chunk.metadata, 'filename': filename, 'text': chunk.page_content}}
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
            ]
            get_vector_db().replace_document(vectors, filename, namespace=user_id)
        return len(vectors)

    def embed_request(self, text):
        with self.lock:
            return self.model.encode(text)


@lru_cache(maxsize=1)
def get_embedder():
    return Embed()
