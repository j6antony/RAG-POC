import asyncio

from google import genai
from google.genai import errors, types

from analysis_agent import AnalysisAgent
from tools import Tools
from web import Web


# Prevent the AI from using too many resources or looping for too long.
MAX_TOOL_CALLS = 5
MODEL = "gemini-3.5-flash-lite"

analysis_agent = AnalysisAgent()

AGENTS = {
    "analysis": {
        "description": (
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
        lines.append(f"- {name}: {config['description']}")

    return "\n".join(lines)


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
                "description": "The search query to use for internal retrieval.",
            }
        },
        "required": ["request"],
    },
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
                "description": "The query to search on the web.",
            }
        },
        "required": ["request"],
    },
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
                "description": "The conversational request that needs to be rewritten.",
            }
        },
        "required": ["request"],
    },
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
        "properties": {},
    },
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
                "description": "A short normalized fact name, such as job or favorite_language.",
            },
            "value": {
                "type": "string",
                "description": "The value of the fact.",
            },
        },
        "required": ["key", "value"],
    },
)

delegate_to_agent_decl = types.FunctionDeclaration(
    name="delegate_to_agent",
    description=(
        "Delegate a multi-step task to another available agent. "
        "Use this when an available agent is better suited to independently analyze "
        "or process information than a single tool call."
    ),
    parameters={
        "type": "object",
        "properties": {
            "agent_name": {
                "type": "string",
                "enum": list(AGENTS.keys()),
                "description": "The registered agent to delegate the task to.",
            },
            "request": {
                "type": "string",
                "description": "A clear, self-contained task for the selected agent.",
            },
            "context": {
                "type": "string",
                "description": (
                    "Relevant information the agent should use, such as results from "
                    "internal or web searches. Only include context needed for the task."
                ),
            },
        },
        "required": ["agent_name", "request"],
    },
)

tools = types.Tool(
    function_declarations=[
        search_internal_decl,
        search_web_decl,
        rewrite_query_decl,
        get_user_facts_decl,
        save_user_fact_decl,
        delegate_to_agent_decl,
    ]
)


async def delegate_to_agent(
    agent_name: str,
    request: str,
    user_id: str,
    user_access: int,
    context: str = "",
):
    print(
        f"[A2A] Delegating to agent='{agent_name}' "
        f"access={user_access} context_chars={len(context)}"
    )

    if agent_name not in AGENTS:
        print(f"[A2A] Unknown agent requested: {agent_name}")
        raise ValueError(f"Unknown agent provided: {agent_name}")

    agent = AGENTS[agent_name]["agent"]

    result = await agent.run(
        request=request,
        user_id=user_id,
        user_access=user_access,
        context=context,
    )

    print(f"[A2A] Agent '{agent_name}' completed successfully")
    return result


async def run_agent(
    request,
    history,
    user_id,
    username,
    user_access,
    supabase,
):
    client = genai.Client()

    tool_handler = Tools(
        web=Web(),
        user_access=user_access,
        user_id=user_id,
        supabase=supabase,
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
        - use context to pass prior tool results when the delegated task depends on them
        - do not delegate trivial actions
        - do not create circular delegation

        ACCESS CONTROL

        All operations must respect the initiating user's user_id and access level.

        Delegating to another agent must never increase the user's permissions.

        The delegated agent inherits the initiating user's identity and access level.

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
            ],
        )
    ]

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[tools],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True
        ),
    )

    print(
        f"[COORDINATOR] Starting request with access={user_access}; "
        f"available_agents={list(AGENTS.keys())}"
    )

    for tool_round in range(1, MAX_TOOL_CALLS + 1):
        response = await call_gemini_with_retry(
            client,
            contents=contents,
            config=config,
        )

        candidate = response.candidates[0]
        model_content = candidate.content
        contents.append(model_content)

        function_calls = response.function_calls

        if not function_calls:
            print(f"[COORDINATOR] Final response produced on round {tool_round}")
            return {
                "answer": response.text,
                "images": list(tool_handler.images.values()),
            }

        tool_response_parts = []

        for function_call in function_calls:
            name = function_call.name
            args = function_call.args or {}
            tool_request = args.get("request", "")

            print(f"[COORDINATOR] Tool selected: {name} (round {tool_round})")

            try:
                if name == "search_internal":
                    result = await tool_handler.search_internal(tool_request)

                elif name == "search_web":
                    result = await tool_handler.search_web(tool_request)

                elif name == "rewrite_query":
                    result = await tool_handler.rewrite_query(
                        tool_request,
                        history,
                    )

                elif name == "get_user_facts":
                    result = await tool_handler.get_user_facts()

                elif name == "save_user_fact":
                    result = await tool_handler.save_user_fact(
                        key=args.get("key", ""),
                        value=args.get("value", ""),
                    )

                elif name == "delegate_to_agent":
                    print(
                        f"[COORDINATOR] Delegation requested: "
                        f"agent={args.get('agent_name', '')} "
                        f"context_chars={len(args.get('context', ''))}"
                    )
                    result = await delegate_to_agent(
                        agent_name=args.get("agent_name", ""),
                        request=tool_request,
                        context=args.get("context", ""),
                        user_id=user_id,
                        user_access=user_access,
                    )

                else:
                    result = {
                        "error": f"Unknown tool: {name}"
                    }

            except Exception as exc:
                print(f"[COORDINATOR] {name} failed: {exc}")
                result = {
                    "error": f"{name} failed: {exc}"
                }

            tool_response_parts.append(
                types.Part.from_function_response(
                    name=name,
                    response={
                        "result": result
                    },
                )
            )

        contents.append(
            types.Content(
                role="user",
                parts=tool_response_parts,
            )
        )

    print("[COORDINATOR] Tool-call limit reached")
    return {
        "answer": "I couldn't complete the request within the tool-call limit.",
        "images": list(tool_handler.images.values()),
    }


async def call_gemini_with_retry(client, contents, config):
    for attempt in range(3):
        try:
            return await asyncio.to_thread(
                client.models.generate_content,
                model=MODEL,
                contents=contents,
                config=config,
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


async def delegate_to_agent(
    target_conversation_id,
    request,
    context,
    source_conversation_id,
    user_id,
    user_access,
    supabase,
):
    task = (
        supabase
        .table("agent_tasks")
        .insert({
            "source_conversation_id": source_conversation_id,
            "target_conversation_id": target_conversation_id,
            "user_id": user_id,
            "task": request,
            "context": context,
            "status": "pending",
        })
        .execute()
    )

    task_id =  task.data[0]

    result = await run_agent(
        request=request,
        history=[],
        user_id=user_id,
        username="",
        user_access=user_access,
        supabase=supabase,
    )

    supabase.table("agent_tasks").update({
        "status": "completed",
        "result": result["answer"],
    }).eq(
        "id",
        task_id
    ).execute()

    return result["answer"]


async def get_pending_tasks(
    conversation_id,
    user_id,
    supabase,
):
    response = (
        supabase
        .table("agent_tasks")
        .select("*")
        .eq("target_conversation_id", str(conversation_id))
        .eq("user_id", user_id)
        .eq("status", "pending")
        .execute()
    )

    return response.data

async def process_pending_tasks(
    conversation_id,
    user_id,
    user_access,
    supabase,
):
    tasks = await get_pending_tasks(
        conversation_id,
        user_id,
        supabase,
    )

    for task in tasks:

        supabase.table("agent_tasks").update({
            "status": "running"
        }).eq(
            "id",
            task["id"]
        ).execute()

        try:
            result = await run_agent(
                request=task["task"],
                history=[],
                user_id=user_id,
                username="",
                user_access=user_access,
                supabase=supabase,
            )

            supabase.table("agent_tasks").update({
                "status": "completed",
                "result": result["answer"],
            }).eq(
                "id",
                task["id"]
            ).execute()

        except Exception as exc:
            supabase.table("agent_tasks").update({
                "status": "failed",
                "result": str(exc),
            }).eq(
                "id",
                task["id"]
            ).execute()