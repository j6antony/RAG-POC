from services import get_embedder, get_vectorDB
from browserbase import Browserbase
import os

class Web:
    def __init__(self):
        self.bb = Browserbase(api_key=os.environ["BROWSERBASE_API_KEY"])
        self.embedder = get_embedder()
        self.vectorDB = get_vectorDB()
    def search(self, request: str):
        responses = self.bb.search.web(
            query=request,
            num_results=5
        )
        pages = []
        for response in responses.results:
            page = self.bb.fetch_api.create(
                url=response.url,
                format="markdown"
            )
            if page.content:
                pages.append({
                    "title": response.title,
                    "url": response.url,
                    "text": page.content
                })
        return pages
    def search_embed(self, pages, user_id: str):
        for page in pages:
            self.embedder.embed(page["title"], page["text"].encode("utf-8"), user_id,self.vectorDB)
