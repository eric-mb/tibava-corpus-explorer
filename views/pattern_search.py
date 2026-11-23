"""View 1: define a pattern as Python code and inspect its hits on a shot timeline."""

import streamlit as st

from explorer.cache import get_video, theme
from explorer.data import list_exports
from explorer.patterns import (PatternError, compile_pattern, load_patterns, run_pattern,
                               save_pattern, slugify)
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
    choice = st.selectbox(
        "Pattern",
        [*patterns, "__new__"],
        format_func=lambda s: "➕ New pattern" if s == "__new__" else patterns[s].name,
    )

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

try:
    compile_pattern(code)
except PatternError as e:
    st.error(f"Pattern failed:\n\n```\n{e}\n```")
    st.stop()

dark = theme()
for path in exports:
    video = get_video(path)
    try:
        hits = run_pattern(code, video)
    except PatternError as e:
        st.subheader(video.name)
        st.error(f"Pattern failed:\n\n```\n{e}\n```")
        continue
    st.subheader(video.name)
    st.caption(
        f"{video.duration / 60:.1f} min · {len(video.shots)} shots · "
        f"{len(video.person_labels)} persons · **{len(hits)} hits**"
        + ("" if video.has_faces else " · no face clustering in this export")
    )
    page, height = render_timeline(video, hits, dark)
    st.iframe(page, height=height)
