"""Probe ke-2: IOC (Rote/Kupang), info dataset klorofil ERDDAP."""
import json, requests
S = requests.Session(); out = {}
def g(k, u, n=3000):
    try:
        r = S.get(u, timeout=120); out[k] = dict(status=r.status_code, head=r.text[:n])
    except Exception as e:
        out[k] = dict(error=repr(e))
IOC = "https://www.ioc-sealevelmonitoring.org/service.php"
st = S.get(IOC + "?query=stationlist&showall=all", timeout=120).json()
out["ioc_match"] = [s for s in st if any(w in (str(s.get("Location", "")) + str(s.get("Code", ""))).lower() for w in ["kupang", "tenau", "rote", "kupa", "atapupu", "waingapu", "ende", "maumere", "labuan", "sabu", "kalabahi"])]
for c in ["rote"]:
    g(f"ioc_{c}_details", f"{IOC}?query=stationdetails&code={c}")
    for a, b in [("2021-04-01", "2021-04-05"), ("2022-04-01", "2022-04-02"), ("2024-04-01", "2024-04-02")]:
        g(f"ioc_{c}_{a}", f"{IOC}?query=data&code={c}&timestart={a}&timestop={b}&format=json", 600)
E = "https://coastwatch.pfeg.noaa.gov/erddap/"
for d in ["nesdisVHNnoaa20chlaDaily", "nesdisVHNSQchlaDaily", "erdMH1chla1day", "erdMH1chla8day", "nesdisVHNchlaGapFilledDaily", "noaacwNPPN20VIIRSchlaSciDaily"]:
    g("info_" + d, E + f"info/{d}/index.csv", 2500)
g("search_chl_sci", E + "search/index.csv?page=1&itemsPerPage=60&searchFor=chlorophyll%20science%20quality%20daily", 8000)
g("search_chl_gap", E + "search/index.csv?page=1&itemsPerPage=60&searchFor=chlorophyll%20gap%20filled", 8000)
json.dump(out, open("data/derived/probe2.json", "w"), indent=1)
print(json.dumps(out, indent=1)[:30000])
