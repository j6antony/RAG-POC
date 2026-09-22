import os
from pinecone import Pinecone, ServerlessSpec

class VectorDB:
    def __init__(self, index_name: str, dimensions: int):

        pc = Pinecone(
            api_key=os.getenv("PINECONE_API_KEY")
        )

        if index_name not in [index.name for index in pc.list_indexes()]:
            pc.create_index(
                name=index_name,
                dimension=dimensions,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
        )

        self.index = pc.Index(index_name)
    def upsert(self, vectors, namespace:str):
        self.index.upsert(
            vectors=vectors,
            namespace=namespace
        )
    def query(self, vector, namespace: int, top_k):
        return self.index.query(
            vector=vector,
            top_k=top_k,
            include_metadata=True,
            namespace=namespace
        )




