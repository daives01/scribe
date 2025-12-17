import os
from faster_whisper import WhisperModel

class Transcriber:
    def __init__(self, model_size="base", device="cpu", compute_type="int8"):
        """
        Initialize the Whisper model.
        Model sizes: 'tiny', 'base', 'small', 'medium', 'large'
        """
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe(self, audio_path: str):
        """
        Transcribes the audio file at the given path.
        Returns a dictionary with segments and full text.
        """
        segments, info = self.model.transcribe(audio_path, beam_size=5)
        
        full_text = ""
        transcription_segments = []
        
        for segment in segments:
            full_text += segment.text + " "
            transcription_segments.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip()
            })
            
        return {
            "text": full_text.strip(),
            "segments": transcription_segments,
            "language": info.language,
            "duration": info.duration
        }

# Global instance for easy access
transcriber = Transcriber(model_size="base")
