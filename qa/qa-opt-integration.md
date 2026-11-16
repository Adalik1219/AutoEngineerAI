# QA optimalizace + integrace (vlna 2, nezávislý audit)

**Vlastněný soubor:** `C:/.DATA/AutoEngineerAI/qa/qa-opt-integration.md`
**Rozsah:** `src/Telemetry/*.py`, `src/Optimizer/*.py`, `autoengineer.py`, `tests/*.py` + integrační verdikt celého řetězce.
**Pravidla:** česky; Python 3 stdlib; žádné git operace (ověřeno — žádný `git` příkaz nespuštěn); READ-ONLY mimo tento report (zápisy pouze `qa/qa-opt-integration.md` + scratch pod `TMPDIR`).
**Zdroje čteny:** `docs/ARCHITECTURE.md` (§3.4, §3.5, §4, §5.2), `docs/TESTING-OPTIMIZATION.md` (A1–A5 §5.3, metriky §4.2, váhy §4.4), `docs/CONTRACTS.md`, `docs/AGENT-RULES.md`, `contracts/*.schema.json`, všechny auditované `src/*` a `tests/*` (viz případy).

---

## 1. Ověřená fakta / předpoklady / neznámé

- **Ověřená fakta:** všechny závěry níže jsou podloženy vlastním během (případy T1–T12, raw výstupy v §3). Cesty jsou absolutní.
- **Předpoklad:** `example-vehicle.json` je DB záznam (bohatý formát), ne pipeline `ReferenceProfile` — převod řeší `reference_from_rich_vehicle` (tolerance 0.5 s / 5 km/h / 2 m).
- **Neznámé (mimo rozsah):** skutečné parametry A-Chassis, Roblox runtime chování, kalibrace vah proti reálnému vozu.

---

## 2. Verdikt po blocích

| Blok | Verdikt | Důvod (jedna věta) |
|---|---|---|
| (1) Telemetry metriky | **PASS** | Vlastní generátor: `t_0_100`, brzdná dráha i `a_lat=v²/R` sedí na analytiku v rámci vzorkování. |
| (1b) TestResult tvar / skóre / chráněné metriky | **FAIL** | `evaluate()` nevrací `schema_version` a `score` je záporné TotalScore mimo schéma `0..1`. |
| (2) Optimizer propose / statistika / store / ChangePlan | **PASS s výhradou** | Funkcionalita správná a deterministická; jméno `propose` z ARCH §5.2 neexistuje (je `propose_candidates`) — proto padá H-test, ne proto, že by funkce chyběla. |
| (3) autoengineer.py end-to-end | **PASS s výhradou** | `run` i `selftest` doběhnou, `best` + manifest zapíší; `src/Optimizer/selftest.py` přímé spuštění mlčí (chybí `__main__`). |
| (4) tests/run_all.py | **FAIL (3 FAIL, 4 PENDING)** | 102 běhů: 95 PASS, 3 FAIL, 4 PENDING. PENDING 2/4 zastaralé, 2/4 oprávněné. |
| (5) Integrace řetězce | **ČÁSTEČNĚ NEFUNGUJE** | Rozhraní 5 a 6 (viz §5) jsou rozbitá: `find_external_sim` nikdy nenajde `src/Sim`, `evaluate` není schéma-validní. |

---

## 3. Případy + raw výstupy (vlastní běhy, ne opsané)

### T1 – Akcelerace, konst. `a` → `t_0_100 = v/a` (vlastní generátor, 60 Hz)

```
T_ACCEL a=4.0: t_0_100=6.9444 exp=6.9444 diff=0.0000 flags=['brake_phase_not_found', 'vmax_not_settled', 'understeer_invalid']
T_ACCEL a=8.0: t_0_100=3.4722 exp=3.4722 diff=0.0000 flags=[...]
```

Zdroj: `C:/.DATA/AutoEngineerAI/src/Telemetry/metrics.py` (`_first_crossing` + lineární interpolace). **PASS.**

### T2 – Brzdění, konst. zpomalení → `s = v0²/2a`, `mean_decel = v0²/2s`

```
T_BRAKE dec=6.0: dist=64.184 exp=64.300 mean_decel=6.000
T_BRAKE dec=8.0: dist=48.109 exp=48.225 mean_decel=8.000
```

Odchylka ~0.1–0.2 m = lichoběžníková integrace při 240 Hz, v toleranci testu (`delta=1.0`). **PASS.**

### T3 – Kruh, `a_lat = v²/R` (vlastní generátor kruhu)

```
T_CIRCLE R=30.0 a=8.0:  vmax_a_lat=8.0000 exp=8.0
T_CIRCLE R=30.0 a=9.81: vmax_a_lat=9.8100 exp=9.81
```

Pozn.: při konstantním `a_lat` je `K_us=None, valid=False` — správně (nulový rozptyl, regrese nemá z čeho počítat). Se sweepem `a_lat ∈ {1..6}×4, steer=K·a, K=0.008`:

```
K_US sweep: 0.008000000000000002 True (expect ~0.008 True)
```

**PASS** (znaménko i hodnota; `>0` = nedotáčivost).

### T4 – Mann-Whitney + mean-std na známých vzorcích

```
T_MW separated: U=0.0 p=0.0040 (expect p<0.05)      # x={1.0,1.1,0.9,1.05,0.95}, y={2.0,...} → správně zamítá H0
T_MW identical: U=12.5 p=1.0000 (expect p~1)        # shodné vzorky → p=1
T_MEANS separated=True gap=0.9800 (expect True)
T_MEANS overlap separated=False gap=-1.9000 (expect False)
```

Zdroj: `C:/.DATA/AutoEngineerAI/src/Optimizer/statistics.py` (exaktní permutace ≤20000 kombinací, midranks při shodách). **PASS.**

### T5 – Váhy a chráněné metriky

```
T_WEIGHTS sum=1.0 w={performance:0.25, braking:0.20, handling:0.25, suspension:0.10, traction:0.10, robustness:0.10}
T_HARDLIMITS={brake_distance_100_0_m:{rel:0.01}, yaw_rate_max_abs:{rel:0.05}, slip_max_abs:{rel:0.05}, susp_bottoming_count:{abs:0}}
```

Součet vah = 1.0 dle §4.4; limity dle §5.3/A2 (brzda +1 %, yaw +5 %, dosednutí nulová tolerance). **PASS.**

### T6 – Determinismus propose + ChangePlan + store

```
T_DET propose same=True n=10 first_ids=['cfg_0001', ...]
T_DET plan same=True plan_id=plan_0007 steps=1 chassis=keep
T_STORE attempts=2 best=cfg_0001 last_event=rollback counts={tested:2, accepted:1, rejected:1}
```

`propose_candidates` i `plan_from_diagnosis` bitově deterministické; store append-only (rollback = nový záznam, historie nemazána, `best_config_id` pointer). **PASS.**

### T7 – TestResult tvar (FAIL – důkaz)

Vlastní `evaluate()` na reálné stopě `vehicle-data/runs/selftest_20261116T213145Z/telemetry/cfg_0001_S1_accel_r0.csv`:

```
TestResult keys: [baseline_total_score, config_id, deviations_vs_target, environment, group_scores,
  metrics, protected, raw_telemetry_ref, reproduced_runs, result_id, scenario_id, score, total_score, verdicts]
missing vs schema: ['schema_version'] | score valid 0..1: False
score: -1.9316144464298013   # záporné TotalScore, schéma žádá 0..1
```

Povinná pole `contracts/test_result.schema.json`: `schema_version, result_id, config_id, scenario_id, environment{mode,seed,code_version}, metrics, deviations_vs_target, score(0..1), reproduced_runs, raw_telemetry_ref`.
`evaluate()` vrací navíc `total_score, group_scores, baseline_total_score, protected, verdicts` (to je v pořádku — nadmnožina), ale **chybí `schema_version`** a **`score` je mimo `0..1`** (lower-better TotalScore, kladná = horší, záporná = lepší než cíl). Příklad `contracts/examples/test_result.valid.json` projde validátorem, živý výstup `evaluate()` neprojde. **FAIL.**

### T8 – `tests/run_all.py` vlastní re-běh

```
Ran 102 tests in 0.091s
FAILED (failures=3, skipped=4)
SOUHRN: behu=102 PASS=95 FAIL=3 ERROR=0 PENDING=4
FAIL: test_propose_api (TestOptimizerContract)
FAIL: test_example_vehicle_provenance (TestReferenceProvenance)
FAIL: test_run_scenario_api (TestSimContract)
PENDING: test_schema_conformance_pending | test_evaluate_wrapper_pending | test_baseline_exists | test_variant_store_append_only
```

- **3 FAIL potvrzeny** (shodné s tvrzením koordinátora).
  - `test_propose_api` — test žádá `Optimizer.propose` + `Optimizer.acceptance_decision`. Realita v `C:/.DATA/AutoEngineerAI/src/Optimizer/__init__.py`: exportuje `propose_candidates` + `acceptance_decision`, `propose` neexistuje. Funkcionalita existuje pod jiným jménem + jinou signaturou než ARCH §5.2 (`propose(history, space)` vs `propose_candidates(best_config, space, ...)`). **Chyba je zastaralý test + odchylka od ARCH, ne chybějící optimalizér.**
  - `test_run_scenario_api` — test žádá `src.Sim.run_scenario`. Realita: `run_scenario(config_path, scenario_id, dt, seed, out_dir)` existuje v `C:/.DATA/AutoEngineerAI/src/Sim/run.py`, `simulate(params, scenario_def, dt, seed)` v `vehicle.py`, ale `C:/.DATA/AutoEngineerAI/src/Sim/__init__.py` exportuje jen `simulate` — `run_scenario` není re-exportováno. **Chyba je chybějící re-export, ne chybějící simulátor.**
  - `test_example_vehicle_provenance` — 4× `null` s `confidence: 0.2` místo `0`: `/mass/yaw_inertia`, `/suspension/spring_rate_front`, `/suspension/spring_rate_rear`, `/aero/drag_coefficient_cd`. Porušení CONTRACTS §7 / ARCH §3.2 (`null` ⇒ `confidence: 0`). **Chyba dat, test má pravdu.**
- **PENDING (4): oprávněnost:**
  - `test_schema_conformance_pending` — **oprávněné** (Fáze 5, mapování DB→profil skutečně chybí).
  - `test_baseline_exists` — **oprávněné** (baseline Fáze 9/10 neexistuje).
  - `test_evaluate_wrapper_pending` — **NEOPRÁVNĚNÉ/zastaralé**: text tvrdí, že `evaluate()->TestResult` „ve vlně 1 zatím neexistuje (Agent F)", ale `C:/.DATA/AutoEngineerAI/src/Telemetry/evaluate.py` existuje a funguje (viz T7). Skip se nikdy neodstranil.
  - `test_variant_store_append_only` — **NEOPRÁVNĚNÉ/zastaralé**: text tvrdí, že `VariantStore` „zatím neexistuje", ale `C:/.DATA/AutoEngineerAI/src/Optimizer/store.py` existuje (viz T6). Druhá větev skipu („neověřeno proti reálným datům") je přitom legitimní — měla zůstat, první je nepravdivá.

### T9 – `autoengineer.py` vlastní end-to-end

```
# run (3 repeats, 4 evaluace, seed 7):
KAMPAN hotova: stop=BUDGET_OUT evals=4 testovano=5 prijato=2 zamitnuto=3
best_config_id=cfg_0001 S_best=0.6590 final_drive_best=2.716
vystupy: .../qatest_run (history.jsonl, best.json, manifest.json, report.json)
# selftest (3 repeats, 6 evaluací):
SELFTEST optimizer-v0 fd_base=4.10 -> fd_best=3.95 S_base=1.0528 S_best=0.8330 best=cfg_0001 stop=BUDGET_OUT evals=6
  [OK] history_nonempty | [OK] accepted_exists | [OK] rejected_with_A_code (kody=['A1_TOTAL_SCORE'])
  [OK] score_improved | [OK] final_drive_toward_factory | [OK] protected_brake_not_worse
  [OK] best_config_id_present | [OK] no_unstable_accepted
```

`best.json` (`best_config_id` + `config` + `stats`), `history.jsonl` (append-only, attempt+rollback záznamy), `manifest.json` (schema_version/run_id/code_version/seed/scenario_versions/artifacts — tvar dle `contracts/manifest.schema.json`), `report.json` (level `SIM (UNCONFIRMED_RUNTIME)`, `backend: fallback-synth-v0`). **PASS.**

### T10 – Proč `G selftest exit 0 bez stdout` (root cause)

`C:/.DATA/AutoEngineerAI/src/Optimizer/selftest.py` **nemá `if __name__ == "__main__"` blok** — definuje pouze `run_selftest()`. Přímé `python src/Optimizer/selftest.py` tedy nic netiskne a vrátí 0. Naproti tomu `C:/.DATA/AutoEngineerAI/src/Telemetry/selftest.py` `__main__` guard má. Cesta přes `autoengineer.py selftest` funguje (volá `run_selftest` a tiskne `report`). **FAIL (minor, diagnostikováno).**

### T11 – Sloupce 30 vs 33

```
src/Telemetry/metrics.py TELEMETRY_COLUMNS: 30
src/Sim/vehicle.py TELEMETRY_COLUMNS:        30
reálné CSV (cfg_0001_S1_accel_r0.csv):       30 (shodná hlavička)
```

Žádný 33-sloupcový formát v repozitáři neexistuje; všechny tři vrstvy mají shodných 30 sloupců dle specifikace. **PASS (tvrzení o 33 sloupcích se nepotvrdilo — není co opravovat).**

### T12 – Sim backend vs Physics

```
src.Sim.physics_backend.backend_name() = 'builtin-v1'   # src/Physics/api neexistuje (adresář má jen aero/brakes/diff/engine/gearbox/...)
find_external_sim() = (None, {module: None, reason: 'src.Sim.run_scenario nenalezeno'})
selftest_manifest.backend = {backend: 'fallback-synth-v0', external: {module: None, ...}}
```

**Důkaz rozpojení:** `find_external_sim` v `C:/.DATA/AutoEngineerAI/src/Optimizer/backend.py` hledá `run_scenario` v `src.Sim.api / .simulation / .engine / src.Sim`, ale funkce žije v `src.Sim.run` (a není re-exportována). Externí Sim se proto **nikdy** nenajde a každá kampaň tiše padá do `fallback-synth-v0`. Manifest to poctivě hlásí, ale optimalizuje se proti syntetice, ne proti `src/Sim`. Viz §5 rozhraní 5.

---

## 4. Integrační verdikt řetězce (kontrakty→fyzika→sim→telemetrie→optimalizátor→config)

| # | Rozhraní | Verdikt | Důkaz |
|---|---|---|---|
| 1 | Kontrakty → kódy (schémata vs implementace) | **NEFUNGUJE** | `evaluate()` výstup není validní vůči `test_result.schema.json` (T7: chybí `schema_version`, `score` mimo `0..1`). `ChangePlan` z `plan_from_diagnosis` je naproti tomu schéma-validní (všechna required pole, `plan_dg_` prefixy OK). |
| 2 | Fyzika `src/Physics` → `src/Sim` | **ČÁSTEČNĚ** | `src/Physics/api.py` neexistuje → `physics_backend` korektně padá na `builtin-v1` a manifest to hlásí (T12). Principy z KNOWLEDGE-TRANSFER (slip+eps, MF+friction circle, kvazistatika, tvarovaná křivka motoru) jsou v builtin implementovány, ale **nikdo je proti `src/Physics/*` (engine/gearbox/… existuje!) neporovnal** — paralelní implementace bez testu shody. |
| 3 | Sim → telemetrie (CSV) | **FUNGUJE** | 30/30/30 sloupců, hlavička validována (`_validate_csv`), `load_telemetry` odmítá cizí formáty (test `test_bad_header_rejected` PASS). |
| 4 | Telemetrie → TestResult → skóre | **FUNGUJE s vadou obalu** | Metriky, váhy (§4.4, součet 1.0), `deviations_vs_target`, chráněné metriky A2 — vše správně (T1–T5, T7). Vada je jen obal: `schema_version` + rozsah `score` (viz #1). Směr „nižší = lepší" je konzistentní v `evaluate`, `acceptance` i `optimizer` (dokumentováno v `report.json`: `lower_better`). |
| 5 | Optimalizátor → Sim (který backend se testuje) | **NEFUNGUJE** | `find_external_sim` nikdy nenajde `src/Sim` (hledá na špatných cestách) → 100 % kampaní běží na `fallback-synth-v0`. Důkaz: `selftest_manifest.json` (`backend: fallback-synth-v0`) + T12. Optimalizér tak neoptimalizuje `src/Sim` vozidlo, ale syntetickou bodovou hmotu. |
| 6 | Optimalizátor → config/store/rollback | **FUNGUJE** | Append-only historie, `best_config_id` pointer, `log_rollback` audit, `safety_filter` meze+krok, deterministický `ChangePlan` (T6, T9). |
| 7 | Pipeline → manifest/best (autoengineer.py) | **FUNGUJE** | `run`/`selftest` zapíší `history.jsonl` + `best.json`/`best_config.json` + `manifest.json` + `report.json`; manifest tvarově odpovídá schématu; level vždy `SIM (UNCONFIRMED_RUNTIME)` (T9). |

**Celkový integrační verdikt: NEFUNGUJE jako celek.** Jednotlivé moduly počítají správně, ale řetězec optimalizuje syntetický model místo `src/Sim` (#5) a jeho výstupy nejsou schéma-validní TestResulty (#1). Prohlášení „kampaň proběhla" je pravdivé pro fallback, nepravdivé pro `src/Sim` vozidlo.

---

## 5. Přesný seznam oprav (číslováno, bez obecností)

1. **`src/Telemetry/evaluate.py` — vrátit schéma-validní TestResult:** doplnit `"schema_version": "1.0.0"`; `score` mapovat do `0..1` (např. `score = 1/(1+exp(-total))` nebo ořezat/normalizovat a dokumentovat), nebo změnit `contracts/test_result.schema.json` na `total_score` lower-better konvenci. Dnes živý výstup schématem neprojde (T7), vzor ano.
2. **`src/Optimizer/backend.py `find_external_sim` — přidat `src.Sim.run`:** kandidát `("src.Sim.run", "run_scenario")` (tam funkce je). Alternativně re-export v `src/Sim/__init__.py`. Bez toho je každá kampaň fallback (T12).
3. **`src/Sim/__init__.py` — re-export `run_scenario`:** `from .run import run_scenario` (opraví i `test_run_scenario_api` FAIL bez změny testu).
4. **`tests/test_module_contracts.py `test_propose_api` — aktualizovat na realitu:** očekávat `propose_candidates` (a volitelně alias `propose = propose_candidates` v `src/Optimizer/__init__.py` pro zpětnou kompatibilitu s ARCH §5.2). Dnes test žádá neexistující jméno.
5. **`src/Optimizer/selftest.py` — doplnit `if __name__ == "__main__":` guard** (volání `run_selftest` + `print(report)` + `sys.exit(code)`), jako má `src/Telemetry/selftest.py`. Dnes přímé spuštění = ticho + exit 0 (T10).
6. **`vehicle-data/references/example-vehicle.json` — 4× `confidence: 0.2 → 0`** u `value: null` (`/mass/yaw_inertia`, `/suspension/spring_rate_front`, `/suspension/spring_rate_rear`, `/aero/drag_coefficient_cd`). Dnes porušuje vlastní kontrakt (T8).
7. **`tests/test_module_contracts.py` — odstranit 2 zastaralé PENDING skipy:** `test_evaluate_wrapper_pending` (`src/Telemetry/evaluate.py` existuje) a první větev `test_variant_store_append_only` (`VariantStore` existuje). Ponechat oprávněné: `test_schema_conformance_pending`, `test_baseline_exists`, druhou větev variant-store (reálná data).
8. **`src/Optimizer/backend.py` — sjednotit `run_one` signaturu s `src/Sim/run.py::run_scenario`:** dnes `ext_fn(config, scenario, seed, csv_path)` vs realita `run_scenario(config_path, scenario_id, dt, seed, out_dir)` — i po opravě č. 2 by volání spadlo do `except → fallback`. Adaptér musí uložit config na tmp soubor a mapovat `scenario_id` (`S1_accel` → `straight_accel`).
9. **`autoengineer.py `normalize_config` — fail-fast na cizí vstup:** odmítnout soubor bez `parameters` (dnes tiše míchá bohatý DB záznam do VehicleConfig → `best_config.json` s 22 klíči místo 8, viz T12). Nesouvisí s hlavní kampaní (selftest používá čistý config), ale je to past na uživatele.
10. **Zvážit (neblokující):** `propose_candidates` čísluje od `start_counter=1`, což koliduje s `cfg_0001`-style best ID mimo selftest (selftest používá `cfg_selftest_base`, proto nenarazí). Doporučeno: čítač odvodit od maxima v historii, nebo prefix `cfg_c*`.

---

## 6. Co nebylo ověřeno (poctivě)

- Shoda `builtin-v1` vs `src/Physics/*` po jednotlivých funkcích (žádné `api.py` k porovnání; testy `TestPhysics*` v `test_module_contracts` ověřují jen `engine/gearbox/diff`, ne integraci se Simem).
- Scénáře S4/S5/S6 (skidpad, losí test, slalom) v optimalizační matici — rychlá matice boduje jen S1+S3 (dokumentované rozhodnutí v `backend.py`, ne chyba).
- Roblox runtime — vše výše je úroveň SIM/MATH; `A5_RUNTIME` brána správně zůstává `UNCONFIRMED_RUNTIME`.
