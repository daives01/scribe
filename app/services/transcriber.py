import os
import nemo.collections.asr as nemo_asr
import torch
import subprocess
import tempfile
import shutil

class Transcriber:
    def __init__(self, model_name="nvidia/parakeet-tdt-0.6b-v2", device=None):
        """
        Initialize the NeMo Parakeet model.
        """
        if device is None:
            if torch.cuda.is_available():
                device = "cuda"
            elif torch.backends.mps.is_available():
                # NeMo ASR models often hit float64/double issues on MPS
                # For inference, CPU is highly optimized on Apple Silicon and more stable
                device = "cpu"
            else:
                device = "cpu"
        
        print(f"Loading NeMo ASR model: {model_name} on {device}...")
        self.model = nemo_asr.models.ASRModel.from_pretrained(model_name=model_name)
        self.model = self.model.to(device)
        self.model.eval()
        
        # Check for ffmpeg for audio conversion
        self.ffmpeg_path = shutil.which("ffmpeg")
        if not self.ffmpeg_path:
            # Check common Homebrew path on Apple Silicon
            if os.path.exists("/opt/homebrew/bin/ffmpeg"):
                self.ffmpeg_path = "/opt/homebrew/bin/ffmpeg"
        
        if not self.ffmpeg_path:
            print("Warning: ffmpeg not found. Non-wav audio files might fail to transcribe.")

    def transcribe(self, audio_path: str):
        """
        Transcribes the audio file at the given path using Parakeet v2.
        Returns a dictionary with full text.
        """
        # If the file is not a wav file and we have ffmpeg, convert it
        temp_wav = None
        is_wav = audio_path.lower().endswith(".wav")
        
        if not is_wav and self.ffmpeg_path:
            try:
                fd, temp_wav = tempfile.mkstemp(suffix=".wav")
                os.close(fd)
                
                print(f"Converting {audio_path} to wav for transcription...")
                # Convert to 16kHz mono wav as expected by most ASR models
                cmd = [
                    self.ffmpeg_path, "-y", "-i", audio_path,
                    "-ar", "16000", "-ac", "1", temp_wav
                ]
                subprocess.run(cmd, check=True, capture_output=True)
                audio_to_transcribe = temp_wav
            except Exception as e:
                print(f"Error converting audio to wav: {e}")
                audio_to_transcribe = audio_path
        else:
            audio_to_transcribe = audio_path

        try:
            # NeMo transcribe expects a list of paths
            with torch.no_grad():
                transcriptions = self.model.transcribe([audio_to_transcribe], verbose=False)
            
            # The result depends on the model type, but for Parakeet-TDT it's usually a list of strings
            if not transcriptions:
                return {
                    "text": "",
                    "segments": [],
                    "language": "en",
                    "duration": 0
                }
                
            full_text = transcriptions[0]
            
            # NeMo Parakeet-TDT can return Hypothesis objects instead of plain strings
            if hasattr(full_text, 'text'):
                full_text = full_text.text
                
            # Handle case where it might be a list of lists or other structures
            if isinstance(full_text, list):
                full_text = " ".join([str(t) for t in full_text])
                    
            return {
                "text": str(full_text).strip(),
                "segments": [], 
                "language": "en",
                "duration": 0
            }
        except Exception as e:
            print(f"Transcription error: {e}")
            return {
                "text": "",
                "segments": [],
                "language": "en",
                "duration": 0
            }
        finally:
            # Cleanup temp wav if created
            if temp_wav and os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except:
                    pass

# Global instance for easy access
# We'll use the default CPU/CUDA detection
transcriber = Transcriber()
