# MIDITyper

**Version 0.1.0**

A highly efficient, background-capable Linux CLI/TUI application that intercepts physical keyboard inputs via `evdev`, translates them into MIDI messages, and sends them to a virtual MIDI port.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Features

- **Real-time keyboard-to-MIDI translation** - Zero-latency async event processing
- **Virtual MIDI port** - Creates ALSA/JACK compatible MIDI port
- **Textual-based TUI** - Clean terminal interface with kill switch
- **Seamless passthrough** - Toggle between MIDI and normal keyboard mode
- **Multiple presets** - Piano, drums, and chromatic layouts included
- **Pydantic validation** - Type-safe JSON configuration

## Requirements

- Python 3.10+
- Linux with evdev and ALSA support
- User must be in the `input` group

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd MIDITyper

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Add user to input group (required for keyboard access)
sudo usermod -aG input $USER

# Logout and login again for group changes to take effect
```

## Usage

### Starting the Application

```bash
# Activate virtual environment
source .venv/bin/activate

# Start the TUI application
PYTHONPATH=. python -m src.main start

# Or with options
PYTHONPATH=. python -m src.main start --preset drums_qwertz --verbose
```

### CLI Commands

```bash
# List available presets
PYTHONPATH=. python -m src.main list-presets

# Set active preset
PYTHONPATH=. python -m src.main set-preset piano_qwertz

# List input devices
PYTHONPATH=. python -m src.main list-devices

# Show current configuration
PYTHONPATH=. python -m src.main info
```

### Keyboard Shortcuts (in TUI)

| Key | Action |
|-----|--------|
| `q` | Quit application |
| `p` | Panic (all notes off) |
| `t` | Toggle capture/passthrough |
| `o` | Octave up |
| `d` | Octave down |

### Control Keys (when capturing)

| Key | Action |
|-----|--------|
| `F12` | Toggle capture mode |
| `F9` | Octave up |
| `F10` | Octave down |
| `ESC` | Panic (all notes off) |
| `+` / `-` | Velocity up/down |

## Included Presets

### piano_qwertz
Standard QWERTZ keyboard layout for piano playing (34 keys, 3+ octaves)

```
Row 1 (Q-P):     C4  D4  E4  F4  G4  A4  B4  C5  D5  E5
Row 2 (A-L):     C3  D3  E3  F3  G3  A3  B3  C4
Black keys:      S, D, G, H, J (sharps/flats)
```

### drums_qwertz
QWERTZ keyboard layout for drum triggering using GM Drum Map (20 keys)

```
Y=Kick  X=Snare  C=HH Closed  V=HH Open  B=Tom Low  N=Tom Mid  M=Tom High
```

### chromatic_qwertz
Full chromatic layout across multiple rows (43 keys, 3+ octaves)

## Configuration

### settings.json
Hardware and application settings:

```json
{
  "device": {
    "path": "/dev/input/by-path/...",
    "auto_detect": true
  },
  "midi": {
    "virtual_port_name": "MIDITyper",
    "default_channel": 0,
    "default_velocity": 100
  },
  "behavior": {
    "start_captured": true,
    "default_octave_shift": 0
  }
}
```

### presets.json
Keyboard layout definitions with key-to-MIDI mappings and action bindings.

## Connecting to DAW

1. Start MIDITyper
2. In your DAW (Ardour, Reaper, Bitwig, etc.), look for a MIDI input device named "MIDITyper"
3. Enable it as a MIDI input
4. Play notes on your keyboard!

## Troubleshooting

### "Permission denied" error
```
Add your user to the 'input' group:
  sudo usermod -aG input $USER

Refresh group membership in your active session:
  # preferred
  log out and back in (or reboot)
  # temporary in current shell
  newgrp input

Verify group is active:
  id -nG | grep -qw input && echo "input group active"
```

### "No keyboard device found"
```
List available devices:
  PYTHONPATH=. python -m src.main list-devices

Specify device manually:
  PYTHONPATH=. python -m src.main start --device /dev/input/event0
```

### "Failed to create MIDI port"
```
Ensure ALSA is available:
  aconnect -l
```

## Project Structure

```
MIDITyper/
├── configs/
│   ├── settings.json      # Application settings
│   └── presets.json       # Keyboard layouts
├── src/
│   ├── __init__.py        # Package init
│   ├── main.py            # CLI entry point
│   ├── config_parser.py   # Pydantic models
│   ├── midi_engine.py     # MIDI output
│   ├── input_listener.py  # Keyboard capture
│   ├── state_manager.py   # Application state
│   └── tui.py             # Textual UI
├── requirements.txt
├── CHANGELOG.md
└── README.md
```

## License

MIT License - See LICENSE file for details.

## Acknowledgments

- [evdev](https://python-evdev.readthedocs.io/) - Input device handling
- [mido](https://mido.readthedocs.io/) - MIDI library
- [Textual](https://textual.textualize.io/) - TUI framework
- [Typer](https://typer.tiangolo.com/) - CLI framework
- [Pydantic](https://docs.pydantic.dev/) - Data validation
