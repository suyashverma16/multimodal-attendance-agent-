"""Tests for database initialisation and basic persistence behaviour."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.database import db

EXPECTED_TABLES = {
    "students",
    "face_embeddings",
    "sessions",
    "attendance",
    "engagement_records",
    "audio_records",
    "fusion_records",
    "recommendations",
}


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "nested" / "test.db"  # nested dir proves auto-creation
    db.initialize_database(path)
    return path


def test_initialize_creates_all_tables(db_path: Path) -> None:
    assert db_path.exists()
    assert EXPECTED_TABLES.issubset(set(db.list_tables(db_path)))


def test_initialize_is_idempotent(db_path: Path) -> None:
    db.add_student("S1", "Asha", "CSE-A", db_path=db_path)
    db.initialize_database(db_path)  # second call must not wipe data
    assert db.count_students(db_path) == 1


def test_foreign_keys_enabled(db_path: Path) -> None:
    with db.get_connection(db_path) as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_duplicate_student_rejected_case_insensitive(db_path: Path) -> None:
    db.add_student("S1", "Asha", "CSE-A", db_path=db_path)
    with pytest.raises(db.DuplicateStudentError):
        db.add_student("s1", "Someone Else", "CSE-B", db_path=db_path)
    assert db.count_students(db_path) == 1


def test_delete_student_cascades(db_path: Path) -> None:
    db.add_student("S1", "Asha", "CSE-A", db_path=db_path)
    session_id = db.create_session("Maths", "live", db_path=db_path)
    with db.get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO attendance (session_id, student_id, total_presence_seconds, status) "
            "VALUES (?, ?, ?, ?)",
            (session_id, "S1", 42.0, "present"),
        )
    assert db.delete_student("S1", db_path=db_path) is True
    with db.get_connection(db_path) as conn:
        remaining = conn.execute("SELECT COUNT(*) FROM attendance").fetchone()[0]
    assert remaining == 0
    assert db.delete_student("S1", db_path=db_path) is False


def test_session_lifecycle(db_path: Path) -> None:
    session_id = db.create_session(
        "Physics", "video", attendance_threshold_seconds=5,
        started_at="2026-10-24T10:00:00", db_path=db_path,
    )
    finished = db.end_session(session_id, ended_at="2026-10-24T10:01:30", db_path=db_path)
    assert finished.duration_seconds == 90.0
    assert finished.attendance_threshold_seconds == 5.0
    assert db.get_latest_session(db_path=db_path).id == session_id
    with pytest.raises(db.SessionNotFoundError):
        db.end_session(9999, db_path=db_path)
    with pytest.raises(ValueError):
        db.create_session("Bad", "satellite", db_path=db_path)


def test_empty_dashboard_summary(db_path: Path) -> None:
    summary = db.get_dashboard_summary(db_path=db_path)
    assert summary["registered_students"] == 0
    assert summary["total_sessions"] == 0
    assert summary["latest_session"] is None
    assert summary["average_attendance_pct"] is None
    assert summary["average_engagement"] is None
    assert db.get_recent_session_summaries(db_path=db_path) == []
