"""
- This is the main step for RAG as this is where it will compare similiarities and return the relvent informaiton
- The formula we will be using to compare similarity is cosine similarity
- then order the chunks based of similarity score 
- for now simply just return the top 3 chunks
Issues:
- Am I allowed to just use the prebuilt cosine_similarity function or do i have to build it myself using numpy
"""

from vectordb import VectorDB

class Retrieval:
    def __init__(self,Request_vector, id):
        self.Request_vector = Request_vector
        self.id = id
    def retrieve (self, vectorDB: VectorDB, count, id, request):
        return vectorDB.query(request, id, count)
    
    

        
