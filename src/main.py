#!/usr/bin/env python3
"""
MIDITyper - Keyboard to MIDI Converter

A highly modular, multi-screen TUI application that intercepts physical
keyboard inputs via evdev, translates them into MIDI messages, and sends
them to a virtual MIDI port.

Usage:
    python -m src.main start           # Start the TUI application
    python -m src.main list-presets    # List available presets
    python -m src.main set-preset NAME # Set active preset
    python -m src.main list-devices    # List input devices
    python -m src.main --help          # Show help
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .config_parser import AppConfig, load_config
from .input_listener import find_keyboard_device, list_input_devices

# Initialize Typer app
app = typer.Typer(
    name="midityper",
    help="MIDITyper - Keyboard to MIDI Converter",
    add_completion=False
)

# Rich console for pretty output
console = Console()

# Configure logging
def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S"
    )


@app.command()
def start(
    preset: Optional[str] = typer.Option(
        None,
        "--preset", "-p",
        help="Preset name to use (e.g., default_piano, default_drums)"
    ),
    device: Optional[str] = typer.Option(
        None,
        "--device", "-d",
        help="Input device path (e.g., /dev/input/event0)"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose logging"
    )
) -> None:
    """
    Start the MIDITyper TUI application.
    
    This launches the multi-screen Textual interface with:
    - Main Menu for navigation
    - Capture Screen for MIDI conversion
    - Settings Screen for configuration
    - Preset Editor for creating/editing presets
    """
    setup_logging(verbose)
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = load_config()
        
        # Override preset if specified
        if preset:
            try:
                config.settings.last_used_preset = preset
                console.print(f"[green]Will use preset: {preset}[/green]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                raise typer.Exit(1)
        
        # Override device if specified
        if device:
            config.settings.default_device_path = device
            config.settings.auto_detect_device = False
            console.print(f"[cyan]Will use device: {device}[/cyan]")
        
        # Import and run TUI
        from .tui import run_tui
        
        console.print("[cyan]Starting MIDITyper...[/cyan]")
        run_tui(config)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("list-presets")
def list_presets(
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Show detailed preset information"
    )
) -> None:
    """
    List all available keyboard presets.
    
    Shows the preset names, descriptions, page counts, and UI modules.
    """
    config = load_config()
    
    # Create table
    table = Table(title="Available Presets")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Pages", style="green")
    table.add_column("UI Modules", style="yellow")
    
    last_preset = config.settings.last_used_preset
    
    for name in config.list_presets():
        try:
            preset = config.load_preset(name)
            active_marker = " [bold](active)[/bold]" if name == last_preset else ""
            
            modules_str = ", ".join(preset.ui_modules[:2])
            if len(preset.ui_modules) > 2:
                modules_str += f" +{len(preset.ui_modules) - 2}"
            
            table.add_row(
                f"{name}{active_marker}",
                preset.description[:40] + ("..." if len(preset.description) > 40 else ""),
                str(preset.page_count),
                modules_str
            )
        except Exception as e:
            table.add_row(name, f"[red]Error: {e}[/red]", "-", "-")
    
    console.print(table)
    
    if verbose:
        console.print("\n[bold]Detailed Preset Information:[/bold]")
        for name in config.list_presets():
            try:
                preset = config.load_preset(name)
                console.print(f"\n[cyan]{name}:[/cyan]")
                console.print(f"  Name: {preset.name}")
                console.print(f"  Description: {preset.description}")
                console.print(f"  UI Modules: {preset.ui_modules}")
                console.print(f"  Pages ({preset.page_count}):")
                for i, page in enumerate(preset.pages):
                    console.print(f"    [{i}] {page.name}: {len(page.mappings)} mappings")
                console.print(f"  Global Actions: {list(preset.global_actions.keys())}")
            except Exception as e:
                console.print(f"\n[red]{name}: Error loading - {e}[/red]")


@app.command("set-preset")
def set_preset(
    preset_name: str = typer.Argument(
        ...,
        help="Name of the preset to set as active"
    )
) -> None:
    """
    Set the active keyboard preset.
    
    This updates the last_used_preset in settings.
    """
    config = load_config()
    
    # Check if preset exists
    if preset_name not in config.list_presets():
        console.print(f"[red]Preset not found: {preset_name}[/red]")
        console.print("[yellow]Available presets:[/yellow]")
        for name in config.list_presets():
            console.print(f"  - {name}")
        raise typer.Exit(1)
    
    # Set as active
    config.settings.last_used_preset = preset_name
    config.save_settings()
    
    preset = config.load_preset(preset_name)
    console.print(f"[green]Active preset set to: {preset_name}[/green]")
    console.print(f"  Name: {preset.name}")
    console.print(f"  Pages: {preset.page_count}")
    console.print(f"  UI Modules: {preset.ui_modules}")


@app.command("list-devices")
def list_devices() -> None:
    """
    List all available input devices.
    
    Shows device paths and names that can be used with --device option.
    """
    console.print("[cyan]Scanning for input devices...[/cyan]\n")
    
    try:
        devices = list_input_devices()
    except PermissionError:
        console.print("[red]Permission denied accessing input devices![/red]")
        console.print("[yellow]Add your user to the 'input' group:[/yellow]")
        console.print("  [bold]sudo usermod -aG input $USER[/bold]")
        console.print("[yellow]Then log out and back in for changes to take effect.[/yellow]")
        raise typer.Exit(1)
    
    if not devices:
        console.print("[yellow]No input devices found.[/yellow]")
        console.print("This could mean:")
        console.print("  - No input devices are connected")
        console.print("  - You don't have permission to access /dev/input/")
        return
    
    # Create table
    table = Table(title="Input Devices")
    table.add_column("Path", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Vendor", style="yellow")
    table.add_column("Product", style="green")
    
    for dev in devices:
        table.add_row(
            dev["path"],
            dev["name"][:40],
            dev["vendor"],
            dev["product"]
        )
    
    console.print(table)
    
    # Try to auto-detect keyboard
    keyboard = find_keyboard_device()
    if keyboard:
        console.print(f"\n[green]Auto-detected keyboard: {keyboard}[/green]")


@app.command("info")
def info() -> None:
    """
    Show current configuration and status.
    """
    config = load_config()
    
    console.print("[bold]MIDITyper Configuration[/bold]\n")
    
    # Settings
    console.print("[cyan]Settings:[/cyan]")
    console.print(f"  Device Path: {config.settings.default_device_path or '(auto-detect)'}")
    console.print(f"  Auto Detect: {config.settings.auto_detect_device}")
    console.print(f"  Virtual Port: {config.settings.virtual_port_name}")
    console.print(f"  Default Velocity: {config.settings.default_velocity}")
    console.print(f"  Theme: {config.settings.theme}")
    console.print()
    
    console.print("[cyan]Last Used Preset:[/cyan]")
    console.print(f"  {config.settings.last_used_preset}")
    console.print()
    
    # Available presets
    console.print("[cyan]Available Presets:[/cyan]")
    for name in config.list_presets():
        try:
            preset = config.load_preset(name)
            active = " (active)" if name == config.settings.last_used_preset else ""
            console.print(f"  - {name}{active}: {preset.page_count} pages")
        except Exception:
            console.print(f"  - {name}: [red]Error loading[/red]")


@app.command("create-preset")
def create_preset(
    name: str = typer.Argument(..., help="Name for the new preset"),
    pages: int = typer.Option(1, "--pages", "-n", help="Number of pages to create")
) -> None:
    """
    Create a new empty preset.
    
    The preset will be saved to data/presets/<name>.json
    """
    from .config_parser import Preset, Page
    
    config = load_config()
    
    # Check if preset already exists
    safe_name = name.lower().replace(" ", "_").replace("-", "_")
    if safe_name in config.list_presets():
        console.print(f"[red]Preset already exists: {safe_name}[/red]")
        raise typer.Exit(1)
    
    # Create preset
    preset_obj = Preset(
        name=name,
        description=f"Custom preset: {name}",
        ui_modules=["event_log", "active_notes_panel"],
        pages=[Page(name=f"Page {i+1}") for i in range(pages)]
    )
    
    # Save preset
    config.save_preset(safe_name, preset_obj)
    console.print(f"[green]Created preset: {safe_name}[/green]")
    console.print(f"  File: data/presets/{safe_name}.json")
    console.print(f"  Pages: {pages}")
    console.print("\n[yellow]Edit the preset file to add key mappings, or use the Preset Editor in the app.[/yellow]")


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
