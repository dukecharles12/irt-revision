import json
import os
import tempfile
import time
from pathlib import Path

import requests
import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).parent

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


@st.cache_resource
def build_page(stamp):
    """Serve the revision page as a component, with the sync bridge loaded first."""
    html = (ROOT / "irt-revision.html").read_text(encoding="utf-8")
    bridge = (ROOT / "sync_bridge.js").read_text(encoding="utf-8")
    html = html.replace("<script>", "<script>\n" + bridge + "\n</script>\n<script>", 1)
    out = Path(tempfile.gettempdir()) / "irt-desk-page"
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(html, encoding="utf-8")
    return str(out)


stamp = tuple((ROOT / f).stat().st_mtime for f in ("irt-revision.html", "sync_bridge.js"))
desk = components.declare_component("irt_desk", path=build_page(stamp))


# ---------- where progress is kept ----------
class GistStore:
    """Keeps progress in a private GitHub gist, so every device sees the same data."""

    DESCRIPTION = "IRT Revision Desk progress"
    FILE = "irt-progress.json"
    API = "https://api.github.com"

    def __init__(self, token):
        self.headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
        self.gist_id = None

    def _find(self):
        if self.gist_id:
            return self.gist_id
        for page in range(1, 11):
            r = requests.get(f"{self.API}/gists", headers=self.headers,
                             params={"per_page": 100, "page": page}, timeout=15)
            r.raise_for_status()
            gists = r.json()
            for g in gists:
                if g.get("description") == self.DESCRIPTION and self.FILE in g.get("files", {}):
                    self.gist_id = g["id"]
                    return self.gist_id
            if len(gists) < 100:
                break
        return None

    def load(self):
        gist_id = self._find()
        if not gist_id:
            return None
        r = requests.get(f"{self.API}/gists/{gist_id}", headers=self.headers, timeout=15)
        r.raise_for_status()
        f = r.json()["files"].get(self.FILE)
        if not f:
            return None
        content = f["content"]
        if f.get("truncated"):
            content = requests.get(f["raw_url"], headers=self.headers, timeout=15).text
        return json.loads(content)

    def save(self, doc):
        body = {"files": {self.FILE: {"content": json.dumps(doc)}}}
        gist_id = self._find()
        if gist_id:
            r = requests.patch(f"{self.API}/gists/{gist_id}", headers=self.headers, json=body, timeout=15)
        else:
            body.update(description=self.DESCRIPTION, public=False)
            r = requests.post(f"{self.API}/gists", headers=self.headers, json=body, timeout=15)
            if r.ok:
                self.gist_id = r.json()["id"]
        r.raise_for_status()


class FileStore:
    """Local file, for running the app on your own machine."""

    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        return json.loads(self.path.read_text()) if self.path.exists() else None

    def save(self, doc):
        self.path.write_text(json.dumps(doc))


@st.cache_resource
def get_store():
    try:
        token = st.secrets.get("GITHUB_TOKEN")
    except Exception:
        token = None
    if token:
        return GistStore(token)
    if os.environ.get("IRT_PROGRESS_FILE"):
        return FileStore(os.environ["IRT_PROGRESS_FILE"])
    return None


store = get_store()
ss = st.session_state


def load_remote():
    try:
        return store.load(), None
    except Exception as e:
        return None, str(e)


if store and "remote" not in ss:
    ss.remote, ss.error = load_remote()
ss.setdefault("remote", None)
ss.setdefault("error", None)
ss.setdefault("ack", None)
ss.setdefault("done_seq", None)

# Handle the latest request from the page before drawing it again.
msg = ss.get("desk")
if store and msg and msg.get("seq") != ss.done_seq:
    ss.done_seq = msg["seq"]
    if msg.get("op") == "pull":
        ss.remote, ss.error = load_remote()
        ss.ack = {"seq": msg["seq"], "ok": ss.error is None}
    elif msg.get("op") == "save":
        try:
            current = store.load()
            if current and current.get("savedAt", 0) > (msg.get("base") or 0):
                # Another device saved since this one last synced: send that back to merge.
                ss.remote = current
                ss.ack = {"seq": msg["seq"], "ok": False, "conflict": True}
            else:
                doc = {"data": msg.get("data") or {}, "savedAt": int(time.time() * 1000)}
                store.save(doc)
                ss.remote, ss.error = doc, None
                ss.ack = {"seq": msg["seq"], "ok": True, "savedAt": doc["savedAt"]}
        except Exception as e:
            ss.error = str(e)
            ss.ack = {"seq": msg["seq"], "ok": False}

desk(enabled=bool(store), remote=ss.remote, ack=ss.ack, key="desk", default=None)
