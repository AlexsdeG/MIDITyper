# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-03-08

### Added
- **Initial Release** - Complete keyboard-to-MIDI converter application

#### Core Features
- Real-time keyboard capture via `evdev` with exclusive device grab
- Virtual MIDI port creation using `mido` (ALSA/JACK compatible)
- Zero-latency async event processing within Textual's asyncio loop
- Seamless passthrough mode toggle for normal keyboard operation

#### User Interface
- Textual-based TUI with responsive layout
- Kill switch button for immediate safe shutdown
- Real-time status display (CAPTURING/PASSTHROUGH)
- Active preset and octave shift visualization
- Key event logging
- Keyboard shortcuts (q: quit, p: panic, t: toggle, o/d: octave)

#### CLI Commands
- `midityper start` - Launch the TUI application
- `midityper list-presets` - List available keyboard presets
- `midityper set-preset <name>` - Set active preset
- `midityper list-devices` - List available input devices
- `midityper info` - Show current configuration

#### Configuration
- JSON-based settings with Pydantic validation
- Multiple keyboard presets:
  - `piano_qwertz` - Standard piano layout (34 keys)
  - `drums_qwertz` - GM drum map layout (20 keys)
  - `chromatic_qwertz` - Full chromatic layout (43 keys)
- Octave shift control (-4 to +4)
- Velocity adjustment
- Configurable control keys (toggle, octave, panic)

#### Safety Features
- Panic button sends All Notes Off across all channels
- Automatic Note Off before passthrough toggle
- Graceful error handling for device disconnection
- Permission error detection with user guidance

### Technical Details
- Python 3.10+ compatible
- Dependencies: evdev, mido, python-rtmidi, textual, typer, pydantic
- Requires user to be in `input` group for device access
- ALSA MIDI backend for virtual port creation
