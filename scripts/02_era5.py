"""ERA5 per jam dari ARCO-ERA5 (Google Cloud Public Dataset, gs://gcp-public-data-arco-era5).
Subset domain analisis. Keluaran mentah: data/raw/era5_hourly.nc (Mar–Mei 2021, per jam).
"""
import os
import numpy as np, xarray as xr
import dask
from common import RAW, LON0, LON1, LAT0, LAT1, T0, T1, log_dataset

STORE = "gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3"
VARS = {"10m_u_component_of_wind": "u10", "10m_v_component_of_wind": "v10", "mean_sea_level_pressure": "msl",
        "sea_surface_temperature": "sst", "surface_sensible_heat_flux": "sshf", "surface_latent_heat_flux": "slhf",
        "surface_net_solar_radiation": "ssr", "surface_net_thermal_radiation": "str", "total_precipitation": "tp"}
out = os.path.join(RAW, "era5_hourly.nc")
if os.path.exists(out):
    print("sudah ada", out); raise SystemExit

ds = xr.open_zarr(STORE, chunks={"time": 1}, storage_options={"token": "anon"}, consolidated=True)
ds = ds[list(VARS)].rename(VARS)
ds = ds.sel(time=slice(T0, T1 + "T23:00"), latitude=slice(LAT1 + 0.5, LAT0 - 0.5),
            longitude=slice(LON0 - 0.5, LON1 + 0.5))
print(ds)
with dask.config.set(scheduler="threads", num_workers=64):
    parts = []
    for m in ["2021-03", "2021-04", "2021-05"]:
        sub = ds.sel(time=m).load()
        print("selesai", m, sub.time.size)
        parts.append(sub)
ds = xr.concat(parts, "time").astype("float32")
# fluks akumulasi per jam (J/m²) → W/m²; tp (m/jam) → mm/jam
for v in ["sshf", "slhf", "ssr", "str"]:
    ds[v] = ds[v] / 3600.0; ds[v].attrs["units"] = "W m-2 (positif ke bawah)"
ds["tp"] = ds["tp"] * 1000.0; ds["tp"].attrs["units"] = "mm/jam"
ds["msl"] = ds["msl"] / 100.0; ds["msl"].attrs["units"] = "hPa"
ds["sst"] = ds["sst"] - 273.15
ds.to_netcdf(out, encoding={v: {"zlib": True, "complevel": 4} for v in ds.data_vars})
log_dataset("ERA5", id="ERA5 hourly single levels via ARCO-ERA5 (full_37-1h-0p25deg-chunk-1.zarr-v3)",
            version="ERA5 (ECMWF), ARCO v3", url=STORE,
            domain=f"{LON0-0.5}–{LON1+0.5}° BT, {LAT0-0.5}–{LAT1+0.5}° LS (0,25°)", period=f"{T0} – {T1}, per jam",
            vars=list(VARS.values()))
print("tersimpan", out, os.path.getsize(out) / 1e6, "MB")
