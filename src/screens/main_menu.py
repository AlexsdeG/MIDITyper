"""
Main Menu Screen for MIDITyper.

This is the landing screen that provides navigation to:
- Start Capture (Capture Screen)
- Preset Editor
- Settings
- Quit
"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Header, Footer, Static, Label


class MenuButton(Button):
    """Styled button for menu options."""
    
    DEFAULT_CSS = """
    MenuButton {
        width: 100%;
        min-height: 3;
        margin: 1 0;
    }
    """
    
    def __init__(self, label: str, variant: str = "default", **kwargs):
        super().__init__(label, variant=variant, **kwargs)


class MainMenuScreen(Screen):
    """
    Main menu screen with navigation buttons.
    
    This is the first screen shown when the app starts.
    Users can navigate to other screens or quit the app.
    """
    
    CSS = """
    MainMenuScreen {
        align: center middle;
    }
    
    #menu-container {
        width: 60;
        height: auto;
        padding: 2;
        border: solid $primary;
        border-title-align: center;
    }
    
    #title-container {
        text-align: center;
        margin-bottom: 2;
    }
    
    #app-title {
        text-style: bold;
        color: $primary;
        text-align: center;
    }
    
    #app-subtitle {
        color: $text-muted;
        text-align: center;
    }
    
    #button-container {
        width: 100%;
    }
    
    .menu-button-start {
        background: $success;
        color: white;
    }
    
    .menu-button-start:hover {
        background: $success-lighten-1;
    }
    
    .menu-button-quit {
        background: $error;
        color: white;
    }
    
    .menu-button-quit:hover {
        background: $error-lighten-1;
    }
    
    #footer-info {
        text-align: center;
        color: $text-muted;
        margin-top: 2;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "start", "Start Capture"),
        ("p", "presets", "Presets"),
        ("o", "settings", "Settings"),
    ]
    
    def compose(self) -> ComposeResult:
        """Create the main menu layout."""
        yield Header()
        
        with Container(id="menu-container"):
            with Vertical(id="title-container"):
                yield Label("🎹 MIDITyper", id="app-title")
                yield Label("Keyboard to MIDI Converter", id="app-subtitle")
            
            with Vertical(id="button-container"):
                yield MenuButton("▶ Start Capture", variant="success", id="btn-start")
                yield MenuButton("📝 Preset Editor", variant="primary", id="btn-presets")
                yield MenuButton("⚙ Settings", variant="primary", id="btn-settings")
                yield MenuButton("✕ Quit", variant="error", id="btn-quit")
            
            yield Static("Press a key or click a button", id="footer-info")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Focus the first button when screen mounts."""
        self.query_one("#btn-start").focus()

    def on_show(self) -> None:
        """Restore focus when returning from other screens."""
        try:
            self.query_one("#btn-start").focus()
        except Exception:
            pass
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id
        
        if button_id == "btn-start":
            self.run_worker(self.action_start())
        elif button_id == "btn-presets":
            self.action_presets()
        elif button_id == "btn-settings":
            self.action_settings()
        elif button_id == "btn-quit":
            self.action_quit()
    
    async def action_start(self) -> None:
        """Initialize capture resources and navigate to Capture screen."""
        initialized = await self.app.initialize_capture_resources()
        if not initialized:
            return

        await self.app.start_capture()
        self.app.push_screen("capture")
    
    def action_presets(self) -> None:
        """Navigate to Preset Editor screen."""
        self.app.push_screen("preset_editor")
    
    def action_settings(self) -> None:
        """Navigate to Settings screen."""
        self.app.push_screen("settings")
    
    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
