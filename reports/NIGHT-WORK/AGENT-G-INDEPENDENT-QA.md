# Agent G — nezávislá adversariální QA vlny S-02 (20. 11. 2026)

**Rozsah:** pouze čtení + vlastní běhy. Zapsán jediný soubor: tento report. Nic jiného neměněno.
**Větev:** `feat/m2-m3-geometry` · **výchozí SHA:** `557ee39cdfe4cd558dd4a1194c81adff6a2968fa`
**Finální stav:** HEAD beze změny (`557ee39…`), změny vlny necommitnuty v pracovním stromě.
**Prostředí vlastních běhů:** Windows 11, Python 3.14.9, `unittest` (repo-runner `tests/run_all.py`).

## 1. Git status / diff

- `git status --porcelain` (vs `557ee39`): `M docs/MAPPING.md` (§10),
  `M src/Chassis/mapping_engine.py` (`map_config`+`build_search_space` přes `_gate_records`),
  `M tests/test_f43_reconciliation.py`, `M tests/test_f4_integration.py` (−182/+~70),
  `M tests/test_f4_mapping.py`, `M tests/test_f4_optimizer_effect.py`,
  `M tests/test_m5_cycle_check.py` (+220); `?? src/Chassis/mapping/gate.py` (nová brána S-02)
  + `?? reports/NIGHT-WORK/` (A/B/C/D/E/F + WAVE-BASELINE).
- Trackované změny = přesně 7 souborů výše. `main` (`5b67315`, merge PR#1) beze změny,
  větev vlny do něj nemergována. **PR#2** nedotčeno (base `main`, head `feat/m1-m2-foundation`;
  žádné nové commity, G nic nepushoval).
- RBXM: `*.rbxm` git-ignorováno; obě pracovní kopie existují lokálně (230421 B),
  `git status` bez RBXM změn — READ-ONLY dodrženo.
- Simulator: žádná změna mimo výše uvedených 7 souborů + `gate.py` (tj. `src/Sim*`,
  `src/Optimizer`, adaptéry, `testgame/`, `assets/`, `contracts/` beze změny).

## 2. S-02 brána — vlastní ověření (ne převzato)

- Katalog: **138 záznamů / 101 `depends_on` položek** (smíšené `str` + `{'param':…}` dict).
- `gate_catalog_file` nad reálným katalogem (vlastní běh): `BLOCKED`, `allowed=False`,
  reason `CYCLE: … (tcs_threshold_sps -> tcs_gradient -> tcs_threshold_sps)`,
  witness `['tcs_threshold_sps', 'tcs_gradient', 'tcs_threshold_sps']`.
- Svědek ověřen hranu po hraně proti surovému grafu:
  `tcs_threshold_sps -> tcs_gradient` EXISTUJE ✅, `tcs_gradient -> tcs_threshold_sps` EXISTUJE ✅.
  Uzavřená cesta délky 3. Jde o **reálný 2-cyklus v katalogu**, ne artefakt.
- Povinný graf `a->[b,c], b->[c], c->[a]` (vlastní běh): `has_cycle=True`, svědek `['a','b','c','a']`,
  brána `BLOCKED/CYCLE (a -> b -> c -> a)`. ✅
- Negativní sondy (vlastní běh přes bránu): cyklický katalog → `BLOCKED/CYCLE`, ne `PASS` ✅;
  neexistující id → `BLOCKED/INTEGRITY (a -> ghost)` — **jiný důvod než cyklus**, ne `PASS` ✅;
  cyklus+integrita → `INTEGRITY` (integrita první — deterministické pořadí); DAG → `OK`. ✅
- Nulová změna při BLOCKED (vlastní sonda): `map_config` nad reálným katalogem — vstupní dict
  bitově nezměněn, `tune_changes=[]`, jediné `rejected=[{param:*catalog*, reason:CYCLE…}]` + warning.
  Chybějící soubor → `INVALID`, rovněž atomické. ✅
- Oba entry pointy: `map_config` → `*catalog*/CYCLE BLOCKED`; `build_search_space` → `[]`
  (důvod přes `gate_catalog_file`). Brána je v obou cestách PRVNÍ, před jakoukoli prací;
  dict-dep `{'param':…}` se normalizují na hrany (`_normalize_for_detector`) — žádná cesta bez
  brány, žádná paralelní validace. ✅
- Poznámka k „12 SCC" (audit A): detektor garantuje existenci + 1 svědka, ne enumeraci;
  alespoň 1 cyklus je prokázán výše; SCC-seznam je manuální analýza, ne výstup detektoru.

## 3. Sporné body — rozhodnutí

- **(a) `qa depends_on qa_tcount` → `engine.turbo.count`: ROZHODNUTO PRO C.** Doslovný návrh B
  byl chybný (fiktivní id `qa_*`); přejmenování na reálné `engine.turbo.count` je správně.
  Turbo-sémantika ověřena vlastní sondou na acyklickém vzorku: `count=0,boost=10` → boost
  REJECTED (`hodnota 0 < požadované minimum 1`), count mapován; `count=2` → oba mapovány.
  **count=0 → boost BLOCKED drží.**
- **(b) Diff `test_f4_integration` −182: ROZHODNUTO — žádný FAIL neskryt.** `run_all` má
  0 FAIL/0 ERROR (§5). Sim-krytí není ztraceno: `test_brakes_bias_change_moves_stopping_distance`
  běží **reálný Sim 2×** (bias 0.62/0.70 → Δ brzdné dráhy > 1 m, vlastní běh prošel);
  `test_final_drive…` běží reálný Sim 2× (Δ t_0_100 > 0.05 s). Odstraněna je jen Sim/evaluate část
  `test_chain…`, která za BLOCKED bránou nemá vstup — a je to v testu explicitně zdůvodněno, ne tiše.
- **(c) 2 vakuové testy: POTVRZENO, oba procházejí vakuově.** `test_sim_runs_on_patched_config_not_original`
  (prázdný tune → rovnosti triviální; Sim se vůbec nespouští, jen file round-trip) a
  `test_f4_11_neoverene_hodnoty_se_neaplikuji` (`len(rejected)==1` platí shodou pro `*catalog*`,
  ne pro tvrzené per-klíč odmítnutí). Agent C je sám eviduje — přiznané, ne skryté.
  **Navíc třetí částečné vakuum, C nepřiznal:** `test_final_drive_change_moves_metric_or_unsupported` —
  mapovací noha je za BLOCKED bránou mrtvá (hodnota proteče passthrough, ne mappingem); Sim-noha
  (citlivost metriky) je pravá. Test prochází a nic neskrývá, ale jméno slibuje víc, než dokazuje.
- **(d) CI vs local `test_limit_single_distinct_model`: PŘÍČINA = PROSTŘEDÍ, ne kód.** Test SKIPpuje
  při `<2` kopiích; `*.rbxm` je v `.gitignore`, takže CI checkout druhou kopii nemá (PENDING),
  lokálně existují obě (PASS). Obě čísla pravdivá ve svém prostředí. Doporučení: do CI reportu psát
  počet nalezených kopií, ať je SKIP auditovatelný.

## 4. Strategie — Jeep vs. Mustang, A-Chassis, UNKNOWN, PROPOSED

- Jeep ≠ Mustang: F-report §8 — „Jeep data: v použitých zdrojích se nevyskytují; nic z nich není
  převzato"; Mustang cíle z `vehicle-data/references/ford-mustang-gt-2024-…json`. V kódu žádný
  Jeep→Mustang přenos hodnot nenalezen. ✅
- A-Chassis nedotčeno: adaptéry (`src/Chassis/adapters/`) beze změny; měněn jen `mapping_engine.py`
  + nové `gate.py`. ✅
- Chybějící = UNKNOWN: katalog `PASS 95 / PENDING 43`, kategorie `MUTABLE_TUNE 82 / UNKNOWN 37 / …`;
  engine default `UNKNOWN` (`mapping_engine.py:61,96,113`). ✅
- Schémata PROPOSED: `contracts/proposed/*.schema.json` — popis „PROPOSED — čeká na schválení",
  `git status` beze změny. ✅ (E-report je audit, nic neschválil.)

## 5. Vlastní běhy (nepřebrána žádná čísla)

| Běh | Výsledek |
|---|---|
| `python -m unittest tests.test_m5_cycle_check` | **39/39 OK** |
| `python tests/run_all.py` (plná sada) | **běhů 443 / PASS 439 / FAIL 0 / ERROR 0 / PENDING 4** (Studio-měření, schema-conformance, baseline-exists, variant-store-append-only) |
| `python tools/validate_contracts.py` | **24 kontrol / 0 chyb** |
| `python -m unittest tests.test_module_contracts` | 45 běhů OK (1 skip) |

Shoda s tvrzenými čísly (443/439/0/0/4, S-02 39/39, kontrakty 24/24) — **ověřena nezávislým během.**

## 6. Verdikt: CONDITIONAL PASS

Brána je správná, atomická, krytá z obou entry pointů; svědek platí hrana po hraně; turbo-sémantika drží; strategie držena; čísla sedí; 0 FAIL; Sim-krytí zachováno reálnými běhy. Vakuové testy procházejí, ale nedokazují svá jména.
**Podmínky:** (1) 2 přiznaná vakuua + mapovací noha `test_final_drive…` zůstávají explicitně označena jako oslabená bránou; (2) s acyklickým katalogem (náprava Agent A) se vrátí per-klíč odmítnutí, plný `test_chain…` včetně Sim/evaluate, a mapovací noha final_drive — do té doby žádný z těchto testů nesmí být citován jako důkaz per-klíč chování; (3) G-report příští vlny ověří (1)–(2) znovu vlastním během.

## Doložka 2026-11-20 — HISTORICKÝ STAV (nepřepisovat)
Tento report popisoval stav k `bc6f955`+dirty. Podmínky (1)–(3) jsou SPLNĚNY: C1 per-klíč test přidán, FinalDrive fixture auto-validována, vakuua V1–V3 opravena a G-potvrzena (AGENT-C-VACUOUS-TEST-REVIEW, AGENT-G-TEST-INDEPENDENT-REVIEW). Aktuální verdikt viz AGENT-G-FINAL-NEXT-WAVE-QA a NEXT-WAVE-FINAL-CLOSEOUT.
