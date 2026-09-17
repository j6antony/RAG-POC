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
class Embed:
    def __init__(self, folder):
        self.folder = folder
        #embedding model
        self.model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    def embed_data(self):
        embedded_chunks = []

        #setup the chunking
        chunk = Chunk(self.folder)
        all_chunks = chunk.get_chunks()
        #iterate throuhgh all the chunks
        for chunk in all_chunks:
            vector = self.model.encode(chunk.page_content)
            # saving this seperatley is better as we are keeping the chunks light
            embedded_chunks.append({
                "text": chunk.page_content,
                "metadata": chunk.metadata,
                "vector": vector
            })
        return embedded_chunks
    def embed_request(self, request):
        vector = self.model.encode(request)
        return vector

