"""SQLite access layer.

All SQL is parameterised. Every public function accepts an optional
``db_path`` so tests can use a temporary database.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import config
from src.database.models import (
    SCHEMA_SQL,
    SESSION_SOURCES,
    SessionRecord,
    Student,
)
from src.utils.helpers import now_iso, parse_iso


class DatabaseError(Exception):
    """Base class for database-related errors."""


class DuplicateStudentError(DatabaseError):
    """Raised when a Student ID already exists."""


class StudentNotFoundError(DatabaseError):
    """Raised when a student does not exist."""


class SessionNotFoundError(DatabaseError):
    """Raised when a session does not exist."""


# --------------------------------------------------------------------------
# Connection / initialisation
# --------------------------------------------------------------------------
@contextmanager
def get_connection(db_path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    """Open a connection with foreign keys enabled; commit/rollback/close automatically."""
    path = Path(db_path) if db_path is not None else config.DATABASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_database(db_path: Path | str | None = None) -> Path:
    """Create the database file and all tables if missing. Safe to call repeatedly."""
    path = Path(db_path) if db_path is not None else config.DATABASE_PATH
    with get_connection(path) as conn:
        conn.executescript(SCHEMA_SQL)
    return path


def list_tables(db_path: Path | str | None = None) -> list[str]:
    """Return the names of all user tables, sorted alphabetically."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    return [row["name"] for row in rows]


# --------------------------------------------------------------------------
# Row mapping
# --------------------------------------------------------------------------
def _row_to_student(row: sqlite3.Row) -> Student:
    return Student(
        student_id=row["student_id"],
        name=row["name"],
        department=row["department"],
        email=row["email"],
        created_at=row["created_at"],
    )


def _row_to_session(row: sqlite3.Row) -> SessionRecord:
    return SessionRecord(
        id=row["id"],
        name=row["name"],
        source_type=row["source_type"],
        started_at=row["started_at"],
        ended_at=row["ended_at"],
        duration_seconds=row["duration_seconds"],
        attendance_threshold_seconds=row["attendance_threshold_seconds"],
        notes=row["notes"],
    )


# --------------------------------------------------------------------------
# Students
# --------------------------------------------------------------------------
def add_student(
    student_id: str,
    name: str,
    department: str,
    email: str | None = None,
    db_path: Path | str | None = None,
) -> Student:
    """Register a student. Raises DuplicateStudentError if the ID exists (case-insensitive)."""
    student_id = (student_id or "").strip()
    name = (name or "").strip()
    department = (department or "").strip()
    email = (email or "").strip() or None
    if not student_id or not name or not department:
        raise ValueError("Student ID, name and department/class are required.")

    created_at = now_iso()
    try:
        with get_connection(db_path) as conn:
            conn.execute(
                "INSERT INTO students (student_id, name, department, email, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (student_id, name, department, email, created_at),
            )
    except sqlite3.IntegrityError as exc:
        raise DuplicateStudentError(
            f"A student with ID '{student_id}' is already registered."
        ) from exc
    return Student(student_id, name, department, email, created_at)


def get_student(student_id: str, db_path: Path | str | None = None) -> Student | None:
    """Return one student or None."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM students WHERE student_id = ?", (student_id.strip(),)
        ).fetchone()
    return _row_to_student(row) if row else None


def list_students(db_path: Path | str | None = None) -> list[Student]:
    """Return all students ordered by name."""
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM students ORDER BY name COLLATE NOCASE").fetchall()
    return [_row_to_student(row) for row in rows]


def count_students(db_path: Path | str | None = None) -> int:
    """Return the number of registered students."""
    with get_connection(db_path) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM students").fetchone()[0])


def delete_student(student_id: str, db_path: Path | str | None = None) -> bool:
    """Delete a student and (via cascade) their embeddings, attendance and engagement rows.

    Returns True if a student was deleted. Reference image files on disk are
    removed by the registration layer (Phase 2).
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM students WHERE student_id = ?", (student_id.strip(),)
        )
        return cursor.rowcount > 0


# --------------------------------------------------------------------------
# Sessions
# --------------------------------------------------------------------------
def create_session(
    name: str,
    source_type: str,
    attendance_threshold_seconds: float | None = None,
    started_at: str | None = None,
    notes: str | None = None,
    db_path: Path | str | None = None,
) -> int:
    """Create a session and return its integer ID."""
    name = (name or "").strip()
    if not name:
        raise ValueError("Session name is required.")
    if source_type not in SESSION_SOURCES:
        raise ValueError(f"source_type must be one of {SESSION_SOURCES}.")
    threshold = (
        config.ATTENDANCE_MIN_SECONDS
        if attendance_threshold_seconds is None
        else attendance_threshold_seconds
    )
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO sessions "
            "(name, source_type, started_at, attendance_threshold_seconds, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, source_type, started_at or now_iso(), float(threshold), notes),
        )
        return int(cursor.lastrowid)


def get_session(session_id: int, db_path: Path | str | None = None) -> SessionRecord | None:
    """Return one session or None."""
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    return _row_to_session(row) if row else None


def end_session(
    session_id: int,
    ended_at: str | None = None,
    duration_seconds: float | None = None,
    db_path: Path | str | None = None,
) -> SessionRecord:
    """Mark a session as finished. Duration defaults to ended_at - started_at."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT started_at FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row is None:
            raise SessionNotFoundError(f"Session {session_id} does not exist.")
        end_ts = ended_at or now_iso()
        if duration_seconds is None:
            elapsed = parse_iso(end_ts) - parse_iso(row["started_at"])
            duration_seconds = max(0.0, elapsed.total_seconds())
        conn.execute(
            "UPDATE sessions SET ended_at = ?, duration_seconds = ? WHERE id = ?",
            (end_ts, float(duration_seconds), session_id),
        )
    session = get_session(session_id, db_path)
    if session is None:  # pragma: no cover - defensive
        raise SessionNotFoundError(f"Session {session_id} does not exist.")
    return session


def list_sessions(
    limit: int | None = None,
    include_demo: bool = True,
    db_path: Path | str | None = None,
) -> list[SessionRecord]:
    """Return sessions, newest first."""
    where = "" if include_demo else "WHERE source_type != 'demo'"
    sql = f"SELECT * FROM sessions {where} ORDER BY started_at DESC, id DESC"
    params: tuple[Any, ...] = ()
    if limit is not None:
        sql += " LIMIT ?"
        params = (int(limit),)
    with get_connection(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_session(row) for row in rows]


def get_latest_session(
    include_demo: bool = True, db_path: Path | str | None = None
) -> SessionRecord | None:
    """Return the most recent session or None."""
    sessions = list_sessions(limit=1, include_demo=include_demo, db_path=db_path)
    return sessions[0] if sessions else None


# --------------------------------------------------------------------------
# Dashboard queries
# --------------------------------------------------------------------------
def get_dashboard_summary(
    include_demo: bool = True, db_path: Path | str | None = None
) -> dict[str, Any]:
    """Aggregate numbers for the Home Dashboard.

    ``average_attendance_pct`` is the share of attendance rows marked
    'present'. ``average_engagement`` is the mean stored engagement score.
    Either is None when no data exists yet.
    """
    # `where` is a fixed literal chosen by a boolean, never user input.
    where = "" if include_demo else "WHERE s.source_type != 'demo'"
    with get_connection(db_path) as conn:
        students = int(conn.execute("SELECT COUNT(*) FROM students").fetchone()[0])
        sessions = int(
            conn.execute(f"SELECT COUNT(*) FROM sessions s {where}").fetchone()[0]
        )
        att = conn.execute(
            "SELECT COUNT(*) AS total, "
            "COALESCE(SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END), 0) AS present "
            f"FROM attendance a JOIN sessions s ON s.id = a.session_id {where}"
        ).fetchone()
        eng = conn.execute(
            "SELECT AVG(e.engagement_score) "
            f"FROM engagement_records e JOIN sessions s ON s.id = e.session_id {where}"
        ).fetchone()[0]

    attendance_pct = (100.0 * att["present"] / att["total"]) if att["total"] else None
    return {
        "registered_students": students,
        "total_sessions": sessions,
        "latest_session": get_latest_session(include_demo, db_path),
        "average_attendance_pct": attendance_pct,
        "average_engagement": float(eng) if eng is not None else None,
    }


def get_recent_session_summaries(
    limit: int = 10,
    include_demo: bool = True,
    db_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Per-session attendance and engagement summary rows, newest first."""
    where = "" if include_demo else "WHERE s.source_type != 'demo'"
    sql = f"""
        SELECT s.id, s.name, s.source_type, s.started_at, s.duration_seconds,
            (SELECT COUNT(*) FROM attendance a
              WHERE a.session_id = s.id) AS tracked_students,
            (SELECT COUNT(*) FROM attendance a
              WHERE a.session_id = s.id AND a.status = 'present') AS present_students,
            (SELECT AVG(e.engagement_score) FROM engagement_records e
              WHERE e.session_id = s.id) AS avg_engagement
        FROM sessions s
        {where}
        ORDER BY s.started_at DESC, s.id DESC
        LIMIT ?
    """
    with get_connection(db_path) as conn:
        rows = conn.execute(sql, (int(limit),)).fetchall()

    summaries: list[dict[str, Any]] = []
    for row in rows:
        tracked = row["tracked_students"]
        summaries.append(
            {
                "id": row["id"],
                "name": row["name"],
                "source_type": row["source_type"],
                "started_at": row["started_at"],
                "duration_seconds": row["duration_seconds"],
                "tracked_students": tracked,
                "present_students": row["present_students"],
                "attendance_pct": (
                    100.0 * row["present_students"] / tracked if tracked else None
                ),
                "avg_engagement": row["avg_engagement"],
            }
        )
    return summaries
