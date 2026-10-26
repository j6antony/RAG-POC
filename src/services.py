from functools import lru_cache

from vectordb import VectorDB
from gliner2 import AutoExtractor
from knowledge_graph import KnowledgeGraph

@lru_cache
def get_embedder():
    from embedding import Embed
    return Embed()

@lru_cache
def get_vectorDB():
    return VectorDB("rag-poc", 384)

@lru_cache
def get_gliner():
    model = AutoExtractor.from_pretrained(
        "fastino/gliner2-base-v1"
    )
    return model

@lru_cache
def get_knowledge_graph():
    return KnowledgeGraph()