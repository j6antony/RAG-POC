from functools import lru_cache
from embedding import Embed
from vectordb import VectorDB

@lru_cache
def get_embedder():
    return Embed()

@lru_cache
def get_vectorDB():
    return VectorDB("rag-poc", 384)
