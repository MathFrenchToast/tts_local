*Coding with one hand? Challenge accepted.*

  After a recent skiing accident left me with only my left hand to work with, I realized I needed a way to code and
  communicate efficiently on Linux.

  I love tools like SuperWhisper, but their lack of Linux support and the price tiers forced me to build my own alternative.  
  I wanted a "Universal Dictation" tool—something that runs locally, respects my privacy, and types exactly where I tell it to.

  So I built an Audio > Auto Speech Recognition > Keyboard input simulation solution.

  The Technical Stack:
   * Backend: A Dockerized FastAPI server running Faster-Whisper (with CUDA or CPUsupport) for real-time transcription.
   * Extensible Pipeline: I architected a modular Plugin System. It comes with an optional built-in LLM Plugin (connected to Ollama) that automatically cleans up hallucinations, formats punctuation, and fixes grammar before the text      is even typed.
   * Frontend: A cross-platform System Tray client (Python/Pystray).
   * The Hack: To bypass Wayland security restrictions on modern Linux (Gnome), I implemented a clipboard injection method
     (xdotool), allowing dictation into any native application—VS Code, Terminal, Firefox, or system apps.

  It’s fast, private, and fully open-source.
  It's usable. I've used various early version to code the next one usin gemini CLI.
  Tested on terminal, gmail, Gemini, Drive, texteditor, slack, firefox...

  If you are looking for a local Speech-to-Text solution that works on Linux (but also Windows & Mac), give it a try!

  GitHub Repo: https://github.com/MathFrenchToast/local_whisper

  #DevLife #Linux #Python #OpenAI #Whisper #LocalLLM #Ollama #Accessibility #OpenSource
