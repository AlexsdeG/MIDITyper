"""Shared action catalog for mapping actions in presets and settings."""

from typing import List, Tuple


ACTION_CATALOG = [
    {
        "value": "TOGGLE_CAPTURE",
        "label": "Toggle Capture",
        "description": "Toggle capture and passthrough mode",
    },
    {
        "value": "PAGE_UP",
        "label": "Page Up",
        "description": "Go to next preset page",
    },
    {
        "value": "PAGE_DOWN",
        "label": "Page Down",
        "description": "Go to previous preset page",
    },
    {
        "value": "PANIC",
        "label": "Panic",
        "description": "Send all notes off",
    },
    {
        "value": "VELOCITY_UP",
        "label": "Velocity Up",
        "description": "Increase note velocity",
    },
    {
        "value": "VELOCITY_DOWN",
        "label": "Velocity Down",
        "description": "Decrease note velocity",
    },
    {
        "value": "QUIT",
        "label": "Quit",
        "description": "Trigger app quit flow",
    },
    {
        "value": "TRACK_SELECT_NEXT",
        "label": "Track Select Next",
        "description": "DAW: select next track",
    },
    {
        "value": "TRACK_SELECT_PREV",
        "label": "Track Select Previous",
        "description": "DAW: select previous track",
    },
    {
        "value": "TRACK_MUTE_TOGGLE",
        "label": "Track Mute Toggle",
        "description": "DAW: toggle mute on selected track",
    },
    {
        "value": "TRACK_SOLO_TOGGLE",
        "label": "Track Solo Toggle",
        "description": "DAW: toggle solo on selected track",
    },
    {
        "value": "LOOP_TOGGLE",
        "label": "Loop Toggle",
        "description": "DAW: toggle loop mode",
    },
    {
        "value": "LOOP_IN_SET",
        "label": "Set Loop In",
        "description": "DAW: set loop in point",
    },
    {
        "value": "LOOP_OUT_SET",
        "label": "Set Loop Out",
        "description": "DAW: set loop out point",
    },
    {
        "value": "LOOP_ENABLE",
        "label": "Loop Enable",
        "description": "DAW: force loop on",
    },
    {
        "value": "LOOP_DISABLE",
        "label": "Loop Disable",
        "description": "DAW: force loop off",
    },
    {
        "value": "ZOOM_IN",
        "label": "Zoom In",
        "description": "DAW: zoom in",
    },
    {
        "value": "ZOOM_OUT",
        "label": "Zoom Out",
        "description": "DAW: zoom out",
    },
    {
        "value": "MOVE_LEFT",
        "label": "Move Left",
        "description": "DAW: move/scroll left",
    },
    {
        "value": "MOVE_RIGHT",
        "label": "Move Right",
        "description": "DAW: move/scroll right",
    },
]


ALLOWED_ACTIONS: Tuple[str, ...] = tuple(
    item["value"] for item in ACTION_CATALOG
)


def get_action_select_options() -> List[Tuple[str, str]]:
    """Return action options for Textual Select widgets."""
    return [(item["label"], item["value"]) for item in ACTION_CATALOG]
