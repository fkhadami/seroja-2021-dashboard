"""Olah data mentah → JSON turunan untuk dashboard + hitungan B3/B4.
Setiap blok berdiri sendiri: jika data mentahnya belum ada, blok dilewati.
"""
import os, json, math, traceback
import numpy as np, pandas as pd, xarray as xr
from scipy import signal
from common import RAW, DER, CASE_BOX, dump, LON0, LON1, LAT0, LAT1

OMEGA, g, rho0, rho_a, cp = 7.2921e-5, 9.81, 1025.0, 1.2, 3990.0
R_E = 6.371e6
calc = {}          # hasil hitungan B3 (nilai dari data)
notes = {}
P = lambda f: os.path.join(RAW, f)
have = lambda f: os.path.exists(P(f))


def block(fn):
    def w():
        try:
            print(f"--- {fn.__name__}")
            fn()
        except Exception:
            traceback.print_exc()
            notes[fn.__name__] = "GAGAL: " + traceback.format_exc()[-600:]
    return w


def cd_lp(U):
    """Koefisien seret Large & Pond (1981), dibatasi 2,4e-3 di angin sangat kencang."""
    U = np.asarray(U)
    cd = np.where(U < 11, 1.2e-3, (0.49 + 0.065 * U) * 1e-3)
    return np.minimum(cd, 2.4e-3)


def dist_km(lon1, lat1, lon2, lat2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dl, dp = np.radians(lon2 - lon1), p2 - p1
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R_E * np.arcsin(np.sqrt(a)) / 1e3


# ------------------------------------------------------------ lintasan
TR = json.load(open(os.path.join(DER, "track.json")))
tr = pd.DataFrame({k: TR[k] for k in ["time", "lat", "lon", "vmax_ms", "pmin_hpa", "rmw_m", "speed_ms", "dir_deg"]})
tr["time"] = pd.to_datetime(tr.time.str.replace("Z", ""))
tr = tr.dropna(subset=["lat", "lon"]).set_index("time")
trh = tr[["lat", "lon", "vmax_ms", "pmin_hpa", "rmw_m", "speed_ms"]].resample("1h").mean().interpolate(limit=12)
inbox = trh[(trh.lon.between(CASE_BOX[0] - 2, CASE_BOX[1] + 1)) & (trh.lat.between(CASE_BOX[2] - 2, CASE_BOX[3] + 1))]


def track_heading(t):
    """Arah gerak (vektor satuan timur, utara) pada waktu t dari lintasan per jam."""
    i = trh.index.get_indexer([t], method="nearest")[0]
    a, b = trh.iloc[max(i - 3, 0)], trh.iloc[min(i + 3, len(trh) - 1)]
    dx = (b.lon - a.lon) * math.cos(math.radians(a.lat)); dy = b.lat - a.lat
    n = math.hypot(dx, dy) or 1
    return dx / n, dy / n


@block
def track_stats():
    s = inbox
    calc["track"] = dict(
        t_first_in_box=str(s.index.min()), t_last_in_box=str(s.index.max()),
        vmax_in_box_ms=float(s.vmax_ms.max()), pmin_in_box_hpa=float(s.pmin_hpa.min()),
        rmw_median_km=float(np.nanmedian(s.rmw_m) / 1e3) if s.rmw_m.notna().any() else None,
        Uh_median_ms=float(np.nanmedian(s.speed_ms)), Uh_min_ms=float(np.nanmin(s.speed_ms)),
        Uh_max_ms=float(np.nanmax(s.speed_ms)))
    # jarak terdekat ke Kupang & Rote
    for nm, (lo, la) in {"Kupang": (123.58, -10.17), "Rote": (123.06, -10.71)}.items():
        d = dist_km(trh.lon.values, trh.lat.values, lo, la)
        i = int(np.nanargmin(d))
        calc["track"][f"closest_{nm}_km"] = float(d[i]); calc["track"][f"closest_{nm}_time"] = str(trh.index[i])


# ------------------------------------------------------------ ERA5
ERA = None


@block
def era5():
    global ERA
    if not have("era5_hourly.nc"):
        print("ERA5 belum ada"); return
    ds = xr.open_dataset(P("era5_hourly.nc")).sortby("latitude")
    U = np.hypot(ds.u10, ds.v10)
    cd = xr.apply_ufunc(cd_lp, U)
    ds["taux"] = rho_a * cd * U * ds.u10
    ds["tauy"] = rho_a * cd * U * ds.v10
    lat = ds.latitude; lon = ds.longitude
    f = 2 * OMEGA * np.sin(np.radians(lat))
    dx = R_E * np.cos(np.radians(lat)) * np.radians(float(lon[1] - lon[0]))
    dy = R_E * np.radians(float(lat[1] - lat[0]))
    dtydx = ds.tauy.differentiate("longitude") / (dx / float(lon[1] - lon[0]))
    dtxdy = (ds.taux * np.cos(np.radians(lat))).differentiate("latitude") / (dy / float(lat[1] - lat[0])) / np.cos(np.radians(lat))
    ds["curl"] = dtydx - dtxdy                                   # N m^-3
    # w_E = (1/ρ0) k·∇×(τ/f) ≈ curl/(ρ0 f) + β τx/(ρ0 f²)
    beta = 2 * OMEGA * np.cos(np.radians(lat)) / R_E
    ds["wE"] = ds.curl / (rho0 * f) + beta * ds.taux / (rho0 * f ** 2)   # m/s, + = upwelling
    ds["Qnet"] = ds.sshf + ds.slhf + ds.ssr + ds.str
    ocean = ds.sst.isel(time=0).notnull()
    for v in ["curl", "wE", "Qnet"]:
        ds[v] = ds[v].where(ocean)
    ERA = ds
    # statistik di bawah siklon (dalam 2×RMW dari pusat), 2021-04-02..04-10
    st = ERA.sel(time=slice("2021-04-02", "2021-04-10"))
    rows = []
    for t in st.time.values:
        t_ = pd.Timestamp(t)
        if t_ not in trh.index or np.isnan(trh.loc[t_, "lat"]):
            continue
        c = trh.loc[t_]
        sub = st.sel(time=t, latitude=slice(c.lat - 1.5, c.lat + 1.5), longitude=slice(c.lon - 1.5, c.lon + 1.5))
        if sub.latitude.size == 0 or sub.longitude.size == 0:
            continue
        rows.append(dict(time=t_, U10max=float(np.hypot(sub.u10, sub.v10).max()), taumax=float(np.hypot(sub.taux, sub.tauy).max()),
                         curlmin=float(sub.curl.min()), wEmax=float(sub.wE.max()), pmin=float(sub.msl.min())))
    r = pd.DataFrame(rows).set_index("time")
    r.to_csv(os.path.join("data/raw_small", "era5_under_storm.csv"))
    sb = r.loc["2021-04-03":"2021-04-07"]
    calc["era5_storm"] = dict(U10max_ms=float(sb.U10max.max()), taumax_Nm2=float(sb.taumax.max()),
                              curl_min_Nm3=float(sb.curlmin.min()), wE_max_m_day=float(sb.wEmax.max() * 86400),
                              wE_median_core_m_day=float(sb.wEmax.median() * 86400), pmin_hpa=float(sb.pmin.min()))
    # perpindahan termoklin kumulatif η = ∫ w_E dt (2021-04-01..04-12)
    ww = ERA.wE.sel(time=slice("2021-04-01", "2021-04-12"))
    eta = (ww * 3600).sum("time", min_count=1)
    eta = eta.where(ERA.sst.isel(time=0).notnull())
    ERA["eta"] = eta
    calc["era5_storm"]["eta_max_m"] = float(eta.max())
    box = eta.sel(longitude=slice(CASE_BOX[0], CASE_BOX[1]), latitude=slice(CASE_BOX[2], CASE_BOX[3]))
    calc["era5_storm"]["eta_max_casebox_m"] = float(box.max())
    iy, ix = np.unravel_index(int(np.nanargmax(eta.values)), eta.shape)
    calc["era5_storm"]["eta_max_lonlat"] = [float(eta.longitude[ix]), float(eta.latitude[iy])]

    # ---- lapisan peta (6-jam) curl & w_E & angin
    sel = ERA.sel(time=slice("2021-03-31", "2021-04-12")).isel(time=slice(0, None, 6))
    coarse = sel.coarsen(latitude=2, longitude=2, boundary="trim").mean()
    dump("map_era5.json", dict(
        lon=coarse.longitude.values, lat=coarse.latitude.values,
        time=[pd.Timestamp(t).strftime("%Y-%m-%dT%HZ") for t in coarse.time.values],
        curl=(coarse.curl * 1e6).round(2).values, wE=(coarse.wE * 86400).round(1).values,
        U10=np.hypot(coarse.u10, coarse.v10).round(1).values, msl=coarse.msl.round(1).values,
        u10=coarse.u10.round(1).values, v10=coarse.v10.round(1).values,
        units=dict(curl="10⁻⁶ N m⁻³", wE="m/hari", U10="m/s", msl="hPa")))
    dump("map_eta.json", dict(lon=eta.longitude.values, lat=eta.latitude.values, eta=eta.round(1).values,
                              units="m (∫w_E dt, 1–12 Apr 2021)"))


# ------------------------------------------------------------ SST (MUR) & klimatologi
MUR = None


@block
def sst():
    global MUR
    if not have("mur_daily_2021.nc"):
        print("MUR belum ada"); return
    ds = xr.open_dataset(P("mur_daily_2021.nc"))
    v = "analysed_sst"
    sst = ds[v]
    if float(sst.max()) > 200: sst = sst - 273.15
    sst["time"] = pd.to_datetime(sst.time.values).normalize()
    MUR = sst
    pre = sst.sel(time=slice("2021-03-25", "2021-03-31")).mean("time")
    anom = sst - pre
    post = anom.sel(time=slice("2021-04-03", "2021-04-25"))
    dmin = post.min("time")
    tmin = post.fillna(99.0).idxmin("time").where(dmin.notnull())
    # peta komposit 0,1°
    c = 4  # MUR stride 3 (0,03°) → coarsen 4 ≈ 0,12°
    an_c = anom.sel(time=slice("2021-03-25", "2021-05-15")).coarsen(latitude=c, longitude=c, boundary="trim").mean()
    sst_c = sst.sel(time=slice("2021-03-25", "2021-05-15")).coarsen(latitude=c, longitude=c, boundary="trim").mean()
    dump("map_sst.json", dict(lon=an_c.longitude.values, lat=an_c.latitude.values,
                              time=[pd.Timestamp(t).strftime("%Y-%m-%d") for t in an_c.time.values],
                              anom=an_c.round(2).values, sst=sst_c.round(2).values,
                              units=dict(anom="°C (relatif rata-rata 25–31 Mar 2021)", sst="°C")))
    dmin_c = dmin.coarsen(latitude=c, longitude=c, boundary="trim").mean()
    tmin_c = (tmin - np.datetime64("2021-04-01")) / np.timedelta64(1, "D")
    tmin_c = tmin_c.coarsen(latitude=c, longitude=c, boundary="trim").mean()
    dump("map_coldwake.json", dict(lon=dmin_c.longitude.values, lat=dmin_c.latitude.values, dmin=dmin_c.round(2).values,
                                   tmin_day_after_apr1=tmin_c.round(1).values,
                                   units="°C, anomali minimum 3–25 Apr relatif 25–31 Mar"))
    i = np.unravel_index(int(np.nanargmin(dmin.values)), dmin.shape)
    calc["sst"] = dict(cooling_max_C=float(dmin.values[i]), cooling_max_lonlat=[float(dmin.longitude[i[1]]), float(dmin.latitude[i[0]])],
                       cooling_max_date=str(pd.Timestamp(tmin.values[i]).date()))
    bx = dmin.sel(longitude=slice(CASE_BOX[0], CASE_BOX[1]), latitude=slice(CASE_BOX[2], CASE_BOX[3]))
    j = np.unravel_index(int(np.nanargmin(bx.values)), bx.shape)
    calc["sst"]["cooling_max_casebox_C"] = float(bx.values[j])
    calc["sst"]["cooling_max_casebox_lonlat"] = [float(bx.longitude[j[1]]), float(bx.latitude[j[0]])]
    calc["sst"]["area_cooling_gt1C_km2"] = float(((dmin < -1).sum() * (0.03 * 111) ** 2 * np.cos(np.radians(-11))).values)

    # ---- asimetri kiri–kanan lintasan (sisi cold wake)
    lon2, lat2 = np.meshgrid(dmin.longitude.values, dmin.latitude.values)
    bins = np.arange(-300, 301, 25); mid = (bins[:-1] + bins[1:]) / 2
    def xprof(t0, t1):
        seg = trh.loc[t0:t1].dropna(subset=["lat", "lon"])
        xs, vs = [], []
        for t, r in seg.iloc[::2].iterrows():
            ex, ny = track_heading(t)
            dx = (lon2 - r.lon) * 111.32 * math.cos(math.radians(r.lat)); dy = (lat2 - r.lat) * 110.57
            along = dx * ex + dy * ny; cross = dx * (-ny) + dy * ex     # + = kiri (menghadap arah gerak)
            m = np.abs(along) < 20
            xs.append(cross[m]); vs.append(dmin.values[m])
        xs = np.concatenate(xs); vs = np.concatenate(vs)
        prof = [float(np.nanmean(vs[(xs >= a) & (xs < b)])) if np.isfinite(vs[(xs >= a) & (xs < b)]).sum() > 5 else None
                for a, b in zip(bins[:-1], bins[1:])]
        pv = np.array([p if p is not None else np.nan for p in prof])
        Lm = np.nanmean(pv[(mid > 0) & (mid <= 150)]); Rm = np.nanmean(pv[(mid < 0) & (mid >= -150)])
        return prof, dict(mean_left_0_150km_C=float(Lm), mean_right_0_150km_C=float(Rm), x_of_min_km=float(mid[np.nanargmin(pv)]),
                          stronger_side="kiri" if Lm < Rm else "kanan", Uh_median_ms=float(seg.speed_ms.median()), t0=t0, t1=t1)
    p_fast, s_fast = xprof("2021-04-05T00:00", "2021-04-07T06:00")
    p_slow, s_slow = xprof("2021-04-03T00:00", "2021-04-04T21:00")
    dump("crosstrack.json", dict(x_km=mid, dsst=p_fast, dsst_slow=p_slow, note="x>0 = kiri lintasan (menghadap arah gerak siklon)"))
    calc["coldwake_side"] = s_fast
    calc["coldwake_side_slow"] = s_slow


# ------------------------------------------------------------ titik analisis (dipilih dari data)
POINTS = {}


@block
def choose_points():
    """W1 = titik pendinginan terbesar di kotak kasus; W2 = titik pada lintasan; L/R = 100 km kiri/kanan lintasan;
    K = Teluk Kupang; C = kontrol jauh dari lintasan."""
    pts = {}
    if "sst" in calc:
        pts["W1"] = dict(name="Pendinginan maks. (kotak kasus)", lonlat=calc["sst"]["cooling_max_casebox_lonlat"])
    t = pd.Timestamp("2021-04-05T00:00")
    r = trh.loc[t]
    ex, ny = track_heading(t)
    pts["T0"] = dict(name="Pada lintasan 5 Apr 00 UTC", lonlat=[float(r.lon), float(r.lat)])
    k = 100 / 111.0
    pts["L100"] = dict(name="100 km kiri lintasan", lonlat=[float(r.lon - ny * k / math.cos(math.radians(r.lat))), float(r.lat + ex * k)])
    pts["R100"] = dict(name="100 km kanan lintasan", lonlat=[float(r.lon + ny * k / math.cos(math.radians(r.lat))), float(r.lat - ex * k)])
    pts["KPG"] = dict(name="Perairan Kupang (Teluk Kupang)", lonlat=[123.50, -10.15])
    pts["ROTE"] = dict(name="Selatan Rote (budidaya)", lonlat=[123.05, -10.95])
    pts["CTRL"] = dict(name="Kontrol: Laut Flores selatan", lonlat=[121.0, -8.3])
    POINTS.update(pts)
    dump("points.json", pts)


def nearest(da, lon, lat):
    return da.sel(longitude=lon, latitude=lat, method="nearest")


# ------------------------------------------------------------ Argo
ARGO = None


@block
def argo():
    global ARGO
    if not have("argo_2021FMAM.csv"):
        return
    a = pd.read_csv(P("argo_2021FMAM.csv"), skiprows=[1])
    a["time"] = pd.to_datetime(a.time).dt.tz_localize(None)
    a = a[(a.temp_qc.astype(str).str[0].isin(["1", "2"])) & a.pres.notna() & a.temp.notna()]
    prof = a.groupby(["platform_number", "cycle_number"])
    rows = []
    for (pn, cy), d in prof:
        d = d.sort_values("pres")
        if d.pres.min() > 10 or d.pres.max() < 150:
            continue
        rows.append(dict(id=f"{pn}_{cy}", platform=int(pn), cycle=int(cy), time=d.time.iloc[0], lon=float(d.longitude.iloc[0]),
                         lat=float(d.latitude.iloc[0]), p=d.pres.values, T=d.temp.values,
                         S=d.psal.values if d.psal.notna().all() else np.full(len(d), np.nan)))
    ARGO = rows
    # jarak minimum tiap profil ke lintasan
    for r in rows:
        d = dist_km(trh.lon.values, trh.lat.values, r["lon"], r["lat"])
        i = int(np.nanargmin(d)); r["dmin_track_km"] = float(d[i]); r["t_closest"] = trh.index[i]
    out = []
    for r in rows:
        out.append(dict(id=r["id"], platform=r["platform"], cycle=r["cycle"], time=str(r["time"]), lon=r["lon"], lat=r["lat"],
                        dmin_track_km=r["dmin_track_km"], t_closest=str(r["t_closest"]),
                        p=np.round(r["p"], 1), T=np.round(r["T"], 3), S=np.round(r["S"], 3)))
    dump("argo.json", out)


def profile_props(p, T, S):
    """MLD (ΔT=0,2 °C dari 10 m), N², kedalaman isoterm 20 °C, mode-1 c dari persamaan struktur vertikal."""
    p = np.asarray(p, float); T = np.asarray(T, float); S = np.asarray(S, float)
    z = np.arange(2, min(p.max(), 1000), 2.0)
    Ti = np.interp(z, p, T)
    Si = np.interp(z, p, S) if np.isfinite(S).all() else np.full_like(z, 34.5)
    T10 = np.interp(10, z, Ti)
    mld = float(z[np.argmax(Ti < T10 - 0.2)]) if (Ti < T10 - 0.2).any() else float(z[-1])
    # densitas linear (cukup untuk N²): α, β pada 25 °C
    rho = rho0 * (1 - 3.0e-4 * (Ti - 25) + 7.6e-4 * (Si - 34.5))
    N2 = g / rho0 * np.gradient(rho, z)
    z20 = float(np.interp(20, Ti[::-1], z[::-1])) if Ti.min() < 20 < Ti.max() else None
    # mode-1: d²φ/dz² + N²/c² φ = 0, φ(0)=φ(H)=0 (rigid lid, dasar datar di z maks)
    N2c = np.clip(N2, 1e-8, None)
    n = len(z); dz = z[1] - z[0]
    A = (np.diag(-2 * np.ones(n)) + np.diag(np.ones(n - 1), 1) + np.diag(np.ones(n - 1), -1)) / dz ** 2
    B = np.diag(N2c)
    from scipy.linalg import eigh
    w, _ = eigh(-A, B)        # -φ'' = (1/c²) N² φ
    c1 = float(1 / np.sqrt(w[0]))
    # 2-lapis: H1 = z20, g' dari beda densitas rata-rata
    if z20:
        up = rho[z <= z20].mean(); lo = rho[(z > z20) & (z <= min(z20 + 200, z[-1]))].mean()
        gp = g * (lo - up) / rho0
        c2l = math.sqrt(gp * z20)
    else:
        gp = c2l = None
    return dict(z=z, T=Ti, S=Si, N2=N2, mld=mld, sst=float(Ti[0]), z20=z20, c1_mode=c1, gprime=gp, c1_2layer=c2l, rho=rho)


@block
def argo_pre_post():
    """Pasangan profil sebelum & sesudah siklon dari float terdekat lintasan."""
    if not ARGO:
        return
    best = None
    for pf in set(r["platform"] for r in ARGO):
        rr = sorted([r for r in ARGO if r["platform"] == pf], key=lambda r: r["time"])
        for a, b in zip(rr[:-1], rr[1:]):
            if a["time"] < pd.Timestamp("2021-04-06") <= b["time"] and (b["time"] - a["time"]).days <= 12:
                d = min(a["dmin_track_km"], b["dmin_track_km"])
                if best is None or d < best[0]:
                    best = (d, a, b)
    if best is None:
        return
    d, a, b = best
    A_, B_ = profile_props(a["p"], a["T"], a["S"]), profile_props(b["p"], b["T"], b["S"])
    calc["argo_pair"] = dict(float=a["platform"], pre=dict(id=a["id"], time=str(a["time"]), lon=a["lon"], lat=a["lat"]),
                             post=dict(id=b["id"], time=str(b["time"]), lon=b["lon"], lat=b["lat"]), dmin_track_km=d,
                             mld_pre=A_["mld"], mld_post=B_["mld"], sst_pre=A_["sst"], sst_post=B_["sst"],
                             z20_pre=A_["z20"], z20_post=B_["z20"], c1_mode=A_["c1_mode"], c1_2layer=A_["c1_2layer"],
                             gprime=A_["gprime"], N2_max=float(np.nanmax(A_["N2"])),
                             N2_max_depth=float(A_["z"][np.nanargmax(A_["N2"])]))
    dump("argo_pair.json", dict(pre={k: A_[k] for k in ["z", "T", "S", "N2"]}, post={k: B_[k] for k in ["z", "T", "S", "N2"]},
                                meta=calc["argo_pair"]))
    PRE_PROFILE.update(A_)
    PRE_PROFILE["lonlat"] = [a["lon"], a["lat"]]


PRE_PROFILE = {}


@block
def inertial_and_froude():
    f10 = 2 * OMEGA * math.sin(math.radians(10))
    calc["inertial"] = dict(f_10S=-f10, T_inertial_h=2 * math.pi / f10 / 3600)
    src = calc.get("profile_W1", {}).get("src") if calc.get("profile_W1") else None
    c1 = calc["profile_W1"]["c1_mode"] if src else (PRE_PROFILE.get("c1_mode") if PRE_PROFILE else None)
    if c1 is None or "track" not in calc:
        return
    slow = trh.loc["2021-04-03T00":"2021-04-04T21"].speed_ms.median()
    fast = trh.loc["2021-04-05T00":"2021-04-07T06"].speed_ms.median()
    Uh = calc["track"]["Uh_median_ms"]
    calc["froude"] = dict(c1_ms=c1, c1_src=src or "Argo " + calc["argo_pair"]["pre"]["id"], Uh_ms=Uh, ratio=Uh / c1,
                          Uh_slow_ms=float(slow), ratio_slow=float(slow / c1), Uh_fast_ms=float(fast), ratio_fast=float(fast / c1),
                          R1_km=c1 / f10 / 1e3, wake_wavelength_km=fast * 2 * math.pi / f10 / 1e3)


@block
def mixing_entrainment():
    """Pendalaman lapisan campuran: kriteria Ri bulk (Price et al. 1986) dengan profil Argo pra-siklon
    dan impuls momentum ∫τ dt dari ERA5 di lokasi float selama ≤ ½ periode inersia."""
    if not PRE_PROFILE or ERA is None:
        return
    lo, la = PRE_PROFILE["lonlat"]
    tau = np.hypot(nearest(ERA.taux, lo, la), nearest(ERA.tauy, lo, la)).sel(time=slice("2021-04-02", "2021-04-12"))
    f = abs(2 * OMEGA * math.sin(math.radians(la)))
    Thalf = math.pi / f
    # jendela ½ periode inersia di sekitar puncak τ
    tp = pd.Timestamp(tau.idxmax("time").values)
    win = tau.sel(time=slice(tp - pd.Timedelta(seconds=Thalf / 2), tp + pd.Timedelta(seconds=Thalf / 2)))
    M = float((win * 3600).sum())
    z, T = PRE_PROFILE["z"], PRE_PROFILE["T"]; rho = PRE_PROFILE["rho"]
    h0 = PRE_PROFILE["mld"]; k0 = int(np.searchsorted(z, h0))
    res = None
    for k in range(k0, len(z) - 1):
        h = z[k]
        rm = rho[:k + 1].mean(); db = g * (rho[k + 1] - rm) / rho0
        U = M / (rho0 * h)
        if db * h / U ** 2 >= 0.65:
            res = (h, T[:k + 1].mean()); break
    calc["entrainment"] = dict(tau_peak_Nm2=float(tau.max()), t_peak=str(tp), impulse_Nsm2=M, window_h=Thalf / 3600,
                               h0_m=h0, h_after_m=res[0] if res else None,
                               dSST_entrain_C=(res[1] - T[0]) if res else None,
                               U_ml_ms=M / (rho0 * res[0]) if res else None)
    # dengan pengangkatan termoklin η dari ERA5 di lokasi yang sama (profil digeser ke atas η)
    eta = float(nearest(ERA.eta, lo, la))
    calc["entrainment"]["eta_local_m"] = eta
    if eta > 0:
        Tz = np.interp(z + eta, z, T); rz = np.interp(z + eta, z, rho)
        Tz[z < h0] = T[0]; rz[z < h0] = rho[0]
        for k in range(k0, len(z) - 1):
            h = z[k]; db = g * (rz[k + 1] - rz[:k + 1].mean()) / rho0; U = M / (rho0 * h)
            if db * h / U ** 2 >= 0.65:
                calc["entrainment"]["h_after_with_upwelling_m"] = h
                calc["entrainment"]["dSST_entrain_upw_C"] = float(Tz[:k + 1].mean() - T[0]); break


# ------------------------------------------------------------ deret waktu titik & budget panas
@block
def point_series():
    if not POINTS:
        return
    out = {}
    for k, p in POINTS.items():
        lo, la = p["lonlat"]; o = {"name": p["name"], "lonlat": p["lonlat"]}
        if MUR is not None:
            s = nearest(MUR, lo, la).sel(time=slice("2021-03-01", "2021-05-31"))
            o["sst_t"] = [pd.Timestamp(t).strftime("%Y-%m-%d") for t in s.time.values]; o["sst"] = s.round(3).values
        if ERA is not None:
            e = ERA.sel(longitude=lo, latitude=la, method="nearest")
            o["era_t"] = [pd.Timestamp(t).strftime("%Y-%m-%dT%H") for t in e.time.values[::3]]
            for v in ["u10", "v10", "msl", "Qnet", "ssr", "slhf", "tp"]:
                o[v] = e[v].values[::3].round(2) if v != "tp" else e[v].coarsen(time=3).sum().values.round(2)
            o["wE"] = (e.wE.values[::3] * 86400).round(1)
            o["tau"] = np.hypot(e.taux, e.tauy).values[::3].round(3)
        out[k] = o
    dump("point_series.json", out)


def ri_deepen(z, T, rho, h0, M, eta=0.0, Ric=0.65):
    """Pendalaman lapisan campuran 1-D: profil digeser naik η, lalu dicampur sampai Ri bulk ≥ Ric."""
    z = np.asarray(z); T = np.asarray(T, float); rho = np.asarray(rho, float)
    if eta > 0:
        T = np.interp(z + eta, z, T); rho = np.interp(z + eta, z, rho)
    k0 = max(int(np.searchsorted(z, h0)), 1)
    T = T.copy(); rho = rho.copy(); T[:k0] = T[0]; rho[:k0] = rho[0]
    for k in range(k0, len(z) - 1):
        h = z[k]; db = g * (rho[k + 1] - rho[:k + 1].mean()) / rho0; U = M / (rho0 * h)
        if U <= 0 or db * h / U ** 2 >= Ric:
            return float(h), float(T[:k + 1].mean())
    return None, None


def local_profile(k, lo, la, t0="2021-03-25", t1="2021-04-01"):
    """Profil pra-siklon: GLORYS di titik (jika ada), selain itu profil Argo pra-siklon."""
    if GL is not None:
        sl = GL.sel(longitude=lo, latitude=la, method="nearest").sel(time=slice(t0, t1)).mean("time")
        T = sl.thetao.dropna("depth"); S_ = sl.so.dropna("depth")
        if T.size > 5:
            pr = profile_props(T.depth.values, T.values, S_.interp(depth=T.depth).values)
            pr["src"] = "GLORYS12"; return pr
    if PRE_PROFILE:
        pr = dict(PRE_PROFILE); pr["src"] = "Argo " + calc.get("argo_pair", {}).get("pre", {}).get("id", ""); return pr
    return None


@block
def heat_budget():
    """Pemisahan pendinginan lapisan campuran di tiap titik (2 Apr → hari SST terdingin):
       fluks permukaan ∫Q/(ρc_p h0) dt, hujan, entrainment (Ri bulk, impuls ∫τ dt ERA5),
       upwelling (tambahan pendinginan bila profil digeser naik η = ∫w_E dt), residu (adveksi/3-D/galat)."""
    if MUR is None or ERA is None:
        return
    res = {}
    for k in ["W1", "T0", "L100", "R100", "KPG", "ROTE"]:
        if k not in POINTS: continue
        lo, la = POINTS[k]["lonlat"]
        pr = local_profile(k, lo, la)
        if pr is None: continue
        sst = nearest(MUR, lo, la).to_series()
        pre = sst.loc["2021-03-25":"2021-03-31"].mean()
        tmin = sst.loc["2021-04-03":"2021-04-20"].idxmin()
        t0 = pd.Timestamp("2021-04-02"); t1 = tmin + pd.Timedelta(hours=9)
        e = ERA.sel(longitude=lo, latitude=la, method="nearest")
        if not np.isfinite(float(e.Qnet.isel(time=0))):        # sel darat di ERA5 → cari sel laut terdekat
            m = ERA.sst.isel(time=0).notnull()
            dd = (ERA.longitude - lo) ** 2 + (ERA.latitude - la) ** 2
            j, i = np.unravel_index(int(dd.where(m).argmin()), dd.shape)
            e = ERA.isel(latitude=j, longitude=i)
        w = e.sel(time=slice(t0, t1))
        h0 = pr["mld"]
        flux = float((w.Qnet * 3600).sum()) / (rho0 * cp * h0)
        rain = float((-1000 * 4186 * (w.tp / 1000 / 3600) * 3.0 * 3600).sum()) / (rho0 * cp * h0)   # hujan ≈ 3 °C lebih dingin
        tau = np.hypot(w.taux, w.tauy)
        f = abs(2 * OMEGA * math.sin(math.radians(la)))
        tp_ = pd.Timestamp(tau.idxmax("time").values); half = pd.Timedelta(seconds=math.pi / f / 2)
        M = float((tau.sel(time=slice(tp_ - half, tp_ + half)) * 3600).sum())
        eta = float((w.wE * 3600).sum())
        hm, Tm = ri_deepen(pr["z"], pr["T"], pr["rho"], h0, M, 0.0)
        hu, Tu = ri_deepen(pr["z"], pr["T"], pr["rho"], h0, M, max(eta, 0.0))
        mix = (Tm - pr["T"][0]) if Tm is not None else np.nan
        upw = ((Tu - pr["T"][0]) - mix) if Tu is not None else np.nan
        obs = float(sst.loc[tmin] - pre)
        resid = obs - flux - rain - mix - upw
        daily = w.Qnet.to_series().resample("1D").mean()
        res[k] = dict(profile_src=pr["src"], h0_m=h0, t_min=str(tmin.date()), days=(tmin - t0).days, dT_obs=obs, flux=flux, rain=rain,
                      entrainment=mix, upwelling=upw, residual=resid, impulse_Nsm2=M, eta_m=eta, h_after_mix=hm, h_after_mixupw=hu,
                      Qnet_mean_Wm2=float(w.Qnet.mean()), rain_total_mm=float(w.tp.sum()), ssr_mean_Wm2=float(w.ssr.mean()),
                      ssr_pre_mean_Wm2=float(e.ssr.sel(time=slice("2021-03-25", "2021-03-31")).mean()),
                      frac_atm=(flux + rain) / obs if obs < 0 else None)
        s2 = sst.loc["2021-03-28":"2021-04-25"]
        q = e.Qnet.to_series().resample("1D").mean().reindex(s2.index.normalize(), method="nearest")
        res[k]["series"] = dict(t=[d.strftime("%Y-%m-%d") for d in s2.index], sst_anom=(s2 - pre).round(3).values,
                                atm_cum=np.round(np.cumsum(np.where(s2.index >= t0, q.values, 0) * 86400 / (rho0 * cp * h0)), 3),
                                Qnet_daily=np.round(q.values, 1))
    dump("heat_budget.json", res)
    calc["heat_budget"] = {k: {kk: v for kk, v in r.items() if kk != "series"} for k, r in res.items()}


GLORYS_MLD, DT_JUMP, PRE_DT_JUMP = {}, {}, {}
GL = None


@block
def glorys():
    global GL
    if not have("glorys_2021.nc"):
        print("GLORYS belum ada (secret CMEMS)"); return
    GL = xr.open_dataset(P("glorys_2021.nc"))
    ds = GL
    mld = ds.mlotst.sel(time=slice("2021-03-25", "2021-05-15"))
    dump("map_glorys.json", dict(lon=ds.longitude.values[::2], lat=ds.latitude.values[::2],
                                 time=[pd.Timestamp(t).strftime("%Y-%m-%d") for t in mld.time.values],
                                 mld=mld.values[:, ::2, ::2].round(1), units="m"))
    # validasi GLORYS vs Argo pra-siklon (lokasi float)
    if PRE_PROFILE:
        lo, la = PRE_PROFILE["lonlat"]
        g_ = ds.sel(longitude=lo, latitude=la, method="nearest").sel(time=calc["argo_pair"]["pre"]["time"][:10])
        T = g_.thetao.dropna("depth")
        gp = profile_props(T.depth.values, T.values, g_.so.dropna("depth").interp(depth=T.depth).values)
        calc["glorys_vs_argo"] = dict(mld_glorys=gp["mld"], mld_argo=PRE_PROFILE["mld"], z20_glorys=gp["z20"], z20_argo=PRE_PROFILE["z20"],
                                      sst_glorys=gp["sst"], sst_argo=PRE_PROFILE["sst"], c1_glorys=gp["c1_mode"], c1_argo=PRE_PROFILE["c1_mode"])
    # profil pra-siklon di W1 untuk c1 lokal
    if "W1" in POINTS:
        pr = local_profile("W1", *POINTS["W1"]["lonlat"])
        if pr: calc["profile_W1"] = dict(src=pr["src"], mld=pr["mld"], z20=pr["z20"], sst=pr["sst"], c1_mode=pr["c1_mode"],
                                         N2_max=float(np.nanmax(pr["N2"])), N2_max_depth=float(pr["z"][np.nanargmax(pr["N2"])]))


@block
def pre_jump():
    if PRE_PROFILE:
        z, T, h = PRE_PROFILE["z"], PRE_PROFILE["T"], PRE_PROFILE["mld"]
        PRE_DT_JUMP["v"] = float(T[0] - np.interp(h + 20, z, T))
        calc.setdefault("argo_pair", {})["dT_jump_C"] = PRE_DT_JUMP["v"]


# ------------------------------------------------------------ pemulihan SST & jeda klorofil
def clim_daily_at(lo, la, index):
    """Klimatologi MUR bulanan 2003–2020 di titik, diinterpolasi ke tanggal (siklis)."""
    cl = xr.open_dataset(P("mur_mday_2003_2020.nc")).sst
    if float(cl.max()) > 200: cl = cl - 273.15
    c = nearest(cl, lo, la).groupby("time.month").mean().values
    mm = np.concatenate([[c[-1]], c, [c[0]]])
    md = np.array([-15, 15, 45, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349, 380])
    return np.interp(index.day_of_year.values, md, mm)


@block
def recovery():
    out = {}
    if MUR is None: return
    for k in ["W1", "T0", "L100", "R100", "ROTE", "KPG"]:
        if k not in POINTS: continue
        lo, la = POINTS[k]["lonlat"]
        s_ = nearest(MUR, lo, la).to_series()
        if s_.isna().all(): continue
        a = s_ - (clim_daily_at(lo, la, s_.index) if have("mur_mday_2003_2020.nc") else 0)
        pre = a.loc["2021-03-25":"2021-03-31"].mean()
        d = a - pre
        tmin = d.loc["2021-04-03":"2021-04-20"].idxmin(); dmin = float(d.loc[tmin])
        after = d.loc[tmin:"2021-06-30"]
        def first(th):
            x = after[after >= th]
            return int((x.index[0] - tmin).days) if len(x) else None
        out[k] = dict(dmin_vs_clim=dmin, tmin=str(tmin.date()), t_efold_days=first(dmin / math.e), t50_days=first(dmin / 2),
                      t90_days=first(dmin * 0.1), days_below_1C=int((d.loc["2021-04-01":"2021-06-30"] < -1).sum()),
                      days_below_05C=int((d.loc["2021-04-01":"2021-06-30"] < -0.5).sum()))
        POINTS[k]["anom_series"] = dict(t=[x.strftime("%Y-%m-%d") for x in a.index], a=(a - pre).round(3).values)
    calc["recovery"] = out
    dump("anom_points.json", {k: v.get("anom_series") for k, v in POINTS.items() if v.get("anom_series")})


@block
def chlorophyll():
    prods = {"nesdisVHNSQchlaDaily": "chlor_a", "erdMH1chla1day": "chlorophyll", "noaacwNPPN20S3ASCIDINEOF2kmDaily": "chlor_a"}
    got = {}
    for dsid, var in prods.items():
        fs = sorted(f for f in os.listdir(RAW) if f.startswith(dsid + "_2021-"))
        if not fs: continue
        d = xr.open_mfdataset([P(f) for f in fs], combine="by_coords")[var].squeeze(drop=True).load()
        d["time"] = pd.to_datetime(d.time.values).normalize()
        got[dsid] = d.sortby("latitude").where(lambda x: (x > 0.01) & (x < 30))
        print(dsid, got[dsid].shape)
    if not got: return
    # peta: L3 VIIRS+MODIS digabung (rata-rata), komposit 3 hari; jika tidak ada pakai DINEOF
    l3 = [got[k] for k in ["nesdisVHNSQchlaDaily", "erdMH1chla1day"] if k in got]
    if l3:
        base = l3[0]
        l3 = [base] + [x.interp(latitude=base.latitude, longitude=base.longitude, method="nearest") for x in l3[1:]]
        chl = xr.concat(l3, "sat").mean("sat", skipna=True) if len(l3) > 1 else l3[0]
        src = "L3 " + " + ".join(k for k in ["nesdisVHNSQchlaDaily", "erdMH1chla1day"] if k in got)
    else:
        chl = got["noaacwNPPN20S3ASCIDINEOF2kmDaily"]; src = "DINEOF"
    c3 = chl.rolling(time=3, center=True, min_periods=1).mean()
    fac = max(1, int(round(0.12 / float(abs(chl.latitude[1] - chl.latitude[0])))))
    cc = np.log10(c3).coarsen(latitude=fac, longitude=fac, boundary="trim").mean()
    sel = cc.sel(time=slice("2021-03-25", "2021-05-15"))
    dump("map_chl.json", dict(lon=sel.longitude.values, lat=sel.latitude.values, time=[pd.Timestamp(t).strftime("%Y-%m-%d") for t in sel.time.values],
                              log10chl=sel.round(3).values, units=f"log10(mg m⁻³), komposit 3 hari, {src}"))
    if "noaacwNPPN20S3ASCIDINEOF2kmDaily" in got:
        dn = got["noaacwNPPN20S3ASCIDINEOF2kmDaily"]
        dnc = np.log10(dn).coarsen(latitude=6, longitude=6, boundary="trim").mean().sel(time=slice("2021-03-25", "2021-05-15"))
        dump("map_chl_dineof.json", dict(lon=dnc.longitude.values, lat=dnc.latitude.values, time=[pd.Timestamp(t).strftime("%Y-%m-%d") for t in dnc.time.values],
                                         log10chl=dnc.round(3).values, units="log10(mg m⁻³), DINEOF gap-filled 2 km"))
    # jeda respons di jejak dingin kotak kasus
    if MUR is None: return
    pre = MUR.sel(time=slice("2021-03-25", "2021-03-31")).mean("time")
    dmn = (MUR.sel(time=slice("2021-04-03", "2021-04-20")) - pre)
    out = {}
    for dsid, d in got.items():
        bx = d.sel(longitude=slice(CASE_BOX[0], CASE_BOX[1]), latitude=slice(CASE_BOX[2], CASE_BOX[3]))
        m = dmn.min("time").interp(latitude=bx.latitude, longitude=bx.longitude) < -1.0
        ts = bx.where(m).median(["latitude", "longitude"]).to_series()
        nv = bx.where(m).count(["latitude", "longitude"]).to_series()
        ts = ts.where(nv >= max(20, 0.05 * float(m.sum())))
        base = ts.loc["2021-03-10":"2021-04-02"].median()
        sm = ts.rolling(5, center=True, min_periods=2).median()
        if sm.loc["2021-04-03":"2021-05-15"].notna().sum() < 3: continue
        pk = sm.loc["2021-04-03":"2021-05-15"].idxmax()
        tmin = dmn.where(dmn.min("time") < -1.0).sel(longitude=slice(CASE_BOX[0], CASE_BOX[1]), latitude=slice(CASE_BOX[2], CASE_BOX[3])).mean(["latitude", "longitude"]).to_series().idxmin()
        half = sm.loc[pk:"2021-05-31"]; back = half[half <= base + 0.5 * (sm.loc[pk] - base)]
        out[dsid] = dict(base_mgm3=float(base), peak_mgm3=float(sm.loc[pk]), ratio=float(sm.loc[pk] / base), peak_date=str(pk.date()),
                         sst_min_date=str(tmin.date()), lag_days=int((pk - tmin).days),
                         decay_half_days=int((back.index[0] - pk).days) if len(back) else None, wake_pixels=int(m.sum()),
                         valid_median=float(nv.loc["2021-04-03":"2021-04-30"].median()))
        out[dsid]["series"] = dict(t=[x.strftime("%Y-%m-%d") for x in ts.index], chl=ts.round(3).values, smooth=sm.round(3).values, n=nv.values)
    dump("chl_wake_series.json", out)
    best = "noaacwNPPN20S3ASCIDINEOF2kmDaily" if "noaacwNPPN20S3ASCIDINEOF2kmDaily" in out else (list(out)[0] if out else None)
    if best:
        calc["chl"] = {kk: v for kk, v in out[best].items() if kk != "series"}; calc["chl"]["product"] = best
        calc["chl"]["lag_after_sstmin_days"] = calc["chl"]["lag_days"]
        calc["chl_all"] = {k: {kk: v for kk, v in o.items() if kk != "series"} for k, o in out.items()}


# ------------------------------------------------------------ musim timur vs Seroja
@block
def east_monsoon():
    if MUR is None or not have("mur_mday_2003_2020.nc"):
        return
    cl = xr.open_dataset(P("mur_mday_2003_2020.nc")).sst
    if float(cl.max()) > 200: cl = cl - 273.15
    bx = dict(longitude=slice(CASE_BOX[0], CASE_BOX[1]), latitude=slice(CASE_BOX[2], CASE_BOX[3]))
    clm = cl.sel(**bx).mean(["latitude", "longitude"]).groupby("time.month").mean()
    s21 = MUR.sel(**bx).mean(["latitude", "longitude"]).to_series()
    # klimatologi harian: interpolasi bulanan ke tanggal (siklis)
    doy = s21.index.dayofyear.values
    mm = np.concatenate([[clm.values[-1]], clm.values, [clm.values[0]]])
    mdoy = np.concatenate([[-15], np.array([15, 45, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349]), [380]])
    clim = np.interp(doy, mdoy, mm)
    an = s21.values - clim
    # siklus tahunan: amplitudo pendinginan musim timur = maks(Mar–Apr) − min(Jul–Sep) klimatologi
    em_cool = float(clm.sel(month=[7, 8, 9]).min() - clm.sel(month=[3, 4]).mean())
    em_months = int((clm < clm.sel(month=[3, 4]).mean() - 0.5).sum())
    # pendinginan lokal Seroja vs pendinginan lokal musim timur di titik W1
    lo, la = POINTS["W1"]["lonlat"] if "W1" in POINTS else (121, -11)
    w = nearest(MUR, lo, la).to_series()
    w_pre = w.loc["2021-03-25":"2021-03-31"].mean()
    w_em = w.loc["2021-07-01":"2021-09-30"]
    # durasi: pendinginan Seroja (relatif klimatologi) vs musim timur (siklus klimatologi)
    wa = w - clim_daily_at(lo, la, w.index); wa = wa - wa.loc["2021-03-25":"2021-03-31"].mean()
    seroja_days = int((wa.loc["2021-04-01":"2021-06-30"] < -0.5).sum())
    cW = pd.Series(clim_daily_at(lo, la, pd.date_range("2021-01-01", "2021-12-31")), pd.date_range("2021-01-01", "2021-12-31"))
    cW_amp = float(cW.loc["2021-07-01":"2021-09-30"].min() - cW.loc["2021-03-01":"2021-04-30"].mean())
    cW_days = int((cW < cW.loc["2021-03-01":"2021-04-30"].mean() - 0.5).sum())
    calc["east_monsoon"] = dict(W1_clim_cooling_C=cW_amp, W1_clim_days_below_05=cW_days, W1_seroja_days_below_05=seroja_days,
        W1_seroja_cooling_vs_clim_C=float(wa.loc["2021-04-03":"2021-04-20"].min()),
        clim_box_cooling_C=em_cool, clim_box_months_below_halfdeg=em_months,
        box_2021_min_anom_Apr=float(pd.Series(an, s21.index).loc["2021-04-01":"2021-04-30"].min()),
        W1_seroja_cooling_C=float(calc["sst"]["cooling_max_casebox_C"]) if "sst" in calc else None,
        W1_eastmonsoon_min_minus_pre_C=float(w_em.min() - w_pre),
        W1_days_below_pre_minus1C_JulSep=int((w_em < w_pre - 1).sum()))
    dump("seasonal.json", dict(t=[d.strftime("%Y-%m-%d") for d in s21.index], box=s21.round(3).values,
                               clim=np.round(clim, 3), anom=np.round(an, 3), W1=w.round(3).values,
                               clim_month=clm.round(3).values))


# ------------------------------------------------------------ stasiun pasut
@block
def tide_gauges():
    import utide
    out = {}
    meta = json.load(open("data/raw_small/tide_stations.json")) if os.path.exists("data/raw_small/tide_stations.json") else {}
    for code, mt in meta.items():
        f = P(mt["file"])
        if not os.path.exists(f) or os.path.getsize(f) < 100:
            continue
        d = pd.read_csv(f)
        tcol = "stime" if "stime" in d else d.columns[d.columns.str.contains("time")][0]
        vcol = "slevel" if "slevel" in d else d.columns[d.columns.str.contains("lev")][0]
        d["t"] = pd.to_datetime(d[tcol].astype(str).str.strip())
        # pilih sensor dengan data terbanyak
        if "sensor" in d:
            sen = d.sensor.value_counts().index[0]; d = d[d.sensor == sen]
        else:
            sen = None
        s = d.set_index("t")[vcol].astype(float).sort_index()
        s = s[~s.index.duplicated()]
        # QC: buang spike > 5σ dari median bergulir 1 jam, lalu rata-rata per jam
        med = s.rolling("60min", center=True).median(); dev = (s - med).abs()
        mad = dev.rolling("1D", center=True).median()
        s = s[dev < 6 * 1.4826 * mad.clip(lower=0.005)]
        h = s.resample("1h").mean()
        frac = float(h.notna().mean())
        if frac < 0.5:
            print(code, "data terlalu sedikit", frac); continue
        h = h - h.mean()
        tt = h.dropna()
        lat = mt["lat"]
        coef = utide.solve(tt.index.to_pydatetime(), tt.values, lat=lat, method="ols", conf_int="none", verbose=False,
                           constit=["M2", "S2", "N2", "K2", "K1", "O1", "P1", "Q1", "MSF", "MF", "M4", "MS4", "MM"])
        pred = utide.reconstruct(h.index.to_pydatetime(), coef, verbose=False).h
        resid = h.values - pred
        # filter lolos-rendah 40 jam (Butterworth orde 4, filtfilt pada data diisi interpolasi)
        r = pd.Series(resid, h.index)
        ri = r.interpolate(limit=6)
        b, a = signal.butter(4, 1 / 40, fs=1.0)
        okm = ri.notna().values
        lp = np.full(len(ri), np.nan)
        if okm.sum() > 100:
            seg = ri.interpolate().bfill().ffill().values
            lp = signal.filtfilt(b, a, seg); lp[~okm] = np.nan
        o = dict(sensor=sen, valid_frac=frac, t=[x.strftime("%Y-%m-%dT%H") for x in h.index], raw=h.round(3).values,
                 pred=np.round(pred, 3), resid=np.round(resid, 3), lowpass=np.round(lp, 3),
                 harmonics=[dict(name=n, A_cm=round(float(A) * 100, 1), g_deg=round(float(gg), 1))
                            for n, A, gg in zip(coef.name, coef.A, coef.g)])
        # spektrum Welch (segmen 15 hari) untuk mentah & residu
        fill = lambda x: pd.Series(x).interpolate(limit_direction="both").values
        fq, Sr = signal.welch(fill(h.values), fs=24.0, nperseg=24 * 15)
        _, Sx = signal.welch(fill(resid), fs=24.0, nperseg=24 * 15)
        o["spec"] = dict(cpd=fq[1:], raw=Sr[1:], resid=Sx[1:])
        # inverse barometer & angin dari ERA5 terdekat
        if ERA is not None:
            lon_ = mt["lon"]
            e = ERA.sel(longitude=lon_, latitude=lat, method="nearest")
            pm = e.msl.to_series()
            ib = -(pm - pm.mean()) * 100 / (rho0 * g)          # m
            ib = ib.reindex(h.index)
            ibl = pd.Series(signal.filtfilt(b, a, ib.interpolate().bfill().ffill().values), h.index)
            o["ib"] = ib.round(3).values; o["ib_lp"] = ibl.round(3).values
            tx = e.taux.to_series().reindex(h.index).interpolate(); ty = e.tauy.to_series().reindex(h.index).interpolate()
            o["taux"] = tx.round(3).values; o["tauy"] = ty.round(3).values
            # regresi residu lowpass = a·IB + b·τx + c·τy + d (selama 15 Mar–30 Apr)
            dfr = pd.DataFrame(dict(y=lp, ib=ibl.values, tx=pd.Series(signal.filtfilt(b, a, tx.bfill().ffill().values)).values,
                                    ty=pd.Series(signal.filtfilt(b, a, ty.bfill().ffill().values)).values), index=h.index)
            dfr = dfr.loc["2021-03-15":"2021-04-30"].dropna()
            X = np.c_[dfr.ib, dfr.tx, dfr.ty, np.ones(len(dfr))]
            beta, *_ = np.linalg.lstsq(X, dfr.y, rcond=None)
            fit = X @ beta
            ws = beta[1] * dfr.tx + beta[2] * dfr.ty
            yy = dfr.y - dfr.y.mean(); xx = dfr.ib - dfr.ib.mean(); lags = np.arange(-72, 73, 3)
            o["lagcorr"] = dict(lag_h=lags, r=[float(np.corrcoef(yy.values[max(0, l):len(yy) + min(0, l)], xx.values[max(0, -l):len(xx) - max(0, l)])[0, 1]) for l in lags])
            st = dfr.loc["2021-04-02":"2021-04-08"]
            ii = st.y.idxmax()
            o["regression"] = dict(a_ib=beta[0], b_taux=beta[1], c_tauy=beta[2], r2=float(1 - np.var(dfr.y - fit) / np.var(dfr.y)))
            o["storm"] = dict(t_max_resid=str(ii), resid_lp_max_cm=float(st.y.max() * 100), resid_raw_max_cm=float(r.loc["2021-04-02":"2021-04-08"].max() * 100),
                              ib_at_max_cm=float(dfr.ib.loc[ii] * 100), wind_at_max_cm=float(ws.loc[ii] * 100),
                              msl_min_hpa=float(pm.loc["2021-04-02":"2021-04-08"].min()))
        o.update(name=mt["name"], lon=mt["lon"], lat=mt["lat"], source=mt["source"])
        o["dist_track_km"] = float(np.nanmin(dist_km(trh.lon.values, trh.lat.values, mt["lon"], mt["lat"])))
        out[code] = o
        print(code, o.get("storm"), o.get("regression"))
    dump("tide.json", out)
    if out:
        key = min(out, key=lambda c: out[c]["dist_track_km"])   # stasiun terdekat lintasan
        o = out[key]
        calc["rote_sealevel"] = dict(station=key, name=o["name"], source=o["source"], dist_track_km=o["dist_track_km"],
                                     **o.get("storm", {}), **o.get("regression", {}),
                                     M2_cm=next((h["A_cm"] for h in o["harmonics"] if h["name"] == "M2"), None),
                                     K1_cm=next((h["A_cm"] for h in o["harmonics"] if h["name"] == "K1"), None))
        calc["tide_stations"] = {c: dict(name=v["name"], dist_track_km=v["dist_track_km"], source=v["source"], **v.get("storm", {})) for c, v in out.items()}


# ------------------------------------------------------------ SLA
@block
def sla():
    if not have("sla_2021.nc"):
        return
    ds = xr.open_dataset(P("sla_2021.nc"))
    s = ds.sla.sel(time=slice("2021-03-25", "2021-05-15"))
    dump("map_sla.json", dict(lon=ds.longitude.values, lat=ds.latitude.values,
                              time=[pd.Timestamp(t).strftime("%Y-%m-%d") for t in s.time.values],
                              sla=(s * 100).round(1).values, units="cm"))
    pre = ds.sla.sel(time=slice("2021-03-25", "2021-03-31")).mean("time")
    d = (ds.sla.sel(time=slice("2021-04-04", "2021-04-20")) - pre).min("time")
    calc["sla"] = dict(min_drop_cm=float(d.min() * 100))


@block
def scenario_h8():
    """H8: siklon identik (impuls momentum & η Seroja di W1) melintas akhir Juli di atas profil musim timur."""
    if "heat_budget" not in calc or "W1" not in calc["heat_budget"]:
        return
    hb = calc["heat_budget"]["W1"]; lo, la = POINTS["W1"]["lonlat"]
    A_ = local_profile("W1", lo, la)
    J = None; jsrc = None
    if GL is not None:
        J = local_profile("W1", lo, la, "2021-07-25", "2021-07-31"); jsrc = "GLORYS12 25–31 Jul 2021"
    elif have("argo_2021JA.csv"):
        a = pd.read_csv(P("argo_2021JA.csv"), skiprows=[1]); a["time"] = pd.to_datetime(a.time).dt.tz_localize(None)
        a = a[(a.temp_qc.astype(str).str[0].isin(["1", "2"])) & a.pres.notna() & a.temp.notna()]
        best = None
        for (pn, cy), d in a.groupby(["platform_number", "cycle_number"]):
            d = d.sort_values("pres")
            if d.pres.min() > 10 or d.pres.max() < 300: continue
            dd = dist_km(lo, la, d.longitude.iloc[0], d.latitude.iloc[0])
            if best is None or dd < best[0]: best = (dd, pn, cy, d)
        if best:
            dd, pn, cy, d = best
            J = profile_props(d.pres.values, d.temp.values, d.psal.values)
            jsrc = f"Argo {int(pn)}_{int(cy)} ({str(d.time.iloc[0])[:10]}, {dd:.0f} km dari W1)"
    if J is None or A_ is None: return
    M, eta = hb["impulse_Nsm2"], max(hb["eta_m"], 0.0)
    res = {}
    for nm, pr in [("apr", A_), ("jul", J)]:
        hm, Tm = ri_deepen(pr["z"], pr["T"], pr["rho"], pr["mld"], M, 0.0)
        hu, Tu = ri_deepen(pr["z"], pr["T"], pr["rho"], pr["mld"], M, eta)
        res[nm] = dict(sst0=pr["sst"], mld0=pr["mld"], z20=pr["z20"], c1=pr["c1_mode"], h_mix=hm, dT_mix=(Tm - pr["T"][0]) if Tm else None,
                       h_mixupw=hu, dT_mixupw=(Tu - pr["T"][0]) if Tu else None, T_after=Tu,
                       T_at_50m=float(np.interp(50, pr["z"], pr["T"])), T_at_100m=float(np.interp(100, pr["z"], pr["T"])))
    calc["h8"] = dict(src_apr=A_["src"], src_jul=jsrc, impulse_Nsm2=M, eta_m=eta, apr=res["apr"], jul=res["jul"],
                      ratio_cooling=(res["jul"]["dT_mixupw"] / res["apr"]["dT_mixupw"]) if res["apr"]["dT_mixupw"] and res["jul"]["dT_mixupw"] else None)
    dump("h8_profiles.json", dict(jul={k: J[k] for k in ["z", "T", "N2"]}, apr={k: A_[k] for k in ["z", "T", "N2"]}))


for b in [track_stats, era5, sst, choose_points, argo, argo_pre_post, pre_jump, glorys, inertial_and_froude, mixing_entrainment,
          point_series, heat_budget, recovery, chlorophyll, east_monsoon, tide_gauges, sla, scenario_h8]:
    b()

dump("calc.json", dict(calc=calc, notes=notes))
print(json.dumps(calc, indent=1, default=str)[:12000])
print("NOTES", notes)
