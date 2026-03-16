"""Shared mapping dialogs and key normalization helpers.

This module provides reusable modal dialogs for key mapping CRUD flows across
settings and preset editor screens.
"""

from __future__ import annotations

import re
from typing import Dict, Optional

from evdev import ecodes
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select

from ..action_catalog import get_action_select_options


_VALID_ECODES: set[str] = {
    name for name in ecodes.ecodes.keys() if isinstance(name, str)
}

_TEXTUAL_KEY_ALIASES: dict[str, str] = {
    "escape": "KEY_ESC",
    "enter": "KEY_ENTER",
    "tab": "KEY_TAB",
    "space": "KEY_SPACE",
    "backspace": "KEY_BACKSPACE",
    "delete": "KEY_DELETE",
    "insert": "KEY_INSERT",
    "home": "KEY_HOME",
    "end": "KEY_END",
    "up": "KEY_UP",
    "down": "KEY_DOWN",
    "left": "KEY_LEFT",
    "right": "KEY_RIGHT",
    "pageup": "KEY_PAGEUP",
    "pagedown": "KEY_PAGEDOWN",
    "minus": "KEY_MINUS",
    "equals": "KEY_EQUAL",
    "comma": "KEY_COMMA",
    "period": "KEY_DOT",
    "slash": "KEY_SLASH",
    "semicolon": "KEY_SEMICOLON",
    "apostrophe": "KEY_APOSTROPHE",
    "grave": "KEY_GRAVE",
    "left_square_bracket": "KEY_LEFTBRACE",
    "right_square_bracket": "KEY_RIGHTBRACE",
    "backslash": "KEY_BACKSLASH",
}


def normalize_key_name(key_input: str) -> Optional[str]:
    """Normalize key input to a valid evdev key symbol.

    The function accepts full evdev symbol names (e.g. ``KEY_A``, ``BTN_SOUTH``,
    ``ABS_X``), plus short keyboard aliases (e.g. ``A`` -> ``KEY_A``).

    Args:
        key_input: User-entered key text.

    Returns:
        Normalized evdev symbol when valid, else ``None``.
    """
    if not key_input:
        return None

    candidate = key_input.strip().upper()
    if not candidate:
        return None

    if candidate in _VALID_ECODES:
        return candidate

    key_prefixed = f"KEY_{candidate}"
    if key_prefixed in _VALID_ECODES:
        return key_prefixed

    btn_prefixed = f"BTN_{candidate}"
    if btn_prefixed in _VALID_ECODES:
        return btn_prefixed

    return None


def mapping_summary(mapping: Dict) -> str:
    """Build a short human-readable mapping summary.

    Args:
        mapping: Mapping dictionary with ``type`` and payload fields.

    Returns:
        Summary for notifications/confirm dialogs.
    """
    mapping_type = mapping.get("type")
    if mapping_type == "note":
        note = mapping.get("note", "?")
        name = mapping.get("name", "")
        if name:
            return f"Note {note} ({name})"
        return f"Note {note}"

    action = mapping.get("action", "?")
    return f"Action {action}"


def textual_key_to_evdev(key: str) -> Optional[str]:
    """Convert a Textual key string to an evdev key symbol.

    Args:
        key: Textual key string, e.g. ``escape`` or ``a``.

    Returns:
        Normalized evdev symbol when conversion succeeds, else ``None``.
    """
    if not key:
        return None

    lowered = key.lower().strip()
    lowered = lowered.split("+")[-1]

    if lowered in _TEXTUAL_KEY_ALIASES:
        return _TEXTUAL_KEY_ALIASES[lowered]

    function_match = re.fullmatch(r"f(\d{1,2})", lowered)
    if function_match:
        return normalize_key_name(f"KEY_F{function_match.group(1)}")

    if len(lowered) == 1 and lowered.isalnum():
        return normalize_key_name(f"KEY_{lowered.upper()}")

    return normalize_key_name(lowered)


class ConfirmOverwriteDialog(ModalScreen[bool]):
    """Confirmation dialog for duplicate key overwrite operations."""

    CSS = """
    ConfirmOverwriteDialog {
        align: center middle;
    }

    #confirm-dialog {
        width: 68;
        height: auto;
        padding: 1;
        background: $surface;
        border: thick $warning;
    }

    #confirm-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #confirm-message {
        margin-bottom: 1;
    }

    #confirm-buttons {
        align: center middle;
    }

    #confirm-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Confirm"),
    ]

    def __init__(self, title: str, message: str):
        super().__init__()
        self._title = title
        self._message = message

    def compose(self) -> ComposeResult:
        with Container(id="confirm-dialog"):
            yield Label(self._title, id="confirm-title")
            yield Label(self._message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button("Replace", variant="warning", id="btn-confirm")
                yield Button("Cancel", variant="error", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-confirm":
            self.action_confirm()
        else:
            self.action_cancel()

    def action_confirm(self) -> None:
        """Confirm overwrite."""
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel overwrite."""
        self.dismiss(False)


class KeyMappingDialog(ModalScreen[Optional[Dict]]):
    """Reusable dialog for adding/editing key mappings with key auto-detect."""

    CSS = """
    KeyMappingDialog {
        align: center middle;
    }

    #mapping-dialog {
        width: 70;
        height: auto;
        padding: 1;
        background: $surface;
        border: thick $primary;
    }

    #dialog-title {
        text-style: bold;
        margin-bottom: 1;
    }

    .dialog-row {
        margin-bottom: 1;
    }

    .dialog-label {
        color: $text-muted;
        margin-bottom: 0;
    }

    #detect-status {
        color: $warning;
        min-height: 1;
    }

    #key-row {
        height: auto;
        align: left middle;
    }

    #key-input {
        width: 1fr;
        min-width: 20;
    }

    #btn-detect {
        width: 20;
        margin-left: 1;
    }

    #dialog-buttons {
        align: center middle;
        margin-top: 1;
    }

    #dialog-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS: list[Binding] = []

    def __init__(
        self,
        *,
        title: str,
        edit_mode: bool = False,
        initial_key: str = "",
        initial_mapping: Optional[Dict] = None,
        action_only: bool = False,
    ):
        super().__init__()
        self._title = title
        self._edit_mode = edit_mode
        self._initial_key = initial_key
        self._initial_mapping = initial_mapping or {
            "type": "action",
            "action": "TOGGLE_CAPTURE",
        }
        self._action_only = action_only
        self._detect_armed = False

    def compose(self) -> ComposeResult:
        mapping_type = "action" if self._action_only else self._initial_mapping.get(
            "type", "action"
        )

        with Container(id="mapping-dialog"):
            yield Label(self._title, id="dialog-title")

            with Vertical(classes="dialog-row"):
                yield Label("Key Code (e.g., KEY_A, BTN_SOUTH):", classes="dialog-label")
                with Horizontal(id="key-row"):
                    yield Input(
                        value=self._initial_key,
                        placeholder="KEY_A",
                        id="key-input",
                    )
                    yield Button("Detect Pressed Key", id="btn-detect", variant="primary")
                yield Label("", id="detect-status")

            with Vertical(classes="dialog-row", id="mapping-type-row"):
                yield Label("Mapping Type:", classes="dialog-label")
                yield Select(
                    options=[("MIDI Note", "note"), ("Action", "action")],
                    value=mapping_type,
                    id="mapping-type-select",
                )

            with Vertical(classes="dialog-row", id="note-config"):
                yield Label("MIDI Note Number (0-127):", classes="dialog-label")
                yield Input(str(self._initial_mapping.get("note", 60)), id="note-input")
                yield Label("Note Name (display):", classes="dialog-label")
                yield Input(self._initial_mapping.get("name", "C4"), id="note-name-input")

            with Vertical(classes="dialog-row", id="action-config"):
                yield Label("Action:", classes="dialog-label")
                yield Select(
                    options=get_action_select_options(),
                    value=self._initial_mapping.get("action", "TOGGLE_CAPTURE"),
                    id="action-select",
                )

            with Horizontal(id="dialog-buttons"):
                yield Button("Save", variant="success", id="btn-confirm")
                yield Button("Cancel", variant="error", id="btn-cancel")

    def on_mount(self) -> None:
        """Initialize dialog state."""
        if self._action_only:
            self.query_one("#mapping-type-row", Vertical).display = False
        self._update_visibility()
        self.query_one("#key-input", Input).focus()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select updates."""
        if event.select.id == "mapping-type-select":
            self._update_visibility()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-confirm":
            self.action_confirm()
        elif event.button.id == "btn-cancel":
            self.action_cancel()
        elif event.button.id == "btn-detect":
            self._toggle_detect_mode()

    def on_key(self, event: events.Key) -> None:
        """Capture next pressed key when detect mode is armed."""
        if not self._detect_armed:
            return

        detected = textual_key_to_evdev(event.key)
        if not detected and event.character:
            detected = textual_key_to_evdev(event.character)
        if not detected:
            self.query_one("#detect-status", Label).update(
                f"Unsupported key '{event.key}'. Try another key."
            )
            event.stop()
            return

        self.query_one("#key-input", Input).value = detected
        self._detect_armed = False
        self.query_one("#detect-status", Label).update(
            f"Detected and set key: {detected}"
        )
        self._update_detect_button()
        self.query_one("#key-input", Input).focus()
        event.stop()

    def action_confirm(self) -> None:
        """Validate and return mapping payload."""
        raw_key = self.query_one("#key-input", Input).value
        key_name = normalize_key_name(raw_key)
        if not key_name:
            self.notify("Valid evdev key code is required", severity="error")
            return

        mapping_type = "action"
        if not self._action_only:
            mapping_type = self.query_one("#mapping-type-select", Select).value

        if mapping_type == "note":
            try:
                note = int(self.query_one("#note-input", Input).value)
            except ValueError:
                self.notify("Valid note number (0-127) required", severity="error")
                return
            if note < 0 or note > 127:
                self.notify("Valid note number (0-127) required", severity="error")
                return
            note_name = self.query_one("#note-name-input", Input).value.strip() or f"Note {note}"
            mapping = {"type": "note", "note": note, "name": note_name}
        else:
            action = self.query_one("#action-select", Select).value
            mapping = {"type": "action", "action": action}

        self.dismiss(
            {
                "original_key": self._initial_key,
                "key": key_name,
                "mapping": mapping,
                "edit_mode": self._edit_mode,
            }
        )

    def action_cancel(self) -> None:
        """Close without saving."""
        self.dismiss(None)

    def _update_visibility(self) -> None:
        """Show/hide note/action config sections."""
        note_config = self.query_one("#note-config", Vertical)
        action_config = self.query_one("#action-config", Vertical)

        mapping_type = "action"
        if not self._action_only:
            mapping_type = self.query_one("#mapping-type-select", Select).value

        note_config.display = mapping_type == "note"
        action_config.display = mapping_type == "action"

    def _toggle_detect_mode(self) -> None:
        """Arm/disarm next-key detection mode."""
        self._detect_armed = not self._detect_armed
        status = self.query_one("#detect-status", Label)
        if self._detect_armed:
            status.update("Detection armed: press the next key now.")
        else:
            status.update("Detection cancelled.")
        self._update_detect_button()

    def _update_detect_button(self) -> None:
        """Update detect button label and style for current mode."""
        detect_button = self.query_one("#btn-detect", Button)
        if self._detect_armed:
            detect_button.label = "Cancel Detect"
            detect_button.variant = "warning"
        else:
            detect_button.label = "Detect Pressed Key"
            detect_button.variant = "primary"
