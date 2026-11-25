"""Konstanta bersama, domain, dan utilitas unduh."""
import os, json, time, datetime as dt
import requests

RAW = "data/raw"
DER = "data/derived"
os.makedirs(RAW, exist_ok=True); os.makedirs(DER, exist_ok=True)

# Domain analisis (lebih luas dari kotak kasus 118–125 BT, 9–14 LS agar lintasan siklon tercakup)
LON0, LON1, LAT0, LAT1 = 112.0, 128.0, -18.0, -7.0
CASE_BOX = (118.0, 125.0, -14.0, -9.0)
T0, T1 = "2021-03-01", "2021-05-31"
STORM_T0, STORM_T1 = "2021-03-29", "2021-04-12"

UA = {"User-Agent": "ospan-seroja-pipeline/1.0 (ITB)"}
S = requests.Session(); S.headers.update(UA)


def get(url, path=None, tries=4, timeout=300, stream=False):
    """GET dengan retry; tulis ke path jika diberikan."""
    for k in range(tries):
        try:
            r = S.get(url, timeout=timeout, stream=bool(path))
            if r.status_code == 200:
                if path:
                    tmp = path + ".part"
                    with open(tmp, "wb") as f:
                        for c in r.iter_content(1 << 20):
                            f.write(c)
                    os.replace(tmp, path)
                    return path
                return r
            print(f"  HTTP {r.status_code} {url[:160]} :: {r.text[:300]}")
            if r.status_code in (400, 404):
                return None
        except Exception as e:
            print(f"  error {e!r} (percobaan {k+1})")
        time.sleep(5 * (k + 1))
    return None


def log_dataset(key, **meta):
    """Catat metadata dataset (untuk panel Metode dan data)."""
    p = os.path.join(DER, "datasets.json")
    d = json.load(open(p)) if os.path.exists(p) else {}
    meta.setdefault("download_utc", dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"))
    d[key] = meta
    json.dump(d, open(p, "w"), indent=1)


def dump(name, obj):
    import numpy as np
    def conv(o):
        if isinstance(o, (np.floating,)):
            return None if not np.isfinite(o) else round(float(o), 5)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, np.ndarray):
            return [conv(x) for x in o.tolist()]
        if isinstance(o, float):
            return None if o != o or o in (float("inf"), float("-inf")) else round(o, 5)
        if isinstance(o, dict):
            return {k: conv(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [conv(x) for x in o]
        return o
    with open(os.path.join(DER, name), "w") as f:
        json.dump(conv(obj), f, separators=(",", ":"))
