"""View 3: number of faces visible on screen over time, one timeline per video."""

from collections import Counter

import streamlit as st

from explorer.cache import get_corpus, theme
from explorer.timeline import render_timeline

STEP = 0.5  # face detection sampling interval in TIB-AV-A exports (seconds)

st.title("Faces on Screen")
st.caption(
    "Number of detected faces per sample (every 0.5 s), from TIB-AV-A face detection, "
    "aligned with the shot thumbnails. Hover over the chart for exact values."
)

videos = get_corpus()


def face_counts(video) -> list[int]:
    per_sample = Counter(round(f.time / STEP) for f in video.faces)
    n = int(video.duration / STEP) + 1
    return [per_sample.get(k, 0) for k in range(n)]


dark = theme()
for video in videos:
    st.subheader(video.name)
    if not video.has_faces:
        st.caption("No face detection results in this export.")
        continue
    counts = face_counts(video)
    visible = sum(c > 0 for c in counts) / len(counts)
    st.caption(
        f"{video.duration / 60:.1f} min · faces visible {visible:.0%} of the time · "
        f"mean {sum(counts) / len(counts):.2f} · max {max(counts)} faces"
    )
    page, height = render_timeline(
        video, [], dark, series={"label": "Faces", "step": STEP, "values": counts}
    )
    st.iframe(page, height=height)
