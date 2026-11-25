"""Unduh satelit dari ERDDAP NOAA CoastWatch:
  - MUR SST v4.1 harian (jplMURSST41), stride 3 (≈0,03°), 2021-01-01..2021-12-31
  - MUR SST bulanan (jplMURSST41mday) 2003–2020 untuk klimatologi (stride 10)
  - OISST v2.1 harian (pembanding produk kedua; OSTIA tidak tersedia di ERDDAP ini)
  - Klorofil VIIRS NOAA-20 & SNPP harian 4 km (Mar–Mei 2021)
"""
import os
import xarray as xr
from common import RAW, LON0, LON1, LAT0, LAT1, get, log_dataset

E = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/"


def grid(dsid, var, t0, t1, stride=1, extra="", lat_desc=False, fname=None):
    fname = fname or os.path.join(RAW, f"{dsid}_{t0[:10]}_{t1[:10]}.nc")
    if os.path.exists(fname):
        return fname
    la = f"({LAT1}):{stride}:({LAT0})" if lat_desc else f"({LAT0}):{stride}:({LAT1})"
    q = f"{E}{dsid}.nc?{var}[({t0}):1:({t1})]{extra}[{la}][({LON0}):{stride}:({LON1})]"
    print(" ", q)
    return get(q, fname, timeout=900)


def by_month(dsid, var, months, **kw):
    fs = []
    for a, b in months:
        f = grid(dsid, var, a, b, **kw)
        if f: fs.append(f)
    return fs


months21 = [(f"2021-{m:02d}-01T09:00:00Z", f"2021-{m:02d}-{d}T09:00:00Z") for m, d in
            zip(range(1, 13), [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])]
fs = by_month("jplMURSST41", "analysed_sst", months21, stride=3)
if fs:
    ds = xr.open_mfdataset(fs, combine="by_coords").load()
    ds.to_netcdf(os.path.join(RAW, "mur_daily_2021.nc"))
    log_dataset("MUR", id="jplMURSST41 (MUR SST v4.1, JPL/GHRSST)", version="fv04.1", url=E + "jplMURSST41",
                domain=f"{LON0}–{LON1}° BT, {LAT0}–{LAT1}° LS, stride 3 (≈0,03°)", period="2021-01-01 – 2021-12-31, harian")

f = grid("jplMURSST41mday", "sst", "2003-01-16T00:00:00Z", "2020-12-16T00:00:00Z", stride=10,
         fname=os.path.join(RAW, "mur_mday_2003_2020.nc"))
if f:
    log_dataset("MUR_mday", id="jplMURSST41mday (MUR bulanan)", version="fv04.1", url=E + "jplMURSST41mday",
                domain=f"{LON0}–{LON1}° BT, {LAT0}–{LAT1}° LS, stride 10 (≈0,1°)", period="2003–2020 bulanan (klimatologi)")

# OISST v2.1 (0.25°), sumbu lintang naik, ada dimensi zlev
f = grid("ncdcOisst21Agg_LonPM180", "sst", "2021-03-01T12:00:00Z", "2021-05-31T12:00:00Z", extra="[(0.0)]",
         fname=os.path.join(RAW, "oisst_2021MAM.nc"))
if f:
    log_dataset("OISST", id="ncdcOisst21Agg_LonPM180 (NOAA OISST v2.1 AVHRR)", version="v2.1",
                url=E + "ncdcOisst21Agg_LonPM180", domain=f"{LON0}–{LON1}° BT, {LAT0}–{LAT1}° LS (0,25°)",
                period="2021-03-01 – 2021-05-31, harian")

for dsid in ["nesdisVHNnoaa20chlaDaily", "nesdisVHNSQchlaDaily"]:
    f = grid(dsid, "chlor_a", "2021-03-01T12:00:00Z", "2021-05-31T12:00:00Z", extra="[(0.0)]", lat_desc=True,
             fname=os.path.join(RAW, f"{dsid}_2021MAM.nc"))
    if f:
        log_dataset("CHL_" + dsid, id=dsid + " (VIIRS L3 chlor_a OC3, NOAA NESDIS, NRT)", version="NRT L3 4 km",
                    url=E + dsid, domain=f"{LON0}–{LON1}° BT, {LAT0}–{LAT1}° LS (4 km)", period="2021-03-01 – 2021-05-31, harian")
