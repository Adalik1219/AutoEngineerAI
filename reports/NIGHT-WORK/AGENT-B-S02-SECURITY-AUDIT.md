# Agent B — S-02: bezpečnostní audit brány a hranice adaptéru

- Větev `wave-b-s02`, HEAD `0f4670a` (rozdíl proti `AGENT-B-S02-INTEGRATION.md`: tam byl
  stav po Z1–Z3 s 19 FAIL; zde je stav po remediaci testů Agentem C — plná sada PASS).
- Rozsah: ČTENÍ vše; ZÁPIS pouze tento report. Produkční kód NEMĚNĚN (žádný patch neaplikován).
- Kontext: reálný katalog `src/Chassis/catalog/parameters.json` je cyklický
  (`tcs_threshold_sps <-> tcs_gradient`); fail-closed BLOCKED je správně.
- Datum: 2026-11-20. Česky; identifikátory anglicky.

## 1. Tabulka VŠECH vstupních cest (žádná bez vysvětlení)

Legenda: „Volá S-02?" = prochází `gate.py` před jakýmkoli výstupem/zápisem.
„Může auto-mapovat?" = umí odvodit `tune_key` změny z `VehicleConfig` cest přes katalog.

| # | Cesta (soubor : funkce) | Volá S-02? | Může auto-mapovat? | Výsledek + vysvětlení |
|---|---|---|---|---|
| 1 | `mapping_engine.py : map_config(vehicle_config, catalog_path, adapter_id)` — veřejný vstup č. 1 | ANO (`_load_catalog` → `_gate_records` → `gate_catalog_records`; chyba načtení → BLOCKED/INVALID; `RuntimeError` při neimportovatelném gate = fail-closed) | ANO (jediná auto-mapující cesta: `config_path → tune_key`) | OK → mapuje (rejected s důvodem, nic tiše); BLOCKED → `tune_changes == []`, `rejected == [{*catalog*, CYCLE/INTEGRITY/INVALID…}]`, vstupní dict nezměněn (ověřeno sondou, §3). Přímé volání `validate_catalog_*`/`cycle_check` z enginu neexistuje (grep). |
| 2 | `mapping_engine.py : build_search_space(catalog_path, backend_caps)` — veřejný vstup č. 2 | ANO (stejná `_gate_records` jako první krok; chyba načtení → `[]`) | NE (neprodukuje `tune_changes`, jen seznam Tune klíčů pro Optimizer; je ale branou chráněn, protože prostor umožňuje downstream ladění) | OK → seřazený prostor (5 filtrů); BLOCKED → `[]` (důvod přes `gate_catalog_file`). Ověřeno sondou (§3). |
| 3 | `Optimizer/search_space.py : search_space(config, plan)` → `_dynamic_specs()` → `build_search_space` | ANO nepřímo (dědí bránu cesty č. 2; nad cyklickým katalogem `tune_keys == []` → `specs == {}`) | NE (prostor, ne zápis) | Při BLOCKED je prostor prázdný — Optimizer nic neladí. Není paralelní cesta bez brány. |
| 4 | `Optimizer/search_space.py : backend_caps(catalog_path)` — čte katalog JSON přímo, BEZ brány | NE (read-only derivace `tune_key` množiny) | NE (nevytváří žádné mapování ani zápis; jen kandidátní množina pro cestu č. 2, kde brána rozhoduje) | Cesta bez brány je přípustná: čistá funkce, katalog nemění, její výstup je bez verdiktu cesty č. 2 bezcenný. Žádné `tune_changes` tudy nevzniknou. |
| 5 | `mapping/gate.py : gate_catalog_file / gate_catalog_records` — samotná brána | JE bránou (pipeline načtení → struktura → integrita → cyklus → OK/BLOCKED; `InvalidGraphError`/`OSError` → BLOCKED/INVALID, nikdy výjimka ven) | NE (jen verdikt, žádné mapování) | Jediné chokepoint API; `gate` neimportuje engine (žádný cyklus importů). |
| 6 | `mapping/validate_catalog.py : validate_catalog_for_mapping / validate_records_for_mapping` — verdikt pod bránou | Součást brány (voláno výhradně z `gate.py`; engine/testy mapování je přímo nevolají — grep) | NE | Rozlišuje CYCLE vs INTEGRITY vs OK; nemění vstup ani katalog. |
| 7 | `mapping/cycle_check.py : check_catalog_*, has_cycle, find_witness, check_integrity, build_graph_*` — detektor (zdroj pravdy, NEMĚNĚN) | Součást brány (voláno z `validate_catalog.py`); testy ho volají přímo, ale jen read-only aserce | NE | Přímé volání z enginu neexistuje. `find_cycles()` = DEPRECATED wrapper (negarantuje všechny cykly) — nikdo v produkční cestě ho nevolá. |
| 8 | `adapters/achassis_v1.py : AChassisV1Adapter.apply_config(model_copy_dir, config)` — hranice, viz §2 | NE (ověřeno: soubor neimportuje `gate` ani katalog; grep negativní) | NE (nečte `parameters.json`, netraverzuje `depends_on`, nepřekládá `config_path → tune_key`; zapisuje jen explicitně předané `config["parameters"]["tune"]` klíče s `mutable == True`, ostatní → `rejected` s důvodem) | Interní downstream nástroj (Varianta A, §2). Sonda: přímý `tune = {Horsepower: 210}` se aplikuje i bez brány — to je očekávané chování downstreamu, ne obchvat (brána chrání auto-map, viz rozhodnutí). Vstup nemutuje (pracuje nad `deepcopy`). Chování NEMĚNĚNO. |
| 9 | `Chassis/registry.py : get_adapter / list_adapters / is_ready`, `base.py : ChassisAdapter` (rozhraní) | NE (jen továrna/interfejs, žádné čtení katalogu) | NE | Nemapují, nezapisují. `_adapter_warning` v enginu je best-effort varování, ne brána. |
| 10 | `run_selftest` (engine i adaptér), interní pomocné (`_load_catalog`, `_norm_entry`, `_check_depends`, `_resolve_entry`) | Selftesty procházejí bránou (engine selftest používá acyklický vzorek → OK); pomocné jsou volány až PO verdiktu OK (kromě `_load_catalog`, který je read-only načtení PŘED bránou) | NE samostatně (jen uvnitř cest č. 1–2) | Selftest enginu: SELFTEST OK (acyklický vzorek, brána propouští). |

Závěr tabulky: neexistuje produkční cesta, která by z `VehicleConfig` odvodila Tune změny
mimo bránu. Jediné čtení katalogu mimo bránu (cesta č. 4) neprodukuje mapování.

## 2. Hranice `apply_config`: rozhodnutí Varianta A (beze změny chování)

**Rozhodnuto: Varianta A — `apply_config` je interní downstream nástroj, testy ho izolují.**
(NE Varianta B — adaptér za bránu nepatří.)

Důvody (ověřeno čtením kódu + sondou):
1. Adaptér nikdy nevidí katalog ani graf závislostí — nemá `catalog_path` v signatuře
   (`apply_config(model_copy_dir, config)` je zmrazené API Agenta D). Bránu by nebylo kam
   připojit bez změny smlouvy → B by znamenala změnu chování (zakázáno).
2. Adaptér nic neodvozuje: `tune` klíče v `config["parameters"]` jsou explicitní požadavek,
   ne výsledek traversálu `depends_on`. S-02 chrání právě automatické odvozování.
3. Řetězec je krytý shora: `map_config` (s bránou) → `tune_patch` → `apply_config`.
   Při BLOCKED je `tune_patch == {}` → `applied == []`, `patched_config` identický se vstupem
   (požadavek na test izolace, §4 bod 8).
4. Sonda potvrzuje absenci skryté vazby: `achassis_v1.py` neobsahuje `gate` ani `parameters.json`.

Akceptované riziko (bez patch-návrhu — není to nedostatek brány):
ručně sestavený `tune` dict aplikovaný přímo přes `apply_config` obchází `depends_on`
pořadí. Mitigace je procesní: Engineering vrstva volá vždy `map_config` nejdřív;
adaptér je vlastnictví Agenta D a jeho smlouva (odmítnout unknown/read-only s důvodem) platí.

## 3. Fail-closed: vlastní sondy (běh 2026-11-20, Python 3.14.9, worktree `C:/.DATA/AE-WORK-B`)

Reálný katalog: `gate_catalog_file` → **BLOCKED**,
`CYCLE: katalog obsahuje cyklus depends_on (tcs_threshold_sps -> tcs_gradient -> tcs_threshold_sps)`,
`witness_path == ["tcs_threshold_sps", "tcs_gradient", "tcs_threshold_sps"]` (uzavřená cesta,
hrany v datech), `integrity_errors == []`, `allowed == False`.

| Případ | Oba entry pointy | Nezměněný cíl (kopie před/po) |
|---|---|---|
| CYCLE (reálný katalog) | `map_config` → `tune_changes == []`, `rejected[0].param == "*catalog*"`, reason obsahuje CYCLE + svědek; `build_search_space` → `[]` | `cfg == deepcopy(cfg)` před/po: ANO; 2 běhy deterministicky shodné; soubor katalogu byte-shodný (sha před/po shoda) |
| INTEGRITY (syntetika `a -> ghost`) | `gate_catalog_records` → BLOCKED, reason `INTEGRITY: … (a -> ghost)`, `integrity_errors == [("a","ghost")]`, reason bez "CYCLE" | N/A (verdiktová vrstva, vstupní records neměněny) |
| INVALID (chybějící soubor; záznam bez `id`) | `gate_catalog_file("neexistuje.json")` → BLOCKED/INVALID bez výjimky; `map_config` → `*catalog*` + INVALID; `build_search_space` → `[]` | ANO (žádná výjimka, žádný částečný stav) |
| Neurčitelný stav (ne-JSON soubor) | BLOCKED/INVALID (kryto testy C, bod 5 v §4) | ANO |

## 4. Požadavky na testy pro Agenta C (SEZNAM — testy nepíšu, kód neměním)

Stav: Agent C remediaci již provedl (`0f7c968`; plná sada PASS, §5). Níže je seznam
požadavků, které musí zůstat trvale kryty (soubor, případ, očekávání):

1. `tests/test_m5_cycle_check.py :: TestMappingEntryPointIntegration.test_a_acyclic_catalog_ok_and_mapping`
   — acyklický katalog → `gate` OK/allowed; `map_config` mapuje obě hodnoty; `build_search_space` vrací oba klíče.
2. `…test_b_two_cycle_blocked_with_witness` — 2-cyklus → BLOCKED/CYCLE + uzavřený svědek
   (hranu po hraně); `map_config` `tune_changes == []`, `rejected[0].param == "*catalog*"`;
   `build_search_space == []`; vstup `deepcopy`-shodný.
3. `…test_c_overlap_witness_edge_by_edge` — překryvový graf → BLOCKED, svědek platná uzavřená cesta.
4. `…test_d_unknown_id_is_integrity_not_cycle` — hrana na `ghost` → BLOCKED/INTEGRITY
   (reason bez "CYCLE"), `integrity_errors == [("m_a","ghost")]`; oba entry pointy prázdné.
5. `…test_e_invalid_catalog_never_ok` — chybějící `id` / špatný typ / duplicitní `id` /
   ne-JSON / chybějící soubor → vždy BLOCKED/INVALID, nikdy výjimka, oba entry pointy prázdné.
6. `…test_f_zero_target_change_when_blocked` — při BLOCKED: vstup shodný, katalog byte-shodný,
   2 běhy identické.
7. `…test_g_real_catalog_blocked_unbypassable` — reálný `parameters.json` → BLOCKED/CYCLE
   s přesným svědkem `tcs_threshold_sps -> tcs_gradient -> tcs_threshold_sps`; OBA entry pointy blokovány.
8. `tests/test_f4_integration.py` — řetězec `map_config → apply_config` nad BLOCKED-výstupem:
   `applied == []`, `patched_config` identický se vstupem (izolace adaptéru, Varianta A).
9. Slovníkové závislosti `{"param": <id>, …}` vstupují do grafu (cyklus přes ně detekován);
   slovník bez `param` → BLOCKED/INVALID (regrese `_normalize_for_detector`).
10. `gate` neimportovatelný → `map_config`/`build_search_space` vyhodí `RuntimeError`
    (fail-closed), nikdy nemapují.

## 5. Čísla + prostředí (běh 2026-11-20, `C:/.DATA/AE-WORK-B`)

- `python tests/run_all.py` → **443 běhů, PASS 438, FAIL 0, ERROR 0, PENDING 5** → VÝSLEDEK: PASS.
  PENDING (5, mimo rozsah S-02): Studio-měření, druhá M2 kopie, schema-conformance Fáze 5,
  2× regresní baseline Fáze 9/10.
- `python tools/validate_contracts.py` → **24 kontrol, 0 chyb** → ÚSPĚCH.
- `python src/Chassis/mapping_engine.py` (selftest, acyklický vzorek) → SELFTEST OK.
- Prostředí: Python 3.14.9, Windows, worktree větev `wave-b-s02`, HEAD `0f4670a`.
  Hlavní klon `C:/.DATA/AutoEngineerAI` nedotčen. Katalog/RBXM/main/PR#2 tabu — nedotčeno.
  M3 CLOSED (Mustang mimo rozsah).

## 6. Změny, patch-návrhy, rizika

- **Změny produkčního kódu: ŽÁDNÉ** (audit je read-only; jediný zápis je tento report).
- **Patch-návrhy: ŽÁDNÉ** (brána je kompletní; adaptér se nemění rozhodnutím §2).
- Rizika: (a) oprava 12 katalogových cyklů je věcí katalogu (Agent A), ne brány — brána se
  NEobchází; (b) `backend_caps` čte katalog mimo bránu — přípustné (§1 cesta č. 4);
  (c) přímé `apply_config` s ručním `tune` obchází `depends_on` — akceptováno procesně (§2).

## 7. Závěr

**Závěr: PASS.** Všechny auto-mapující cesty procházejí bránou S-02; CYCLE / INTEGRITY /
INVALID / chyba načtení či validace grafu končí fail-closed BLOCKED s přesným důvodem a nulovou
změnou cíle (ověřeno vlastními sondami na obou entry pointech); hranice adaptéru je
rozhodnuta jako Varianta A beze změny chování; plná sada 443/0/0/5 + kontrakty 24/0.
