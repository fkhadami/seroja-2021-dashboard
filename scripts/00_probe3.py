"""Probe ke-3: stasiun pasut alternatif (UHSLC, PacIOOS, BIG, IOC lain)."""
import json, requests
S = requests.Session(); S.headers["User-Agent"] = "ospan-seroja/1.0"; out = {}
def g(k, u, n=1500, t=200):
    try:
        r = S.get(u, timeout=t); out[k] = dict(status=r.status_code, head=r.text[:n])
    except Exception as e:
        out[k] = dict(error=repr(e)[:300])
IOC = "https://www.ioc-sealevelmonitoring.org/service.php"
for c in ["waik", "lemba", "beno", "brom", "darw", "saum", "dbal", "djve"]:
    g("ioc_" + c, f"{IOC}?query=data&code={c}&timestart=2021-04-03&timestop=2021-04-03T03:00&format=json", 400, 120)
g("uhslc_http", "http://uhslc.soest.hawaii.edu/data/csv/fast/hourly/", 3000, 120)
g("uhslc_https_fast", "https://uhslc.soest.hawaii.edu/data/csv/fast/hourly/", 3000, 120)
g("pacioos_search", "https://pae-paha.pacioos.hawaii.edu/erddap/search/index.csv?page=1&itemsPerPage=50&searchFor=sea%20level%20hourly", 6000)
g("big_ina", "https://ina-sealevelmonitoring.big.go.id/ipasut/", 800, 60)
g("big_srgi", "https://srgi.big.go.id/", 500, 60)
g("noaa_erddap_uhslc", "https://coastwatch.pfeg.noaa.gov/erddap/search/index.csv?page=1&itemsPerPage=50&searchFor=UHSLC", 6000)
g("osmc_uhslc", "https://osmc.noaa.gov/erddap/search/index.csv?page=1&itemsPerPage=50&searchFor=sea%20level", 6000)
json.dump(out, open("data/derived/probe3.json", "w"), indent=1)
print(json.dumps(out, indent=1)[:20000])
