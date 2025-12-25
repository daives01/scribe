"""Transcription service using MLX-Whisper."""

from pathlib import Path

import mlx_whisper

from app.config import settings


class TranscriptionService:
    """Service for audio transcription using MLX-Whisper."""

    def __init__(self, model: str | None = None):
        """
        Initialize transcription service.

        Args:
            model: Whisper model to use (default from settings)
        """
        self.model = model or settings.whisper_model
        self._model_path = f"mlx-community/whisper-{self.model}-mlx"

    def transcribe_file(self, file_path: str | Path) -> str:
        """
        Transcribe an audio file to text.

        Args:
            file_path: Path to the audio file

        Returns:
            Transcribed text
        """
        result = mlx_whisper.transcribe(
            str(file_path),
            path_or_hf_repo=self._model_path,
        )
        return result.get("text", "").strip()


# Singleton instance
transcription_service = TranscriptionService()
