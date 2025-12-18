import httpx
import os
import json
from app.repositories.settings_repository import settings_repository

class LLMService:
    def __init__(self):
        pass

    @property
    def base_url(self):
        url = settings_repository.get("ollama_url", os.getenv("OLLAMA_URL", "http://localhost:11434"))
        # Ensure base_url ends with /v1 for OpenAI compatibility
        if not url.endswith("/v1") and not url.endswith("/v1/"):
            url = url.rstrip("/") + "/v1"
        return url

    @property
    def model(self):
        return settings_repository.get("llm_model", "llama3")

    @property
    def api_key(self):
        return settings_repository.get("ollama_api_key", os.getenv("OLLAMA_API_KEY", ""))

    def _get_headers(self, api_key=None):
        headers = {"Content-Type": "application/json"}
        key = api_key or self.api_key
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

    async def get_available_models(self, url=None, api_key=None):
        """
        Fetches available models from an OpenAI-compatible API.
        Returns a dict with 'models' (list) and 'error' (str or None).
        """
        target_url = url or self.base_url
        if not target_url.endswith("/v1") and not target_url.endswith("/v1/"):
            target_url = target_url.rstrip("/") + "/v1"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{target_url}/models", 
                    headers=self._get_headers(api_key=api_key),
                    timeout=5.0
                )
                response.raise_for_status()
                data = response.json()
                # OpenAI format: {"data": [{"id": "model-id", ...}, ...]}
                models = [m["id"] for m in data.get("data", [])]
                # If it's Ollama's native response by mistake, handle it
                if not models and "models" in data:
                    models = [m["name"] for m in data.get("models", [])]
                
                return {"models": models, "error": None}
            except httpx.ConnectError:
                return {"models": [], "error": f"Could not connect to LLM server at {target_url}. Is it running?"}
            except Exception as e:
                return {"models": [], "error": f"Error fetching models: {str(e)}"}

    async def summarize_and_tag(self, text: str):
        """
        Sends the transcript to an OpenAI-compatible API to get analysis.
        """
        system_prompt = "You are a helpful assistant that analyzes voice note transcripts. You MUST respond ONLY with a valid JSON object."
        user_prompt = f"""
        Analyze the following voice note transcript: "{text}"
        
        1. **Title**: Provide a short, descriptive title (max 5 words).
        2. **Type**: Classify into ONE type: [Task, Idea, Journal, Meeting, Quick Thought].
        3. **Tags**: List 3-5 relevant keywords/tags.
        4. **Metadata**: Extract key entities (people, dates, project names, locations).
        
        Respond ONLY with a JSON object in this format:
        {{
            "title": "Short Title",
            "note_type": "One of the types above",
            "tags": ["tag1", "tag2", "tag3"],
            "metadata": {{
                "people": [],
                "dates": [],
                "projects": [],
                "locations": []
            }}
        }}
        """
        
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "stream": False,
                    "response_format": {"type": "json_object"}
                }
                
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                result = response.json()
                
                # OpenAI format: choices[0].message.content
                choice = result.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "{}")
                
                # Some models return JSON as a string inside the content, or just the JSON
                # Handle cases where the model might wrap the JSON in code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                return json.loads(content)
            except Exception as e:
                print(f"Error calling LLM: {e}")
                return {
                    "title": "New Note",
                    "note_type": "Quick Thought",
                    "tags": [],
                    "metadata": {}
                }

# Global instance
llm_service = LLMService()
