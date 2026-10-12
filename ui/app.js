/* Aura - UI + audio engine. No dependencies. */
"use strict";

/* ============================================================ helpers */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const fmtTime = s => { if (!isFinite(s) || s < 0) s = 0; s = Math.floor(s); return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); };
const fmtTotal = s => { const m = Math.round(s / 60); return m >= 60 ? `${Math.floor(m / 60)} hr ${m % 60} min` : `${m} min`; };
const plural = (n, w) => `${n.toLocaleString()} ${w}${n === 1 ? "" : "s"}`;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

async function api(path, body, method) {
  const r = await fetch(path, {
    method: method || (body !== undefined ? "POST" : "GET"),
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || r.statusText);
  return j;
}

const IC = {
  logo: '<path d="M2 12h3l2.5-7 4 14 3.5-10 2 3H22"/>',
  home: '<path d="M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
  library: '<rect x="3" y="3" width="6" height="18" rx="1.2"/><rect x="11" y="3" width="6" height="18" rx="1.2"/><path d="M19 5l2 .6-3.6 14.6-2-.5z"/>',
  heart: '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1.1L12 21l7.8-7.5 1-1.1a5.5 5.5 0 0 0 0-7.8z"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/>',
  cog: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
  play: '<path d="M7 4.5v15a1 1 0 0 0 1.5.86l12-7.5a1 1 0 0 0 0-1.72l-12-7.5A1 1 0 0 0 7 4.5z" fill="currentColor" stroke="none"/>',
  pause: '<rect x="5.5" y="4" width="4.5" height="16" rx="1.2" fill="currentColor" stroke="none"/><rect x="14" y="4" width="4.5" height="16" rx="1.2" fill="currentColor" stroke="none"/>',
  prev: '<path d="M19 5.5v13a.9.9 0 0 1-1.4.75l-9-6.5a.9.9 0 0 1 0-1.5l9-6.5A.9.9 0 0 1 19 5.5z" fill="currentColor" stroke="none"/><path d="M5 5v14"/>',
  next: '<path d="M5 5.5v13a.9.9 0 0 0 1.4.75l9-6.5a.9.9 0 0 0 0-1.5l-9-6.5A.9.9 0 0 0 5 5.5z" fill="currentColor" stroke="none"/><path d="M19 5v14"/>',
  shuffle: '<path d="M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5"/>',
  repeat: '<path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><path d="M7 23l-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>',
  repeat1: '<path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><path d="M7 23l-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/><path d="M11 10h1.5v4.5" />',
  queue: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
  sliders: '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>',
  volume: '<path d="M11 5L6 9H2v6h4l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M19 5a10 10 0 0 1 0 14"/>',
  volume0: '<path d="M11 5L6 9H2v6h4l5 4z"/><path d="M22 9l-6 6M16 9l6 6"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  x: '<path d="M18 6L6 18M6 6l12 12"/>',
  more: '<circle cx="5" cy="12" r="1.3" fill="currentColor"/><circle cx="12" cy="12" r="1.3" fill="currentColor"/><circle cx="19" cy="12" r="1.3" fill="currentColor"/>',
  left: '<path d="M15 18l-6-6 6-6"/>', right: '<path d="M9 18l6-6-6-6"/>',
  music: '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  trash: '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>',
  refresh: '<path d="M21 12a9 9 0 0 1-15.5 6.2L3 16M3 12A9 9 0 0 1 18.5 5.8L21 8M21 3v5h-5M3 21v-5h5"/>',
  radio: '<circle cx="12" cy="12" r="2"/><path d="M16.2 7.8a6 6 0 0 1 0 8.4M7.8 16.2a6 6 0 0 1 0-8.4M19 5a10 10 0 0 1 0 14M5 19a10 10 0 0 1 0-14"/>',
  expand: '<path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7"/>',
  next1: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  disc: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.5"/>',
  queueadd: '<path d="M3 6h12M3 12h12M3 18h8M18 15v6M15 18h6"/>',
  edit: '<path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
};
const ic = n => `<i data-ic="${n}"><svg viewBox="0 0 24 24">${IC[n] || ""}</svg></i>`;
const hydrate = (root = document) => $$("i[data-ic]:empty", root).forEach(i => { i.innerHTML = `<svg viewBox="0 0 24 24">${IC[i.dataset.ic] || ""}</svg>`; });

function toast(msg, err = false) {
  const el = document.createElement("div");
  el.className = "toast" + (err ? " err" : "");
  el.textContent = msg;
  $("#toasts").append(el);
  setTimeout(() => el.remove(), err ? 4200 : 2400);
}

/* ============================================================ state */
const S = {
  settings: {}, caps: {}, lib: [], likes: new Map(), playlists: [], jobs: [],
  eq: null, view: null, viewTok: 0,
};
const Q = { list: [], i: -1, shuffle: false, repeat: "off", stack: [], tok: 0 };
const REG = { lists: [], acts: [] };           // per-render registries (rows / click handlers)
const reg = fn => REG.acts.push(fn) - 1;

const key = t => t.key;
const isLiked = t => S.likes.has(t.key);
const normStr = s => (s || "").toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, " ").trim();
const firstArtist = a => (a || "").split(/,|&| feat\.| x /)[0].trim();

function qualityOf(t) {
  const q = t.q || {};
  if (t.source === "local") {
    const codec = (q.codec || "").toUpperCase();
    const hires = q.lossless && (q.bit_depth >= 24 || q.sample_rate >= 88200);
    let txt = codec;
    if (q.lossless && q.bit_depth && q.sample_rate) txt += ` ${q.bit_depth}/${+(q.sample_rate / 1000).toFixed(1)}`;
    else if (q.bitrate) txt += ` ${q.bitrate}k`;
    return { txt: hires ? "Hi-Res " + txt : txt, cls: hires ? "hires" : q.lossless ? "lossless" : "" };
  }
  const s = t.sq;
  if (s) return { txt: `${(s.codec || s.ext || "").toUpperCase()}${s.abr ? " " + s.abr + "k" : ""}`, cls: "web" };
  return { txt: "Stream", cls: "web" };
}
const badge = t => { const q = qualityOf(t); return `<span class="badge ${q.cls}">${esc(q.txt)}</span>`; };

/* ============================================================ menu */
function openMenu(x, y, items, header) {
  const m = $("#menu");
  m.innerHTML = (header ? `<div class="mh">${esc(header)}</div>` : "") + items.map((it, i) => it === "-" ? "<hr>" :
    `<button data-i="${i}">${it.icon ? ic(it.icon) : ""}<span>${esc(it.label)}</span></button>`).join("");
  m.hidden = false;
  m.onclick = e => {
    const b = e.target.closest("button[data-i]"); if (!b) return;
    const it = items[+b.dataset.i];
    if (!it.keep) closeMenu();
    it.fn();
  };
  const r = m.getBoundingClientRect();
  m.style.left = clamp(x, 8, innerWidth - r.width - 8) + "px";
  m.style.top = clamp(y, 8, innerHeight - r.height - 8) + "px";
}
const closeMenu = () => { $("#menu").hidden = true; };
document.addEventListener("mousedown", e => { if (!e.target.closest("#menu")) closeMenu(); });
document.addEventListener("scroll", closeMenu, true);

function trackMenu(t, x, y, ctx = {}) {
  const items = [
    { label: "Play next", icon: "next1", fn: () => queueAdd([t], true) },
    { label: "Add to queue", icon: "queueadd", fn: () => queueAdd([t], false) },
    { label: "Start radio", icon: "radio", fn: () => startRadio(t) },
    "-",
    { label: "Add to playlist", icon: "plus", keep: true, fn: () => playlistMenu(t, x, y) },
    { label: isLiked(t) ? "Remove from liked songs" : "Add to liked songs", icon: "heart", fn: () => toggleLike(t) },
  ];
  if (t.source !== "local") items.push({ label: "Download", icon: "download", keep: true, fn: () => downloadMenu(t, x, y) });
  if (firstArtist(t.artist)) items.push({ label: "Go to artist", icon: "user", fn: () => nav("#/artist/" + encodeURIComponent(firstArtist(t.artist))) });
  if (ctx.playlistId && t.item_id) items.push("-", { label: "Remove from this playlist", icon: "trash", fn: async () => { await api(`/api/playlists/${ctx.playlistId}/remove`, { item_id: t.item_id }); render(); loadPlaylists(); } });
  openMenu(x, y, items);
}
function playlistMenu(t, x, y) {
  const items = [{ label: "New playlist", icon: "plus", fn: async () => { const n = prompt("Playlist name"); if (n === null) return; await api("/api/playlists", { name: n, tracks: [strip(t)] }); loadPlaylists(); toast("Added to new playlist"); } }];
  if (S.playlists.length) items.push("-");
  S.playlists.forEach(p => items.push({ label: p.name, icon: "music", fn: async () => { await api(`/api/playlists/${p.id}/add`, { tracks: [strip(t)] }); loadPlaylists(); toast(`Added to ${p.name}`); } }));
  openMenu(x, y, items, "Add to playlist");
}
function downloadMenu(t, x, y) {
  const items = [{ label: "Original quality (best)", fn: () => download([t], "original") }];
  if (S.caps.ffmpeg) items.push({ label: "MP3 320 kbps", fn: () => download([t], "mp3_320") }, { label: "MP3 192 kbps", fn: () => download([t], "mp3_192") });
  openMenu(x, y, items, "Download as");
}
const strip = t => { const c = { ...t }; delete c.item_id; return c; };

/* ============================================================ audio engine + EQ */
const audio = new Audio();
audio.preload = "auto";
const AC = { ctx: null };

const BANDS = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000];
const BAND_LABEL = ["31", "62", "125", "250", "500", "1k", "2k", "4k", "8k", "16k"];
const ADV_PRESETS = {
  "Flat": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], "Bass boost": [6, 5, 4, 2, 0, 0, 0, 0, 0, 0],
  "Treble boost": [0, 0, 0, 0, 0, 1, 2, 4, 5, 6], "Vocal": [-2, -2, -1, 1, 3, 4, 3, 1, 0, -1],
  "Rock": [5, 4, 2, -1, -2, -1, 2, 3, 4, 4], "Pop": [-1, 1, 3, 4, 3, 0, -1, -1, 1, 2],
  "Jazz": [3, 2, 1, 2, -2, -2, 0, 1, 2, 3], "Classical": [4, 3, 2, 2, -1, -1, 0, 2, 3, 4],
  "Electronic": [5, 4, 1, 0, -2, 2, 1, 2, 4, 5], "Hip-hop": [5, 5, 3, 3, -1, -1, 1, -1, 2, 3],
  "Acoustic": [4, 4, 3, 1, 2, 2, 3, 3, 3, 2], "Loudness": [6, 4, 1, 0, -1, 0, -1, 1, 4, 5],
  "Late night": [-3, -2, 0, 1, 2, 3, 3, 2, 1, 0],
};
const BASIC_PRESETS = {
  "Flat": [0, 0, 0], "Bass boost": [8, 0, 0], "Vocal": [-2, 4, 1], "Treble boost": [0, 0, 8],
  "Rock": [5, -2, 4], "Pop": [-1, 3, 2], "Electronic": [6, -1, 5], "Warm": [4, 1, -3],
};
const eqDefault = () => ({ on: true, mode: "basic", pre: 0, basic: { bass: 0, mid: 0, treble: 0 }, bands: Array(10).fill(0), boost: 0, width: 100, dyn: "off", preset: "Flat" });
const DYN = {
  off: { threshold: 0, knee: 0, ratio: 1, attack: .003, release: .25 },
  gentle: { threshold: -26, knee: 30, ratio: 3, attack: .012, release: .3 },
  limiter: { threshold: -3, knee: 0, ratio: 20, attack: .001, release: .1 },
};

function initAudio() {
  if (AC.ctx) { if (AC.ctx.state === "suspended") AC.ctx.resume(); return; }
  const Ctx = window.AudioContext || window.webkitAudioContext;
  const rate = +S.settings.output_rate || 0;
  try { AC.ctx = new Ctx(rate ? { sampleRate: rate, latencyHint: "playback" } : { latencyHint: "playback" }); }
  catch { AC.ctx = new Ctx(); }
  const c = AC.ctx;
  const filt = (type, f, q = 1.1) => { const n = c.createBiquadFilter(); n.type = type; n.frequency.value = f; n.Q.value = q; n.gain.value = 0; return n; };
  const gain = (v = 1) => { const g = c.createGain(); g.gain.value = v; return g; };

  AC.src = c.createMediaElementSource(audio);
  AC.pre = gain();
  AC.bass = filt("lowshelf", 110); AC.mid = filt("peaking", 1000, .8); AC.treble = filt("highshelf", 6000);
  AC.bands = BANDS.map(f => filt("peaking", f, 1.15));
  AC.boost = filt("lowshelf", 85);
  // mid/side stereo width
  AC.wIn = gain(); AC.wIn.channelCount = 2; AC.wIn.channelCountMode = "explicit";
  const split = c.createChannelSplitter(2), merge = c.createChannelMerger(2);
  const mid = gain(1); AC.side = gain(1); const sideInv = gain(-1);
  const mL = gain(.5), mR = gain(.5), sL = gain(.5), sR = gain(-.5), outL = gain(1), outR = gain(1);
  AC.wIn.connect(split);
  split.connect(mL, 0); split.connect(mR, 1); split.connect(sL, 0); split.connect(sR, 1);
  mL.connect(mid); mR.connect(mid); sL.connect(AC.side); sR.connect(AC.side);
  mid.connect(outL); mid.connect(outR); AC.side.connect(outL); AC.side.connect(sideInv); sideInv.connect(outR);
  outL.connect(merge, 0, 0); outR.connect(merge, 0, 1);
  AC.comp = c.createDynamicsCompressor();
  AC.master = gain(1);
  AC.an = c.createAnalyser(); AC.an.fftSize = 512; AC.an.smoothingTimeConstant = .82;

  const chain = [AC.src, AC.pre, AC.bass, AC.mid, AC.treble, ...AC.bands, AC.boost, AC.wIn];
  chain.reduce((a, b) => (a.connect(b), b));
  merge.connect(AC.comp); AC.comp.connect(AC.master); AC.master.connect(AC.an); AC.an.connect(c.destination);
  applyEQ();
}

function applyEQ() {
  if (!AC.ctx) return;
  const e = S.eq, t = AC.ctx.currentTime, adv = e.mode === "advanced", on = e.on;
  const set = (p, v) => p.setTargetAtTime(v, t, .02);
  const gains = adv ? e.bands : [e.basic.bass, e.basic.mid, e.basic.treble];
  const headroom = on ? -Math.max(0, ...gains) * .6 : 0;       // auto headroom against clipping
  set(AC.pre.gain, Math.pow(10, ((on && adv ? e.pre : 0) + headroom) / 20));
  set(AC.bass.gain, on && !adv ? e.basic.bass : 0); set(AC.mid.gain, on && !adv ? e.basic.mid : 0); set(AC.treble.gain, on && !adv ? e.basic.treble : 0);
  AC.bands.forEach((b, i) => set(b.gain, on && adv ? e.bands[i] : 0));
  set(AC.boost.gain, on && adv ? e.boost : 0);
  set(AC.side.gain, on && adv ? e.width / 100 : 1);
  const d = DYN[on && adv ? e.dyn : "off"];
  AC.comp.threshold.setTargetAtTime(d.threshold, t, .02); AC.comp.knee.setTargetAtTime(d.knee, t, .02);
  AC.comp.ratio.setTargetAtTime(d.ratio, t, .02); AC.comp.attack.setTargetAtTime(d.attack, t, .02); AC.comp.release.setTargetAtTime(d.release, t, .02);
}
const saveEQ = debounce(() => api("/api/settings", { eq: S.eq }).catch(() => {}), 500);
const eqChanged = () => { applyEQ(); saveEQ(); };

/* ---- EQ panel ---- */
function fader(id, label, val, min, max, cls = "") {
  return `<div class="fader ${cls}"><div class="db" data-db="${id}">${val > 0 ? "+" : ""}${(+val).toFixed(0)}</div>
    <div class="rail"><input type="range" data-f="${id}" min="${min}" max="${max}" step="0.5" value="${val}" aria-label="${esc(label)} dB"></div><div class="hz">${esc(label)}</div></div>`;
}
const paintFader = inp => {
  const v = +inp.value, mn = +inp.min, mx = +inp.max;
  inp.style.setProperty("--p2", ((v - mn) / (mx - mn) * 100) + "%");
  const d = $(`[data-db="${inp.dataset.f}"]`); if (d) d.textContent = (v > 0 ? "+" : "") + v.toFixed(v % 1 ? 1 : 0);
};
function renderEQ() {
  const e = S.eq, adv = e.mode === "advanced";
  $("#eq-on").checked = e.on;
  $$("#eq-mode button").forEach(b => b.classList.toggle("on", b.dataset.m === e.mode));
  $("#eq-sub").textContent = adv ? "10-band graphic EQ, preamp and sound effects" : "Quick bass, mid and treble shaping";
  const custom = S.settings.eq_presets || {};
  const base = Object.keys(adv ? ADV_PRESETS : BASIC_PRESETS);
  const mine = Object.keys(custom).filter(n => custom[n].mode === e.mode);
  $("#eq-presets").innerHTML = base.map(n => `<button class="chip ${e.preset === n ? "on" : ""}" data-p="${esc(n)}">${esc(n)}</button>`).join("") +
    mine.map(n => `<button class="chip ${e.preset === n ? "on" : ""}" data-cp="${esc(n)}">★ ${esc(n)}</button>`).join("");
  $("#eq-basic").className = "eq-pane" + (adv ? "" : " show");
  $("#eq-adv").className = "eq-pane" + (adv ? " show" : "");
  $("#eq-basic").innerHTML = `<div class="faders three">${fader("bass", "Bass", e.basic.bass, -12, 12)}${fader("mid", "Mid", e.basic.mid, -12, 12)}${fader("treble", "Treble", e.basic.treble, -12, 12)}</div>`;
  $("#eq-adv").innerHTML = `<div class="faders"><div class="zero"></div>${fader("pre", "Preamp", e.pre, -12, 12, "pre")}${BANDS.map((f, i) => fader("b" + i, BAND_LABEL[i], e.bands[i], -12, 12)).join("")}</div>`;
  $("#eq-fx").style.display = adv ? "grid" : "none";
  $("#eq-fx").innerHTML = `
    <div class="fx"><label>Bass enhancer <span id="fx-boost-v">${e.boost} dB</span></label><input type="range" id="fx-boost" min="0" max="12" step="0.5" value="${e.boost}"></div>
    <div class="fx"><label>Stereo width <span id="fx-width-v">${e.width}%</span></label><input type="range" id="fx-width" min="0" max="200" step="5" value="${e.width}"></div>
    <div class="fx"><label>Dynamics</label><div class="seg" id="fx-dyn">${["off", "gentle", "limiter"].map(d => `<button data-d="${d}" class="${e.dyn === d ? "on" : ""}">${d[0].toUpperCase() + d.slice(1)}</button>`).join("")}</div></div>`;
  $$("#eq .rail input").forEach(paintFader);
  $$("#eq-fx input[type=range]").forEach(r => r.style.setProperty("--p", ((r.value - r.min) / (r.max - r.min) * 100) + "%"));
}
function bindEQ() {
  $("#eq-on").onchange = e => { S.eq.on = e.target.checked; eqChanged(); };
  $("#eq-mode").onclick = e => { const b = e.target.closest("button"); if (!b) return; S.eq.mode = b.dataset.m; S.eq.preset = ""; eqChanged(); renderEQ(); };
  $("#eq-x").onclick = () => closeEQ();
  $("#eq").addEventListener("mousedown", e => { if (e.target.id === "eq") closeEQ(); });
  $("#eq-presets").onclick = e => {
    const b = e.target.closest("button"); if (!b) return;
    const E = S.eq;
    if (b.dataset.p) {
      const n = b.dataset.p;
      if (E.mode === "advanced") E.bands = [...ADV_PRESETS[n]]; else { const [a, m, t] = BASIC_PRESETS[n]; E.basic = { bass: a, mid: m, treble: t }; }
      E.preset = n;
    } else if (b.dataset.cp) {
      const p = S.settings.eq_presets[b.dataset.cp];
      Object.assign(E, JSON.parse(JSON.stringify({ pre: p.pre, basic: p.basic, bands: p.bands, boost: p.boost, width: p.width, dyn: p.dyn })));
      E.preset = b.dataset.cp;
    }
    E.on = true; eqChanged(); renderEQ();
  };
  $("#eq").addEventListener("input", e => {
    const f = e.target.dataset.f, E = S.eq;
    if (f) {
      const v = +e.target.value; paintFader(e.target);
      if (f === "pre") E.pre = v; else if (f[0] === "b" && f.length <= 3) E.bands[+f.slice(1)] = v; else E.basic[f] = v;
      E.preset = ""; $$("#eq-presets .chip").forEach(c => c.classList.remove("on")); E.on = true; $("#eq-on").checked = true; eqChanged();
    } else if (e.target.id === "fx-boost" || e.target.id === "fx-width") {
      const r = e.target; r.style.setProperty("--p", ((r.value - r.min) / (r.max - r.min) * 100) + "%");
      if (r.id === "fx-boost") { E.boost = +r.value; $("#fx-boost-v").textContent = r.value + " dB"; } else { E.width = +r.value; $("#fx-width-v").textContent = r.value + "%"; }
      eqChanged();
    }
  });
  $("#eq-fx").addEventListener("click", e => { const b = e.target.closest("[data-d]"); if (!b) return; S.eq.dyn = b.dataset.d; eqChanged(); renderEQ(); });
  $("#eq-reset").onclick = () => { const m = S.eq.mode; S.eq = { ...eqDefault(), mode: m }; eqChanged(); renderEQ(); };
  $("#eq-save").onclick = async () => {
    const n = (prompt("Name this preset") || "").trim(); if (!n) return;
    const p = { ...(S.settings.eq_presets || {}) };
    p[n] = { mode: S.eq.mode, pre: S.eq.pre, basic: S.eq.basic, bands: S.eq.bands, boost: S.eq.boost, width: S.eq.width, dyn: S.eq.dyn };
    S.settings = await api("/api/settings", { eq_presets: p }); S.eq.preset = n; saveEQ(); renderEQ(); toast("Preset saved");
  };
}
const openEQ = () => { renderEQ(); $("#eq").classList.add("open"); };
const closeEQ = () => $("#eq").classList.remove("open");

/* ============================================================ visualizer */
let vizOn = false;
function drawViz() {
  if (!vizOn) return;
  const cv = $("#viz"), g = cv.getContext("2d"), W = cv.width, H = cv.height;
  g.clearRect(0, 0, W, H);
  if (AC.an) {
    const data = new Uint8Array(AC.an.frequencyBinCount); AC.an.getByteFrequencyData(data);
    const n = 56, bw = W / n, accent = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim();
    g.fillStyle = accent;
    for (let i = 0; i < n; i++) {
      const idx = Math.floor(Math.pow(i / n, 1.6) * (data.length * .78)) + 1;
      const v = data[idx] / 255, h = Math.max(4, v * H * .95);
      g.globalAlpha = .35 + v * .65;
      const x = i * bw + bw * .18, w = bw * .64, r = Math.min(w / 2, 6);
      g.beginPath(); g.roundRect ? g.roundRect(x, H - h, w, h, r) : g.rect(x, H - h, w, h); g.fill();
    }
    g.globalAlpha = 1;
  }
  requestAnimationFrame(drawViz);
}

/* ============================================================ covers */
function cover(src, cls = "", icon = "music") {
  return `<div class="cv ${cls}">${ic(icon)}${src ? `<img src="${esc(src)}" loading="lazy" referrerpolicy="no-referrer" alt="" onerror="this.remove()">` : ""}</div>`;
}
function mosaic(arts) {
  const a = (arts || []).filter(Boolean);
  if (a.length >= 4) return `<div class="cv mosaic">${a.slice(0, 4).map(s => `<img src="${esc(s)}" loading="lazy" referrerpolicy="no-referrer" alt="" onerror="this.style.visibility='hidden'">`).join("")}</div>`;
  return cover(a[0], "", "music");
}
const clean = t => { const c = { ...t }; delete c.sq; delete c.item_id; return c; };

/* ============================================================ playback */
function playList(tracks, i = 0) {
  if (!tracks.length) return;
  Q.list = tracks.map(t => t); Q.i = i; Q.stack = [];
  loadCurrent(); renderQueue();
}
function playShuffled(tracks) {
  if (!tracks.length) return;
  const l = [...tracks].sort(() => Math.random() - .5);
  Q.shuffle = true; syncModes(); playList(l, 0);
}
function queueAdd(tracks, atNext) {
  tracks = tracks.map(clean);
  if (Q.i < 0) return playList(tracks, 0);
  if (atNext) Q.list.splice(Q.i + 1, 0, ...tracks); else Q.list.push(...tracks);
  toast(atNext ? "Playing next" : "Added to queue"); renderQueue();
}
async function startRadio(t) {
  toast("Building radio…");
  try { const r = await api("/api/radio", { track: clean(t) }); playList([t, ...r.tracks], 0); }
  catch (e) { toast(e.message, true); }
}

async function loadCurrent() {
  const t = Q.list[Q.i]; if (!t) return;
  const my = ++Q.tok;
  initAudio(); setNow(t);
  let url;
  if (t.source === "local") url = `/local/${t.local_id}`;
  else {
    setBuffering(true);
    try {
      const p = new URLSearchParams({ src: t.source === "yt" ? "yt" : "sp", id: t.video_id || t.sp_id || "", t: t.title, a: t.artist, d: t.duration || 0 });
      const info = await api("/api/resolve?" + p);
      if (my !== Q.tok) return;
      t.sq = info; url = info.stream; paintQual(t);
    } catch (e) {
      if (my !== Q.tok) return;
      setBuffering(false); toast(e.message, true);
      setTimeout(() => { if (my === Q.tok) next(true); }, 1200); return;
    }
  }
  audio.src = url;
  try { await audio.play(); } catch (e) { if (my === Q.tok && e.name !== "AbortError") toast("Couldn't play this track", true); }
  if (my !== Q.tok) return;
  setBuffering(false);
  api("/api/played", { track: clean(t) }).catch(() => {});
  preloadNext(); updateMedia(t);
}
function preloadNext() {
  const n = Q.list[Q.i + 1];
  if (n && n.source !== "local" && !n.sq) {
    const p = new URLSearchParams({ src: n.source === "yt" ? "yt" : "sp", id: n.video_id || n.sp_id || "", t: n.title, a: n.artist, d: n.duration || 0 });
    api("/api/resolve?" + p).then(i => { n.sq = i; }).catch(() => {});
  }
}
async function extendWithRadio() {
  const last = Q.list[Q.list.length - 1];
  try {
    const r = await api("/api/radio", { track: clean(last) });
    const have = new Set(Q.list.map(t => t.key));
    const add = r.tracks.filter(t => !have.has(t.key));
    if (!add.length) return false;
    Q.list.push(...add); toast("Autoplay: similar songs added"); return true;
  } catch { return false; }
}
async function next(auto = false) {
  if (Q.i < 0) return;
  if (auto && Q.repeat === "one") { audio.currentTime = 0; audio.play(); return; }
  let ni;
  if (Q.shuffle && Q.list.length > 1) { do { ni = Math.floor(Math.random() * Q.list.length); } while (ni === Q.i); }
  else ni = Q.i + 1;
  if (ni >= Q.list.length) {
    if (Q.repeat === "all") ni = 0;
    else if (S.settings.autoplay_similar && await extendWithRadio()) ni = Q.i + 1;
    else { audio.pause(); audio.currentTime = 0; return; }
  }
  Q.stack.push(Q.i); Q.i = ni; loadCurrent(); renderQueue();
}
function prev() {
  if (Q.i < 0) return;
  if (audio.currentTime > 3 || (!Q.stack.length && Q.i === 0)) { audio.currentTime = 0; return; }
  Q.i = Q.stack.length ? Q.stack.pop() : Q.i - 1; loadCurrent(); renderQueue();
}
const toggle = () => { if (Q.i < 0) return; initAudio(); audio.paused ? audio.play() : audio.pause(); };
const curTrack = () => Q.list[Q.i];
const curDur = () => (isFinite(audio.duration) && audio.duration > 0 ? audio.duration : (curTrack()?.duration || 0));

function setBuffering(b) { $("#b-play").style.opacity = b ? .6 : 1; }
function setNow(t) {
  $("#p-title").textContent = t.title; $("#p-artist").innerHTML = artistLinks(t.artist);
  $("#p-art").innerHTML = ic("music") + (t.art ? `<img src="${esc(t.art)}" referrerpolicy="no-referrer" alt="" onerror="this.remove()">` : "");
  $("#np-title").textContent = t.title; $("#np-artist").textContent = [t.artist, t.album].filter(Boolean).join(" · ");
  $("#np-art").innerHTML = ic("music") + (t.art ? `<img src="${esc(t.art)}" referrerpolicy="no-referrer" alt="" onerror="this.remove()">` : "");
  $("#np-bg").style.backgroundImage = t.art ? `url("${t.art.replace(/"/g, "%22")}")` : "none";
  document.title = `${t.title} · ${t.artist} — Aura`;
  paintQual(t); paintLike(); markPlaying();
  $("#seek").value = 0; $("#seek").style.setProperty("--p", "0%"); $("#t-cur").textContent = "0:00"; $("#t-dur").textContent = fmtTime(t.duration);
}
const artistLinks = a => (a || "").split(/,\s*/).map(n => `<a href="#/artist/${encodeURIComponent(n)}" style="cursor:pointer">${esc(n)}</a>`).join(", ");
function paintQual(t) {
  const q = qualityOf(t), el = $("#p-qual");
  el.hidden = false; el.className = "badge " + q.cls; el.textContent = (t.source === "local" ? "Local · " : "Stream · ") + q.txt;
  const n = $("#np-qual"); n.className = "badge " + q.cls; n.textContent = el.textContent;
}
function markPlaying() {
  const t = curTrack();
  $$(".row").forEach(r => r.classList.toggle("playing", !!t && r.dataset.k === t.key));
}
function setPlaying(p) {
  $("#b-play").innerHTML = ic(p ? "pause" : "play");
  document.body.classList.toggle("paused", !p);
}
function syncModes() {
  $("#b-shuf").classList.toggle("on", Q.shuffle);
  $("#b-rep").classList.toggle("on", Q.repeat !== "off");
  $("#b-rep").innerHTML = ic(Q.repeat === "one" ? "repeat1" : "repeat");
}
audio.addEventListener("play", () => setPlaying(true));
audio.addEventListener("pause", () => setPlaying(false));
audio.addEventListener("ended", () => next(true));
audio.addEventListener("waiting", () => setBuffering(true));
audio.addEventListener("playing", () => setBuffering(false));
audio.addEventListener("error", () => { if (audio.src && Q.i >= 0) { toast("Couldn't play “" + (curTrack()?.title || "track") + "” — skipping", true); setTimeout(() => next(true), 900); } });
let seeking = false;
audio.addEventListener("timeupdate", () => {
  const d = curDur();
  if (!seeking && d) { const p = audio.currentTime / d * 1000; $("#seek").value = p; $("#seek").style.setProperty("--p", p / 10 + "%"); }
  $("#t-cur").textContent = fmtTime(audio.currentTime); $("#t-dur").textContent = fmtTime(d);
});
audio.addEventListener("durationchange", () => { $("#t-dur").textContent = fmtTime(curDur()); });
$("#seek").addEventListener("input", e => { seeking = true; const p = e.target.value / 10; e.target.style.setProperty("--p", p + "%"); $("#t-cur").textContent = fmtTime(curDur() * p / 100); });
$("#seek").addEventListener("change", e => { audio.currentTime = curDur() * e.target.value / 1000; seeking = false; });

function setVolume(v) {
  audio.volume = clamp(v, 0, 1);
  const el = $("#vol"); el.value = audio.volume * 100; el.style.setProperty("--p", audio.volume * 100 + "%");
  $("#b-vol").innerHTML = ic(audio.volume === 0 ? "volume0" : "volume");
}
let preMute = .8;
$("#vol").addEventListener("input", e => setVolume(e.target.value / 100));
$("#vol").addEventListener("change", e => api("/api/settings", { volume: e.target.value / 100 }).catch(() => {}));
$("#b-vol").onclick = () => { if (audio.volume > 0) { preMute = audio.volume; setVolume(0); } else setVolume(preMute || .8); };

function updateMedia(t) {
  if (!("mediaSession" in navigator)) return;
  navigator.mediaSession.metadata = new MediaMetadata({ title: t.title, artist: t.artist, album: t.album || "", artwork: t.art ? [{ src: t.art.startsWith("http") ? t.art : location.origin + t.art, sizes: "512x512" }] : [] });
  navigator.mediaSession.setActionHandler("play", () => audio.play());
  navigator.mediaSession.setActionHandler("pause", () => audio.pause());
  navigator.mediaSession.setActionHandler("previoustrack", prev);
  navigator.mediaSession.setActionHandler("nexttrack", () => next());
}

/* ============================================================ likes / playlists / downloads */
async function loadLikes() {
  const r = await api("/api/likes"); S.likes = new Map(r.tracks.map(t => [t.key, t]));
  paintLike();
}
async function toggleLike(t) {
  try {
    const r = await api("/api/like", { track: clean(t) });
    if (r.liked) S.likes.set(t.key, clean(t)); else S.likes.delete(t.key);
    paintLike(); toast(r.liked ? "Added to liked songs" : "Removed from liked songs");
    if (S.view?.name === "likes") render();
  } catch (e) { toast(e.message, true); }
}
function paintLike() {
  const t = curTrack(), b = $("#p-like");
  b.classList.toggle("on", !!t && isLiked(t)); b.disabled = !t;
  $$(".row").forEach(r => { const on = S.likes.has(r.dataset.k); $(".hb", r)?.classList.toggle("on", on); $(".ac", r)?.classList.toggle("liked", on); });
}
async function loadPlaylists() {
  S.playlists = (await api("/api/playlists")).playlists;
  $("#pls").innerHTML = S.playlists.map(p => `<a class="pl-item ${S.view?.name === "playlist" && S.view.id == p.id ? "on" : ""}" href="#/playlist/${p.id}">${mosaic(p.arts).replace('class="cv', 'class="cv').replace("<div", '<div style="border-radius:7px"')}<div><b>${esc(p.name)}</b><small>${plural(p.count, "song")}</small></div></a>`).join("") ||
    `<div style="padding:8px 12px;color:var(--dim);font-size:13px">Create your first playlist with the + above.</div>`;
}
async function newPlaylist() {
  const n = prompt("Playlist name"); if (n === null) return;
  const r = await api("/api/playlists", { name: n }); await loadPlaylists(); nav("#/playlist/" + r.id);
}

let pollTimer = null; const jobState = {};
async function download(tracks, fmt) {
  tracks = tracks.filter(t => t.source !== "local").map(clean);
  if (!tracks.length) return toast("These songs are already in your library");
  try {
    if (tracks.length === 1) await api("/api/download", { track: tracks[0], format: fmt }); else await api("/api/download/many", { tracks, format: fmt });
    toast(tracks.length === 1 ? "Download started" : `Downloading ${tracks.length} songs`); pollDownloads();
  } catch (e) { toast(e.message, true); }
}
async function pollDownloads() {
  clearTimeout(pollTimer);
  try {
    S.jobs = (await api("/api/downloads")).jobs;
    let active = 0, refresh = false;
    S.jobs.forEach(j => {
      if (!["done", "error"].includes(j.status)) active++;
      if (jobState[j.id] && jobState[j.id] !== j.status) {
        if (j.status === "done") { refresh = true; toast(`Saved “${j.title}” to your library`); }
        if (j.status === "error") toast(`Download failed: ${j.error}`, true);
      }
      jobState[j.id] = j.status;
    });
    const b = $("#dlbadge"); b.hidden = !active; b.textContent = active;
    if (refresh) loadLibrary();
    if (S.view?.name === "downloads") paintDownloads();
    if (active) pollTimer = setTimeout(pollDownloads, 1000);
  } catch { pollTimer = setTimeout(pollDownloads, 3000); }
}

/* ============================================================ queue drawer + now playing */
function renderQueue() {
  const body = $("#qd-body"); if (!body) return;
  if (Q.i < 0) { body.innerHTML = `<div class="empty" style="padding:50px 10px"><p>Your queue is empty.</p></div>`; return; }
  const row = (t, i, cur) => `<div class="qrow ${cur ? "cur" : ""}" data-qi="${i}">${cover(t.art)}<div><div class="t">${esc(t.title)}</div><div class="a">${esc(t.artist)}</div></div>${cur ? "" : `<button class="ic" data-qx="${i}" title="Remove">${ic("x")}</button>`}</div>`;
  body.innerHTML = `<div class="qlabel">Now playing</div>${row(Q.list[Q.i], Q.i, true)}` +
    (Q.list.length > Q.i + 1 ? `<div class="qlabel">Next up</div>${Q.list.slice(Q.i + 1, Q.i + 120).map((t, k) => row(t, Q.i + 1 + k, false)).join("")}` : "");
}
$("#qd-body").addEventListener("click", e => {
  const x = e.target.closest("[data-qx]");
  if (x) { Q.list.splice(+x.dataset.qx, 1); renderQueue(); return; }
  const r = e.target.closest("[data-qi]"); if (r) { Q.stack.push(Q.i); Q.i = +r.dataset.qi; loadCurrent(); renderQueue(); }
});
$("#qd-clear").onclick = () => { if (Q.i >= 0) { Q.list = Q.list.slice(0, Q.i + 1); renderQueue(); } };
const toggleQueue = f => { const d = $("#qd"); d.classList.toggle("open", f); if (d.classList.contains("open")) renderQueue(); $("#b-q").classList.toggle("on", d.classList.contains("open")); };
$("#b-q").onclick = () => toggleQueue();
$("#qd-x").onclick = () => toggleQueue(false);
function openNP() { if (Q.i < 0) return; $("#np").classList.add("open"); vizOn = true; drawViz(); }
function closeNP() { $("#np").classList.remove("open"); vizOn = false; }
$("#b-np").onclick = openNP; $("#p-art").onclick = openNP; $("#np-x").onclick = closeNP;

/* player buttons */
$("#b-play").onclick = toggle; $("#b-next").onclick = () => next(); $("#b-prev").onclick = prev;
$("#b-shuf").onclick = () => { Q.shuffle = !Q.shuffle; syncModes(); };
$("#b-rep").onclick = () => { Q.repeat = { off: "all", all: "one", one: "off" }[Q.repeat]; syncModes(); toast("Repeat: " + { off: "off", all: "all", one: "this song" }[Q.repeat]); };
$("#p-like").onclick = () => { const t = curTrack(); if (t) toggleLike(t); };
$("#b-eq").onclick = () => $("#eq").classList.contains("open") ? closeEQ() : openEQ();

/* ============================================================ view building blocks */
const main = () => $("#main");
const skeleton = n => Array.from({ length: n }, () => `<div class="skel"></div>`).join("");
const sum = ts => ts.reduce((a, t) => a + (t.duration || 0), 0);
const hero = (kind, title, sub, cv) => `<div class="hero">${cv}<div><div class="kind">${esc(kind)}</div><h1>${esc(title)}</h1><p>${esc(sub)}</p></div></div>`;
const actions = (tracks, extra = "") => `<div class="actions">
  <button class="btn pri" data-act="${reg(() => playList(tracks, 0))}">${ic("play")}Play</button>
  <button class="btn" data-act="${reg(() => playShuffled(tracks))}">${ic("shuffle")}Shuffle</button>
  ${tracks.some(t => t.source !== "local") ? `<button class="btn ghost" data-act="${reg(() => download(tracks))}">${ic("download")}Download all</button>` : ""}${extra}</div>`;
const emptyState = (title, text, cta = "", icon = "music", cls = "") => `<div class="empty">${cover(null, cls, icon)}<h3>${esc(title)}</h3><p>${text}</p>${cta ? `<div class="actions">${cta}</div>` : ""}</div>`;

const albumHref = t => "#/album/" + encodeURIComponent((t.album || "") + "\u0001" + firstArtist(t.artist));

function rowHtml(L, i) {
  const t = REG.lists[L].tracks[i], o = REG.lists[L].o, liked = isLiked(t);
  const src = t.source === "yt" ? `<span class="badge web">YT Music</span>` : t.source === "sp" ? `<span class="badge web">Spotify</span>` : badge(t);
  const album = t.album ? (t.source === "local" ? `<a href="${albumHref(t)}">${esc(t.album)}</a>` : esc(t.album)) : "";
  return `<div class="row ${curTrack() && curTrack().key === t.key ? "playing" : ""}" data-l="${L}" data-i="${i}" data-k="${esc(t.key)}">
    <div class="idx"><span class="n">${i + 1}</span><button class="pl" tabindex="-1">${ic("play")}</button><span class="bars"><s></s><s></s><s></s></span></div>
    <div class="ti">${cover(t.art)}<div><div class="t">${esc(t.title)}</div><div class="a">${artistLinks(t.artist)}</div></div></div>
    <div class="al">${album}</div><div class="ql">${src}</div><div class="du">${fmtTime(t.duration)}</div>
    <div class="ac ${liked ? "liked" : ""}"><button class="hb ${liked ? "on" : ""}" title="Like">${ic("heart")}</button><button class="mb" title="More">${ic("more")}</button></div></div>`;
}
const BATCH = 150;
function trackTable(tracks, o = {}) {
  const L = REG.lists.push({ tracks, shown: Math.min(BATCH, tracks.length), o }) - 1;
  let rows = ""; for (let i = 0; i < REG.lists[L].shown; i++) rows += rowHtml(L, i);
  return `<div class="tt"><div class="thead"><div>#</div><div>Title</div><div class="c-al">Album</div><div>Source</div><div style="text-align:right">Time</div><div></div></div>
    <div class="rows" data-l="${L}">${rows}</div>${tracks.length > BATCH ? `<div class="more" data-more="${L}"></div>` : ""}</div>`;
}
const moreObserver = new IntersectionObserver(es => es.forEach(e => {
  if (!e.isIntersecting) return;
  const L = +e.target.dataset.more, l = REG.lists[L]; if (!l) return;
  const rows = $(`.rows[data-l="${L}"]`); let h = "";
  for (let i = l.shown; i < Math.min(l.shown + BATCH, l.tracks.length); i++) h += rowHtml(L, i);
  l.shown = Math.min(l.shown + BATCH, l.tracks.length); rows.insertAdjacentHTML("beforeend", h);
  if (l.shown >= l.tracks.length) { moreObserver.unobserve(e.target); e.target.remove(); }
}), { root: null, rootMargin: "400px" });
const watchMore = () => $$(".more[data-more]").forEach(el => moreObserver.observe(el));

function trackCard(tracks, i) {
  const t = tracks[i], id = reg(() => playList(tracks, i));
  return `<div class="card" data-act="${id}">${cover(t.art)}<b>${esc(t.title)}</b><small>${esc(t.artist)}</small><button class="fab" data-act="${id}" aria-label="Play">${ic("play")}</button></div>`;
}
function mixCard(m) {
  S.mixes.push(m); const idx = S.mixes.length - 1;
  return `<div class="card" data-act="${reg(() => nav("#/mix/" + idx))}">${mosaic(m.tracks.map(t => t.art))}<b>${esc(m.title)}</b><small>${esc(m.subtitle || "")}</small><button class="fab" data-act="${reg(() => playList(m.tracks, 0))}" aria-label="Play">${ic("play")}</button></div>`;
}
const shelf = (title, sub, cards, link = "") => cards ? `<div class="sec-head"><h2 class="sec">${esc(title)}</h2>${link}</div>${sub ? `<div class="sec-sub">${esc(sub)}</div>` : ""}<div class="shelf">${cards}</div>` : "";

/* ============================================================ views */
const VIEWS = {};
S.mixes = [];

VIEWS.home = async (arg, qs, tok) => {
  main().innerHTML = `<h1 class="page">${skeleton(1)}</h1>${skeleton(4)}`;
  const h = await api("/api/home"); if (tok !== S.viewTok) return;
  S.mixes = [];
  const hr = new Date().getHours(), greet = hr < 5 ? "Still up?" : hr < 12 ? "Good morning" : hr < 18 ? "Good afternoon" : "Good evening";
  let html = `<h1 class="page">${greet}</h1><div class="sub">${h.counts.tracks ? `${plural(h.counts.tracks, "song")} in your library` : "Search for anything — Aura checks your library first, then the web"}</div>`;
  if (!h.counts.tracks && !h.recent.length) {
    html += emptyState("Start with some music", "Add a folder to build your local library, or search to stream anything instantly — no ads.",
      `<button class="btn pri" data-act="${reg(addFolderFlow)}">${ic("folder")}Add music folder</button><button class="btn" data-act="${reg(() => $("#q").focus())}">${ic("search")}Search online</button>`, "music");
  }
  if (h.recent.length) {
    html += `<div class="greet">${h.recent.slice(0, 6).map((t, i) => { const id = reg(() => playList(h.recent, i)); return `<div class="tile" data-act="${id}">${cover(t.art)}<b>${esc(t.title)}</b><button class="fab" data-act="${id}">${ic("play")}</button></div>`; }).join("")}</div>`;
    html += shelf("Jump back in", "", h.recent.map((_, i) => trackCard(h.recent, i)).join(""));
  }
  html += shelf("Made from your library", "Mixes generated from what's on your drive", h.mixes.map(mixCard).join(""));
  html += shelf("Recently added", "", h.added.map((_, i) => trackCard(h.added, i)).join(""), `<a class="link" href="#/library/songs">Show all</a>`);
  html += shelf("Rediscover", "Songs you haven't played yet", h.unheard.map((_, i) => trackCard(h.unheard, i)).join(""));
  html += `<div id="recs"></div>`;
  main().innerHTML = html; watchMore();
  // online recommendations load after the local shelves are already on screen
  const box = $("#recs"); box.innerHTML = `<h2 class="sec">Recommended for you</h2><div class="note"><span class="spin"></span>Finding songs similar to what you play…</div>`;
  try {
    const r = await api("/api/recs"); if (tok !== S.viewTok) return;
    if (!r.mixes.length) box.innerHTML = r.reason ? `<h2 class="sec">Recommended for you</h2><div class="note">${esc(r.reason)}</div>` : "";
    else box.innerHTML = `<h2 class="sec">Recommended for you</h2><div class="sec-sub">Based on your listening and liked songs</div><div class="shelf">${r.mixes.map(mixCard).join("")}</div>`;
  } catch (e) { if (tok === S.viewTok) box.innerHTML = ""; }
};

VIEWS.mix = async (arg, qs, tok) => {
  const m = S.mixes[+arg]; if (!m) return nav("#/home");
  main().innerHTML = hero("Mix", m.title, `${m.subtitle || ""} · ${plural(m.tracks.length, "song")}`, mosaic(m.tracks.map(t => t.art))) + actions(m.tracks) + trackTable(m.tracks); watchMore();
};

/* ---------- search: local first, then online ---------- */
VIEWS.search = async (arg, qs, tok) => {
  const text = (qs.get("q") || "").trim();
  if ($("#q").value !== text && document.activeElement !== $("#q")) $("#q").value = text;
  if (!text) { main().innerHTML = emptyState("Search everything", "Type a song, artist or album. Aura looks in your library first and only goes online if it needs to.", "", "search"); return; }
  main().innerHTML = `<h1 class="page">Results for “${esc(text)}”</h1>${skeleton(4)}`;
  let local;
  try { local = (await api("/api/search?" + new URLSearchParams({ q: text, scope: "local" }))).local; } catch (e) { local = []; }
  if (tok !== S.viewTok) return;
  const auto = !local.length || local.length < 3 || S.settings.always_online;
  let html = `<h1 class="page">Results for “${esc(text)}”</h1>`;
  html += `<h2 class="sec" style="margin-top:14px">In your library</h2>`;
  html += local.length ? trackTable(local) : `<div class="note">${ic("folder")}Nothing in your library matches${auto ? " — searching online" : ""}.</div>`;
  html += `<div id="online">${auto ? "" : `<div class="actions"><button class="btn" data-act="${reg(() => loadOnline(text, local, tok))}">${ic("search")}Search online for “${esc(text)}”</button></div>`}</div>`;
  main().innerHTML = html; watchMore();
  if (auto) loadOnline(text, local, tok);
};
async function loadOnline(text, local, tok) {
  const box = $("#online"); if (!box) return;
  box.innerHTML = `<h2 class="sec">From the web</h2><div class="note"><span class="spin"></span>Searching YouTube Music${S.caps.spotify ? " and Spotify" : ""}…</div>`;
  let r;
  try { r = await api("/api/search?" + new URLSearchParams({ q: text, scope: "online" })); }
  catch (e) { if (tok === S.viewTok) box.innerHTML = `<h2 class="sec">From the web</h2><div class="note err">Couldn't reach online providers: ${esc(e.message)}</div>`; return; }
  if (tok !== S.viewTok) return;
  const have = new Set(local.map(t => normStr(t.title) + "|" + normStr(firstArtist(t.artist))));
  const dedupe = ts => ts.filter(t => !have.has(normStr(t.title) + "|" + normStr(firstArtist(t.artist))));
  const yt = dedupe(r.yt), sp = dedupe(r.sp);
  let html = "";
  if (yt.length) html += `<h2 class="sec">From YouTube Music</h2><div class="sec-sub">Plays instantly, ad-free · use ⋯ to download</div>` + trackTable(yt);
  if (sp.length) html += `<h2 class="sec">From Spotify</h2><div class="sec-sub">Catalog match — audio is streamed from YouTube Music</div>` + trackTable(sp);
  if (!yt.length && !sp.length) html += `<h2 class="sec">From the web</h2><div class="note">No online results${r.errors.length ? "" : " for this search"}.</div>`;
  r.errors.forEach(e => { html += `<div class="note err">${esc(e)}</div>`; });
  box.innerHTML = html; watchMore();
}

/* ---------- library ---------- */
function group(tracks, keyFn) { const m = new Map(); tracks.forEach(t => { const k = keyFn(t); if (!m.has(k)) m.set(k, []); m.get(k).push(t); }); return m; }
VIEWS.library = async (arg, qs, tok) => {
  const tab = arg || "songs", f = S.libFilter || "";
  if (!S.lib.length) { main().innerHTML = `<h1 class="page">Your library</h1>` + emptyState("Your library is empty", "Add a folder with your music — MP3, FLAC, WAV, M4A, OGG, OPUS and more are supported.", `<button class="btn pri" data-act="${reg(addFolderFlow)}">${ic("folder")}Add music folder</button>`, "folder"); return; }
  main().innerHTML = `<h1 class="page">Your library</h1><div class="tabs">${["songs", "albums", "artists"].map(t => `<a class="chip ${t === tab ? "on" : ""}" href="#/library/${t}">${t[0].toUpperCase() + t.slice(1)}</a>`).join("")}
    <label class="filter">${ic("search")}<input id="lf" placeholder="Filter" value="${esc(f)}" autocomplete="off"></label></div><div id="lib-body"></div>`;
  $("#lf").addEventListener("input", debounce(e => { S.libFilter = e.target.value; paintLib(tab); }, 150));
  paintLib(tab);
};
function paintLib(tab) {
  const nf = normStr(S.libFilter || "");
  const tracks = nf ? S.lib.filter(t => normStr(`${t.title} ${t.artist} ${t.album}`).includes(nf)) : S.lib;
  REG.lists = []; REG.acts = [];
  let h = "";
  if (tab === "songs") h = actions(tracks) + trackTable(tracks);
  else if (tab === "albums") {
    const g = [...group(tracks, t => (t.album || "") + "\u0001" + firstArtist(t.artist))];
    h = `<div class="grid">${g.map(([k, ts]) => `<div class="card" data-act="${reg(() => nav("#/album/" + encodeURIComponent(k)))}">${cover(ts[0].art, "", "disc")}<b>${esc(ts[0].album)}</b><small>${esc(firstArtist(ts[0].artist))}</small><button class="fab" data-act="${reg(() => playList(ts, 0))}">${ic("play")}</button></div>`).join("")}</div>`;
  } else {
    const g = [...group(tracks, t => firstArtist(t.artist))].sort((a, b) => a[0].localeCompare(b[0]));
    h = `<div class="grid">${g.map(([k, ts]) => `<div class="card round" data-act="${reg(() => nav("#/artist/" + encodeURIComponent(k)))}">${cover(ts.find(t => t.art)?.art, "", "user")}<b>${esc(k)}</b><small>${plural(ts.length, "song")}</small><button class="fab" data-act="${reg(() => playList(ts, 0))}">${ic("play")}</button></div>`).join("")}</div>`;
  }
  $("#lib-body").innerHTML = tracks.length ? h : `<div class="note">No matches in your library.</div>`;
  watchMore();
}
VIEWS.album = async (arg, qs, tok) => {
  const [album, artist] = arg.split("\u0001");
  const ts = S.lib.filter(t => t.album === album && firstArtist(t.artist) === artist).sort((a, b) => (a.no || 0) - (b.no || 0));
  if (!ts.length) return nav("#/library/albums");
  main().innerHTML = hero("Album", album, `${artist} · ${ts[0].year ? ts[0].year + " · " : ""}${plural(ts.length, "song")}, ${fmtTotal(sum(ts))}`, cover(ts[0].art, "", "disc")) + actions(ts) + trackTable(ts);
};
VIEWS.artist = async (arg, qs, tok) => {
  const ts = S.lib.filter(t => (t.artist || "").split(/,\s*/).includes(arg) || firstArtist(t.artist) === arg);
  if (!ts.length) return nav("#/search?q=" + encodeURIComponent(arg));
  const albums = [...group(ts, t => (t.album || "") + "\u0001" + firstArtist(t.artist))];
  main().innerHTML = hero("Artist", arg, `${plural(ts.length, "song")} in your library`, cover(ts.find(t => t.art)?.art, "", "user").replace('class="cv', 'class="cv" style="border-radius:50%" data-x="')) +
    actions(ts, `<button class="btn ghost" data-act="${reg(() => nav("#/search?q=" + encodeURIComponent(arg)))}">${ic("search")}Find more online</button>`) +
    `<h2 class="sec">Albums</h2><div class="shelf">${albums.map(([k, a]) => `<div class="card" data-act="${reg(() => nav("#/album/" + encodeURIComponent(k)))}">${cover(a[0].art, "", "disc")}<b>${esc(a[0].album)}</b><small>${plural(a.length, "song")}</small></div>`).join("")}</div>
    <h2 class="sec">Songs</h2>` + trackTable(ts); watchMore();
};

VIEWS.likes = async () => {
  const ts = [...S.likes.values()];
  if (!ts.length) { main().innerHTML = hero("Playlist", "Liked songs", "Songs you heart show up here", `<div class="cv heart">${ic("heart")}</div>`) + emptyState("Nothing liked yet", "Tap the heart on any song, local or online.", "", "heart"); return; }
  main().innerHTML = hero("Playlist", "Liked songs", `${plural(ts.length, "song")}, ${fmtTotal(sum(ts))}`, `<div class="cv heart">${ic("heart")}</div>`) + actions(ts) + trackTable(ts); watchMore();
};

VIEWS.playlist = async (arg, qs, tok) => {
  let p; try { p = await api("/api/playlists/" + arg); } catch { return nav("#/home"); }
  if (tok !== S.viewTok) return;
  const ts = p.tracks;
  const extra = `<button class="btn ghost" data-act="${reg(async () => { const n = prompt("Rename playlist", p.name); if (n) { await api(`/api/playlists/${p.id}/rename`, { name: n }); loadPlaylists(); render(); } })}">${ic("edit")}Rename</button>
    <button class="btn ghost danger" data-act="${reg(async () => { if (confirm(`Delete “${p.name}”?`)) { await api(`/api/playlists/${p.id}/delete`, {}); await loadPlaylists(); nav("#/home"); } })}">${ic("trash")}Delete</button>`;
  main().innerHTML = hero("Playlist", p.name, ts.length ? `${plural(ts.length, "song")}, ${fmtTotal(sum(ts))}` : "Empty", mosaic(ts.map(t => t.art))) +
    (ts.length ? actions(ts, extra) + trackTable(ts, { playlistId: p.id }) : `<div class="actions">${extra}</div>` + emptyState("This playlist is empty", "Use ⋯ on any song and choose “Add to playlist”.", "", "music"));
  watchMore(); loadPlaylists();
};

VIEWS.downloads = async () => { await pollDownloads(); paintDownloads(); };
function paintDownloads() {
  if (S.view?.name !== "downloads") return;
  const dir = S.settings.download_dir;
  const open = `<button class="btn ghost" data-act="${reg(() => openPath(dir))}">${ic("folder")}Open downloads folder</button>`;
  main().innerHTML = `<h1 class="page">Downloads</h1><div class="sub">Saved to ${esc(dir)} and added to your library automatically</div>` +
    (S.jobs.length ? `<div class="actions">${open}</div>` + S.jobs.map(j => `<div class="dl ${j.status}">${cover(j.art)}<div><div class="t">${esc(j.title)}</div><div class="a">${esc(j.artist)}</div></div>
      <div><div class="prog"><i style="width:${j.progress}%"></i></div><div class="st">${j.status === "done" ? "Saved to library" : j.status === "error" ? esc(j.error) : esc(j.status[0].toUpperCase() + j.status.slice(1)) + (j.progress ? " · " + j.progress + "%" : "")}${j.note ? " · " + esc(j.note) : ""}</div></div>
      <div>${j.status === "done" ? `<span class="ok">${ic("check")}</span>` : ""}</div></div>`).join("")
      : emptyState("No downloads yet", "Search for a song online, then use ⋯ → Download to keep it offline in your library.", "", "download"));
}
function openPath(p) { try { window.pywebview.api.open_path(p); } catch { toast("Open this folder manually: " + p); } }

/* ---------- settings ---------- */
const SWATCHES = ["#ffb547", "#ff7a9c", "#5ee0c8", "#8f9bff", "#c4e86b", "#ff7a45"];
const seg = (k, opts, cur) => `<div class="seg" data-seg="${k}">${opts.map(([v, l]) => `<button data-v="${v}" class="${String(cur) === String(v) ? "on" : ""}">${l}</button>`).join("")}</div>`;
const sw = (k, on) => `<label class="switch"><input type="checkbox" data-set="${k}" ${on ? "checked" : ""}><span></span></label>`;
VIEWS.settings = async (arg, qs, tok) => {
  const s = S.settings, c = S.caps, folders = (await api("/api/folders")).folders; if (tok !== S.viewTok) return;
  const st = (ok, l) => `<b>${l}</b><span class="${ok ? "ok" : "no"}">${ok ? "Installed" : "Missing"}</span>`;
  main().innerHTML = `<h1 class="page">Settings</h1>
  <div class="set"><h3>Music library</h3><p>Aura searches these folders first, before going online.</p>
    ${folders.map(f => `<div class="folder">${ic("folder")}<span>${esc(f)}</span><button class="btn ghost" data-act="${reg(async () => { await api("/api/folders/remove", { path: f }); await loadLibrary(); render(); })}">Remove</button></div>`).join("") || `<div class="folder" style="color:var(--dim)">No folders yet</div>`}
    <div class="actions"><button class="btn pri" data-act="${reg(addFolderFlow)}">${ic("plus")}Add folder</button><button class="btn" data-act="${reg(async () => { await api("/api/library/scan", {}); pollScan(); })}">${ic("refresh")}Rescan</button></div></div>
  <div class="set"><h3>Playback</h3><p>Streams are fetched as direct audio, so there are no ads.</p>
    <div class="line"><div><b>Streaming quality</b><small>Max picks the best audio stream available</small></div>${seg("stream_quality", [["low", "Low"], ["normal", "Normal"], ["high", "High"], ["max", "Max"]], s.stream_quality)}</div>
    <div class="line"><div><b>Prefer AAC (m4a) streams</b><small>Better compatibility on macOS; Opus is usually higher quality elsewhere</small></div>${sw("prefer_aac", s.prefer_aac)}</div>
    <div class="line"><div><b>Always search online too</b><small>Otherwise Aura only goes online when your library has fewer than 3 matches</small></div>${sw("always_online", s.always_online)}</div>
    <div class="line"><div><b>Autoplay similar songs</b><small>Keep playing related tracks when the queue ends</small></div>${sw("autoplay_similar", s.autoplay_similar)}</div>
    <div class="line"><div><b>High-resolution audio engine</b><small>Processing sample rate. Restart Aura after changing. Final output depends on your device's settings.</small></div>
      <select class="field" data-set="output_rate">${[[0, "Device default"], [44100, "44.1 kHz"], [48000, "48 kHz"], [88200, "88.2 kHz"], [96000, "96 kHz"], [192000, "192 kHz"]].map(([v, l]) => `<option value="${v}" ${+s.output_rate === v ? "selected" : ""}>${l}</option>`).join("")}</select></div>
    <div class="line"><div><b>Equalizer</b><small>Basic and advanced modes, presets and effects</small></div><button class="btn" data-act="${reg(openEQ)}">${ic("sliders")}Open equalizer</button></div></div>
  <div class="set"><h3>YouTube access</h3><p>If songs fail with “Sign in to confirm you're not a bot”, choose the browser where you're signed in to YouTube. Aura only reads its cookies locally to unlock streams. Close that browser if you get a cookie error.</p>
    <div class="line"><div><b>Use login from</b></div><select class="field" data-set="cookies_browser">${[["", "None"], ["chrome", "Chrome"], ["edge", "Edge"], ["firefox", "Firefox"], ["brave", "Brave"], ["opera", "Opera"]].map(([v, l]) => `<option value="${v}" ${s.cookies_browser === v ? "selected" : ""}>${l}</option>`).join("")}</select></div>
    <div class="line"><div><b>Or cookies.txt file</b><small>Path to an exported cookies file (optional)</small></div><input class="field" data-set="cookies_file" value="${esc(s.cookies_file)}" style="min-width:320px"></div></div>
  <div class="set"><h3>Downloads</h3><p>Downloaded songs are saved in your library with tags and artwork${c.ffmpeg ? "" : " (install ffmpeg for MP3 conversion and embedded artwork)"}.</p>
    <div class="line"><div><b>Default format</b></div>${seg("download_format", [["original", "Original"], ["mp3_320", "MP3 320"], ["mp3_192", "MP3 192"]], s.download_format)}</div>
    <div class="line"><div><b>Save to</b></div><input class="field" data-set="download_dir" value="${esc(s.download_dir)}" style="min-width:320px"><button class="btn ghost" data-act="${reg(async () => { try { const p = await window.pywebview.api.pick_folder(); if (p) { S.settings = await api("/api/settings", { download_dir: p }); render(); } } catch { toast("Type the path into the box instead"); } })}">Browse</button></div></div>
  <div class="set"><h3>Spotify (optional)</h3><p>Add a free Spotify developer app's credentials to include Spotify's catalog in search. Audio is always matched and streamed from YouTube Music, because Spotify's own streams are DRM-protected.</p>
    <div class="line"><div><b>Client ID</b></div><input class="field" data-set="spotify_id" value="${esc(s.spotify_id)}" autocomplete="off"></div>
    <div class="line"><div><b>Client secret</b></div><input class="field" type="password" data-set="spotify_secret" value="${esc(s.spotify_secret)}" autocomplete="off"></div></div>
  <div class="set"><h3>Appearance</h3><div class="line"><div><b>Accent colour</b></div><div class="swatches">${SWATCHES.map(a => `<button class="sw ${a === s.accent ? "on" : ""}" data-sw="${a}" style="background:${a}" aria-label="${a}"></button>`).join("")}</div></div></div>
  <div class="set"><h3>Status</h3><div class="dots">${st(c.yt_dlp, "yt-dlp (streaming and downloads)")}${st(c.ytmusicapi, "ytmusicapi (online search)")}${st(c.mutagen, "mutagen (tags and artwork)")}${st(c.ffmpeg, "ffmpeg (MP3 conversion, optional)")}</div></div>`;
};
document.addEventListener("change", async e => {
  const k = e.target.dataset?.set; if (!k) return;
  let v = e.target.type === "checkbox" ? e.target.checked : e.target.value;
  if (k === "output_rate") v = +v;
  try { S.settings = await api("/api/settings", { [k]: v }); S.caps = await api("/api/caps"); toast("Saved"); } catch (er) { toast(er.message, true); }
});
document.addEventListener("click", async e => {
  const sg = e.target.closest("[data-seg] button");
  if (sg) { const k = sg.parentElement.dataset.seg; S.settings = await api("/api/settings", { [k]: sg.dataset.v }); $$("button", sg.parentElement).forEach(b => b.classList.toggle("on", b === sg)); toast("Saved"); return; }
  const w = e.target.closest("[data-sw]");
  if (w) { S.settings = await api("/api/settings", { accent: w.dataset.sw }); applyAccent(w.dataset.sw); $$(".sw").forEach(b => b.classList.toggle("on", b === w)); }
});
function applyAccent(c) {
  const r = document.documentElement.style; r.setProperty("--accent", c);
  const [R, G, B] = [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16));
  r.setProperty("--accent-ink", (.299 * R + .587 * G + .114 * B) / 255 > .55 ? "#1d1300" : "#ffffff");
}

/* ============================================================ router + global events */
let lastHash = null;
function nav(h) { if (location.hash === h) render(); else location.hash = h; }
async function render() {
  const h = location.hash || "#/home", [path, qs] = h.slice(2).split("?"), parts = path.split("/");
  const name = VIEWS[parts[0]] ? parts[0] : "home", arg = decodeURIComponent(parts.slice(1).join("/") || "");
  S.view = { name, arg, id: arg }; const tok = ++S.viewTok;
  const keep = lastHash === h ? main().scrollTop : 0; lastHash = h;
  REG.lists = []; REG.acts = [];
  $$("#nav a, .side-foot").forEach(a => a.classList.toggle("on", a.dataset.nav === name));
  $$(".pl-item").forEach(a => a.classList.toggle("on", name === "playlist" && a.getAttribute("href") === "#/playlist/" + arg));
  try { await VIEWS[name](arg, new URLSearchParams(qs || ""), tok); }
  catch (e) { if (tok === S.viewTok) main().innerHTML = `<div class="note err" style="margin-top:20px">Something went wrong: ${esc(e.message)}</div>`; }
  if (tok === S.viewTok) { main().scrollTop = keep; hydrate(main()); markPlaying(); }
}
window.addEventListener("hashchange", render);
$("#back").onclick = () => history.back(); $("#fwd").onclick = () => history.forward();
$("#newpl").onclick = newPlaylist;

// search box
const doSearch = () => {
  const text = $("#q").value.trim(), h = "#/search" + (text ? "?q=" + encodeURIComponent(text) : "");
  if (location.hash.startsWith("#/search")) { history.replaceState(null, "", h); render(); } else nav(h);
};
$("#q").addEventListener("input", debounce(doSearch, 320));
$("#q").addEventListener("keydown", e => { if (e.key === "Enter") doSearch(); if (e.key === "Escape") { e.target.value = ""; e.target.blur(); } });
$("#q").addEventListener("focus", () => { if (!location.hash.startsWith("#/search")) nav("#/search"); });

// delegated clicks for cards, rows
const rowInfo = row => ({ L: +row.dataset.l, i: +row.dataset.i });
const rowTrack = row => { const { L, i } = rowInfo(row); return REG.lists[L].tracks[i]; };
const playRow = row => { const { L, i } = rowInfo(row); playList(REG.lists[L].tracks, i); };
document.addEventListener("click", e => {
  const a = e.target.closest("[data-act]");
  if (a && REG.acts[+a.dataset.act]) { REG.acts[+a.dataset.act](e); return; }
  const row = e.target.closest(".row"); if (!row) return;
  if (e.target.closest(".pl")) return playRow(row);
  if (e.target.closest(".hb")) return toggleLike(rowTrack(row));
  const mb = e.target.closest(".mb");
  if (mb) { const r = mb.getBoundingClientRect(); return trackMenu(rowTrack(row), r.left - 190, r.bottom + 4, REG.lists[rowInfo(row).L].o); }
  if (e.target.closest("a")) return;
  $$(".row.sel").forEach(r => r.classList.remove("sel")); row.classList.add("sel");
});
document.addEventListener("dblclick", e => { const row = e.target.closest(".row"); if (row && !e.target.closest(".ac,a")) playRow(row); });
document.addEventListener("contextmenu", e => { const row = e.target.closest(".row"); if (row) { e.preventDefault(); trackMenu(rowTrack(row), e.clientX, e.clientY, REG.lists[rowInfo(row).L].o); } });

// keyboard
document.addEventListener("keydown", e => {
  const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName) && document.activeElement.type !== "range";
  if (e.key === "Escape") { closeMenu(); closeEQ(); closeNP(); toggleQueue(false); return; }
  if (typing) return;
  if (e.key === " ") { e.preventDefault(); toggle(); }
  else if (e.key === "/") { e.preventDefault(); $("#q").focus(); }
  else if (e.key === "ArrowRight") e.shiftKey ? next() : (audio.currentTime += 5);
  else if (e.key === "ArrowLeft") e.shiftKey ? prev() : (audio.currentTime -= 5);
  else if (e.key === "ArrowUp") { e.preventDefault(); setVolume(audio.volume + .05); }
  else if (e.key === "ArrowDown") { e.preventDefault(); setVolume(audio.volume - .05); }
  else if (e.key.toLowerCase() === "e") $("#b-eq").click();
  else if (e.key.toLowerCase() === "q") $("#b-q").click();
  else if (e.key.toLowerCase() === "m") $("#b-vol").click();
  else if (e.key.toLowerCase() === "l" && curTrack()) toggleLike(curTrack());
});

/* ============================================================ library + folders */
async function loadLibrary() { S.lib = (await api("/api/library")).tracks; }
async function addFolderFlow() {
  let p = null;
  try { p = window.pywebview?.api?.pick_folder ? await window.pywebview.api.pick_folder() : prompt("Full path to your music folder"); } catch { }
  if (!p) return;
  try { await api("/api/folders", { path: p }); toast("Scanning your music…"); pollScan(); } catch (e) { toast(e.message, true); }
}
async function pollScan() {
  const pill = $("#scan-pill");
  try {
    const s = await api("/api/library/status");
    if (s.running) { pill.hidden = false; pill.textContent = `Scanning ${s.scanned.toLocaleString()} of ${s.total.toLocaleString()}`; setTimeout(pollScan, 700); return; }
    pill.hidden = true; await loadLibrary();
    if (s.done && s.added) toast(`Library updated · ${plural(s.added, "new song")}`);
    if (["home", "library", "settings"].includes(S.view?.name)) render();
  } catch { pill.hidden = true; }
}

/* ============================================================ boot */
(async function boot() {
  hydrate(); setPlaying(false);
  try {
    [S.settings, S.caps] = await Promise.all([api("/api/settings"), api("/api/caps")]);
    applyAccent(S.settings.accent || "#ffb547");
    S.eq = Object.assign(eqDefault(), S.settings.eq || {});
    S.eq.bands = (S.eq.bands || []).concat(Array(10).fill(0)).slice(0, 10);
    bindEQ(); setVolume(S.settings.volume ?? .85); syncModes();
    await Promise.all([loadLibrary(), loadLikes(), loadPlaylists()]);
  } catch (e) { toast("Couldn't reach the Aura backend: " + e.message, true); }
  pollDownloads(); render();
  api("/api/library/scan", {}).then(pollScan).catch(() => {});   // pick up new files on every launch
})();
