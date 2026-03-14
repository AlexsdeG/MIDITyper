## Project Context & Architecture
- **Goal:** Fix capture-page regressions by hardening input/capture lifecycle, correcting state synchronization, and upgrading velocity controls while preserving integer MIDI semantics.
- **Tech Stack:** Python 3.10+, Textual, evdev, mido, Pydantic v2.
- **Key Files:**
  - `src/screens/capture_screen.py`
  - `src/input_listener.py`
  - `src/tui.py`
  - `src/state_manager.py`
  - `src/screens/preset_editor.py`
  - `src/screens/main_menu.py`
  - `styles/app.tcss`
  - `src/config_parser.py`

---

## Execution Phases

### Phase 1: Baseline Diagnostics and Guardrails
- [x] **Step 1.1:** Add targeted capture lifecycle logging in `src/tui.py:189`, `src/tui.py:284`, `src/tui.py:289`, and `src/screens/capture_screen.py:786-870`.
  - **Verify:** Start capture, toggle mode, press ESC. Logs must show ordered lifecycle transitions from init to cleanup.
  - **Note:** Added lifecycle `logger.info` / `logger.debug` calls in `src/tui.py` (`initialize_capture_resources`, `start_capture`, `stop_capture`, `set_capture_mode`) and in `src/screens/capture_screen.py` (`on_mount`, preset loading, toggle, back, cleanup).

- [x] **Step 1.2:** Add defensive widget/query guards in `src/screens/capture_screen.py:551-559` and `src/screens/capture_screen.py:871-894` so capture does not crash when optional modules are not present.
  - **Verify:** Load a preset without `event_log`; screen renders and navigation still works.
  - **Note:** Added `_get_event_log()` helper with safe fallback and replaced direct event-log writes in mount, toggle, page change, panic, and key-event paths.

### Phase 2: Input Capture Correctness and Exclusivity
- [x] **Step 2.1:** Harden `grab()` / `ungrab()` error handling in `src/input_listener.py:118-138`; keep `_is_grabbed` consistent only on success.
  - **Verify:** Capture mode blocks key passthrough to other apps; passthrough mode restores normal typing.
  - **Note:** Added explicit `OSError` handling for `grab()` and `ungrab()` with state-safe `_is_grabbed` updates and structured error logging.

- [x] **Step 2.2:** Ensure grab-state synchronization is applied on all capture transitions in `src/tui.py:284-303` and `src/input_listener.py:431-433`.
  - **Verify:** `start_captured` true/false from settings is respected immediately upon capture entry.
  - **Note:** Removed `is_running` check in `set_capture_mode()` to ensure `sync_grab_state()` is always called on mode changes. The grab/ungrab methods already have device guards, making unconditional sync safe.

- [x] **Step 2.3:** Keep callback events for internal flow but suppress unmapped key logging in `src/tui.py:314-337` and `src/screens/capture_screen.py:871-894`.
  - **Verify:** Mapped key logs; unmapped key does not create a capture log line.
  - **Note:** Updated TUI key-event bridge to resolve mapping presence across page, preset-global actions/mappings, and app-global mappings before writing to capture event log.

### Phase 3: Velocity Controls and Initialization
- [x] **Step 3.1:** Keep integer velocity semantics and consistent clamping (1-127) in `src/screens/capture_screen.py:325-354`, `src/state_manager.py:178-189`, `src/config_parser.py:226-237`.
  - **Verify:** Invalid values are clamped safely without runtime errors.
  - **Note:** Added `__setattr__` override to StateManager to auto-clamp min/max_velocity to 1-127 range. Config Pydantic validation and VelocitySliderSection input clamping already enforce valid ranges.

- [x] **Step 3.2:** Upgrade `VelocitySliderSection` in `src/screens/capture_screen.py:249-325` to provide both editable numeric input and slider for min/max velocity.
  - **Verify:** Slider/input/value label stay synchronized for both min and max.
  - **Note:** Added visual slider bars with +/- buttons alongside numeric input fields. All three components (slider bar, buttons, input) update synchronously via `_update_display()` method.

- [x] **Step 3.3:** Ensure capture-page velocity initializes from global settings/state when opening capture in `src/screens/capture_screen.py:577-611`.
  - **Verify:** Changing settings min/max is reflected when opening capture.
  - **Note:** Added velocity range updates in tui.py reuse path to sync state_manager and midi_engine with current settings. CaptureScreen already loaded from state_manager in `_load_preset_async()`.

- [x] **Step 3.4:** Keep `Max Velocity` directly below `Min Velocity` in `src/screens/capture_screen.py:307-314` and `styles/app.tcss:239-283`.
  - **Verify:** Layout remains stable on narrow and wide terminals.
  - **Note:** Layout already correct from Step 3.2 implementation. VelocitySliderSection composes Min then Max rows sequentially in Vertical containers with proper height:auto and margin-bottom:1 spacing.

### Phase 4: Mapping and Page-State Reliability
- [x] **Step 4.1:** Remove duplicate `_sync_active_notes` and keep one authoritative implementation in `src/screens/capture_screen.py:901-1004`.
  - **Verify:** Active notes panel updates correctly with only one method definition.
  - **Note:** Removed duplicate method at end of file (line 1047). Kept first implementation at line 982 which uses cleaner `getattr` pattern and maintains same defensive behavior.

- [x] **Step 4.2:** Synchronize capture `current_page` with `state_manager.current_page_index` in `src/screens/capture_screen.py:689-708` and `src/screens/capture_screen.py:789-822`.
  - **Verify:** F9/F10 updates page display and actual key resolution page.
  - **Note:** Added bidirectional sync: load current_page from state_manager in `_load_preset_async()`, and update state_manager.current_page_index in `action_page_up()`, `action_page_down()`, and preset switching.

- [x] **Step 4.3:** Normalize key names from editor input in `src/screens/preset_editor.py:1018-1051` and confirm lookup compatibility with evdev key names in `src/input_listener.py:155-163`.
  - **Verify:** Add `KEY_A` mapping, save, reload, press `A`, and receive MIDI output.
  - **Note:** Added `normalize_key_name()` function that converts user input ('A', 'a', 'key_a') to proper evdev format ('KEY_A'). Validates against ecodes.KEY and ecodes.BTN. Applied in `_handle_key_input()` with error notification for invalid keys.

### Phase 5: ESC Return and Black-Screen Fix
- [x] **Step 5.1:** Stabilize cleanup ordering for ESC/back in `src/screens/capture_screen.py:860-870` and `src/tui.py:289-293`.
  - **Verify:** Repeated ESC always returns to visible main menu without blank frame.
  - **Note:** Added re-entry guard (`_is_exiting`) and cleanup ordering in `CaptureScreen._cleanup_and_exit()`: force passthrough first, panic, stop capture, then navigate.

- [x] **Step 5.2:** Add screen-stack safety checks for pop transitions in `src/screens/capture_screen.py:860-870` and `src/tui.py:101-104`.
  - **Verify:** No empty render state from back-navigation.
  - **Note:** Added fallback navigation to `main_menu` when stack depth is 1 in both `CaptureScreen._cleanup_and_exit()` and `KeyboardMidiApp.action_back()`.

- [x] **Step 5.3:** Confirm `MainMenuScreen` focus/render reliability on return in `src/screens/main_menu.py:124-126`.
  - **Verify:** `#btn-start` receives focus and UI remains visible after ESC return.
  - **Note:** Added `MainMenuScreen.on_show()` to refocus `#btn-start` whenever returning to the main menu.

### Phase 6: Regression Coverage
- [x] **Step 6.1:** Add tests for capture toggle/grab sync, page sync, and velocity clamp under `tests/`.
  - **Verify:** `pytest tests/ -v` passes.
  - **Note:** Added `tests/test_phase6_regression.py` with coverage for `set_capture_mode` sync behavior, toggle capture flow, capture page/state-manager sync, velocity clamping, and preset-editor key normalization. Verified with `pytest tests -v` (5 passed).

- [x] **Step 6.2:** Add manual QA checklist in `worklog.md` or `docs/` for exclusivity, unmapped-key behavior, mapping activation, velocity controls, and ESC stability.
  - **Verify:** Checklist can be executed end-to-end on Linux.
  - **Note:** Added a Linux-focused manual QA checklist under `Task ID: 3` in `worklog.md` covering exclusivity, passthrough restore, unmapped key logging, mapping activation, page sync, velocity controls, and ESC return stability.

---

## Decisions Applied
- Velocity UI remains integer-only.
- Capture-on-entry respects `start_captured`.
- Unmapped keys should not be logged in capture event log.

### Phase 7: Capture Startup Reliability (In Progress)
- [x] **Step 7.1:** Add input-listener startup readiness handshake so capture start only succeeds after device open/grab attempt completes.
  - **Verify:** Listener returns failure when grab fails instead of optimistic success.
  - **Note:** Implemented readiness event and timeout in `src/input_listener.py` (`start`, `_event_loop`) with startup error propagation.

- [x] **Step 7.2:** Gate capture-screen navigation on capture start success.
  - **Verify:** Main menu does not open capture screen when listener startup fails.
  - **Note:** Updated `src/screens/main_menu.py` to require `start_capture()` success before `push_screen("capture")`.

- [x] **Step 7.3:** Force passthrough fallback when capture sync fails.
  - **Verify:** Failed capture-mode sync no longer leaves UI in a false-capturing state.
  - **Note:** Updated `src/tui.py::set_capture_mode` to detect failed sync and revert to passthrough with warnings.
