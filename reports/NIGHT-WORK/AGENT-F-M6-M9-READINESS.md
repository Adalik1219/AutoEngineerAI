# Agent F – M6 až M9: architektura a připravenost (readiness)

**Větev:** `feat/m2-m3-geometry`, **HEAD:** `9803db3` (2026-11-19).
**Rozsah práce:** pouze čtení + tento report. Žádné změny RBXM, žádná runtime tvrzení,
žádné auto-aplikování do modelu. Jazyk: česky; kód/identifikátory anglicky.
**Vstupy čteny:** `src/Optimizer/` (9 souborů), `src/Telemetry/` (`evaluate.py`, `metrics.py`),
`src/Sim/` (`run.py`, `scenarios.py`, `config.py`, `vehicle.py`), `autoengineer.py`,
`src/common/ids.py`, `contracts/` (6 schémat + examples), `docs/HYBRID_WORKFLOW.md`,
`docs/ACCEPTANCE_CRITERIA.md`, `docs/IMPLEMENTATION_ROADMAP.md` (M6–M9),
`docs/ARCHITECTURE.md`, `docs/TESTING-OPTIMIZATION.md` (§5), `docs/PROJECT_STATUS.md`,
`testgame/.../ScenarioDefinitions.lua`.

## 1. Souhrn: co existuje vs co chybí

| Modul | Existuje (soubor) | Chybí |
|---|---|---|
| **M6 Config & Rollback** | `vehicle_config.schema.json` + `change_plan.schema.json` + `manifest.schema.json`; `Optimizer/change_plan.py` (pravidlový ChangePlan v0, deterministický); `Optimizer/store.py` (append-only `history.jsonl`, `best.json` přes tmp+replace, `log_rollback`, `counts`); `autoengineer.py cmd_run` (píše `manifest.json`/`report.json`/`best_config.json`); `common/ids.py` (`cfg_/plan_/run_` vzory) | generátor balíčku `iteration_NNN/` (9 souborů vč. `rollback.json`); `diff_report` (dnes jen interní `_diff_params`); rollback s ověřeným nulovým diffem; atomicita M6.10 (kopie+swap, kill-test, last-known-good); hash-integrita vstupu (SHA originálu před/po) |
| **M7 Test Protocol** | `Sim/scenarios.py` (5 scénářů + `SCENARIO_VERSIONS`); `ScenarioDefinitions.lua` (T01/T01B…, track/surface/repetitions/tolerance); `scenario.schema.json`; `test_result.schema.json` (`environment.mode: local-sim/roblox-runtime`); `TESTING-OPTIMIZATION.md` (S1–S11 + minima opakování); `backend.py SCENARIOS` (S1+S3) + `SCENARIO_METRICS` | generátor `test_protocol.md`; `expected_results.json` s `{target, unit, tolerance, min_repetitions, verdict_rule}`; formulář/`result_schema` JSON pro ruční měření; trasabilita T-* ↔ S-* (jen dílčí zmínka T-ACC-01→S1, T-BRK-01→S3); L1/L2/L3 gating v generátoru |
| **M8 Evaluator & Advisor** | `Optimizer/statistics.py` (median/IQR/exaktní MW-U/mid-ranks/`means_separated`); `Optimizer/acceptance.py` (A1–A5, `UNCONFIRMED_RUNTIME` flag); `Telemetry/evaluate.py` (single-run A1–A3, protected, `unstable`/`suspect`); `Telemetry/metrics.py` (30 fixních sloupců, sanity meze) | `measurement_loader` (formulář M7 → čísla); oddělená opakovatelnost `R=(max−min)/\|x̄\|` vs přesnost (dnes jen `scenario_tol` 3 %); outlier-flag `\|odchylka\|>3s`/Grubbs s evidencí, nikdy tiché mazání; `iteration_advisor` (`NEXT-ITERATION\|ACCEPTED\|ROLLED-BACK` s důvodem nad runtime měřením) |
| **M9 Workflow** | `autoengineer.py` CLI (`run/selftest/plan`); `Optimizer/optimizer.py` (`run_optimization`: baseline → sondy → A1–A5 → best/rollback; `TARGET_MET/BUDGET_OUT/CONVERGED/UNSTABLE_STOP`); `VariantStore` historie; `manifest.json` + `report.json` na běh | orchestrace M1→M8 (`BuildVehicle`); stavový stroj `PLANNED→CONFIGURED→TESTED→EVALUATED→(ACCEPTED\|ROLLED-BACK\|NEXT-ITERATION)` + `workflow_state.json`; `iteration_manager` (2 iterace za sebou); import výsledků ze Studia (M9.9); generátor finálního reportu; workflow test s testovacím RBXM |

**Klíčové omezení pro všechny:** M3 NOT IMPLEMENTED, M2 měřítko BLOCKED (rozptyl 7,44 % > 5 %),
M4/M5 PARTIAL bez vazby cíl→Tune. `geometry_target` / `physics_target` / `achassis_changes`
proto pro M6–M9 **neexistují jako vstupy** — M6 generátor musí umět SIM-only balíček
(bez geometrické větve), M7/M8 se staví na S1/S3 + Lua T-protokolech, ne na M3/M4 číslech.

## 2. M6 – detail

**Existuje:**
- Kontrakty: `vehicle_config` (povinné `schema_version, config_id, vehicle_profile_id,
  chassis_adapter, parameters, rationale`; volitelné `parent_config_id`, `model_patch_ref`),
  `change_plan` (`plan_id^plan_`, `diagnosis_ref^dg_`, `steps[].area/action/from/to`,
  `chassis_decision keep|adapt|replace`, `stop_conditions.max_iterations`),
  `manifest` (`run_id^run_`, `code_version`, `seed`, `scenario_versions`, `artifacts[]`).
- `change_plan.py`: 5 pravidel symptom→krok, deterministické pořadí, fallback sonda
  `probe_final_drive`, kroky mimo prostor se generují, ale optimizer je ignoruje.
- `store.py`: `history.jsonl` append-only (vč. rollback záznamů), `best.json` atomicky
  (tmp + `os.replace`), `set_best`/`log_rollback`/`attempts`/`counts`. Rollback = O(1) pointer swap.
- `autoengineer.py cmd_run`: `run_id` normalizace, `manifest.json` (history/best_config/report
  artifacts), `report.json` (stop_reason, S_best, counts, backend info), `best_config.json`.
- `search_space.py`: dynamický prostor z katalogu přes `build_search_space` ∩ `backend_caps`
  (dnes fakticky 2 knoby: `transmission.final_drive`, `brakes.bias_front`); `safety_filter`
  (meze + `max_step = 2·step·scale`).
- `Sim/run.py`: `sim_src_version` (sha256 vlastních zdrojů → `code_version`), manifest
  s `telemetry_sha256`, `used_defaults`; determinismus „stejné args = bitově stejné CSV".

**Chybí (blokuje DoD M6):**
1. `generator` balíčku `vehicle-data/runs/<vehicle>/iteration_NNN/` — 9 souborů dle ROADMAP
   (`vehicle_profile, geometry_target, physics_target, achassis_changes, test_protocol.md,
   expected_results, rollback` + `manifest`). Dnes jen plochý `run_<stamp>/` (SIM artefakty).
2. `diff_report.json` — dnes jen interní `_diff_params(best, cand)` pro `param_diff` v historii.
3. `rollback.json` s **ověřeným nulovým diffem** (aplikuj rollback → přepočítej hash/diff → `diff==0`).
4. Atomicita M6.10 — zápis do nové kopie + atomický swap celé iterace; kill-test
   (pád uprostřed aplikace nechá předchozí iteraci funkční). Dnes atomický jen `best.json`.
5. Integrita vstupu — SHA originálu RBXM/configu před/po (brána G-01). `sim_src_version`
   kryje jen zdroje Simu, ne vstupní model.
6. Oddělení návrhu od aplikace (G-08, jedna logická skupina parametrů na iteraci) —
   dnes vynuceno jen konvencí sond (`_diff_params` typicky 1–2 knoby), ne validátorem balíčku.

## 3. M7 – detail

**Existuje:**
- `Sim/scenarios.py`: `straight_accel`, `straight_brake_100_0`, `constant_radius_turn`,
  `lane_change`, `bump_section` — deterministický driver, `SCENARIO_VERSIONS 1.0.0`.
- `ScenarioDefinitions.lua`: T01 (akcelerace 0–100), T01B (gate+dobrzdění), track/surface/
  `initial_conditions`/`procedure`/`completion`/`failure_abort`/`measurements`/`repeatability`,
  `DEFAULT_REPEAT_TOL` (časy/drhy ±5 %, RMS ±10 %).
- `backend.py`: rychlá matice S1+S3, `SCENARIO_METRICS` (S1=výkon, S3=brzdy — zákaz bodování
  V-max z brzdného běhu), aliasy metrik, `load_reference_targets` (rp i rich formát).
- Kontrakty: `scenario` (`scenario_id/kind/seed` + `tolerances`), `test_result`
  (`environment.mode` povinně `local-sim|roblox-runtime`; L3 bez `roblox-runtime` není důkaz).
- Minima opakování: `HYBRID_WORKFLOW.md` §3 (T-ACC-01 5×, T-BRK-01 5×, T-STEER 3+3×,
  T-REL-01 3×, T-STAB-01 3×) + `autoengineer.py` fail-fast `repeats >= 3`.

**Chybí (blokuje DoD M7):**
1. `protocol_generator` → `test_protocol.md` (lidsky čitelný, bez expertních znalostí proveditelný).
2. `expected_results.json` — ke každému testu `{target, unit, tolerance, min_repetitions,
   verdict_rule}`; `verdict_rule` = explicitní nerovnost (např. `|Error_%| ≤ tolerance → PASS`).
   Protokol bez čísel se zamítá (AC M7).
3. Formulář/`result_schema` JSON pro ruční měření (prázdný i plný validuje schéma).
4. Trasabilita T-* (Mustang) ↔ S-* (Sim): doloženo jen T-ACC-01→S1, T-BRK-01→S3; chybí
   T-GEO/T-STEER/T-REL/T-STAB mapování a `test_conditions` (trať/povrch/seed/počáteční stav).
5. L1/L2/L3 přiřazení testům + `mode` gating v generátoru (L3 → `roblox-runtime` povinně).

## 4. M8 – detail

**Existuje:**
- `statistics.py`: `median`, `mean`, `stdev_sample`, `iqr` (hinges), `describe`,
  `mann_whitney_less` (exaktní permutační ≤20000 kombinací, jinak normální aproximace
  s korekcí na shody + kontinuitu), `means_separated` (pásma mean±std pro n<4).
- `acceptance.py` A1–A5: A1 TotalScore s margínem, A2 lower-better limity + higher-better
  stráž V-max (2 %), A3 stabilita (0 UNSTABLE/SUSPECT, aborty ≤ best), A4 MW-U na
  standardizovaném poolu + praktický práh 0.02 + konzistence scénářů (3 %), A5 runtime
  brána (`UNCONFIRMED_RUNTIME` v SIM, nikdy zamítnutí).
- `Telemetry/evaluate.py`: single-run A1–A3, `protected` (baseline→target fallback),
  `verdicts{unstable, suspect, accepted, failed_condition}`, `total_score` + monotonní
  `score=1/(1+e^total)`, `result_id = tr_<sha1(telemetrie)>`.
- `metrics.py`: `t_0_60/t_0_100`, `v_max`, `brake_distance_100_0`, `stopping_time`,
  `mean_decel`, `a_lat/yaw/slip/susp/yaw_variance`, `unstable` (yaw_rate > 120 °/s),
  sanity meze (§6.3) → `suspect`.

**Chybí (blokuje DoD M8):**
1. `measurement_loader` — načtení ručního formuláře M7 + telemetrie ze Studia, validace
   jednotek/podmínek, mapování aliasů (accel_0_100_s→t_0_100_s…).
2. Opakovatelnost vs přesnost odděleně — `R = (max−min)/|x̄|·100 %` (precedent F7.2 AC3:
   R ≤ 10 % jen je-li |x̄| bezpečně od nuly) vs `|x̄−target|/|target|·100 %`. Dnes jen
   `scenario_tol` 3 % v A4; R se nikde nepočítá.
3. Outlier engine — flag `|odchylka| > 3s`/Grubbs, vyřazení **jen se záznamem důvodu**
   v `evaluation.json`, nikdy tiché mazání. Dnes `suspect` existuje, ale bez 3-sigma pravidla.
4. `iteration_advisor` — `NEXT-ITERATION | ACCEPTED | ROLLED-BACK` s důvodem nad
   **runtime měřením** (optimizer `stop_reason` je SIM cyklus, ne advisor).
5. Pravidlo `n < 3 → INSUFFICIENT`, nikdy PASS (AC M8) — dnes `repeats>=3` fail-fast
   v CLI, ale evaluator ho nevynucuje jako verdikt.
6. Sjednocení duplicity `Telemetry/*` vs `Optimizer/{statistics,acceptance}.py`
   (známý bod `PROJECT_STATUS.md` §1/D3) — před M8 rozhodnout, který modul je zdroj pravdy.

## 5. M9 – detail

**Existuje:**
- `autoengineer.py` CLI: `run` (plná kampaň), `selftest` (exit 0/1, 8 checks:
  history_nonempty/accepted_exists/rejected_with_A_code/score_improved/bias_toward_factory/
  protected_brake_not_worse/best_config_id_present/no_unstable_accepted), `plan`.
- `optimizer.py run_optimization`: baseline re-validation → kola sond+grid → safety filtr →
  `evaluate_config` → A1–A5 → best/rollback; `step_scale` halving, `CONVERGED` po
  2 zamítnutých kolech / `step<0.25`, `UNSTABLE_STOP` při >20 % UNSTABLE, `TARGET_MET`
  (|dev|≤1 všech bodovaných metrik).
- Historie + manifest na běh; `vehicle-data/runs/` obsahuje reálné kampaně
  (`opt_selftest_*`, `selftest_*`).

**Chybí (blokuje DoD M9 + bránu M9.12):**
1. `vehicle_build` orchestrace M1→M8 (M9.1–M9.12) — dnes jen SIM větev
   (load→simulate→evaluate→propose), bez M1/M2/M3/M4/M5 kroků.
2. Stavový stroj `PLANNED → CONFIGURED → TESTED → EVALUATED →
   (ACCEPTED | ROLLED-BACK | NEXT-ITERATION)` + `workflow_state.json` (M9.12 historie).
3. `iteration_manager` — dvě po sobě jdoucí iterace nad stejným RBXM (integrační test M9).
4. Import výsledků ze Studia M9.9 (formulář + telemetrie → `evaluation.json`).
5. `report_generator` — finální report (protokol + telemetrie + manifest na iteraci).
6. Brána M9.12: všechny G-01–G-10 PASS + archivovaný protokol/telemetrie/manifest na iteraci
   + žádný `local-sim` výsledek vydávaný za runtime důkaz.

## 6. Závislostní graf

```text
M1 (VERIFIED) ──┐
                ├─→ M3 (NOT IMPL, BLOCKED měřítkem M2) ──┐
M2 (CONDITIONAL │                                        ├─→ M5 (PARTIAL, chybí cíl→Tune) ─→ M6 ─→ M7 ─→ M8 ─→ M9
   PASS/BLOCKED)┘                                        │
M4 (PARTIAL) ───────────────────────────────────────────┘

SIM-paralelní větev (nezávislá na M2/M3, existuje dnes):
  Sim/scenarios + Telemetry/evaluate + Optimizer/{backend,optimizer,acceptance,statistics,store}
  + autoengineer.py  =  uzavřený SIM cyklus (CODE-VERIFIED přes selftest).

M6–M9 hrana k M5: generátor balíčku MUSÍ fungovat v SIM-only režimu
(geometry_target/physics_target/achassis_changes = BLOCKED placeholder),
jinak M6–M9 stojí do odblokování M2/M3.
```

Kritická cesta: **M2 měřítko → M3 → M5 vazba → M6 plný balíček → M9 plný workflow**.
SIM cesta (M6s→M7→M8s→M9s) je na ní nezávislá a jde stavět hned.

## 7. Implementační pořadí (doporučené)

1. **M6a — balíčkový generátor (SIM-only):** `generator` píšící `iteration_NNN/` ze SIM kampaně
   (vehicle_profile≈config snapshot, `BLOCKED.json` za M3/M4/M5 vstupy, manifest).
   Bez čekání na M3/M4/M5. Odblokuje M7/M9 kostru.
2. **M6b — diff + rollback-verify + hash:** `diff_report.json`, `rollback.json` + nulový-diff
   check, SHA vstupu před/po (G-01), validátor „1 skupina parametrů" (G-08). Pak M6 DoD testy.
3. **M6c — atomicita M6.10:** kopie+swap iterace, kill-test, last-known-good. Až po M6b.
4. **M7a — protokol + expected_results:** generátor z `ScenarioDefinitions.lua` + S1/S3
   (T-ACC-01, T-BRK-01 nejdřív — mají SIM krytí), `verdict_rule` nerovnosti, T-↔S trasabilita.
5. **M7b — formulář/result_schema + L1/L2/L3 + mode gating.** Odblokuje M8 loader.
6. **M8a — loader + R vs přesnost + n<3 INSUFFICIENT + outlier-flag.** Nad formulářem M7b,
   testovatelné na syntetických fixture bez Studia.
7. **M8b — iteration_advisor** (důvody NEXT/ACCEPTED/ROLLED-BACK). Vyžaduje M8a + M6b rollback.
8. **M9a — stavový stroj + workflow_state.json + report_generator (SIM-only).**
9. **M9b — import výsledků Studia + 2-iterace test + hash-originálu check (G-01).**
10. **M9c — plný M1→M8 workflow** — až po odblokování M2/M3/M5; do té doby M9s SIM-only s `mode` flagem.

Pořadí respektuje: paralelnost M6a/M7a (M7a čte Lua+S1/S3, ne M6 výstup — spojí se až v M9a),
sériovost M7b→M8a→M8b, M6b→M8b/M9b (rollback), vše→M9.

## 8. Testy vyžadované před dokončením každého modulu

Společné brány: G-01 (hash vstupu), G-02 (`validate_contracts.py` PASS), G-05 (PENDING≠PASS),
G-06/G-07 (`local-sim` ≠ runtime důkaz), G-08 (1 skupina/iterace), G-09 (rollback),
G-10 (reprodukovatelnost). PENDING se nezapočítává do PASS.

**M6 (7 pravidel + M6.10):**
- unit: determinismus (stejné vstupy → stejný balíček, byte-identický kromě run_id/stamp);
  nevalidní config → odmítnuto (fail-fast jako `normalize_config`); `cfg_/plan_/run_` ID
  unikátní a validní (`ids.require_valid`).
- integration: SHA originálu před/po generováním shodný (G-01); každá iterace unikátní ID;
  změny dohledatelné v historii (`param_diff` chain bez mezer); rollback → nulový diff
  proti last-known-good (G-09); kill-test M6.10 (pád uprostřed → předchozí iterace funkční).
- acceptance: všech 7 pravidel + atomicita M6.10 PASS; žádná auto-aplikace na originál.

**M7 (AC: postup + cíl s tolerancí + verdict_rule + jednotky + L-úroveň):**
- unit: každý test má `{target, unit, tolerance, min_repetitions, verdict_rule}` —
  chybějící číslo → generátor odmítne (protokol bez čísel se zamítá); schéma validuje
  prázdný i plný formulář; L3 test bez `environment.mode: roblox-runtime` → odmítnuto.
- integration: protokol `iteration_NNN` ↔ `expected_results.json` 1:1 (žádný test bez
  očekávání a naopak); podmínky == `ROBLOX-RUNTIME.md` prostředí Studia; opakování ≥ minima
  z `HYBRID_WORKFLOW.md` §3 (5/5/3+3/3/3).
- acceptance: člověk bez expertních znalostí provede test a odevzdá validní měření (DoD M7).

**M8 (8 pravidel + `n<3 → INSUFFICIENT`):**
- unit: průměr/odchylka/`Error_%`/medián/R na ručně spočtených fixture (3–5 vzorků);
  `R` a přesnost na fixture, kde se liší (vysoká R + dobrá přesnost a naopak);
  outlier fixture → flag + důvod, hodnota zachována.
- integration: nekompletní sada (`n<3` nebo chybějící metrika) → `INSUFFICIENT`, nikdy PASS;
  outlier se nezkracuje bez evidence; každé doporučení uvádí důvod; neúspěšná iterace
  vyvolá rollback (vazba M6b).
- acceptance: 8 pravidel PASS; lidská variabilita ≠ efekt změny (R a přesnost reportovány odděleně).

**M9 (9 pravidel + brána M9.12):**
- unit: stavový stroj — všechny přechody `PLANNED→…→(ACCEPTED|ROLLED-BACK|NEXT-ITERATION)`,
  nelegální přechod → odmítnuto; rollback na libovolnou (ne jen předchozí) iteraci.
- integration: kompletní SIM-only workflow s testovacím RBXM kopiemi + Mustang profilem;
  dvě po sobě jdoucí iterace (druhá staví na `best` z první); hash originálu nezměněn (G-01);
  import syntetického Studio-formuláře (M9.9) → `evaluation.json`; žádné runtime PASS
  bez Studio testu (G-06/G-07).
- acceptance: 9 pravidel PASS + brána M9.12 (G-01–G-10, archiv protokol+telemetrie+manifest
  na iteraci, `local-sim` ≠ runtime).

## 9. Rizika a otevřené body

1. M2 měřítko BLOCKED — M6 plný balíček a M9 plné workflow čekají; SIM-only větev je
   pojistka, ne náhrada (musí nést `mode` flag, jinak porušuje G-07).
2. Duplicita statistiky (`Telemetry/*` vs `Optimizer/*`) — rozhodnout zdroj pravdy před M8a.
3. Prostor má 2 knoby; M5/F4.3 wiring nových knobů změní `safety_filter`/`_diff_params`/
   `PARAM_DEFS` současně — M6 validátor G-08 na to musí být připraven (číst `search_space`, ne hardcode).
4. Binární artefakty v gitu (LFS?) — otevřený bod ARCHITECTURE §11, dopadá na M6/M9
   (telemetrie mimo git, manifest v gitu).
5. Lidský faktor M7/M8 (opakovatelnost) — F7.2 AC1–AC7 precedent pro přísnost prahů.
