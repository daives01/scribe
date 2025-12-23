"""Ollama service for LLM and embedding operations."""

from datetime import datetime
import json
import logging
from typing import TypedDict


import httpx
import numpy as np

from app.config import settings
from app.models.note import Note
from app.utils.vector import serialize_vector

logger = logging.getLogger(__name__)


class SummaryResult(TypedDict):
    """Result from generate_summary_and_tag."""

    summary: str
    tag: str | None
    notification_timestamp: datetime | None


class OllamaService:
    """Service for interacting with Ollama API."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        embedding_model: str | None = None,
        api_key: str | None = None,
    ):
        """
        Initialize the Ollama service.

        Args:
            base_url: Ollama API base URL
            model: LLM model to use for generation
            embedding_model: Model to use for embeddings
            api_key: Optional API key for authentication
        """
        self.base_url = (base_url or settings.default_ollama_url).rstrip("/")
        self.model = model or settings.default_ollama_model
        self.embedding_model = embedding_model or settings.embedding_model
        self.api_key = api_key

    def _get_headers(self) -> dict[str, str]:
        """Get request headers including auth if configured."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def check_connection(self) -> bool:
        """
        Check if Ollama is reachable.

        Returns:
            True if connected, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    headers=self._get_headers(),
                    timeout=5.0,
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama connection check failed: {e}")
            return False

    async def get_available_models(self) -> list[str]:
        """
        Get list of available models from Ollama.

        Returns:
            List of model names
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    headers=self._get_headers(),
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            logger.error(f"Failed to get Ollama models: {e}")
            return []

    async def generate_embedding(self, text: str) -> bytes:
        """
        Generate embedding for text using Ollama.

        Args:
            text: Text to embed

        Returns:
            Serialized embedding as bytes
        """
        async with httpx.AsyncClient() as client:
            try:
                # Try the newer /api/embed endpoint first
                response = await client.post(
                    f"{self.base_url}/api/embed",
                    headers=self._get_headers(),
                    json={"model": self.embedding_model, "input": text},
                    timeout=60.0,
                )

                # If /api/embed is not found (404), fallback to legacy /api/embeddings
                if response.status_code == 404 and "page not found" in response.text:
                    logger.info("Falling back to legacy /api/embeddings endpoint")
                    response = await client.post(
                        f"{self.base_url}/api/embeddings",
                        headers=self._get_headers(),
                        json={"model": self.embedding_model, "prompt": text},
                        timeout=60.0,
                    )

                if response.status_code == 404:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", "")
                        if "not found" in error_msg.lower():
                            raise ValueError(
                                f"Embedding model '{self.embedding_model}' not found in Ollama. "
                                f"Please run 'ollama pull {self.embedding_model}' or change the model in settings."
                            )
                    except (json.JSONDecodeError, ValueError) as e:
                        if isinstance(e, ValueError):
                            raise e
                        pass

                response.raise_for_status()
                data = response.json()
                logger.info(f"Ollama response received. Model: {self.embedding_model}")

                # Newer /api/embed returns "embeddings", legacy /api/embeddings returns "embedding"
                if "embeddings" in data:
                    embeddings = data.get("embeddings", [[]])
                    if embeddings and len(embeddings) > 0:
                        embedding = np.array(embeddings[0], dtype=np.float32)
                    else:
                        raise ValueError("No embedding returned from Ollama")
                else:
                    embedding_list = data.get("embedding", [])
                    if embedding_list:
                        embedding = np.array(embedding_list, dtype=np.float32)
                    else:
                        raise ValueError("No embedding returned from Ollama")

                logger.info(
                    f"Successfully generated embedding: {embedding.shape} {embedding.dtype}"
                )
                return serialize_vector(embedding)

            except httpx.HTTPStatusError as e:
                # Provide a more descriptive error if possible
                try:
                    error_json = e.response.json()
                    error_msg = error_json.get("error", str(e))
                except Exception:
                    error_msg = str(e)
                raise Exception(f"Ollama Error: {error_msg}") from e

    async def generate_summary_and_tag(
        self, transcript: str, available_tags: list[str]
    ) -> SummaryResult:
        """
        Generate a summary and tag for a transcript.

        Args:
            transcript: The voice note transcript
            available_tags: List of available tags to choose from

        Returns:
            Dict with "summary" and "tag" keys
        """
        tags_str = ", ".join(available_tags)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prompt = f"""Current system time: {current_time}

Analyze this transcript and determine:
1. Summary (max 5 words)
2. Tag: {tags_str}
3. When a notification should be sent (if this is time-based)

For timestamp: calculate the EXACT time when user should be notified. If transcript mentions "in X minutes/hours", add that to current time. If it mentions a specific time like "2 AM Saturday", use that time. If no specific notification time is mentioned, use null.

Respond with only JSON:
{{
  "summary": "brief summary (max 5 words)",
  "tag": "todo|note|misc",
  "timestamp_rationale": "explanation of timestamp calculation",
  "timestamp": "YYYY-MM-DDTHH:MM:SS or null"
}}

Transcript: {transcript}

JSON response:"""

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                headers=self._get_headers(),
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()

            # Parse the response
            response_text = data.get("response", "{}")
            try:
                result = json.loads(response_text)
                timestamp = result.get("timestamp")
                notification_time = None
                if timestamp and timestamp != "null":
                    try:
                        # Parse ISO format timestamp to datetime (local time)
                        notification_time = datetime.fromisoformat(timestamp)
                    except (ValueError, TypeError):
                        logger.warning(f"Failed to parse timestamp: {timestamp}")

                # Normalize tag to match available tags (case-insensitive)
                tag = result.get("tag", available_tags[0] if available_tags else None)
                if tag and available_tags:
                    tag_lower = tag.lower()
                    for available_tag in available_tags:
                        if available_tag.lower() == tag_lower:
                            tag = available_tag
                            break

                return {
                    "summary": result.get("summary", ""),
                    "tag": tag,
                    "notification_timestamp": notification_time,
                }
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM response: {response_text}")
                return {"summary": "", "tag": None, "notification_timestamp": None}

    async def answer_question(self, question: str, context_notes: list[Note]) -> str:
        """
        Answer a question using RAG with provided notes as context.

        Args:
            question: The user's question
            context_notes: List of relevant notes for context

        Returns:
            Generated answer string
        """
        # Build context from notes
        context_parts = []
        for i, note in enumerate(context_notes, 1):
            context_parts.append(
                f"Note {i} ({note.created_at.strftime('%Y-%m-%d')}):\n{note.raw_transcript}"
            )
        context = "\n\n---\n\n".join(context_parts)

        prompt = f"""You are a helpful assistant answering questions based on the user's personal voice notes.
Use the following notes as context to answer the question. If the answer cannot be found in the notes, say so.

Context Notes:
{context}

Question: {question}

Answer:"""

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                headers=self._get_headers(),
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()

    async def answer_question_stream(self, question: str, context_notes: list[Note]):
        """
        Answer a question using RAG with provided notes as context, streaming the response.
        """
        # Build context from notes
        context_parts = []
        for i, note in enumerate(context_notes, 1):
            created_str = (
                note.created_at.strftime("%Y-%m-%d")
                if hasattr(note.created_at, "strftime")
                else str(note.created_at)
            )
            context_parts.append(f"Note {i} ({created_str}):\n{note.raw_transcript}")
        context = "\n\n---\n\n".join(context_parts)

        prompt = f"""You are a helpful assistant answering questions based on the user's personal voice notes.
Use the following notes as context to answer the question. If the answer cannot be found in the notes, say so.

Context Notes:
{context}

Question: {question}

Answer:"""

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                headers=self._get_headers(),
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True,
                },
                timeout=120.0,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue


def get_ollama_service(
    base_url: str | None = None,
    model: str | None = None,
    embedding_model: str | None = None,
    api_key: str | None = None,
) -> OllamaService:
    """
    Factory function to create OllamaService with custom settings.

    Args:
        base_url: Optional custom Ollama URL
        model: Optional custom model
        embedding_model: Optional custom embedding model
        api_key: Optional API key

    Returns:
        Configured OllamaService instance
    """
    return OllamaService(
        base_url=base_url,
        model=model,
        embedding_model=embedding_model,
        api_key=api_key,
    )
