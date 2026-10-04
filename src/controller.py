from google import genai
from google.genai import types, errors

from tools import Tools
from web import Web
from analysis_agent import Analysis_agent

import asyncio
import supabase


# to prevent the ai from using up too many resources and taking a long time
MAX_TOOL_CALLS = 5
MODEL = "gemini-3.5-flash-lite"
analysis_agent = Analysis_agent()
AGENTS = {
    #"knowledge": {"description": "Searches internal company documents and RAG knowledge.", "agent": knowledge_agent},
   # "web": {"description": "Searches external web sources.", "agent": web_agent},
    "analysis": {"description": (
            "Analyzes provided information, compares results, identifies "
            "patterns or contradictions, and produces conclusions."
        ),
        "agent": analysis_agent,
        }
    }

def get_available_agents():
    if not AGENTS:
        return "No additional agents are currently available."
    lines = ["Available agents:"]

    for name, config in AGENTS.items():
        lines.append(
            f"-{name}: {config["dicription"]}"
        )
    return "\n".join(lines)


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

delegate_to_agent = types.FunctionDeclaration(
    name="delegate_to_agent",
    description="Delegate a multi-step task to another available agent.",
    parameters={
        "type": "object",
        "properties": {
            "agent_name": {
                "type": "string",
                "enum": list(AGENTS.keys()),
                "description": "The registered agent to delegate the task to."
            },
            "request": {
                "type": "string",
                "description": "A clear self-contained task for the agent."
            }
        },
        "required": ["agent_name", "request"]
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
    agent_context = get_available_agents()

    system_instruction = f"""
        You are the coordinator for an enterprise Retrieval-Augmented Generation system.

        Your job is to understand the user's request and decide whether to answer
        directly, use a tool, or delegate a task to another agent.

        TOOLS VS AGENTS

        Tools perform specific actions.

        Agents are independent workers capable of performing larger multi-step tasks.

        Do not delegate something to an agent when a normal tool can perform the
        operation directly.

        AGENT SELECTION

        You may ONLY use agents listed under Available Agents.

        Never invent an agent name, type, or capability.

        {agent_context}

        When delegating, select the agent whose description best matches the task.

        If no available agent is appropriate, do not delegate.

        DELEGATION

        When calling delegate_to_agent:
        - provide the exact registered agent name
        - provide a clear, self-contained task
        - include only relevant context
        - do not delegate trivial actions
        - do not create circular delegation

        ACCESS CONTROL

        All operations must respect the initiating user's user_id and access level.

        Delegating to another agent must never increase the user's permissions.

        You are responsible for combining tool and agent results into the final answer.
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

async def degelegate_to_agent(agent_name: str, request: str, user_id: str, user_access: int):
    if agent_name not in AGENTS:
        raise ValueError(f"Unknown agent provided: {agent_name}")
    agent_config = AGENTS[agent_name]

    agent = agent_config["agent"]
    return await agent.run(
        request,
        user_id,
        user_access
    )
