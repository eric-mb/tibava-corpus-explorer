"""View 3: number of faces visible on screen over time, one chart per video."""

from collections import Counter

import altair as alt
import pandas as pd
import streamlit as st

from explorer.cache import get_corpus

SERIES = "#2a78d6"  # categorical slot 1 (single series)
STEP = 0.5  # face detection sampling interval in TIB-AV-A exports (seconds)

st.title("Faces on Screen")
st.caption(
    "Number of detected faces per sample (every 0.5 s), from TIB-AV-A face detection. "
    "Faint vertical lines mark shot boundaries."
)

videos = get_corpus()


def face_counts(video) -> pd.DataFrame:
    per_sample = Counter(round(f.time / STEP) for f in video.faces)
    n = int(video.duration / STEP) + 1
    return pd.DataFrame({
        "Time": [k * STEP for k in range(n)],
        "Faces": [per_sample.get(k, 0) for k in range(n)],
    })


data = {v.name: face_counts(v) for v in videos if v.has_faces}


def fmt_time(seconds: float) -> str:
    return f"{int(seconds // 60)}:{seconds % 60:04.1f}"


def chart(video, df: pd.DataFrame) -> alt.LayerChart:
    df = df.assign(Clock=df["Time"].map(fmt_time))
    x = alt.X("Time:Q", title="Time (s)", scale=alt.Scale(domain=[0, video.duration], nice=False))
    y_max = max(int(df["Faces"].max()), 3)
    y = alt.Y("Faces:Q", title="Faces", scale=alt.Scale(domain=[0, y_max]),
              axis=alt.Axis(values=list(range(y_max + 1)), format="d"))

    cuts = pd.DataFrame({"Time": [s.start for s in video.shots[1:]]})
    boundaries = alt.Chart(cuts).mark_rule(color="#898781", opacity=0.25, strokeWidth=1).encode(x="Time:Q")

    area = alt.Chart(df).mark_area(interpolate="step-after", color=SERIES, opacity=0.18).encode(x=x, y=y)
    line = alt.Chart(df).mark_line(interpolate="step-after", color=SERIES, strokeWidth=2).encode(x=x, y=y)

    hover = alt.selection_point(fields=["Time"], nearest=True, on="pointerover", empty=False)
    points = alt.Chart(df).mark_point(opacity=0, size=200).encode(
        x=x, y=y, tooltip=[alt.Tooltip("Clock:N", title="Time"), "Faces:Q"]
    ).add_params(hover)
    rule = alt.Chart(df).mark_rule(color="#52514e", strokeWidth=1).encode(x=x).transform_filter(hover)
    dot = alt.Chart(df).mark_point(filled=True, color=SERIES, size=70).encode(x=x, y=y).transform_filter(hover)

    return alt.layer(boundaries, area, line, points, rule, dot).properties(height=170)


for video in videos:
    st.subheader(video.name)
    if not video.has_faces:
        st.caption("No face detection results in this export.")
        continue
    df = data[video.name]
    on_screen = df["Faces"] > 0
    st.caption(
        f"{video.duration / 60:.1f} min · faces visible {on_screen.mean():.0%} of the time · "
        f"mean {df['Faces'].mean():.2f} · max {int(df['Faces'].max())} faces"
    )
    st.altair_chart(chart(video, df), width="stretch")
