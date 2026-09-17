"""
- for the preliminary step to ensure all processes are currently working we are going to simply contruct the promp with sections
    context, request, prompt(this tells llm to use context to respond to request)
- afterwards connect to llm and add the info to context window of llm before sending the llm the given request
- for the POC lets go with simply taking the first 3 in the list
- note that the gamini api call thing has a bug which is why it throws that warning in the terminal it can be ignored
- small error that I was running into with the LLM was that it would take to long or the LLM had to many requests so I like made it try 3 times with wait time in between before throwing an error
"""

from retrieval import Retrieval
from embedding import Embed
from google import genai
from google.genai import errors
from google.genai import types
import os
import time

def answer_request(request):
    api_key = os.environ["GEMINI_API_KEY"]
    folder = "/Users/johanantony/Desktop/Rag POC/RAG-POC/Raw Data"
    context = "Context \n "
    embedder = Embed(folder)
    retrieval = Retrieval(
        embedder.embed_request(request),
        embedder.embed_data()
        )
    context_list = retrieval.score_list(5)
    context = "\n\n".join(
        chunk["text"]
        for score, chunk in context_list
    )

    """
    print("Retrieved chunks:")
    for score, chunk in context_list:
        source = chunk["metadata"].get("source", "unknown")
        print(f"- {score:.4f} {source}")
    """

    context_window = f"""
    Use the following context to answer the question.

    Context:
    {context}

    Question:
    {request}
    """

    client = genai.Client()

    config = types.GenerateContentConfig(
        # the system instructions are currently built in here but i believe that it should be built better elswhere
        system_instruction="""
        You are a documentation assistant.
        Answer using only the provided context.
        If the context does not contain the answer,
        say that you do not have enough information.
        """
    )

    response = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=context_window,
                config=config
            )
            break
        except errors.APIError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise

            wait_seconds = 2 ** attempt
            print(f"Gemini is temporarily unavailable ({error.code}). Retrying in {wait_seconds}s...")
            time.sleep(wait_seconds)

    if response is None:
        raise RuntimeError("Gemini did not return a response.")

    return response.text
