"""
- for the preliminary step to ensure all processes are currently working we are going to simply contruct the promp with sections
    context, request, prompt(this tells llm to use context to respond to request)
- afterwards connect to llm and add the info to context window of llm before sending the llm the given request
- for the POC lets go with simply taking the first 3 in the list
- note that the gamini api call thing has a bug which is why it throws that warning in the terminal it can be ignored
- small error that I was running into with the LLM was that it would take to long or the LLM had to many requests so I like made it try 3 times with wait time in between before throwing an error
"""

from retrieval import Retrieval
from google import genai
from google.genai import errors
from google.genai import types
import time
from services import get_embedder, get_vectorDB


def rewrite_query(history, request):
    context = "\n".join(
        f"{message.role}: {message.text}"
        for message in history[-6:]
    )

    context_window = f"""
        Conversation history:
        {context}

        Current user question:
        {request}

        Rewrite the current question so it can be understood without the conversation history.
    """

    client = genai.Client()

    config = types.GenerateContentConfig(
        system_instruction="""
        You rewrite conversational user questions into standalone search queries.

        Use the conversation history only to resolve references and missing context.

        Do not answer the question.
        Do not invent information.
        Return only the rewritten standalone query.
        """
    )

    response = None

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=context_window,
                config=config
            )
            break

        except errors.APIError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise

            wait_seconds = 2 ** attempt
            print(
                f"Gemini is temporarily unavailable "
                f"({error.code}). Retrying in {wait_seconds}s..."
            )
            time.sleep(wait_seconds)

    if response is None:
        raise RuntimeError("Gemini did not return a response.")

    return response.text.strip()

def answer_request(request, history, user_id, username):
    request = rewrite_query(history, request)
    vectorDB = get_vectorDB()
    #track the last 6 requests

    embedder = get_embedder()
    request_vector = embedder.embed_request(request).tolist()
    retrieval = Retrieval(request_vector, user_id)
    context_list = retrieval.retrieve(vectorDB, 5, user_id, request_vector)
    context = "\n\n".join(
        match["metadata"]["text"]
        for match in context_list["matches"]
    )


    """
    print("Retrieved chunks:")
    for score, chunk in context_list:
        source = chunk["metadata"].get("source", "unknown")
        print(f"- {score:.4f} {source}")
    """

    context_window = f"""
    you are speaking with a user named {username}
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
                model="gemini-3.5-flash-lite",
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
