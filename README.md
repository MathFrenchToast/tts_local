# Real-Time Local Speech-to-Text Server

This project provides a real-time, local speech-to-text (ASR) service using a client-server architecture. It captures audio from a microphone, streams it to a server, and returns transcriptions in near real-time.

## Architecture

The application is built on a client-server model, allowing for flexible integration with various types of clients in the future.

*   **Server (`src/main.py`):** A WebSocket server built with **FastAPI**. It accepts audio streams from clients, processes the audio, and sends back transcribed text.
*   **Client (`src/client.py`):** A command-line interface (CLI) client that captures audio from the microphone using **PyAudio** and streams it to the server over a WebSocket connection.
*   **ASR Service (`src/asr_service.py`):** A core service class that wraps the **`faster-whisper`** model. It is responsible for loading the transcription model and performing the actual speech-to-text conversion.
*   **Audio Recorder (`src/audio_recorder.py`):** A utility class that handles the details of capturing audio from the system's microphone in real-time.

The server continuously listens for audio chunks from the client. It accumulates a few seconds of audio before sending it to the ASR service for transcription. This segment-based approach provides a good balance between latency and transcription accuracy.

## Architecture Decision Record (ADR)

1.  **ASR Engine - `faster-whisper`**: We chose `faster-whisper` as the core ASR engine. It is an optimized implementation of OpenAI's Whisper model, offering significant speed improvements and reduced memory usage, which are critical for achieving real-time performance on local hardware.

2.  **Server Framework - `FastAPI`**: `FastAPI` was selected for the server implementation due to its high performance, asynchronous capabilities, and native support for WebSockets. This makes it an ideal choice for handling real-time, bidirectional communication with clients.

3.  **Server Configuration - Environment Variables**: The server's configuration (e.g., `MODEL_SIZE`, `LANGUAGE`) is managed through environment variables. This approach was chosen over command-line arguments because process managers like `uvicorn` do not pass unknown arguments to the application. Environment variables are a standard, robust, and container-friendly method for configuring applications.

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
    ```

2.  **Install System Dependencies:**
    This project requires `portaudio` for microphone access. On Debian-based systems (like Ubuntu), you can install it with:
    ```bash
    sudo apt-get update && sudo apt-get install -y portaudio19-dev
    ```

3.  **Create and Activate Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

4.  **Install Python Packages:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

You need to run the server first, and then run the client in a separate terminal.

### 1. Running the Server

The server can be configured via a `config.json` file and overridden by environment variables.

**To run the server with default settings (`small` model, `en` language, VAD enabled):**
```bash
venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000
```

**To specify the language, model size, and VAD setting, use environment variables:**
This example starts the server with the `medium` model for French and disables the VAD filter.
```bash
MODEL_SIZE="medium" LANGUAGE="fr" VAD_FILTER="false" venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000
```
The server will load the model and wait for client connections.

### 2. Running the Client

Open a **new terminal** in the same project directory.

**To start the client and stream your microphone input:**
```bash
venv/bin/python -m src.client
```

The client will connect to the server. Start speaking, and you will see the transcribed text appear in your terminal. Press `Ctrl+C` to stop the client.
