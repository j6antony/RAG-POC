"""
- This is the main step for RAG as this is where it will compare similiarities and return the relvent informaiton
- The formula we will be using to compare similarity is cosine similarity
- then order the chunks based of similarity score 
- for now simply just return the top 3 chunks
Issues:
- Am I allowed to just use the prebuilt cosine_similarity function or do i have to build it myself using numpy
"""
from storage import CHROMA_DIR, COLLECTION_NAME
import chromadb

class Retrieval:
    def __init__(self,Request_vector):
        self.Request_vector = Request_vector
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self.collection = client.get_collection(
            name=COLLECTION_NAME
        )
    #if I choose to work with a chromadb vector database then the way to compare is using the inbuilt function
    #note the chromadb uses l2 distance by defualt unless specifcied
    def score_list_chroma (self, count):


        results = self.collection.query(
            query_embeddings=[self.Request_vector.tolist()],
            n_results= count,
            include = ["documents", "metadatas", "distances"]
        )
        return results
    

        
