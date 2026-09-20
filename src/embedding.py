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
from pathlib import Path
from sentence_transformers import SentenceTransformer
from chunk import Chunk
from storage import DATA_DIR, CHROMA_DIR, COLLECTION_NAME, INDEX_LOCK
import chromadb


class Embed:
    def __init__(self, folder=DATA_DIR):
        self.folder = Path(folder).resolve()
        self.model = SentenceTransformer("BAAI/bge-small-en-v1.5")

    def _collection(self):
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        return client.get_or_create_collection(name=COLLECTION_NAME)

    def _index_file(self, collection, file):
        chunks = Chunk(self.folder).get_chunks_file(file)
        ids = [f"{file.name}_{index}" for index in range(len(chunks))]
        # Finish encoding before changing the existing index. A failed model
        # call must not remove the document's previous chunks.
        vectors = [self.model.encode(chunk.page_content).tolist() for chunk in chunks]
        previous = collection.get(where={"source": file.name}, include=[])["ids"]
        if chunks:
            collection.upsert(
                ids=ids,
                embeddings=vectors,
                documents=[chunk.page_content for chunk in chunks],
                metadatas=[chunk.metadata for chunk in chunks],
            )
        # Also removes legacy bulk IDs and surplus chunks when a file shrinks
        # or becomes empty. Other documents are left alone.
        stale = sorted(set(previous) - set(ids))
        if stale:
            collection.delete(ids=stale)

    def embed_data(self):
        if not self.folder.is_dir():
            raise FileNotFoundError(f"Document folder does not exist: {self.folder}")
        with INDEX_LOCK:
            collection = self._collection()
            for file in sorted(self.folder.glob("*.md")):
                if file.is_file():
                    self._index_file(collection, file)
            return collection

    def embed_request(self, request):
        return self.model.encode(request)

    def embed_data_file(self, data):
        file = Path(data)
        if not file.is_absolute():
            file = self.folder / file
        with INDEX_LOCK:
            collection = self._collection()
            self._index_file(collection, file)
            return collection
