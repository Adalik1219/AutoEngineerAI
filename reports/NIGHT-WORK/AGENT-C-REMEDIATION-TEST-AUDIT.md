# Agent C — Remediation Test Audit (důkazní síla C1–C5)

- Větev: `wave-c-tests`, workdir `C:/.DATA/AE-WORK-C`, base HEAD `0f4670a`.
- Prostředí: Windows 11 (10.0.26300), CPython 3.14.9, test runner `unittest` (stdlib), Sim seed 7.
- Rozsah zápisu dodržen: změněny POUZE `tests/test_f4_integration.py`,
  `tests/test_f4_mapping.py` + tento report. Produkční kód, katalog, RBXM, `main`/PR#2 nedotčeny.
- Stav M3: CLOSED (žádný zásah do M3).

## C1 — per-parametrické odmítnutí (NOVÝ test, skutečný PASS)

Test: `tests/test_f4_mapping.py::TestF4Mapping::test_f4_07_per_param_rejection_acyclic_fixture` — PASS.

- Architektura per-parametrické odmítnutí UMÍ (ověřeno během na acyklické fixture),
  takže test je plnohodnotný PASS, ne dokumentující PENDING.
- Fixture: `_sample_catalog()` (8 záznamů), bránou předem ověřena jako
  `allowed` — měří se tedy skutečně per-klíč odmítnutí, ne katalog-BLOCKED.
- Vstup: horsepower 210 + final_drive 3.2 + bias_front 0.62 (vše validní) + warp_drive 5.
- Výsledek: `tune_changes` == přesně {Horsepower, FinalDrive, Bias} (validní NEblokovány);
  `rejected` == právě 1: `param == "engine.warp_drive"`,
  důvod `"kategorie UNKNOWN: engine.warp_drive -> WarpDrive se nemapuje
  (change_method=pending-studio; ...)"` — konkrétní, obsahuje `pending-studio`,
  neobsahuje `CYCLE`, `param != "*catalog*"`. Odmítnutý klíč neunikl do `tune_changes`;
  vstupní dict nezměněn; opakování dává bitově identické JSON.
- Chytá: (a) tiché zahození validních parametrů s nevalidním, (b) důvod-less nebo
  bránou zastíněné odmítnutí, (c) mutaci vstupu, (d) únik odmítnutého do tune.
- Bez klíčových asercí by falešně PASoval při prázdném `tune_changes` nebo při BLOCKED.

## C2 — Sim běží nad patchnutou konfigurací (zpevněn, 12 kroků)

Test: `tests/test_f4_integration.py::TestF4Integration::test_sim_runs_on_patched_config_not_original` — PASS.

- RAW: `patched==captured: True; captured!=original: True; bias captured=0.7 original=0.62`.
- Klíčová změna proti předchozí verzi: originál má bias **0.62** (záměrně odlišný od cíle
  0.70 — předtím byl originál i cíl 0.70, takže záměna nebyla detekovatelná), patch
  jde explicitně přes adaptér (`tune: {BrakeBias: 0.70}`), zachycuje se přesný obsah
  souboru předaného Simu (`captured`) a test SELŽE při předání originálu
  (negativní kontrola `captured != original` + bias 0.70 ≠ 0.62).
- Rozsah přesně zdokumentován v docstringu: **downstream-izolace (adaptér → Sim),
  NE důkaz mapování přes S-02** (map_config je za reálným katalogem BLOCKED; tune se
  staví explicitně). Mapování kryjí C1/C4. Metriky sekundární (`t_0_100_s` jen existence).
- Determinismus: stejný seed + stejný vstup → stejný zachycený obsah.

## C3 — FinalDrive fixture bez křehkých hran (přepsán)

Test: `tests/test_f4_integration.py::TestF4Integration::test_final_drive_change_moves_metric_or_unsupported` — PASS.

- RAW: `fd 2.6 -> t_0_100 9.528 s (v_max 123.8 km/h); fd 3.2 -> t_0_100 9.160 s (v_max 131.6 km/h)`.
- Ruční seznam ~40 cyklových hran ODSTRANĚN. Fixture je deterministická (2 pevné literály:
  FinalDrive [2.5, 4.2] + BrakeBias [0, 1], MUTABLE_TUNE/PASS/used_in, žádné hrany,
  žádné čtení reálného katalogu) + **auto-validace**: integrita hran explicitně
  + `gate_catalog_file(fixture)` musí být `allowed`, jinak FAIL s důvodem brány (NE tichý PASS).
- Řetězec: map 2.6/3.2 → přesně 1 `tune_change` FinalDrive se správnou hodnotou, `rejected == []`
  → adaptér `applied == fd`, `rejected == []` → Sim-vstup `final_drive` 2.6/3.2
  → `|t_hi − t_lo| > 0.05` s (jinak FAIL s konkrétními čísly). Determinismus mapování
  2.6 → identické JSON. Nelze-li fixture sestavit → FAIL s důvodem, nikdy falešný PASS.

## C4 — reálný katalog BLOCKED-CYCLE (zachováno, vše PASS)

- `test_chain_vehicleconfig_to_testresult` (S-02 BLOCKED + svědek `tcs_threshold_sps -> tcs_gradient -> tcs_threshold_sps`, nulová změna) — PASS.
- `test_peak_torque_path_explicitly_rejected` (*catalog*/CYCLE) — PASS.
- `test_horsepower_kept_as_separate_tune_param` (žádný částečný stav) — PASS.
- `test_f4_mapping.py`: `test_f4_05_peak_torque_nema_tune_protejsek`,
  `test_retezec_map_config_az_adapter`, `test_f4_08_realny_katalog_prostor_sedm_klicu`,
  `test_f4_09_backend_caps_ze_simu_a_prostor_bez_peak_torque` — vše PASS.

## C5 — audit každého upraveného testu

| Test | Jakou chybu odhalí | Falešný výsledek bez klíč. asercí | Bránící aserce | Determinismus | Skip / slabá podmínka | Konkrétní důvod |
|---|---|---|---|---|---|---|
| C1 per-param (nový) | tiché zahození validních; důvod-less odmítnutí; mutace vstupu; únik do tune | PASS při prázdném tune_changes / BLOCKED | gate allowed + přesně 1 rejected + přesná množina tune_changes + snapshot vstupu + repeat-JSON | opakováním identické JSON | žádný skip; samé konkrétní hodnoty | `kategorie UNKNOWN ... pending-studio`, param `engine.warp_drive` |
| C2 patched-vs-original | Sim nad originálem; mutace originálu; ztráta tune | PASS i při čtení originálu (dřív bias 0.70 == 0.70) | captured == sim_cfg + captured != original + bias 0.70 ≠ 0.62 | seed 7 + JSON round-trip | žádný skip; None jen sekundární | bias 0.7 vs 0.62, `tune` přítomnost |
| C3 final_drive | necitlivost Simu na fd; prázdné mapování; zastaralá fixture | PASS při ignorovaném fd / BLOCKED fixture | přesné tune_changes + práh 0.05 s s čísly + gate allowed | repeat-JSON + seed | žádný skip | `t_lo/t_hi` hodnoty, reason brány |

## Výsledky běhů

- `python -m unittest tests.test_f4_mapping tests.test_f4_integration`: **36 testů, OK (skipped=1)** —
  skip je `test_studio_mereni_pending_ne_pass` (PENDING: vyžaduje Roblox Studio).
- `python tests/run_all.py`: **běhů=444 PASS=439 FAIL=0 ERROR=0 PENDING=5** — všech 5 PENDING
  pre-existing a zdokumentovaných (Studio-měření; M2 druhá kopie; reference schema Fáze 5;
  2× regresní baseline Fáze 9/10). Žádný nový PENDING, žádný nový skip.
- `python -m unittest tests.test_module_contracts`: **45 testů, OK (skipped=1)** (pre-existing PENDING).

## PENDING

Žádný PENDING nepřibyl. Jediné Studio-nedostupné místo zůstává `test_studio_mereni_pending_ne_pass`
(skip s důvodem, nikdy PASS) — beze změny.

## SHA a závěr

- Base HEAD: `0f4670a`; remediation commit: `c(tests): dukazni sila C1-C3 + audit`
  na větvi `wave-c-tests` (jen 3 povolené soubory; finální SHA viz `git log -1`).
- **Závěr: PASS** — důkazní síla C1 (nový per-klíč test, skutečný PASS), C2 (negativní kontrola
  originál-vs-patched, rozsah downstream-izolace), C3 (deterministická fixture + auto-validace
  brány, bez ručních hran) dodána; C4 BLOCKED-CYCLE testy zachovány zelené; C5 audit výše.
