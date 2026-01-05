import os
import sys
import glob

def fix_library_paths():
    """
    Manually add the nvidia library paths to LD_LIBRARY_PATH so ctranslate2 can find them.
    This is necessary because pip-installed nvidia packages don't automatically update 
    the system linker path.
    """
    try:
        import nvidia.cublas.lib
        import nvidia.cudnn.lib
        
        libs_paths = [
            list(nvidia.cublas.lib.__path__)[0],
            list(nvidia.cudnn.lib.__path__)[0],
        ]
        
        current_ld_path = os.environ.get("LD_LIBRARY_PATH", "")
        new_paths = [p for p in libs_paths if p not in current_ld_path]
        
        if new_paths:
            print(f"Adding NVIDIA library paths to LD_LIBRARY_PATH: {new_paths}")
            os.environ["LD_LIBRARY_PATH"] = f"{':'.join(new_paths)}:{current_ld_path}"
            
            # Also re-exec the process with the new environment if we are just starting
            # This ensures dynamic linkers pick up the change for C++ extensions
            # However, for ctranslate2 loaded via Python, setting env var *might* be enough 
            # if done before the extension is loaded. Let's try just setting it first.
            
    except ImportError:
        print("NVIDIA libraries not found in python environment. proceeding without adding paths.")

fix_library_paths()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from src.asr_service import ASRService
import numpy as np
import asyncio
import json
import os
import torch
import collections
from enum import Enum

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
    vad_filter_env = os.environ.get('VAD_FILTER', 'true')
    device_env = os.environ.get('DEVICE')
    compute_type_gpu_env = os.environ.get('COMPUTE_TYPE_GPU')
    compute_type_cpu_env = os.environ.get('COMPUTE_TYPE_CPU')

    # 3. Determine final config (Env > File > Hardcoded default)
    config = {
        "model_size": model_size_env or config_from_file.get("model_size", "small"),
        "language": language_env or config_from_file.get("language", "en"),
        "vad_filter": vad_filter_env.lower() == 'true',
        "device": device_env or config_from_file.get("device", "auto"),
        "compute_type_gpu": compute_type_gpu_env or config_from_file.get("compute_type_gpu", "float16"),
        "compute_type_cpu": compute_type_cpu_env or config_from_file.get("compute_type_cpu", "int8"),
    }

    # 4. Auto-detect device if set to "auto"
    if config["device"] == "auto":
        config["device"] = "cuda" if torch.cuda.is_available() else "cpu"
    
    # 5. Select compute type based on final device
    config["compute_type"] = config["compute_type_gpu"] if config["device"] == "cuda" else config["compute_type_cpu"]
    
    return config

config = get_config()

# --- FastAPI App ---
app = FastAPI()

# Initialize ASR Service with configured model size
print(f"Initializing ASR service with model: {config['model_size']}")
print(f"Using device: {config['device']} ({config['compute_type']})")
print(f"Internal VAD filter enabled: {config['vad_filter']}")
asr_service = ASRService(
    model_size=config['model_size'], 
    device=config['device'], 
    compute_type=config['compute_type']
)

# --- Audio Processing Configuration ---
AUDIO_SAMPLE_RATE = 16000
# Max duration to accumulate audio in seconds before forcing a transcription
MAX_ACCUMULATE_DURATION = 10
# Duration of silence in seconds to trigger transcription
SILENCE_PAUSE_DURATION = 1.0
# RMS threshold for silence detection. This may need tuning.
SILENCE_THRESHOLD = 200
# Number of chunks for the history buffer (~0.5 seconds)
HISTORY_BUFFER_CHUNKS = 8

class VadState(Enum):
    IDLE = 1
    SPEAKING = 2
    COOLDOWN = 3

def is_silent(audio_chunk: np.ndarray) -> bool:
    """Check if an audio chunk is silent based on RMS energy."""
    rms = np.sqrt(np.mean(audio_chunk.astype(np.float32)**2))
    return rms < SILENCE_THRESHOLD

async def process_and_transcribe(websocket: WebSocket, audio_data: list):
    """Concatenate, convert, and transcribe a list of audio chunks."""
    if not audio_data:
        return

    full_audio_segment_int16 = np.concatenate(audio_data)
    full_audio_segment_float32 = full_audio_segment_int16.astype(np.float32) / 32768.0 
    
    # Transcribe using the configured language and VAD setting
    transcription = asr_service.transcribe_audio(
        full_audio_segment_float32, 
        language=config['language'],
        vad_filter=config['vad_filter']  # This should be false to rely on our VAD
    )
    
    if transcription:
        print(f"Transcription ({config['language']}): {transcription}")
        await websocket.send_text(transcription)

@app.websocket("/ws/asr")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connected.")

    main_buffer = []
    # History buffer to keep some audio before speech starts (pre-roll)
    history_buffer = collections.deque(maxlen=HISTORY_BUFFER_CHUNKS)
    state = VadState.IDLE
    silence_start_time = None
    loop = asyncio.get_running_loop()

    try:
        while True:
            data = await websocket.receive_bytes()
            audio_chunk = np.frombuffer(data, dtype=np.int16)
            history_buffer.append(audio_chunk)

            chunk_is_silent = is_silent(audio_chunk)

            if state == VadState.IDLE:
                if not chunk_is_silent:
                    # Speech detected, dump history buffer into main buffer
                    state = VadState.SPEAKING
                    main_buffer.extend(list(history_buffer))
                    history_buffer.clear()
            
            elif state == VadState.SPEAKING:
                main_buffer.append(audio_chunk)
                if chunk_is_silent:
                    # Speech has paused, enter cooldown
                    state = VadState.COOLDOWN
                    silence_start_time = loop.time()
                elif len(main_buffer) * (audio_chunk.shape[0] if audio_chunk.ndim > 0 else 1) >= AUDIO_SAMPLE_RATE * MAX_ACCUMULATE_DURATION:
                    # Force transcription if max duration is reached
                    await process_and_transcribe(websocket, main_buffer)
                    main_buffer = []
                    state = VadState.IDLE

            elif state == VadState.COOLDOWN:
                main_buffer.append(audio_chunk)
                if not chunk_is_silent:
                    # Speech resumed
                    state = VadState.SPEAKING
                    silence_start_time = None
                elif (loop.time() - silence_start_time) > SILENCE_PAUSE_DURATION:
                    # Silence pause is long enough, transcribe
                    await process_and_transcribe(websocket, main_buffer)
                    main_buffer = []
                    state = VadState.IDLE
            
    except WebSocketDisconnect:
        print("WebSocket disconnected.")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        print("WebSocket connection closed.")


