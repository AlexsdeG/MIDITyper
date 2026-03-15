"""
Input Listener module for capturing keyboard events via evdev.

This module provides asynchronous keyboard capture functionality:
- Evdev device management
- Key event processing
- MIDI note triggering
- Action handling (PAGE_UP, PAGE_DOWN, TOGGLE_CAPTURE, etc.)
- Keybind resolution cascade: Page -> Preset Global -> App Global
"""

import asyncio
import logging
from enum import IntEnum
from typing import Callable, Optional, TYPE_CHECKING

import evdev
from evdev import InputDevice, ecodes

from .config_parser import Preset, Settings
from .midi_engine import MidiEngine
from .state_manager import StateManager

if TYPE_CHECKING:
    from .config_parser import AppConfig

logger = logging.getLogger(__name__)


class KeyEvent(IntEnum):
    """Key event types from evdev."""
    KEY_UP = 0
    KEY_DOWN = 1
    KEY_HOLD = 2


class InputListener:
    """
    Asynchronous keyboard input listener that captures evdev events
    and translates them to MIDI messages.
    
    This class handles:
    - Opening and grabbing input devices
    - Processing key events
    - Routing keys to MIDI notes or application actions
    - Dynamic grab/ungrab for passthrough mode
    - Keybind resolution cascade: Page -> Preset Global -> App Global
    """

    def __init__(
        self,
        device_path: str,
        state_manager: StateManager,
        midi_engine: MidiEngine,
        settings: Optional[Settings] = None,
        on_key_event: Optional[Callable[[str, bool], None]] = None,
        on_device_error: Optional[Callable[[Exception], None]] = None,
        on_toggle_capture: Optional[Callable[[], bool]] = None,
        on_quit: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize the input listener.
        
        Args:
            device_path: Path to the input device (e.g., /dev/input/event0)
            state_manager: StateManager instance for state tracking
            midi_engine: MidiEngine instance for sending MIDI messages
            settings: Settings instance for app-global mappings (optional)
            on_key_event: Optional callback for key events (key_name, is_pressed)
            on_device_error: Optional callback for device errors
            on_toggle_capture: Optional callback to toggle capture mode via app
            on_quit: Optional callback to trigger app shutdown
        """
        self._device_path = device_path
        self._state_manager = state_manager
        self._midi_engine = midi_engine
        self._settings = settings
        self._on_key_event = on_key_event
        self._on_device_error = on_device_error
        self._on_toggle_capture = on_toggle_capture
        self._on_quit = on_quit
        
        self._device: Optional[InputDevice] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._startup_ready = asyncio.Event()
        self._startup_timeout_seconds = 5.0
        self._last_start_error: Optional[str] = None
        
        # Track if device was grabbed
        self._is_grabbed = False
        self._ctrl_keys_held: set[str] = set()

    @staticmethod
    def _is_ctrl_key(keycode: str) -> bool:
        """Return True when keycode is a Ctrl modifier key."""
        return keycode in {"KEY_LEFTCTRL", "KEY_RIGHTCTRL"}

    def _update_modifier_state(self, keycode: str, event_value: int) -> None:
        """Track currently held Ctrl keys for Ctrl+Q handling."""
        if not self._is_ctrl_key(keycode):
            return

        if event_value in {KeyEvent.KEY_DOWN, KeyEvent.KEY_HOLD}:
            self._ctrl_keys_held.add(keycode)
        elif event_value == KeyEvent.KEY_UP:
            self._ctrl_keys_held.discard(keycode)

    def _is_ctrl_held(self) -> bool:
        """Return True when at least one Ctrl key is currently pressed."""
        return bool(self._ctrl_keys_held)

    def _handle_global_shortcuts(self, keycode: str, event_value: int) -> bool:
        """Handle always-available shortcuts before mapping resolution.

        Returns:
            True if the key event is fully handled and should not continue.
        """
        if (
            event_value == KeyEvent.KEY_DOWN
            and keycode == "KEY_Q"
            and self._is_ctrl_held()
            and self._state_manager.is_captured
        ):
            logger.info("Ctrl+Q detected during capture; triggering quit")
            if self._on_quit is not None:
                self._on_quit()
            return True

        return False

    @property
    def device_path(self) -> str:
        """Get the device path."""
        return self._device_path

    @property
    def is_running(self) -> bool:
        """Check if the listener is running."""
        return self._running

    @property
    def device_name(self) -> Optional[str]:
        """Get the device name if opened."""
        return self._device.name if self._device else None

    def _open_device(self) -> InputDevice:
        """
        Open the input device.
        
        Returns:
            Opened InputDevice instance
            
        Raises:
            PermissionError: If user lacks permission to access device
            FileNotFoundError: If device doesn't exist
            OSError: If device is already grabbed by another process
        """
        try:
            device = InputDevice(self._device_path)
            logger.info(f"Opened input device: {device.name} ({self._device_path})")
            return device
        except PermissionError:
            logger.error(
                f"Permission denied for device {self._device_path}. "
                "Add user to 'input' group: sudo usermod -aG input $USER"
            )
            raise
        except FileNotFoundError:
            logger.error(f"Device not found: {self._device_path}")
            raise
        except OSError as e:
            logger.error(f"Failed to open device {self._device_path}: {e}")
            raise

    def _grab_device(self) -> bool:
        """Grab the device to capture all input events exclusively.

        Returns:
            True when the device is grabbed or already grabbed.
        """
        if not self._device or self._is_grabbed:
            return self._is_grabbed

        try:
            self._device.grab()
            self._is_grabbed = True
            logger.info("Device grabbed - capturing input exclusively")
            return True
        except OSError as error:
            self._is_grabbed = False
            self._last_start_error = (
                f"Failed to grab input device {self._device_path}: {error}"
            )
            logger.error(self._last_start_error)
            return False

    def _ungrab_device(self) -> None:
        """Ungrab the device to allow passthrough to OS."""
        if not self._device or not self._is_grabbed:
            return

        try:
            self._device.ungrab()
            logger.debug("Device ungrabbed - passthrough mode")
        except OSError as error:
            logger.error("Failed to ungrab input device: %s", error)
        finally:
            self._is_grabbed = False

    def _update_grab_state(self) -> bool:
        """Update device grab state based on state_manager.is_captured.

        Returns:
            True if requested mode is successfully applied.
        """
        if self._state_manager.is_captured:
            return self._grab_device()

        # Send Note Off for all active notes before ungrabbing
        self._send_all_notes_off()
        self._ungrab_device()
        return True

    def _send_all_notes_off(self) -> None:
        """Send Note Off for all tracked active notes."""
        if self._state_manager.has_active_notes():
            active_notes = self._state_manager.clear_active_notes()
            for note, channel in active_notes.items():
                self._midi_engine.send_note_off(note, channel)
            logger.debug(f"Sent Note Off for {len(active_notes)} active notes")

    def _get_keycode_name(self, code: int) -> Optional[str]:
        """
        Get the keycode name from the event code.
        
        Args:
            code: Event code from evdev
            
        Returns:
            Keycode name string (e.g., 'KEY_A') or None
        """
        try:
            return ecodes.KEY.get(code) or ecodes.BTN.get(code)
        except (ValueError, KeyError):
            return None

    def _handle_note_event(
        self,
        note: int,
        is_pressed: bool,
        channel: int
    ) -> None:
        """
        Handle a MIDI note event.
        
        Args:
            note: MIDI note number
            is_pressed: True for key down, False for key up
            channel: MIDI channel
        """
        if is_pressed:
            velocity = self._state_manager.get_playback_velocity()
            self._midi_engine.send_note_on(note, velocity, channel)
            self._state_manager.register_note_on(note, channel)
        else:
            self._midi_engine.send_note_off(note, channel)
            self._state_manager.register_note_off(note)

    def _handle_action(self, action: str) -> None:
        """
        Handle an application action.
        
        Args:
            action: Action name (e.g., 'TOGGLE_CAPTURE', 'PAGE_UP')
        """
        logger.debug(f"Handling action: {action}")
        
        # Normalize action name to uppercase
        action_upper = action.upper()
        
        if action_upper == "TOGGLE_CAPTURE":
            if self._on_toggle_capture is not None:
                captured = self._on_toggle_capture()
                logger.debug("Capture toggled via app callback. Captured=%s", captured)
            else:
                self._state_manager.toggle_capture()
                if not self._update_grab_state():
                    logger.warning("Capture toggle requested but device grab failed")
            
        elif action_upper == "PAGE_UP":
            self._state_manager.next_page()
            
        elif action_upper == "PAGE_DOWN":
            self._state_manager.prev_page()
            
        elif action_upper == "PANIC":
            self._midi_engine.panic()
            self._state_manager.clear_active_notes()
            if self._on_quit is not None:
                logger.info("PANIC action escalating to app shutdown")
                self._on_quit()
            
        elif action_upper == "VELOCITY_UP":
            self._state_manager.velocity_up()
            
        elif action_upper == "VELOCITY_DOWN":
            self._state_manager.velocity_down()
            
        elif action_upper == "QUIT":
            logger.info("QUIT action triggered")
            if self._on_quit is not None:
                self._on_quit()

        elif action_upper in {
            "TRACK_SELECT_NEXT",
            "TRACK_SELECT_PREV",
            "TRACK_MUTE_TOGGLE",
            "TRACK_SOLO_TOGGLE",
            "LOOP_TOGGLE",
            "LOOP_IN_SET",
            "LOOP_OUT_SET",
            "LOOP_ENABLE",
            "LOOP_DISABLE",
            "ZOOM_IN",
            "ZOOM_OUT",
            "MOVE_LEFT",
            "MOVE_RIGHT",
        }:
            self._midi_engine.send_daw_action(action_upper)
            
        else:
            logger.warning(f"Unknown action: {action}")

    def _process_key_event(self, keycode: str, event_value: int) -> None:
        """
        Process a key event and route to MIDI or action.
        
        Resolution order (highest to lowest priority):
        1. Active Page's mappings (MIDI notes)
        2. Preset's global_actions (actions)
        3. Preset's global_mappings (MIDI notes/actions)
        4. Settings' app_global_mappings (MIDI notes/actions)
        
        Args:
            keycode: Keycode name (e.g., 'KEY_A')
            event_value: Event value (0=up, 1=down, 2=hold)
        """
        preset = self._state_manager.active_preset
        if not preset:
            logger.warning("No active preset configured")
            return

        is_pressed = event_value == KeyEvent.KEY_DOWN
        is_release = event_value == KeyEvent.KEY_UP

        # Skip key hold events
        if event_value == KeyEvent.KEY_HOLD:
            return

        # In passthrough mode, ignore note/action processing so keys behave normally
        # in other applications. Keep critical safety actions available on key down.
        if not self._state_manager.is_captured:
            if is_pressed:
                action = self._resolve_action_for_key(keycode, preset)
                if action in {
                    "TOGGLE_CAPTURE",
                    "PANIC",
                    "QUIT",
                    "PAGE_UP",
                    "PAGE_DOWN",
                    "VELOCITY_UP",
                    "VELOCITY_DOWN",
                }:
                    self._handle_action(action)
            return

        # Track if we found a mapping
        mapping_found = False
        current_page = preset.get_page(self._state_manager.current_page_index)
        
        # =====================================================================
        # 1. Check Active Page's mappings (highest priority)
        # =====================================================================
        if current_page and keycode in current_page.mappings:
            mapping = current_page.mappings[keycode]
            note = mapping.note
            channel = 0  # Default channel
            
            self._handle_note_event(note, is_pressed, channel)
            mapping_found = True
        
        # =====================================================================
        # 2. Check Preset's global_actions (actions that work on all pages)
        # =====================================================================
        elif keycode in preset.global_actions:
            mapping = preset.global_actions[keycode]
            # Actions only trigger on key down
            if is_pressed:
                self._handle_action(mapping.action)
            mapping_found = True
        
        # =====================================================================
        # 3. Check Preset's global_mappings (fallback mappings for preset)
        # =====================================================================
        elif keycode in preset.global_mappings:
            mapping = preset.global_mappings[keycode]
            self._handle_mapping(mapping, is_pressed)
            mapping_found = True
        
        # =====================================================================
        # 4. Check Settings' app_global_mappings (lowest priority, app-wide)
        # =====================================================================
        elif self._settings and keycode in self._settings.app_global_mappings:
            mapping = self._settings.app_global_mappings[keycode]
            self._handle_mapping(mapping, is_pressed)
            mapping_found = True
        
        # Notify callback if set
        if self._on_key_event and (is_pressed or is_release):
            self._on_key_event(keycode, is_pressed)

    def _resolve_action_for_key(self, keycode: str, preset: Preset) -> Optional[str]:
        """Resolve an action mapping for a key across preset/settings scopes."""
        if keycode in preset.global_actions:
            return preset.global_actions[keycode].action

        if keycode in preset.global_mappings:
            mapping = preset.global_mappings[keycode]
            if mapping.get("type") == "action":
                return mapping.get("action")

        if self._settings and keycode in self._settings.app_global_mappings:
            mapping = self._settings.app_global_mappings[keycode]
            if mapping.get("type") == "action":
                return mapping.get("action")

        return None
    
    def _handle_mapping(self, mapping: dict, is_pressed: bool) -> None:
        """
        Handle a mapping dictionary (can be note or action).
        
        Args:
            mapping: Mapping dictionary with 'type' and related fields
            is_pressed: True for key down, False for key up
        """
        mapping_type = mapping.get('type', 'note')
        
        if mapping_type == 'note':
            note = mapping.get('note', 60)
            channel = mapping.get('channel', 0)
            self._handle_note_event(note, is_pressed, channel)
            
        elif mapping_type == 'action':
            # Actions only trigger on key down
            if is_pressed:
                action = mapping.get('action', '')
                self._handle_action(action)
        else:
            logger.warning(f"Unknown mapping type: {mapping_type}")

    async def _event_loop(self) -> None:
        """
        Main event loop for reading and processing input events.
        
        This runs continuously until stop() is called or an error occurs.
        """
        try:
            self._last_start_error = None
            # Open the device
            self._device = self._open_device()
            
            # Initial grab state
            if self._state_manager.is_captured and not self._grab_device():
                raise RuntimeError(
                    self._last_start_error
                    or "Capture requested, but keyboard grab failed"
                )
            
            self._running = True
            logger.info(f"Started listening to {self._device.name}")
            self._startup_ready.set()

            # Main event loop
            async for event in self._device.async_read_loop():
                if not self._running:
                    break

                # Only process key events
                if event.type != ecodes.EV_KEY:
                    continue

                # Get keycode name
                keycode = self._get_keycode_name(event.code)
                if not keycode:
                    continue

                self._update_modifier_state(keycode, event.value)

                if self._handle_global_shortcuts(keycode, event.value):
                    continue

                # Process the key event
                self._process_key_event(keycode, event.value)

        except asyncio.CancelledError:
            logger.info("Input listener cancelled")
            
        except OSError as e:
            # Device disconnected or other I/O error
            logger.error(f"Device error: {e}")
            self._last_start_error = str(e)
            if self._on_device_error:
                self._on_device_error(e)
            # Send panic to prevent hanging notes
            self._midi_engine.panic()
            
        except Exception as e:
            logger.error(f"Unexpected error in input listener: {e}")
            self._last_start_error = str(e)
            if self._on_device_error:
                self._on_device_error(e)
            
        finally:
            self._startup_ready.set()
            self._cleanup()

    def _cleanup(self) -> None:
        """Clean up resources."""
        self._running = False
        
        # Ungrab device if grabbed
        if self._is_grabbed:
            try:
                self._ungrab_device()
            except Exception as e:
                logger.warning(f"Error ungrabbing device: {e}")
        
        # Device is closed automatically by async_read_loop context

    async def start(self) -> bool:
        """
        Start the input listener asynchronously.
        
        This creates a background task that reads events from the device.

        Returns:
            True if the listener reaches a running/ready state.
        """
        if self._running:
            logger.warning("Input listener already running")
            return True

        self._startup_ready.clear()
        self._last_start_error = None
        self._task = asyncio.create_task(self._event_loop())
        logger.info("Input listener start requested")

        try:
            await asyncio.wait_for(
                self._startup_ready.wait(),
                timeout=self._startup_timeout_seconds,
            )
        except asyncio.TimeoutError:
            self._last_start_error = (
                "Timed out waiting for input listener startup readiness"
            )
            logger.error(self._last_start_error)
            if self._task:
                self._task.cancel()
            self._running = False
            return False

        if not self._running:
            logger.error(
                "Input listener failed to start: %s",
                self._last_start_error or "unknown startup error",
            )
            return False

        logger.info("Input listener started")
        return True

    async def stop(self) -> None:
        """
        Stop the input listener.
        
        This cancels the background task and cleans up resources.
        """
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        # Send all notes off before stopping
        self._send_all_notes_off()
        logger.info("Input listener stopped")

    def sync_grab_state(self) -> bool:
        """Synchronize keyboard grab state with the current capture flag.

        Returns:
            True if requested mode is successfully applied.
        """
        return self._update_grab_state()

    async def __aenter__(self) -> "InputListener":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()


# =============================================================================
# Utility Functions
# =============================================================================

def list_input_devices() -> list[dict]:
    """
    List all available input devices.
    
    Returns:
        List of dictionaries with device info (path, name, capabilities)
    """
    devices = []
    
    for path in evdev.list_devices():
        try:
            device = InputDevice(path)
            devices.append({
                "path": path,
                "name": device.name,
                "phys": device.phys,
                "vendor": hex(device.info.vendor),
                "product": hex(device.info.product),
            })
        except Exception as e:
            logger.warning(f"Could not read device {path}: {e}")
    
    return devices


def find_keyboard_device() -> Optional[str]:
    """
    Find the first keyboard device automatically.
    
    Returns:
        Device path or None if no keyboard found
    """
    for path in evdev.list_devices():
        try:
            device = InputDevice(path)
            capabilities = device.capabilities()
            
            # Check if device has keys
            if ecodes.EV_KEY in capabilities:
                keys = capabilities[ecodes.EV_KEY]
                # Check for common keyboard keys
                if ecodes.KEY_A in keys or ecodes.KEY_Q in keys:
                    logger.info(f"Found keyboard device: {device.name} ({path})")
                    return path
                    
        except Exception as e:
            logger.debug(f"Could not check device {path}: {e}")
    
    logger.warning("No keyboard device found")
    return None
