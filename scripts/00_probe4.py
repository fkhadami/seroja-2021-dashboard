"""Probe ke-4: metadata stasiun UHSLC (fast delivery) di sekitar Nusa Tenggara."""
import json, re, requests, io
S = requests.Session(); out = {}
B = "https://uhslc.soest.hawaii.edu/"
for k, u in [("data_root", B + "data/"), ("nc_fast", B + "data/netcdf/fast/hourly/"), ("meta1", B + "data/meta.geojson"),
             ("meta2", B + "metadata/fd/"), ("stations", B + "stations/"), ("fd_json", B + "data/fd.json")]:
    try:
        r = S.get(u, timeout=120); out[k] = dict(status=r.status_code, head=r.text[:2500])
    except Exception as e:
        out[k] = dict(error=repr(e)[:200])
# baca atribut netCDF beberapa ID (unduh berkas kecil? pakai rentang byte tidak cukup) – coba file indeks
try:
    import xarray as xr, tempfile, os
    found = []
    lst = S.get(B + "data/netcdf/fast/hourly/", timeout=120).text
    ids = sorted(set(re.findall(r'h(\d{3,4})\.nc', lst)))
    out["n_ids"] = len(ids)
    cand = [i for i in ids if 100 <= int(i) <= 450]  # Pasifik barat & Samudra Hindia
    for i in cand:
        r = S.get(B + f"data/netcdf/fast/hourly/h{i}.nc", timeout=120)
        if r.status_code != 200: continue
        p = tempfile.mktemp(suffix=".nc"); open(p, "wb").write(r.content)
        try:
            ds = xr.open_dataset(p)
            lat = float(ds.lat.values.ravel()[0]); lon = float(ds.lon.values.ravel()[0])
            nm = str(ds.station_name.values.ravel()[0]) if "station_name" in ds else ""
            t0, t1 = str(ds.time.values[0])[:10], str(ds.time.values[-1])[:10]
            if 110 <= lon <= 135 and -20 <= lat <= -5:
                found.append(dict(id=i, name=nm, lat=lat, lon=lon, t0=t0, t1=t1))
            ds.close()
        except Exception as e:
            pass
        os.remove(p)
    out["found"] = found
except Exception as e:
    out["scan_error"] = repr(e)[:500]
json.dump(out, open("data/derived/probe4.json", "w"), indent=1)
print(json.dumps(out.get("found"), indent=1), out.get("n_ids"))
