"""Regression coverage for Phase 6 capture/page/velocity fixes."""

from types import SimpleNamespace

from src.config_parser import ActionMapping, NoteMapping, Page, Preset
from src.input_listener import InputListener
from src.screens.capture_screen import CaptureScreen
from src.screens.mapping_dialogs import textual_key_to_evdev
from src.screens.preset_editor import normalize_key_name
from src.state_manager import StateManager
from src.tui import KeyboardMidiApp


class DummyStateManager:
    """Minimal state manager stub for capture mode tests."""

    def __init__(self, is_captured: bool = False) -> None:
        self.is_captured = is_captured
        self.calls: list[bool] = []

    def set_capture(self, captured: bool) -> None:
        self.is_captured = captured
        self.calls.append(captured)


class DummyInputListener:
    """Minimal listener stub for grab sync tests."""

    def __init__(self) -> None:
        self.sync_calls = 0

    def sync_grab_state(self) -> bool:
        self.sync_calls += 1
        return True


def test_set_capture_mode_syncs_grab_state() -> None:
    """Capture mode changes must always request listener grab sync."""
    app = SimpleNamespace(
        state_manager=DummyStateManager(is_captured=False),
        input_listener=DummyInputListener(),
    )

    result = KeyboardMidiApp.set_capture_mode(app, True)

    assert result is True
    assert app.state_manager.calls == [True]
    assert app.input_listener.sync_calls == 1


def test_toggle_capture_mode_flips_state_and_syncs() -> None:
    """Toggle should invert capture state and sync exactly once."""
    app = SimpleNamespace(
        state_manager=DummyStateManager(is_captured=True),
        input_listener=DummyInputListener(),
    )
    app.set_capture_mode = lambda captured: KeyboardMidiApp.set_capture_mode(
        app, captured
    )

    result = KeyboardMidiApp.toggle_capture_mode(app)

    assert result is False
    assert app.state_manager.calls == [False]
    assert app.input_listener.sync_calls == 1


def test_capture_page_actions_sync_state_manager_index() -> None:
    """Page navigation in capture screen must update state_manager page index."""
    state_manager = SimpleNamespace(current_page_index=0)
    screen = SimpleNamespace(
        current_page=0,
        total_pages=3,
        page_name="Page 1",
        app=SimpleNamespace(state_manager=state_manager),
    )
    screen._update_page_display = lambda: None
    screen._get_event_log = lambda: None

    CaptureScreen.action_page_up(screen)
    assert screen.current_page == 1
    assert state_manager.current_page_index == 1

    CaptureScreen.action_page_down(screen)
    assert screen.current_page == 0
    assert state_manager.current_page_index == 0


def test_velocity_limits_are_clamped_in_state_manager() -> None:
    """StateManager should clamp velocity limits to MIDI-safe values."""
    state = StateManager(min_velocity=-20, max_velocity=999)

    assert state.min_velocity == 1
    assert state.max_velocity == 127

    state.min_velocity = 12
    state.max_velocity = 90

    state.set_velocity(2)
    assert state.current_velocity == 12

    state.set_velocity(120)
    assert state.current_velocity == 90


def test_normalize_key_name_accepts_editor_input_variants() -> None:
    """Preset editor key names should normalize to evdev-compatible values."""
    assert normalize_key_name("a") == "KEY_A"
    assert normalize_key_name("KEY_A") == "KEY_A"
    assert normalize_key_name("space") == "KEY_SPACE"
    assert normalize_key_name(" key_enter ") == "KEY_ENTER"
    assert normalize_key_name("BTN_SOUTH") == "BTN_SOUTH"
    assert normalize_key_name("ABS_X") == "ABS_X"
    assert normalize_key_name("not_a_real_key") is None


def test_textual_key_conversion_supports_detection_flow() -> None:
    """Key-detect conversion should translate Textual keys to evdev names."""
    assert textual_key_to_evdev("escape") == "KEY_ESC"
    assert textual_key_to_evdev("a") == "KEY_A"
    assert textual_key_to_evdev("f12") == "KEY_F12"
    assert textual_key_to_evdev("ctrl+a") == "KEY_A"


def test_passthrough_ignores_note_mappings_but_allows_toggle_capture() -> None:
    """Passthrough should not send MIDI notes, but TOGGLE_CAPTURE must still work."""

    class DummyMidiEngine:
        def __init__(self) -> None:
            self.note_on_calls = 0

        def send_note_on(self, note: int, velocity: int, channel: int) -> None:
            self.note_on_calls += 1

        def send_note_off(self, note: int, channel: int) -> None:
            pass

        def panic(self) -> None:
            pass

    state = StateManager(is_captured=False)
    preset = Preset(
        name="Test",
        pages=[
            Page(
                name="Page 1",
                mappings={"KEY_A": NoteMapping(note=60, name="C4")},
            )
        ],
        global_actions={"KEY_F12": ActionMapping(action="TOGGLE_CAPTURE")},
    )
    state.set_active_preset(preset)

    midi = DummyMidiEngine()
    listener = InputListener(
        device_path="/dev/input/event0",
        state_manager=state,
        midi_engine=midi,
    )

    listener._process_key_event("KEY_A", 1)
    assert midi.note_on_calls == 0
    assert state.is_captured is False

    listener._process_key_event("KEY_F12", 1)
    assert state.is_captured is True
