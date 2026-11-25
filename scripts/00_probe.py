"""Probe ketersediaan sumber data publik untuk kasus Seroja 2021.
Menulis data/derived/probe.json (status tiap sumber + ID dataset yang ditemukan).
"""
import json, os, datetime as dt, traceback
import requests

OUT = "data/derived/probe.json"
res = {"run_utc": dt.datetime.utcnow().isoformat(timespec="seconds")}
S = requests.Session(); S.headers["User-Agent"] = "ospan-seroja-probe/1.0"

def tryget(name, url, n=600, **kw):
    try:
        r = S.get(url, timeout=60, **kw)
        res[name] = {"url": url, "status": r.status_code, "head": r.text[:n]}
    except Exception as e:
        res[name] = {"url": url, "error": repr(e)}

# 1. IBTrACS (cekungan South Indian)
tryget("ibtracs_SI", "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.SI.list.v04r01.csv", n=300, stream=True)

# 2. ERDDAP CoastWatch: cari dataset SST & klorofil
for key, q in [("erddap_mur", "jplMURSST41"), ("erddap_ostia", "OSTIA"),
               ("erddap_chl_viirs", "VIIRS chlorophyll daily"),
               ("erddap_chl_occci", "OC-CCI chlorophyll")]:
    tryget(key, "https://coastwatch.pfeg.noaa.gov/erddap/search/index.csv?page=1&itemsPerPage=40&searchFor="
           + requests.utils.quote(q), n=6000)

# 3. Argo via Ifremer ERDDAP
tryget("argo_ifremer", "https://erddap.ifremer.fr/erddap/tabledap/ArgoFloats.csv?platform_number,time,longitude,latitude"
       "&longitude>=115&longitude<=128&latitude>=-16&latitude<=-7&time>=2021-03-01&time<=2021-05-31&distinct()", n=6000)

# 4. UHSLC fast-delivery hourly (ERDDAP UHSLC) – stasiun Indonesia/Timor/Australia utara
tryget("uhslc_stations", "https://uhslc.soest.hawaii.edu/erddap/tabledap/global_hourly_fast.csv?station_name,uhslc_id,latitude,longitude"
       "&latitude>=-20&latitude<=-5&longitude>=110&longitude<=135&distinct()", n=6000)
tryget("uhslc_rqds_stations", "https://uhslc.soest.hawaii.edu/erddap/tabledap/global_hourly_rqds.csv?station_name,uhslc_id,latitude,longitude"
       "&latitude>=-20&latitude<=-5&longitude>=110&longitude<=135&distinct()", n=6000)

# 5. IOC Sea Level Monitoring – daftar stasiun
try:
    r = S.get("https://www.ioc-sealevelmonitoring.org/service.php?query=stationlist&showall=all", timeout=90)
    st = r.json()
    sel = [s for s in st if s.get("Lon") is not None and 110 <= float(s["Lon"]) <= 135 and -20 <= float(s["Lat"]) <= -5]
    res["ioc_stations"] = {"status": r.status_code, "n": len(st), "region": sel}
except Exception as e:
    res["ioc_stations"] = {"error": repr(e)}

# 6. ARCO-ERA5 (Google Cloud public)
try:
    import xarray as xr
    ds = xr.open_zarr("gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3",
                      chunks=None, storage_options={"token": "anon"})
    vs = [v for v in ["10m_u_component_of_wind", "10m_v_component_of_wind", "mean_sea_level_pressure",
                      "surface_sensible_heat_flux", "surface_latent_heat_flux", "surface_net_solar_radiation",
                      "surface_net_thermal_radiation", "total_precipitation", "sea_surface_temperature"] if v in ds]
    res["arco_era5"] = {"ok": True, "vars_found": vs, "time_range": [str(ds.time.values[0]), str(ds.time.values[-1])],
                        "chunks_u10": str(ds["10m_u_component_of_wind"].encoding.get("chunks"))}
except Exception as e:
    res["arco_era5"] = {"error": traceback.format_exc()[-1500:]}

# 7. Copernicus Marine (butuh secret)
u, p = os.environ.get("CMEMS_USERNAME"), os.environ.get("CMEMS_PASSWORD")
res["cmems_secret_present"] = bool(u and p)
if u and p:
    try:
        import copernicusmarine as cm
        for did in ["cmems_mod_glo_phy_my_0.083deg_P1D-m", "cmems_mod_glo_phy_myint_0.083deg_P1D-m",
                    "cmems_obs-sl_glo_phy-ssh_my_allsat-l4-duacs-0.125deg_P1D"]:
            try:
                ds = cm.open_dataset(dataset_id=did, username=u, password=p,
                                     minimum_longitude=120, maximum_longitude=121,
                                     minimum_latitude=-11, maximum_latitude=-10)
                res["cmems_" + did] = {"ok": True, "vars": list(ds.data_vars),
                                       "time": [str(ds.time.values[0]), str(ds.time.values[-1])]}
            except Exception as e:
                res["cmems_" + did] = {"error": repr(e)[:800]}
    except Exception as e:
        res["cmems"] = {"error": repr(e)[:800]}

os.makedirs("data/derived", exist_ok=True)
json.dump(res, open(OUT, "w"), indent=1, default=str)
print(json.dumps(res, indent=1, default=str)[:20000])
