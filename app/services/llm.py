import httpx
import os
import json

class LLMService:
    def __init__(self, base_url=None, model="llama3"):
        self.base_url = base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.model = model

    async def summarize_and_tag(self, text: str):
        """
        Sends the transcript to Ollama to get a summary and relevant tags.
        """
        prompt = f"""
        Analyze the following transcript. Provide a concise summary (2-3 sentences) 
        and a list of 3-5 relevant keywords/tags.
        
        Transcript: {text}
        
        Respond ONLY with a JSON object in this format:
        {{
            "summary": "your summary here",
            "tags": ["tag1", "tag2", "tag3"]
        }}
        """
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json"
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                result = response.json()
                content = result.get("response", "{}")
                return json.loads(content)
            except Exception as e:
                print(f"Error calling LLM: {e}")
                return {
                    "summary": "Summary unavailable.",
                    "tags": []
                }

# Global instance
llm_service = LLMService()
