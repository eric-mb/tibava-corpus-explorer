"""Streamlit caching helpers shared by all views."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from explorer.data import Video, list_exports, load_video


@st.cache_resource(show_spinner="Loading video export …")
def _load(path: str, mtime: float) -> Video:
    return load_video(path)


def get_video(path: Path) -> Video:
    return _load(str(path), path.stat().st_mtime)


def get_corpus() -> list[Video]:
    paths = list_exports()
    bar = st.progress(0.0, text="Loading corpus …")
    videos = []
    for k, p in enumerate(paths):
        videos.append(get_video(p))
        bar.progress((k + 1) / len(paths), text=f"Loading corpus … {p.stem}")
    bar.empty()
    return videos


def theme() -> str:
    try:
        return st.context.theme.type or "light"
    except Exception:  # noqa: BLE001
        return "light"
