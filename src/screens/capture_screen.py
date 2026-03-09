"""
Capture Screen for MIDITyper.

This is the main capture screen that dynamically renders UI modules based on
the active preset configuration. Modules include:
- event_log: RichLog for displaying key events
- active_notes_panel: Shows currently playing notes
- shortcut_guide: Displays keyboard shortcuts
- drum_pad_visualizer: Visual representation of drum pads
- piano_keyboard_visualizer: Piano keyboard visualization
- page_indicator: Shows current page for multi-page presets
- velocity_sliders: Min/Max velocity controls with randomization
"""

import logging
from typing import List, Optional
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button, Header, Footer, Static, Label, RichLog, Input, Select
from textual.binding import Binding
from textual.message import Message
from rich.text import Text
from rich.table import Table


logger = logging.getLogger(__name__)


class EventLogWidget(RichLog):
    """Event log widget for displaying key events with Rich markup support."""
    
    DEFAULT_CSS = """
    EventLogWidget {
        height: 1fr;
        border: solid $border;
        background: $panel;
    }
    """
    
    def __init__(self, **kwargs):
        """Initialize the event log with markup enabled."""
        # Explicitly enable markup to parse [bold cyan] style tags
        super().__init__(markup=True, **kwargs)


class ActiveNotesPanel(Static):
    """Panel showing currently active notes."""
    
    DEFAULT_CSS = """
    ActiveNotesPanel {
        height: auto;
        min-height: 3;
        padding: 1;
        border: solid $border;
        background: $panel;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._notes: List[str] = []
    
    def render(self) -> str:
        """Render the active notes display."""
        if self._notes:
            return f"[bold]Active Notes:[/bold] {', '.join(self._notes)}"
        else:
            return "[dim]No active notes[/dim]"
    
    def update_notes(self, notes: List[str]) -> None:
        """Update the displayed notes."""
        self._notes = notes
        self.refresh()


class ShortcutGuide(Static):
    """Widget displaying keyboard shortcuts."""
    
    DEFAULT_CSS = """
    ShortcutGuide {
        height: auto;
        padding: 1;
        border: solid $border;
        background: $panel;
    }
    """
    
    def __init__(self, shortcuts: Optional[dict] = None, **kwargs):
        super().__init__(**kwargs)
        self._shortcuts = shortcuts or {
            "F12": "Toggle Capture",
            "F9": "Page Up",
            "F10": "Page Down",
            "ESC": "Panic",
            "+/-": "Velocity"
        }
    
    def render(self) -> str:
        """Render the shortcuts."""
        lines = ["[bold]Shortcuts:[/bold]"]
        for key, action in self._shortcuts.items():
            lines.append(f"  [cyan]{key}[/cyan]: {action}")
        return "\n".join(lines)
    
    def update_shortcuts(self, shortcuts: dict) -> None:
        """Update the shortcuts dictionary."""
        self._shortcuts = shortcuts
        self.refresh()


class DrumPadVisualizer(Static):
    """Visual representation of drum pads."""
    
    DEFAULT_CSS = """
    DrumPadVisualizer {
        height: auto;
        min-height: 8;
        padding: 1;
        border: solid $border;
        background: $panel;
    }
    
    .pad-active {
        background: $success;
        color: white;
    }
    
    .pad-inactive {
        background: $surface;
    }
    """
    
    def __init__(self, mapping: Optional[dict] = None, **kwargs):
        super().__init__(**kwargs)
        self._mapping = mapping or {}
        self._active_pads: set = set()
    
    def render(self) -> object:
        """Render the drum pad grid."""
        # Simplified drum pad visualization
        if not self._mapping:
            return "[dim]No drum mappings configured[/dim]"
        
        # Create a simple grid layout
        table = Table(show_header=False, box=None, padding=0)
        table.add_column(width=8)
        table.add_column(width=8)
        table.add_column(width=8)
        table.add_column(width=8)
        
        # Group pads by rows
        keys = list(self._mapping.keys())[:16]  # Max 16 pads
        
        for i in range(0, len(keys), 4):
            row = []
            for j in range(4):
                if i + j < len(keys):
                    key = keys[i + j]
                    mapping = self._mapping[key]
                    note_name = mapping.name if hasattr(mapping, 'name') else f"Note {mapping.note}"
                    is_active = key in self._active_pads
                    style = "[bold green]●[/bold green]" if is_active else "○"
                    row.append(f"{style} {note_name[:6]}")
                else:
                    row.append("")
            table.add_row(*row)
        
        return table
    
    def set_active_pad(self, key: str, active: bool) -> None:
        """Set a pad as active or inactive."""
        if active:
            self._active_pads.add(key)
        else:
            self._active_pads.discard(key)
        self.refresh()


class PianoKeyboardVisualizer(Static):
    """Visual representation of piano keyboard."""
    
    DEFAULT_CSS = """
    PianoKeyboardVisualizer {
        height: auto;
        min-height: 5;
        padding: 1;
        border: solid $border;
        background: $panel;
    }
    """
    
    def __init__(self, mapping: Optional[dict] = None, **kwargs):
        super().__init__(**kwargs)
        self._mapping = mapping or {}
        self._active_keys: set = set()
    
    def render(self) -> str:
        """Render a simple piano keyboard visualization."""
        if not self._mapping:
            return "[dim]No piano mappings configured[/dim]"
        
        active_notes = [self._mapping[k].name for k in self._active_keys if k in self._mapping]
        
        # Simple text representation
        if active_notes:
            return f"[bold green]Playing:[/bold green] {', '.join(active_notes[:5])}"
        else:
            return "[dim]Press mapped keys to play[/dim]"
    
    def set_active_key(self, key: str, active: bool) -> None:
        """Set a key as active or inactive."""
        if active:
            self._active_keys.add(key)
        else:
            self._active_keys.discard(key)
        self.refresh()


class PageIndicator(Static):
    """Widget showing current page for multi-page presets."""
    
    DEFAULT_CSS = """
    PageIndicator {
        height: auto;
        padding: 1;
        border: solid $primary;
        background: $panel;
    }
    """
    
    current_page: reactive[int] = reactive(0)
    total_pages: reactive[int] = reactive(1)
    page_name: reactive[str] = reactive("Page 1")
    
    def render(self) -> str:
        """Render the page indicator."""
        if self.total_pages > 1:
            return f"[bold cyan]Page:[/bold cyan] {self.page_name} ({self.current_page + 1}/{self.total_pages})"
        else:
            return f"[dim]{self.page_name}[/dim]"
    
    def watch_current_page(self, value: int) -> None:
        """Refresh when current page changes."""
        self.refresh()
    
    def watch_total_pages(self, value: int) -> None:
        """Refresh when total pages changes."""
        self.refresh()
    
    def watch_page_name(self, value: str) -> None:
        """Refresh when page name changes."""
        self.refresh()


class VelocitySliderSection(Static):
    """
    Widget containing min/max velocity controls with sliders and numeric inputs.
    
    When min != max, each note will have a random velocity between min and max.
    When min == max, all notes use that fixed velocity.
    """
    
    DEFAULT_CSS = """
    VelocitySliderSection {
        height: auto;
        padding: 1;
        border: solid $border;
        background: $panel;
        margin-bottom: 1;
    }
    
    VelocitySliderSection .slider-row {
        height: auto;
        margin-bottom: 1;
    }
    
    VelocitySliderSection .slider-label {
        color: $text;
        margin-bottom: 0;
        width: 15;
    }
    
    VelocitySliderSection .slider-value {
        color: $accent;
        text-align: center;
        width: 4;
    }
    
    VelocitySliderSection .slider-bar {
        height: 1;
        content-align: left middle;
        background: $surface;
        border: tall $border;
        width: 1fr;
    }
    
    VelocitySliderSection Button {
        min-width: 3;
        margin: 0 1;
    }
    
    VelocitySliderSection Input {
        width: 8;
    }
    """
    
    min_velocity: reactive[int] = reactive(100)
    max_velocity: reactive[int] = reactive(100)
    
    def __init__(self, min_vel: int = 100, max_vel: int = 100, **kwargs):
        super().__init__(**kwargs)
        self.min_velocity = min_vel
        self.max_velocity = max_vel
    
    def compose(self) -> ComposeResult:
        """Create the velocity control layout with sliders and inputs."""
        # Min Velocity Row
        with Vertical(classes="slider-row"):
            with Horizontal():
                yield Label("Min Velocity:", classes="slider-label")
                yield Label(str(self.min_velocity), id="min-velocity-value", classes="slider-value")
            with Horizontal():
                yield Button("-", id="min-velocity-dec", variant="default")
                yield Static(self._render_slider_bar(self.min_velocity), id="min-velocity-bar", classes="slider-bar")
                yield Button("+", id="min-velocity-inc", variant="default")
            yield Input(str(self.min_velocity), id="min-velocity-input", type="integer", placeholder="1-127")

        # Max Velocity Row
        with Vertical(classes="slider-row"):
            with Horizontal():
                yield Label("Max Velocity:", classes="slider-label")
                yield Label(str(self.max_velocity), id="max-velocity-value", classes="slider-value")
            with Horizontal():
                yield Button("-", id="max-velocity-dec", variant="default")
                yield Static(self._render_slider_bar(self.max_velocity), id="max-velocity-bar", classes="slider-bar")
                yield Button("+", id="max-velocity-inc", variant="default")
            yield Input(str(self.max_velocity), id="max-velocity-input", type="integer", placeholder="1-127")
    
    def _render_slider_bar(self, value: int) -> str:
        """Render a visual slider bar showing the velocity value."""
        # Create a 20-character bar representing 1-127 range
        bar_width = 20
        filled = int((value - 1) / 126 * bar_width)
        return "█" * filled + "░" * (bar_width - filled)
    
    def on_mount(self) -> None:
        """Initialize the display."""
        self._update_display()
    
    def _update_display(self) -> None:
        """Update all display elements (input, label, slider bar)."""
        try:
            # Update min velocity displays
            self.query_one("#min-velocity-value", Label).update(str(self.min_velocity))
            self.query_one("#min-velocity-bar", Static).update(self._render_slider_bar(self.min_velocity))
            min_input = self.query_one("#min-velocity-input", Input)
            if min_input.value != str(self.min_velocity):
                min_input.value = str(self.min_velocity)

            # Update max velocity displays
            self.query_one("#max-velocity-value", Label).update(str(self.max_velocity))
            self.query_one("#max-velocity-bar", Static).update(self._render_slider_bar(self.max_velocity))
            max_input = self.query_one("#max-velocity-input", Input)
            if max_input.value != str(self.max_velocity):
                max_input.value = str(self.max_velocity)
        except Exception:
            pass
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle slider button presses."""
        button_id = event.button.id
        
        if button_id == "min-velocity-dec":
            self.min_velocity = max(1, self.min_velocity - 1)
        elif button_id == "min-velocity-inc":
            self.min_velocity = min(127, self.min_velocity + 1)
        elif button_id == "max-velocity-dec":
            self.max_velocity = max(1, self.max_velocity - 1)
        elif button_id == "max-velocity-inc":
            self.max_velocity = min(127, self.max_velocity + 1)
        
        self._update_display()
        self.post_message(VelocityChanged(self.min_velocity, self.max_velocity))
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle direct input value changes."""
        try:
            value = int(event.input.value) if event.input.value else 1
            # Clamp value to valid MIDI range (1-127)
            value = max(1, min(127, value))
            
            if event.input.id == "min-velocity-input":
                self.min_velocity = value
            elif event.input.id == "max-velocity-input":
                self.max_velocity = value

            self._update_display()
            self.post_message(VelocityChanged(self.min_velocity, self.max_velocity))
        except (ValueError, AttributeError):
            # Ignore non-numeric input
            pass


class VelocityChanged(Message):
    """Message sent when velocity range changes."""
    
    def __init__(self, min_vel: int, max_vel: int):
        super().__init__()
        self.min_velocity = min_vel
        self.max_velocity = max_vel


class CaptureScreen(Screen):
    """
    Dynamic capture screen that renders UI modules based on preset.
    
    This screen is responsible for:
    - Displaying capture status
    - Showing active notes
    - Logging key events
    - Displaying page information
    - Dynamic module rendering
    - Velocity range control with sliders
    """
    
    CSS = """
    CaptureScreen {
        layout: vertical;
    }
    
    /* Top Toolbar - Step 5.4 & 5.5 */
    #top-toolbar {
        dock: top;
        height: 3;
        padding: 0 1;
        align: left middle;
        background: $surface;
    }

    #toolbar-status {
        width: 1fr;
        align: left middle;
    }

    #toolbar-right {
        width: auto;
        align: right middle;
    }

    #capture-preset-select {
        width: 20;
        margin: 0 1;
    }

    #top-toolbar Button {
        margin: 0 1;
        min-width: 12;
    }
    
    #btn-capture {
        background: $success;
        color: white;
    }
    
    #btn-capture:hover {
        background: $success-lighten-1;
    }
    
    #btn-capture.capturing {
        background: $warning;
        color: black;
    }
    
    #btn-kill {
        background: $error;
        color: white;
    }
    
    #btn-kill:hover {
        background: $error-lighten-1;
    }
    
    /* Status bar removed - merged into top toolbar */
    #status-indicator {
        text-style: bold;
        margin-right: 2;
    }
    
    .status-capturing {
        color: $success;
    }
    
    .status-passthrough {
        color: $warning;
    }
    
    /* Main content area */
    #main-container {
        layout: horizontal;
        height: 1fr;
    }
    
    #left-panel {
        width: 1fr;
        padding: 1;
    }
    
    #right-panel {
        width: 1fr;
        padding: 1;
    }
    
    /* Kill bar removed - moved to top toolbar */
    
    .module-container {
        margin-bottom: 1;
    }
    
    .info-panel {
        background: $panel;
        border: solid $border;
        padding: 1;
        margin-bottom: 1;
    }
    """
    
    # Reactive properties
    status: reactive[str] = reactive("CAPTURING")
    current_page: reactive[int] = reactive(0)
    page_name: reactive[str] = reactive("Page 1")
    total_pages: reactive[int] = reactive(1)
    has_multiple_pages: reactive[bool] = reactive(False)
    preset_name: reactive[str] = reactive("Loading...")
    
    # Velocity range reactive properties (Step 5.2)
    min_velocity: reactive[int] = reactive(100)
    max_velocity: reactive[int] = reactive(100)
    
    # UI modules to render
    ui_modules: List[str] = []
    
    # Internal preset reference
    _preset_loaded: bool = False
    
    def compose(self) -> ComposeResult:
        """Create the capture screen layout dynamically based on preset."""
        yield Header()
        
        # Top toolbar with status on the left and controls on the right.
        with Horizontal(id="top-toolbar"):
            with Horizontal(id="toolbar-status"):
                yield Label(self._get_status_text(), id="status-indicator")
            with Horizontal(id="toolbar-right"):
                yield Label("Preset:")
                yield Select(options=self._get_preset_options(), id="capture-preset-select")
                yield Button("● Capture", variant="success", id="btn-capture")
                yield Button("⚠ KILL", variant="error", id="btn-kill")
        
        # Main content area
        with Container(id="main-container"):
            # Left panel - preset info, page indicator, and velocity sliders
            with Vertical(id="left-panel"):
                yield Static(
                    f"[bold]Preset:[/bold] {self.preset_name}", 
                    classes="info-panel", 
                    id="preset-info"
                )
                
                # Page indicator (always shown, will hide if single page)
                yield PageIndicator(id="page-indicator")
                
                # Velocity Sliders Section (Step 5.2)
                yield VelocitySliderSection(
                    min_vel=self.min_velocity,
                    max_vel=self.max_velocity,
                    id="velocity-section"
                )
            
            # Right panel - dynamic modules
            with Vertical(id="right-panel"):
                # Render modules based on preset configuration
                yield from self._compose_modules()
        
        yield Footer()
    
    def _compose_modules(self) -> ComposeResult:
        """Compose widgets based on ui_modules configuration."""
        modules = self.ui_modules or ["event_log", "active_notes_panel"]
        
        for module in modules:
            if module == "event_log":
                yield EventLogWidget(id="event-log")
            elif module == "active_notes_panel":
                yield ActiveNotesPanel(id="active-notes-panel")
            elif module == "shortcut_guide":
                yield ShortcutGuide(id="shortcut-guide")
            elif module == "drum_pad_visualizer":
                yield DrumPadVisualizer(id="drum-pad-viz")
            elif module == "piano_keyboard_visualizer":
                yield PianoKeyboardVisualizer(id="piano-viz")
            # page_indicator is already in left panel
            # velocity_meter is already in left panel
    
    def _get_preset_options(self) -> List[tuple]:
        """Build available preset options for in-capture switching."""
        options: List[tuple] = []
        if hasattr(self.app, "config") and self.app.config:
            options = [(name, name) for name in sorted(self.app.config.list_presets())]
        return options

    def _get_status_text(self) -> Text:
        """Get styled status text."""
        if self.status == "CAPTURING":
            return Text("● CAPTURING", style="bold green")
        else:
            return Text("○ PASSTHROUGH", style="bold yellow")
    
    # Key bindings
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("f12", "toggle", "Toggle"),
        Binding("p", "panic", "Panic"),
        Binding("f9", "page_up", "Page Up"),
        Binding("f10", "page_down", "Page Down"),
    ]
    
    def on_mount(self) -> None:
        """Initialize the screen on mount - load preset and update UI."""
        logger.info("CaptureScreen mounted")

        if hasattr(self.app, "state_manager") and self.app.state_manager:
            self.status = "CAPTURING" if self.app.state_manager.is_captured else "PASSTHROUGH"

        self._update_status_display()
        self._load_preset_async()

        try:
            preset_select = self.query_one("#capture-preset-select", Select)
            if hasattr(self.app, "config") and self.app.config:
                preset_select.value = self.app.config.settings.last_used_preset
        except Exception:
            pass

        event_log = self._get_event_log()
        if event_log:
            event_log.write("[bold cyan]MIDITyper Capture Started[/bold cyan]")
            event_log.write("[dim]Press F12 to toggle capture mode[/dim]")

        self.set_interval(0.1, self._sync_active_notes)
        self._update_footer()
    
    def _load_preset_async(self) -> None:
        """Load the active preset and update UI reactively."""
        logger.debug("CaptureScreen loading active preset")

        # Try to get preset from app first (may already be loaded)
        preset = getattr(self.app, 'preset', None)
        
        if preset is None:
            # Try to load from config
            if hasattr(self.app, 'config') and self.app.config:
                try:
                    preset_name = self.app.config.settings.last_used_preset
                    preset = self.app.config.load_preset(preset_name)
                    self.app.preset = preset  # Cache for future use
                    logger.info("Loaded preset '%s' for capture", preset_name)
                except Exception as e:
                    # Fallback to default preset
                    self.preset_name = "Error loading preset"
                    logger.exception("Failed to load preset for capture: %s", e)
                    return
        
        if preset:
            self._apply_preset(preset)
    
    def _apply_preset(self, preset) -> None:
        """Apply the loaded preset to update the UI."""
        self._preset_loaded = True
        self.preset_name = preset.name
        
        # Update preset info display
        try:
            preset_info = self.query_one("#preset-info", Static)
            preset_info.update(f"[bold]Preset:[/bold] {preset.name}")
        except Exception:
            pass
        
        # Update page info
        self.total_pages = preset.page_count
        self.has_multiple_pages = preset.has_multiple_pages
        
        # Update page indicator
        try:
            page_indicator = self.query_one("#page-indicator", PageIndicator)
            page_indicator.total_pages = self.total_pages
        except Exception:
            pass
        
        # Store UI modules
        self.ui_modules = preset.ui_modules
        
        # Load velocity range from state manager or settings (Step 5.2)
        if hasattr(self.app, 'state_manager') and self.app.state_manager:
            self.min_velocity = getattr(self.app.state_manager, 'min_velocity', 100)
            self.max_velocity = getattr(self.app.state_manager, 'max_velocity', 100)
        elif hasattr(self.app, 'config') and self.app.config:
            self.min_velocity = self.app.config.settings.min_velocity
            self.max_velocity = self.app.config.settings.max_velocity
        
        # Update velocity controls and labels
        try:
            velocity_section = self.query_one("#velocity-section", VelocitySliderSection)
            velocity_section.min_velocity = self.min_velocity
            velocity_section.max_velocity = self.max_velocity
            velocity_section._update_display()
        except Exception:
            pass
        
        self._update_page_display()
        
        # Configure visualizer based on preset type
        self._configure_visualizer()
        
        # Log preset loaded
        try:
            event_log = self.query_one("#event-log", EventLogWidget)
            event_log.write(f"[green]Loaded preset: {preset.name}[/green]")
            if preset.has_multiple_pages:
                event_log.write(f"[dim]Pages: {preset.page_count} | Use F9/F10 to navigate[/dim]")
            event_log.write(f"[dim]Velocity: {self.min_velocity}-{self.max_velocity}[/dim]")
        except Exception:
            pass
    
    def watch_preset_name(self, old_value: str, new_value: str) -> None:
        """Watcher for preset_name reactive property - updates UI when preset name changes."""
        try:
            preset_info = self.query_one("#preset-info", Static)
            preset_info.update(f"[bold]Preset:[/bold] {new_value}")
        except Exception:
            pass
    
    def _update_footer(self) -> None:
        """Update the footer to show current shortcuts."""
        # Force footer refresh
        footer = self.query_one(Footer)
        footer._bindings = self.BINDINGS
    
    def _update_status_display(self) -> None:
        """Update the status indicator."""
        status_label = self.query_one("#status-indicator", Label)
        status_label.update(self._get_status_text())
    
    def _configure_visualizer(self) -> None:
        """Configure the appropriate visualizer based on preset."""
        preset = getattr(self.app, 'preset', None)
        if not preset:
            return
        
        current_page = preset.get_page(self.current_page)
        if not current_page:
            return
        
        mappings = current_page.mappings
        
        # Try to configure drum pad visualizer
        try:
            drum_viz = self.query_one("#drum-pad-viz", DrumPadVisualizer)
            drum_viz._mapping = mappings
            drum_viz._render()
        except Exception:
            pass
        
        # Try to configure piano visualizer
        try:
            piano_viz = self.query_one("#piano-viz", PianoKeyboardVisualizer)
            piano_viz._mapping = mappings
            piano_viz._render()
        except Exception:
            pass
    
    def _update_page_display(self) -> None:
        """Update the page display."""
        preset = getattr(self.app, 'preset', None)
        
        if preset:
            page = preset.get_page(self.current_page)
            self.page_name = page.name if page else f"Page {self.current_page + 1}"
        
        # Update page indicator
        page_indicator = self.query_one("#page-indicator", PageIndicator)
        page_indicator.current_page = self.current_page
        page_indicator.page_name = self.page_name
        
        # Configure visualizer for new page
        self._configure_visualizer()
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "btn-capture":
            self.action_toggle()
        elif event.button.id == "btn-kill":
            await self._kill_app()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle preset switching directly from capture toolbar."""
        if event.select.id != "capture-preset-select":
            return
        if not event.value:
            return

        if hasattr(self.app, "load_preset") and self.app.load_preset(event.value):
            self.current_page = 0
            self._load_preset_async()
            event_log = self._get_event_log()
            if event_log:
                event_log.write(f"[green]Loaded preset: {event.value}[/green]")

    def on_velocity_changed(self, event) -> None:
        """Handle VelocityChanged message from the velocity slider section."""
        self.min_velocity = event.min_velocity
        self.max_velocity = event.max_velocity
        
        # Update state manager if available
        if hasattr(self.app, 'state_manager') and self.app.state_manager:
            self.app.state_manager.min_velocity = self.min_velocity
            self.app.state_manager.max_velocity = self.max_velocity
            self.app.state_manager.set_velocity(self.app.state_manager.current_velocity)

        # Update config settings if available
        if hasattr(self.app, 'config') and self.app.config:
            self.app.config.settings.min_velocity = self.min_velocity
            self.app.config.settings.max_velocity = self.max_velocity

        # Update MIDI engine velocity range immediately
        if hasattr(self.app, 'midi_engine') and self.app.midi_engine:
            self.app.midi_engine.set_velocity_range(self.min_velocity, self.max_velocity)
        
        # Log the change
        try:
            event_log = self.query_one("#event-log", EventLogWidget)
            if self.min_velocity == self.max_velocity:
                event_log.write(f"[dim]Velocity: fixed at {self.min_velocity}[/dim]")
            else:
                event_log.write(f"[dim]Velocity: {self.min_velocity}-{self.max_velocity} (random)[/dim]")
        except Exception:
            pass
    
    async def action_back(self) -> None:
        """Return to main menu and force capture off."""
        logger.info("CaptureScreen back action triggered")
        await self._cleanup_and_exit()

    def action_toggle(self) -> None:
        """Toggle capture mode and synchronize input listener grab state."""
        logger.debug("CaptureScreen toggle requested from UI")
        if hasattr(self.app, "toggle_capture_mode"):
            captured = self.app.toggle_capture_mode()
            self.status = "CAPTURING" if captured else "PASSTHROUGH"
        else:
            self.status = "PASSTHROUGH" if self.status == "CAPTURING" else "CAPTURING"

        self._update_status_display()

        try:
            capture_btn = self.query_one("#btn-capture", Button)
            if self.status == "CAPTURING":
                capture_btn.label = "● Capture"
                capture_btn.remove_class("capturing")
            else:
                capture_btn.label = "○ Resume"
                capture_btn.add_class("capturing")
        except Exception:
            pass

        event_log = self._get_event_log()
        if event_log:
            event_log.write(f"[yellow]Mode: {self.status}[/yellow]")
    
    def action_page_up(self) -> None:
        """Go to next page."""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._update_page_display()
            event_log = self._get_event_log()
            if event_log:
                event_log.write(f"[cyan]Page: {self.page_name}[/cyan]")
    
    def action_page_down(self) -> None:
        """Go to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self._update_page_display()
            event_log = self._get_event_log()
            if event_log:
                event_log.write(f"[cyan]Page: {self.page_name}[/cyan]")
    
    def action_panic(self) -> None:
        """Send panic (all notes off)."""
        event_log = self._get_event_log()
        if event_log:
            event_log.write("[red]⚠ PANIC - All notes off[/red]")
        
        # Clear visualizer states
        try:
            drum_viz = self.query_one("#drum-pad-viz", DrumPadVisualizer)
            drum_viz._active_pads.clear()
            drum_viz._render()
        except Exception:
            pass
        
        try:
            piano_viz = self.query_one("#piano-viz", PianoKeyboardVisualizer)
            piano_viz._active_keys.clear()
            piano_viz._render()
        except Exception:
            pass
        
        # Call MIDI engine panic if available
        if hasattr(self.app, 'midi_engine') and self.app.midi_engine:
            self.app.midi_engine.panic()
    
    async def _kill_app(self) -> None:
        """Kill the application safely."""
        await self._cleanup_and_exit()

    async def _cleanup_and_exit(self) -> None:
        """Clean up and return to main menu with capture disabled."""
        logger.info("CaptureScreen cleanup started")

        if hasattr(self.app, 'midi_engine') and self.app.midi_engine:
            self.app.midi_engine.panic()

        if hasattr(self.app, 'stop_capture'):
            await self.app.stop_capture()

        logger.info("CaptureScreen cleanup complete, popping screen")
        self.app.pop_screen()
    
    def add_key_event(self, key_name: str, is_pressed: bool, note: str = "") -> None:
        """
        Add a key event to the log and update visualizers.
        
        Args:
            key_name: Name of the key pressed
            is_pressed: True for key down, False for key up
            note: Optional note name for MIDI events
        """
        event_log = self._get_event_log()
        if event_log is None:
            return

        action = "▼" if is_pressed else "▲"
        color = "green" if is_pressed else "red"
        
        if note:
            event_log.write(f"[{color}]{action} {key_name}[/{color}] → {note}")
        else:
            event_log.write(f"[{color}]{action} {key_name}[/{color}]")
        
        # Update visualizers
        try:
            drum_viz = self.query_one("#drum-pad-viz", DrumPadVisualizer)
            drum_viz.set_active_pad(key_name, is_pressed)
        except Exception:
            pass

    def _get_event_log(self) -> Optional[EventLogWidget]:
        """Return event log widget when present in current module layout."""
        try:
            return self.query_one("#event-log", EventLogWidget)
        except Exception:
            return None
        
        try:
            piano_viz = self.query_one("#piano-viz", PianoKeyboardVisualizer)
            piano_viz.set_active_key(key_name, is_pressed)
        except Exception:
            pass
    
    def _sync_active_notes(self) -> None:
        """Synchronize active notes panel from state manager."""
        state_manager = getattr(self.app, "state_manager", None)
        preset = getattr(self.app, "preset", None)
        if not state_manager or not preset:
            return

        active = state_manager.get_active_notes()
        page = preset.get_page(state_manager.current_page_index)
        note_names: List[str] = []
        if page:
            for note in active.keys():
                match = next((m.name for m in page.mappings.values() if m.note == note), None)
                note_names.append(match or str(note))
        self.update_active_notes(len(active), note_names)

    def update_active_notes(self, count: int, notes: List[str] = None) -> None:
        """
        Update the active notes display.

        Args:
            count: Number of active notes
            notes: List of note names (optional)
        """
        try:
            notes_panel = self.query_one("#active-notes-panel", ActiveNotesPanel)
            notes_panel.update_notes(notes or [])
        except Exception:
            pass
    
    def update_velocity_range(self, min_vel: int, max_vel: int) -> None:
        """
        Update the velocity range display.

        Args:
            min_vel: Minimum velocity
            max_vel: Maximum velocity
        """
        self.min_velocity = min_vel
        self.max_velocity = max_vel
        try:
            velocity_section = self.query_one("#velocity-section", VelocitySliderSection)
            velocity_section.min_velocity = min_vel
            velocity_section.max_velocity = max_vel
            velocity_section._update_display()
        except Exception:
            pass
    
    def update_state_from_manager(self) -> None:
        """Update display from state manager."""
        state_manager = getattr(self.app, 'state_manager', None)
        if not state_manager:
            return
        
        self.current_page = state_manager.current_page_index
        self.status = "CAPTURING" if state_manager.is_captured else "PASSTHROUGH"
        
        # Update velocity range
        self.min_velocity = getattr(state_manager, 'min_velocity', 100)
        self.max_velocity = getattr(state_manager, 'max_velocity', 100)
        
        self._update_status_display()
        self._update_page_display()
        self.update_velocity_range(self.min_velocity, self.max_velocity)

    def _sync_active_notes(self) -> None:
        """Periodic callback to sync active notes display from state manager."""
        if not hasattr(self.app, 'state_manager') or not self.app.state_manager:
            return
        if not hasattr(self.app, 'preset') or not self.app.preset:
            return

        active_notes = self.app.state_manager.get_active_notes()
        page_index = getattr(self.app.state_manager, 'current_page_index', 0)
        page = self.app.preset.get_page(page_index)
        note_names = []
        if page:
            for note in active_notes.keys():
                match = next((m.name for m in page.mappings.values() if m.note == note), None)
                note_names.append(match or str(note))

        try:
            self.update_active_notes(len(active_notes), note_names)
        except Exception:
            pass
