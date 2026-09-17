"""
- This is the main step for RAG as this is where it will compare similiarities and return the relvent informaiton
- The formula we will be using to compare similarity is cosine similarity
- then order the chunks based of similarity score 
- for now simply just return the top 3 chunks
Issues:
- Am I allowed to just use the prebuilt cosine_similarity function or do i have to build it myself using numpy
"""
from sklearn.metrics.pairwise import cosine_similarity

class Retrieval:
    def __init__(self,Request_vector, Vector_Database):
        self.A = Request_vector
        self.B = Vector_Database
    def score_list (self, count):
        result = []
        for chunk in self.B:
            score = cosine_similarity(
                [self.A],
                [chunk["vector"]]
            )[0][0]
            result.append((score, chunk))
        #sort in ascending order
        result.sort(key=lambda x: x[0], reverse=True)
        return result[:count]
    

        
