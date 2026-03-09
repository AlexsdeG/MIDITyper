"""
State Manager module for tracking application state.

This module provides the StateManager class that tracks:
- Capture state (is_captured)
- Current page index (replaces octave shift)
- Active preset
- Velocity settings
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, Optional

from .config_parser import Preset

logger = logging.getLogger(__name__)


class CaptureState(Enum):
    """Enum for capture state."""
    CAPTURING = "CAPTURING"
    PASSTHROUGH = "PASSTHROUGH"


@dataclass
class StateManager:
    """
    Manages the application state including capture mode, current page,
    velocity, and active preset.
    
    Attributes:
        is_captured: Whether keyboard input is being captured for MIDI
        current_page_index: Current page index (0-based, replaces octave shift)
        active_preset: Currently active preset configuration
        current_velocity: Current note velocity (0-127)
        min_velocity: Minimum velocity (1-127), auto-clamped
        max_velocity: Maximum velocity (1-127), auto-clamped
    """
    
    # Core state
    is_captured: bool = True
    current_page_index: int = 0  # NEW: replaces current_octave_shift
    active_preset: Optional[Preset] = None
    
    # Velocity state
    current_velocity: int = 100
    velocity_step: int = 10
    
    # Limits - will be clamped to 1-127 in __setattr__
    min_velocity: int = 1
    max_velocity: int = 127
    
    # Callbacks for state change notifications
    _on_state_change: Optional[Callable] = field(default=None, repr=False)
    
    def __post_init__(self):
        """Initialize after dataclass creation."""
        # Track active notes for cleanup
        self._active_notes: Dict[int, int] = {}  # note -> channel
        
        # Clamp velocity limits to valid MIDI range (1-127)
        self.min_velocity = max(1, min(127, self.min_velocity))
        self.max_velocity = max(1, min(127, self.max_velocity))
    
    def __setattr__(self, name: str, value):
        """Override setattr to clamp velocity values to MIDI range."""
        if name in ('min_velocity', 'max_velocity') and not name.startswith('_'):
            # Clamp velocity to valid MIDI range (1-127)
            value = max(1, min(127, int(value)))
        object.__setattr__(self, name, value)

    @property
    def capture_state(self) -> CaptureState:
        """Get the current capture state as an enum."""
        return CaptureState.CAPTURING if self.is_captured else CaptureState.PASSTHROUGH

    @property
    def capture_state_str(self) -> str:
        """Get the current capture state as a string."""
        return self.capture_state.value
    
    @property
    def page_count(self) -> int:
        """Get the total number of pages in the active preset."""
        if self.active_preset:
            return self.active_preset.page_count
        return 1
    
    @property
    def current_page_name(self) -> str:
        """Get the name of the current page."""
        if self.active_preset:
            page = self.active_preset.get_page(self.current_page_index)
            if page:
                return page.name
        return f"Page {self.current_page_index + 1}"
    
    @property
    def has_multiple_pages(self) -> bool:
        """Check if the active preset has multiple pages."""
        if self.active_preset:
            return self.active_preset.has_multiple_pages
        return False

    def toggle_capture(self) -> bool:
        """
        Toggle between capture and passthrough mode.
        
        Returns:
            New capture state (True = capturing, False = passthrough)
        """
        self.is_captured = not self.is_captured
        logger.info(f"Capture state toggled: {self.capture_state_str}")
        self._notify_state_change()
        return self.is_captured

    def set_capture(self, captured: bool) -> None:
        """
        Set the capture state explicitly.
        
        Args:
            captured: True for capture mode, False for passthrough
        """
        if self.is_captured != captured:
            self.is_captured = captured
            logger.info(f"Capture state set: {self.capture_state_str}")
            self._notify_state_change()

    def next_page(self) -> int:
        """
        Go to the next page.
        
        Returns:
            New page index
        """
        if self.active_preset and self.current_page_index < self.active_preset.page_count - 1:
            self.current_page_index += 1
            logger.info(f"Page: {self.current_page_name} (index {self.current_page_index})")
            self._notify_state_change()
        else:
            logger.debug(f"Already at last page (index {self.current_page_index})")
        return self.current_page_index

    def prev_page(self) -> int:
        """
        Go to the previous page.
        
        Returns:
            New page index
        """
        if self.current_page_index > 0:
            self.current_page_index -= 1
            logger.info(f"Page: {self.current_page_name} (index {self.current_page_index})")
            self._notify_state_change()
        else:
            logger.debug(f"Already at first page (index {self.current_page_index})")
        return self.current_page_index

    def set_page(self, index: int) -> None:
        """
        Set the current page index.
        
        Args:
            index: Page index (0-based)
        """
        if self.active_preset and 0 <= index < self.active_preset.page_count:
            self.current_page_index = index
            logger.info(f"Page set: {self.current_page_name} (index {index})")
            self._notify_state_change()

    def reset_page(self) -> None:
        """Reset to first page."""
        self.current_page_index = 0
        logger.info("Reset to first page")
        self._notify_state_change()

    def velocity_up(self) -> int:
        """
        Increase velocity by the step amount.
        
        Returns:
            New velocity value
        """
        new_velocity = min(self.max_velocity, self.current_velocity + self.velocity_step)
        if new_velocity != self.current_velocity:
            self.current_velocity = new_velocity
            logger.info(f"Velocity: {self.current_velocity}")
            self._notify_state_change()
        return self.current_velocity

    def velocity_down(self) -> int:
        """
        Decrease velocity by the step amount.
        
        Returns:
            New velocity value
        """
        new_velocity = max(self.min_velocity, self.current_velocity - self.velocity_step)
        if new_velocity != self.current_velocity:
            self.current_velocity = new_velocity
            logger.info(f"Velocity: {self.current_velocity}")
            self._notify_state_change()
        return self.current_velocity

    def set_velocity(self, velocity: int) -> None:
        """
        Set velocity directly.
        
        Args:
            velocity: Velocity value (1-127)
        """
        self.current_velocity = max(self.min_velocity, min(self.max_velocity, velocity))
        logger.info(f"Velocity set: {self.current_velocity}")
        self._notify_state_change()

    def set_active_preset(self, preset: Preset) -> None:
        """
        Set the active preset.
        
        Args:
            preset: Preset configuration to activate
        """
        self.active_preset = preset
        # Reset to first page when changing preset
        self.current_page_index = 0
        logger.info(f"Active preset: {preset.name}")
        self._notify_state_change()

    def register_note_on(self, note: int, channel: int) -> None:
        """
        Register an active note for tracking.
        
        Args:
            note: MIDI note number
            channel: MIDI channel
        """
        self._active_notes[note] = channel

    def register_note_off(self, note: int) -> None:
        """
        Remove a note from active tracking.
        
        Args:
            note: MIDI note number
        """
        self._active_notes.pop(note, None)

    def get_active_notes(self) -> Dict[int, int]:
        """
        Get all currently active notes.
        
        Returns:
            Dictionary mapping note numbers to channels
        """
        return self._active_notes.copy()

    def clear_active_notes(self) -> Dict[int, int]:
        """
        Clear all active note tracking and return the cleared notes.
        
        Returns:
            Dictionary of notes that were cleared (for sending Note Off)
        """
        notes = self._active_notes.copy()
        self._active_notes.clear()
        return notes

    def has_active_notes(self) -> bool:
        """Check if there are any active notes."""
        return len(self._active_notes) > 0

    def set_state_change_callback(self, callback: Callable) -> None:
        """
        Set a callback to be called when state changes.
        
        Args:
            callback: Function to call on state change
        """
        self._on_state_change = callback

    def _notify_state_change(self) -> None:
        """Notify listeners of state change."""
        if self._on_state_change is not None:
            try:
                self._on_state_change(self)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")

    def get_state_summary(self) -> Dict:
        """
        Get a summary of the current state.
        
        Returns:
            Dictionary with state summary
        """
        return {
            "capture_state": self.capture_state_str,
            "current_page_index": self.current_page_index,
            "current_page_name": self.current_page_name,
            "total_pages": self.page_count,
            "velocity": self.current_velocity,
            "preset_name": self.active_preset.name if self.active_preset else None,
            "active_notes": len(self._active_notes)
        }

    def __str__(self) -> str:
        """String representation of the state."""
        return (
            f"StateManager(capture={self.capture_state_str}, "
            f"page={self.current_page_index}/{self.page_count}, "
            f"velocity={self.current_velocity}, "
            f"preset={self.active_preset.name if self.active_preset else 'None'})"
        )
