"""Regression tests for shutdown and global quit behavior."""

import asyncio
from types import SimpleNamespace

from evdev import ecodes

from src.config_parser import ActionMapping, NoteMapping, Page, Preset, Settings
from src.input_listener import InputListener, KeyEvent
from src.screens.capture_screen import CaptureScreen
from src.state_manager import StateManager


class DummyMidiEngine:
    """Minimal MIDI stub for input-listener tests."""

    def __init__(self) -> None:
        self.note_on_calls = 0
        self.note_off_calls = 0
        self.panic_calls = 0

    def send_note_on(self, note: int, velocity: int, channel: int) -> None:
        self.note_on_calls += 1

    def send_note_off(self, note: int, channel: int) -> None:
        self.note_off_calls += 1

    def panic(self) -> None:
        self.panic_calls += 1

    def send_daw_action(self, action: str) -> None:
        pass


def _build_state(is_captured: bool, global_actions: dict[str, ActionMapping]) -> StateManager:
    """Build a StateManager with a simple preset for action tests."""
    state = StateManager(is_captured=is_captured)
    preset = Preset(
        name="Test",
        pages=[
            Page(
                name="Page 1",
                mappings={"KEY_A": NoteMapping(note=60, name="C4")},
            )
        ],
        global_actions=global_actions,
    )
    state.set_active_preset(preset)
    return state


def test_quit_action_invokes_quit_callback() -> None:
    """QUIT mapping should call the app quit callback."""
    quit_calls = {"count": 0}

    def on_quit() -> None:
        quit_calls["count"] += 1

    state = _build_state(True, {"KEY_ESC": ActionMapping(action="QUIT")})
    midi = DummyMidiEngine()
    listener = InputListener(
        device_path="/dev/input/event0",
        state_manager=state,
        midi_engine=midi,
        on_quit=on_quit,
    )

    listener._process_key_event("KEY_ESC", KeyEvent.KEY_DOWN)

    assert quit_calls["count"] == 1


def test_passthrough_allows_quit_and_panic_actions() -> None:
    """Passthrough mode should execute QUIT and PANIC shutdown actions."""
    quit_calls = {"count": 0}

    def on_quit() -> None:
        quit_calls["count"] += 1

    state = _build_state(
        False,
        {
            "KEY_ESC": ActionMapping(action="QUIT"),
            "KEY_P": ActionMapping(action="PANIC"),
        },
    )
    midi = DummyMidiEngine()
    listener = InputListener(
        device_path="/dev/input/event0",
        state_manager=state,
        midi_engine=midi,
        on_quit=on_quit,
    )

    listener._process_key_event("KEY_ESC", KeyEvent.KEY_DOWN)
    listener._process_key_event("KEY_P", KeyEvent.KEY_DOWN)
    listener._process_key_event("KEY_A", KeyEvent.KEY_DOWN)

    assert quit_calls["count"] == 2
    assert midi.panic_calls == 1
    assert midi.note_on_calls == 0


def test_passthrough_allows_page_navigation_actions() -> None:
    """Passthrough mode should still allow PAGE_UP/PAGE_DOWN actions."""
    state = _build_state(
        False,
        {
            "KEY_F9": ActionMapping(action="PAGE_UP"),
            "KEY_F10": ActionMapping(action="PAGE_DOWN"),
        },
    )
    state.active_preset.pages.append(
        Page(name="Page 2", mappings={"KEY_B": NoteMapping(note=62, name="D4")})
    )
    midi = DummyMidiEngine()
    listener = InputListener(
        device_path="/dev/input/event0",
        state_manager=state,
        midi_engine=midi,
    )

    assert state.current_page_index == 0
    listener._process_key_event("KEY_F9", KeyEvent.KEY_DOWN)
    assert state.current_page_index == 1
    listener._process_key_event("KEY_F10", KeyEvent.KEY_DOWN)
    assert state.current_page_index == 0


def test_ctrl_q_shortcut_triggers_quit_only_while_captured() -> None:
    """Ctrl+Q shortcut should trigger quit only in captured mode."""
    quit_calls = {"count": 0}

    def on_quit() -> None:
        quit_calls["count"] += 1

    state = _build_state(True, {})
    midi = DummyMidiEngine()
    listener = InputListener(
        device_path="/dev/input/event0",
        state_manager=state,
        midi_engine=midi,
        on_quit=on_quit,
    )

    listener._update_modifier_state("KEY_LEFTCTRL", KeyEvent.KEY_DOWN)
    handled = listener._handle_global_shortcuts("KEY_Q", KeyEvent.KEY_DOWN)
    assert handled is True
    assert quit_calls["count"] == 1

    state.set_capture(False)
    handled = listener._handle_global_shortcuts("KEY_Q", KeyEvent.KEY_DOWN)
    assert handled is False
    assert quit_calls["count"] == 1


def test_caps_lock_shortcut_triggers_capture_toggle() -> None:
    """Caps Lock should always act as a capture toggle shortcut."""
    toggle_calls = {"count": 0}

    def on_toggle_capture() -> bool:
        toggle_calls["count"] += 1
        return True

    state = _build_state(False, {})
    midi = DummyMidiEngine()
    listener = InputListener(
        device_path="/dev/input/event0",
        state_manager=state,
        midi_engine=midi,
        on_toggle_capture=on_toggle_capture,
    )

    handled = listener._handle_global_shortcuts("KEY_CAPSLOCK", KeyEvent.KEY_DOWN)

    assert handled is True
    assert toggle_calls["count"] == 1


def test_caps_lock_shortcut_respects_disabled_setting() -> None:
    """Caps Lock shortcut should be disabled when setting is false."""
    toggle_calls = {"count": 0}

    def on_toggle_capture() -> bool:
        toggle_calls["count"] += 1
        return True

    state = _build_state(False, {})
    midi = DummyMidiEngine()
    settings = Settings(caps_lock_capture_toggle_enabled=False)
    listener = InputListener(
        device_path="/dev/input/event0",
        state_manager=state,
        midi_engine=midi,
        settings=settings,
        on_toggle_capture=on_toggle_capture,
    )

    handled = listener._handle_global_shortcuts("KEY_CAPSLOCK", KeyEvent.KEY_DOWN)

    assert handled is False
    assert toggle_calls["count"] == 0


def test_update_grab_state_syncs_caps_lock_led() -> None:
    """Capture state sync should update Caps Lock LED on/off."""

    class DummyDevice:
        def __init__(self) -> None:
            self.calls: list[tuple[int, int]] = []

        def set_led(self, led_code: int, value: int) -> None:
            self.calls.append((led_code, value))

    state = _build_state(False, {})
    midi = DummyMidiEngine()
    listener = InputListener(
        device_path="/dev/input/event0",
        state_manager=state,
        midi_engine=midi,
    )

    device = DummyDevice()
    listener._device = device
    listener._is_grabbed = True
    listener._ungrab_device = lambda: None  # type: ignore[method-assign]
    listener._send_all_notes_off = lambda: None  # type: ignore[method-assign]

    listener._update_grab_state()

    assert (ecodes.LED_CAPSL, 0) in device.calls


def test_capture_back_cleanup_uses_shared_app_shutdown() -> None:
    """Capture back flow should call shared shutdown-to-menu handler."""
    calls = {"count": 0}

    async def shutdown_to_main_menu() -> None:
        calls["count"] += 1

    screen = SimpleNamespace(
        _is_exiting=False,
        app=SimpleNamespace(shutdown_to_main_menu=shutdown_to_main_menu),
    )

    asyncio.run(CaptureScreen._cleanup_and_exit(screen))

    assert calls["count"] == 1
    assert screen._is_exiting is False


def test_capture_kill_button_uses_shared_app_exit_shutdown() -> None:
    """Capture kill path should call shared shutdown-and-exit handler."""
    calls = {"count": 0}

    async def shutdown_and_exit() -> None:
        calls["count"] += 1

    screen = SimpleNamespace(app=SimpleNamespace(shutdown_and_exit=shutdown_and_exit))

    asyncio.run(CaptureScreen._kill_app(screen))

    assert calls["count"] == 1


def test_app_back_uses_capture_shutdown_path() -> None:
    """App back action should not bypass capture cleanup on capture screen."""
    calls = {"run_worker": 0}

    async def shutdown_to_main_menu() -> None:
        return None

    def run_worker(coro, **kwargs):
        calls["run_worker"] += 1
        coro.close()

    app = SimpleNamespace(
        screen=CaptureScreen(),
        run_worker=run_worker,
        shutdown_to_main_menu=shutdown_to_main_menu,
        screen_stack=[object(), object()],
        pop_screen=lambda: None,
        switch_screen=lambda _: None,
    )

    from src.tui import KeyboardMidiApp

    KeyboardMidiApp.action_back(app)

    # action_back should queue shutdown_to_main_menu via run_worker in capture context
    assert calls["run_worker"] == 1
