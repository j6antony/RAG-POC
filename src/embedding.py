"""Generate document and query embeddings via the hosted Gemini API."""
from google import genai
from google.genai import types
from chunk import Chunk
from vectordb import VectorDB
import os
import numpy as np


class Embed:

    def __init__(self):
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.model_NAME = "gemini-embedding-001"
        self.dimensions = 768
        self.chunk = Chunk()

    def encode(self, texts, task_type="RETRIEVAL_DOCUMENT"):
        is_single = isinstance(texts, str)
        texts = [texts] if is_single else list(texts)
        if not texts:
            return np.empty((0, self.dimensions), dtype=np.float32)

        vectors = []
        for offset in range(0, len(texts), 32):
            batch = texts[offset:offset + 32]
            response = self.client.models.embed_content(
                model=self.model_NAME,
                contents=batch,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=self.dimensions,
                ),
            )
            vectors.extend(item.values for item in response.embeddings)

        embeddings = np.asarray(vectors, dtype=np.float32)
        if embeddings.shape != (len(texts), self.dimensions):
            raise ValueError(f"Unexpected embedding shape: {embeddings.shape}")
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
        return self.encode(text, task_type="RETRIEVAL_QUERY")[0]


