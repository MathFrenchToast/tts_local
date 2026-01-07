# Local Whisper Project To-Do List

This document tracks the remaining tasks and potential future improvements for the local ASR server project.

## High Priority

- [x] **Containerize the Application:** Create a `Dockerfile` to package the server for easy deployment and dependency management. This was an original goal that has not been completed.

## Client and UI Development

- [ ] **Create a Browser Extension Client:** Develop a browser extension (e.g., for Chrome) that can capture audio and send it to the server, as mentioned in the initial objectives.
- [ ] **Create a Python Module Client:** Package the client logic into an installable Python module (`pip installable`) to make it easy to integrate into other Python applications.
- [ ] **Develop a Basic GUI:** Create a simple graphical user interface for the client to replace the current CLI, which would fulfill the "basic UI" requirement of the MVP.

## Testing and Quality Assurance

- [ ] **Write Unit Tests:** Add unit tests for the `ASRService` to verify transcription logic and for the VAD state machine.
- [ ] **Write Integration Tests:** Create tests for the WebSocket communication between the client and server to ensure reliability.

## Performance and Feature Refinements

- [ ] **Make Silence Threshold Configurable:** Allow the `SILENCE_THRESHOLD` to be set via the configuration file or environment variables to better suit different microphones and environments.
- [ ] **Expose ASR Parameters:** Allow advanced `faster-whisper` parameters (e.g., `beam_size`) to be configured for fine-tuning the speed vs. accuracy trade-off.
- [ ] **Improve Client Reconnection Logic:** Make the client more robust so it can automatically try to reconnect to the server if the connection is lost.

## Troubleshooting / Known Issues

### CUDA / cuDNN Library Not Found (Aborted core dumped)

**Problem:** When running the server on a CUDA-enabled GPU, the application aborts with an error indicating that `libcudnn_ops.so` or other cuDNN related libraries cannot be loaded.

**Cause:** This typically means that the NVIDIA cuDNN library (which is essential for accelerated deep learning operations on GPUs) is either not installed, not correctly installed, or not discoverable by the system's dynamic linker (i.e., not in `LD_LIBRARY_PATH`).

**Solution:**

We have provided a convenience script `start_server.sh` that automatically sets up the environment variables to locate the NVIDIA libraries installed in the virtual environment.

1.  **Use the Startup Script (Recommended):**
    ```bash
    ./start_server.sh
    ```
    This script finds the necessary libraries (like `libcudnn` and `libcublas`) within your `venv` and adds them to `LD_LIBRARY_PATH` before starting the server.

2.  **Manual Fix (If running manually):**
    If you prefer to run `uvicorn` directly, you must export the `LD_LIBRARY_PATH` first:
    ```bash
    export LD_LIBRARY_PATH=$(find venv/lib/python*/site-packages/nvidia -name lib -type d | paste -sd ":" -):$LD_LIBRARY_PATH
    venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000
    ```

3.  **Fallback to CPU:** If you still face issues or lack a GPU:
    ```bash
    DEVICE="cpu" ./start_server.sh
    ```