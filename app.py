"""Home Dashboard (entry point): streamlit run app.py"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

import config
from src.database import db
from src.database.models import SOURCE_LABELS
from src.utils.helpers import format_duration, format_timestamp
from src.utils.ui import render_limitations, setup_page


def _fmt_pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.0f}%"


def _fmt_score(value: float | None) -> str:
    return "—" if value is None else f"{value:.1f} / 100"


def main() -> None:
    setup_page("Home")
    include_demo = st.sidebar.checkbox(
        "Include DEMO (synthetic) sessions",
        value=True,
        help="Demo sessions contain synthetic data, not AI detections.",
    )

    st.title(f"{config.APP_ICON} {config.APP_TITLE}")
    st.caption(
        "Offline classroom attendance and observable-engagement analytics. "
        "Engagement indicators are heuristics, not measures of emotion or learning."
    )

    try:
        summary = db.get_dashboard_summary(include_demo=include_demo)
        recent = db.get_recent_session_summaries(
            limit=config.RECENT_SESSIONS_LIMIT, include_demo=include_demo
        )
        students = db.list_students()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not read the local database: {exc}")
        st.stop()

    latest = summary["latest_session"]
    cols = st.columns(5)
    cols[0].metric("Registered students", summary["registered_students"])
    cols[1].metric("Total sessions", summary["total_sessions"])
    cols[2].metric("Latest session", latest.name if latest else "—")
    if latest:
        cols[2].caption(f"{format_timestamp(latest.started_at)} · {latest.source_label}")
    cols[3].metric("Avg attendance", _fmt_pct(summary["average_attendance_pct"]))
    cols[4].metric("Avg engagement indicator", _fmt_score(summary["average_engagement"]))

    st.divider()
    st.subheader("Recent sessions")

    if not recent:
        st.info(
            "No sessions recorded yet. Register students, then run a live session or "
            "analyse a recorded video. (Demo mode arrives in a later phase.)"
        )
    else:
        df = pd.DataFrame(recent)
        df["attendance_pct"] = pd.to_numeric(df["attendance_pct"], errors="coerce")
        df["avg_engagement"] = pd.to_numeric(df["avg_engagement"], errors="coerce")
        df["source"] = df["source_type"].map(SOURCE_LABELS).fillna(df["source_type"])
        df["label"] = "#" + df["id"].astype(str) + " " + df["name"]

        table = pd.DataFrame(
            {
                "Session": df["label"],
                "Source": df["source"],
                "Started": df["started_at"].map(format_timestamp),
                "Duration": df["duration_seconds"].map(format_duration),
                "Present / tracked": df["present_students"].astype(str)
                + " / "
                + df["tracked_students"].astype(str),
                "Attendance %": df["attendance_pct"].round(0),
                "Avg engagement": df["avg_engagement"].round(1),
            }
        )
        st.dataframe(table, use_container_width=True, hide_index=True)

        chart_df = df.sort_values("started_at")  # chronological for trend charts
        left, right = st.columns(2)
        with left:
            fig = px.bar(
                chart_df,
                x="label",
                y="attendance_pct",
                color="source",
                title="Attendance per session (%)",
                labels={"label": "Session", "attendance_pct": "Attendance %", "source": "Source"},
            )
            fig.update_yaxes(range=[0, 100])
            st.plotly_chart(fig, use_container_width=True)
        with right:
            eng_df = chart_df.dropna(subset=["avg_engagement"])
            if eng_df.empty:
                st.info("No engagement data stored yet.")
            else:
                fig = px.line(
                    eng_df,
                    x="label",
                    y="avg_engagement",
                    markers=True,
                    title="Average observable engagement indicator",
                    labels={"label": "Session", "avg_engagement": "Score (0-100)"},
                )
                fig.update_yaxes(range=[0, 100])
                st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Registered students")
    if not students:
        st.info("No students registered yet. Registration is built in Phase 2.")
    else:
        st.dataframe(
            pd.DataFrame(
                [
                    {"Student ID": s.student_id, "Name": s.name, "Department / class": s.department}
                    for s in students
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

    render_limitations()


main()
