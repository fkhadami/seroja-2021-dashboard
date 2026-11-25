"""GLORYS12 (D6) dan SLA DUACS L4 (D3) dari Copernicus Marine. Butuh secret CMEMS_USERNAME/PASSWORD."""
import os
from common import RAW, LON0, LON1, LAT0, LAT1, T0, T1, log_dataset

u, p = os.environ.get("CMEMS_USERNAME"), os.environ.get("CMEMS_PASSWORD")
if not (u and p):
    print("Secret CMEMS belum ada – dilewati."); raise SystemExit
import copernicusmarine as cm

MY = ["cmems_mod_glo_phy_my_0.083deg_P1D-m", "cmems_mod_glo_phy_myint_0.083deg_P1D-m"]
MYI = ["cmems_mod_glo_phy_myint_0.083deg_P1D-m", "cmems_mod_glo_phy_my_0.083deg_P1D-m"]
BOX = dict(minimum_longitude=117.0, maximum_longitude=126.0, minimum_latitude=-15.0, maximum_latitude=-8.0)
DOM = dict(minimum_longitude=LON0, maximum_longitude=LON1, minimum_latitude=LAT0, maximum_latitude=LAT1)
jobs = [
    # (kunci, ID kandidat, variabel, argumen ruang/kedalaman, nama berkas, mulai, akhir)
    ("GLORYS", MY, ["thetao", "so", "mlotst"], dict(**DOM, minimum_depth=0, maximum_depth=400), "glorys_MarApr.nc", "2021-03-20", "2021-04-30"),
    ("GLORYS_Jul", MYI, ["thetao", "so", "mlotst"], dict(**BOX, minimum_depth=0, maximum_depth=400), "glorys_Jul.nc", "2021-07-20", "2021-08-05"),
    ("SLA", ["cmems_obs-sl_glo_phy-ssh_my_allsat-l4-duacs-0.125deg_P1D", "cmems_obs-sl_glo_phy-ssh_my_allsat-l4-duacs-0.25deg_P1D",
             "cmems_obs-sl_glo_phy-ssh_nrt_allsat-l4-duacs-0.125deg_P1D"], ["sla", "ugosa", "vgosa", "adt"], dict(**DOM), "sla_2021.nc", T0, T1),
]
for key, ids, vars_, extra, fn, a, b in jobs:
    out = os.path.join(RAW, fn)
    if os.path.exists(out):
        continue
    for did in ids:
        try:
            cm.subset(dataset_id=did, variables=vars_, start_datetime=a + "T00:00:00",
                      end_datetime=b + "T23:59:59", output_directory=RAW, output_filename=fn,
                      username=u, password=p, **extra)
            log_dataset(key, id=did, version="CMEMS (lihat ID)", url="https://data.marine.copernicus.eu/product/" + did,
                        domain=f"{extra['minimum_longitude']}–{extra['maximum_longitude']}° BT, {extra['minimum_latitude']}–{extra['maximum_latitude']}° LS" + (f", 0–{extra['maximum_depth']} m" if 'maximum_depth' in extra else ""), period=f"{a} – {b}, harian", vars=vars_)
            print("ok", did); break
        except Exception as e:
            print("gagal", did, repr(e)[:400])
