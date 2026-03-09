"""
MIDI Engine module for creating and managing virtual MIDI ports.

This module provides the MidiEngine class that handles all MIDI output
operations including note on/off messages and panic functionality.
Includes support for randomized velocity ranges.
"""

import logging
import random
from typing import Optional

import mido
from mido.ports import BaseOutput

logger = logging.getLogger(__name__)


class MidiEngine:
    """
    MIDI engine that manages a virtual MIDI port for sending MIDI messages.

    This class provides methods to:
    - Open a virtual MIDI port (ALSA/JACK compatible)
    - Send Note On/Off messages with random velocity support
    - Send panic (all notes off) messages
    - Close the port cleanly
    """

    def __init__(
        self,
        port_name: str = "MIDITyper",
        default_channel: int = 0,
        default_velocity: int = 100,
        min_velocity: int = 100,
        max_velocity: int = 100
    ):
        """
        Initialize the MIDI engine and open a virtual port.

        Args:
            port_name: Name for the virtual MIDI port
            default_channel: Default MIDI channel (0-15)
            default_velocity: Default note velocity (0-127) - used when min=max
            min_velocity: Minimum velocity for random range (0-127)
            max_velocity: Maximum velocity for random range (0-127)

        Raises:
            OSError: If the MIDI backend fails to initialize
        """
        self._port_name = port_name
        self._default_channel = default_channel
        self._default_velocity = default_velocity
        self._min_velocity = min_velocity
        self._max_velocity = max_velocity
        self._port: Optional[BaseOutput] = None
        self._active_notes: set[tuple[int, int]] = set()  # (note, channel) pairs

        # Open the virtual port
        self._open_port()

    def _open_port(self) -> None:
        """Open the virtual MIDI output port."""
        try:
            self._port = mido.open_output(
                self._port_name,
                virtual=True,
                autoreset=True
            )
            logger.info(f"Opened virtual MIDI port: {self._port_name}")
        except OSError as e:
            logger.error(f"Failed to open virtual MIDI port: {e}")
            raise

    @property
    def port_name(self) -> str:
        """Get the name of the virtual port."""
        return self._port_name

    @property
    def is_open(self) -> bool:
        """Check if the MIDI port is open."""
        return self._port is not None and not self._port.closed

    def set_velocity_range(self, min_vel: int, max_vel: int) -> None:
        """
        Set the velocity range for random velocity.
        
        Args:
            min_vel: Minimum velocity (1-127)
            max_vel: Maximum velocity (1-127)
        """
        self._min_velocity = max(1, min(127, min_vel))
        self._max_velocity = max(1, min(127, max_vel))
        logger.debug(f"Velocity range set to: {self._min_velocity}-{self._max_velocity}")

    def get_random_velocity(self) -> int:
        """
        Get a velocity value, either fixed or random based on min/max settings.
        
        When min == max, returns that fixed value.
        When min != max, returns a random value between min and max (inclusive).
        Handles the case where min > max by swapping them.
        
        Returns:
            Velocity value between 1 and 127
        """
        if self._min_velocity == self._max_velocity:
            return self._min_velocity
        
        # Handle inverted range (min > max) by swapping
        min_vel = min(self._min_velocity, self._max_velocity)
        max_vel = max(self._min_velocity, self._max_velocity)
        
        return random.randint(min_vel, max_vel)

    def send_note_on(
        self,
        note: int,
        velocity: Optional[int] = None,
        channel: Optional[int] = None,
        use_random_velocity: bool = True
    ) -> int:
        """
        Send a MIDI Note On message.

        Args:
            note: MIDI note number (0-127)
            velocity: Note velocity (0-127), uses random if not specified and use_random_velocity=True
            channel: MIDI channel (0-15), uses default if not specified
            use_random_velocity: If True and velocity is None, use random velocity from range

        Returns:
            The actual velocity used

        Raises:
            ValueError: If note, velocity, or channel is out of range
        """
        if not self.is_open:
            logger.warning("Cannot send Note On: MIDI port is not open")
            return 0

        # Determine velocity
        if velocity is None:
            if use_random_velocity:
                velocity = self.get_random_velocity()
            else:
                velocity = self._default_velocity
        
        channel = channel if channel is not None else self._default_channel

        # Validate ranges
        if not 0 <= note <= 127:
            raise ValueError(f"Note must be 0-127, got {note}")
        if not 0 <= velocity <= 127:
            raise ValueError(f"Velocity must be 0-127, got {velocity}")
        if not 0 <= channel <= 15:
            raise ValueError(f"Channel must be 0-15, got {channel}")

        # Create and send the message
        msg = mido.Message(
            'note_on',
            note=note,
            velocity=velocity,
            channel=channel
        )
        self._port.send(msg)

        # Track active note
        self._active_notes.add((note, channel))

        logger.debug(f"Note On: note={note}, velocity={velocity}, channel={channel}")

        return velocity

    def send_note_off(
        self,
        note: int,
        channel: Optional[int] = None
    ) -> None:
        """
        Send a MIDI Note Off message.

        Args:
            note: MIDI note number (0-127)
            channel: MIDI channel (0-15), uses default if not specified

        Raises:
            ValueError: If note or channel is out of range
        """
        if not self.is_open:
            logger.warning("Cannot send Note Off: MIDI port is not open")
            return

        channel = channel if channel is not None else self._default_channel

        # Validate ranges
        if not 0 <= note <= 127:
            raise ValueError(f"Note must be 0-127, got {note}")
        if not 0 <= channel <= 15:
            raise ValueError(f"Channel must be 0-15, got {channel}")

        # Create and send the message
        msg = mido.Message(
            'note_off',
            note=note,
            velocity=0,
            channel=channel
        )
        self._port.send(msg)

        # Remove from active notes
        self._active_notes.discard((note, channel))

        logger.debug(f"Note Off: note={note}, channel={channel}")

    def send_control_change(
        self,
        control: int,
        value: int,
        channel: Optional[int] = None
    ) -> None:
        """
        Send a MIDI Control Change message.

        Args:
            control: Controller number (0-127)
            value: Controller value (0-127)
            channel: MIDI channel (0-15), uses default if not specified
        """
        if not self.is_open:
            logger.warning("Cannot send CC: MIDI port is not open")
            return

        channel = channel if channel is not None else self._default_channel

        msg = mido.Message(
            'control_change',
            control=control,
            value=value,
            channel=channel
        )
        self._port.send(msg)

        logger.debug(f"CC: control={control}, value={value}, channel={channel}")

    def panic(self) -> None:
        """
        Send panic message: All Notes Off for all channels.

        This sends Note Off for all 128 notes across all 16 channels
        to immediately stop any hanging notes.
        """
        if not self.is_open:
            logger.warning("Cannot send panic: MIDI port is not open")
            return

        logger.info("Sending panic: All Notes Off")

        # Send Note Off for all notes on all channels
        for channel in range(16):
            # Method 1: All Notes Off CC (CC 123)
            self._port.send(mido.Message(
                'control_change',
                control=123,
                value=0,
                channel=channel
            ))

            # Method 2: Explicit Note Off for all notes (belt and suspenders)
            for note in range(128):
                self._port.send(mido.Message(
                    'note_off',
                    note=note,
                    velocity=0,
                    channel=channel
                ))

        # Clear active notes tracking
        self._active_notes.clear()

        logger.info("Panic complete: All notes off sent")

    def all_sounds_off(self) -> None:
        """
        Send All Sounds Off CC message (CC 120) for all channels.

        This is a more aggressive version that stops sounds immediately,
        even if sustain pedal is held.
        """
        if not self.is_open:
            return

        for channel in range(16):
            self._port.send(mido.Message(
                'control_change',
                control=120,
                value=0,
                channel=channel
            ))

        self._active_notes.clear()
        logger.info("All Sounds Off sent")

    def reset_all_controllers(self) -> None:
        """
        Send Reset All Controllers CC message (CC 121) for all channels.
        """
        if not self.is_open:
            return

        for channel in range(16):
            self._port.send(mido.Message(
                'control_change',
                control=121,
                value=0,
                channel=channel
            ))

        logger.info("Reset All Controllers sent")

    def get_active_notes(self) -> set[tuple[int, int]]:
        """
        Get the set of currently active (playing) notes.

        Returns:
            Set of (note, channel) tuples for active notes
        """
        return self._active_notes.copy()

    def note_off_active_notes(self) -> None:
        """
        Send Note Off for all currently tracked active notes.

        This is useful before toggling passthrough mode to prevent
        hanging notes in the DAW.
        """
        if not self.is_open:
            return

        # Copy the set since we'll be modifying it
        notes_to_kill = self._active_notes.copy()

        for note, channel in notes_to_kill:
            self.send_note_off(note, channel)

        logger.info(f"Sent Note Off for {len(notes_to_kill)} active notes")

    def close(self) -> None:
        """Close the MIDI port and clean up resources."""
        if self._port is not None and not self._port.closed:
            # Send panic before closing
            self.panic()
            self._port.close()
            logger.info(f"Closed MIDI port: {self._port_name}")

        self._port = None
        self._active_notes.clear()

    def __enter__(self) -> "MidiEngine":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - close port."""
        self.close()

    def __del__(self) -> None:
        """Destructor - ensure port is closed."""
        self.close()
