"""
Configuration parser with Pydantic models for strict validation.

This module defines the data models for the new architecture:
- Page: Contains key mappings for a single page
- Preset: Contains name, ui_modules, and pages list
- Settings: Global application settings
"""

from pathlib import Path
from typing import Dict, List, Literal, Optional
import json
import os

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# UI Module Types
# =============================================================================

UIModuleType = Literal[
    "event_log",
    "active_notes_panel",
    "shortcut_guide",
    "drum_pad_visualizer",
    "piano_keyboard_visualizer",
    "page_indicator",
    "velocity_meter"
]


# =============================================================================
# Key Mapping Models
# =============================================================================

class NoteMapping(BaseModel):
    """Mapping for a key that produces a MIDI note."""
    type: Literal["note"] = "note"
    note: int = Field(
        ...,
        ge=0,
        le=127,
        description="MIDI note number (0-127)"
    )
    name: str = Field(
        ...,
        description="Human-readable note name (e.g., 'C4')"
    )


class ActionMapping(BaseModel):
    """Mapping for a key that triggers an application action."""
    type: Literal["action"] = "action"
    action: Literal[
        "TOGGLE_CAPTURE",
        "PAGE_UP",
        "PAGE_DOWN",
        "PANIC",
        "VELOCITY_UP",
        "VELOCITY_DOWN",
        "QUIT"
    ] = Field(
        ...,
        description="Action to perform"
    )


# Union type for key mappings
KeyMapping = NoteMapping | ActionMapping


# =============================================================================
# Page Model (New Architecture)
# =============================================================================

class Page(BaseModel):
    """
    A single page containing key mappings.
    
    Pages replace the old "octave shift" concept. A drum preset has 1 page,
    while a piano preset has multiple pages (one per octave).
    
    Note: Page name is mutable and can be updated via the Preset Editor.
    """
    name: str = Field(
        default="Default Page",
        description="Display name for this page (e.g., 'Octave 3', 'Drum Kit')"
    )
    mappings: Dict[str, NoteMapping] = Field(
        default_factory=dict,
        description="Mapping of keycodes to MIDI notes for this page"
    )

    @field_validator('mappings', mode='before')
    @classmethod
    def validate_mappings(cls, v):
        """Validate and convert mappings to NoteMapping objects."""
        if not isinstance(v, dict):
            return v
        validated = {}
        for key, mapping in v.items():
            if isinstance(mapping, dict):
                if mapping.get('type') == 'note':
                    validated[key] = NoteMapping(**mapping)
                else:
                    # Skip non-note mappings in page mappings
                    continue
            else:
                validated[key] = mapping
        return validated


# =============================================================================
# Preset Model (New Architecture)
# =============================================================================

class Preset(BaseModel):
    """
    Complete keyboard preset with pages and UI modules.
    
    This is the main preset model for the new architecture:
    - name: Display name for the preset
    - description: Human-readable description
    - ui_modules: List of UI components to render in Capture Screen
    - pages: List of Page objects (each representing a different "layer")
    - global_actions: Actions that work across all pages
    - global_mappings: Key mappings that work across all pages (fallback)
    """
    name: str = Field(
        ...,
        description="Display name for the preset"
    )
    description: str = Field(
        default="",
        description="Human-readable description of the preset"
    )
    ui_modules: List[UIModuleType] = Field(
        default_factory=lambda: ["event_log", "active_notes_panel"],
        description="List of UI modules to display in Capture Screen"
    )
    pages: List[Page] = Field(
        default_factory=lambda: [Page(name="Default")],
        description="List of pages (each with its own key mappings)"
    )
    global_actions: Dict[str, ActionMapping] = Field(
        default_factory=dict,
        description="Global actions that work across all pages"
    )
    global_mappings: Dict[str, dict] = Field(
        default_factory=dict,
        description="Global key mappings that work across all pages (fallback to page mappings)"
    )

    @field_validator('global_actions', mode='before')
    @classmethod
    def validate_global_actions(cls, v):
        """Validate and convert global_actions to ActionMapping objects."""
        if not isinstance(v, dict):
            return v
        validated = {}
        for key, mapping in v.items():
            if isinstance(mapping, dict):
                if mapping.get('type') == 'action':
                    validated[key] = ActionMapping(**mapping)
                else:
                    continue
            else:
                validated[key] = mapping
        return validated

    @property
    def page_count(self) -> int:
        """Get the number of pages in this preset."""
        return len(self.pages)

    @property
    def has_multiple_pages(self) -> bool:
        """Check if this preset has multiple pages."""
        return len(self.pages) > 1

    def get_page(self, index: int) -> Optional[Page]:
        """
        Get a page by index, safely handling out-of-bounds.
        
        Args:
            index: Page index (0-based)
            
        Returns:
            Page object or None if index is out of bounds
        """
        if 0 <= index < len(self.pages):
            return self.pages[index]
        return None


# =============================================================================
# Settings Model
# =============================================================================

class Settings(BaseModel):
    """
    Global application settings stored in data/settings.json.
    
    Settings include:
    - Device configuration
    - Velocity range (min/max for randomization)
    - App-global key mappings (lowest priority fallback)
    """
    default_device_path: str = Field(
        default="",
        description="Path to the default input device"
    )
    virtual_port_name: str = Field(
        default="MIDITyper",
        description="Name for the virtual MIDI port"
    )
    last_used_preset: str = Field(
        default="default_piano",
        description="Name of the last used preset"
    )
    auto_detect_device: bool = Field(
        default=True,
        description="Whether to auto-detect keyboard device"
    )
    min_velocity: int = Field(
        default=100,
        ge=1,
        le=127,
        description="Minimum velocity for random velocity range"
    )
    max_velocity: int = Field(
        default=100,
        ge=1,
        le=127,
        description="Maximum velocity for random velocity range"
    )
    start_captured: bool = Field(
        default=True,
        description="Whether to start in capture mode"
    )
    theme: Literal["dark", "light"] = Field(
        default="dark",
        description="UI theme"
    )
    app_global_mappings: Dict[str, dict] = Field(
        default_factory=dict,
        description="App-global key mappings (lowest priority, fallback for all presets)"
    )


# =============================================================================
# AppConfig - Main Configuration Manager
# =============================================================================

class AppConfig:
    """
    Main configuration manager that handles settings and presets.
    
    This class provides:
    - Settings loading/saving from data/settings.json
    - Preset loading from data/presets/*.json
    - Default data directory creation
    """
    
    # Default presets to create if presets directory is empty
    DEFAULT_PRESETS = {
        "default_piano": {
            "name": "Default Piano",
            "description": "Standard piano layout with multiple octave pages",
            "ui_modules": ["event_log", "active_notes_panel", "shortcut_guide"],
            "pages": [
                {"name": "Octave 3", "mappings": {}},
                {"name": "Octave 4", "mappings": {}},
                {"name": "Octave 5", "mappings": {}}
            ],
            "global_actions": {
                "KEY_F12": {"type": "action", "action": "TOGGLE_CAPTURE"},
                "KEY_F9": {"type": "action", "action": "PAGE_UP"},
                "KEY_F10": {"type": "action", "action": "PAGE_DOWN"},
                "KEY_ESC": {"type": "action", "action": "PANIC"}
            }
        },
        "default_drums": {
            "name": "Default Drums",
            "description": "GM Drum Map layout for keyboard drumming",
            "ui_modules": ["drum_pad_visualizer", "event_log"],
            "pages": [
                {"name": "Drum Kit", "mappings": {}}
            ],
            "global_actions": {
                "KEY_F12": {"type": "action", "action": "TOGGLE_CAPTURE"},
                "KEY_ESC": {"type": "action", "action": "PANIC"}
            }
        }
    }
    
    def __init__(
        self,
        data_dir: Optional[Path] = None
    ):
        """
        Initialize the AppConfig.
        
        Args:
            data_dir: Path to data directory (defaults to MIDITyper/data/)
        """
        # Determine base directory (project root)
        self._base_dir = Path(__file__).parent.parent
        self._data_dir = data_dir or self._base_dir / "data"
        self._presets_dir = self._data_dir / "presets"
        
        # Paths
        self._settings_path = self._data_dir / "settings.json"
        
        # Initialize as None, will be loaded on demand
        self._settings: Optional[Settings] = None
        self._presets: Dict[str, Preset] = {}
        
        # Ensure data directories exist
        self._ensure_data_directories()
    
    def _ensure_data_directories(self) -> None:
        """Create data directories if they don't exist."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._presets_dir.mkdir(parents=True, exist_ok=True)
        
        # Create default settings if not exists
        if not self._settings_path.exists():
            self._create_default_settings()
        
        # Create default presets if presets directory is empty
        preset_files = list(self._presets_dir.glob("*.json"))
        if not preset_files:
            self._create_default_presets()
    
    def _create_default_settings(self) -> None:
        """Create default settings.json."""
        settings = Settings()
        with open(self._settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings.model_dump(), f, indent=2)
    
    def _create_default_presets(self) -> None:
        """Create default preset files."""
        for preset_id, preset_data in self.DEFAULT_PRESETS.items():
            preset_path = self._presets_dir / f"{preset_id}.json"
            with open(preset_path, 'w', encoding='utf-8') as f:
                json.dump(preset_data, f, indent=2)
    
    @property
    def settings(self) -> Settings:
        """Get the validated settings configuration."""
        if self._settings is None:
            self._settings = self._load_settings()
        return self._settings
    
    def _load_settings(self) -> Settings:
        """Load and validate settings.json."""
        if not self._settings_path.exists():
            self._create_default_settings()
        
        with open(self._settings_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return Settings(**data)
    
    def save_settings(self) -> None:
        """Save current settings to disk."""
        if self._settings is None:
            return
        
        with open(self._settings_path, 'w', encoding='utf-8') as f:
            json.dump(self._settings.model_dump(), f, indent=2)
    
    def load_preset(self, preset_name: str) -> Preset:
        """
        Load a preset by name.
        
        Args:
            preset_name: Name of the preset file (without .json extension)
            
        Returns:
            Preset object
            
        Raises:
            FileNotFoundError: If preset file doesn't exist
            ValueError: If preset validation fails
        """
        preset_path = self._presets_dir / f"{preset_name}.json"
        
        if not preset_path.exists():
            raise FileNotFoundError(f"Preset not found: {preset_name}")
        
        with open(preset_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        preset = Preset(**data)
        self._presets[preset_name] = preset
        return preset
    
    def save_preset(self, preset_name: str, preset: Preset) -> None:
        """
        Save a preset to disk.
        
        Args:
            preset_name: Name for the preset file (without .json extension)
            preset: Preset object to save
        """
        preset_path = self._presets_dir / f"{preset_name}.json"
        
        with open(preset_path, 'w', encoding='utf-8') as f:
            json.dump(preset.model_dump(), f, indent=2)
        
        self._presets[preset_name] = preset
    
    def list_presets(self) -> List[str]:
        """
        List all available preset names.
        
        Returns:
            List of preset names (without .json extension)
        """
        preset_files = self._presets_dir.glob("*.json")
        return [f.stem for f in preset_files]
    
    def get_last_preset(self) -> Optional[Preset]:
        """
        Get the last used preset.
        
        Returns:
            Preset object or None if not found
        """
        preset_name = self.settings.last_used_preset
        try:
            return self.load_preset(preset_name)
        except FileNotFoundError:
            return None
    
    def set_last_preset(self, preset_name: str) -> None:
        """
        Set the last used preset and save settings.
        
        Args:
            preset_name: Name of the preset to mark as last used
        """
        self._settings.last_used_preset = preset_name
        self.save_settings()
    
    def delete_preset(self, preset_name: str) -> bool:
        """
        Delete a preset file.

        Args:
            preset_name: Name of the preset to delete
            
        Returns:
            True if deleted, False if not found
        """
        preset_path = self._presets_dir / f"{preset_name}.json"

        if preset_path.exists():
            try:
                # Call delete twice as workaround for file deletion issues
                # First delete
                preset_path.unlink()
            except Exception:
                pass
            
            try:
                # Second delete (auto-accept like pressing delete again)
                if preset_path.exists():
                    preset_path.unlink()
            except Exception:
                pass
            
            self._presets.pop(preset_name, None)
            return True
        return False
    
    def reload(self) -> None:
        """Reload all configuration from disk."""
        self._settings = None
        self._presets.clear()
        _ = self.settings


# =============================================================================
# Convenience function
# =============================================================================

def load_config(data_dir: Optional[Path] = None) -> AppConfig:
    """
    Load and return an AppConfig instance.
    
    Args:
        data_dir: Optional custom path to data directory
        
    Returns:
        AppConfig instance
    """
    return AppConfig(data_dir=data_dir)
