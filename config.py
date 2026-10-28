"""Central configuration for the Multimodal Attendance & Engagement Agent.

Every tunable value lives here so no magic numbers are scattered through the
code base. Values marked "(later phase)" are defined now so the configuration
file stays stable, and are consumed by modules built in later phases.
"""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent
DATA_DIRECTORY: Path = BASE_DIR / "data"
STUDENTS_DIRECTORY: Path = DATA_DIRECTORY / "students"
SESSIONS_DIRECTORY: Path = DATA_DIRECTORY / "sessions"
DATABASE_DIRECTORY: Path = DATA_DIRECTORY / "database"
DATABASE_PATH: Path = DATABASE_DIRECTORY / "attendance_agent.db"
MODELS_DIRECTORY: Path = DATA_DIRECTORY / "models"  # downloaded model files (later phase)

# --------------------------------------------------------------------------
# Application
# --------------------------------------------------------------------------
APP_TITLE: str = "Multimodal Attendance & Engagement Agent"
APP_ICON: str = "🎓"
RECENT_SESSIONS_LIMIT: int = 10

# --------------------------------------------------------------------------
# Attendance
# --------------------------------------------------------------------------
# A student qualifies as "present" only after this much sustained presence.
# For quick demonstrations set this to 5.
ATTENDANCE_MIN_SECONDS: int = 30
# If a student is not seen for this long, their continuous presence streak
# resets (later phase).
PRESENCE_GAP_TOLERANCE_SECONDS: float = 3.0

# --------------------------------------------------------------------------
# Video processing (later phase)
# --------------------------------------------------------------------------
FRAME_SKIP: int = 5  # analyse every Nth frame
FACE_MATCH_THRESHOLD: float = 0.60  # calibrated for the chosen recognizer in Phase 2
MAX_REFERENCE_IMAGES: int = 10
MIN_REFERENCE_IMAGES: int = 3

# --------------------------------------------------------------------------
# Engagement (later phases)
# --------------------------------------------------------------------------
ENGAGEMENT_WINDOW_SECONDS: int = 30

# Head pose angles (degrees). A face is "looking forward" when the absolute
# yaw and pitch are inside these limits. These are rough estimates.
HEAD_POSE_THRESHOLDS: dict[str, float] = {
    "yaw_degrees": 20.0,       # beyond this -> left / right
    "pitch_up_degrees": 15.0,  # beyond this -> up
    "pitch_down_degrees": 15.0,  # beyond this -> down
}

# Weights must sum to 1.0. The score is a transparent heuristic, not a
# trained model.
ENGAGEMENT_WEIGHTS: dict[str, float] = {
    "looking_forward": 0.40,
    "movement": 0.20,
    "presence": 0.25,
    "face_visibility": 0.15,
}

# Inactivity: movement below this normalised level counts as "still".
INACTIVITY_MOVEMENT_THRESHOLD: float = 0.02
INACTIVITY_ALERT_SECONDS: float = 120.0

# --------------------------------------------------------------------------
# Audio (later phase)
# --------------------------------------------------------------------------
AUDIO_SAMPLE_RATE: int = 16000
AUDIO_FRAME_SECONDS: float = 0.5
AUDIO_SILENCE_RMS: float = 0.01       # below -> silence
AUDIO_HIGH_ACTIVITY_RMS: float = 0.08  # above -> high activity

# --------------------------------------------------------------------------
# Recommendation rules (later phase)
# --------------------------------------------------------------------------
ENGAGEMENT_DECLINE_POINTS: float = 10.0
LONG_INSTRUCTION_SECONDS: int = 600
LOW_AUDIO_ACTIVE_PERCENT: float = 10.0
HIGH_ENGAGEMENT_SCORE: float = 75.0

# --------------------------------------------------------------------------
# User-facing notices (shown in the UI and README)
# --------------------------------------------------------------------------
PRIVACY_NOTE: str = (
    "All data is stored locally on this computer. No images, audio or "
    "analytics are sent to any cloud service."
)
ENGAGEMENT_DISCLAIMER: str = (
    "The engagement score is a heuristic built only from observable session "
    "signals (head orientation, face visibility, presence and movement). It "
    "does NOT measure emotion, intelligence, learning ability or any "
    "psychological state, and head-pose estimates are approximate. It should "
    "support, never replace, the instructor's own judgement."
)


def ensure_directories() -> None:
    """Create all required data directories if they do not exist."""
    for directory in (
        DATA_DIRECTORY,
        STUDENTS_DIRECTORY,
        SESSIONS_DIRECTORY,
        DATABASE_DIRECTORY,
        MODELS_DIRECTORY,
    ):
        directory.mkdir(parents=True, exist_ok=True)
