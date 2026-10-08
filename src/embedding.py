"""
- For embedding we are not embedding the metadata of the chunks but simply the text of the individual chunks
- For this POC we are choosing to use a locally run embedder but for real time usage it will likley be an API
- reason we are doing this is becuase other has a cost attached to it
- The model we are going with BAAI/bge-small-en-v1.5
- ensure that the same model is used to embed the request as well
Issues:
- the list I have created here I am just using that as like the vector database not sure if this is correct
- do i have to chunk the users request, like what if it is very huge
"""
from huggingface_hub import InferenceClient
from chunk import Chunk
from vectordb import VectorDB
import os
import numpy as np


class Embed:

    def __init__(self):
        self.client = InferenceClient(
            provider="hf-inference",
            api_key=os.environ["HF_TOKEN"]
        )
        self.model_NAME ="BAAI/bge-small-en-v1.5"
        self.chunk = Chunk()
    def encode(self, texts):
        is_single = isinstance(texts, str)
        embeddings = self.client.feature_extraction(
            texts, model=self.model_NAME
        )
        embeddings = np.asarray(embeddings, dtype=np.float32)
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        if embeddings.ndim != 2 or embeddings.shape[1] != 384:
            raise ValueError(f"Unexpected embedding shape: {embeddings.shape}")
        expected = 1 if is_single else len(texts)
        if embeddings.shape[0] != expected:
            raise ValueError(f"Expected {expected} vectors, got {embeddings.shape[0]}")
        return embeddings

    def embed(self, filename, contents, id, vectorDB: VectorDB, access_level: int, document_id,classification, contains_sensitive_data=False, chunks=None):
        print("started embedding")

        if chunks is None:
            chunks = self.chunk.get_chunks_file(contents, filename)
        if not chunks:
            raise ValueError("The document contains no searchable text.")

        texts = [chunk.page_content for chunk in chunks]

        embeddings = self.encode(texts)

        vectors = []

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vectors.append({
                "id": f"{document_id}-{i}",
                "values": embedding.tolist(),
                "metadata": {
                    "document_id": str(document_id),
                    "filename": filename,
                    "text": chunk.page_content,
                    "owner_id": str(id),
                    "access_level": access_level,
                    "classification": classification,
                    "contains_sensitive_data": contains_sensitive_data,
                    **{key: chunk.metadata[key] for key in ("page", "image_ids") if key in chunk.metadata}
                }
            })
        # the reason this is required is sometimes the scraped website may give you no data then there is not point in doing and uspert and the uspert will fail which is why I 
        # have implemented this saftey check. The problem with this is that the websearch will give you nothing so the LLM will really not get any quality context

        vectorDB.upsert(
            vectors=vectors,
            namespace="company"
        )
        print("finished embedding")
    def embed_request(self, text):
        return self.encode(text)[0]


