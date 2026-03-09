# Architecture Blueprint - MIDITyper

## System Overview
MIDITyper is a keyboard-to-MIDI translator with a Textual TUI and Typer CLI. It intercepts Linux `evdev` keyboard events, resolves them against multiple keybind layers, and emits MIDI messages to a virtual ALSA/JACK port.

## Core Data Flow

```
Linux Input Event (evdev)
    ↓
Input Listener (input_listener.py)
    ├── Resolve Keybind (Page → Preset Global → App Global)
    ↓
Config Data (Pydantic models in config_parser.py)
    ├── Settings (app-wide globals, MIDI port)
    ├── Preset (pages, preset-level keybinds)
    └── Page (keybind mappings)
    ↓
MIDI Engine (midi_engine.py)
    ├── Construct MIDI message
    ├── Apply velocity range (min/max)
    ↓
Virtual MIDI Port (mido/python-rtmidi)
    ↓
DAW or MIDI synth
```

## File Roles

### `src/main.py`
- **Role:** CLI entry point (Typer app)
- **Responsibilities:**
  - Parse CLI commands (`start`, `list-presets`, `set-preset`, `list-devices`)
  - Initialize Textual app or execute CLI actions
- **Key Functions:**
  - `app.command("start")` – Launch TUI
  - `list_presets()`, `list_devices()` – Info commands

### `src/config_parser.py`
- **Role:** Pydantic schema definitions + file I/O
- **Responsibilities:**
  - Define `Settings`, `Preset`, `Page` Pydantic models
  - Load/save JSON configs from `data/` directory
  - Provide config validation
- **Key Classes:**
  - `Settings` – App globals (MIDI port, default preset, app-level keybinds)
  - `Preset` – Preset container (pages, preset-level keybinds)
  - `Page` – Individual page (keybind mappings for a layout)

### `src/input_listener.py`
- **Role:** evdev event loop + keybind resolution
- **Responsibilities:**
  - Open Linux input device via `evdev`
  - Listen for key press/release events
  - Resolve key against: Page Mappings → Preset Global → App Global
  - Emit MIDI when mapping found
- **Key Functions:**
  - `find_keyboard_device()` – Auto-detect or list input devices
  - `listen_for_events()` – Main event loop

### `src/midi_engine.py`
- **Role:** Stateless MIDI message generator
- **Responsibilities:**
  - Construct MIDI Note On/Off messages
  - Handle velocity ranges (random between min/max)
  - Send to virtual MIDI port (mido)
- **Key Functions:**
  - `send_note_on(note, velocity)` – Emit note on
  - `send_note_off(note)` – Emit note off

### `src/state_manager.py`
- **Role:** Shared application state
- **Responsibilities:**
  - Hold current preset, active page, global settings
  - Coordinate state updates across screens
- **Pattern:** Singleton or reactive signal store

### `src/tui.py`
- **Role:** Main Textual application class
- **Responsibilities:**
  - Initialize Textual App
  - Mount screen stack (MainMenu, Capture, Settings, PresetEditor)
  - Handle app-level events (quit, mode switching)
- **Key Classes:**
  - `MIDITyperApp(App)` – Main Textual app

### `src/screens/`
**Four main screens:**

1. **`main_menu.py`** – Navigation hub
   - Links to Capture, Settings, Preset Editor
   - Display current preset, MIDI port status

2. **`capture_screen.py`** – Real-time key capture
   - Show incoming key events in real-time
   - Display resolved MIDI output
   - Show current page layout
   - Kill switch to disable MIDI

3. **`settings_screen.py`** – App configuration
   - MIDI port selection/creation
   - App-level keybinds (DataTable with Add/Delete)
   - Keyboard input device selection
   - Auto-detect option

4. **`preset_editor.py`** – Preset management
   - Preset selection dropdown
   - Pages list + rename capability
   - Key Mappings DataTable (Add/Edit/Delete)
   - Preset-level globals section

## Configuration Files

### `data/settings.json`
User's app-wide settings:
```json
{
  "midi_port": "MIDITyper", 
  "default_preset": "default_piano",
  "min_velocity": 100,
  "max_velocity": 127,
  "app_global_mappings": { "key_code": {...} }
}
```

### `data/presets/<name>.json`
Preset definition:
```json
{
  "name": "default_piano",
  "pages": [
    { "name": "Page 1", "mappings": {...} },
    ...
  ],
  "global_mappings": { "key_code": {...} }
}
```

## Key Interactions

### Keybind Resolution
```python
def resolve_key(key_code, current_page, active_preset, settings):
    # 1. Check current page mappings
    if key_code in current_page.mappings:
        return current_page.mappings[key_code]
    
    # 2. Check preset global mappings
    if key_code in active_preset.global_mappings:
        return active_preset.global_mappings[key_code]
    
    # 3. Check app global mappings
    if key_code in settings.app_global_mappings:
        return settings.app_global_mappings[key_code]
    
    return None  # No mapping
```

### Screen Lifecycle
1. **Main Menu** (entry)
2. **Capture Screen** (real-time, evdev + MIDI active)
3. **Settings** (pause evdev, edit app config)
4. **Preset Editor** (pause evdev, edit preset config)
5. Return to Main Menu or Capture

## Testing Strategy (Future)

- **Unit Tests:** Pydantic model validation, MIDI message construction
- **Integration Tests:** Config loading, keybind resolution
- **E2E Tests:** (Optional) Textual screen interactions via text-based testing

## Performance Notes

- **Async/Await:** Textual handles async natively. Use for file I/O.
- **evdev Loop:** Keep blocking `listen_for_events()` separate from Textual thread (use threading or subprocesses if needed).
- **MIDI Latency:** Minimize overhead in keybind resolution (use dict lookups, not linear searches).
