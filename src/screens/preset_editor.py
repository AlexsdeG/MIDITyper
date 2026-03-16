"""
Preset Editor Screen for MIDITyper.

This screen allows users to:
- Create new presets
- Edit existing presets
- Manage pages and key mappings
- Rename pages
- Assign MIDI notes and actions to keys
- Manage preset global mappings
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from rich.text import Text

from evdev import ecodes

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.screen import Screen, ModalScreen
from textual.widgets import (
    Button, Header, Footer, Static, Label, Input, Select,
    TabbedContent, TabPane, Checkbox, ListView, ListItem,
    DataTable
)
from textual.reactive import reactive
from textual.message import Message
from textual.binding import Binding

from ..action_catalog import get_action_select_options
from .mapping_dialogs import (
    ConfirmOverwriteDialog,
    KeyMappingDialog,
    mapping_summary,
    normalize_key_name as shared_normalize_key_name,
)


def normalize_key_name(key_input: str) -> Optional[str]:
    """
    Normalize user key input to evdev KEY_ format.
    
    Examples:
        'A' -> 'KEY_A'
        'a' -> 'KEY_A'
        'KEY_A' -> 'KEY_A'
        'key_a' -> 'KEY_A'
        'SPACE' -> 'KEY_SPACE'
    
    Args:
        key_input: User input string
        
    Returns:
        Normalized key name if valid, None if invalid
    """
    return shared_normalize_key_name(key_input)


# Available UI modules
UI_MODULES = [
    ("event_log", "Event Log"),
    ("active_notes_panel", "Active Notes Panel"),
    ("shortcut_guide", "Shortcut Guide"),
    ("drum_pad_visualizer", "Drum Pad Visualizer"),
    ("piano_keyboard_visualizer", "Piano Keyboard Visualizer"),
    ("page_indicator", "Page Indicator"),
    ("velocity_meter", "Velocity Meter"),
]

# Common MIDI notes for quick selection
COMMON_NOTES = [
    (36, "C2 - Bass Drum"),
    (38, "D2 - Snare"),
    (40, "E2 - Snare 2"),
    (42, "F#2 - HH Closed"),
    (44, "G#2 - HH Pedal"),
    (46, "A#2 - HH Open"),
    (48, "C3"),
    (49, "C#3"),
    (50, "D3"),
    (51, "D#3"),
    (52, "E3"),
    (53, "F3"),
    (54, "F#3"),
    (55, "G3"),
    (56, "G#3"),
    (57, "A3"),
    (58, "A#3"),
    (59, "B3"),
    (60, "C4 (Middle C)"),
    (61, "C#4"),
    (62, "D4"),
    (63, "D#4"),
    (64, "E4"),
    (65, "F4"),
    (66, "F#4"),
    (67, "G4"),
    (68, "G#4"),
    (69, "A4 (440Hz)"),
    (70, "A#4"),
    (71, "B4"),
    (72, "C5"),
]


class MappingEditDialog(ModalScreen):
    """
    Modal dialog for editing a single key mapping.
    
    Allows assigning either a MIDI note or an action to a key.
    """
    
    CSS = """
    MappingEditDialog {
        align: center middle;
    }
    
    #dialog {
        width: 60;
        height: auto;
        padding: 1;
        background: $surface;
        border: thick $primary;
    }
    
    #dialog-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    
    .dialog-row {
        margin-bottom: 1;
        padding: 0 1;
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
        Binding("enter", "save", "Save"),
    ]
    
    key_name: reactive[str] = reactive("")
    mapping_type: reactive[str] = reactive("note")
    note_value: reactive[int] = reactive(60)
    note_name: reactive[str] = reactive("C4")
    action_value: reactive[str] = reactive("TOGGLE_CAPTURE")
    
    def __init__(
        self,
        key_name: str = "",
        mapping_type: str = "note",
        note: int = 60,
        note_name: str = "C4",
        action: str = "TOGGLE_CAPTURE"
    ):
        super().__init__()
        self.key_name = key_name
        self.mapping_type = mapping_type
        self.note_value = note
        self.note_name = note_name
        self.action_value = action
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        with Container(id="dialog"):
            yield Label(f"Edit Mapping for: {self.key_name}", id="dialog-title")
            
            with Vertical(classes="dialog-row"):
                yield Label("Mapping Type:", classes="dialog-label")
                yield Select(
                    options=[
                        ("MIDI Note", "note"),
                        ("Action", "action"),
                    ],
                    value=self.mapping_type,
                    id="mapping-type-select"
                )
            
            # Note configuration (shown when type is "note")
            with Vertical(classes="dialog-row", id="note-config"):
                yield Label("MIDI Note:", classes="dialog-label")
                yield Select(
                    options=[(label, value) for value, label in COMMON_NOTES],
                    value=self.note_value,
                    id="note-select"
                )
                
                yield Label("Note Name (display):", classes="dialog-label")
                yield Input(
                    value=self.note_name,
                    placeholder="e.g., C4, Snare, Kick",
                    id="note-name-input"
                )
            
            # Action configuration (shown when type is "action")
            with Vertical(classes="dialog-row", id="action-config"):
                yield Label("Action:", classes="dialog-label")
                yield Select(
                    options=get_action_select_options(),
                    value=self.action_value,
                    id="action-select"
                )
            
            with Horizontal(id="button-row"):
                yield Button("Save", variant="success", id="btn-save")
                yield Button("Cancel", variant="error", id="btn-cancel")
                yield Button("Delete", variant="warning", id="btn-delete")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the dialog."""
        self._update_visibility()
    
    def _update_visibility(self) -> None:
        """Show/hide config sections based on mapping type."""
        note_config = self.query_one("#note-config", Vertical)
        action_config = self.query_one("#action-config", Vertical)
        
        if self.mapping_type == "note":
            note_config.display = True
            action_config.display = False
        else:
            note_config.display = False
            action_config.display = True
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select widget changes."""
        if event.select.id == "mapping-type-select":
            self.mapping_type = event.value
            self._update_visibility()
        elif event.select.id == "note-select":
            self.note_value = event.value
            # Auto-set note name from selection
            for value, label in COMMON_NOTES:
                if value == event.value:
                    self.note_name = label.split(" - ")[0]
                    self.query_one("#note-name-input", Input).value = self.note_name
                    break
        elif event.select.id == "action-select":
            self.action_value = event.value
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        if event.input.id == "note-name-input":
            self.note_name = event.value
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-save":
            self.action_save()
        elif event.button.id == "btn-cancel":
            self.action_cancel()
        elif event.button.id == "btn-delete":
            self.dismiss(None)  # Signal deletion
    
    def action_save(self) -> None:
        """Save and close the dialog."""
        result = {
            "type": self.mapping_type,
        }
        
        if self.mapping_type == "note":
            result["note"] = self.note_value
            result["name"] = self.note_name
        else:
            result["action"] = self.action_value
        
        self.dismiss(result)
    
    def action_cancel(self) -> None:
        """Cancel and close the dialog."""
        self.dismiss(False)


class PresetEditorScreen(Screen):
    """
    Preset editor screen for creating and editing presets.
    
    Features:
    - Preset selection/creation
    - General settings (name, UI modules)
    - Page management with rename capability
    - Key mapping editor with CRUD operations
    - Preset global mappings management
    - Preset global actions management
    """
    
    CSS = """
    PresetEditorScreen {
        layout: vertical;
    }
    
    #editor-container {
        height: 1fr;
        padding: 1;
    }
    
    #preset-select-row {
        height: auto;
        margin-bottom: 1;
        padding: 1;
        background: $panel;
    }
    
    #preset-select-row Label {
        width: auto;
        margin-right: 1;
    }
    
    #preset-select-row Select {
        width: 20;
    }
    
    #tab-content {
        height: 1fr;
    }
    
    .setting-row {
        height: auto;
        margin-bottom: 1;
        padding: 1;
    }
    
    .setting-label {
        color: $text;
        margin-bottom: 0;
    }
    
    #button-row {
        dock: bottom;
        height: 3;
        padding: 1;
        align: center middle;
        background: $surface;
    }
    
    #module-list {
        height: auto;
        padding: 1;
    }
    
    .module-item {
        padding: 0 1;
    }
    
    #page-editor-container {
        height: 1fr;
        layout: horizontal;
    }
    
    #page-list-panel {
        width: 1fr;
        padding: 1;
    }
    
    #mapping-panel {
        width: 2fr;
        padding: 1;
    }
    
    #page-list {
        height: 1fr;
    }
    
    #page-name-row {
        margin-top: 1;
        height: auto;
    }
    
    #page-name-input {
        width: 1fr;
    }
    
    #mapping-table {
        height: 1fr;
    }
    
    #mapping-buttons {
        margin-top: 1;
    }
    
    #mapping-buttons Button {
        margin-right: 1;
    }
    
    #mapping-info {
        color: $text-muted;
        text-align: center;
        margin-top: 1;
    }
    
    .global-section {
        margin-top: 1;
        padding: 1;
        background: $surface;
        border: solid $border;
    }
    
    .global-section-title {
        text-style: bold;
        margin-bottom: 1;
    }
    
    .global-table {
        height: auto;
        max-height: 8;
    }
    
    .global-buttons {
        margin-top: 1;
    }
    
    .global-buttons Button {
        margin-right: 1;
    }
    """
    
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("ctrl+s", "save", "Save"),
        Binding("ctrl+n", "new", "New Preset"),
    ]
    
    # Reactive properties
    current_preset_name: reactive[str] = reactive("")
    preset_name: reactive[str] = reactive("")
    preset_description: reactive[str] = reactive("")
    selected_page_index: reactive[int] = reactive(0)
    
    def __init__(self):
        super().__init__()
        self._preset_names: List[str] = []
        self._selected_modules: List[str] = ["event_log", "active_notes_panel"]
        
        # Internal preset data structure
        self._preset_data: Dict = {
            "name": "",
            "description": "",
            "ui_modules": ["event_log", "active_notes_panel"],
            "pages": [
                {"name": "Page 1", "mappings": {}}
            ],
            "global_actions": {},
            "global_mappings": {}
        }
        self._page_mapping_keys: List[str] = []
        self._global_mapping_keys: List[str] = []
        self._global_action_keys: List[str] = []
    
    def compose(self) -> ComposeResult:
        """Create the preset editor layout."""
        yield Header()
        
        with Container(id="editor-container"):
            # Preset selection row (toolbar - reduced height)
            with Horizontal(id="preset-select-row"):
                yield Label("Select Preset:")
                yield Select(
                    options=self._get_preset_options(),
                    id="preset-select"
                )
                yield Button("+ New", variant="success", id="btn-new")
                yield Button("🗑 Delete", variant="error", id="btn-delete")
            
            # Tabbed content for editing
            with TabbedContent(id="tab-content"):
                # General Tab
                with TabPane("General", id="tab-general"):
                    with ScrollableContainer():
                        with Container(classes="setting-row"):
                            yield Label("Preset Name:", classes="setting-label")
                            yield Input(
                                placeholder="My Preset",
                                id="preset-name-input"
                            )
                        
                        with Container(classes="setting-row"):
                            yield Label("Description:", classes="setting-label")
                            yield Input(
                                placeholder="Description of the preset",
                                id="preset-desc-input"
                            )
                        
                        with Container(classes="setting-row"):
                            yield Label("UI Modules:", classes="setting-label")
                            with Vertical(id="module-list"):
                                for module_id, module_label in UI_MODULES:
                                    yield Checkbox(
                                        module_label,
                                        value=module_id in self._selected_modules,
                                        id=f"mod-{module_id}"
                                    )
                
                # Pages Tab
                with TabPane("Pages", id="tab-pages"):
                    with Horizontal(id="page-editor-container"):
                        # Left: Page list with rename input
                        with Vertical(id="page-list-panel"):
                            yield Label("Pages:", classes="setting-label")
                            yield ListView(
                                *[ListItem(Label("Page 1"))],
                                id="page-list"
                            )
                            with Horizontal():
                                yield Button("+ Add Page", id="btn-add-page")
                                yield Button("- Remove", id="btn-remove-page")
                            
                            # Page rename input (Step 3.2)
                            with Horizontal(id="page-name-row"):
                                yield Label("Name:")
                                yield Input(
                                    value="Page 1",
                                    placeholder="Page name",
                                    id="page-name-input"
                                )
                        
                        # Right: Mapping editor
                        with Vertical(id="mapping-panel"):
                            yield Label("Key Mappings for Selected Page:", classes="setting-label")
                            yield DataTable(
                                id="mapping-table",
                                show_header=True,
                                zebra_stripes=True
                            )
                            with Horizontal(id="mapping-buttons"):
                                yield Button("Add Mapping", variant="primary", id="btn-add-mapping")
                                yield Button("Edit Selected", id="btn-edit-mapping")
                                yield Button("Delete Selected", variant="warning", id="btn-delete-mapping")
                
                # Preset Global Mappings Tab (Step 3.4)
                with TabPane("Global Mappings", id="tab-global-mappings"):
                    with ScrollableContainer():
                        yield Static(
                            "Preset Global Mappings are key bindings that work across all pages in this preset. "
                            "They have lower priority than page-specific mappings.",
                            classes="setting-label"
                        )
                        
                        with Container(classes="global-section"):
                            yield Label("Global Mappings:", classes="global-section-title")
                            yield DataTable(
                                id="global-mappings-table",
                                show_header=True,
                                zebra_stripes=True,
                                classes="global-table"
                            )
                            with Horizontal(classes="global-buttons"):
                                yield Button("Add Mapping", variant="primary", id="btn-add-global-mapping")
                                yield Button("Edit Selected", id="btn-edit-global-mapping")
                                yield Button("Delete Selected", variant="warning", id="btn-delete-global-mapping")
                        
                        with Container(classes="global-section"):
                            yield Label("Global Actions (work on all pages):", classes="global-section-title")
                            yield DataTable(
                                id="global-actions-table",
                                show_header=True,
                                zebra_stripes=True,
                                classes="global-table"
                            )
                            with Horizontal(classes="global-buttons"):
                                yield Button("Add Action", variant="primary", id="btn-add-global-action")
                                yield Button("Edit Selected", id="btn-edit-global-action")
                                yield Button("Delete Selected", variant="warning", id="btn-delete-global-action")
        
        yield Footer()
    
    def _get_preset_options(self) -> List[tuple]:
        """Get available presets for the select widget."""
        options = [("-- Select a preset --", None)]
        
        # Get presets from data directory
        presets_dir = Path(__file__).parent.parent.parent / "data" / "presets"
        if presets_dir.exists():
            for preset_file in sorted(presets_dir.glob("*.json")):
                preset_name = preset_file.stem
                options.append((preset_name, preset_name))
                self._preset_names.append(preset_name)
        
        return options
    
    def on_mount(self) -> None:
        """Initialize the screen."""
        # Initialize mapping table
        mapping_table = self.query_one("#mapping-table", DataTable)
        mapping_table.add_columns("Key", "Type", "Value", "Name")
        
        # Initialize global mappings table
        global_mappings_table = self.query_one("#global-mappings-table", DataTable)
        global_mappings_table.add_columns("Key", "Type", "Value", "Name")
        
        # Initialize global actions table
        global_actions_table = self.query_one("#global-actions-table", DataTable)
        global_actions_table.add_columns("Key", "Type", "Value", "Name")
        
        # Set default module checkboxes
        self._update_module_checkboxes(self._selected_modules)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id
        
        if button_id == "btn-new":
            self._create_new_preset()
        elif button_id == "btn-delete":
            self._delete_preset()
        elif button_id == "btn-add-page":
            self._add_page()
        elif button_id == "btn-remove-page":
            self._remove_page()
        elif button_id == "btn-add-mapping":
            self._add_mapping()
        elif button_id == "btn-edit-mapping":
            self._edit_mapping()
        elif button_id == "btn-delete-mapping":
            self._delete_mapping()
        elif button_id == "btn-add-global-mapping":
            self._add_global_mapping()
        elif button_id == "btn-edit-global-mapping":
            self._edit_global_mapping()
        elif button_id == "btn-delete-global-mapping":
            self._delete_global_mapping()
        elif button_id == "btn-add-global-action":
            self._add_global_action()
        elif button_id == "btn-edit-global-action":
            self._edit_global_action()
        elif button_id == "btn-delete-global-action":
            self._delete_global_action()

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """Treat cell selection as row selection for Edit/Delete actions."""
        row = getattr(event, "cursor_row", None)
        if row is None:
            coordinate = getattr(event, "coordinate", None)
            row = getattr(coordinate, "row", None)
        if row is not None:
            event.data_table.move_cursor(row=row)
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select widget changes."""
        if event.select.id == "preset-select":
            if event.value:
                self._load_preset(event.value)
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input widget changes."""
        if event.input.id == "preset-name-input":
            self.preset_name = event.value
            self._preset_data["name"] = event.value
        elif event.input.id == "preset-desc-input":
            self.preset_description = event.value
            self._preset_data["description"] = event.value
        elif event.input.id == "page-name-input":
            # Update page name in preset data (Step 3.2)
            self._update_page_name(event.value)
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if event.input.id == "page-name-input":
            # Confirm page name change
            self.notify(f"Page renamed to: {event.value}", severity="information")
    
    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox changes for UI modules."""
        module_id = event.checkbox.id.replace("mod-", "")
        
        if event.value:
            if module_id not in self._selected_modules:
                self._selected_modules.append(module_id)
        else:
            if module_id in self._selected_modules:
                self._selected_modules.remove(module_id)
        
        self._preset_data["ui_modules"] = self._selected_modules.copy()
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle page selection."""
        if event.list_view.id == "page-list":
            self.selected_page_index = event.list_view.index
            self._refresh_mapping_table()
            self._update_page_name_input()
    
    def _update_page_name(self, new_name: str) -> None:
        """Update the name of the currently selected page."""
        pages = self._preset_data.get("pages", [])
        if 0 <= self.selected_page_index < len(pages):
            pages[self.selected_page_index]["name"] = new_name
            self._update_page_list()
    
    def _update_page_name_input(self) -> None:
        """Update the page name input widget with the current page name."""
        pages = self._preset_data.get("pages", [])
        if 0 <= self.selected_page_index < len(pages):
            page_name = pages[self.selected_page_index].get("name", f"Page {self.selected_page_index + 1}")
            try:
                page_name_input = self.query_one("#page-name-input", Input)
                page_name_input.value = page_name
            except Exception:
                pass
    
    def _load_preset(self, preset_name: str) -> None:
        """Load a preset into the editor."""
        preset_path = Path(__file__).parent.parent.parent / "data" / "presets" / f"{preset_name}.json"
        
        if not preset_path.exists():
            self.notify(f"Preset '{preset_name}' not found", severity="error")
            return
        
        try:
            with open(preset_path, 'r') as f:
                self._preset_data = json.load(f)
            
            # Ensure global_mappings exists
            if "global_mappings" not in self._preset_data:
                self._preset_data["global_mappings"] = {}
            
            # Update form fields
            name_input = self.query_one("#preset-name-input", Input)
            name_input.value = self._preset_data.get("name", "")
            
            desc_input = self.query_one("#preset-desc-input", Input)
            desc_input.value = self._preset_data.get("description", "")
            
            self.current_preset_name = preset_name
            self.preset_name = self._preset_data.get("name", "")
            self.preset_description = self._preset_data.get("description", "")
            
            # Update modules
            self._selected_modules = list(self._preset_data.get("ui_modules", []))
            self._update_module_checkboxes(self._selected_modules)
            
            # Update page list
            self._update_page_list()
            
            # Update mapping table
            self._refresh_mapping_table()
            
            # Update page name input
            self._update_page_name_input()
            
            # Update global tables
            self._refresh_global_mappings_table()
            self._refresh_global_actions_table()
            
            self.notify(f"Loaded preset: {preset_name}", severity="information")
            
        except Exception as e:
            self.notify(f"Failed to load preset: {e}", severity="error")
    
    def _update_module_checkboxes(self, modules: List[str]) -> None:
        """Update module checkboxes based on preset."""
        for module_id, _ in UI_MODULES:
            try:
                checkbox = self.query_one(f"#mod-{module_id}", Checkbox)
                checkbox.value = module_id in modules
            except Exception:
                pass
    
    def _update_page_list(self) -> None:
        """Update the page list display."""
        page_list = self.query_one("#page-list", ListView)
        page_list.clear()
        
        pages = self._preset_data.get("pages", [])
        for i, page in enumerate(pages):
            page_list.append(ListItem(Label(f"[{i}] {page.get('name', f'Page {i+1}')}")))
        
        if pages:
            page_list.index = min(self.selected_page_index, len(pages) - 1)
    
    def _refresh_mapping_table(self) -> None:
        """Refresh the mapping table for the current page."""
        mapping_table = self.query_one("#mapping-table", DataTable)
        mapping_table.clear()
        self._page_mapping_keys = []
        
        pages = self._preset_data.get("pages", [])
        if not pages or self.selected_page_index >= len(pages):
            return
        
        current_page = pages[self.selected_page_index]
        mappings = current_page.get("mappings", {})
        
        for key, mapping in mappings.items():
            self._page_mapping_keys.append(key)
            if mapping.get("type") == "note":
                mapping_table.add_row(
                    key,
                    "Note",
                    str(mapping.get("note", 0)),
                    mapping.get("name", "")
                )
            elif mapping.get("type") == "action":
                mapping_table.add_row(
                    key,
                    "Action",
                    mapping.get("action", ""),
                    "-"
                )
    
    def _refresh_global_mappings_table(self) -> None:
        """Refresh the global mappings table."""
        table = self.query_one("#global-mappings-table", DataTable)
        table.clear()
        self._global_mapping_keys = []
        
        global_mappings = self._preset_data.get("global_mappings", {})
        
        for key, mapping in global_mappings.items():
            self._global_mapping_keys.append(key)
            if mapping.get("type") == "note":
                table.add_row(
                    key,
                    "Note",
                    str(mapping.get("note", 0)),
                    mapping.get("name", "")
                )
            elif mapping.get("type") == "action":
                table.add_row(
                    key,
                    "Action",
                    mapping.get("action", ""),
                    "-"
                )
    
    def _refresh_global_actions_table(self) -> None:
        """Refresh the global actions table."""
        global_table = self.query_one("#global-actions-table", DataTable)
        global_table.clear()
        self._global_action_keys = []
        
        global_actions = self._preset_data.get("global_actions", {})
        
        for key, mapping in global_actions.items():
            self._global_action_keys.append(key)
            global_table.add_row(
                key,
                "Action",
                mapping.get("action", ""),
                "-",
            )

    def _get_selected_table_key(self, table: DataTable, keys: List[str]) -> Optional[str]:
        """Get selected key from a table based on cursor row."""
        if table.cursor_row is None:
            return None
        row = table.cursor_row
        if row < 0 or row >= len(keys):
            return None
        return keys[row]
    
    def _create_new_preset(self) -> None:
        """Create a new preset."""
        self.current_preset_name = ""
        
        # Reset preset data
        self._preset_data = {
            "name": "New Preset",
            "description": "",
            "ui_modules": ["event_log", "active_notes_panel"],
            "pages": [
                {"name": "Page 1", "mappings": {}}
            ],
            "global_actions": {},
            "global_mappings": {}
        }
        
        name_input = self.query_one("#preset-name-input", Input)
        name_input.value = "New Preset"
        name_input.focus()
        
        desc_input = self.query_one("#preset-desc-input", Input)
        desc_input.value = ""
        
        self._selected_modules = ["event_log", "active_notes_panel"]
        self._update_module_checkboxes(self._selected_modules)
        
        self._update_page_list()
        self._refresh_mapping_table()
        self._update_page_name_input()
        self._refresh_global_mappings_table()
        self._refresh_global_actions_table()
        
        # Reset preset select
        preset_select = self.query_one("#preset-select", Select)
        preset_select.value = None
        
        self.notify("Creating new preset - edit the name and add mappings", severity="information")
    
    def _delete_preset(self) -> None:
        """Delete the current preset."""
        if not self.current_preset_name:
            self.notify("No preset selected", severity="warning")
            return
        
        preset_path = Path(__file__).parent.parent.parent / "data" / "presets" / f"{self.current_preset_name}.json"
        
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
            
            self.notify(f"Deleted preset: {self.current_preset_name}", severity="information")
            self._create_new_preset()
            
            # Refresh preset select options
            preset_select = self.query_one("#preset-select", Select)
            preset_select.set_options(self._get_preset_options())
        else:
            self.notify("Preset file not found", severity="error")
    
    def _add_page(self) -> None:
        """Add a new page to the preset."""
        pages = self._preset_data.setdefault("pages", [])
        new_index = len(pages)
        pages.append({
            "name": f"Page {new_index + 1}",
            "mappings": {}
        })
        
        self._update_page_list()
        self.notify(f"Added page {new_index + 1}", severity="information")
    
    def _remove_page(self) -> None:
        """Remove the selected page."""
        pages = self._preset_data.get("pages", [])
        
        if len(pages) <= 1:
            self.notify("Cannot remove the last page", severity="warning")
            return
        
        if 0 <= self.selected_page_index < len(pages):
            del pages[self.selected_page_index]
            self.selected_page_index = min(self.selected_page_index, len(pages) - 1)
            self._update_page_list()
            self._refresh_mapping_table()
            self._update_page_name_input()
            self.notify("Page removed", severity="information")
    
    def _add_mapping(self) -> None:
        """Add a new key mapping."""
        pages = self._preset_data.get("pages", [])
        if not pages:
            self.notify("No pages available", severity="error")
            return
        
        if self.selected_page_index >= len(pages):
            self.notify("Invalid page selection", severity="error")
            return
        
        self.app.push_screen(
            KeyMappingDialog(
                title="Add Page Mapping",
                initial_key="KEY_A",
                initial_mapping={"type": "note", "note": 60, "name": "C4"},
            ),
            lambda payload: self._apply_mapping_payload(payload, "page"),
        )
    
    def _edit_mapping(self) -> None:
        """Edit the selected mapping."""
        mapping_table = self.query_one("#mapping-table", DataTable)
        row_key = self._get_selected_table_key(mapping_table, self._page_mapping_keys)
        if row_key is None:
            self.notify("Select a mapping to edit", severity="warning")
            return
        
        pages = self._preset_data.get("pages", [])
        if self.selected_page_index >= len(pages):
            return
        
        mappings = pages[self.selected_page_index].get("mappings", {})
        if row_key not in mappings:
            return
        
        mapping = mappings[row_key]
        
        self.app.push_screen(
            KeyMappingDialog(
                title="Edit Page Mapping",
                edit_mode=True,
                initial_key=row_key,
                initial_mapping=mapping,
            ),
            lambda payload: self._apply_mapping_payload(payload, "page"),
        )
    
    def _delete_mapping(self) -> None:
        """Delete the selected mapping."""
        mapping_table = self.query_one("#mapping-table", DataTable)
        row_key = self._get_selected_table_key(mapping_table, self._page_mapping_keys)
        if row_key is None:
            self.notify("Select a mapping to delete", severity="warning")
            return
        
        pages = self._preset_data.get("pages", [])
        if self.selected_page_index >= len(pages):
            return
        
        mappings = pages[self.selected_page_index].get("mappings", {})
        if row_key in mappings:
            del mappings[row_key]
            self._refresh_mapping_table()
            self.notify(f"Deleted mapping for {row_key}", severity="information")
    
    def _apply_mapping_payload(self, payload: Optional[Dict], target: str) -> None:
        """Apply a mapping dialog payload to the selected target collection."""
        if not payload:
            return

        original_key = payload.get("original_key", "")
        new_key = payload.get("key", "")
        mapping = payload.get("mapping", {})

        mapping_store = self._resolve_mapping_store(target)
        if mapping_store is None:
            return

        existing = mapping_store.get(new_key)
        if existing is not None and new_key != original_key:
            warning = (
                f"{new_key} is already mapped to {mapping_summary(existing)}.\n"
                f"Replace it with {mapping_summary(mapping)}?"
            )
            self.app.push_screen(
                ConfirmOverwriteDialog("Key Conflict", warning),
                lambda confirmed, p=payload, t=target: self._finalize_mapping_payload(
                    p,
                    t,
                    bool(confirmed),
                ),
            )
            return

        self._finalize_mapping_payload(payload, target, True)

    def _finalize_mapping_payload(self, payload: Dict, target: str, confirmed: bool) -> None:
        """Finalize mapping update after conflict confirmation."""
        if not confirmed:
            self.notify("Mapping update cancelled", severity="warning")
            return

        original_key = payload.get("original_key", "")
        new_key = payload.get("key", "")
        mapping = payload.get("mapping", {})

        mapping_store = self._resolve_mapping_store(target)
        if mapping_store is None:
            return

        if original_key and original_key != new_key and original_key in mapping_store:
            del mapping_store[original_key]

        existed_before = new_key in mapping_store
        mapping_store[new_key] = mapping
        self._refresh_target_table(target)

        verb = "Updated" if payload.get("edit_mode") or existed_before else "Added"
        self.notify(f"{verb} mapping for {new_key}", severity="information")

    def _resolve_mapping_store(self, target: str) -> Optional[Dict[str, Dict]]:
        """Resolve a mapping store by target scope."""
        if target == "page":
            pages = self._preset_data.get("pages", [])
            if self.selected_page_index >= len(pages):
                return None
            return pages[self.selected_page_index].setdefault("mappings", {})

        if target == "global":
            return self._preset_data.setdefault("global_mappings", {})

        if target == "global_action":
            return self._preset_data.setdefault("global_actions", {})

        return None

    def _refresh_target_table(self, target: str) -> None:
        """Refresh table for a target scope."""
        if target == "page":
            self._refresh_mapping_table()
        elif target == "global":
            self._refresh_global_mappings_table()
        elif target == "global_action":
            self._refresh_global_actions_table()
    
    # Global Mappings CRUD
    def _add_global_mapping(self) -> None:
        """Add a new global mapping."""
        self.app.push_screen(
            KeyMappingDialog(
                title="Add Preset Global Mapping",
                initial_key="KEY_F1",
                initial_mapping={"type": "note", "note": 60, "name": "C4"},
            ),
            lambda payload: self._apply_mapping_payload(payload, "global"),
        )
    
    def _edit_global_mapping(self) -> None:
        """Edit the selected global mapping."""
        table = self.query_one("#global-mappings-table", DataTable)
        row_key = self._get_selected_table_key(table, self._global_mapping_keys)
        if row_key is None:
            self.notify("Select a mapping to edit", severity="warning")
            return
        
        global_mappings = self._preset_data.get("global_mappings", {})
        if row_key not in global_mappings:
            return
        
        mapping = global_mappings[row_key]
        
        self.app.push_screen(
            KeyMappingDialog(
                title="Edit Preset Global Mapping",
                edit_mode=True,
                initial_key=row_key,
                initial_mapping=mapping,
            ),
            lambda payload: self._apply_mapping_payload(payload, "global"),
        )
    
    def _delete_global_mapping(self) -> None:
        """Delete the selected global mapping."""
        table = self.query_one("#global-mappings-table", DataTable)
        row_key = self._get_selected_table_key(table, self._global_mapping_keys)
        if row_key is None:
            self.notify("Select a mapping to delete", severity="warning")
            return
        
        global_mappings = self._preset_data.get("global_mappings", {})
        if row_key in global_mappings:
            del global_mappings[row_key]
            self._refresh_global_mappings_table()
            self.notify(f"Deleted global mapping for {row_key}", severity="information")
    
    # Global Actions CRUD
    def _add_global_action(self) -> None:
        """Add a global action."""
        self.app.push_screen(
            KeyMappingDialog(
                title="Add Preset Global Action",
                initial_key="KEY_F12",
                initial_mapping={"type": "action", "action": "TOGGLE_CAPTURE"},
                action_only=True,
            ),
            lambda payload: self._apply_mapping_payload(payload, "global_action"),
        )
    
    def _delete_global_action(self) -> None:
        """Delete the selected global action."""
        global_table = self.query_one("#global-actions-table", DataTable)
        row_key = self._get_selected_table_key(global_table, self._global_action_keys)
        if row_key is None:
            self.notify("Select a global action to delete", severity="warning")
            return

        global_actions = self._preset_data.get("global_actions", {})
        if row_key in global_actions:
            del global_actions[row_key]
            self._refresh_global_actions_table()
            self.notify(f"Deleted global action for {row_key}", severity="information")

    def _edit_global_action(self) -> None:
        """Edit the selected global action."""
        global_table = self.query_one("#global-actions-table", DataTable)
        row_key = self._get_selected_table_key(global_table, self._global_action_keys)
        if row_key is None:
            self.notify("Select a global action to edit", severity="warning")
            return

        global_actions = self._preset_data.get("global_actions", {})
        mapping = global_actions.get(row_key)
        if mapping is None:
            return

        self.app.push_screen(
            KeyMappingDialog(
                title="Edit Preset Global Action",
                edit_mode=True,
                initial_key=row_key,
                initial_mapping=mapping,
                action_only=True,
            ),
            lambda payload: self._apply_mapping_payload(payload, "global_action"),
        )
    
    def action_save(self) -> None:
        """Save the preset."""
        if not self.preset_name:
            self.notify("Preset name is required", severity="error")
            return
        
        # Generate filename from name
        filename = self.preset_name.lower().replace(" ", "_").replace("-", "_")
        # Remove special characters
        filename = "".join(c for c in filename if c.isalnum() or c == "_")
        
        preset_path = Path(__file__).parent.parent.parent / "data" / "presets" / f"{filename}.json"
        
        try:
            with open(preset_path, 'w') as f:
                json.dump(self._preset_data, f, indent=2)
            
            self.notify(f"Saved preset: {filename}", severity="information")
            self.current_preset_name = filename
            
            # Refresh preset select options
            preset_select = self.query_one("#preset-select", Select)
            preset_select.set_options(self._get_preset_options())
            
        except Exception as e:
            self.notify(f"Failed to save: {e}", severity="error")
    
    def action_back(self) -> None:
        """Return to main menu."""
        self.app.pop_screen()
    
    def action_new(self) -> None:
        """Create new preset."""
        self._create_new_preset()


class InputScreen(ModalScreen):
    """Simple input dialog for getting a single value."""
    
    CSS = """
    InputScreen {
        align: center middle;
    }
    
    #dialog {
        width: 50;
        padding: 1;
        background: $surface;
        border: thick $primary;
    }
    
    #dialog-title {
        margin-bottom: 1;
    }
    
    #input-field {
        margin-bottom: 1;
    }
    
    #button-row {
        align: center middle;
    }
    
    #button-row Button {
        margin: 0 1;
    }
    """
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Confirm"),
    ]
    
    def __init__(self, prompt: str, default: str = ""):
        super().__init__()
        self._prompt = prompt
        self._default = default
    
    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label(self._prompt, id="dialog-title")
            yield Input(value=self._default, id="input-field")
            with Horizontal(id="button-row"):
                yield Button("Confirm", variant="success", id="btn-confirm")
                yield Button("Cancel", variant="error", id="btn-cancel")
    
    def on_mount(self) -> None:
        """Focus the input field."""
        self.query_one("#input-field", Input).focus()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-confirm":
            self.action_confirm()
        else:
            self.action_cancel()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        self.action_confirm()
    
    def action_confirm(self) -> None:
        """Confirm and return the value."""
        value = self.query_one("#input-field", Input).value.strip()
        self.dismiss(value if value else None)
    
    def action_cancel(self) -> None:
        """Cancel and return None."""
        self.dismiss(None)
