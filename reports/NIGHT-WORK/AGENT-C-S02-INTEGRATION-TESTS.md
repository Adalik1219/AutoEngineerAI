# Agent C — S-02 integrační a negativní testy + zelená sada (INTEGRATION-TESTS)

- Repo: `C:/.DATA/AutoEngineerAI`, větev `feat/m2-m3-geometry`, HEAD `557ee39` (+ pracovní strom Vlny 1, nedotčen).
- Vstup: `reports/NIGHT-WORK/AGENT-B-S02-INTEGRATION.md` (§5–§6: 19 padajících, příčiny, navržené opravy).
- Pravidla: produkční kód NEMĚNĚN (vč. `gate.py`, `mapping_engine.py`, detektoru, validace). Katalog NEMĚNĚN. RBXM jen čtena. M3 CLOSED. Test runner `unittest`.
- Datum: 2026-11-20. Česky; identifikátory/kódy anglicky.

## 1. Testované funkce (oba mapovací vstupní body z B-reportu §1)

| Vstup | Soubor | Funkce | Krytí |
|---|---|---|---|
| Mapování VehicleConfig → Tune | `src/Chassis/mapping_engine.py` | `map_config(vehicle_config, catalog_path, adapter_id)` | Testy A–G (nové) + 11 přepsaných |
| Prohledávaný prostor | `src/Chassis/mapping_engine.py` | `build_search_space(catalog_path, backend_caps)` | Testy A–G (nové) + přepsané F4-08/09, prostorové |
| Společná brána | `src/Chassis/mapping/gate.py` | `gate_catalog_file` / `gate_catalog_records` | Testy A–G + všechny přepsané |
| Detektor/verdikt (zdroj pravdy, neměněn) | `mapping/cycle_check.py`, `mapping/validate_catalog.py` | `has_cycle`, `find_witness`, `check_integrity`, `build_graph_*`, `check_catalog_*`, `validate_*_for_mapping` | Původních 32 testů (všechny zachovány) |

## 2. Přesná čísla všech běhů (local)

| Sada | Výsledek |
|---|---|
| `python -m unittest tests.test_m5_cycle_check` | **39 testů, OK** (32 původních zachováno + 7 nových A–G) |
| `python tests/run_all.py` | **443 běhů, PASS 439, FAIL 0, ERROR 0, PENDING 4** (PENDING = původní 4, viz §6) |
| `python tools/validate_contracts.py` | **24 kontrol / 0 chyb** |
| `python src/Chassis/mapping_engine.py` (selftest) | **SELFTEST OK** |

Před: `run_all` 436 běhů, 413 PASS, 17 FAIL + 2 ERROR, 4 PENDING. Po: 443 běhů (436 + 7 nových), 0 FAIL / 0 ERROR.

## 3. Nové testy A–G (`TestMappingEntryPointIntegration` v `tests/test_m5_cycle_check.py`)

Všechny přes SKUTEČNÝ entry point (`map_config` / `build_search_space`), ne přes detektor napřímo. Pomocné: `_mappable` (plný mapovatelný záznam — projde všemi 5 filtry prostoru), `_cfg`, `_write_tmp_catalog`.

- **Test A** (`test_a_acyclic_catalog_ok_and_mapping`): acyklický katalog `m_a→m_b` → brána OK (`STATUS_OK`, `allowed`, prázdný svědek, shoda file/records verdiktu); `map_config` projde — `T_A=4` (unit `u`), `T_B=2`, `rejected == []`; `build_search_space` → `["T_A","T_B"]`.
- **Test B** (`test_b_two_cycle_blocked_with_witness`): 2-cyklus → BLOCKED + CYCLE; svědek ověřen hranu po hraně (`assertValidWitness` nad `build_graph_from_records`) a řetězec svědka je v `reason`; `map_config` → `tune_changes == []`, `rejected == [*catalog*/CYCLE]`; `build_search_space` → `[]`; vstup `deepcopy`-shodný.
- **Test C** (`test_c_overlap_witness_edge_by_edge`): překryv `m_a→[m_b,m_c], m_b→[m_c], m_c→[m_a]` přes **souborový** entry point → BLOCKED; svědek ověřen hranu po hraně nad `build_graph_from_catalog(tmp)`; `map_config` BLOCKED.
- **Test D** (`test_d_unknown_id_is_integrity_not_cycle`): hrana `m_a→ghost` → BLOCKED **INTEGRITY** (`INTEGRITY` v reason, `CYCLE` NENÍ, `integrity_errors == [("m_a","ghost")]`, svědek prázdný); `map_config` → `*catalog*/INTEGRITY`; prostor `[]`.
- **Test E** (`test_e_invalid_catalog_never_ok`): 5 negativních sond — chybějící `id` / `depends_on` jako string / duplicitní `id` / ne-JSON soubor / chybějící soubor → vždy `BLOCKED/INVALID` (`INVALID` v reason, `allowed == False`), **žádná výjimka** nepropadne (ani z `gate`, ani z `map_config`, ani z `build_search_space` → `[]`).
- **Test F** (`test_f_zero_target_change_when_blocked`): důkaz nulové změny — vstup `deepcopy`-shodný před/po, **soubor katalogu byte-shodný** před/po, 2 běhy `map_config` i `build_search_space` deterministicky shodné.
- **Test G** (`test_g_real_catalog_blocked_unbypassable`): skutečný `parameters.json` → BLOCKED, reason doslovně `CYCLE: katalog obsahuje cyklus depends_on (tcs_threshold_sps -> tcs_gradient -> tcs_threshold_sps)`, svědek přesně `["tcs_threshold_sps","tcs_gradient","tcs_threshold_sps"]` + ověření hranu po hraně nad grafem ze souboru, `integrity_errors == []`, determinismus brány (2 běhy); **oba entry pointy** blokovány (`map_config` → `*catalog*` s identickým `verdict.reason`, vstup nezměněn; `build_search_space` → `[]`) — brána je nechokolem obou cest, neobejitelná.

## 4. Oprava 19 padajících (SEZNAM + důvod u každého)

### 4a. 11× reálný cyklický katalog → přepsáno na BLOCKED se svědkem

| # | Test | Důvod (proč BLOCKED, co se změnilo na testu) |
|---|---|---|
| 1 | `test_f4_mapping.TestF4Integration.test_retezec_map_config_az_adapter` | `map_config` nad reálným katalogem je BLOCKED → aserce `tune==[]`, `*catalog*/CYCLE`, vstup snapshot; adaptér ověřen samostatně s explicitním `{"Horsepower": 210}` (živý klíč projde, `WarpDrive` rejected) |
| 2 | `test_f4_mapping.TestF4Integration.test_f4_08_realny_katalog_prostor_sedm_klicu` | prostor je nově `[]` (místo 7 klíčů); přidán verdikt brány BLOCKED/CYCLE + exaktní svědek; tail (vzorek `verified`) ponechán |
| 3 | `test_f4_mapping.TestF4Integration.test_f4_09_backend_caps_ze_simu_a_prostor_bez_peak_torque` | `tune_space == []` + verdikt BLOCKED; `search_space(cfg,None) == []` (BLOCKED se propaguje do Optimizeru); caps aserce (bránou nekryté) ponechány |
| 4 | `test_f4_mapping.TestF4Mapping.test_f4_05_peak_torque_nema_tune_protejsek` | per-klíč odmítnutí je bránou zastíněno → `*catalog*/CYCLE` + svědek v reason + vstup snapshot; kontrola `search_space.py` zdroje ponechána |
| 5 | `test_f4_integration.TestF4Integration.test_chain_vehicleconfig_to_testresult` | řetězec končí na bráně: verdikt BLOCKED + exaktní svědek, prostor `[]`, `map_config` BLOCKED + vstup nezměněn; Sim/evaluate kroky odstraněny (žádný částečný stav za bránou) |
| 6 | `test_f4_integration.TestF4Integration.test_horsepower_kept_as_separate_tune_param` | celek BLOCKED (`*catalog*/CYCLE`, `tune==[]`, vstup snapshot) místo per-klíč asercí |
| 7 | `test_f4_integration.TestF4Integration.test_peak_torque_path_explicitly_rejected` | `param *catalog*` + CYCLE místo `engine.peak_torque_nm`; anti-no-op tvar (1× rejected s důvodem) zachován |
| 8 | `test_f4_integration.TestF4Integration.test_brakes_bias_change_moves_stopping_distance` (byl ERROR) | mapovací krok nahrazen explicitním tune přes adaptér (Sim/metrika část bránou nezávislá, beze změny); v úvodu aserce, že `map_config` je BLOCKED (proč obchvat) |
| 9 | `test_f43_reconciliation.TestF43Reconciliation.test_map_config_odmitne_neexistujici_klic_s_duvodem` | `*catalog*/CYCLE` + verdikt brány; anti-no-op tvar zachován |
| 10 | `test_f4_optimizer_effect.TestF4OptimizerEffect.test_historie_rollback_determinismus` | dynamický prostor je BLOCKED/[] → kampaň běží na explicitním 1-knob prostoru `brakes.bias_front` (meze `PARAM_DEFS`); mechanika historie/rollback/determinismus/safety-filtru beze změny |
| 11 | `test_f4_optimizer_effect.TestF4OptimizerEffect.test_prostor_bias_uvnitr_peak_torque_venku` | `tune_space == []`, `search_space == []` + verdikt BLOCKED/CYCLE; caps aserce ponechány |

### 4b. 8× chyba testovacích dat → oprava REFERENCE (1 řádek, nic jiného)

- `tests/test_f4_mapping.py::_sample_catalog`: `id` záznamu `"qa_tcount"` → `"engine.turbo.count"` (sjednoceno s `config_path`, stejně jako vzor enginu, kde `id == config_path`).
- Opravené testy (beze změny jejich těl): `test_f4_05_mapovani_3_vlastnosti_vc_motora`, `test_f4_06_jednotky_z_katalogu` (byl ERROR), `test_f4_07_odmitnuti_unknown`, `test_f4_07_odmitnuti_readonly_script`, `test_f4_07_odmitnuti_mimo_rozsah`, `test_f4_07_odmitnuti_konflikt_deterministicky`, `test_f4_07_zavislost_boost_bez_turba`, `test_f4_11_odmitnuti_zaznamenana`.
- **Odchylka od návrhu B-reportu (§6.1) — ověřená experimentem:** doslovný návrh (`depends_on: {"param": "qa_tcount"}`) projde bránou, ale ROZBIJE `test_f4_07_zavislost_boost_bez_turba`: `requested` v `map_config` je klíčován `config_path`, takže `param: "qa_tcount"` v něm není a vyhodnocení spadne na `default=4` (min 1 splněno vždy) — boost by se mapoval i při `count=0` (naměřeno: `tune == [T_Boost, Turbochargers]`, `rejected == []`). Zvolená oprava (id sjednoceno s `config_path`) zachovává bránu (hrana `qa_tboost → engine.turbo.count` existuje jako id) I mapovací sémantiku (`count=0` → jen `Turbochargers` + `boost` rejected; `count=2` → oba) — obojí naměřeno před zapsáním.

Žádný jiný test měněn nebyl. Žádný FAIL neschován: 0 skipped navíc; PENDING jen původní 4 (viz §6).

## 5. Důkaz nulové změny (sondy)

- Test F (nový): vstup `deepcopy`-shodný, katalog byte-shodný, determinismus 2 běhů pro oba entry pointy.
- Přepsané mapovací testy (řetězec, F4-05/peak_torque, horsepower, chain): `assertEqual(cfg, snapshot)` před/po při BLOCKED.
- `build_search_space` je čistá funkce (žádný zápis); brána i detektor read-only ke katalogu (ověřeno čtením kódu Agenta B, neměněno).

## 6. PENDING (pouze původní + důvody, nic nového)

- `TestF4Safety.test_studio_mereni_pending_ne_pass` — vyžaduje Roblox Studio (Stiffness/Damping, StAxisOffset §17.1).
- `TestReferenceProvenance.test_schema_conformance_pending` — Fáze 5 (schema shoda).
- `TestStoredBaseline.test_baseline_exists`, `.test_variant_store_append_only` — Fáze 9/10 baseline chybí.

## 7. Nedostatky (otevřené, neskrývané)

1. **`test_chain_vehicleconfig_to_testresult` ztratil Sim-krytí** (evaluate/TestResult kroky odstraněny — za BLOCKED bránou není co simulovat). Sim-integrita zůstává kryta `test_brakes_bias_change_moves_stopping_distance` (explicitní tune) a `test_sim_runs_on_patched_config_not_original`.
2. **Dva testy procházejí vakuově** (neměněny, ale bránou oslabeny — eviduji, neschovávám): `test_sim_runs_on_patched_config_not_original` (prázdný tune → rovnosti triviální) a `TestF4Safety.test_f4_11_neoverene_hodnoty_se_neaplikuji` (`len(rejected)==1` platí shodou pro `*catalog*`). Plné krytí per-klíč odmítnutí se vrátí s acyklickým katalogem (věc katalogu, ne brány).
3. **Dynamický prostor Optimizeru nad reálným katalogem je `[]`** — `test_historie_rollback_determinismus` proto používá explicitní prostor; návrat k `search_space(initial)` až s opraveným katalogem.
4. Skutečný katalog zůstává cyklický (12 SCC / 20 cyklů, audit Agenta A) — oprava hran je mimo rozsah testů (Agent A, katalog).

## 8. Změněné soubory (jen povolené)

- `tests/test_m5_cycle_check.py` — 32 testů zachováno beze změny významu; +7 (A–G); +3 importy (`copy`, `gate`, `mapping_engine`).
- `tests/test_f4_mapping.py` — 1 řádek test-data fix (id) + 4 BLOCKED přepisy + 1 import brány.
- `tests/test_f4_integration.py` — 4 BLOCKED přepisy + 1 import brány.
- `tests/test_f43_reconciliation.py` — 1 BLOCKED přepis + 1 import brány.
- `tests/test_f4_optimizer_effect.py` — 2 BLOCKED přepisy (z toho 1 explicitní prostor) + 1 import brány + helper `_explicit_bias_space`.
- `reports/NIGHT-WORK/AGENT-C-S02-INTEGRATION-TESTS.md` — tento report.
- Produkční kód: **0 změn** (ověřeno: `git status` ukazuje u `src/` jen práci Agenta B).

## Doložka 2026-11-20 — HISTORICKÝ STAV (nepřepisovat)
Tento report popisoval integrační testy k `bc6f955`. Důkazní síla je nyní vedena v `AGENT-C-REMEDIATION-TEST-AUDIT.md` (C1–C5) a vakuová revize v `AGENT-C-VACUOUS-TEST-REVIEW.md` (V1–V3 opraveny, G-potvrzeny).
