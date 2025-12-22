"""Ollama service for LLM and embedding operations."""

import json
import logging

import httpx
import numpy as np

from app.config import settings
from app.models.note import Note
from app.utils.vector import serialize_vector

logger = logging.getLogger(__name__)


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
            response = await client.post(
                f"{self.base_url}/api/embed",
                headers=self._get_headers(),
                json={"model": self.embedding_model, "input": text},
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

            # Ollama returns embeddings in "embeddings" array
            embeddings = data.get("embeddings", [[]])
            if embeddings and len(embeddings) > 0:
                embedding = np.array(embeddings[0], dtype=np.float32)
            else:
                raise ValueError("No embedding returned from Ollama")

            return serialize_vector(embedding)

    async def generate_summary_and_tag(
        self, transcript: str, available_tags: list[str]
    ) -> dict[str, str]:
        """
        Generate a summary and tag for a transcript.

        Args:
            transcript: The voice note transcript
            available_tags: List of available tags to choose from

        Returns:
            Dict with "summary" and "tag" keys
        """
        tags_str = ", ".join(available_tags)
        prompt = f"""Analyze this voice note transcript and provide:
1. A summary in 5 words or less
2. The most appropriate tag from this list: {tags_str}

Transcript:
{transcript}

Respond in this exact JSON format only, no other text:
{{"summary": "your 5 word summary", "tag": "chosen tag"}}"""

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
                return {
                    "summary": result.get("summary", ""),
                    "tag": result.get("tag", available_tags[0] if available_tags else None),
                }
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM response: {response_text}")
                return {"summary": "", "tag": None}

    async def answer_question(
        self, question: str, context_notes: list[Note]
    ) -> str:
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


def get_ollama_service(
    base_url: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> OllamaService:
    """
    Factory function to create OllamaService with custom settings.

    Args:
        base_url: Optional custom Ollama URL
        model: Optional custom model
        api_key: Optional API key

    Returns:
        Configured OllamaService instance
    """
    return OllamaService(base_url=base_url, model=model, api_key=api_key)
