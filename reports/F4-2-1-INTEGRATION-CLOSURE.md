# F4-2-1 Integration Closure — Agent D (nezávislé QA)

**Vlastník:** Agent D, FÁZE 4.2.1. Vlastněný soubor: `reports/F4-2-1-INTEGRATION-CLOSURE.md`.
**Datum:** 2026-11-17. Česky; identifikátory anglicky. Pouze stdlib. Žádné kódové změny, žádné zapisující git operace (pouze read-only `git status --short` dle AGENT-RULES §5).
**Metoda:** vlastní běhy + čtení kódu; tvrzení vln 1 (A/B/C) nepřevzata. PENDING ≠ PASS.

## Verdikt po 8 bodech

| # | Bod | Verdikt |
|---|-----|---------|
| 1 | patched_config vstupuje do Simu (vlastní běh: změna biasu, Sim četl změněnou hodnotu) | **PASS** |
| 2 | Rozdíl původní vs změněná konfigurace v telemetrii (before/after čísla) | **PASS** |
| 3 | Odezva relevantní metriky na podporovaný parametr (bias→brzda, final_drive→akcelerace/V-max) | **PASS** |
| 4 | Nepodporované (peak_torque_nm) mimo prostor + odmítnuty | **PASS** |
| 5 | Žádná vymyšlená unknown (spot-check katalogu) | **PASS** |
| 6 | sha256 chasis.rbxm + Simulator status prázdný | **PASS** |
| 7 | tests/run_all.py 0 FAIL (vlastní běh) | **PASS** |
| 8 | Shrnutí co funguje / ne / PENDING | viz níže |

## Raw výstupy (vlastní běhy, 2026-11-17)

**B1 — Sim čte patched hodnotu** (`tests/test_f4_integration.py:91-113` projekce `sim_input_from_patched`, běh přes `src/Sim/run.py:run_scenario`):
`disk-bias: 0.62 | patched-tune-Bias: 0.62 | shoda: True` — hodnota zapsaná na disk a čtená Simem (`parameters.brakes.bias_front`) se rovná aplikovanému Tune patchi, nikoli továrnímu vstupu (ten `tune` vůbec neobsahuje).

**B2 — before/after brzda** (scénář `straight_brake_100_0`, seed 7, reálný Sim):
`brake_distance_100_0_m: 0.62 → 46.000 m; 0.70 → 51.842 m; diff = 5.842 m` (práh testu 1.0 m splněn s rezervou).

**B3 — odezva metrik** (scénář `straight_accel`, seed 7, reálný Sim):
`final_drive 2.6 → t_0_100 9.548 s, v_max 123.8 km/h; 3.2 → 9.164 s, 131.6 km/h` (Δt = 0.384 s > práh 0.05 s).

**B4 — peak_torque odmítnut:** `tune_changes: [] | rejected: [('engine.peak_torque_nm', "neznámý parametr: katalog neobsahuje záznam …")]`; prostor `search_space` = `['brakes.bias_front']`, `backend_caps` = `['Bias','BrakeForce','FinalDrive','IdleRPM','Ratios','Redline']` — torque v žádném z nich.

**B5 — katalog:** 125 záznamů, 79 MUTABLE_TUNE, **27 UNKNOWN**; spot-check `suspension.anchor_offset` (UNKNOWN, PENDING) → `rejected` s důvodem kategorie, nic nevymyšleno. `engine.peak_torque_nm` nemá v katalogu **žádný** záznam. `Bias` (`brake_bias_front → brakes.bias_front`, MUTABLE_TUNE, PASS, min 0 max 1) je jediný plně ověřený rozsah.

**B6 — integrita:** `sha256sum C:/Users/adamr/Downloads/chasis.rbxm = dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf` — **shoda**; `git -C C:/.DATA/RobloxSimulator status --short` — **prázdný** (read-only ověření).

**B7 — plná sada** (vlastní běh `python tests/run_all.py`): `behu=141 PASS=137 FAIL=0 ERROR=0 PENDING=4` → **0 FAIL**. 4 PENDING (ne PASS): `test_studio_mereni_pending_ne_pass` (vyžaduje Roblox Studio), `test_schema_conformance_pending` (Fáze 5), `test_baseline_exists` + `test_variant_store_append_only` (baseline Fáze 9/10 neexistuje).

## Co funguje / co ne / PENDING

- **Funguje:** řetězec VehicleConfig → map_config → adapter.apply_config → patched_config → Sim → TestResult; bias hýbe brzdnou dráhou v reálném i fallback Simu (fallback: 5/5 párovaných běhů, p~0.03); final_drive hýbe akcelerací/V-max; nepodporované parametry končí v `rejected` s důvodem; determinismus + append-only historie + rollback ověřeny (F4-C stub-kampaň: best_bias 0.61, CONVERGED).
- **Nefunguje / omezeno:** z 6 backend-podporovaných Tune klíčů je laditelný **pouze Bias** — `BrakeForce, FinalDrive, Ratios, IdleRPM, Redline` mají `min/max: null` (ověřeno čtením katalogu), takže je `build_search_space` vyřadí a `search_space` vrací jen `brakes.bias_front`. Kalibrační optimum biasu 0.60 platí jen pro fallback model, ne pro reálný Sim.
- **PENDING (4):** viz B7; žádný neblokuje uzávěrku F4-2-1, všechny patří pozdějším fázím.

## Zbytkové vady (soubor:řádka)

1. `src/Optimizer/search_space.py:116-125` — `PARAM_DEFS["transmission.final_drive"]` nese pevné meze 2.5–4.2, ale katalogový záznam `FinalDrive` má `min/max null`; `_dynamic_specs` (`:74-106`) je proto nikdy nepoužije (meze bere z katalogu) — mrtvá jistota v komentáři `:108-111`, matoucí pro F4.3.
2. `src/Optimizer/search_space.py:40-48` — `SIM_SUPPORTED_CONFIG_PATHS` obsahuje `engine.peak_torque_nm`/`engine.peak_power_kw` jako „Sim čte", ale katalog k nim nemá záznam ani Tune protějšek (MAPPING.md §6/1) — množina slibuje víc, než mapování umí doručit.
3. `tests/test_f4_integration.py:91-113` — `sim_input_from_patched` je test-side projekce `tune → config_path`, nikoli produkční kód; řetězec je uzavřen jen potud, pokud produkce tutéž projekci převezme (wiring F4.3).

## Doporučení pro F4.3

1. Kalibrovat Studio sweepy S1+S9 pro 5 neladitelných klíčů v pořadí **FinalDrive → BrakeForce → Redline → IdleRPM → Ratios** (postup viz `reports/F4-3-CALIBRATION-BACKLOG.md`); každý ověřený rozsah zapsat do katalogu (`min/max` + PASS), prostor se rozšíří automaticky bez změny kódu.
2. Rozhodnout osud `PARAM_DEFS` final_drive mezí: buď doložit zdrojem měření, nebo smazat a nechat jediný zdroj v katalogu.
3. Povýšit projekci `tune → config_path` z test-helperu do produkčního `mapping_engine`/adaptéru, ať Sim-doručení negarantuje jen test.
4. Kalibrační optimum biasu přeměřit na reálném Simu (0.60 je artefakt fallback modelu).
