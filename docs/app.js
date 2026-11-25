/* Dashboard Seroja 2021 – semua angka dibaca dari data/derived/*.json */
const REPO = "fkhadami/seroja-2021-dashboard";
const BASES = ["../data/derived/", `https://raw.githubusercontent.com/${REPO}/main/data/derived/`];
const D = {};               // cache JSON
async function load(name, optional = true) {
  if (name in D) return D[name];
  for (const b of BASES) {
    try { const r = await fetch(b + name, {cache: "no-cache"}); if (r.ok) { D[name] = await r.json(); return D[name]; } } catch (e) {}
  }
  D[name] = null; if (!optional) console.warn("gagal memuat", name); return null;
}
const $ = s => document.querySelector(s);
const el = (t, a = {}, h = "") => { const e = document.createElement(t); Object.assign(e, a); if (h) e.innerHTML = h; return e; };
function pick(obj, path) { return path.split(".").reduce((o, k) => (o == null ? undefined : o[k]), obj); }
function fmt(v, d = 1) {
  if (v === null || v === undefined || (typeof v === "number" && !isFinite(v))) return "–";
  if (typeof v !== "number") return String(v);
  return v.toLocaleString("id-ID", {minimumFractionDigits: d, maximumFractionDigits: d});
}
/* templat: {calc.sst.cooling_max_C:1} | {abs:calc.x:1} | {neg:..} */
function tpl(s, ctx) {
  return s.replace(/\{([a-z]+:)?([\w.]+)(?::(\d))?\}/gi, (m, op, p, d) => {
    let v = pick(ctx, p);
    if (op === "abs:" && typeof v === "number") v = Math.abs(v);
    if (op === "neg:" && typeof v === "number") v = -v;
    if (op === "date:" && v) return new Date(v.replace(" ", "T")).toLocaleDateString("id-ID", {day: "numeric", month: "long"});
    if (op === "pct:" && typeof v === "number") return fmt(v * 100, d ? +d : 0) + "%";
    return fmt(v, d === undefined ? 1 : +d);
  });
}

/* ---------- tab ---------- */
document.querySelectorAll("#tabs button").forEach(b => b.onclick = () => showTab(b.dataset.p));
function showTab(p) {
  document.querySelectorAll("#tabs button").forEach(x => x.classList.toggle("on", x.dataset.p === p));
  document.querySelectorAll(".panel").forEach(x => x.classList.toggle("on", x.id === p));
  if (p === "peta" && MAP) setTimeout(() => MAP.invalidateSize(), 50);
  if (p === "stasiun" && MAP2) setTimeout(() => MAP2.invalidateSize(), 50);
  window.dispatchEvent(new Event("resize"));
  history.replaceState(null, "", "#" + p);
}

/* ---------- peta warna ---------- */
const CM = {
  rdbu: ["#053061", "#2166ac", "#4393c3", "#92c5de", "#d1e5f0", "#f7f7f7", "#fddbc7", "#f4a582", "#d6604d", "#b2182b", "#67001f"],
  blues_r: ["#08306b", "#08519c", "#2171b5", "#4292c6", "#6baed6", "#9ecae1", "#c6dbef", "#eff3ff"],
  thermal: ["#042333", "#2c3395", "#744992", "#b15f82", "#eb7958", "#fbb43d", "#e8fa5b"],
  algae: ["#d7f9d0", "#a2d595", "#64b463", "#129450", "#126e45", "#1a482f", "#122414"],
  viridis: ["#440154", "#414487", "#2a788e", "#22a884", "#7ad151", "#fde725"],
  purple: ["#fcfbfd", "#dadaeb", "#9e9ac8", "#6a51a3", "#3f007d"],
};
function hex2rgb(h) { return [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16)); }
function cmap(name) {
  const st = CM[name].map(hex2rgb), n = st.length - 1;
  return t => { if (!isFinite(t)) return null; t = Math.max(0, Math.min(1, t)); const i = Math.min(Math.floor(t * n), n - 1), f = t * n - i;
    return st[i].map((c, k) => Math.round(c + f * (st[i + 1][k] - c))); };
}
function gridImage(lon, lat, Z, vmin, vmax, name) {
  const nx = lon.length, ny = lat.length, cv = document.createElement("canvas"); cv.width = nx; cv.height = ny;
  const ctx = cv.getContext("2d"), im = ctx.createImageData(nx, ny), f = cmap(name), asc = lat[1] > lat[0];
  for (let j = 0; j < ny; j++) { const row = Z[asc ? ny - 1 - j : j]; if (!row) continue;
    for (let i = 0; i < nx; i++) { const v = row[i], c = v == null ? null : f((v - vmin) / (vmax - vmin)), o = 4 * (j * nx + i);
      if (c) { im.data[o] = c[0]; im.data[o + 1] = c[1]; im.data[o + 2] = c[2]; im.data[o + 3] = 215; } } }
  ctx.putImageData(im, 0, 0);
  const dx = (lon[1] - lon[0]) / 2, dy = Math.abs(lat[1] - lat[0]) / 2;
  return {url: cv.toDataURL(), bounds: [[Math.min(...lat) - dy, lon[0] - dx], [Math.max(...lat) + dy, lon[nx - 1] + dx]]};
}

/* ---------- graticule bujur–lintang ---------- */
function graticule(map, step = 2) {
  const g = L.layerGroup().addTo(map);
  function draw() {
    g.clearLayers(); const b = map.getBounds();
    const s = map.getZoom() >= 8 ? 0.5 : map.getZoom() >= 7 ? 1 : step;
    for (let x = Math.ceil(b.getWest() / s) * s; x <= b.getEast(); x += s) {
      g.addLayer(L.polyline([[b.getSouth(), x], [b.getNorth(), x]], {color: "#555", weight: .6, opacity: .5, dashArray: "3 4", interactive: false}));
      g.addLayer(L.marker([b.getSouth(), x], {icon: L.divIcon({className: "", html: `<span class="ll-label">${fmt(x, s < 1 ? 1 : 0)}° BT</span>`, iconAnchor: [18, 18]}), interactive: false}));
    }
    for (let y = Math.ceil(b.getSouth() / s) * s; y <= b.getNorth(); y += s) {
      g.addLayer(L.polyline([[y, b.getWest()], [y, b.getEast()]], {color: "#555", weight: .6, opacity: .5, dashArray: "3 4", interactive: false}));
      g.addLayer(L.marker([y, b.getWest()], {icon: L.divIcon({className: "", html: `<span class="ll-label">${fmt(Math.abs(y), s < 1 ? 1 : 0)}° LS</span>`, iconAnchor: [-2, 8]}), interactive: false}));
    }
  }
  map.on("moveend zoomend", draw); draw();
}
function basemap(map) {
  L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}",
    {attribution: "Basemap © Esri, GEBCO, NOAA", maxZoom: 10}).addTo(map);
  L.control.scale({imperial: false}).addTo(map);
}

/* ---------- lapisan ---------- */
const LAYERS = [
  {id: "anom", file: "map_sst.json", key: "anom", lab: "Anomali SST harian (MUR)", unit: "°C, relatif 25–31 Mar", vmin: -3, vmax: 3, cm: "rdbu", t: true},
  {id: "sst", file: "map_sst.json", key: "sst", lab: "SST harian (MUR)", unit: "°C", vmin: 26, vmax: 31, cm: "thermal", t: true},
  {id: "dmin", file: "map_coldwake.json", key: "dmin", lab: "Cold wake: pendinginan maksimum 3–25 Apr", unit: "°C", vmin: -4, vmax: 0, cm: "blues_r", t: false},
  {id: "tmin", file: "map_coldwake.json", key: "tmin_day_after_apr1", lab: "Tanggal SST terdingin (hari setelah 1 Apr)", unit: "hari", vmin: 0, vmax: 20, cm: "viridis", t: false},
  {id: "chl", file: "map_chl.json", key: "log10chl", lab: "Klorofil-a VIIRS (komposit 3 hari)", unit: "log₁₀ mg m⁻³", vmin: -1.5, vmax: 0.5, cm: "algae", t: true},
  {id: "U10", file: "map_era5.json", key: "U10", lab: "Kecepatan angin 10 m (ERA5, 6-jam)", unit: "m/s", vmin: 0, vmax: 25, cm: "purple", t: true, arrows: true},
  {id: "curl", file: "map_era5.json", key: "curl", lab: "Curl tegangan angin (ERA5)", unit: "10⁻⁶ N m⁻³", vmin: -40, vmax: 40, cm: "rdbu", t: true},
  {id: "wE", file: "map_era5.json", key: "wE", lab: "Kecepatan Ekman pumping w_E (+ = naik)", unit: "m/hari", vmin: -60, vmax: 60, cm: "rdbu", t: true},
  {id: "msl", file: "map_era5.json", key: "msl", lab: "Tekanan muka laut (ERA5)", unit: "hPa", vmin: 990, vmax: 1012, cm: "viridis", t: true},
  {id: "eta", file: "map_eta.json", key: "eta", lab: "Perpindahan termoklin kumulatif η = ∫w_E dt (1–12 Apr)", unit: "m (+ = naik)", vmin: -40, vmax: 40, cm: "rdbu", t: false},
  {id: "sla", file: "map_sla.json", key: "sla", lab: "Anomali muka laut altimetri (DUACS)", unit: "cm", vmin: -15, vmax: 15, cm: "rdbu", t: true},
  {id: "mld", file: "map_glorys.json", key: "mld", lab: "Kedalaman lapisan campuran (GLORYS12)", unit: "m", vmin: 10, vmax: 80, cm: "viridis", t: true},
];
let MAP, MAP2, OVER, ARROWS, TRACK, TRACKPOS, PTS, CUR = {layer: null, data: null, ti: 0}, PLAY;

function legend(map) {
  const c = L.control({position: "bottomright"});
  c.onAdd = () => (c.div = el("div", {className: "legend"}));
  c.update = (Ly) => {
    const cv = el("canvas"); cv.width = 180; cv.height = 10; const x = cv.getContext("2d"), f = cmap(Ly.cm);
    for (let i = 0; i < 180; i++) { const k = f(i / 179); x.fillStyle = `rgb(${k})`; x.fillRect(i, 0, 1, 10); }
    c.div.innerHTML = `<b>${Ly.lab}</b><br><span>${Ly.unit}</span>`; c.div.appendChild(cv);
    c.div.appendChild(el("div", {className: "ticks"}, `<span>${fmt(Ly.vmin, 0)}</span><span>${fmt((Ly.vmin + Ly.vmax) / 2, 1)}</span><span>${fmt(Ly.vmax, 0)}</span>`));
  };
  c.addTo(map); return c;
}
let LEG;
async function setLayer(id, ti = null) {
  const Ly = LAYERS.find(l => l.id === id); const d = await load(Ly.file); if (!d) return;
  CUR = {layer: Ly, data: d, ti: ti ?? (Ly.t ? defaultTi(d) : 0)};
  $("#timebox").style.display = Ly.t ? "" : "none";
  if (Ly.t) { $("#tslider").max = d.time.length - 1; $("#tslider").value = CUR.ti; }
  LEG.update(Ly);
  $("#layerinfo").textContent = d.units ? (typeof d.units === "string" ? d.units : (d.units[Ly.key] || "")) : "";
  drawLayer();
}
function defaultTi(d) { const k = d.time.findIndex(t => t >= "2021-04-08"); return k < 0 ? 0 : k; }
function drawLayer() {
  const {layer: Ly, data: d, ti} = CUR; const Z = Ly.t ? d[Ly.key][ti] : d[Ly.key];
  const g = gridImage(d.lon, d.lat, Z, Ly.vmin, Ly.vmax, Ly.cm);
  if (OVER) MAP.removeLayer(OVER); OVER = L.imageOverlay(g.url, g.bounds, {opacity: .85}).addTo(MAP);
  if (ARROWS) MAP.removeLayer(ARROWS); ARROWS = null;
  if (Ly.arrows) {
    ARROWS = L.layerGroup(); const u = d.u10[ti], v = d.v10[ti];
    for (let j = 0; j < d.lat.length; j += 3) for (let i = 0; i < d.lon.length; i += 3) {
      const uu = u[j][i], vv = v[j][i]; if (uu == null) continue; const s = 0.025;
      ARROWS.addLayer(L.polyline([[d.lat[j], d.lon[i]], [d.lat[j] + vv * s, d.lon[i] + uu * s]], {color: "#222", weight: 1, interactive: false}));
      ARROWS.addLayer(L.circleMarker([d.lat[j] + vv * s, d.lon[i] + uu * s], {radius: 1, color: "#222", interactive: false}));
    }
    ARROWS.addTo(MAP);
  }
  if (Ly.t) { $("#tlabel").textContent = d.time[ti].replace("T", " ") + (d.time[ti].length > 10 ? " UTC" : ""); moveStorm(d.time[ti]); }
  else if (TRACKPOS) TRACKPOS.setStyle({opacity: 0, fillOpacity: 0});
}
function moveStorm(t) {
  const T = D["track.json"]; if (!T || !TRACKPOS) return;
  const tt = new Date((t.length <= 10 ? t + "T12:00" : t.replace("Z", "") + ":00") + "Z").getTime();
  let best = -1, bd = 1e15; T.time.forEach((s, i) => { const d = Math.abs(new Date(s).getTime() - tt); if (d < bd && T.lat[i] != null) { bd = d; best = i; } });
  if (best >= 0 && bd < 7 * 3600e3) { TRACKPOS.setLatLng([T.lat[best], T.lon[best]]); TRACKPOS.setStyle({opacity: 1, fillOpacity: .9}); }
  else TRACKPOS.setStyle({opacity: 0, fillOpacity: 0});
}
function vcol(v) { return v == null ? "#888" : v < 17 ? "#6baed6" : v < 25 ? "#fdae61" : v < 33 ? "#f46d43" : "#a50026"; }

async function initMap() {
  MAP = L.map("map", {zoomSnap: .5}).setView([-11.5, 120.5], 6); basemap(MAP); graticule(MAP); LEG = legend(MAP);
  const sel = $("#layer");
  for (const Ly of LAYERS) { const d = await load(Ly.file); if (d) sel.appendChild(el("option", {value: Ly.id, textContent: Ly.lab})); }
  sel.onchange = () => setLayer(sel.value);
  $("#tslider").oninput = e => { CUR.ti = +e.target.value; drawLayer(); };
  $("#play").onclick = () => { if (PLAY) { clearInterval(PLAY); PLAY = null; $("#play").textContent = "▶"; return; }
    $("#play").textContent = "❚❚"; PLAY = setInterval(() => { CUR.ti = (CUR.ti + 1) % CUR.data.time.length; $("#tslider").value = CUR.ti; drawLayer(); }, 450); };
  MAP.on("mousemove", e => {
    let s = `${fmt(e.latlng.lng, 2)}° BT, ${fmt(-e.latlng.lat, 2)}° LS`;
    if (CUR.data) { const d = CUR.data, i = nearestIdx(d.lon, e.latlng.lng), j = nearestIdx(d.lat, e.latlng.lat);
      const Z = CUR.layer.t ? d[CUR.layer.key][CUR.ti] : d[CUR.layer.key]; const v = Z?.[j]?.[i];
      if (v != null && Math.abs(d.lon[i] - e.latlng.lng) < .3 && Math.abs(d.lat[j] - e.latlng.lat) < .3) s += ` · ${fmt(v, 2)} ${CUR.layer.unit.split(",")[0]}`; }
    $("#cursor").textContent = s; });
  // case box
  L.rectangle([[-14, 118], [-9, 125]], {color: "#111", weight: 1.2, fill: false, dashArray: "6 4", interactive: false}).addTo(MAP);
  const T = await load("track.json");
  if (T) {
    TRACK = L.layerGroup().addTo(MAP); const ll = T.lat.map((y, i) => [y, T.lon[i]]).filter(p => p[0] != null);
    TRACK.addLayer(L.polyline(ll, {color: "#111", weight: 2}));
    T.time.forEach((t, i) => { if (T.lat[i] == null || !t.endsWith("00:00Z") && !t.endsWith("12:00Z")) return;
      TRACK.addLayer(L.circleMarker([T.lat[i], T.lon[i]], {radius: 5, color: "#111", weight: 1, fillColor: vcol(T.vmax_ms[i]), fillOpacity: 1})
        .bindTooltip(`${t.replace("T", " ")}<br>Vmax ${fmt(T.vmax_ms[i], 0)} m/s · ${fmt(T.pmin_hpa[i], 0)} hPa<br>translasi ${fmt(T.speed_ms[i], 1)} m/s`)); });
    TRACKPOS = L.circleMarker(ll[0], {radius: 10, color: "#000", weight: 2, fillColor: "#fff", fillOpacity: .9}).addTo(MAP);
    $("#showtrack").onchange = e => { e.target.checked ? TRACK.addTo(MAP) : MAP.removeLayer(TRACK); };
  }
  PTS = L.layerGroup().addTo(MAP); await addPointMarkers(PTS, false);
  $("#showpts").onchange = e => { e.target.checked ? PTS.addTo(MAP) : MAP.removeLayer(PTS); };
  if (sel.options.length) { sel.value = sel.options[0].value; await setLayer(sel.value); }
}
function nearestIdx(a, x) { let b = 0, d = 1e9; a.forEach((v, i) => { const e = Math.abs(v - x); if (e < d) { d = e; b = i; } }); return b; }

const TIDE_LL = {rote: [123.06, -10.708, "Rote"], waik: [119.22, -9.39, "Waikelo (Sumba)"], lemba: [116.07, -8.73, "Lembar"],
  beno: [115.22, -8.77, "Benoa"], brom: [122.22, -18.0, "Broome"], darw: [130.85, -12.47, "Darwin"]};
async function addPointMarkers(group, clickable) {
  const P = await load("points.json"), TD = await load("tide.json"), AR = await load("argo_pair.json");
  if (P) for (const [k, p] of Object.entries(P)) {
    const m = L.circleMarker([p.lonlat[1], p.lonlat[0]], {radius: 6, color: "#fff", weight: 2, fillColor: "#0b5f8a", fillOpacity: 1})
      .bindTooltip(`<b>${k}</b> · ${p.name}<br>${fmt(p.lonlat[0], 2)}° BT, ${fmt(-p.lonlat[1], 2)}° LS`);
    if (clickable) m.on("click", () => showPoint(k)); group.addLayer(m);
  }
  if (TD) for (const k of Object.keys(TD)) { const [x, y, n] = TIDE_LL[k];
    const m = L.marker([y, x], {icon: L.divIcon({className: "", html: `<div style="width:12px;height:12px;background:#b26b00;border:2px solid #fff;transform:rotate(45deg)"></div>`, iconAnchor: [6, 6]})})
      .bindTooltip(`<b>Stasiun pasut ${n}</b> (IOC: ${k})`);
    if (clickable) m.on("click", () => showTide(k)); group.addLayer(m); }
  if (AR) for (const w of ["pre", "post"]) { const a = AR.meta[w];
    const m = L.circleMarker([a.lat, a.lon], {radius: 6, color: "#000", weight: 1.5, fillColor: w === "pre" ? "#fdd835" : "#e65100", fillOpacity: 1})
      .bindTooltip(`<b>Argo ${a.id}</b> (${w === "pre" ? "sebelum" : "sesudah"})<br>${a.time}`);
    if (clickable) m.on("click", () => showArgo()); group.addLayer(m); }
}

/* ---------- plot util ---------- */
const PL = {displaylogo: false, responsive: true, modeBarButtonsToRemove: ["lasso2d", "select2d"]};
const LAY = (o = {}) => Object.assign({margin: {l: 55, r: 20, t: 30, b: 40}, font: {size: 12, family: "system-ui"}, paper_bgcolor: "#fff",
  plot_bgcolor: "#fff", legend: {orientation: "h", y: -0.18}, hovermode: "x unified"}, o);
const vline = (x, txt) => ({type: "line", x0: x, x1: x, yref: "paper", y0: 0, y1: 1, line: {color: "#999", dash: "dot", width: 1}});
async function passage() { const c = await load("calc.json"); return c?.calc?.track?.closest_Rote_time?.replace(" ", "T") || "2021-04-04T12:00"; }

/* ---------- panel 3 ---------- */
async function initStations() {
  MAP2 = L.map("map2").setView([-11.5, 120], 5.5); basemap(MAP2); graticule(MAP2, 2);
  const T = D["track.json"]; if (T) L.polyline(T.lat.map((y, i) => [y, T.lon[i]]).filter(p => p[0] != null), {color: "#111", weight: 1.5}).addTo(MAP2);
  const g = L.layerGroup().addTo(MAP2); await addPointMarkers(g, true);
  $("#stlist").innerHTML = "Biru = titik analisis satelit/ERA5 · jingga belah ketupat = stasiun pasut IOC · kuning/oranye = float Argo sebelum/sesudah siklon.";
}
async function showTide(k) {
  const d = (await load("tide.json"))[k]; const v = $("#stview"); const pas = await passage();
  v.innerHTML = `<h3>Stasiun pasut ${TIDE_LL[k][2]} <span class="tag">IOC ${k}${d.sensor ? " · sensor " + d.sensor : ""}</span> <span class="tag">data valid ${fmt(d.valid_frac * 100, 0)}%</span></h3>
  <div id="c1" class="chart"></div><div id="c2" class="chart" style="margin-top:10px"></div>
  <div class="cols two"><div><h3>Konstanta harmonik (UTide, Mar–Mei 2021)</h3><table class="tbl" id="hm"></table></div>
  <div><div id="c3" class="chart"></div><div id="c4" class="chart" style="margin-top:10px"></div></div></div><p class="small" id="tnote"></p>`;
  Plotly.newPlot("c1", [{x: d.t, y: d.raw, name: "Muka laut terukur (mentah, QC)", line: {width: 1, color: "#9aa5b1"}},
    {x: d.t, y: d.pred, name: "Prediksi pasut", line: {width: 1, color: "#0b5f8a"}},
    {x: d.t, y: d.resid, name: "Residu", line: {width: 1, color: "#b2182b"}}],
    LAY({title: {text: "Deret waktu per jam (m, relatif rata-rata)", font: {size: 13}}, shapes: [vline(pas)]}), PL);
  const tr = [{x: d.t, y: d.lowpass, name: "Residu lolos-rendah 40 jam", line: {color: "#b2182b", width: 2}}];
  if (d.ib_lp) tr.push({x: d.t, y: d.ib_lp, name: "Inverse barometer (ERA5)", line: {color: "#2166ac", dash: "dash"}});
  if (d.regression) { const r = d.regression; tr.push({x: d.t, y: d.ib_lp.map((ib, i) => r.a_ib * ib + r.b_taux * lp40(d.taux)[i] + r.c_tauy * lp40(d.tauy)[i]), name: "Regresi IB + τ angin", line: {color: "#1b7f4b", dash: "dot"}}); }
  Plotly.newPlot("c2", tr, LAY({title: {text: "Residu terfilter vs forcing atmosfer (m)", font: {size: 13}}, shapes: [vline(pas)], xaxis: {range: ["2021-03-20", "2021-04-30"]}}), PL);
  $("#hm").innerHTML = "<tr><th>Konstituen</th><th>Amplitudo (cm)</th><th>Fase g (°)</th></tr>" + d.harmonics.slice(0, 13).map(h => `<tr><td>${h.name}</td><td class="n">${fmt(h.A_cm, 1)}</td><td class="n">${fmt(h.g_deg, 0)}</td></tr>`).join("");
  if (d.spec) Plotly.newPlot("c3", [{x: d.spec.cpd, y: d.spec.raw, name: "Mentah", line: {color: "#9aa5b1"}}, {x: d.spec.cpd, y: d.spec.resid, name: "Residu", line: {color: "#b2182b"}}],
    LAY({title: {text: "Spektrum daya (Welch)", font: {size: 13}}, xaxis: {type: "log", title: "siklus/hari"}, yaxis: {type: "log", title: "m²/cpd"}, hovermode: "closest"}), PL);
  if (d.lagcorr) Plotly.newPlot("c4", [{x: d.lagcorr.lag_h, y: d.lagcorr.r, mode: "lines", line: {color: "#0b5f8a"}, name: "r"}],
    LAY({title: {text: "Lag-korelasi residu terfilter vs inverse barometer", font: {size: 13}}, xaxis: {title: "lag (jam, + = muka laut tertinggal)"}, yaxis: {title: "r"}, hovermode: "closest"}), PL);
  if (d.storm) $("#tnote").innerHTML = tpl(`Saat siklon (2–8 Apr): residu terfilter maksimum <b>{s.resid_lp_max_cm:1} cm</b> pada {s.t_max_resid:0}; kontribusi inverse barometer saat itu {s.ib_at_max_cm:1} cm, kontribusi angin (regresi) {s.wind_at_max_cm:1} cm. Tekanan minimum ERA5 di stasiun {s.msl_min_hpa:1} hPa. Regresi 15 Mar–30 Apr: koefisien IB {r.a_ib:2}, R² = {r.r2:2}.`, {s: d.storm, r: d.regression}).replace("{s.t_max_resid:0}", d.storm.t_max_resid);
}
const _lp = new Map();
function lp40(a) { if (_lp.has(a)) return _lp.get(a); const n = a.length, o = new Array(n); let w = 20; // rata-rata bergerak 40 jam (pendekatan tampilan)
  for (let i = 0; i < n; i++) { let s = 0, c = 0; for (let j = Math.max(0, i - w); j <= Math.min(n - 1, i + w); j++) if (a[j] != null) { s += a[j]; c++; } o[i] = c ? s / c : null; }
  _lp.set(a, o); return o; }
async function showPoint(k) {
  const S = (await load("point_series.json"))?.[k]; const B = (await load("heat_budget.json"))?.[k]; const v = $("#stview"); const pas = await passage();
  if (!S) { v.innerHTML = "<p>Deret waktu belum tersedia.</p>"; return; }
  v.innerHTML = `<h3>${k} · ${S.name} <span class="tag">${fmt(S.lonlat[0], 2)}° BT, ${fmt(-S.lonlat[1], 2)}° LS</span></h3>
   <div id="p1" class="chart"></div><div id="p2" class="chart" style="margin-top:10px"></div><div id="p3" class="chart" style="margin-top:10px"></div>`;
  const pre = S.sst ? S.sst.slice(S.sst_t.indexOf("2021-03-25"), S.sst_t.indexOf("2021-03-31") + 1) : [];
  const pm = pre.reduce((a, b) => a + b, 0) / (pre.length || 1);
  if (S.sst) Plotly.newPlot("p1", [{x: S.sst_t, y: S.sst, name: "SST MUR (harian)", line: {color: "#b2182b", width: 2}},
    {x: [S.sst_t[0], S.sst_t[S.sst_t.length - 1]], y: [pm, pm], name: "rata-rata 25–31 Mar", line: {color: "#999", dash: "dash"}}],
    LAY({title: {text: "Suhu permukaan laut (°C)", font: {size: 13}}, shapes: [vline(pas)]}), PL);
  if (S.era_t) Plotly.newPlot("p2", [{x: S.era_t, y: S.tau, name: "|τ| (N/m²)", line: {color: "#6a51a3"}},
    {x: S.era_t, y: S.wE, name: "w_E (m/hari)", yaxis: "y2", line: {color: "#1b7f4b"}}],
    LAY({title: {text: "Tegangan angin dan Ekman pumping (ERA5, 3-jam)", font: {size: 13}}, yaxis: {title: "N/m²"}, yaxis2: {title: "m/hari", overlaying: "y", side: "right"},
      xaxis: {range: ["2021-03-28", "2021-04-20"]}, shapes: [vline(pas)]}), PL);
  if (B) { const s = B.series;
    Plotly.newPlot("p3", [{x: s.t, y: s.flux, type: "bar", name: "Fluks panas permukaan"}, {x: s.t, y: s.rain, type: "bar", name: "Hujan"},
      {x: s.t, y: s.upw, type: "bar", name: "Upwelling (w_E·ΔT/h)"}, {x: s.t, y: s.resid, type: "bar", name: "Entrainment + adveksi (residu)"},
      {x: s.t, y: s.dTdt, mode: "lines+markers", name: "dT/dt terukur", line: {color: "#000"}}],
      LAY({barmode: "relative", title: {text: `Budget panas lapisan campuran (°C/hari), h = ${fmt(B.h_m, 0)} m, ΔT = ${fmt(B.dT_jump_C, 2)} °C`, font: {size: 13}}, shapes: [vline(pas)]}), PL); }
}
async function showArgo(target = "stview") {
  const A = await load("argo_pair.json"); if (!A) return; const m = A.meta;
  if (target === "stview") $("#stview").innerHTML = `<h3>Float Argo ${m.float}: profil sebelum (${m.pre.time.slice(0, 10)}) dan sesudah (${m.post.time.slice(0, 10)}) siklon</h3><div id="ap" class="chart tall"></div>
    <p class="small">${tpl("Jarak terdekat ke lintasan {m.dmin_track_km:0} km. MLD {m.mld_pre:0} → {m.mld_post:0} m; SST {m.sst_pre:2} → {m.sst_post:2} °C; isoterm 20 °C {m.z20_pre:0} → {m.z20_post:0} m. c₁ (mode-1 dari N²) = {m.c1_mode:2} m/s.", {m})}</p>`;
  const id = target === "stview" ? "ap" : target;
  Plotly.newPlot(id, [{x: A.pre.T, y: A.pre.z, name: "T sebelum", line: {color: "#fdb827", width: 2}}, {x: A.post.T, y: A.post.z, name: "T sesudah", line: {color: "#e65100", width: 2}},
    {x: A.pre.N2.map(v => v * 1e4), y: A.pre.z, name: "N² sebelum (10⁻⁴ s⁻²)", xaxis: "x2", line: {color: "#2166ac", width: 1}}],
    LAY({yaxis: {autorange: "reversed", title: "kedalaman (m)", range: [300, 0]}, xaxis: {title: "suhu (°C)", domain: [0, .62]}, xaxis2: {title: "N² (10⁻⁴ s⁻²)", domain: [.68, 1]},
      hovermode: "closest", margin: {l: 55, r: 15, t: 20, b: 50}}), PL);
  if (target === "stview") Plotly.relayout(id, {"yaxis.range": [300, 0]});
}

/* ---------- panel 4 ---------- */
async function initPred() {
  const B = await load("b1_predictions.json"), C = (await load("calc.json"))?.calc || {}, N = window.NARR || {};
  const P = B.predictions, A = B.assumptions;
  const rows = [
    ["Periode inersia di 10° LS", P.T_inertial_h, C.inertial?.T_inertial_h, "jam", 1, "inertial"],
    ["Kecepatan angin maksimum (dekat Rote–Sawu)", A.Vmax, C.track?.vmax_in_box_ms, "m/s", 1, "vmax"],
    ["Angin 10 m maksimum ERA5 di bawah siklon", A.Vmax, C.era5_storm?.U10max_ms, "m/s", 1, "era5wind"],
    ["Tegangan angin maksimum τ", P.tau_max_Nm2, C.era5_storm?.taumax_Nm2, "N/m²", 2, "tau"],
    ["Curl tegangan angin (besar, di bawah inti)", P.curl_scale_Nm3 * 1e6, C.era5_storm ? Math.abs(C.era5_storm.curl_min_Nm3) * 1e6 : null, "10⁻⁶ N m⁻³", 1, "curl"],
    ["Ekman pumping maksimum w_E", P.wE_m_per_day, C.era5_storm?.wE_max_m_day, "m/hari", 0, "wE"],
    ["Kecepatan translasi siklon U_h (median di kotak kasus)", A.Uh, C.track?.Uh_median_ms, "m/s", 1, "Uh"],
    ["Perpindahan termoklin η (maks., kotak kasus)", P.thermocline_uplift_m, C.era5_storm?.eta_max_casebox_m, "m", 0, "eta"],
    ["Kecepatan gelombang internal mode-1 c₁", P.c1_ms, C.froude?.c1_ms, "m/s", 2, "c1"],
    ["Rasio U_h/c₁", P.Uh_over_c1, C.froude?.ratio, "–", 2, "froude"],
    ["MLD setelah siklon (Argo terukur)", P.MLD_after_m, C.argo_pair?.mld_post, "m", 0, "mld"],
    ["MLD setelah siklon (model Ri bulk + data)", P.MLD_after_m, C.entrainment?.h_after_m, "m", 0, "mldmodel"],
    ["Pendinginan SST maksimum (kotak kasus, MUR)", P.dSST_entrainment_C + P.dSST_surface_flux_C, C.sst?.cooling_max_casebox_C, "°C", 2, "cool"],
    ["Pendinginan oleh fluks permukaan (W1, 2–12 Apr)", P.dSST_surface_flux_C, C.heat_budget?.W1?.flux, "°C", 2, "flux"],
    ["Inverse barometer di Rote saat residu maks.", P.eta_IB_cm, C.rote_sealevel?.ib_at_max_cm, "cm", 1, "ib"],
    ["Setup angin di Rote saat residu maks.", P.eta_wind_setup_cm, C.rote_sealevel?.wind_at_max_cm, "cm", 1, "setup"],
    ["e-folding pemulihan SST (W1)", P.SST_recovery_efold_days, C.recovery?.W1?.efold_days, "hari", 0, "recov"],
    ["Jeda puncak klorofil setelah SST terdingin", P.chl_lag_days, C.chl?.lag_after_sstmin_days, "hari", 0, "chl"],
    ["Pendinginan musim timur (klimatologi kotak kasus)", P.east_monsoon_dSST_C, C.east_monsoon?.clim_box_cooling_C, "°C", 2, "em"],
  ];
  const tb = $("#predtab");
  tb.innerHTML = "<tr><th>Besaran</th><th>Prediksi B1</th><th>Dari data</th><th>Selisih</th><th>Satuan</th><th>Penjelasan</th></tr>";
  for (const [lab, p, d, u, dg, key] of rows) {
    const diff = (typeof p === "number" && typeof d === "number") ? d - p : null;
    tb.innerHTML += `<tr><td>${lab}</td><td class="n">${fmt(p, dg)}</td><td class="n">${fmt(d, dg)}</td><td class="n">${diff == null ? "–" : (diff > 0 ? "+" : "") + fmt(diff, dg)}</td><td>${u}</td><td class="small">${N.pred?.[key] ? tpl(N.pred[key], {c: C, p: P, a: A}) : ""}</td></tr>`;
  }
  tb.innerHTML += `<tr><td>Sisi cold wake terkuat</td><td>kiri</td><td>${C.coldwake_side?.stronger_side ?? "–"}</td><td></td><td></td><td class="small">${N.pred?.side ? tpl(N.pred.side, {c: C}) : ""}</td></tr>`;
}

/* ---------- panel 5 ---------- */
async function initClaim() {
  const C = (await load("calc.json"))?.calc || {}, N = window.NARR || {}, hb = C.heat_budget?.W1;
  if (hb) {
    const atm = hb.flux + hb.rain, frac = atm / hb.dT_obs;
    const [lab, col] = frac < 0.3 ? ["SALAH", "#b2182b"] : frac < 0.7 ? ["BENAR SEBAGIAN", "#b26b00"] : ["BENAR", "#1b7f4b"];
    $("#verdict").innerHTML = `<span class="vbadge" style="background:${col}">${lab}</span> ` + tpl(N.verdict || "", {c: C, f: {frac, atm}});
    Plotly.newPlot("budgetbar", ["W1", "T0", "L100", "R100", "ROTE", "KPG"].filter(k => C.heat_budget?.[k]).map((k, i) => null).length ? [
      ...[["flux", "Fluks permukaan"], ["rain", "Hujan"], ["upwelling", "Upwelling Ekman"], ["entrain_resid", "Entrainment + adveksi (residu)"]].map(([kk, nn]) => ({
        type: "bar", name: nn, x: Object.keys(C.heat_budget), y: Object.values(C.heat_budget).map(r => r[kk])})),
      {type: "scatter", mode: "markers", name: "ΔT terukur (MUR)", x: Object.keys(C.heat_budget), y: Object.values(C.heat_budget).map(r => r.dT_obs), marker: {color: "#000", size: 10, symbol: "diamond"}}] : [],
      LAY({barmode: "relative", yaxis: {title: "°C (kumulatif 2–12 Apr)"}, hovermode: "closest"}), PL);
  }
  showArgo("argoprof");
  const ev = N.evidence || [];
  $("#evidence").innerHTML = ev.map((e, i) => `<div class="ev"><h4>${e.title}</h4><p class="small">${tpl(e.text, {c: C})}</p><a data-i="${i}">→ ${e.linklab}</a></div>`).join("");
  document.querySelectorAll(".ev a").forEach(a => a.onclick = () => { const e = ev[+a.dataset.i];
    if (e.layer) { showTab("peta"); $("#layer").value = e.layer; setLayer(e.layer, e.ti ?? null); }
    if (e.point) { showTab("stasiun"); e.point === "argo" ? showArgo() : TIDE_LL[e.point] ? showTide(e.point) : showPoint(e.point); } });
}

/* ---------- panel 6: kalkulator ---------- */
function deepen(par) {
  // profil: lapisan campuran h0 bersuhu T0, di bawahnya gradien γ (°C/m); impuls M = τ·t_res; Ri bulk 0,6
  const g = 9.81, rho0 = 1025, al = 3e-4, dz = 1, n = 500, z = [], T = [];
  for (let k = 0; k < n; k++) { const zz = k * dz + .5; z.push(zz); T.push(zz < par.h0 ? par.T0 : Math.max(par.T0 - par.gam * (zz - par.h0), 8)); }
  let Tu = T.slice(); if (par.eta > 0) Tu = z.map((zz, k) => zz < par.h0 ? par.T0 : interp(zz + par.eta, z, T));
  for (let k = Math.floor(par.h0); k < n - 1; k++) { const h = (k + 1) * dz; let s = 0; for (let j = 0; j <= k; j++) s += Tu[j]; const Tm = s / (k + 1);
    const db = g * al * (Tm - Tu[k + 1]), U = par.M / (rho0 * h); if (db * h / (U * U) >= 0.65) return {h, Tm, dT: Tm - par.T0, U, z, T: Tu}; }
  return {h: null, Tm: null, dT: null, z, T: Tu};
}
function interp(x, xs, ys) { if (x <= xs[0]) return ys[0]; for (let i = 1; i < xs.length; i++) if (x <= xs[i]) return ys[i - 1] + (ys[i] - ys[i - 1]) * (x - xs[i - 1]) / (xs[i] - xs[i - 1]); return ys[ys.length - 1]; }
function slider(box, id, lab, min, max, step, val, dec) {
  const l = el("label", {}, `<span>${lab}</span><input type="range" id="${id}" min="${min}" max="${max}" step="${step}" value="${val}"><output id="${id}o"></output>`);
  box.appendChild(l); const inp = l.querySelector("input"), o = l.querySelector("output");
  const upd = () => (o.textContent = fmt(+inp.value, dec)); upd(); inp.addEventListener("input", upd); return inp;
}
async function initCalc() {
  const C = (await load("calc.json"))?.calc || {}, B = await load("b1_predictions.json");
  const A = B.assumptions, ap = C.argo_pair || {}, tk = C.track || {}, es = C.era5_storm || {};
  // nilai bawaan dari data (fallback: asumsi B1)
  const dflt = {
    V: tk.vmax_in_box_ms ?? A.Vmax, R: (tk.rmw_median_km ?? A.Rmax / 1e3), Uh: tk.Uh_median_ms ?? A.Uh,
    lat: -(C.sst?.cooling_max_casebox_lonlat?.[1] ? -C.sst.cooling_max_casebox_lonlat[1] : 10), h0: ap.mld_pre ?? A.h0, T0: ap.sst_pre ?? A.T0,
    gam: ap.z20_pre && ap.mld_pre && ap.sst_pre ? (ap.sst_pre - 20) / (ap.z20_pre - ap.mld_pre) : A.gamma,
  };
  $("#calcsrc").innerHTML = "Nilai bawaan dari data: V_max, RMW dan U_h dari IBTrACS (median di kotak kasus); h₀, SST₀ dan gradien termoklin dari profil Argo " +
    (ap.pre ? ap.pre.id + " (" + ap.pre.time.slice(0, 10) + ")" : "–") + "; lintang dari titik pendinginan maksimum MUR. Model: τ = ρₐC_dU² (C_d Large & Pond, dibatasi 2,4×10⁻³), curl ≈ τ/RMW, w_E = curl/(ρ₀|f|), η = w_E·2RMW/U_h, pendalaman lapisan campuran dengan kriteria Ri bulk 0,65 dan impuls τ·min(2RMW/U_h, ½ periode inersia) (Price, Weller & Pinkel 1986).";
  const bx = $("#calcA");
  const s = {V: slider(bx, "sV", "V_max (m/s)", 10, 60, 1, Math.round(dflt.V), 0), R: slider(bx, "sR", "Radius angin maks. RMW (km)", 10, 150, 5, Math.round(dflt.R / 5) * 5, 0),
    Uh: slider(bx, "sU", "Kecepatan translasi U_h (m/s)", .5, 10, .1, dflt.Uh.toFixed(1), 1), lat: slider(bx, "sL", "Lintang (° LS)", 3, 20, .5, Math.abs(dflt.lat).toFixed(1), 1),
    h0: slider(bx, "sH", "Lapisan campuran awal h₀ (m)", 5, 100, 1, Math.round(dflt.h0), 0), T0: slider(bx, "sT", "SST awal (°C)", 24, 31, .1, dflt.T0.toFixed(1), 1),
    gam: slider(bx, "sG", "Gradien termoklin γ (°C/m)", .01, .3, .005, dflt.gam.toFixed(3), 3)};
  const run = () => {
    const V = +s.V.value, R = +s.R.value * 1e3, Uh = +s.Uh.value, la = +s.lat.value, h0 = +s.h0.value, T0 = +s.T0.value, gam = +s.gam.value;
    const cd = Math.min(V < 11 ? 1.2e-3 : (0.49 + 0.065 * V) * 1e-3, 2.4e-3), tau = 1.2 * cd * V * V, f = 2 * 7.2921e-5 * Math.sin(la * Math.PI / 180);
    const curl = tau / R, wE = curl / (1025 * f), tres = 2 * R / Uh, eta = wE * tres, M = tau * Math.min(tres, Math.PI / f);
    const N2 = 9.81 * 3e-4 * gam, c1 = Math.sqrt(N2) * 150 / Math.PI; // mode-1 untuk lapisan bergradien tetap setebal ~150 m
    const r0 = deepen({h0, T0, gam, M, eta: 0}), r1 = deepen({h0, T0, gam, M, eta});
    $("#outA").innerHTML = [["τ maks.", fmt(tau, 2) + " N/m²"], ["Curl ≈ τ/RMW", fmt(curl * 1e6, 1) + " ×10⁻⁶ N m⁻³"], ["w_E di bawah inti", fmt(wE * 86400, 0) + " m/hari"],
      ["Waktu tinggal di atas satu titik 2RMW/U_h", fmt(tres / 3600, 1) + " jam"], ["Pengangkatan termoklin η", fmt(eta, 0) + " m"], ["Periode inersia 2π/|f|", fmt(2 * Math.PI / f / 3600, 1) + " jam"],
      ["U_h / c₁ (c₁ ≈ N·H/π, H = 150 m)", fmt(Uh / c1, 2) + (Uh / c1 > 1 ? " (superkritis)" : " (subkritis)")],
      ["MLD setelah siklon (mixing saja)", r0.h ? fmt(r0.h, 0) + " m" : "> 500 m"], ["ΔSST mixing saja", fmt(r0.dT, 2) + " °C"],
      ["MLD setelah siklon (mixing + upwelling)", r1.h ? fmt(r1.h, 0) + " m" : "> 500 m"], ["ΔSST mixing + upwelling", fmt(r1.dT, 2) + " °C"]]
      .map(([a, b]) => `<span>${a}</span><span class="n">${b}</span>`).join("");
    Plotly.react("calcAchart", [{x: r0.T.slice(0, 250), y: r0.z.slice(0, 250), name: "profil awal", line: {color: "#fdb827"}},
      {x: r1.T.slice(0, 250), y: r1.z.slice(0, 250), name: "setelah upwelling η", line: {color: "#2166ac", dash: "dot"}},
      ...(r1.h ? [{x: [r1.Tm, r1.Tm], y: [0, r1.h], name: "lapisan campuran baru", line: {color: "#e65100", width: 3}}] : [])],
      LAY({yaxis: {autorange: "reversed", title: "kedalaman (m)"}, xaxis: {title: "°C"}, hovermode: "closest", margin: {l: 55, r: 15, t: 10, b: 45}}), PL);
  };
  Object.values(s).forEach(i => i.addEventListener("input", run)); run();

  // B: muka laut pantai
  const rs = C.rote_sealevel || {}, bxb = $("#calcB");
  const dp0 = rs.msl_min_hpa ? Math.max(1, Math.round(1010 - rs.msl_min_hpa)) : 10;
  const b = {dp: slider(bxb, "bP", "Penurunan tekanan Δp (hPa)", 0, 60, 1, dp0, 0), W: slider(bxb, "bW", "Angin ke arah pantai (m/s)", 0, 40, 1, Math.round(es.U10max_ms ? es.U10max_ms / 2 : 12), 0),
    L: slider(bxb, "bL", "Panjang fetch / lebar paparan L (km)", 2, 100, 1, 20, 0), h: slider(bxb, "bH", "Kedalaman rata-rata h (m)", 5, 100, 1, 30, 0)};
  const runB = () => { const dp = +b.dp.value, W = +b.W.value, L = +b.L.value * 1e3, h = +b.h.value;
    const cd = Math.min(W < 11 ? 1.2e-3 : (0.49 + 0.065 * W) * 1e-3, 2.4e-3), tau = 1.2 * cd * W * W, ib = dp * 100 / (1025 * 9.81) * 100, su = tau * L / (1025 * 9.81 * h) * 100;
    $("#outB").innerHTML = [["Inverse barometer Δp/(ρg)", fmt(ib, 1) + " cm"], ["τ angin", fmt(tau, 2) + " N/m²"], ["Setup angin τL/(ρgh)", fmt(su, 1) + " cm"], ["Total (tanpa pasut & gelombang)", fmt(ib + su, 1) + " cm"]]
      .map(([a, c]) => `<span>${a}</span><span class="n">${c}</span>`).join(""); };
  Object.values(b).forEach(i => i.addEventListener("input", runB)); runB();
  $("#calcBnote").innerHTML = rs.resid_lp_max_cm != null ? tpl("Pembanding terukur di Rote: residu terfilter maksimum {r.resid_lp_max_cm:1} cm, tekanan minimum ERA5 {r.msl_min_hpa:1} hPa. Δp bawaan = 1010 hPa − tekanan minimum ERA5 di Rote.", {r: rs}) : "";
}

/* ---------- panel 7 ---------- */
async function initH8() {
  const C = (await load("calc.json"))?.calc || {}, H = C.h8, N = window.NARR || {}, P = await load("h8_profiles.json");
  if (!H) { $("#h8text").innerHTML = "<p>Belum ada data profil Juli.</p>"; return; }
  $("#h8text").innerHTML = tpl(N.h8 || "", {h: H, c: C});
  $("#h8tab").innerHTML = "<tr><th></th><th>April (Seroja, pra-siklon)</th><th>Akhir Juli (musim timur)</th></tr>" +
    [["Profil Argo", H.profile ? "–" : "", H.profile + " (" + H.time.slice(0, 10) + ")"], ["SST awal (°C)", fmt(H.sst_apr, 2), fmt(H.sst_jul, 2)], ["MLD awal (m)", fmt(H.mld_apr, 0), fmt(H.mld_jul, 0)],
      ["Isoterm 20 °C (m)", fmt(H.z20_apr, 0), fmt(H.z20_jul, 0)], ["MLD setelah siklon (m)", fmt(H.h_after_apr, 0), fmt(H.h_after_jul, 0)],
      ["Pendinginan SST (°C)", fmt(H.dSST_apr, 2), fmt(H.dSST_jul, 2)], ["SST setelah siklon (°C)", fmt(H.T_after_apr, 2), fmt(H.T_after_jul, 2)]]
      .map(r => `<tr><td>${r[0]}</td><td class="n">${r[1]}</td><td class="n">${r[2]}</td></tr>`).join("");
  if (P) Plotly.newPlot("h8chart", [{x: P.apr.T, y: P.apr.z, name: "April (pra-Seroja)", line: {color: "#b2182b", width: 2}}, {x: P.jul.T, y: P.jul.z, name: "Juli (musim timur)", line: {color: "#2166ac", width: 2}}],
    LAY({yaxis: {autorange: "reversed", title: "kedalaman (m)", range: [300, 0]}, xaxis: {title: "suhu (°C)"}, hovermode: "closest"}), PL);
}

/* ---------- panel 8 ---------- */
async function initMethods() {
  const ds = await load("datasets.json"), N = window.NARR || {};
  $("#dstab").innerHTML = "<tr><th>Kode</th><th>Produk / ID</th><th>Versi</th><th>Domain</th><th>Periode</th><th>Diunduh (UTC)</th></tr>" +
    Object.entries(ds || {}).map(([k, d]) => `<tr><td>${k}</td><td>${d.id}<br><span class="small">${d.url ? `<a href="${d.url}" target="_blank">sumber</a>` : ""} ${d.note || ""}</span></td><td>${d.version || ""}</td><td>${d.domain || ""}</td><td>${d.period || ""}</td><td class="n">${d.download_utc || ""}</td></tr>`).join("");
  $("#steps").innerHTML = (N.steps || []).map(s => `<li>${s}</li>`).join("");
  $("#limits").innerHTML = (N.limits || []).map(s => `<li>${s}</li>`).join("");
  $("#repo").innerHTML = `Kode dan data turunan: <a href="https://github.com/${REPO}" target="_blank">github.com/${REPO}</a>. Pipeline dijalankan oleh GitHub Actions (<code>.github/workflows/data.yml</code>); unduhan memakai API publik. Untuk menjalankan ulang satu gambar: <code>pip install -r scripts/requirements.txt && bash scripts/run_all.sh</code>.`;
  $("#team").innerHTML = "<tr><th>Peran</th><th>Tanggung jawab</th></tr>" + (N.team || []).map(r => `<tr><td>${r[0]}</td><td>${r[1]}</td></tr>`).join("");
  $("#b1commit").href = `https://github.com/${REPO}/commits/main/scripts/b1_predictions.py`;
}

/* ---------- panel 1 ---------- */
async function initSummary() {
  const C = (await load("calc.json"))?.calc || {}, N = window.NARR || {};
  $("#sum-text").innerHTML = tpl(N.summary || "", {c: C});
  const k = [["{c.sst.cooling_max_casebox_C:1} °C", "pendinginan terbesar di Laut Sawu–Rote"], ["{c.recovery.W1.t90_days:0} hari", "sampai SST kembali (90% pulih)"],
    ["{c.chl.ratio:1}×", "kenaikan klorofil di jejak dingin"], ["{c.east_monsoon.clim_box_cooling_C:1} °C", "pendinginan musim timur biasa (rata-rata kotak)"]];
  $("#sum-kpi").innerHTML = k.map(([v, l]) => `<div class="kpi"><div class="v">${tpl(v, {c: C})}</div><div class="l">${l}</div></div>`).join("");
  const S = await load("seasonal.json");
  if (S) Plotly.newPlot("sum-chart", [{x: S.t, y: S.W1, name: "SST titik W1 (jejak dingin)", line: {color: "#b2182b"}}, {x: S.t, y: S.box, name: "SST rata-rata kotak kasus", line: {color: "#0b5f8a"}},
    {x: S.t, y: S.clim, name: "Klimatologi 2003–2020 (kotak)", line: {color: "#999", dash: "dash"}}],
    LAY({title: {text: "SST 2021 (MUR, °C): Seroja vs musim timur", font: {size: 13}}, shapes: [vline(await passage())]}), PL);
}

/* ---------- panel 2 grafik ---------- */
async function initMapCharts() {
  const X = await load("crosstrack.json"), T = await load("track.json"), C = (await load("calc.json"))?.calc || {};
  if (X) Plotly.newPlot("xtrack", [{x: X.x_km, y: X.dsst, mode: "lines+markers", line: {color: "#2166ac"}, name: "ΔSST"}],
    LAY({xaxis: {title: "jarak tegak lurus lintasan (km) · kiri (+) / kanan (−)", zeroline: true}, yaxis: {title: "pendinginan maks. (°C)"}, hovermode: "closest",
      shapes: [{type: "line", x0: 0, x1: 0, yref: "paper", y0: 0, y1: 1, line: {color: "#000"}}]}), PL);
  if (C.coldwake_side) $("#xtrack-note").innerHTML = tpl("Rata-rata 0–150 km di kiri lintasan {c.coldwake_side.mean_left_0_150km_C:2} °C vs kanan {c.coldwake_side.mean_right_0_150km_C:2} °C; pendinginan terbesar pada x = {c.coldwake_side.x_of_min_km:0} km (3–9 Apr).", {c: C});
  if (T) Plotly.newPlot("trackchart", [{x: T.time, y: T.vmax_ms, name: "V_max (m/s)", line: {color: "#b2182b"}}, {x: T.time, y: T.pmin_hpa, name: "p_min (hPa)", yaxis: "y2", line: {color: "#2166ac"}},
    {x: T.time, y: T.speed_ms, name: "U_h translasi (m/s)", line: {color: "#1b7f4b", dash: "dot"}}],
    LAY({yaxis: {title: "m/s"}, yaxis2: {title: "hPa", overlaying: "y", side: "right"}}), PL);
}

/* ---------- start ---------- */
(async () => {
  await Promise.all(["track.json", "calc.json", "b1_predictions.json", "points.json"].map(n => load(n)));
  const c = D["calc.json"]; $("#buildinfo").textContent = c ? "" : "(calc.json belum tersedia)";
  await initSummary(); await initMap(); await initMapCharts(); await initStations(); await initPred(); await initClaim(); await initCalc(); await initH8(); await initMethods();
  const h = location.hash.slice(1); if (h && document.getElementById(h)) showTab(h);
})();
