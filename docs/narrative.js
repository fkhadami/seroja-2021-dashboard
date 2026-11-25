/* Teks naratif dashboard. Angka TIDAK diketik di sini: setiap {c.x.y:d} diisi dari data/derived/calc.json. */
window.NARR = {
  summary: `<p>(menunggu hasil olahan)</p>`,
  pred: {},
  verdict: "",
  evidence: [],
  h8: "",
  steps: [
    "Lintasan, kecepatan angin maksimum, tekanan pusat, RMW dan kecepatan translasi Seroja dari IBTrACS v04r01 (cekungan South Indian), diinterpolasi per jam.",
    "ERA5 per jam (ARCO-ERA5): τ = ρₐC_d|U|U dengan C_d Large & Pond (1981) dibatasi 2,4×10⁻³ (pilihan kami untuk angin > 29 m/s); curl τ pada bola; w_E = (1/ρ₀)k·∇×(τ/f) (termasuk suku β); η = ∫w_E dt (1–12 Apr). Fluks akumulasi per jam dibagi 3600 s → W/m².",
    "MUR SST v4.1 harian (stride 0,03°): anomali relatif rata-rata 25–31 Mar 2021 (pra-siklon); cold wake = anomali minimum 3–25 Apr; profil lintas-lintasan dari bin 25 km tegak lurus lintasan 3–9 Apr. Klimatologi bulanan MUR 2003–2020 untuk pembanding musim timur.",
    "Argo (Ifremer ERDDAP), QC 1–2: pasangan profil float sebelum/sesudah siklon yang paling dekat lintasan; MLD (ΔT = 0,2 °C dari 10 m), N² (densitas linear), isoterm 20 °C, c₁ dari persamaan struktur vertikal mode-1 (rigid lid).",
    "Pendalaman lapisan campuran: kriteria Ri bulk 0,65 (Price, Weller & Pinkel 1986; prediksi B1 memakai 0,6) dengan impuls ∫τ dt ERA5 di lokasi float selama ½ periode inersia, dengan dan tanpa pengangkatan termoklin η.",
    "Budget panas lapisan campuran harian: dT/dt (MUR) = Q_net/(ρc_ph) + Q_hujan/(ρc_ph) − w_E·ΔT/h + residu (entrainment + adveksi). h dan ΔT dari Argo pra-siklon (atau GLORYS bila tersedia).",
    "Stasiun pasut IOC (Kupang tidak tersedia; dipakai Rote sebagai stasiun terdekat): despike (6×MAD), rata-rata per jam, analisis harmonik UTide (13 konstituen, OLS), residu, filter Butterworth lolos-rendah 40 jam, spektrum Welch, inverse barometer dari tekanan ERA5, regresi residu = a·IB + b·τx + c·τy.",
    "Klorofil-a VIIRS NOAA-20 + SNPP harian, komposit 3 hari; median di wilayah cold wake (pendinginan > 1 °C) untuk menentukan jeda puncak.",
    "Pemulihan SST: kurva eksponensial dari hari terdingin; t₉₀ = hari sampai pendinginan tinggal 10%.",
  ],
  limits: [
    "ERA5 0,25° melemahkan inti siklon kecil (RMW beberapa puluh km): angin maksimum, curl dan w_E dari ERA5 adalah batas bawah. Kalkulator memakai V_max dan RMW IBTrACS sebagai pembanding.",
    "Kupang tidak punya data di IOC/UHSLC yang terjangkau; Rote (±80 km barat daya Kupang, pantai terbuka) dipakai sebagai pengganti. Data IOC adalah data real-time tanpa QC resmi.",
    "MUR adalah produk L4 terinterpolasi; di bawah awan tebal siklon nilai hari-hari pertama sangat bergantung pada interpolasi dan mikrogelombang, sehingga waktu terdingin bisa tergeser 1–2 hari.",
    "Klorofil VIIRS banyak bolong karena awan selama dan sesudah siklon; di perairan dangkal dekat pantai klorofil dapat tercampur sedimen tersuspensi dari limpasan banjir.",
    "Budget panas mengabaikan adveksi horizontal; residu memuat entrainment dan adveksi sekaligus. Profil Argo hanya satu float dan tidak berada tepat di titik pendinginan maksimum.",
    "Model pendalaman 1-D (Ri bulk) tidak memuat perambatan energi inersia ke bawah, sehingga MLD dan pendinginan bisa berbeda dari profil terukur.",
  ],
  team: [
    ["Dosen (kasus contoh)", "Seluruh alur B1–B5, pipeline dan dashboard. Untuk kelompok: isi nama 4 anggota dan bagi peran seperti di bawah."],
    ["Anggota 1 – Atmosfer & siklon", "IBTrACS, ERA5, τ, curl, w_E, η, kalkulator A"],
    ["Anggota 2 – Satelit", "MUR/OISST, klorofil VIIRS, cold wake, pemulihan SST, musim timur"],
    ["Anggota 3 – Kolom air", "Argo, N², c₁, MLD, entrainment, budget panas, skenario H8"],
    ["Anggota 4 – Muka laut & integrasi", "Stasiun pasut, UTide, residu, IB & setup, kalkulator B, dashboard"],
  ],
};
