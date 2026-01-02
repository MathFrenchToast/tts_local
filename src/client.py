import asyncio
import websockets
import json
import numpy as np
from src.audio_recorder import AudioRecorder

async def send_audio_and_receive_transcriptions(uri):
    async with websockets.connect(uri) as websocket:
        print(f"Connected to WebSocket server at {uri}")

        recorder = AudioRecorder(
            rate=16000,
            chunk_size=1024, # Must match server's expected chunking if any, or be consistent.
                             # For our current server, it accumulates based on seconds, not chunk_size.
            channels=1
        )
        recorder.start_recording()

        try:
            # Task to send audio
            async def send_audio():
                print("Sending audio... (Press Ctrl+C to stop)")
                for audio_chunk_int16 in recorder.get_audio_chunk():
                    # Send raw bytes of the int16 numpy array
                    await websocket.send(audio_chunk_int16.tobytes())
                    await asyncio.sleep(0.01) # Small delay to prevent overwhelming the network/CPU

            # Task to receive transcriptions
            async def receive_transcriptions():
                while True:
                    transcription = await websocket.recv()
                    print(f"\rTranscription: {transcription.strip()}", end="") # \r to overwrite line

            # Run both tasks concurrently
            await asyncio.gather(send_audio(), receive_transcriptions())

        except websockets.exceptions.ConnectionClosedOK:
            print("\nWebSocket connection closed normally.")
        except asyncio.CancelledError:
            print("\nClient stopped.")
        except Exception as e:
            print(f"\nClient error: {e}")
        finally:
            recorder.stop_recording()
            print("Audio recording stopped.")

if __name__ == "__main__":
    websocket_uri = "ws://127.0.0.1:8000/ws/asr" # Assuming server is running locally
    try:
        asyncio.run(send_audio_and_receive_transcriptions(websocket_uri))
    except KeyboardInterrupt:
        print("\nExiting client.")
