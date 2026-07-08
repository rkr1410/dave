"""Hardcoded first-pass Textual palette."""

# Gruvbox dark-ish colors. Keep this as constants until multiple themes justify
# a real theme/config system.
BACKGROUND = "#282828"
PANEL = BACKGROUND
PANEL_BORDER = "#3c3836"
INPUT_BORDER = "#d5c4a1"
TEXT = "#ebdbb2"
MUTED = "#928374"

USER = "#83a598"
ASSISTANT = "#b8bb26"
REASONING = "#fabd2f"
STATUS = "#d3869b"
INFO = "#458588"
WARNING = "#fe8019"
ERROR = "#fb4934"

USER_LABEL = f"bold {USER}"
ASSISTANT_LABEL = f"bold {ASSISTANT}"
REASONING_LABEL = f"bold {REASONING}"
REASONING_LABEL_PULSE_STYLES = (
    f"bold {REASONING}",
    "bold #e3b64b",
    f"bold {INPUT_BORDER}",
    "bold #e3b64b",
)
STATUS_LABEL = f"bold {STATUS}"

REASONING_CONTENT = f"dim {REASONING}"
CANCELLED_CONTENT = f"dim {MUTED}"
FAILED_CONTENT = ERROR

STREAMING_STATE = f"italic {INFO}"
FAILED_STATE = f"bold {ERROR}"
CANCELLED_STATE = f"italic {WARNING}"

STATUS_TEXT_LABEL = "bold"
STATUS_IDLE = f"dim {MUTED}"
STATUS_ACTIVE = INFO
STATUS_CANCELLED = WARNING
STATUS_FAILED = ERROR
