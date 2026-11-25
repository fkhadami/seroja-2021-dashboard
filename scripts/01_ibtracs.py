"""Lintasan Siklon Seroja dari IBTrACS v04r01 (NOAA NCEI)."""
import os, io
import numpy as np, pandas as pd
from common import RAW, get, log_dataset, dump

URL = "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.SI.list.v04r01.csv"
p = os.path.join(RAW, "ibtracs.SI.list.v04r01.csv")
if not os.path.exists(p):
    get(URL, p)
df = pd.read_csv(p, skiprows=[1], low_memory=False, na_values=[" ", ""])
s = df[(df.NAME == "SEROJA") & (df.SEASON == 2021)].copy()
print("SID:", s.SID.unique(), "n =", len(s))
s["time"] = pd.to_datetime(s.ISO_TIME)
num = ["LAT", "LON", "WMO_WIND", "WMO_PRES", "USA_WIND", "USA_PRES", "USA_RMW", "BOM_WIND", "BOM_PRES",
       "BOM_RMW", "STORM_SPEED", "STORM_DIR", "DIST2LAND", "USA_R34_NE", "USA_R34_SE", "USA_R34_SW", "USA_R34_NW",
       "BOM_ROCI", "USA_ROCI"]
for c in num:
    if c in s:
        s[c] = pd.to_numeric(s[c], errors="coerce")
s.to_csv(os.path.join("data/raw_small", "seroja_ibtracs.csv"), index=False)
# kecepatan angin terbaik: BOM (10-min) bila ada, jika tidak USA (1-min) dikonversi ×0.88
kt = 0.514444
wind = s.BOM_WIND.where(s.BOM_WIND.notna(), s.USA_WIND * 0.88) * kt
rmw = s.BOM_RMW.where(s.BOM_RMW.notna(), s.USA_RMW) * 1852.0
pres = s.BOM_PRES.where(s.BOM_PRES.notna(), s.WMO_PRES.where(s.WMO_PRES.notna(), s.USA_PRES))
track = {
    "sid": str(s.SID.iloc[0]),
    "time": s.time.dt.strftime("%Y-%m-%dT%H:%MZ").tolist(),
    "lat": s.LAT.values, "lon": s.LON.values,
    "vmax_ms": wind.values, "pmin_hpa": pres.values, "rmw_m": rmw.values,
    "speed_ms": (s.STORM_SPEED * kt).values, "dir_deg": s.STORM_DIR.values,
    "nature": s.NATURE.fillna("").tolist(),
}
dump("track.json", track)
log_dataset("IBTrACS", id="IBTrACS v04r01, ibtracs.SI.list", version="v04r01", url=URL,
            domain="Cekungan South Indian; difilter NAME=SEROJA, SEASON=2021", period=f"{s.time.min()} – {s.time.max()}")
print(s[["ISO_TIME", "LAT", "LON", "BOM_WIND", "USA_WIND", "BOM_PRES", "BOM_RMW", "USA_RMW", "STORM_SPEED"]].to_string())
