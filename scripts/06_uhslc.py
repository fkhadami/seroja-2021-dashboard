"""Muka laut per jam UHSLC fast-delivery untuk stasiun di 110–135° BT, 5–20° LS (dari meta.geojson)."""
import os, json, io
import pandas as pd
from common import RAW, get, log_dataset

B = "https://uhslc.soest.hawaii.edu/"
meta = get(B + "data/meta.geojson").json()
TS = "data/raw_small/tide_stations.json"
tmeta = json.load(open(TS)) if os.path.exists(TS) else {}
names = []
print("contoh properti:", meta["features"][0]["properties"])
for f in meta["features"]:
    lon, lat = f["geometry"]["coordinates"][:2]
    pr = f["properties"]
    if not (110 <= lon <= 135 and -20 <= lat <= -5):
        continue
    sid = str(pr.get("uhslc_id") or pr.get("id") or "").zfill(3)
    if not sid.strip("0"):
        continue
    fo = os.path.join(RAW, f"uhslc_{sid}_2021MAM.csv")
    if not os.path.exists(fo):
        r = get(B + f"data/csv/fast/hourly/h{sid}.csv", timeout=300)
        if r is None:
            continue
        d = pd.read_csv(io.StringIO(r.text), header=None, names=["y", "m", "d", "h", "mm"])
        d["t"] = pd.to_datetime(dict(year=d.y, month=d.m, day=d.d, hour=d.h))
        d = d[(d.t >= "2021-03-01") & (d.t < "2021-06-01") & (d.mm > -30000)]
        if len(d) < 24 * 30:
            print(sid, pr.get("name"), "data 2021 tidak cukup", len(d)); continue
        pd.DataFrame(dict(stime=d.t.dt.strftime("%Y-%m-%d %H:%M:%S"), slevel=d.mm / 1000.0, sensor="uhslc")).to_csv(fo, index=False)
    if os.path.exists(fo):
        key = "uh" + sid
        tmeta[key] = dict(name=f'{pr.get("name")} (UHSLC {sid})', lon=lon, lat=lat, file=os.path.basename(fo), source="UHSLC fast delivery")
        names.append(f'{pr.get("name")} ({sid})')
json.dump(tmeta, open(TS, "w"), indent=1)
log_dataset("UHSLC", id="UHSLC Fast Delivery hourly (csv/fast/hourly)", version="fast delivery", url=B + "data/csv/fast/hourly/",
            domain="stasiun: " + ", ".join(names), period="2021-03-01 – 2021-05-31, per jam",
            note="Kupang & Rote tidak ada di UHSLC; IOC Rote tidak berisi data")
print(names)
