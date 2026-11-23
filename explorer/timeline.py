"""Interactive shot timeline rendered as a self-contained HTML/JS component.

Rows (top to bottom): time axis, one thumbnail per shot, shot boundaries
(coloured by shot scale, labelled with the main person), and one or more
lanes of pattern hits. Hovering a hit shows one thumbnail per shot of the
sequence; clicking pins that preview. Zooming happens client side.
"""

from __future__ import annotations

import base64
import html
import json

from explorer.data import SHOT_SCALES, Video
from explorer.patterns import Hit

# Categorical slots (light, dark) in fixed order - see dataviz reference palette.
SERIES = [
    ("#2a78d6", "#3987e5"), ("#eb6834", "#d95926"), ("#1baf7a", "#199e70"),
    ("#eda100", "#c98500"), ("#e87ba4", "#d55181"), ("#008300", "#0ca30c"),
    ("#6250d6", "#9085e9"), ("#e34948", "#e66767"),
]
# Hits skip slot 1 (blue) because blue already encodes the shot scale.
HIT_SERIES = SERIES[1:]
OTHER = ("#898781", "#898781")
# Ordinal blue ramp for shot scales, Extreme Close-Up (darkest) -> Long (lightest).
SCALE_COLORS = {
    "Extreme Close-Up": ("#0d366b", "#0d366b"),
    "Close-Up": ("#1c5cab", "#1c5cab"),
    "Medium": ("#3987e5", "#3987e5"),
    "Full": ("#6da7ec", "#6da7ec"),
    "Long": ("#9ec5f4", "#9ec5f4"),
}
SCALE_ABBR = {"Extreme Close-Up": "ECU", "Close-Up": "CU", "Medium": "M", "Full": "F", "Long": "L"}


def group_colors(groups: list[str]) -> dict[str, tuple[str, str]]:
    """Colour per group in order of first appearance; >7 groups fold into grey."""
    out: dict[str, tuple[str, str]] = {}
    for g in groups:
        if g not in out:
            out[g] = HIT_SERIES[len(out)] if len(out) < len(HIT_SERIES) else OTHER
    return out


def _b64(data: bytes | None) -> str | None:
    return "data:image/jpeg;base64," + base64.b64encode(data).decode() if data else None


def _lanes(hits: list[Hit]) -> list[int]:
    """Greedy lane assignment so overlapping hits don't cover each other."""
    lane_end: list[int] = []
    lanes = []
    for h in hits:
        lo, hi = min(h.shots), max(h.shots)
        for k, end in enumerate(lane_end):
            if lo > end:
                lane_end[k] = hi
                lanes.append(k)
                break
        else:
            lane_end.append(hi)
            lanes.append(len(lane_end) - 1)
    return lanes


def render_timeline(video: Video, hits: list[Hit], theme: str = "light") -> tuple[str, int]:
    """Return (html, height) for ``st.components.v1.html``."""
    thumbs = video.images([s.thumbnail_id for s in video.shots])
    colors = group_colors([h.group for h in hits])
    order = sorted(range(len(hits)), key=lambda i: min(hits[i].shots))
    hits = [hits[i] for i in order]
    lanes = _lanes(hits)

    data = {
        "duration": video.duration,
        "shots": [
            {
                "i": s.index, "start": s.start, "end": s.end,
                "scale": s.scale, "abbr": SCALE_ABBR.get(s.scale, "?"),
                "person": video.label(s.main_person) if s.main_person else "",
                "persons": [video.label(p) for p, _ in s.persons.most_common()],
                "thumb": _b64(thumbs.get(s.thumbnail_id)),
            }
            for s in video.shots
        ],
        "hits": [
            {"shots": h.shots, "label": h.label, "group": h.group, "lane": lane,
             "color": colors[h.group]}
            for h, lane in zip(hits, lanes)
        ],
        "groups": [{"name": g, "color": c} for g, c in colors.items()],
        "scales": [{"name": s, "abbr": SCALE_ABBR[s], "color": SCALE_COLORS[s]} for s in SHOT_SCALES],
    }
    n_lanes = max(lanes, default=-1) + 1
    height = 24 + 18 + 64 + 26 + max(n_lanes, 1) * 26 + 40 + 290
    page = _TEMPLATE.replace("__DATA__", json.dumps(data)).replace(
        "__THEME__", html.escape("dark" if theme == "dark" else "light")
    )
    return page, height


_TEMPLATE = r"""<!doctype html>
<html data-theme="__THEME__"><head><meta charset="utf-8">
<style>
  :root { color-scheme: light;
    --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781;
    --grid:#e1e0d9; --axis:#c3c2b7; --ring:rgba(11,11,11,.10); --panel:#ffffff; }
  :root[data-theme="dark"] { color-scheme: dark;
    --surface:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --muted:#898781;
    --grid:#2c2c2a; --axis:#383835; --ring:rgba(255,255,255,.10); --panel:#262624; }
  * { box-sizing: border-box; }
  body { margin:0; font:12px/1.3 system-ui,-apple-system,"Segoe UI",sans-serif;
         color:var(--ink); background:transparent; }
  #wrap { position:relative; }
  .bar { display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin-bottom:6px; }
  .bar button { font:inherit; border:1px solid var(--axis); background:var(--surface);
    color:var(--ink); border-radius:6px; padding:2px 9px; cursor:pointer; }
  .bar button:hover { border-color:var(--muted); }
  .legend { display:flex; gap:10px; flex-wrap:wrap; color:var(--ink2); }
  .legend span { display:inline-flex; align-items:center; gap:4px; }
  .sw { width:10px; height:10px; border-radius:2px; display:inline-block; }
  #scroll { overflow-x:auto; overflow-y:hidden; background:var(--surface);
            border:1px solid var(--ring); border-radius:8px; padding:4px 0 6px; }
  #track { position:relative; }
  .tick { position:absolute; top:0; height:14px; border-left:1px solid var(--axis);
          color:var(--muted); padding-left:3px; font-size:10px; white-space:nowrap; }
  .thumb { position:absolute; height:60px; background-size:cover; background-position:center;
           border-radius:3px; background-color:var(--grid); }
  .shot { position:absolute; height:22px; border-radius:3px; color:#fff; font-size:10px;
          display:flex; align-items:center; justify-content:center; overflow:hidden;
          white-space:nowrap; cursor:default; }
  .shot.none { background:var(--grid); color:var(--muted); }
  .hit { position:absolute; height:20px; border-radius:4px; color:#fff; font-size:11px;
         font-weight:600; display:flex; align-items:center; padding:0 6px; overflow:hidden;
         white-space:nowrap; cursor:pointer; box-shadow:0 0 0 2px var(--surface); }
  .hit.yellow { color:#0b0b0b; }
  .hit.active { outline:2px solid var(--ink); outline-offset:1px; }
  .shot:hover, .thumb:hover { outline:2px solid var(--ink); }
  #tip { position:absolute; display:none; z-index:10; background:var(--panel);
         border:1px solid var(--ring); border-radius:8px; padding:8px 10px;
         box-shadow:0 6px 24px rgba(0,0,0,.18); max-width:min(720px, 96vw); overflow-y:auto; }
  #tip h4 { margin:0 0 6px; font-size:12px; }
  #tip .muted { color:var(--muted); font-weight:400; }
  .seq { display:flex; flex-wrap:wrap; gap:6px; }
  .seq figure { margin:0; width:128px; }
  .seq img, .seq .noimg { width:128px; height:72px; object-fit:cover; border-radius:4px;
         display:block; background:var(--grid); }
  .seq figcaption { color:var(--ink2); font-size:11px; margin-top:2px; display:flex;
         justify-content:space-between; }
  .seq b { color:var(--ink); }
  .empty { color:var(--muted); padding:4px 8px; }
</style></head>
<body><div id="wrap">
  <div class="bar">
    <button id="zout" title="Zoom out">−</button>
    <button id="zfit" title="Fit to width">Fit</button>
    <button id="zin" title="Zoom in">+</button>
    <div class="legend" id="legend"></div>
  </div>
  <div id="scroll"><div id="track"></div></div>
  <div id="tip"></div>
</div>
<script>
const D = __DATA__;
const dark = document.documentElement.dataset.theme === "dark";
const col = c => c[dark ? 1 : 0];
const scaleColor = Object.fromEntries(D.scales.map(s => [s.name, col(s.color)]));
const track = document.getElementById("track"), scroll = document.getElementById("scroll");
const tip = document.getElementById("tip"), wrap = document.getElementById("wrap");
let zoom = 1, pinned = null, hitEls = [];
const fmt = t => { const m = Math.floor(t / 60), s = (t % 60).toFixed(1).padStart(4, "0"); return `${m}:${s}`; };
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

// legend: scales + pattern groups
const lg = document.getElementById("legend");
lg.innerHTML = D.scales.map(s => `<span><i class="sw" style="background:${col(s.color)}"></i>${s.abbr} = ${esc(s.name)}</span>`).join("")
  + (D.groups.length ? '<span style="margin-left:8px">Hits:</span>' : "")
  + D.groups.map(g => `<span><i class="sw" style="background:${col(g.color)}"></i>${esc(g.name)}</span>`).join("");

function el(cls, x, y, w, extra = "") {
  const d = document.createElement("div");
  d.className = cls;
  d.style.cssText = `left:${x}px;top:${y}px;width:${Math.max(w, 1)}px;${extra}`;
  track.appendChild(d);
  return d;
}

function render() {
  const pad = 8, avail = scroll.clientWidth - 2 * pad;
  const pps = Math.max(avail / Math.max(D.duration, 1), 0.5) * zoom;
  const W = D.duration * pps;
  track.innerHTML = "";
  const lanes = Math.max(1, ...D.hits.map(h => h.lane + 1));
  track.style.width = (W + 2 * pad) + "px";
  track.style.height = (18 + 64 + 26 + lanes * 26) + "px";
  const X = t => pad + t * pps;

  // time axis
  const steps = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600];
  const step = steps.find(s => s * pps >= 70) || 900;
  for (let t = 0; t <= D.duration; t += step) el("tick", X(t), 0, 1).textContent = fmt(t).replace(/\.0$/, "");

  D.shots.forEach(s => {
    const x = X(s.start), w = (s.end - s.start) * pps - 2;
    const th = el("thumb", x, 18, w, s.thumb ? `background-image:url(${s.thumb})` : "");
    const sh = el("shot" + (s.scale ? "" : " none"), x, 18 + 64, w,
      s.scale ? `background:${scaleColor[s.scale]};${["Full", "Long"].includes(s.scale) ? "color:#0b0b0b" : ""}` : "");
    if (w > 22) sh.textContent = w > 46 ? `${s.abbr}${s.person ? " · " + s.person : ""}` : (s.person || s.abbr);
    for (const node of [th, sh]) {
      node.onmouseenter = e => { if (!pinned) showShot(s, e); };
      node.onmouseleave = () => { if (!pinned) hide(); };
    }
  });

  D.hits.forEach((h, k) => {
    const a = D.shots[Math.min(...h.shots)], b = D.shots[Math.max(...h.shots)];
    const x = X(a.start), w = (b.end - a.start) * pps - 2;
    const c = col(h.color);
    const d = el("hit" + (c === "#eda100" ? " yellow" : "") + (pinned === k ? " active" : ""),
      x, 18 + 64 + 26 + h.lane * 26, w, `background:${c}`);
    d.textContent = h.label;
    d.onmouseenter = e => { if (pinned === null) showHit(h, d); };
    d.onmouseleave = () => { if (pinned === null) hide(); };
    d.onclick = e => {
      e.stopPropagation();
      pinned = pinned === k ? null : k;
      render();
      if (pinned !== null) showHit(h, hitEls[k]); else hide();
    };
    hitEls[k] = d;
  });
}

function place(anchor) {
  const r = anchor.getBoundingClientRect(), wr = wrap.getBoundingClientRect();
  tip.style.display = "block";
  const tw = tip.offsetWidth;
  let left = r.left - wr.left;
  left = Math.max(0, Math.min(left, wrap.clientWidth - tw));
  tip.style.left = left + "px";
  const top = r.bottom - wr.top + 8;
  tip.style.top = top + "px";
  tip.style.maxHeight = Math.max(120, window.innerHeight - top - 8) + "px";
}

function figure(s) {
  const img = s.thumb ? `<img src="${s.thumb}" alt="Shot ${s.i + 1}">` : `<div class="noimg"></div>`;
  return `<figure>${img}<figcaption><span><b>${esc(s.person || "–")}</b> · ${esc(s.abbr)}</span><span>#${s.i + 1} ${fmt(s.start)}</span></figcaption></figure>`;
}

function showHit(h, anchor) {
  const shots = h.shots.map(i => D.shots[i]);
  const a = shots[0], b = shots[shots.length - 1];
  tip.innerHTML = `<h4>${esc(h.label)} <span class="muted">· ${shots.length} shots · ${fmt(a.start)}–${fmt(b.end)} (${(b.end - a.start).toFixed(1)} s)${pinned !== null ? " · pinned, click again to release" : " · click to pin"}</span></h4>`
    + `<div class="seq">${shots.map(figure).join("")}</div>`;
  place(anchor);
}

function showShot(s, e) {
  tip.innerHTML = `<h4>Shot ${s.i + 1} <span class="muted">· ${fmt(s.start)}–${fmt(s.end)} · ${esc(s.scale || "no scale")} · persons: ${esc(s.persons.join(", ") || "none")}</span></h4><div class="seq">${figure(s)}</div>`;
  place(e.currentTarget);
}

function hide() { tip.style.display = "none"; }

document.getElementById("zin").onclick = () => { zoom = Math.min(zoom * 1.6, 200); render(); };
document.getElementById("zout").onclick = () => { zoom = Math.max(zoom / 1.6, 1); render(); };
document.getElementById("zfit").onclick = () => { zoom = 1; render(); };
tip.onclick = e => e.stopPropagation();
document.body.onclick = () => { if (pinned !== null) { pinned = null; hide(); render(); } };
scroll.addEventListener("scroll", () => { if (pinned === null) hide(); });
window.addEventListener("resize", render);

// start zoomed so that the median shot is at least ~70px wide
const durs = D.shots.map(s => s.end - s.start).sort((a, b) => a - b);
const med = durs.length ? durs[Math.floor(durs.length / 2)] : 1;
const fitPps = (scroll.clientWidth - 16) / Math.max(D.duration, 1);
zoom = Math.max(1, 70 / (med * fitPps));
render();
</script></body></html>
"""
