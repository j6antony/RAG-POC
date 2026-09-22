"""Pinecone access; every operation requires a user's namespace."""
import os
from hashlib import sha256
from functools import lru_cache

from pinecone import Pinecone, ServerlessSpec


def document_prefix(filename: str):
    # Pinecone IDs must be ASCII. Keep existing IDs for ordinary filenames.
    name = filename if filename.isascii() else sha256(filename.encode('utf-8')).hexdigest()
    return f'{name}-'


class VectorDB:
    def __init__(self, index_name: str, dimensions: int):
        pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        if index_name not in [index.name for index in pc.list_indexes()]:
            pc.create_index(
                name=index_name, dimension=dimensions, metric='cosine',
                spec=ServerlessSpec(cloud='aws', region='us-east-1'), timeout=60,
            )
        description = pc.describe_index(index_name)
        if description.dimension != dimensions:
            raise ValueError(f'Pinecone index must have {dimensions} dimensions for the embedding model.')
        self.index = pc.Index(host=description.host)

    def upsert(self, vectors, namespace: str):
        if not namespace:
            raise ValueError('A user namespace is required.')
        for offset in range(0, len(vectors), 100):
            self.index.upsert(vectors=vectors[offset:offset + 100], namespace=namespace)

    def query(self, vector, namespace: str, top_k: int = 5):
        if not namespace:
            raise ValueError('A user namespace is required.')
        return self.index.query(vector=vector, top_k=top_k, include_metadata=True, namespace=namespace)

    def replace_document(self, vectors, filename: str, namespace: str):
        if not namespace:
            raise ValueError('A user namespace is required.')
        prefix = document_prefix(filename)
        previous_ids = {
            item.id
            for page in self.index.list(prefix=prefix, namespace=namespace)
            for item in page.vectors
            if item.id[len(prefix):].isdigit()
        }
        # Finish the new writes before removing leftover chunks from a shorter file.
        self.upsert(vectors, namespace)
        stale_ids = sorted(previous_ids - {vector['id'] for vector in vectors})
        for offset in range(0, len(stale_ids), 1000):
            self.index.delete(ids=stale_ids[offset:offset + 1000], namespace=namespace)


@lru_cache(maxsize=1)
def get_vector_db():
    return VectorDB(os.getenv('PINECONE_INDEX', 'rag-poc'), 384)
