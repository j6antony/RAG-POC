import asyncio

from google import genai
from google.genai import types


class AnalysisAgent:
    def __init__(self):
        self.client = genai.Client()
        self.model = "gemini-3.5-flash-lite"

    async def run(
        self,
        request: str,
        user_id: str,
        user_access: int,
        context: str = "",
    ):
        print(
            f"[ANALYSIS AGENT] Starting task access={user_access} "
            f"request_chars={len(request)} context_chars={len(context)}"
        )

        prompt = f"""
        Task:
        {request}

        Additional context:
        {context or "No additional context was provided."}

        Analyze the task carefully and return a useful result.
        """

        config = types.GenerateContentConfig(
            system_instruction="""
            You are an analysis agent.

            Your job is to perform focused analysis on information provided
            by the coordinator.

            You may:
            - compare information
            - identify patterns
            - summarize findings
            - identify contradictions
            - draw conclusions supported by the provided information
            - organize complex information into a useful result

            You do not have permission to retrieve additional information
            unless tools are explicitly provided to you.

            Do not invent missing facts.

            If the provided information is insufficient, clearly say what
            information is missing.

            Return only the result of the analysis. Do not discuss internal
            orchestration or the fact that another agent delegated the task.
            """
        )

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=config,
            )
        except Exception as exc:
            print(f"[ANALYSIS AGENT] Failed: {exc}")
            raise

        result = response.text or ""
        print(f"[ANALYSIS AGENT] Completed result_chars={len(result)}")
        return result
