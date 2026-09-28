"""
- This is the main step for RAG as this is where it will compare similiarities and return the relvent informaiton
- The formula we will be using to compare similarity is cosine similarity
- then order the chunks based of similarity score 
- for now simply just return the top 3 chunks
Issues:
- Am I allowed to just use the prebuilt cosine_similarity function or do i have to build it myself using numpy
"""

from vectordb import VectorDB
from authentification import get_user_access

class Retrieval:
    def __init__(self,Request_vector, id):
        self.Request_vector = Request_vector
        self.id = id
    def retrieve (self, vectorDB: VectorDB, count, id, request):
        #this is very inefficient just for simplicity sake i have done it like this us ai to fix this it is very simple just tedious
        user_access = get_user_access(id)
        return vectorDB.query(request, "company", count, user_access, id)
    
    

        
