"""
- for the preliminary step to ensure all processes are currently working we are going to simply contruct the promp with sections
    context, request, prompt(this tells llm to use context to respond to request)
- afterwards connect to llm and add the info to context window of llm before sending the llm the given request
- for the POC lets go with simply taking the first 3 in the list
"""

from retrieval import Retrieval
from embedding import Embed
request = "How many vacation days do employees receive?"
folder = "/Users/johanantony/Desktop/Rag POC/RAG-POC/Raw Data"
context = "Context \n "
embedder = Embed(folder)
retrieval = Retrieval(
    embedder.embed_request(request),
    embedder.embed_data()
    )
context_list = retrieval.score_list(5)
for score, context in context_list:
    print(score)
    print(context["text"])
