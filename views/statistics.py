"""View 2: corpus-wide statistics for shot scales and the saved patterns."""

import altair as alt
import pandas as pd
import streamlit as st

from explorer.cache import get_corpus
from explorer.data import SHOT_SCALES
from explorer.patterns import PatternError, load_patterns, run_pattern
from explorer.timeline import SCALE_COLORS

st.title("Corpus Statistics")

videos = get_corpus()
scale_range = [SCALE_COLORS[s][0] for s in SHOT_SCALES]
scale_enc = alt.Color("Scale:N", sort=SHOT_SCALES,
                      scale=alt.Scale(domain=SHOT_SCALES, range=scale_range),
                      legend=alt.Legend(orient="top", title=None))

# --- shot scales ---------------------------------------------------------------
shot_rows = [
    {"Video": v.name, "Shot": s.index, "Scale": s.scale, "Duration": s.duration}
    for v in videos for s in v.shots
]
shots = pd.DataFrame(shot_rows)

c1, c2, c3 = st.columns(3)
c1.metric("Videos", len(videos))
c2.metric("Shots", len(shots))
c3.metric("Total duration", f"{sum(v.duration for v in videos) / 60:.1f} min")

st.header("Camera sizes")
measure = st.segmented_control("Measure", ["Shot count", "Screen time"], default="Shot count",
                               label_visibility="collapsed") or "Shot count"
value = "Shots" if measure == "Shot count" else "Seconds"

scaled = shots.dropna(subset=["Scale"])
agg = (scaled.groupby(["Video", "Scale"])
       .agg(Shots=("Shot", "count"), Seconds=("Duration", "sum")).reset_index())
agg["Share"] = agg[value] / agg.groupby("Video")[value].transform("sum")
order = sorted(agg["Video"].unique(), key=str.lower)

corpus = (scaled.groupby("Scale").agg(Shots=("Shot", "count"), Seconds=("Duration", "sum"))
          .reindex(SHOT_SCALES).fillna(0).reset_index())
corpus["Share"] = corpus[value] / corpus[value].sum()
corpus["Video"] = "Whole corpus"

both = pd.concat([corpus, agg], ignore_index=True)
st.altair_chart(
    alt.Chart(both)
    .mark_bar()
    .encode(
        y=alt.Y("Video:N", sort=["Whole corpus", *order], title=None,
                axis=alt.Axis(labelOverlap=False, labelLimit=220)),
        x=alt.X("Share:Q", stack="normalize", axis=alt.Axis(format="%", title=None, grid=False)),
        color=scale_enc,
        order=alt.Order("order:Q"),
        tooltip=["Video", "Scale", alt.Tooltip("Share:Q", format=".1%"), "Shots",
                 alt.Tooltip("Seconds:Q", format=".1f")],
    )
    .transform_calculate(order=f"indexof({SHOT_SCALES!r}, datum.Scale)")
    .properties(height=24 * (len(order) + 1)),
    width="stretch",
)

with st.expander("Table"):
    table = agg.pivot(index="Video", columns="Scale", values=value).reindex(columns=SHOT_SCALES).fillna(0)
    st.dataframe(table.round(1), width="stretch")

# --- patterns ------------------------------------------------------------------
st.header("Patterns")
patterns = load_patterns()
if not patterns:
    st.info("No saved patterns yet – define one in the Pattern Search view.")
    st.stop()

pattern = st.selectbox("Pattern", patterns, format_func=lambda p: p.name)

hit_rows, per_video, errors = [], [], []
for v in videos:
    try:
        hits = run_pattern(pattern.code, v)
    except PatternError as e:
        errors.append(f"{v.name}: {e}")
        continue
    covered = {i for h in hits for i in h.shots}
    per_video.append({
        "Video": v.name, "Hits": len(hits), "Shots": len(v.shots),
        "Shots in hits": len(covered),
        "Share of shots": len(covered) / len(v.shots) if v.shots else 0,
        "Seconds in hits": sum(v.shots[i].duration for i in covered),
        "Has faces": v.has_faces,
    })
    for h in hits:
        hit_rows.append({
            "Video": v.name, "Length": len(h.shots), "Label": h.label,
            "Duration": v.shots[max(h.shots)].end - v.shots[min(h.shots)].start,
        })
        for i in h.shots:
            shot_rows.append({"Video": v.name, "Shot": i, "Scale": v.shots[i].scale,
                              "Duration": v.shots[i].duration, "in_hit": True})

for e in errors:
    st.error(e)

pv = pd.DataFrame(per_video)
hits_df = pd.DataFrame(hit_rows)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Hits", int(pv["Hits"].sum()) if len(pv) else 0)
m2.metric("Videos with hits", f"{int((pv['Hits'] > 0).sum())} / {len(pv)}" if len(pv) else "0")
m3.metric("Shots in hits", f"{pv['Shots in hits'].sum() / max(pv['Shots'].sum(), 1):.0%}" if len(pv) else "–")
m4.metric("Median length", f"{hits_df['Length'].median():.0f} shots" if len(hits_df) else "–")

left, right = st.columns(2)
with left:
    st.subheader("Hits per video")
    base = alt.Chart(pv).encode(y=alt.Y("Video:N", sort=order, title=None, axis=alt.Axis(labelOverlap=False, labelLimit=220)))
    st.altair_chart(
        base.mark_bar(color=SCALE_COLORS["Medium"][0], cornerRadiusEnd=4, height=14).encode(
            x=alt.X("Hits:Q", title="Hits", axis=alt.Axis(tickMinStep=1)),
            tooltip=["Video", "Hits", "Shots in hits", alt.Tooltip("Share of shots:Q", format=".0%")],
        ).properties(height=26 * len(pv)),
        width="stretch",
    )
    no_faces = pv.loc[~pv["Has faces"], "Video"].tolist()
    if no_faces:
        st.caption("No face data (cannot match person patterns): " + ", ".join(no_faces))
with right:
    st.subheader("Share of shots inside hits")
    st.altair_chart(
        alt.Chart(pv).mark_bar(color=SCALE_COLORS["Medium"][0], cornerRadiusEnd=4, height=14).encode(
            y=alt.Y("Video:N", sort=order, title=None, axis=alt.Axis(labelOverlap=False, labelLimit=220)),
            x=alt.X("Share of shots:Q", axis=alt.Axis(format="%"), title="Shots in hits",
                    scale=alt.Scale(domain=[0, 1])),
            tooltip=["Video", "Shots in hits", "Shots", alt.Tooltip("Share of shots:Q", format=".0%")],
        ).properties(height=26 * len(pv)),
        width="stretch",
    )

if len(hits_df):
    left, right = st.columns(2)
    with left:
        st.subheader("Hit length")
        st.altair_chart(
            alt.Chart(hits_df).mark_bar(color=SCALE_COLORS["Medium"][0], cornerRadiusEnd=4).encode(
                x=alt.X("Length:O", title="Shots per hit", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("count():Q", title="Hits", axis=alt.Axis(tickMinStep=1)),
                tooltip=[alt.Tooltip("Length:O", title="Shots per hit"), alt.Tooltip("count():Q", title="Hits")],
            ).properties(height=260),
            width="stretch",
        )
    with right:
        st.subheader("Camera sizes: in hits vs. all shots")
        all_rows = pd.DataFrame(shot_rows)
        all_rows["Set"] = all_rows["in_hit"].fillna(False).map({True: "In hits", False: "All shots"})
        cmp = (all_rows.dropna(subset=["Scale"]).groupby(["Set", "Scale"]).size()
               .rename("Shots").reset_index())
        cmp["Share"] = cmp["Shots"] / cmp.groupby("Set")["Shots"].transform("sum")
        st.altair_chart(
            alt.Chart(cmp).mark_bar().encode(
                y=alt.Y("Set:N", title=None, sort=["All shots", "In hits"]),
                x=alt.X("Share:Q", stack="normalize", axis=alt.Axis(format="%", title=None)),
                color=scale_enc,
                order=alt.Order("order:Q"),
                tooltip=["Set", "Scale", "Shots", alt.Tooltip("Share:Q", format=".1%")],
            ).transform_calculate(order=f"indexof({SHOT_SCALES!r}, datum.Scale)")
            .properties(height=alt.Step(40)),
            width="stretch",
        )

with st.expander("Table"):
    st.dataframe(pv.drop(columns=["Has faces"]), hide_index=True, width="stretch",
                 column_config={"Share of shots": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
                                "Seconds in hits": st.column_config.NumberColumn(format="%.1f")})
