"""
Textual Screens for MIDITyper.

This package contains all screen classes for the multi-screen TUI:
- MainMenuScreen: Landing screen with navigation buttons
- CaptureScreen: Dynamic capture view based on preset
- SettingsScreen: Device selection and global config
- PresetEditorScreen: GUI to create/edit presets
"""

from .main_menu import MainMenuScreen
from .capture_screen import CaptureScreen
from .settings_screen import SettingsScreen
from .preset_editor import PresetEditorScreen

__all__ = [
    "MainMenuScreen",
    "CaptureScreen",
    "SettingsScreen",
    "PresetEditorScreen",
]
