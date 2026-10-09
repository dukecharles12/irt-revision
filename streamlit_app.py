from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="IRT Revision Desk", page_icon="📘", layout="wide")

# Let the revision page fill the whole window.
st.markdown(
    """
    <style>
      header, footer, #MainMenu {visibility: hidden; height: 0;}
      .block-container {padding: 0 !important; max-width: 100% !important;}
      iframe {height: 100vh !important; width: 100%; border: 0;}
    </style>
    """,
    unsafe_allow_html=True,
)

html = (Path(__file__).parent / "irt-revision.html").read_text(encoding="utf-8")

# Streamlit shows the page in an iframe whose links would otherwise resolve
# against the Streamlit URL, so handle the page's "#section" links here.
HASH_LINKS = """<script>
document.addEventListener("click", e => {
  const a = e.target.closest('a[href^="#"]');
  if (a) { e.preventDefault(); location.hash = a.getAttribute("href"); }
}, true);
</script>"""
html = html.replace("</body>", HASH_LINKS + "</body>")
components.html(html, height=900, scrolling=True)
