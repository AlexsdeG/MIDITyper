### 1. Project Context & Architecture
- **Goal:** Resolve major UI/UX bugs in the Settings and Capture screens, and expand the configuration architecture to support app-wide globals, preset-wide globals, page renaming, and randomized velocity ranges. Refactor layout structures to fix squished elements and properly render Rich text markup.
- **Tech Stack & Dependencies:**
  - Language: Python 3.10+
  - Dependencies: `pip install evdev mido python-rtmidi textual typer pydantic` (No new dependencies, strictly utilizing Textual's built-in widgets).
- **File Structure:** 
  ```text
  keyboard2midi/
  ├── data/
  │   └── settings.json
  ├── src/
  │   ├── config_parser.py        # Updated for global mappings & velocity ranges
  │   ├── midi_engine.py          # Updated to calculate random velocity
  │   ├── input_listener.py       # Updated to cascade global keybind resolutions
  │   └── screens/
  │       ├── capture_screen.py   # Fixed loading state, RichLog markup, and Sliders
  │       ├── settings_screen.py  # Fixed CSS scaling, Select widgets, added global binds
  │       └── preset_editor.py    # Added page rename, mapping CRUD logic
  └── styles/
      └── app.tcss                # Centralized CSS updates for heights/spacing
  ```
- **Attention Points:**
  - **CSS Refactor:** Textual uses `.tcss`. Squished settings items and oversized toolbars are CSS issues (e.g., missing `height: auto` or bad `fr` fraction distribution).
  - **Keybind Resolution Order:** `input_listener.py` must resolve keys in this exact order: Page Mappings -> Preset Global Mappings -> App Global Mappings. 
  - **State Race Condition:** The "Loading..." bug in `CaptureScreen` is caused by blocking synchronous file reads in `on_mount`. State loading must be awaited or handled via Textual's reactive variables correctly.

---

### 2. Execution Phases

#### Phase 1: Pydantic Schema & App-Global Architecture
- [x] **Step 1.1:** In `src/config_parser.py`, update the `Preset` model to include `global_mappings: Dict[str, dict] = {}`. Update the `Page` model to ensure `name` is mutable. Update the `Settings` model to include `app_global_mappings: Dict[str, dict] = {}`.
- [x] **Step 1.2:** In the same file, update the state models for velocity to support ranges: change `default_velocity` to `min_velocity: int = 100` and `max_velocity: int = 100`.
- [x] **Step 1.3:** In `src/input_listener.py`, update the event resolution logic. When a key is pressed, check the Active Page's mappings. If not found, fallback to `preset.global_mappings`. If still not found, fallback to `settings.app_global_mappings`.
- [x] **Verification:** Run a Python script importing `Settings` and `Preset`, instantiate them with the new fields (`app_global_mappings`, `min_velocity`, `max_velocity`), and print the validated JSON schema to ensure Pydantic accepts the changes.

#### Phase 2: Settings Screen Layout & Inputs Fixes
- [x] **Step 2.1:** In `styles/app.tcss`, target the `SettingsScreen` containers. Remove fixed heights that cause squishing. Apply `height: auto; margin-bottom: 1;` to input rows to allow natural spacing.
- [x] **Step 2.2:** In `src/screens/settings_screen.py`, replace the broken Virtual MIDI Port Name and Auto-detect keyboard inputs with Textual `Select` widgets. Populate options dynamically (e.g., `[("Port 1", "port_1"), ("New Virtual Port", "new_virtual")]`).
- [x] **Step 2.3:** In `src/screens/settings_screen.py`, append a new section below the main settings for "App-Global Keybinds" utilizing a `DataTable` and basic Add/Delete buttons to mutate `settings.app_global_mappings`.
- [x] **Verification:** Launch the app, navigate to Settings. Verify the items are visually spaced correctly without squishing. Verify the `Select` widgets open drop-downs successfully.

#### Phase 3: Preset Editor CRUD & Toolbar UI
- [x] **Step 3.1:** In `styles/app.tcss`, target the Preset Editor top toolbar. Set `height: 3;` or `height: auto;` to reduce its footprint.
- [x] **Step 3.2:** In `src/screens/preset_editor.py`, locate the "Pages" tab. Add an `Input` widget next to the Page Select list. Bind its `on_input_changed` or `on_input_submitted` event to update the active `page.name` in the Pydantic model.
- [x] **Step 3.3:** In the Key Mappings `DataTable`, implement Textual event listeners for the "Edit Selected" and "Delete Selected" buttons. When "Delete Selected" is pressed, remove the mapped key from the `page.mappings` dictionary and refresh the `DataTable`.
- [x] **Step 3.4:** Add a new section/tab in the Preset Editor specifically for "Preset Global Actions". Wire it to mutate `preset.global_mappings`.
- [x] **Verification:** Launch the app -> Preset Editor. Select a preset. Rename a page and verify the UI updates. Add a mapping, select it, click "Delete Selected", and verify it disappears from the table.

#### Phase 4: Capture Screen Critical Fixes (Loading & Log)
- [x] **Step 4.1:** In `src/screens/capture_screen.py`, locate the `RichLog` widget initialization. You must explicitly set `markup=True` (e.g., `RichLog(markup=True)`) to parse the `[bold cyan]` tags.
- [x] **Step 4.2:** Fix the "Loading..." bug in `CaptureScreen`. Ensure the `on_mount` method asynchronously loads the preset via `self.preset = AppConfig.load_active_preset()`. Ensure the UI labels (e.g., `self.query_one("#preset_name_label").update(...)`) are updated directly inside the `on_mount` or via a reactive variable watcher (`watch_preset`).
- [x] **Verification:** Launch the app -> Capture Screen. Verify the "Preset:" label updates instantly from "Loading..." to the actual preset name. Trigger a key event and verify the log shows colored text, NOT raw `[bold]` brackets.

#### Phase 5: Capture Screen Velocity Sliders & Toolbar
- [x] **Step 5.1:** In `src/screens/capture_screen.py`, completely remove the current Velocity widget.
- [x] **Step 5.2:** Yield two Textual `Slider` widgets configured for velocity (`min=1, max=127`). Label them "Min Velocity" and "Max Velocity". Bind their `on_slider_changed` events to update `state_manager.min_velocity` and `state_manager.max_velocity`.
- [x] **Step 5.3:** In `src/midi_engine.py`, import the `random` module. Update the `send_note_on` function to accept min/max bounds and calculate `velocity = random.randint(min_vel, max_vel)`.
- [x] **Step 5.4:** In `src/screens/capture_screen.py`, remove the Kill button from the bottom footer. Create a `Horizontal` container at the very top of the screen (Top Toolbar).
- [x] **Step 5.5:** Yield a "Capture / Stop" button and a "Kill / Exit" button inside this new Top Toolbar container. Bind "Capture / Stop" to toggle the `evdev` exclusive grab state.
- [x] **Verification:** Launch Capture Screen. Verify the buttons are at the top. Adjust the Min and Max velocity sliders with the mouse. Press a mapped key multiple times and use `aseqdump` in the terminal to verify the outgoing MIDI velocity randomly fluctuates between the defined slider bounds.

---

### 3. Global Testing Strategy
- **Resolution Hierarchy Test:** Map `KEY_F12` to `OCTAVE_UP` in App Globals. Map `KEY_F12` to `PANIC` in Preset Globals. Map `KEY_F12` to `NOTE_60` in the Active Page. Press `KEY_F12`. Verify it *only* triggers `NOTE_60` (Page overrides Preset, Preset overrides App).
- **CSS Responsiveness:** Resize the terminal window vertically while in the Settings screen. Verify the elements do not overlap or squish together in unreadable ways, utilizing scrolling if necessary.
- **Velocity Inversion Defense:** Move the "Min Velocity" slider to 100, and the "Max Velocity" slider to 50. Press a mapped key. The application (`midi_engine.py`) must handle this gracefully (e.g., automatically swapping min/max or clamping) without throwing a `ValueError: empty range for randrange()`.
