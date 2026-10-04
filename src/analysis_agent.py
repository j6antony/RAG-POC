from google import genai
from google.genai import types

class Analysis_agent:
    def __init__(self):
        self.client = genai.Client()
        self.model = "gemini-3.5-flash-lite"
    async def run(self, request, user_id, user_access, context):
        prompt = f"""
        Task:
        {request}

        Additional context:
        {context}

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

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )

        return response.text
    