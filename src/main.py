from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from src.asr_service import ASRService
import numpy as np
import asyncio
import json
import os

# --- Configuration Loading ---
def get_config():
    # 1. Load defaults from config file
    try:
        with open("config.json") as f:
            config_from_file = json.load(f)
    except FileNotFoundError:
        config_from_file = {}

    # 2. Get config from environment variables
    model_size_env = os.environ.get('MODEL_SIZE')
    language_env = os.environ.get('LANGUAGE')
    vad_filter_env = os.environ.get('VAD_FILTER')

    # 3. Determine final config (Env > File > Hardcoded default)
    # The VAD filter env var is compared to the string 'true'
    final_config = {
        "model_size": model_size_env or config_from_file.get("model_size", "small"),
        "language": language_env or config_from_file.get("language", "en"),
        "vad_filter": vad_filter_env.lower() == 'true' if vad_filter_env is not None else config_from_file.get("vad_filter", True)
    }
    return final_config

config = get_config()

# --- FastAPI App ---
app = FastAPI()

# Initialize ASR Service with configured model size
print(f"Initializing ASR service with model: {config['model_size']}")
print(f"VAD filter enabled: {config['vad_filter']}")
asr_service = ASRService(model_size=config['model_size'], device="cpu", compute_type="int8")

# --- Audio Processing Configuration ---
AUDIO_SAMPLE_RATE = 16000
ACCUMULATE_DURATION = 3 # seconds of audio to accumulate

@app.websocket("/ws/asr")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connected.")

    accumulated_audio_data = [] # To store np.int16 audio chunks
    accumulated_samples = 0

    try:
        while True:
            data = await websocket.receive_bytes()
            audio_chunk = np.frombuffer(data, dtype=np.int16)
            accumulated_audio_data.append(audio_chunk)
            accumulated_samples += len(audio_chunk)

            if accumulated_samples >= AUDIO_SAMPLE_RATE * ACCUMULATE_DURATION:
                full_audio_segment_int16 = np.concatenate(accumulated_audio_data)
                full_audio_segment_float32 = full_audio_segment_int16.astype(np.float32) / 32768.0 
                
                # Transcribe using the configured language and VAD setting
                transcription = asr_service.transcribe_audio(
                    full_audio_segment_float32, 
                    language=config['language'],
                    vad_filter=config['vad_filter']
                )
                
                if transcription:
                    print(f"Transcription ({config['language']}): {transcription}")
                    await websocket.send_text(transcription)
                
                accumulated_audio_data = []
                accumulated_samples = 0

    except WebSocketDisconnect:
        print("WebSocket disconnected.")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        print("WebSocket connection closed.")


