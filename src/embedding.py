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
from sentence_transformers import SentenceTransformer
from chunk import Chunk
from vectordb import VectorDB


class Embed:

    def __init__(self):
        self.model = SentenceTransformer("BAAI/bge-small-en-v1.5")
        self.chunk = Chunk()
    def embed(self, filename, contents, id, vectorDB: VectorDB):

        chunks = self.chunk.get_chunks_file(contents, filename)

        texts = [chunk.page_content for chunk in chunks]

        embeddings = self.model.encode(texts)

        vectors = []

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vectors.append({
                "id": f"{filename}-{i}",
                "values": embedding.tolist(),
                "metadata": {
                    "filename": filename,
                    "text": chunk.page_content
                }
            })

        vectorDB.upsert(
            vectors=vectors,
            namespace=id
        )
    def embed_request(self, text):
        return self.model.encode(text)


