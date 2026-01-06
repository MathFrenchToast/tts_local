# Plugin System Documentation

The TTS Local Server features a flexible plugin system that allows developers to extend the text processing pipeline without modifying the core server code.

## Architecture

The server uses a sequential processing pipeline:

```
[ASR Engine] --> [Pipeline Step 1] --> [Pipeline Step 2] --> ... --> [Client]
```

By default, the `LLMCorrectionStep` (if enabled) is the first step in this pipeline. Any custom plugins found in the `plugins/` directory are appended after it.

## Creating a Plugin

To create a new plugin, simply create a Python file (e.g., `my_plugin.py`) in the `plugins/` directory.

### Minimal Example

Your plugin must inherit from `ProcessingStep` (defined in `src.interfaces`) and implement two methods: `name` and `process`.

```python
# plugins/logger_plugin.py
from src.interfaces import ProcessingStep
from typing import Dict, Any

class LoggerPlugin(ProcessingStep):
    """
    A simple plugin that logs all transcribed text to a file.
    """
    
    @property
    def name(self) -> str:
        """Unique name for the plugin."""
        return "file_logger"

    async def process(self, text: str, context: Dict[str, Any] = None) -> str:
        """
        Process the text.
        
        Args:
            text: The text received from the previous step.
            context: Metadata (e.g., {'language': 'en', 'raw_asr': '...'})
        
        Returns:
            The text to pass to the next step (or the final output).
        """
        
        # Perform your custom logic
        with open("transcriptions.log", "a") as f:
            f.write(f"{text}\n")
            
        # Return the text unmodified (or modified if you want to change the output)
        return text
```

### Installation

1.  Drop your `.py` file into the `plugins/` folder at the root of the project.
2.  Restart the server (`./start_server.sh`).
3.  The server log will show: `Pipeline: Added step 'file_logger'`.

## Advanced Usage

### Context Dictionary
The `context` dictionary allows you to share data between plugins or access metadata.
- `context['language']`: The detected or configured language code (e.g., "en").
- `context['raw_asr']`: The original raw text from the ASR engine (before LLM correction).

### Modifying the Pipeline Order
Currently, plugins are loaded in alphabetical order of their filenames. To control the order, you can prefix your filenames (e.g., `01_cleaner.py`, `99_logger.py`).

### Dependencies
If your plugin requires external libraries (e.g., `requests`, `googletrans`), make sure to install them in the server's virtual environment:
```bash
source venv/bin/activate
pip install <library_name>
```
