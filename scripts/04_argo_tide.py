"""Profil Argo (Ifremer ERDDAP) dan muka laut stasiun pasut (IOC Sea Level Monitoring)."""
import os, io, json
import pandas as pd
from common import RAW, get, log_dataset

# ---- Argo
A = "https://erddap.ifremer.fr/erddap/tabledap/ArgoFloats.csv"
fa = os.path.join(RAW, "argo_2021FMAM.csv")
if not os.path.exists(fa):
    q = (A + "?platform_number,cycle_number,time,longitude,latitude,pres,temp,psal,temp_qc,psal_qc,pres_qc"
         "&longitude>=110&longitude<=128&latitude>=-20&latitude<=-6&time>=2021-02-15&time<=2021-05-31")
    get(q, fa, timeout=900)
if os.path.exists(fa):
    log_dataset("Argo", id="ArgoFloats (Argo GDAC via Ifremer ERDDAP)", version="GDAC snapshot saat unduh", url=A,
                domain="110–128° BT, 6–20° LS", period="2021-02-15 – 2021-05-31")

# Argo Juli–Agustus 2021 (profil musim timur untuk skenario H8)
fj = os.path.join(RAW, "argo_2021JA.csv")
if not os.path.exists(fj):
    q = (A + "?platform_number,cycle_number,time,longitude,latitude,pres,temp,psal,temp_qc,psal_qc,pres_qc"
         "&longitude>=112&longitude<=128&latitude>=-18&latitude<=-7&time>=2021-07-01&time<=2021-08-31")
    get(q, fj, timeout=900)

# ---- IOC Sea Level Monitoring
STATIONS = {"rote": "Rote", "waik": "Waikelo (Sumba)", "lemba": "Lembar (Lombok)", "beno": "Benoa (Bali)",
            "brom": "Broome", "darw": "Darwin"}
IOC = "https://www.ioc-sealevelmonitoring.org/service.php"
meta = {}
for code, name in STATIONS.items():
    fo = os.path.join(RAW, f"ioc_{code}_2021MAM.csv")
    if not os.path.exists(fo):
        frames = []
        for a, b in [("2021-03-01", "2021-03-31"), ("2021-04-01", "2021-04-30"), ("2021-05-01", "2021-05-31")]:
            r = get(f"{IOC}?query=data&code={code}&timestart={a}&timestop={b}T23:59:59&format=json", timeout=300)
            if r is None:
                continue
            try:
                frames.append(pd.DataFrame(r.json()))
            except Exception as e:
                print(code, a, "gagal parse", e, r.text[:200])
        if frames:
            pd.concat(frames).to_csv(fo, index=False)
    if os.path.exists(fo):
        d = pd.read_csv(fo)
        print(code, len(d), d.columns.tolist(), d.head(3).to_dict("records"))
        meta[code] = name
log_dataset("IOC_SLM", id="IOC Sea Level Station Monitoring Facility (VLIZ/IOC-UNESCO), data mentah tanpa QC",
            version="real-time raw", url=IOC, domain="stasiun: " + ", ".join(f"{k}={v}" for k, v in meta.items()),
            period="2021-03-01 – 2021-05-31", note="Kupang tidak tersedia di IOC; dipakai Rote (±80 km barat daya Kupang) sebagai stasiun terdekat")
