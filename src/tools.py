from web import Web
from vectordb import VectorDB
from services import get_embedder, get_vectorDB
import asyncio
from google import genai
from google.genai import types
import supabase
class Tools:
    def __init__(self, web: Web, user_access: int, user_id: str, supabase: supabase):
        self.web = web
        self.vectorDB = get_vectorDB()
        self.embedder = get_embedder()
        self.namespace = "company"
        self.access = user_access
        self.user_id = user_id
        self.supabase = supabase
    async def search_internal(self, request: str):
        request_vector = await asyncio.to_thread(
            self.embedder.embed_request,
            request
        )

        request_vector = request_vector.tolist()

        response = await asyncio.to_thread(
            self.vectorDB.query,
            request_vector,
            self.namespace,
            5,
            self.access,
            self.user_id
        )

        return {
            "matches": [
                {
                    "id": match.id,
                    "score": match.score,
                    "metadata": match.metadata
                }
                for match in response.matches
            ]
        }
    async def search_web(self, request: str):
        #just testing the build so for now web embedding will not be happening
       return await asyncio.to_thread(
            self.web.search,
            request
        )
    async def rewrite_query(self, request: str, history):
        context = "\n".join(
             f"{message.role}: {message.text}"
            for message in history[-6:]
        )
        prompt = f"""
        Conversation history:
        {context}

        Current request:
        {request}

        Rewrite the current request so it can be understood without the conversation history.
        """

        client = genai.Client()

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="""
                Rewrite conversational user questions into standalone queries.

                Use conversation history only to resolve references or missing context.
                Do not answer the question.
                Do not invent information.
                Return only the rewritten request.
                """
            )
        )

        return response.text.strip()
    # need to build the following functions from scratch also have to setup a supabase table for it :(
    async def get_user_facts(self):
        response = await asyncio.to_thread(
            lambda: self.supabase
            .table("user_facts")
            .select("key,value")
            .eq("user_id", self.user_id)
            .execute()
        )

        return response.data
    async def save_user_fact(self, key: str, value: str):
        response = await asyncio.to_thread(
            lambda: self.supabase
            .table("user_facts")
            .upsert(
                {
                    "user_id": self.user_id,
                    "key": key,
                    "value": value
                },
                on_conflict="user_id,key"
            )
            .execute()
        )

        return {
            "saved": True,
            "key": key,
            "value": value
        }
