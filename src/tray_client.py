import asyncio
import os
import platform
import queue
import subprocess
import sys
import threading

import pyperclip
import pystray
import websockets
from PIL import Image, ImageDraw
from pynput import keyboard

sys.path.append(os.getcwd())

from src.audio_recorder import AudioRecorder

# --- Configuration ---
ICON_SIZE = 64
COLOR_ACTIVE = (40, 167, 69, 255)  # Green
COLOR_INACTIVE = (220, 53, 69, 255)  # Red
COLOR_ERROR = (255, 193, 7, 255)  # Orange/Yellow for errors


class TrayClient:
    def __init__(self, websocket_uri):
        self.websocket_uri = websocket_uri
        self.stop_event = threading.Event()
        self.is_typing_enabled = False
        self.paste_mode = False  # False = Type mode, True = Paste (Clipboard) mode
        self.icon = None
        self.kb_controller = keyboard.Controller()
        self.currently_pressed = set()

        # Queue for thread-safe communication
        self.status_queue = queue.Queue()

        # Pre-generate icons to avoid redrawing issues
        self.icons = {
            "active": self.create_image(COLOR_ACTIVE),
            "inactive": self.create_image(COLOR_INACTIVE),
            "error": self.create_image(COLOR_ERROR),
        }

    def create_image(self, color):
        """Generate a professional looking microphone icon with state color."""
        image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # 1. Draw the background circle (Status color)
        border_color = (0, 0, 0, 50)
        draw.ellipse(
            (2, 2, ICON_SIZE - 2, ICON_SIZE - 2), fill=color, outline=border_color, width=2
        )

        # 2. Draw a stylized white microphone
        mic_color = (255, 255, 255, 230)
        draw.rounded_rectangle((24, 14, 40, 38), radius=8, fill=mic_color)
        draw.arc((18, 26, 46, 44), start=0, end=180, fill=mic_color, width=3)
        draw.line((32, 44, 32, 52), fill=mic_color, width=3)
        draw.line((24, 52, 40, 52), fill=mic_color, width=3)

        return image

    def update_icon_state(self, state):
        """Update the icon based on state ('active', 'inactive', 'error')."""
        if state in self.icons:
            self.icon.icon = self.icons[state]

            if state == "active":
                self.icon.title = "TTS Client: Listening"
            elif state == "inactive":
                self.icon.title = "TTS Client: Paused (F8)"
            elif state == "error":
                self.icon.title = "TTS Client: Connection Error"

    def on_toggle_click(self, icon, item):
        self.toggle_typing()

    def on_mode_click(self, icon, item):
        """Toggle between Type and Paste modes."""
        self.paste_mode = not self.paste_mode
        print(f"Mode changed: {'Paste' if self.paste_mode else 'Type'}")
        # Pystray menu is immutable, but we can re-assign the whole menu if needed.
        # For simplicity, we just print and rely on the user seeing the toggle state if we had one.
        # On some platforms, item.checked works if we used a checkbox.

    def on_exit_click(self, icon, item):
        print("Exiting...")
        self.stop_event.set()
        if self.icon:
            self.icon.stop()

    def toggle_typing(self):
        self.is_typing_enabled = not self.is_typing_enabled
        new_state = "active" if self.is_typing_enabled else "inactive"
        self.update_icon_state(new_state)
        print(f"State toggled: {new_state}")

    def on_press(self, key):
        """Keyboard press handler with Shift+F8 exit support."""
        if key == keyboard.Key.f8:
            is_shift = any(
                k in self.currently_pressed
                for k in [keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r]
            )
            if is_shift:
                self.on_exit_click(None, None)
            else:
                self.toggle_typing()

        self.currently_pressed.add(key)

    def on_release(self, key):
        """Keyboard release handler."""
        if key in self.currently_pressed:
            self.currently_pressed.remove(key)

    async def async_audio_loop(self):
        """Main async loop for audio and websocket."""
        print(f"Connecting to {self.websocket_uri}...")

        while not self.stop_event.is_set():
            try:
                async with websockets.connect(self.websocket_uri) as websocket:
                    print("Connected to server.")
                    self.status_queue.put("active" if self.is_typing_enabled else "inactive")

                    recorder = AudioRecorder(rate=16000, chunk_size=1024, channels=1)
                    recorder.start_recording()

                    try:
                        # Task: Send Audio
                        async def send_audio():
                            audio_iter = recorder.get_audio_chunk()
                            for chunk in audio_iter:
                                if self.stop_event.is_set():
                                    break
                                if self.is_typing_enabled:
                                    await websocket.send(chunk.tobytes())
                                await asyncio.sleep(0.001)

                        # Task: Receive Text
                        async def receive_text():
                            while not self.stop_event.is_set():
                                try:
                                    message = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                                    text = message.strip()
                                    if text:
                                        print(f"Server: {text}")
                                        if self.is_typing_enabled:
                                            full_text = text + " "

                                            if self.paste_mode:
                                                # --- Paste Mode (Clipboard Injection) ---
                                                try:
                                                    pyperclip.copy(full_text)
                                                    await asyncio.sleep(0.05)
                                                    if platform.system() == "Linux":
                                                        # Try Shift+Insert first as it's more universal
                                                        subprocess.run(
                                                            ["xdotool", "key", "shift+Insert"],
                                                            check=False,
                                                        )
                                                    else:
                                                        with self.kb_controller.pressed(
                                                            keyboard.Key.ctrl
                                                        ):
                                                            self.kb_controller.press("v")
                                                            self.kb_controller.release("v")
                                                except Exception as e:
                                                    print(f"Paste Error: {e}")
                                            else:
                                                # --- Type Mode (Simulated Typing) ---
                                                if platform.system() == "Linux":
                                                    try:
                                                        # Use xdotool type for robustness
                                                        subprocess.run(
                                                            [
                                                                "xdotool",
                                                                "type",
                                                                "--delay",
                                                                "2",
                                                                full_text,
                                                            ],
                                                            check=False,
                                                        )
                                                    except FileNotFoundError:
                                                        # Fallback to pynput
                                                        self.kb_controller.type(full_text)
                                                else:
                                                    self.kb_controller.type(full_text)

                                except asyncio.TimeoutError:
                                    continue

                        task_send = asyncio.create_task(send_audio())
                        task_recv = asyncio.create_task(receive_text())

                        while not self.stop_event.is_set():
                            if task_send.done() or task_recv.done():
                                break
                            await asyncio.sleep(0.1)

                        task_send.cancel()
                        task_recv.cancel()

                    except Exception as e:
                        print(f"Session error: {e}")
                    finally:
                        recorder.stop_recording()

            except Exception as e:
                if not self.stop_event.is_set():
                    print(f"Connection failed: {e}. Retrying in 2s...")
                    self.status_queue.put("error")
                    await asyncio.sleep(2)

    def run_async_thread(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.async_audio_loop())
        loop.close()

    def run(self):
        kb_listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        kb_listener.start()

        t = threading.Thread(target=self.run_async_thread, daemon=True)
        t.start()

        # Define the menu with a toggle-able mode item
        def get_mode_text(item):
            return "Switch to Type Mode" if self.paste_mode else "Switch to Paste Mode"

        self.icon = pystray.Icon(
            "TTS Client",
            self.icons["inactive"],
            "TTS Client: Paused",
            menu=pystray.Menu(
                pystray.MenuItem("Toggle (F8)", self.on_toggle_click),
                pystray.MenuItem(get_mode_text, self.on_mode_click),
                pystray.MenuItem("Exit (Shift+F8)", self.on_exit_click),
            ),
        )

        self.icon.run()
        kb_listener.stop()
        print("Tray client exited.")


if __name__ == "__main__":
    uri = "ws://127.0.0.1:8000/ws/asr"
    client = TrayClient(uri)
    client.run()
