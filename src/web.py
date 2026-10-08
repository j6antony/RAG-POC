from services import get_embedder, get_vectorDB
from browserbase import Browserbase
import os
from uuid import uuid4


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
            try:    
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
            except Exception as error:
                print(f"Failed to fetch {response.url}: {error}")
                continue
        return pages
    def search_embed(self, pages, user_id: str, user_access: int):
        for page in pages:
            self.embedder.embed(\n                page["title"], page["text"].encode("utf-8"), user_id,\n                self.vectorDB, user_access, str(uuid4()), "internal"\n            )
