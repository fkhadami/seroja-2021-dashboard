/* Teks naratif dashboard. Angka TIDAK diketik di sini: setiap {c.x.y:d} diisi dari data/derived/calc.json. */
window.NARR = {
  summary: `
<p><b>Ya, laut yang mendadak dingin itu akibat Siklon Seroja, dan sebagian besar dinginnya datang dari dalam laut sendiri, bukan dari hujan.</b></p>
<p>Seroja tumbuh di Laut Sawu pada 2 April 2021, lalu hampir diam di dekat Rote dan Kupang selama 3–4 April. Pusatnya lewat sekitar {c.track.closest_Rote_km:0} km dari Rote dan {c.track.closest_Kupang_km:0} km dari Kupang. Karena siklon berhenti lama di satu tempat, anginnya terus mengaduk laut di bawahnya.</p>
<p>Suhu permukaan laut di timur Rote dan selatan Kupang turun sampai {abs:c.sst.cooling_max_casebox_C:1} °C. Angin kencang mencampur air hangat di permukaan dengan air dingin di bawahnya. Putaran angin juga mengangkat air dingin dari kedalaman. Hujan dan mendung hanya menyumbang sekitar {pct:c.heat_budget.W1.frac_atm} dari pendinginan itu.</p>
<p>Air berubah warna karena air dari bawah membawa hara dan fitoplankton ke permukaan: klorofil di jejak dingin naik sekitar {c.chl.ratio:1} kali. Di dekat pantai, lumpur dari banjir ikut membuat air keruh.</p>
<p><b>Berapa lama?</b> Separuh pendinginan hilang dalam {c.recovery.W1.t50_days:0} hari, dan suhu hampir normal setelah {c.recovery.W1.t90_days:0} hari. Meski begitu, laut masih sedikit lebih dingin dari biasanya selama sekitar {c.recovery.W1.days_below_05C:0} hari.</p>
<p><b>Bisa terulang?</b> Bisa, terutama pada Maret–April ketika siklon masih mungkin terbentuk di dekat Nusa Tenggara. Setiap musim timur (Juli–September) laut juga mendingin sekitar {abs:c.east_monsoon.W1_clim_cooling_C:1} °C, tetapi perlahan selama berbulan-bulan. Seroja membawa dingin yang sama besarnya hanya dalam beberapa hari. Kejutan cepat inilah yang berbahaya bagi rumput laut.</p>
<p><b>Bisa diperingatkan?</b> Bisa. Jika peringatan siklon dari BMKG menyebut siklon akan lewat atau melambat di dekat lokasi budidaya, bersiaplah menghadapi air yang lebih dingin hingga {abs:c.sst.cooling_max_casebox_C:0} °C dalam {c.heat_budget.W1.days:0} hari dan air yang lebih dingin 1 °C dari normal selama sekitar {c.recovery.W1.days_below_1C:0} hari. Pertimbangkan panen lebih awal dan menunda penanaman bibit baru. Pasang pencatat suhu di lokasi budidaya.</p>`,
  pred: {
    inertial: "Hitungan langsung 2π/|f| (tidak bergantung data). Osilasi inersia di jejak siklon berperiode sama.",
    vmax: "IBTrACS (BoM, 10 menit) mencatat V_max {c.track.vmax_in_box_ms:1} m/s di sekitar kotak kasus, lebih kuat dari asumsi; Seroja menguat cepat di Laut Sawu.",
    era5wind: "ERA5 0,25° melemahkan inti siklon kecil (RMW median {c.track.rmw_median_km:0} km ≈ 2 sel ERA5), sehingga U10 ERA5 lebih rendah dari IBTrACS. Curl dan w_E dari ERA5 adalah batas bawah.",
    tau: "Meskipun U10 ERA5 lebih lemah, τ sebanding dengan prediksi karena C_d naik dengan kecepatan angin.",
    curl: "Curl terukur sebanding dengan τ/RMW. Inti siklon tersebar di beberapa sel ERA5.",
    wE: "w_E maksimum ERA5 sebanding dengan prediksi; nilai median di inti lebih kecil ({c.era5_storm.wE_median_core_m_day:0} m/hari).",
    Uh: "Translasi median di kotak {c.track.Uh_median_ms:1} m/s, tetapi saat diam dekat Rote–Kupang hanya {c.froude.Uh_slow_ms:1} m/s. Siklon yang lambat menghabiskan waktu lebih lama di atas satu titik.",
    eta: "η terukur lebih besar dari prediksi karena siklon hampir diam: waktu tinggal ≫ 2RMW/U_h asumsi. Lokasi maksimum {c.era5_storm.eta_max_casebox_lonlat.0:2}° BT, {abs:c.era5_storm.eta_max_casebox_lonlat.1:2}° LS.",
    c1: "c₁ dari persamaan struktur vertikal profil {c.froude.c1_src} lebih besar dari model 2-lapis asumsi karena termoklin (isoterm 20 °C ≈ {c.argo_pair.z20_pre:0} m) lebih dalam dari H₁ = 70 m.",
    froude: "Rasio ≈ 1: saat diam U_h/c₁ = {c.froude.ratio_slow:2} (subkritis, respons dekat siklon lebih simetris dan upwelling kuat), saat bergerak ke barat {c.froude.ratio_fast:2} (superkritis, jejak inersia-gravitasi dengan panjang gelombang ≈ {c.froude.wake_wavelength_km:0} km).",
    mld: "Float Argo {c.argo_pair.float} ({c.argo_pair.dmin_track_km:0} km dari lintasan, di 113° BT) mencatat MLD {c.argo_pair.mld_pre:0} → {c.argo_pair.mld_post:0} m.",
    mldmodel: "Model Ri bulk dengan impuls ∫τ dt ERA5 di lokasi float memberi MLD {c.entrainment.h_after_m:0} m: lebih dangkal dari profil Argo, karena impuls dari ERA5 lemah dan model 1-D tidak memuat shear inersia lanjutan.",
    cool: "Pendinginan terukur jauh lebih besar dari prediksi karena siklon diam dan MLD awal lebih tipis ({c.heat_budget.W1.h0_m:0} m); upwelling η menambah {c.heat_budget.W1.upwelling:2} °C.",
    flux: "Q_net rata-rata {c.heat_budget.W1.Qnet_mean_Wm2:0} W/m² selama {c.heat_budget.W1.days:0} hari pada lapisan {c.heat_budget.W1.h0_m:0} m (batas atas, karena lapisan sebenarnya menebal).",
    ib: "Perkiraan ERA5 untuk Kupang: Δp = {c.kupang.dp_hpa:1} hPa. Tidak ada data pasut terbuka di Kupang/Rote untuk April 2021; stasiun terdekat yang tersedia adalah {c.rote_sealevel.name} ({c.rote_sealevel.dist_track_km:0} km dari lintasan).",
    setup: "Setup Teluk Kupang dari τ ERA5 ke arah sumbu teluk (maks. {c.kupang.tau_into_bay_max_Nm2:2} N/m²), L = 25 km, h = 30 m (asumsi geometri).",
    tg: "Stasiun terbuka terdekat berjarak {c.rote_sealevel.dist_track_km:0} km dari lintasan, sehingga sinyal badainya lemah; regresi IB + τ menjelaskan R² = {c.rote_sealevel.r2:2} variansi residu terfilter.",
    emdur: "Musim timur adalah pendinginan berbulan-bulan; Seroja menyebabkan anomali < −0,5 °C selama {c.east_monsoon.W1_seroja_days_below_05:0} hari di W1.",
    recov: "e-folding diukur dari anomali relatif klimatologi MUR 2003–2020; pemulihan lebih cepat dari prediksi karena lapisan campuran tipis cepat dipanaskan kembali oleh matahari setelah langit cerah.",
    chl: "Puncak klorofil hampir bersamaan dengan SST terdingin, bukan beberapa hari kemudian. Kenaikan awal adalah fitoplankton dari maksimum klorofil bawah permukaan yang ikut teraduk ke atas, belum pertumbuhan baru.",
    em: "Klimatologi MUR kotak kasus: SST musim timur lebih dingin {abs:c.east_monsoon.clim_box_cooling_C:1} °C daripada Maret–April, di bawah −0,5 °C selama ±{c.east_monsoon.W1_clim_days_below_05:0} hari di W1, dibandingkan {c.east_monsoon.W1_seroja_days_below_05:0} hari untuk Seroja.",
    side: "Fase bergerak (5–7 Apr): rata-rata 0–150 km kiri {c.coldwake_side.mean_left_0_150km_C:2} °C vs kanan {c.coldwake_side.mean_right_0_150km_C:2} °C. Asimetrinya kecil karena U_h/c₁ ≈ 1 dan siklon lebih lama diam, sehingga pendinginan terkonsentrasi di bawah pusat.",
  },
  verdict: "Klaim ini <b>sebagian besar keliru</b>. Di titik pendinginan terbesar (W1), fluks panas permukaan termasuk berkurangnya sinar matahari (radiasi surya turun dari {c.heat_budget.W1.ssr_pre_mean_Wm2:0} ke {c.heat_budget.W1.ssr_mean_Wm2:0} W/m²) menyumbang {c.heat_budget.W1.flux:2} °C, dan hujan ({c.heat_budget.W1.rain_total_mm:0} mm) hanya {c.heat_budget.W1.rain:2} °C, dari total {c.heat_budget.W1.dT_obs:2} °C. Bagian atmosfer ≈ {pct:f.frac}; sisanya dari laut, yaitu entrainment {c.heat_budget.W1.entrainment:2} °C dan upwelling Ekman {c.heat_budget.W1.upwelling:2} °C. Bagian yang benar dari klaim: atmosfer memang ikut mendinginkan, tetapi bukan penyebab utama.",
  evidence: [
    {title: "1 · Budget panas: atmosfer tidak cukup", text: "Bahkan dengan asumsi paling menguntungkan bagi klaim (panas hilang hanya dari lapisan {c.heat_budget.W1.h0_m:0} m), fluks permukaan + hujan menjelaskan {pct:c.heat_budget.W1.frac_atm} pendinginan di W1. Pola serupa di semua titik.", linklab: "lihat budget W1 di deret waktu", point: "W1"},
    {title: "2 · Kolom air terukur berubah", text: "Argo {c.argo_pair.float}: lapisan campuran menebal {c.argo_pair.mld_pre:0} → {c.argo_pair.mld_post:0} m dan SST turun {c.argo_pair.sst_pre:2} → {c.argo_pair.sst_post:2} °C. Hujan dan mendung tidak menebalkan lapisan campuran; angin dan shear yang melakukannya.", linklab: "lihat profil Argo", point: "argo"},
    {title: "3 · Pola ruang mengikuti angin, bukan awan", text: "Jejak dingin terkonsentrasi di bawah tempat siklon diam dan tempat η = ∫w_E dt besar (hingga {c.era5_storm.eta_max_casebox_m:0} m), bukan di seluruh area hujan. Klorofil ikut naik {c.chl.ratio:1}× tepat di jejak itu, tanda air dari bawah naik ke permukaan.", linklab: "buka peta cold wake", layer: "dmin"},
  ],
  h8: `<p>Skenario ini dijawab dengan kerangka yang sama: impuls momentum ∫τ dt ({c.h8.impulse_Nsm2:0} N s m⁻²) dan pengangkatan termoklin η ({c.h8.eta_m:0} m) di W1 seperti saat Seroja, diterapkan pada profil musim timur.</p>
<p>Profil April: <b>{c.h8.src_apr}</b>. Profil Juli: <b>{c.h8.src_jul}</b>.</p>
<p>Pada akhir Juli, SST awal sudah lebih dingin ({c.h8.jul.sst0:1} °C vs {c.h8.apr.sst0:1} °C) dan lapisan campuran lebih tebal ({c.h8.jul.mld0:0} m vs {c.h8.apr.mld0:0} m). Siklon yang sama menurunkan SST {c.h8.jul.dT_mixupw:2} °C, dibandingkan {c.h8.apr.dT_mixupw:2} °C pada April. Pendinginan musim timur sekitar {c.h8.ratio_cooling:2}× pendinginan April.</p>
<p><b>Artinya bagi budidaya:</b> kejutan suhu oleh siklon terbesar ketika laut sedang hangat dan berlapis tipis, yaitu akhir musim barat dan peralihan (Maret–April). Pada musim timur, angin musim sudah mengaduk dan mendinginkan laut, sehingga siklon menambah sedikit pendinginan meski tetap membawa gelombang dan arus kuat.</p>
<p class="small">Catatan keyakinan: jika profil Juli berasal dari Argo yang jauh dari Laut Sawu, hasil ini bersifat indikatif. Profil GLORYS di W1 (bila secret CMEMS tersedia) menggantikannya otomatis.</p>`,
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
