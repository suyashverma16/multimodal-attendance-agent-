"""Shared Streamlit UI helpers used by every page."""

from __future__ import annotations

import streamlit as st

import config
from src.database import db


def setup_page(title: str, icon: str = config.APP_ICON) -> None:
    """Configure the page, ensure storage exists, and render the sidebar notice.

    Must be the first Streamlit call on every page. Stops the page with a
    readable error if local storage cannot be initialised.
    """
    st.set_page_config(page_title=f"{title} · {config.APP_TITLE}", page_icon=icon, layout="wide")
    try:
        config.ensure_directories()
        db.initialize_database()
    except Exception as exc:  # noqa: BLE001 - surface any storage problem to the user
        st.error(f"Could not initialise local storage: {exc}")
        st.stop()
    render_sidebar()


def render_sidebar() -> None:
    """Sidebar privacy notice shown on all pages."""
    with st.sidebar:
        st.caption("🔒 Offline · local storage only")
        st.info(config.PRIVACY_NOTE)


def render_limitations() -> None:
    """Collapsible explanation of what the engagement indicator is and is not."""
    with st.expander("ℹ️ What does the engagement indicator mean? (limitations)"):
        st.write(config.ENGAGEMENT_DISCLAIMER)
