"""
Textual TUI module for MIDITyper.

This is the core application router that manages:
- Screen registration and navigation
- MIDI engine lifecycle
- Input listener lifecycle
- Application state
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from textual.app import App
from textual.screen import Screen

from .config_parser import AppConfig, Preset
from .input_listener import InputListener
from .midi_engine import MidiEngine
from .state_manager import StateManager

# Import screens
from .screens import (
    MainMenuScreen,
    CaptureScreen,
    SettingsScreen,
    PresetEditorScreen,
)

logger = logging.getLogger(__name__)


class KeyboardMidiApp(App):
    """
    Main Textual application for MIDITyper.
    
    This is a multi-screen application with:
    - Main Menu: Navigation hub
    - Capture Screen: Dynamic capture view
    - Settings Screen: Configuration
    - Preset Editor: Create/edit presets
    
    The app manages shared resources:
    - MIDI engine (virtual port)
    - Input listener (keyboard capture)
    - State manager (application state)
    - Configuration (settings & presets)
    """
    
    # Load CSS from external file
    CSS_PATH = Path(__file__).parent.parent / "styles" / "app.tcss"
    
    SCREENS = {
        "main_menu": MainMenuScreen,
        "capture": CaptureScreen,
        "settings": SettingsScreen,
        "preset_editor": PresetEditorScreen,
    }
    
    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+b", "back", "Back"),
    ]
    
    # Application state
    config: Optional[AppConfig] = None
    preset: Optional[Preset] = None
    midi_engine: Optional[MidiEngine] = None
    state_manager: Optional[StateManager] = None
    input_listener: Optional[InputListener] = None
    _input_task: Optional[asyncio.Task] = None
    
    def __init__(
        self,
        config: Optional[AppConfig] = None,
        **kwargs
    ):
        """
        Initialize the application.
        
        Args:
            config: Application configuration (loaded if not provided)
        """
        super().__init__(**kwargs)
        self.config = config or AppConfig()
    
    def on_mount(self) -> None:
        """Initialize the application on mount."""
        logger.info("MIDITyper starting...")
        
        # Push main menu as the first screen
        self.push_screen("main_menu")
    
    def on_unmount(self) -> None:
        """Clean up on unmount."""
        logger.info("MIDITyper shutting down...")
        self._cleanup_resources()
    
    def _cleanup_resources(self) -> None:
        """Clean up all resources."""
        # Stop input listener
        if self._input_task:
            self._input_task.cancel()
            self._input_task = None
        
        # Close MIDI engine
        if self.midi_engine:
            self.midi_engine.close()
            self.midi_engine = None
    
    def action_quit(self) -> None:
        """Quit the application."""
        self._cleanup_resources()
        self.exit()
    
    def action_back(self) -> None:
        """Go back to previous screen."""
        if len(self.screen_stack) > 1:
            self.pop_screen()
    
    async def initialize_capture_resources(self) -> bool:
        """
        Initialize resources needed for capture mode.

        Returns:
            True if initialization successful, False otherwise
        """
        settings = self.config.settings
        logger.info("Initializing capture resources")

        # Load last used preset
        self.preset = self.config.get_last_preset()
        if not self.preset:
            try:
                self.preset = self.config.load_preset("default_piano")
            except FileNotFoundError:
                self.notify("No presets available!", severity="error")
                return False

        # Reuse existing running listener/resources if already initialized
        if self.input_listener and self.input_listener.is_running and self.state_manager and self.midi_engine:
            logger.info("Capture resources already running; reusing existing instances")
            self.set_capture_mode(settings.start_captured)
            # Update velocity range from settings
            self.state_manager.min_velocity = settings.min_velocity
            self.state_manager.max_velocity = settings.max_velocity
            self.midi_engine.set_velocity_range(settings.min_velocity, settings.max_velocity)
            if self.preset:
                self.state_manager.set_active_preset(self.preset)
            return True

        initial_velocity = max(settings.min_velocity, min(settings.max_velocity, 100))

        self.state_manager = StateManager(
            is_captured=settings.start_captured,
            current_page_index=0,
            current_velocity=initial_velocity,
            min_velocity=settings.min_velocity,
            max_velocity=settings.max_velocity,
        )
        self.state_manager.set_active_preset(self.preset)

        try:
            self.midi_engine = MidiEngine(
                port_name=settings.virtual_port_name,
                default_channel=0,
                default_velocity=initial_velocity,
                min_velocity=settings.min_velocity,
                max_velocity=settings.max_velocity,
            )
            logger.info(f"MIDI engine initialized: {settings.virtual_port_name}")
        except OSError as e:
            logger.error(f"Failed to initialize MIDI: {e}")
            self.notify(
                f"Failed to create MIDI port: {e}\nMake sure ALSA is available.",
                severity="error",
                title="MIDI Error",
            )
            return False

        device_path = settings.default_device_path
        if settings.auto_detect_device:
            from .input_listener import find_keyboard_device

            detected = find_keyboard_device()
            if detected:
                device_path = detected

        if not device_path:
            self.notify(
                "No keyboard device found!\nConfigure device in Settings.",
                severity="warning",
                title="Device Error",
            )
            return False

        try:
            self.input_listener = InputListener(
                device_path=device_path,
                state_manager=self.state_manager,
                midi_engine=self.midi_engine,
                settings=settings,
                on_key_event=self._on_key_event,
                on_device_error=self._on_device_error,
            )
            logger.info(f"Input listener initialized: {device_path}")
        except PermissionError:
            self.notify(
                "Permission denied!\nAdd user to 'input' group:\nsudo usermod -aG input $USER",
                severity="error",
                title="Permission Error",
            )
            return False
        except FileNotFoundError:
            self.notify(
                f"Device not found: {device_path}",
                severity="error",
                title="Device Error",
            )
            return False
        except Exception as e:
            logger.error(f"Failed to initialize input listener: {e}")
            self.notify(f"Input error: {e}", severity="error")
            return False

        return True
    
    async def start_capture(self) -> None:
        """Start the input capture."""
        logger.info("Starting capture listener")
        if self.input_listener:
            await self.input_listener.start()
            logger.info("Input capture started")
            self.set_capture_mode(self.state_manager.is_captured if self.state_manager else True)

    async def stop_capture(self) -> None:
        """Stop the input capture and force passthrough state."""
        logger.info("Stopping capture listener")
        self.set_capture_mode(False)
        if self.input_listener:
            await self.input_listener.stop()
            logger.info("Input capture stopped")

    def set_capture_mode(self, captured: bool) -> bool:
        """Set capture mode and synchronize keyboard grab state."""
        logger.debug("Setting capture mode to %s", captured)
        if self.state_manager:
            self.state_manager.set_capture(captured)
        if self.input_listener:
            self.input_listener.sync_grab_state()
            logger.debug("Synchronized listener grab state after mode change")
        return self.state_manager.is_captured if self.state_manager else captured

    def toggle_capture_mode(self) -> bool:
        """Toggle capture mode and synchronize keyboard grab state."""
        current = self.state_manager.is_captured if self.state_manager else False
        return self.set_capture_mode(not current)
    
    def _on_key_event(self, key_name: str, is_pressed: bool) -> None:
        """
        Handle key events from the input listener.

        Args:
            key_name: Name of the key pressed
            is_pressed: True for key down, False for key up
        """
        screen = self.screen
        if isinstance(screen, CaptureScreen):
            mapping_found = False
            note_name = ""

            if self.state_manager and self.preset:
                page_index = getattr(self.state_manager, "current_page_index", 0)
                page = self.preset.get_page(page_index)

                if page and key_name in page.mappings:
                    mapping_found = True
                    note_name = page.mappings[key_name].name
                elif key_name in self.preset.global_actions:
                    mapping_found = True
                elif key_name in self.preset.global_mappings:
                    mapping_found = True
                    mapping = self.preset.global_mappings[key_name]
                    note_name = mapping.get("name", "") if mapping.get("type") == "note" else ""
                elif self.config and key_name in self.config.settings.app_global_mappings:
                    mapping_found = True
                    mapping = self.config.settings.app_global_mappings[key_name]
                    note_name = mapping.get("name", "") if mapping.get("type") == "note" else ""

            if mapping_found:
                screen.add_key_event(key_name, is_pressed, note_name)

            if self.state_manager and self.preset:
                active_notes = self.state_manager.get_active_notes()
                page = self.preset.get_page(
                    getattr(self.state_manager, "current_page_index", 0)
                )
                note_names = []
                if page:
                    for note in active_notes.keys():
                        match = next(
                            (m.name for m in page.mappings.values() if m.note == note),
                            None,
                        )
                        note_names.append(match or str(note))
                screen.update_active_notes(len(active_notes), note_names)
    
    def _on_device_error(self, error: Exception) -> None:
        """
        Handle device errors from the input listener.
        
        Args:
            error: The exception that occurred
        """
        logger.error(f"Device error: {error}")
        self.notify(
            f"Device error: {error}",
            severity="error",
            title="Device Error"
        )
        
        # Pop back to main menu
        if len(self.screen_stack) > 1:
            self.pop_screen()
    
    def load_preset(self, preset_name: str) -> bool:
        """
        Load a preset by name.
        
        Args:
            preset_name: Name of the preset to load
            
        Returns:
            True if loaded successfully
        """
        try:
            self.preset = self.config.load_preset(preset_name)
            self.config.set_last_preset(preset_name)
            
            if self.state_manager:
                self.state_manager.set_active_preset(self.preset)
            
            self.notify(f"Loaded preset: {self.preset.name}", severity="information")
            return True
        except FileNotFoundError:
            self.notify(f"Preset not found: {preset_name}", severity="error")
            return False


def run_tui(config: Optional[AppConfig] = None) -> None:
    """
    Run the TUI application.
    
    Args:
        config: Optional pre-loaded configuration
    """
    app = KeyboardMidiApp(config=config)
    app.run()


if __name__ == "__main__":
    from .config_parser import load_config
    logging.basicConfig(level=logging.INFO)
    config = load_config()
    run_tui(config)
