# Copilot Instructions for MIDITyper

## Project Overview
MIDITyper is a Python 3.10+ application that translates keyboard inputs via `evdev` into MIDI messages via `mido`, with a Textual-based terminal UI and Typer CLI routing.

## Tech Stack

- **Language:** Python 3.10+
- **Package Manager:** pip (requirements.txt)
- **Primary Framework:** Textual 0.47.0+ (Terminal UI)
- **CLI Framework:** Typer 0.9.0+ (Command routing)
- **Config Layer:** Pydantic 2.5.0+ (schema validation)
- **MIDI Engine:** mido 1.3.0+, python-rtmidi 1.5.8+
- **Input Handling:** evdev 1.6.1+ (Linux keyboard events)
- **Testing:** pytest (recommended, not yet integrated)
- **Linting:** ruff (recommended, not yet integrated)

## Strict Coding Standards

### Python
- **PEP-8 Compliance:** All code must follow PEP-8. Lines ≤88 characters (Black standard).
- **Type Hints:** All function signatures must include type annotations. Use `from typing import ...` for complex types.
- **Docstrings:** Module, class, and public method docstrings required (Google style).
- **Async/Await:** Use `async`/`await` for I/O operations. Avoid blocking calls in Textual UI threads.
- **Pydantic Models:** All config schemas must be Pydantic v2 models with validation.

### Textual UI
- **CSS:** All styling via `styles/app.tcss` (TCSS format). No inline styles.
- **Widgets:** Use Textual's built-in widget library. No external widget packages.
- **State Management:** Use reactive variables and Textual's message system.
- **Layout:** Vertical/Horizontal containers with proper spacing (`height: auto`, `fr` fractions).

### Project Structure
```
src/
├── main.py              # CLI entry point (Typer app)
├── config_parser.py     # Pydantic models & config loading
├── midi_engine.py       # MIDI message generation
├── input_listener.py    # evdev event loop & keybind resolution
├── state_manager.py     # Shared state across screens
├── tui.py               # Main Textual app class
└── screens/
    ├── main_menu.py
    ├── capture_screen.py
    ├── settings_screen.py
    └── preset_editor.py

data/
├── settings.json        # User configuration
└── presets/
    ├── default_piano.json
    ├── default_drums.json
    └── ...

styles/
└── app.tcss             # Centralized styling

configs/
├── settings.json        # Template config
└── presets.json         # Preset templates
```

## Verification Commands

```bash
# Install dependencies
pip install -r requirements.txt

# (Future) Run tests
pytest tests/ -v

# (Future) Run linter
ruff check src/

# Run the application
python -m src.main start

# List input devices
python -m src.main list-devices

# List available presets
python -m src.main list-presets
```

## Key Architectural Principles

1. **Separation of Concerns:** 
   - `config_parser.py` handles schema & loading only.
   - `input_listener.py` manages evdev event loop & keybind resolution.
   - `midi_engine.py` generates MIDI messages (stateless).
   - `screen/*` modules handle user interaction and rendering.

2. **Keybind Resolution Order:** 
   Page Mappings → Preset Global Mappings → App Global Mappings.

3. **Non-blocking I/O:** 
   Config loading, file writes, and MIDI sends must be async where possible.

4. **Pydantic Validation:** 
   All user data (configs, presets) must pass Pydantic schema validation before use.

## Common Commands

| Command | Purpose |
|---------|---------|
| `/plan <request>` | Route to Architect. Generates checklist in IMPLEMENTATION.md. |
| `/execute` | Route to Engineer. Execute first unchecked step in IMPLEMENTATION.md. |
| `/debug` | Route to Engineer. Fix terminal error and re-run test. |
| `/explain <code>` | Route to Architect. Technical analysis of selected code. |
