"""Transcription service using MLX-Whisper."""

import tempfile
from pathlib import Path

import mlx_whisper

from app.config import settings


class TranscriptionService:
    """Service for audio transcription using MLX-Whisper."""

    def __init__(self, model: str | None = None):
        """
        Initialize the transcription service.

        Args:
            model: Whisper model to use (default from settings)
        """
        self.model = model or settings.whisper_model
        self._model_path = f"mlx-community/whisper-{self.model}-mlx"

    def transcribe_audio(self, audio_bytes: bytes, file_extension: str = ".m4a") -> str:
        """
        Transcribe audio bytes to text.

        Args:
            audio_bytes: Raw audio file bytes
            file_extension: File extension hint for the audio format

        Returns:
            Transcribed text
        """
        # Write to temp file (mlx-whisper requires file path)
        with tempfile.NamedTemporaryFile(
            suffix=file_extension, delete=False
        ) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name

        try:
            result = mlx_whisper.transcribe(
                tmp_path,
                path_or_hf_repo=self._model_path,
            )
            return result.get("text", "").strip()
        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)

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
