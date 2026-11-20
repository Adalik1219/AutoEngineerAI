# Agent B — S-02: brána do SKUTEČNÉHO mapovacího entry pointu (INTEGRATION)

- Repo: `C:/.DATA/AutoEngineerAI`, větev `feat/m2-m3-geometry`, HEAD `557ee39` (+ soubory Vlny 1, nedotčeny).
- Vstupy: `reports/NIGHT-WORK/AGENT-A-S02-CATALOG-AUDIT.md` + `AGENT-A-CATALOG-REMEDIATION.md`
  (12 SCC, 101 hran, 0 real-cyklů / 12 model-chyb — brána nerozhoduje o vině, jen blokuje),
  `src/Chassis/mapping/{cycle_check,validate_catalog,dependencies}.py`, `src/Chassis/catalog/loader.py`.
- API detektoru (`cycle_check`) ani `validate_catalog.py` NEMĚNĚNY — pouze používány.
  `parameters.json` NEMĚNĚN. Testy NEMĚNĚNY. RBXM/Simulator nedotčeny (read-only).
- Datum: 2026-11-20. Jazyk: čeština; identifikátory/kód anglicky.

## 1. Skutečný produkční entry point (nalezen prohledáním repa, ne podle jména)

| Vstup | Soubor | Funkce | Vstupní body (parametry) |
|---|---|---|---|
| Mapování VehicleConfig → Tune | `src/Chassis/mapping_engine.py` | `map_config(vehicle_config, catalog_path, adapter_id) -> dict` | `vehicle_config` (dict s `parameters`), `catalog_path` (cesta k `parameters.json`), `adapter_id` (registr) |
| Prohledávaný prostor pro optimalizaci | `src/Chassis/mapping_engine.py` | `build_search_space(catalog_path, backend_caps) -> list[str]` | `catalog_path`, `backend_caps` (list Tune klíčů backendu) |

- Zmrazené API (neměněno): `map_config`, `build_search_space`, `run_selftest` (`__all__` beze změny).
- Jediná čtecí cesta katalogu v enginu: `_load_catalog` (list i obálka `{"parameters": [...]}`).
- Jediná zapisující/mutační vrstva pod mapováním: `AChassisV1Adapter.apply_config`
  (`src/Chassis/adapters/achassis_v1.py`, vlastník Agent D — **neměněno**; adaptér konzumuje
  výstup `map_config`, takže zablokované mapování = nic k aplikaci = nic k patchi).
- `dependencies.py` (`KNOWN_DEPENDS`/`KNOWN_CONFLICTS`) NENÍ vstup mapování — engine čte
  `depends_on`/`conflicts` přímo z katalogu (tabulky kryjí ~1 % hran, viz audit Agenta A §7).

## 2. Změny (3 soubory; katalog, detektor, testy nedotčeny)

### Z1 — NOVÝ `src/Chassis/mapping/gate.py` (společná bezpečná funkce)
- **Proč:** dosud žádná cesta neměla bránu; `map_config`/`build_search_space` mapovaly i nad
  cyklickým katalogem. Všechny veřejné vstupy musí procházet jedním místem —
  žádná paralelní validace, žádná cesta bez brány.
- **Co řeší:** jediné chokepoint API: `gate_catalog_file(path)` / `gate_catalog_records(records)`
  → `MappingCatalogVerdict` (OK/BLOCKED + přesný důvod + svědek/hrany). Pořadí:
  načtení → struktura → integrita → detekce cyklu → OK/BLOCKED (delegací na
  `validate_catalog_for_mapping` / `validate_records_for_mapping`, zdroj pravdy se nemění).
  Chyby načtení/struktury (`InvalidGraphError`, `OSError`, ne-JSON) se NEpropagují jako
  výjimka, ale vracejí BLOCKED/INVALID — volající mapovací cesty tak vždy končí
  atomicky (nulová změna), nikdy pádem uprostřed.
- **Rozhodnutí k zaznamenání:** `mapping_engine._check_depends` podporuje v `depends_on`
  i slovníkové závislosti `{"param": <id>, "min"/"max"/"equals": …}`. `_normalize_for_detector`
  je promítá na hrany `id -> param` (podmínka `min/max/equals` existenci hrany nemění),
  takže vstupují do detekce cyklu i integrity — **nejsou slepou cestou mimo bránu**.
  Chybějící `depends_on`/`None` = `[]` (shodně s `_norm_entry` v enginu). Čistě řetězcové
  katalogy (včetně skutečného `parameters.json`) procházejí beze změny (stejný svědek).
- **Test pro C (předej):** `gate_catalog_records` nad acyklickým vzorkem → OK/allowed;
  nad 2-cyklem → BLOCKED/CYCLE + platný uzavřený svědek (hranu po hraně); nad `a -> ghost`
  → BLOCKED/INTEGRITY (reason bez "CYCLE") + `integrity_errors == [("a","ghost")]`;
  nad duplicitním id / ne-JSON / chybějícím souborem → BLOCKED/INVALID (žádná výjimka);
  slovníková závislost `{"param": "qa_tcount"}` → hrana v grafu (cyklus přes ni detekován),
  slovník bez `param` → BLOCKED/INVALID; vstupní `records` po bráně nezměněny.
- **Rollback:** smazat soubor + revert Z2 (níže); nic jiného na něm nezávisí.
- **Vliv:** pouze nová závislost `mapping_engine` → `gate` → `validate_catalog`/`cycle_check`
  (žádný cyklus importů: `gate` neimportuje engine). `mapping/__init__.py` neměněn.

### Z2 — `src/Chassis/mapping_engine.py` (brána v obou veřejných vstupech)
- **Proč:** brána musí stát PŘED každou mutací/výstupem/zápisem; jediná paralelní cesta
  ( byť jen čtení-then-mapování bez kontroly) by rušila záruku.
- **Co řeší:** `map_config`: jako první krok načte katalog (`_load_catalog`; chyba →
  BLOCKED/INVALID), pak `_gate_records` (společná funkce ze Z1); při BLOCKED vrací
  `_blocked_mapping(verdict.reason)`: `tune_changes == []`, `rejected == [{param:
  "*catalog*", reason: "mapování zablokováno bránou S-02: <CYCLE|INTEGRITY|INVALID…>"}]`,
  vstupní `vehicle_config` nezměněn (funkce vstup nikdy nemutovala — jen čte), žádný
  částečný stav. `build_search_space`: stejná brána jako první krok; při BLOCKED vrací `[]`
  (nulový prostor; přesný důvod přes `gate_catalog_file`, viz docstring). Odstraněno
  duplicitní druhé čtení katalogu ve smyčce (`for raw in raw_records`).
- **Test pro C (předej):** BLOCKED: `map_config` nad cyklickým katalogem → `tune_changes == []`,
  `rejected[0].param == "*catalog*"`, reason obsahuje "CYCLE" + svědek, `deepcopy` vstupu
  beze změny (2× volání → identický výsledek); `build_search_space` nad cyklickým →
  `[]`; nad katalogem s `ghost` hranou → BLOCKED/INTEGRITY; nad acyklickým vzorkem se
  slovníkovou závislostí → OK a mapování beze změny chování (viz Z1). Negativní probe:
  záměrně cyklický katalog NESMÍ projít (status BLOCKED, ne OK).
- **Rollback:** revert tohoto souboru na HEAD (brána je aditivní; zmrazené signatury
  `map_config`/`build_search_space`/`run_selftest` nedotčeny).
- **Vliv:** všichni konzumenti enginu (`tests/*`, `Optimizer/search_space.py` přes
  `build_search_space`, adaptér přes výstup `map_config`) dostanou při BLOCKED prázdný
  výstup místo mapování — viz §5 (očekávané, správné; testy opravuje C).

### Z3 — `docs/MAPPING.md` (§10, vlastněný soubor)
- **Proč:** dokumentace musí pravdivě popisovat chování bran (vlastník souboru: Agent B).
- **Test pro C:** žádný (dokumentace). **Rollback:** smazat §10. **Vliv:** žádný běhový.

## 3. Chráněné cesty (všechny přes společnou funkci — ověřeno čtením kódu)
- `map_config` → `_gate_records` → `gate_catalog_records` (jediná cesta; přímé volání
  `validate_catalog_*`/`cycle_check` z enginu neexistuje).
- `build_search_space` → `_gate_records` → `gate_catalog_records` (dtto).
- `gate_catalog_file` (pro externí volající: testy C, budoucí wiring D) → tatáž pipeline.
- `_gate_records` při neimportovatelném `gate` modulu vyhazuje `RuntimeError`
  ("bez brány se nesmí provést") — fail-closed, ne fail-open.

## 4. Výsledek reálného katalogu přes bránu (MUSÍ být BLOCKED — je to správně)
- `gate_catalog_file("src/Chassis/catalog/parameters.json")` →
  **BLOCKED**, `CYCLE: katalog obsahuje cyklus depends_on
  (tcs_threshold_sps -> tcs_gradient -> tcs_threshold_sps)`,
  `witness_path == ["tcs_threshold_sps", "tcs_gradient", "tcs_threshold_sps"]`
  (uzavřená cesta, hrany ověřeny v datech; shoda s auditem Agenta A, cyklus č. 1;
  `checked_nodes == 138`, `checked_edges == 101`, `integrity_errors == []`).
- `map_config(cfg_horsepower210, real, "achassis-v1")` → `tune_changes == []`,
  `rejected == [*catalog*: …CYCLE…]`; vstupní dict beze změny (`deepcopy` shoda).
- `build_search_space(real, [...])` → `[]`.
- Důvod, proč se brána NEobchází: 12 SCC / 20 jednoduchých cyklů v datech (§5 auditu A);
  mapování nad cyklem by produkovalo nedefinované pořadí aplikace. Oprava hran je
  věcí katalogu (návrhy Agenta A), ne brány.

## 5. Čísla testů (prostředí = local; před → po)
| Sada | Před | Po |
|---|---|---|
| `python -m unittest tests.test_m5_cycle_check` (32 testů) | 32 OK | **32 OK** (detektor/verdikt nedotčeny) |
| `python tools/validate_contracts.py` | 24 kontrol / 0 chyb | **24 / 0** |
| `python tests/run_all.py` | 436 běhů, PASS 432, FAIL 0, ERROR 0, PENDING 4 | **436 běhů, PASS 413, FAIL 17, ERROR 2, PENDING 4** |
| `python src/Chassis/mapping_engine.py` (selftest, acyklický vzorek) | SELFTEST OK | **SELFTEST OK** |

- 19 nových FAIL/ERROR = **výhradně efekt brány** (žádná regrese logiky):
  brána nikdy nevyhazuje (oba ERRORy jsou `StopIteration`/`KeyError` v testech nad
  prázdným `tune_changes`, tj. důsledek BLOCKED, ne pád brány).
- Rozpad 19 (pro C — přesný seznam k opravě, testy píše C):
  - **11× reálný katalog → BLOCKED/CYCLE (správně; testy předpokládaly mapování bez brány):**
    `test_f4_mapping.TestF4Integration.test_retezec_map_config_az_adapter`,
    `.test_f4_08_realny_katalog_prostor_sedm_klicu`,
    `.test_f4_09_backend_caps_ze_simu_a_prostor_bez_peak_torque`,
    `test_f4_mapping.TestF4Mapping.test_f4_05_peak_torque_nema_tune_protejsek`,
    `test_f4_integration.TestF4Integration.test_chain_vehicleconfig_to_testresult`,
    `.test_horsepower_kept_as_separate_tune_param`,
    `.test_peak_torque_path_explicitly_rejected`,
    `.test_brakes_bias_change_moves_stopping_distance` (ERROR),
    `test_f43_reconciliation.TestF43Reconciliation.test_map_config_odmitne_neexistujici_klic_s_duvodem`,
    `test_f4_optimizer_effect.TestF4OptimizerEffect.test_historie_rollback_determinismus`,
    `.test_prostor_bias_uvnitr_peak_torque_venku`.
  - **8× vzorek testu → BLOCKED/INTEGRITY (chyba dat testu, ne brány:**
    `tests/test_f4_mapping.py::_sample_catalog`, `qa_tboost.depends_on ==
    [{"param": "engine.turbo.count", …}]`, ale katalog obsahuje jen id `qa_tcount`;
    `engine.turbo.count` je `config_path`, ne `id` — jmenný prostor `depends_on` je
    `id` (audit A §2/§7); oprava pro C: `{"param": "qa_tcount"}`):
    `test_f4_mapping.TestF4Mapping.test_f4_05_mapovani_3_vlastnosti_vc_motora`,
    `.test_f4_06_jednotky_z_katalogu` (ERROR),
    `.test_f4_07_odmitnuti_unknown`, `.test_f4_07_odmitnuti_readonly_script`,
    `.test_f4_07_odmitnuti_mimo_rozsah`, `.test_f4_07_odmitnuti_konflikt_deterministicky`,
    `.test_f4_07_zavislost_boost_bez_turba`,
    `test_f4_mapping.TestF4Safety.test_f4_11_odmitnuti_zaznamenana`.
- PENDING beze změny (4; Studio/baseline — mimo rozsah).

## 6. Požadavky na Agenta C (testy; kód brány je hotov, neměnit chování)
1. Opravit `_sample_catalog` v `tests/test_f4_mapping.py`: `engine.turbo.count` → `qa_tcount`
   (8 testů výše se pak musí vrátit na PASS beze změny produkčního kódu).
2. Reálný katalog: přidat negativní probe — `map_config`/`build_search_space` nad
   `parameters.json` MUSÍ vracet BLOCKED-prázdno (CYCLE + svědek), nikdy mapování;
   stávajících 11 testů přepsat na toto očekávání (nebo na acyklickou kopii katalogu),
   NE obcházet bránu.
3. Nové testy brány: OK-vs-BLOCKED matice (CYCLE/INTEGRITY/INVALID), atomicita
   (vstup `deepcopy`-shoda, `tune_changes == []`, determinismus 2 běhů), slovníkové
   závislosti v grafu, `gate` modul neimportovatelný → fail-closed.
4. Atomicita adaptéru (Agent D k rozhodnutí): `apply_config` s BLOCKED-výstupem
   nesmí zapsat nic (`applied == []`, `patched_config` identický se vstupem).

## 7. Atomicita (ověřeno během)
- `map_config` nikdy nemutuje vstup (pouze čte; ověřeno `deepcopy` shodou před/po
  při OK i BLOCKED) a při BLOCKED nevytváří žádný výstup (`tune_changes == []`,
  `rejected` nese jen záznam brány, žádný částečný stav).
- `build_search_space` při BLOCKED vrací `[]` bez vedlejších efektů (čistá funkce).
- Katalogový soubor je bránou vždy read-only (žádný zápis v `gate`/`cycle_check`/
  `validate_catalog` cestě).
