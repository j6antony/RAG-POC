from services import get_embedder, get_vectorDB
from browserbase import Browserbase
import os

class Web:
    def __init__(self):
        self.bb = Browserbase(api_key=os.environ["BROWSERBASE_API_KEY"])
        self.embedder = get_embedder()
        self.vectorDB = get_vectorDB()
    def search_embed(self, request: str, user_id: str, vector):
        response = self.bb.search.web(
            query=request,
            num_results= 5
        )

        for result in response.results:
            page = self.bb.fetch_api.create(
                url = result.url,
                format="markdown"
            )
            self.embedder.embed(result.title, page.content.encode("utf-8"), user_id)
        results = self.vectorDB.query(vector, user_id, 5)
        return results
