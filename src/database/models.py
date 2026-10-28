"""Database schema and lightweight record types."""

from __future__ import annotations

from dataclasses import dataclass

SESSION_SOURCES: tuple[str, ...] = ("live", "video", "demo")
ATTENDANCE_STATUSES: tuple[str, ...] = ("present", "absent")

SOURCE_LABELS: dict[str, str] = {
    "live": "Live webcam",
    "video": "Recorded video",
    "demo": "DEMO (synthetic data)",
}

SCHEMA_SQL: str = """
CREATE TABLE IF NOT EXISTS students (
    student_id  TEXT PRIMARY KEY COLLATE NOCASE,
    name        TEXT NOT NULL,
    department  TEXT NOT NULL,
    email       TEXT,
    created_at  TEXT NOT NULL
);

-- Local face features (one row per reference image). Deleting a student
-- removes their embeddings automatically.
CREATE TABLE IF NOT EXISTS face_embeddings (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id     TEXT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    embedding      BLOB NOT NULL,
    embedding_dim  INTEGER NOT NULL,
    image_path     TEXT,
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id                           INTEGER PRIMARY KEY AUTOINCREMENT,
    name                         TEXT NOT NULL,
    source_type                  TEXT NOT NULL
                                 CHECK (source_type IN ('live', 'video', 'demo')),
    started_at                   TEXT NOT NULL,
    ended_at                     TEXT,
    duration_seconds             REAL,
    attendance_threshold_seconds REAL NOT NULL,
    notes                        TEXT
);

CREATE TABLE IF NOT EXISTS attendance (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id             INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    student_id             TEXT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    first_seen             TEXT,
    last_seen              TEXT,
    total_presence_seconds REAL NOT NULL DEFAULT 0,
    status                 TEXT NOT NULL CHECK (status IN ('present', 'absent')),
    UNIQUE (session_id, student_id)
);

-- One row per student per time window; component scores are stored so the
-- engagement indicator stays explainable.
CREATE TABLE IF NOT EXISTS engagement_records (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id            INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    student_id            TEXT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    window_start_sec      REAL NOT NULL,
    window_end_sec        REAL NOT NULL,
    looking_forward_score REAL NOT NULL,
    movement_score        REAL NOT NULL,
    presence_score        REAL NOT NULL,
    face_visibility_score REAL NOT NULL,
    engagement_score      REAL NOT NULL,
    dominant_head_pose    TEXT,
    UNIQUE (session_id, student_id, window_start_sec)
);

CREATE TABLE IF NOT EXISTS audio_records (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id       INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    window_start_sec REAL NOT NULL,
    window_end_sec   REAL NOT NULL,
    rms_energy       REAL NOT NULL,
    active_percent   REAL NOT NULL,
    activity_level   TEXT NOT NULL,
    UNIQUE (session_id, window_start_sec)
);

-- Class-level fused (video + audio) values per time window.
CREATE TABLE IF NOT EXISTS fusion_records (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id          INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    window_start_sec    REAL NOT NULL,
    window_end_sec      REAL NOT NULL,
    avg_engagement      REAL,
    audio_activity_level TEXT,
    audio_rms           REAL,
    students_visible    INTEGER NOT NULL DEFAULT 0,
    fused_score         REAL,
    UNIQUE (session_id, window_start_sec)
);

CREATE TABLE IF NOT EXISTS recommendations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    category      TEXT NOT NULL,
    severity      TEXT NOT NULL,
    message       TEXT NOT NULL,
    evidence_json TEXT,
    source        TEXT NOT NULL DEFAULT 'rule_based',
    created_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_embeddings_student ON face_embeddings(student_id);
CREATE INDEX IF NOT EXISTS idx_attendance_session ON attendance(session_id);
CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id);
CREATE INDEX IF NOT EXISTS idx_engagement_session ON engagement_records(session_id);
CREATE INDEX IF NOT EXISTS idx_audio_session ON audio_records(session_id);
CREATE INDEX IF NOT EXISTS idx_fusion_session ON fusion_records(session_id);
CREATE INDEX IF NOT EXISTS idx_reco_session ON recommendations(session_id);
"""


@dataclass(frozen=True)
class Student:
    """A registered student."""

    student_id: str
    name: str
    department: str
    email: str | None
    created_at: str


@dataclass(frozen=True)
class SessionRecord:
    """A classroom session (live, recorded video, or synthetic demo)."""

    id: int
    name: str
    source_type: str
    started_at: str
    ended_at: str | None
    duration_seconds: float | None
    attendance_threshold_seconds: float
    notes: str | None

    @property
    def is_demo(self) -> bool:
        """True when this session contains synthetic demo data."""
        return self.source_type == "demo"

    @property
    def source_label(self) -> str:
        """Human-readable label for the data source."""
        return SOURCE_LABELS.get(self.source_type, self.source_type)
