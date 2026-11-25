"""B1 – Prediksi kuantitatif a priori (DIKUNCI sebelum melihat data).

Semua masukan di sini adalah asumsi teori/orde besaran, BUKAN hasil data.
Nilai data pembanding dihitung di 30_analysis.py dan digabung di panel "Prediksi vs hasil".
Keluaran: data/derived/b1_predictions.json
"""
import json, math, os

OMEGA, g = 7.2921e-5, 9.81
rho_a, rho0, cp = 1.2, 1025.0, 3990.0
alpha = 3.0e-4          # koef. muai termal air laut tropis (1/°C)

A = dict(  # asumsi a priori
    lat_deg=-10.0,            # lintang acuan
    Vmax=25.0,                # m/s, angin maksimum siklon di sekitar Rote–Sawu (badai tropis kuat)
    Rmax=40e3,                # m, radius angin maksimum
    Cd=2.0e-3,                # koefisien seret angin kencang
    Uh=3.0,                   # m/s, kecepatan translasi siklon
    h0=30.0,                  # m, lapisan campuran awal (akhir musim barat)
    T0=29.5,                  # °C, SST awal
    gamma=0.08,               # °C/m, gradien suhu di bawah lapisan campuran
    H1=70.0,                  # m, kedalaman lapisan atas (termoklin) untuk model 2-lapis
    dT12=9.0,                 # °C, beda suhu lapisan atas–bawah
    Ri_c=0.6,                 # Ri bulk kritis (Price et al. 1986)
    dp_kupang=10.0,           # hPa, penurunan tekanan di Kupang
    tau_kupang=0.5,           # N/m², tegangan angin di Teluk Kupang
    L_fetch=20e3, h_bay=30.0, # m, fetch & kedalaman efektif teluk Kupang
    Qnet=-300.0, t_flux_d=2.0,# W/m² & hari: kehilangan panas permukaan selama siklon
)

f = 2 * OMEGA * math.sin(math.radians(A["lat_deg"]))
af = abs(f)
P = {}
P["f_s-1"] = f
P["T_inertial_h"] = 2 * math.pi / af / 3600

tau = rho_a * A["Cd"] * A["Vmax"] ** 2
curl = tau / A["Rmax"]                    # skala curl ~ τmax/Rmax
wE = curl / (rho0 * af)
t_res = 2 * A["Rmax"] / A["Uh"]
P["tau_max_Nm2"] = tau
P["curl_scale_Nm3"] = curl
P["wE_m_per_day"] = wE * 86400
P["residence_h"] = t_res / 3600
P["thermocline_uplift_m"] = wE * t_res

gp = g * alpha * A["dT12"]
c1 = math.sqrt(gp * A["H1"])
P["g_prime"] = gp
P["c1_ms"] = c1
P["Uh_over_c1"] = A["Uh"] / c1
P["R1_km"] = c1 / af / 1e3

# pendalaman lapisan campuran: kriteria Ri bulk dengan impuls momentum τ·t_res
M = tau * t_res
dz = 1.0
z = [i * dz + dz / 2 for i in range(400)]
T = [A["T0"] if zz < A["h0"] else max(A["T0"] - A["gamma"] * (zz - A["h0"]), 8.0) for zz in z]
h_new, Tml = A["h0"], A["T0"]
for k in range(int(A["h0"]), 399):
    h = (k + 1) * dz
    Tm = sum(T[:k + 1]) / (k + 1)
    db = g * alpha * (Tm - T[k + 1])
    U = M / (rho0 * h)
    if db * h / U ** 2 >= A["Ri_c"]:
        h_new, Tml = h, Tm
        break
P["MLD_after_m"] = h_new
P["dSST_entrainment_C"] = Tml - A["T0"]
P["U_mixed_layer_ms"] = M / (rho0 * h_new)

P["dSST_surface_flux_C"] = A["Qnet"] * A["t_flux_d"] * 86400 / (rho0 * cp * h_new)
P["eta_IB_cm"] = A["dp_kupang"] * 1.0          # 1 cm per hPa
P["eta_wind_setup_cm"] = A["tau_kupang"] * A["L_fetch"] / (rho0 * g * A["h_bay"]) * 100
P["SST_recovery_efold_days"] = 21.0             # orde besaran: 2–4 minggu
P["chl_lag_days"] = 5.0                         # orde besaran: 3–7 hari
P["cold_wake_side_SH"] = "kiri lintasan (resonansi rotasi angin berlawanan jarum jam dengan osilasi inersia BBS)"
P["east_monsoon_dSST_C"] = -1.5                 # orde besaran pendinginan musim timur
P["east_monsoon_duration_days"] = 90.0
P["claim_verdict_predicted"] = "salah: pendinginan entrainment ≈ 2× pendinginan fluks permukaan, belum termasuk efek pengangkatan termoklin"

out = {"locked_note": "Prediksi a priori – dikunci sebelum data diunduh (lihat riwayat commit).",
       "assumptions": A, "predictions": P}
os.makedirs("data/derived", exist_ok=True)
json.dump(out, open("data/derived/b1_predictions.json", "w"), indent=1)
for k, v in P.items():
    print(f"{k:28s} {v}")
