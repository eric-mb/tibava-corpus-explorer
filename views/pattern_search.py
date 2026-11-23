"""View 1: define a pattern as Python code and inspect its hits on a shot timeline."""

import pandas as pd
import streamlit as st

from explorer.cache import get_video, theme
from explorer.data import list_exports
from explorer.patterns import PatternError, load_patterns, run_pattern, save_pattern, slugify
from explorer.timeline import render_timeline

NEW_TEMPLATE = '''NAME = "My pattern"

# Return a list of Hit(shots=[shot indices], persons=[person ids]).
# Useful attributes: video.shots, shot.main_person, shot.persons, shot.scale,
# shot.start, shot.end, video.label(person) -> "A", "B", ...


def find(video):
    hits = []
    return hits
'''

st.title("Pattern Search")

st.markdown(
    """
    <style>
      .stTextArea textarea { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
                             font-size: 13px; }
    </style>
    """,
    unsafe_allow_html=True,
)

exports = list_exports()
if not exports:
    st.error("No exports found in `exports/`.")
    st.stop()

patterns = {p.slug: p for p in load_patterns()}

with st.sidebar:
    path = st.selectbox("Video", exports, format_func=lambda p: p.stem)
    choice = st.selectbox(
        "Pattern",
        [*patterns, "__new__"],
        format_func=lambda s: "➕ New pattern" if s == "__new__" else patterns[s].name,
    )

video = get_video(path)

# keep edited (unsaved) code per pattern in the session
code_key = f"code::{choice}"
if code_key not in st.session_state:
    st.session_state[code_key] = patterns[choice].code if choice in patterns else NEW_TEMPLATE

with st.expander("Pattern code", expanded=True):
    code = st.text_area("Python", key=code_key, height=380, label_visibility="collapsed")
    c1, c2, c3, _ = st.columns([1, 2, 1, 4])
    c1.button("▶ Run", type="primary", width="stretch")
    default_slug = choice if choice in patterns else slugify(
        next((l.split("=", 1)[1].strip(" \"'") for l in code.splitlines() if l.startswith("NAME")), "pattern")
    )
    slug = c2.text_input("File name", value=default_slug, label_visibility="collapsed",
                         help="Saved as patterns/<name>.py and used by the statistics view")
    if c3.button("💾 Save", width="stretch"):
        saved = save_pattern(slug, code)
        st.toast(f"Saved {saved.relative_to(saved.parent.parent)}")
        if choice == "__new__":
            del st.session_state[code_key]
        st.rerun()
    if choice in patterns and code != patterns[choice].code:
        st.caption("Unsaved changes – the statistics view uses the saved version.")

st.subheader(video.name)
m1, m2, m3, m4 = st.columns(4)
m1.metric("Duration", f"{video.duration / 60:.1f} min")
m2.metric("Shots", len(video.shots))
m3.metric("Persons (face clusters)", len(video.person_labels))

if not video.has_faces:
    st.warning("This export contains no face clustering results, so person-based patterns cannot match.")

try:
    hits = run_pattern(code, video)
except PatternError as e:
    m4.metric("Hits", "–")
    st.error(f"Pattern failed:\n\n```\n{e}\n```")
    hits = None

if hits is not None:
    m4.metric("Hits", len(hits))
    page, height = render_timeline(video, hits, theme())
    st.iframe(page, height=height)

    if hits:
        rows = []
        for k, h in enumerate(sorted(hits, key=lambda h: min(h.shots))):
            a, b = video.shots[min(h.shots)], video.shots[max(h.shots)]
            rows.append({
                "#": k + 1, "Pattern": h.label, "Group": h.group, "Shots": len(h.shots),
                "Start": round(a.start, 2), "End": round(b.end, 2),
                "Duration (s)": round(b.end - a.start, 2),
                "Scales": ", ".join(sorted({video.shots[i].scale or "?" for i in h.shots})),
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

        persons = []
        for h in hits:
            persons += [p for p in h.persons if p not in persons]
        st.markdown("**Persons in hits**")
        faces = video.images([video.person_face(p) for p in persons])
        cols = st.columns(min(len(persons), 10) or 1)
        for k, p in enumerate(persons):
            img = faces.get(video.person_face(p))
            with cols[k % len(cols)]:
                if img:
                    st.image(img, width=80)
                st.caption(f"**{video.label(p)}** · {sum(video.shots[i].persons[p] > 0 for i in range(len(video.shots)))} shots")
