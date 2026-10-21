// Cross-device sync for the revision page when it runs inside Streamlit.
// The page calls window.IRT_REMOTE.attach() on start and .changed() after
// every save; this file talks to streamlit_app.py, which stores the progress.
(function () {
  const post = (type, extra) =>
    parent.postMessage(Object.assign({ isStreamlitMessage: true, type }, extra), "*");

  const client = Math.random().toString(36).slice(2);
  let app = null, first, gotFirst = false, enabled = false;
  let n = 0, pending = null, pendingTimer = null, changedWhilePending = false, pushTimer = null;
  let meta = { base: 0, dirty: false };
  try { meta = Object.assign(meta, JSON.parse(localStorage.getItem("irt.sync") || "{}")); } catch (e) {}
  const saveMeta = () => { try { localStorage.setItem("irt.sync", JSON.stringify(meta)); } catch (e) {} };
  const status = t => app && app.status(t);

  const hasData = d => {
    const p = d.progress || {};
    return ["q", "cards", "nums", "topicsDone"].some(k => p[k] && Object.keys(p[k]).length) ||
      (p.history && p.history.length) || (d.custom && d.custom.items && d.custom.items.length);
  };
  const local = () => JSON.parse(JSON.stringify(app.get()));

  // Used only when both devices changed things since they last synced.
  function mergeCounts(a = {}, b = {}) {
    const o = Object.assign({}, a);
    for (const [k, v] of Object.entries(b)) {
      const u = o[k];
      o[k] = !u ? v : ((v.r || 0) + (v.w || 0) > (u.r || 0) + (u.w || 0) ? v : u);
    }
    return o;
  }
  function merge(a, b) {
    const pa = a.progress || {}, pb = b.progress || {};
    const hist = {};
    for (const h of (pb.history || []).concat(pa.history || [])) hist[h.at + "|" + h.label] = h;
    const items = {};
    for (const q of ((b.custom || {}).items || []).concat((a.custom || {}).items || [])) items[q.id] = q;
    return {
      progress: Object.assign({}, pb, pa, {
        topicsDone: Object.assign({}, pb.topicsDone, pa.topicsDone),
        q: mergeCounts(pa.q, pb.q), cards: mergeCounts(pa.cards, pb.cards), nums: mergeCounts(pa.nums, pb.nums),
        history: Object.values(hist).sort((x, y) => x.at - y.at),
        work: Object.assign({}, pb.work, pa.work),
      }),
      custom: Object.assign({}, b.custom, a.custom, { items: Object.values(items) }),
    };
  }

  function send(op, payload) {
    n++;
    pending = { seq: client + ":" + n, op };
    changedWhilePending = false;
    clearTimeout(pendingTimer);
    pendingTimer = setTimeout(() => { pending = null; status("Saved in this browser (sync is slow, will retry)"); }, 20000);
    post("streamlit:setComponentValue", {
      value: Object.assign({ op, seq: pending.seq, base: meta.base }, payload), dataType: "json",
    });
  }
  function push() {
    if (!enabled || !app) return;
    if (pending) { changedWhilePending = true; return; }
    status("Syncing…");
    send("save", { data: local() });
  }
  function pull() { if (enabled && app && !pending) send("pull", {}); }

  function reconcile(remote) {
    if (!remote) { hasData(local()) ? push() : status("Synced across your devices"); return; }
    if (!meta.dirty) {
      if (remote.savedAt !== meta.base) app.set(remote.data);
      meta.base = remote.savedAt; saveMeta();
      status("Synced across your devices");
    } else if (remote.savedAt === meta.base) {
      push();
    } else {
      app.set(merge(local(), remote.data));
      meta.base = remote.savedAt; saveMeta();
      push();
    }
  }

  function onRender(args) {
    enabled = !!args.enabled;
    if (!enabled) { status("Saved in this browser"); return; }
    const ack = args.ack;
    if (pending && ack && ack.seq === pending.seq) {
      const op = pending.op;
      pending = null; clearTimeout(pendingTimer);
      if (op === "pull") { reconcile(args.remote); return; }
      if (ack.ok) {
        meta.base = ack.savedAt; meta.dirty = changedWhilePending; saveMeta();
        if (changedWhilePending) push(); else status("Synced across your devices");
      } else if (ack.conflict) {
        reconcile(args.remote);
      } else {
        status("Saved in this browser (sync failed, will retry)");
      }
    }
  }

  window.addEventListener("message", e => {
    const m = e.data;
    if (!m || m.type !== "streamlit:render") return;
    const args = m.args || {};
    if (!app) { first = args; gotFirst = true; return; }
    if (!gotFirst) { gotFirst = true; onRender(args); if (enabled) reconcile(args.remote); return; }
    onRender(args);
  });

  window.IRT_REMOTE = {
    attach(a) {
      app = a;
      if (!meta.base && hasData(local())) { meta.dirty = true; saveMeta(); }
      status("Connecting…");
      if (first) { const f = first; first = null; onRender(f); if (enabled) reconcile(f.remote); }
    },
    changed() {
      meta.dirty = true; saveMeta();
      if (!enabled) { status("Saved in this browser"); return; }
      if (pending) changedWhilePending = true;
      clearTimeout(pushTimer); pushTimer = setTimeout(push, 1000);
    },
  };

  // Pick up changes made on another device when you come back to this tab.
  document.addEventListener("visibilitychange", () => { if (!document.hidden) { meta.dirty ? push() : pull(); } });
  setInterval(() => { if (!document.hidden && !meta.dirty) pull(); }, 120000);

  post("streamlit:componentReady", { apiVersion: 1 });
  post("streamlit:setFrameHeight", { height: Math.max(window.innerHeight, 900) });

  // Links like "#property" must stay inside this frame.
  document.addEventListener("click", e => {
    const a = e.target.closest && e.target.closest('a[href^="#"]');
    if (a) { e.preventDefault(); location.hash = a.getAttribute("href"); }
  }, true);
})();
