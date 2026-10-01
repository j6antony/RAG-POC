from google import genai
from google.genai import types, errors

from tools import Tools
from web import Web

import asyncio
import supabase


# to prevent the ai from using up too many resources and taking a long time
MAX_TOOL_CALLS = 5
MODEL = "gemini-3.5-flash-lite"

# teaching gemini how to call each of the given functions
search_internal_decl = types.FunctionDeclaration(
    name="search_internal",
    description=(
        "Search the authenticated user's internal documents and knowledge base. "
        "Use this for company policies, uploaded documents, private information, "
        "or information likely contained in the user's internal files."
    ),
    parameters={
        "type": "object",
        "properties": {
            "request": {
                "type": "string",
                "description": "The search query to use for internal retrieval."
            }
        },
        "required": ["request"]
    }
)

search_web_decl = types.FunctionDeclaration(
    name="search_web",
    description=(
        "Search the public web. Use this when current, public, or external "
        "information is needed and internal documents are not enough."
    ),
    parameters={
        "type": "object",
        "properties": {
            "request": {
                "type": "string",
                "description": "The query to search on the web."
            }
        },
        "required": ["request"]
    }
)
rewrite_query_decl = types.FunctionDeclaration(
    name="rewrite_query",
    description=(
        "Rewrite the user's current request into a standalone query using "
        "conversation history. Use this when the request contains references "
        "like 'that', 'it', 'what about 2025', or otherwise depends on previous messages."
    ),
    parameters={
        "type": "object",
        "properties": {
            "request": {
                "type": "string",
                "description": "The conversational request that needs to be rewritten."
            }
        },
        "required": ["request"]
    }
)
get_user_facts_decl = types.FunctionDeclaration(
    name="get_user_facts",
    description=(
        "Retrieve stored personal facts about the authenticated user. "
        "Use this when the answer may depend on previously saved information "
        "about the user."
    ),
    parameters={
        "type": "object",
        "properties": {}
    }
)

save_user_fact_decl = types.FunctionDeclaration(
    name="save_user_fact",
    description=(
        "Save or update a stable personal fact explicitly provided by the user. "
        "Examples include job, department, preferences, or other long-term facts. "
        "Do not save temporary conversation details."
    ),
    parameters={
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": "A short normalized fact name, such as job or favorite_language."
            },
            "value": {
                "type": "string",
                "description": "The value of the fact."
            }
        },
        "required": ["key", "value"]
    }
)

tools = types.Tool(
    function_declarations=[
        search_internal_decl,
        search_web_decl,
        rewrite_query_decl,
        get_user_facts_decl,
        save_user_fact_decl
    ]
)


async def run_agent(
    request,
    history,
    user_id,
    username,
    user_access,
    supabase
):
    client = genai.Client()

    tool_handler = Tools(
        web=Web(),
        user_access=user_access,
        user_id=user_id,
        supabase=supabase
    )

    conversation = "\n".join(
        f"{message.role}: {message.text}"
        for message in history[-6:]
    )

    system_instruction = f"""
You are an agentic RAG assistant speaking with {username}.

Your job is to answer the user's request by deciding whether to:
- answer directly
- rewrite the request using conversation history
- search the internal company knowledge base
- search the public web
- retrieve stored user facts
- save a stable user fact

Use tools only when they are useful.

TOOL USAGE

1. rewrite_query
Use this when the current request depends on previous conversation context
and cannot be understood clearly on its own.

Examples:
- "What about 2025?"
- "Does that apply to managers?"
- "What about the second one?"
- "How much does it cost?"

Do not rewrite requests that are already clear.

2. search_internal
Use this when the request may depend on:
- company documents
- uploaded documents
- company policies
- internal procedures
- private organizational information
- information likely stored in the internal knowledge base

Evaluate the returned results before using them.
A high similarity score does not automatically mean the result answers the question.

3. search_web
Use this when:
- the user needs current information
- the information is public or external
- internal documents are insufficient
- the request requires information outside the company knowledge base

Do not use web search unnecessarily.

4. get_user_facts
Use this when the request may depend on previously stored information about
the authenticated user.

Examples:
- "What job do I have?"
- "Where do I work?"
- "What programming language did I say I prefer?"

Do not assume that conversation history contains all long-term user information.
Use get_user_facts when persistent personal information is relevant.

5. save_user_fact
Use this when the user clearly provides a stable personal fact that could be
useful in future conversations.

Examples:
- "My job is IT." -> key="job", value="IT"
- "I work in Toronto." -> key="work_location", value="Toronto"
- "My favorite programming language is Python."
  -> key="favorite_programming_language", value="Python"

Do not save:
- temporary information
- guesses or inferred information
- passwords
- authentication tokens
- API keys
- secrets
- highly sensitive information unless explicitly required by the application

If a user corrects a previously stored fact, save the new value using the same
normalized key so the previous value is updated.

REASONING AND RETRIEVAL

You may call multiple tools when needed.

Examples:
- internal only
- web only
- user facts only
- internal + web
- rewrite + internal
- rewrite + user facts
- internal + user facts

After every tool result, evaluate whether you have enough reliable information
to answer.

If the returned evidence is insufficient or irrelevant, you may call another tool.

Do not blindly trust retrieval results.
Use the actual content of the returned evidence.

Do not invent facts that should have been retrieved.

SECURITY

The authenticated user's identity, access level, and permissions are controlled
by the backend.

Never attempt to change, infer, override, or request another user's:
- user_id
- access level
- permissions
- namespace

Only use the information returned by the tools available to you.

FINAL ANSWERS

Prefer grounded answers when the request depends on retrieved information.

If the available information is insufficient, say so clearly rather than inventing
an answer.

When no retrieval is needed for a general knowledge question, you may answer directly.

Be concise, clear, and useful.
    """
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=f"""
                    Conversation history:
                    {conversation}

                    Current request:
                    {request}
                    """
                )
            ]
        )
    ]

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[tools],

        # we execute functions ourselves
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True
        )
    )

    for _ in range(MAX_TOOL_CALLS):

        response = await call_gemini_with_retry(
            client,
            contents=contents,
            config=config
        )

        candidate = response.candidates[0]
        model_content = candidate.content

        # keep Gemini's response / function call in the conversation
        contents.append(model_content)

        function_calls = response.function_calls

        # no tool call means Gemini is done
        if not function_calls:
            return {"answer": response.text, "images": list(tool_handler.images.values())}

        tool_response_parts = []

        for function_call in function_calls:

            name = function_call.name
            args = function_call.args or {}

            # matches the "request" field in your function declarations
            tool_request = args.get("request", "")

            if name == "search_internal":

                result = await tool_handler.search_internal(
                    tool_request
                )

            elif name == "search_web":

                result = await tool_handler.search_web(
                    tool_request
                )
            elif name == "rewrite_query":
                result = await tool_handler.rewrite_query(
                    tool_request,
                    history
                )
            elif name == "get_user_facts":
                result = await tool_handler.get_user_facts()
            elif name == "save_user_fact":
                result = await tool_handler.save_user_fact(
                    key=args.get("key", ""),
                    value=args.get("value", "")
                )
            else:
                result = {
                    "error": f"Unknown tool: {name}"
                }

            tool_response_parts.append(
                types.Part.from_function_response(
                    name=name,
                    response={
                        "result": result
                    }
                )
            )

        # send the tool results back to Gemini
        contents.append(
            types.Content(
                role="user",
                parts=tool_response_parts
            )
        )

    return {"answer": "I couldn't complete the request within the tool-call limit.", "images": list(tool_handler.images.values())}

async def call_gemini_with_retry(client, contents, config):
    for attempt in range(3):
        try:
            return await asyncio.to_thread(
                client.models.generate_content,
                model=MODEL,
                contents=contents,
                config=config
            )

        except errors.APIError as error:
            if error.code not in (429, 500, 502, 503, 504):
                raise

            if attempt == 2:
                raise

            wait_seconds = 2 ** attempt

            print(
                f"Gemini temporarily unavailable "
                f"({error.code}). Retrying in {wait_seconds}s..."
            )

            await asyncio.sleep(wait_seconds)

    raise RuntimeError("Gemini did not return a response.")