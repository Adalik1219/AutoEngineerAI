# QA recheck integrace (nezávislý, vlastní běhy)

**Vlastněný soubor:** `C:/.DATA/AutoEngineerAI/qa/qa-recheck-integration.md`
**Pravidla:** česky; stdlib; žádné git operace; READ-ONLY mimo tento report.
**Ověřováno vůči:** `qa/qa-opt-integration.md` §5 opravy 1–10.

## R1 – Živý `evaluate()` je striktně validní vůči `contracts/test_result.schema.json`
Běh (vlastní, reálné CSV):
```
CSV: vehicle-data/runs\fixverify_selftest2\telemetry\cfg_0001_S1_accel_r0.csv
KEYS: ['baseline_total_score', 'config_id', 'deviations_vs_target', 'environment', 'group_scores', 'metrics', 'protected', 'raw_telemetry_ref', 'reproduced_runs', 'result_id', 'scenario_id', 'schema_version', 'score', 'total_score', 'verdicts']
schema_version: 1.0.0
score: 0.0002712297374544041 total: 8.212273090001869
result_id: tr_959c5b3d reproduced: 1
ERRORS: NONE - VALID
```
Kontrola stdlib: všechna `required` přítomna, žádné `extra` klíče (`additionalProperties: false` v
`contracts/test_result.schema.json:8`), `score` v `0..1`, `environment.mode` = `local-sim`.
Oprava č. 1 (§5.1: `src/Telemetry/evaluate.py:210-224` – `schema_version` + `_total_to_score`) **funguje**.
Pět nových volitelných polí (`total_score, group_scores, baseline_total_score, protected, verdicts`,
schéma řádky 29–33) je přítomno a povolených. **PASS.**

## R2 – Kampaň běží na external-src.Sim (manifest backend, žádný fallback)
```
find_external_sim: {'module': 'src.Sim.run', 'func': 'run_scenario'} callable: True
re-export run_scenario OK: True
```
Vlastní kampaň `python3 autoengineer.py selftest --repeats 3 --max-evaluations 6 --seed 7`:
```
SELFTEST optimizer-v0 bias_base=0.70 -> bias_best=0.69 S_base=8.2768 S_best=8.0736 best=cfg_0005 stop=BUDGET_OUT evals=6
vystupy: .../scratch/qarecheck_selftest
backend: {"backend": "external-src.Sim", "external": {"module": "src.Sim.run", "func": "run_scenario"}, "telemetry": "src.Telemetry.evaluate"}
```
Opravy č. 2 (`src/Optimizer/backend.py:152-158` kandidát `src.Sim.run`), č. 3
(`src/Sim/__init__.py` re-export `run_scenario`), č. 8 (adaptér `_call_external_sim`) **fungují**.
Žádný `fallback-synth-v0`. **PASS.**

## R3 – Optimizer selftest přímým spuštěním tiskne a exit 0
```
python3 src/Optimizer/selftest.py
SELFTEST optimizer-v0 bias_base=0.70 -> bias_best=0.61 S_base=8.2742 S_best=6.7122 best=cfg_0110 stop=CONVERGED evals=72
  [OK] history_nonempty / accepted_exists / rejected_with_A_code / score_improved /
       bias_toward_factory / protected_brake_not_worse / best_config_id_present / no_unstable_accepted
--- RAW historie (history.jsonl) --- ...
EXIT: 0
```
Oprava č. 5 (`src/Optimizer/selftest.py` `if __name__ == "__main__"` guard) **funguje**. **PASS.**

## R4 – `tests/run_all.py`: 0 FAIL
```
Ran 102 tests in 0.078s
OK (skipped=3)
SOUHRN: behu=102 PASS=99 FAIL=0 ERROR=0 PENDING=3
PENDING: test_schema_conformance_pending | test_baseline_exists | test_variant_store_append_only
VYSLEDEK: PASS (s 3 PENDING)
```
Všechny 3 PENDING jsou oprávněné (Fáze 5 / Fáze 9-10 baseline / regresní napojení VariantStore –
druhá větev; zastaralé skipy z §5.7 odstraněny). Původní 3 FAIL (propose/run_scenario/provenance)
opraveny (opravy č. 3, 4, 6). **PASS.**

## R5 – Finální integrační verdikt řetězce po rozhraních 1–7

| # | Rozhraní | Verdikt | Důkaz (vlastní běh) |
|---|---|---|---|
| 1 | Kontrakty → kódy (TestResult validita) | **FUNGUJE** | R1: živý `evaluate()` striktně validní, 5 volitelných polí OK |
| 2 | Fyzika `src/Physics` → `src/Sim` | **FUNGUJE** | `physics_backend = src.Physics.api` (dříve `builtin-v1`); `src/Physics/api.py` existuje |
| 3 | Sim → telemetrie (CSV) | **FUNGUJE** | 30/30/30 sloupců (`metrics.TELEMETRY_COLUMNS` = `vehicle.TELEMETRY_COLUMNS` = reálné CSV, hlavička shodná) |
| 4 | Telemetrie → TestResult → skóre | **FUNGUJE** | R1: metriky + `score=1/(1+exp(total))` v `0..1`, `total_score` lower-better konzistentní |
| 5 | Optimalizátor → Sim (backend) | **FUNGUJE** | R2: manifest `backend: external-src.Sim`, modul `src.Sim.run` |
| 6 | Optimalizátor → config/store/rollback | **FUNGUJE** | R2/R3: `best.json {best_config_id, config, stats}`, append-only `history.jsonl`, rollback záznamy, deterministické `ChangePlan` |
| 7 | Pipeline → manifest/best | **FUNGUJE** | R2: `best.json` + `selftest_manifest.json` zapsány; `report.json` level `SIM` |

**Celkový integrační verdikt: FUNGUJE jako celek.** Všech 7 rozhraní FUNGUJE, 0 FAIL v `run_all.py`.

## Zbytkové vady (soubor:řádka)
- Žádná blokující vada. 3 PENDING v `tests/run_all.py` jsou oprávněné a evidované (Fáze 5 / 9-10).
- Neblokující z §5.10 trvá: `src/Optimizer/search_space.py` – čítač `propose_candidates` od 1 může
  kolidovat s `cfg_0001`-style best ID mimo selftest (selftest používá `cfg_selftest_base`, nenaráží).
- Neblokující z §5.9: ověřeno jen pro selftest-cestu (čistý config); `autoengineer.py run` s cizím
  vstupem bez `parameters` nebyl v tomto rechecku znovu testován.
