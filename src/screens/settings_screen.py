"""
Settings Screen for MIDITyper.

This screen allows users to configure:
- Input device selection
- Virtual MIDI port name
- Theme settings
- App-Global Keybinds (new)
"""

from pathlib import Path
from typing import Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen, ModalScreen
from textual.widgets import (
    Button, Header, Footer, Static, Label, Input, Select,
    DataTable, TabbedContent, TabPane
)
from textual.reactive import reactive
from textual.binding import Binding

from ..input_listener import list_input_devices


class AddGlobalMappingDialog(ModalScreen):
    """Modal dialog for adding or editing an app-global key mapping."""

    CSS = """
    AddGlobalMappingDialog {
        align: center middle;
    }

    #dialog {
        width: 50;
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

    #button-row {
        align: center middle;
        margin-top: 1;
    }

    #button-row Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Save"),
    ]

    def __init__(
        self,
        *,
        edit_mode: bool = False,
        initial_key: str = "",
        initial_mapping: Optional[Dict] = None,
    ):
        super().__init__()
        self._edit_mode = edit_mode
        self._initial_key = initial_key
        self._initial_mapping = initial_mapping or {"type": "action", "action": "TOGGLE_CAPTURE"}

    def compose(self) -> ComposeResult:
        title = "Edit App-Global Keybind" if self._edit_mode else "Add App-Global Keybind"
        action_label = "Save" if self._edit_mode else "Add"

        with Container(id="dialog"):
            yield Label(title, id="dialog-title")

            with Vertical(classes="dialog-row"):
                yield Label("Key Code (e.g., KEY_F12):", classes="dialog-label")
                yield Input(
                    value=self._initial_key,
                    placeholder="KEY_F12",
                    id="key-input",
                    disabled=self._edit_mode,
                )

            mapping_type = self._initial_mapping.get("type", "action")
            with Vertical(classes="dialog-row"):
                yield Label("Mapping Type:", classes="dialog-label")
                yield Select(
                    options=[
                        ("MIDI Note", "note"),
                        ("Action", "action"),
                    ],
                    value=mapping_type,
                    id="mapping-type-select"
                )

            with Vertical(classes="dialog-row", id="note-config"):
                yield Label("MIDI Note Number (0-127):", classes="dialog-label")
                yield Input(str(self._initial_mapping.get("note", 60)), id="note-input")
                yield Label("Note Name (display):", classes="dialog-label")
                yield Input(self._initial_mapping.get("name", "C4"), id="note-name-input")

            with Vertical(classes="dialog-row", id="action-config"):
                yield Label("Action:", classes="dialog-label")
                yield Select(
                    options=[
                        ("Toggle Capture", "TOGGLE_CAPTURE"),
                        ("Page Up", "PAGE_UP"),
                        ("Page Down", "PAGE_DOWN"),
                        ("Panic", "PANIC"),
                        ("Velocity Up", "VELOCITY_UP"),
                        ("Velocity Down", "VELOCITY_DOWN"),
                        ("Quit", "QUIT"),
                        ("Track Select Next", "TRACK_SELECT_NEXT"),
                        ("Track Select Previous", "TRACK_SELECT_PREV"),
                        ("Track Mute Toggle", "TRACK_MUTE_TOGGLE"),
                        ("Track Solo Toggle", "TRACK_SOLO_TOGGLE"),
                        ("Loop Toggle", "LOOP_TOGGLE"),
                        ("Set Loop In", "LOOP_IN_SET"),
                        ("Set Loop Out", "LOOP_OUT_SET"),
                        ("Loop Enable", "LOOP_ENABLE"),
                        ("Loop Disable", "LOOP_DISABLE"),
                        ("Zoom In", "ZOOM_IN"),
                        ("Zoom Out", "ZOOM_OUT"),
                        ("Move Left", "MOVE_LEFT"),
                        ("Move Right", "MOVE_RIGHT"),
                    ],
                    value=self._initial_mapping.get("action", "TOGGLE_CAPTURE"),
                    id="action-select"
                )

            with Horizontal(id="button-row"):
                yield Button(action_label, variant="success", id="btn-confirm")
                yield Button("Cancel", variant="error", id="btn-cancel")

    def on_mount(self) -> None:
        """Initialize the dialog."""
        self._update_visibility()
        if self._edit_mode:
            self.query_one("#mapping-type-select", Select).focus()
        else:
            self.query_one("#key-input", Input).focus()

    def _update_visibility(self) -> None:
        """Show/hide config sections based on mapping type."""
        try:
            note_config = self.query_one("#note-config", Vertical)
            action_config = self.query_one("#action-config", Vertical)
            mapping_type = self.query_one("#mapping-type-select", Select).value

            if mapping_type == "note":
                note_config.display = True
                action_config.display = False
            else:
                note_config.display = False
                action_config.display = True
        except Exception:
            pass

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select widget changes."""
        if event.select.id == "mapping-type-select":
            self._update_visibility()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-confirm":
            self.action_confirm()
        elif event.button.id == "btn-cancel":
            self.action_cancel()

    def action_confirm(self) -> None:
        """Confirm and return the mapping."""
        if self._edit_mode:
            key = self._initial_key
        else:
            key = self.query_one("#key-input", Input).value.strip().upper()
            if not key:
                self.notify("Key code is required", severity="error")
                return

        mapping_type = self.query_one("#mapping-type-select", Select).value

        if mapping_type == "note":
            try:
                note = int(self.query_one("#note-input", Input).value)
                if not (0 <= note <= 127):
                    raise ValueError("Note out of range")
            except ValueError:
                self.notify("Valid note number (0-127) required", severity="error")
                return

            note_name = self.query_one("#note-name-input", Input).value.strip() or f"Note {note}"
            result = {
                "type": "note",
                "note": note,
                "name": note_name
            }
        else:
            action = self.query_one("#action-select", Select).value
            result = {
                "type": "action",
                "action": action
            }

        self.dismiss((key, result))

    def action_cancel(self) -> None:
        """Cancel and close."""
        self.dismiss(None)


class SettingsScreen(Screen):
    """
    Settings screen for configuring MIDITyper.
    
    Features:
    - Device selection from available input devices
    - MIDI port configuration (Select widget with options)
    - Auto-detect toggle (Select widget)
    - Theme toggle
    - App-Global Keybinds management
    """
    
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("ctrl+s", "save", "Save"),
    ]
    
    # Reactive settings
    device_path: reactive[str] = reactive("")
    port_name: reactive[str] = reactive("MIDITyper")
    auto_detect: reactive[bool] = reactive(True)
    theme: reactive[str] = reactive("dark")
    min_velocity: reactive[int] = reactive(100)
    max_velocity: reactive[int] = reactive(100)
    
    def __init__(self):
        super().__init__()
        self._devices: List[tuple] = []
        self._port_options: List[tuple] = []
        self._global_key_rows: List[str] = []
    
    def compose(self) -> ComposeResult:
        """Create the settings screen layout."""
        yield Header()
        
        yield Label("⚙ Settings", id="title")
        
        with TabbedContent():
            # General Settings Tab
            with TabPane("General Settings", id="general-tab"):
                with Vertical(id="settings-container"):
                    # Device Selection
                    with Container(classes="setting-row"):
                        yield Label("Input Device:", classes="setting-label")
                        yield Select(
                            options=self._get_device_options(),
                            id="device-select",
                            classes="setting-widget"
                        )
                        yield Static("", id="device-info")
                    
                    # MIDI Port Configuration
                    with Container(classes="setting-row"):
                        yield Label("Virtual MIDI Port:", classes="setting-label")
                        yield Select(
                            options=self._get_port_options(),
                            id="port-select",
                            classes="setting-widget"
                        )
                    
                    # Auto-detect Keyboard
                    with Container(classes="setting-row"):
                        yield Label("Auto-detect Keyboard:", classes="setting-label")
                        yield Select(
                            options=[
                                ("Enabled", True),
                                ("Disabled", False),
                            ],
                            value=True,
                            id="auto-detect-select",
                            classes="setting-widget"
                        )
                    
                    # Theme Selection
                    with Container(classes="setting-row"):
                        yield Label("Theme:", classes="setting-label")
                        yield Select(
                            options=[("Dark", "dark"), ("Light", "light")],
                            value="dark",
                            id="theme-select",
                            classes="setting-widget"
                        )
                    
                    # Velocity Range
                    with Container(classes="setting-row"):
                        yield Label("Min Velocity:", classes="setting-label")
                        yield Select(
                            options=[(str(i), i) for i in list(range(1, 128, 10)) + [100]],
                            value=100,
                            id="min-velocity-select",
                            classes="setting-widget"
                        )
                    
                    with Container(classes="setting-row"):
                        yield Label("Max Velocity:", classes="setting-label")
                        yield Select(
                            options=[(str(i), i) for i in list(range(1, 128, 10)) + [100]],
                            value=100,
                            id="max-velocity-select",
                            classes="setting-widget"
                        )
            
            # App-Global Keybinds Tab
            with TabPane("App-Global Keybinds", id="keybinds-tab"):
                with Vertical(id="keybinds-container"):
                    with Container(id="global-keybinds-section"):
                        yield Label("App-Global Keybinds", id="global-keybinds-title")
                        yield DataTable(
                            id="global-keybinds-table",
                            show_header=True,
                            zebra_stripes=True
                        )
                        with Horizontal(id="global-keybinds-buttons"):
                            yield Button("+ Add", variant="success", id="btn-add-global")
                            yield Button("Edit", variant="primary", id="btn-edit-global")
                            yield Button("- Delete", variant="warning", id="btn-delete-global")
        
        yield Footer()
    
    def _get_device_options(self) -> List[tuple]:
        """Get available input devices for the select widget."""
        options = [("-- Auto-detect --", "")]
        
        try:
            # Try to list devices from /dev/input/by-id/
            by_id_path = Path("/dev/input/by-id/")
            if by_id_path.exists():
                for device in sorted(by_id_path.iterdir()):
                    if device.is_symlink():
                        device_name = device.name
                        device_path = str(device)
                        options.append((device_name, device_path))
            
            # Also check /dev/input/by-path/
            by_path_path = Path("/dev/input/by-path/")
            if by_path_path.exists():
                for device in sorted(by_path_path.iterdir()):
                    if device.is_symlink() and "event-kbd" in device.name:
                        device_name = device.name
                        device_path = str(device)
                        if (device_name, device_path) not in options[1:]:
                            options.append((device_name, device_path))

            seen_paths = {path for _, path in options}
            for device in list_input_devices():
                event_path = device.get("path", "")
                if event_path and event_path not in seen_paths:
                    options.append((f"{device.get('name', 'Unknown')} ({event_path})", event_path))
                    seen_paths.add(event_path)
        
        except PermissionError:
            pass
        except Exception:
            pass
        
        self._devices = options
        return options
    
    def _get_port_options(self) -> List[tuple]:
        """Get available MIDI port options."""
        options = [
            ("MIDITyper (Default)", "MIDITyper"),
            ("MIDITyper_2", "MIDITyper_2"),
            ("MIDITyper_3", "MIDITyper_3"),
            ("-- Custom Port Name --", "_custom_"),
        ]
        self._port_options = options
        return options
    
    def _refresh_global_keybinds_table(self) -> None:
        """Refresh the global keybinds table."""
        table = self.query_one("#global-keybinds-table", DataTable)
        table.clear()
        self._global_key_rows = []

        if hasattr(self.app, 'config') and self.app.config:
            mappings = self.app.config.settings.app_global_mappings
            for key, mapping in mappings.items():
                if mapping.get('type') == 'note':
                    value = f"Note {mapping.get('note', 0)} ({mapping.get('name', '?')})"
                else:
                    value = mapping.get('action', '?')
                self._global_key_rows.append(key)
                table.add_row(key, mapping.get('type', '?'), value)
    
    def on_mount(self) -> None:
        """Initialize the screen with current settings."""
        table = self.query_one("#global-keybinds-table", DataTable)
        table.add_columns("Key", "Type", "Value")
        
        # Load settings from app if available
        if hasattr(self.app, 'config') and self.app.config:
            settings = self.app.config.settings
            self.port_name = settings.virtual_port_name
            self.auto_detect = settings.auto_detect_device
            self.theme = settings.theme
            self.min_velocity = settings.min_velocity
            self.max_velocity = settings.max_velocity
            
            # Update device select
            device_select = self.query_one("#device-select", Select)
            if settings.default_device_path:
                # Check if the saved device path exists in the available options
                available_values = [opt[1] for opt in self._devices]
                if settings.default_device_path in available_values:
                    device_select.value = settings.default_device_path
                else:
                    # If device not found, set to auto-detect
                    device_select.value = ""
            
            # Update port select
            port_select = self.query_one("#port-select", Select)
            if settings.virtual_port_name in [opt[1] for opt in self._port_options]:
                port_select.value = settings.virtual_port_name
            else:
                port_select.value = "_custom_"
            
            # Update auto-detect select
            auto_detect_select = self.query_one("#auto-detect-select", Select)
            auto_detect_select.value = settings.auto_detect_device
            
            # Update theme select
            theme_select = self.query_one("#theme-select", Select)
            theme_select.value = settings.theme
            
            # Update velocity selects
            min_vel_select = self.query_one("#min-velocity-select", Select)
            min_vel_select.value = settings.min_velocity
            
            max_vel_select = self.query_one("#max-velocity-select", Select)
            max_vel_select.value = settings.max_velocity
            
            # Update device info
            device_info = self.query_one("#device-info", Static)
            if settings.default_device_path:
                device_info.update(f"[dim]Current: {settings.default_device_path}[/dim]")
            
            # Refresh global keybinds table
            self._refresh_global_keybinds_table()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "btn-add-global":
            self._add_global_keybind()
        elif event.button.id == "btn-edit-global":
            self._edit_global_keybind()
        elif event.button.id == "btn-delete-global":
            self._delete_global_keybind()
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select widget changes."""
        if event.select.id == "device-select":
            self.device_path = event.value or ""
            if self.device_path:
                self.auto_detect = False
                auto_detect_select = self.query_one("#auto-detect-select", Select)
                auto_detect_select.value = False
        elif event.select.id == "port-select":
            if event.value == "_custom_":
                # Prompt for custom port name (simplified - just use default for now)
                self.port_name = "MIDITyper_Custom"
            else:
                self.port_name = event.value
        elif event.select.id == "auto-detect-select":
            self.auto_detect = event.value
        elif event.select.id == "theme-select":
            self.theme = event.value
        elif event.select.id == "min-velocity-select":
            self.min_velocity = event.value
        elif event.select.id == "max-velocity-select":
            self.max_velocity = event.value

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """Treat cell selection as row selection for action buttons."""
        if event.data_table.id != "global-keybinds-table":
            return
        row = getattr(event, "cursor_row", None)
        if row is None:
            coordinate = getattr(event, "coordinate", None)
            row = getattr(coordinate, "row", None)
        if row is not None:
            event.data_table.move_cursor(row=row)

    def _get_selected_global_key(self) -> Optional[str]:
        """Get the currently selected app-global keybind key."""
        table = self.query_one("#global-keybinds-table", DataTable)
        if table.cursor_row is None:
            return None
        row = table.cursor_row
        if row < 0 or row >= len(self._global_key_rows):
            return None
        return self._global_key_rows[row]
    
    def _add_global_keybind(self) -> None:
        """Add a new global keybind."""
        self.app.push_screen(AddGlobalMappingDialog(), self._handle_add_global_result)

    def _edit_global_keybind(self) -> None:
        """Edit the selected global keybind."""
        key = self._get_selected_global_key()
        if key is None:
            self.notify("Select a keybind to edit", severity="warning")
            return

        mappings = self.app.config.settings.app_global_mappings if hasattr(self.app, 'config') and self.app.config else {}
        mapping = mappings.get(key)
        if mapping is None:
            return

        self.app.push_screen(
            AddGlobalMappingDialog(edit_mode=True, initial_key=key, initial_mapping=mapping),
            self._handle_edit_global_result,
        )

    def _handle_add_global_result(self, result: Optional[tuple]) -> None:
        """Handle the result from the add global mapping dialog."""
        if result is None:
            return

        key, mapping = result

        if hasattr(self.app, 'config') and self.app.config:
            self.app.config.settings.app_global_mappings[key] = mapping
            self._refresh_global_keybinds_table()
            self.notify(f"Added global keybind: {key}", severity="information")

    def _handle_edit_global_result(self, result: Optional[tuple]) -> None:
        """Handle the result from the edit global mapping dialog."""
        if result is None:
            return

        key, mapping = result

        if hasattr(self.app, 'config') and self.app.config:
            self.app.config.settings.app_global_mappings[key] = mapping
            self._refresh_global_keybinds_table()
            self.notify(f"Updated global keybind: {key}", severity="information")

    def _delete_global_keybind(self) -> None:
        """Delete the selected global keybind."""
        row_key = self._get_selected_global_key()
        if row_key is None:
            self.notify("Select a keybind to delete", severity="warning")
            return

        if hasattr(self.app, 'config') and self.app.config:
            mappings = self.app.config.settings.app_global_mappings
            if row_key in mappings:
                del mappings[row_key]
                self._refresh_global_keybinds_table()
                self.notify(f"Deleted global keybind: {row_key}", severity="information")
    
    def action_save(self) -> None:
        """Save settings and return to main menu."""
        # Update app config if available
        if hasattr(self.app, 'config') and self.app.config:
            self.app.config.settings.default_device_path = self.device_path
            self.app.config.settings.virtual_port_name = self.port_name
            self.app.config.settings.auto_detect_device = self.auto_detect
            self.app.config.settings.theme = self.theme
            self.app.config.settings.min_velocity = self.min_velocity
            self.app.config.settings.max_velocity = self.max_velocity
            self.app.config.save_settings()
            
            # Notify user
            self.notify("Settings saved!", title="Success", severity="information")
        
        self.app.pop_screen()
    
    def action_back(self) -> None:
        """Return to main menu without saving."""
        self.app.pop_screen()
