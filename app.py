import streamlit as st

st.set_page_config(page_title="TIB-AV-A Corpus Explorer", page_icon="🎬", layout="wide")

pages = st.navigation(
    [
        st.Page("views/pattern_search.py", title="Pattern Search", icon="🔎", default=True),
        st.Page("views/statistics.py", title="Corpus Statistics", icon="📊"),
        st.Page("views/faces.py", title="Faces on Screen", icon="👥"),
    ]
)
pages.run()
