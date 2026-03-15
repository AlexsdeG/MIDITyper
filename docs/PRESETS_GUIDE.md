# MIDITyper Presets Guide

This guide explains how to create, customize, and understand preset files for MIDITyper.

## Table of Contents

1. [Overview](#overview)
2. [JSON Structure](#json-structure)
3. [Pages Architecture](#pages-architecture)
4. [UI Modules](#ui-modules)
5. [Mapping Types](#mapping-types)
6. [Global Actions](#global-actions)
7. [Examples](#examples)
8. [Best Practices](#best-practices)

---

## Overview

MIDITyper uses JSON-based preset files to define keyboard-to-MIDI mappings. Each preset file contains:

- **Metadata**: Name and description
- **UI Modules**: Which visual components to display
- **Pages**: One or more key mapping configurations
- **Global Actions**: Key bindings that work across all pages

Presets are stored in the `data/presets/` directory and can be loaded through the TUI or CLI.

---

## JSON Structure

### Basic Schema

```json
{
  "name": "Preset Name",
  "description": "Human-readable description",
  "ui_modules": ["module1", "module2"],
  "pages": [
    {
      "name": "Page Name",
      "mappings": {
        "KEY_X": { "type": "note", "note": 60, "name": "C4" }
      }
    }
  ],
  "global_actions": {
    "KEY_F12": { "type": "action", "action": "TOGGLE_CAPTURE" }
  }
}
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Display name for the preset |
| `description` | string | No | Longer description shown in UI |
| `ui_modules` | string[] | No | List of UI modules to display |
| `pages` | Page[] | Yes | Array of page configurations |
| `global_actions` | object | No | Key-to-action mappings for all pages |

---

## Pages Architecture

### The Pages System

MIDITyper uses a **Pages** system instead of fixed octave shifting. This provides flexibility for different use cases:

- **Piano Presets**: Multiple pages representing different octaves
- **Drum Presets**: Single page with all drum sounds
- **Custom Layouts**: Any number of pages with arbitrary mappings

### Page Object Structure

```json
{
  "name": "Octave 4",
  "mappings": {
    "KEY_Z": { "type": "note", "note": 60, "name": "C4" },
    "KEY_S": { "type": "note", "note": 61, "name": "C#4" }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Display name for the page |
| `mappings` | object | Key-to-mapping dictionary |

### Page Navigation

For multi-page presets, navigation is handled via global actions:

```json
"global_actions": {
  "KEY_F9": { "type": "action", "action": "PAGE_UP" },
  "KEY_F10": { "type": "action", "action": "PAGE_DOWN" }
}
```

**Important**: Single-page presets automatically hide page navigation UI elements.

---

## UI Modules

UI modules determine which visual components appear in the Capture Screen. Configure them via the `ui_modules` array:

```json
"ui_modules": ["event_log", "active_notes_panel", "shortcut_guide"]
```

### Available Modules

| Module | Description |
|--------|-------------|
| `event_log` | Scrollable log of key press/release events |
| `active_notes_panel` | Shows currently playing notes |
| `shortcut_guide` | Displays keyboard shortcuts |
| `drum_pad_visualizer` | Visual grid for drum pad layouts |
| `piano_keyboard_visualizer` | Piano keyboard representation |
| `page_indicator` | Shows current page (for multi-page presets) |
| `velocity_meter` | Current velocity display |

### Module Recommendations

**For Piano Presets:**
```json
"ui_modules": ["event_log", "active_notes_panel", "piano_keyboard_visualizer"]
```

**For Drum Presets:**
```json
"ui_modules": ["drum_pad_visualizer", "event_log"]
```

---

## Mapping Types

### Note Mapping

Send a MIDI Note On/Off message:

```json
"KEY_Z": {
  "type": "note",
  "note": 60,
  "name": "C4"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Must be `"note"` |
| `note` | int | MIDI note number (0-127) |
| `name` | string | Display name (optional) |

### Action Mapping

Trigger an application action:

```json
"KEY_F12": {
  "type": "action",
  "action": "TOGGLE_CAPTURE"
}
```

#### Available Actions

| Action | Type | MIDI/Behavior | Description |
|--------|------|---------------|-------------|
| `TOGGLE_CAPTURE` | `action` | App state | Switch between capture and passthrough mode |
| `PAGE_UP` | `action` | App state | Go to next page |
| `PAGE_DOWN` | `action` | App state | Go to previous page |
| `PANIC` | `action` | MIDI Panic | Send All Notes Off |
| `VELOCITY_UP` | `action` | App state | Increase note velocity |
| `VELOCITY_DOWN` | `action` | App state | Decrease note velocity |
| `QUIT` | `action` | App state | Trigger app quit flow |
| `TRACK_SELECT_NEXT` | `action` | CC 20 (127) | DAW: select next track |
| `TRACK_SELECT_PREV` | `action` | CC 21 (127) | DAW: select previous track |
| `TRACK_MUTE_TOGGLE` | `action` | CC 22 (0/127 toggle) | DAW: toggle track mute |
| `TRACK_SOLO_TOGGLE` | `action` | CC 23 (0/127 toggle) | DAW: toggle track solo |
| `LOOP_TOGGLE` | `action` | CC 24 (0/127 toggle) | DAW: toggle loop |
| `LOOP_IN_SET` | `action` | CC 25 (127) | DAW: set loop in point |
| `LOOP_OUT_SET` | `action` | CC 26 (127) | DAW: set loop out point |
| `LOOP_ENABLE` | `action` | CC 24 (127) | DAW: force loop on |
| `LOOP_DISABLE` | `action` | CC 24 (0) | DAW: force loop off |
| `ZOOM_IN` | `action` | CC 27 (127) | DAW: zoom in |
| `ZOOM_OUT` | `action` | CC 28 (127) | DAW: zoom out |
| `MOVE_LEFT` | `action` | CC 29 (127) | DAW: move/scroll left |
| `MOVE_RIGHT` | `action` | CC 30 (127) | DAW: move/scroll right |

---

## Global Actions

Global actions work across all pages in a preset. Define them at the root level:

```json
{
  "name": "My Preset",
  "pages": [...],
  "global_actions": {
    "KEY_F12": { "type": "action", "action": "TOGGLE_CAPTURE" },
    "KEY_F9": { "type": "action", "action": "PAGE_UP" },
    "KEY_F10": { "type": "action", "action": "PAGE_DOWN" },
    "KEY_ESC": { "type": "action", "action": "PANIC" },
    "KEY_MINUS": { "type": "action", "action": "VELOCITY_DOWN" },
    "KEY_EQUAL": { "type": "action", "action": "VELOCITY_UP" }
  }
}
```

---

## Examples

### Multi-Page Piano Preset

```json
{
  "name": "Piano 3-Octave",
  "description": "Full piano layout across 3 octaves",
  "ui_modules": ["event_log", "active_notes_panel", "piano_keyboard_visualizer"],
  "pages": [
    {
      "name": "Octave 3",
      "mappings": {
        "KEY_Z": { "type": "note", "note": 48, "name": "C3" },
        "KEY_S": { "type": "note", "note": 49, "name": "C#3" },
        "KEY_X": { "type": "note", "note": 50, "name": "D3" },
        "KEY_D": { "type": "note", "note": 51, "name": "D#3" },
        "KEY_C": { "type": "note", "note": 52, "name": "E3" },
        "KEY_V": { "type": "note", "note": 53, "name": "F3" }
      }
    },
    {
      "name": "Octave 4",
      "mappings": {
        "KEY_Z": { "type": "note", "note": 60, "name": "C4" },
        "KEY_S": { "type": "note", "note": 61, "name": "C#4" },
        "KEY_X": { "type": "note", "note": 62, "name": "D4" }
      }
    },
    {
      "name": "Octave 5",
      "mappings": {
        "KEY_Z": { "type": "note", "note": 72, "name": "C5" },
        "KEY_S": { "type": "note", "note": 73, "name": "C#5" },
        "KEY_X": { "type": "note", "note": 74, "name": "D5" }
      }
    }
  ],
  "global_actions": {
    "KEY_F12": { "type": "action", "action": "TOGGLE_CAPTURE" },
    "KEY_F9": { "type": "action", "action": "PAGE_UP" },
    "KEY_F10": { "type": "action", "action": "PAGE_DOWN" },
    "KEY_ESC": { "type": "action", "action": "PANIC" },
    "KEY_MINUS": { "type": "action", "action": "VELOCITY_DOWN" },
    "KEY_EQUAL": { "type": "action", "action": "VELOCITY_UP" }
  }
}
```

### Single-Page Drum Preset

```json
{
  "name": "GM Drums",
  "description": "General MIDI drum kit on numpad",
  "ui_modules": ["drum_pad_visualizer", "event_log"],
  "pages": [
    {
      "name": "Drum Kit",
      "mappings": {
        "KEY_KP0": { "type": "note", "note": 36, "name": "Kick" },
        "KEY_KP5": { "type": "note", "note": 38, "name": "Snare" },
        "KEY_KP4": { "type": "note", "note": 42, "name": "HH Closed" },
        "KEY_KP6": { "type": "note", "note": 46, "name": "HH Open" },
        "KEY_KPASTERISK": { "type": "note", "note": 49, "name": "Crash" },
        "KEY_KPMINUS": { "type": "note", "note": 51, "name": "Ride" }
      }
    }
  ],
  "global_actions": {
    "KEY_F12": { "type": "action", "action": "TOGGLE_CAPTURE" },
    "KEY_ESC": { "type": "action", "action": "PANIC" }
  }
}
```

---

## Best Practices

### 1. Naming Conventions

- Use descriptive page names: `"Octave 4"` instead of `"Page 1"`
- Include note names in mappings for clarity
- Name presets to indicate their purpose

### 2. Key Mapping Layouts

- Use logical groupings (e.g., left hand = lower octave, right hand = upper)
- Consider ergonomic comfort for frequently used notes
- Avoid conflicts with global actions

### 3. Single-Page vs Multi-Page

**Use single-page when:**
- All sounds fit comfortably on one keyboard row
- Quick access is more important than range (drums, sound FX)

**Use multi-page when:**
- You need a wider note range than keys available
- You want to organize sounds by category

### 4. Testing Presets

1. Start with a minimal mapping and test
2. Gradually add more mappings
3. Verify MIDI output with a MIDI monitor
4. Check that global actions don't conflict with mappings

---

## Key Code Reference

Common evdev key codes used in mappings:

| Key Code | Key |
|----------|-----|
| `KEY_A` - `KEY_Z` | Letter keys |
| `KEY_0` - `KEY_9` | Number row |
| `KEY_F1` - `KEY_F12` | Function keys |
| `KEY_KP0` - `KEY_KP9` | Numpad numbers |
| `KEY_KPASTERISK` | Numpad * |
| `KEY_KPMINUS` | Numpad - |
| `KEY_KPPLUS` | Numpad + |
| `KEY_KPDOT` | Numpad . |
| `KEY_KPSLASH` | Numpad / |
| `KEY_KPENTER` | Numpad Enter |
| `KEY_ESC` | Escape |
| `KEY_MINUS` | - |
| `KEY_EQUAL` | = |
| `KEY_COMMA` | , |
| `KEY_DOT` | . |
| `KEY_SLASH` | / |
| `KEY_SEMICOLON` | ; |

For a complete list, refer to the Linux `input-event-codes.h` header file.

---

## MIDI Note Reference

Common MIDI note numbers:

| Note | Number | Note | Number | Note | Number |
|------|--------|------|--------|------|--------|
| C2 | 36 | C3 | 48 | C4 | 60 |
| C#2 | 37 | C#3 | 49 | C#4 | 61 |
| D2 | 38 | D3 | 50 | D4 | 62 |
| D#2 | 39 | D#3 | 51 | D#4 | 63 |
| E2 | 40 | E3 | 52 | E4 | 64 |
| F2 | 41 | F3 | 53 | F4 | 65 |
| F#2 | 42 | F#3 | 54 | F#4 | 66 |
| G2 | 43 | G3 | 55 | G4 | 67 |
| G#2 | 44 | G#3 | 56 | G#4 | 68 |
| A2 | 45 | A3 | 57 | A4 | 69 |
| A#2 | 46 | A#3 | 58 | A#4 | 70 |
| B2 | 47 | B3 | 59 | B4 | 71 |

### General MIDI Drums (Channel 10)

| Note | Sound | Note | Sound |
|------|-------|------|-------|
| 35 | Bass Drum 2 | 49 | Crash Cymbal 1 |
| 36 | Bass Drum 1 | 51 | Ride Cymbal 1 |
| 37 | Side Stick | 53 | Ride Bell |
| 38 | Snare Drum 1 | 54 | Tambourine |
| 39 | Hand Clap | 55 | Splash Cymbal |
| 40 | Snare Drum 2 | 56 | Cowbell |
| 42 | Closed Hi-Hat | 58 | Vibraslap |
| 44 | Pedal Hi-Hat | 59 | Ride Cymbal 2 |
| 46 | Open Hi-Hat |  |  |

---

## Troubleshooting

### Keys Not Registering

1. Check the key code matches evdev naming
2. Verify the input device is correctly selected in Settings
3. Ensure no other application is capturing the keyboard

### Wrong MIDI Notes

1. Verify note numbers in your preset JSON
2. Check if the receiving application expects a specific channel
3. Confirm the virtual MIDI port is connected

### Page Navigation Not Working

1. Verify `PAGE_UP`/`PAGE_DOWN` actions are in `global_actions`
2. Ensure your preset has multiple pages
3. Check for key conflicts with page mappings

---

For more information, see the MIDITyper main documentation or visit the project repository.
