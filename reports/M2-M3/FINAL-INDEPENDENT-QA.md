# Finální nezávislé QA — vlna M2/M3 geometrie (Agent D)

**Datum:** 2026-11-19 · **Větev:** `feat/m2-m3-geometry` · **PR #2 nemergován, žádné git operace**
**Režim:** READ-ONLY vůči kódu i testům (měněn pouze tento soubor).
**Báze diffu:** `4cad304` (QA re-konfirmace) → pracovní strom (8 modifikovaných + 2 nové: `tests/test_m2_integration.py`, `reports/M2-M3/INTEGRATION-TEST-REPORT.md`).
**Stav vlny:** 4-tier klasifikace, MSB-first, I-1 opraveno, kalibrace BLOCKED, M3 návrh bez kódu.

## 1. Diff vs 4cad304 — co se změnilo (ověřeno `git diff`)

- `src/Inspection/wheel_detect.py` (+179/−?): 4-tier `classify_candidate` (VALID_WHEEL / KNOWN_NON_WHEEL / UNKNOWN_CANDIDATE / INVALID_WHEEL), `CHASSIS_PART_ALLOWLIST` (11 názvů), `detect_wheels` eviduje `known_non_wheels` bez bloku; **I-1 oprava**: `report_from_assess` nově přebírá každý `assess blocked_reason` jako `assess_blocked_reasons` → report je vždy BLOCKED, když je assess BLOCKED (dřív se `float_decode_unverified`/kalibrační důvody házely jen do warnings a report vycházel GEOMETRY_OK).
- `src/Inspection/rbxm_parser.py` (+54): `assess_wheel_geometry(instances, known_non_wheels=None)` — allowlist/known_ids se evidují do `result["known_non_wheels"]`, neblokují; neznámí kandidáti blokují dál.
- `tests/test_m2_wheel_detect.py` (+273), `test_m2_scale_calibration.py` (+120), `test_m2_rbxm_parser.py` (+89): 4-tier testy, ESTIMATED-brána, JeepTemplate ground-truth (BLOCKED 7.44 %), NaN/edge testy.
- `reports/M3/GEOMETRY-ENGINE-PROPOSAL.md`: brána zpřísněna — M3 propouští **pouze VERIFIED** (`usable_for_m3`/`require_verified_for_m3`); ESTIMATED blokuje stejně jako chybějící.
- `src/Inspection/scale_calibration.py`: **beze změny** (pravidlo 2 rodin, práh 5 %/2 %, CalibrationError — vše drží).
- `src/Geometry/`, `geometry_target.json`, `geometry_diff.json`: **neexistují** — M3 bez kódu, správně.

## 2. Sériové běhy (vlastní, živě)

- Plná sada `python tests/run_all.py`: **372 běhů, PASS=368, FAIL=0, ERROR=0, PENDING=4** (4 PENDING očekávané: Studio/Fáze 5/Fáze 9-10, žádný se nezapočítává do PASS).
- Cílené M2: `test_m2_rbxm_parser + test_m2_wheel_detect + test_m2_scale_calibration + test_m2_integration` = **161 testů OK** (~18 s, sériově).

## 3. Adversariální sondy — 15/15 + I-1 (vlastní skript, stdlib, bez zápisu do repa)

| # | Sonda | Výsledek (očekávaný) |
|---|---|---|
| T01 | zdravá hierarchie 4× Ball FL/FR/RL/RR | OK, 4× VALID_WHEEL, deterministické |
| T02 | chybějící RR | BLOCKED (`missing_wheel`), RR=UNKNOWN |
| T03 | duplicitní FL | BLOCKED (`duplicate designation FL: 2 candidates`) |
| T04 | Block se jménem FL ve Wheels | BLOCKED, tier INVALID_WHEEL |
| T05 | Spare Ball ve Wheels | BLOCKED, tier UNKNOWN_CANDIDATE |
| T06 | Ball FR mimo Wheels (duplicita) | **neblokuje**, FR=id 52 drží (ochrana před záměnou) |
| T07 | známý díl Hub (Block) ve Wheels | **neblokuje**, evidován KNOWN_NON_WHEEL |
| T08 | prohozené strany FL↔FR (geometrie) | BLOCKED (`side_or_axle_swap`) |
| T09 | výšková asymetrie Y +0.38 | BLOCKED (`height_asymmetry`) |
| T10 | NaN střed kola | kolo UNKNOWN (`missing_geometry`), report UNKNOWN/BLOCKED — žádné číslo z NaN |
| T11 | `verified_in_studio=false` + zdravá geometrie | strop **UNKNOWN** |
| T12 | cyklus Wheels→FL | BLOCKED (`parent_cycle`) |
| T13 | kalibrace ESTIMATED | `usable_for_m3=false`, `require_verified_for_m3` vyhazuje |
| T14 | kalibrace UNKNOWN (vše None) | UNKNOWN + brána vyhazuje |
| T15 | kalibrace BLOCKED: JeepTemplate (rozptyl 7.44 %) + 1 rodina | obojí BLOCKED + brána vyhazuje |
| T16 | **I-1**: assess BLOCKED → `report_from_assess` | report **BLOCKED** (oprava potvrzena) |

Pozn.: T11 v první iteraci sondy selhala chybou sondy (prohozená geometrie z T08 měla přednost BLOCKED před stropem UNKNOWN); po opravě sondy na zdravou geometrii je strop UNKNOWN potvrzen.

## 4. Kalibrační brána V / E / U / B (ne Body)

- **VERIFIED** → jediný stav propuštěný do M3 (`usable_for_m3=true`).
- **ESTIMATED** (konzistentní, ale pneu/premium odhad) → brána ZAVŘENA (`CalibrationBlockedError`).
- **UNKNOWN** (žádná měření) → brána ZAVŘENA.
- **BLOCKED** (JeepTemplate 7.44 % > 5 %; < 2 rodiny) → `estimates=[]`, `combined=null`, brána ZAVŘENA.
- Nezávislý přepočet: wheelbase 3.870092, track_f 3.779597, track_r 3.648430, tire_d 3.93/3.84 studs/m → rozptyl 7.44 % → BLOCKED je **správné chování** (JeepTemplate ≠ Mustang), ne defekt.

## 5. Verdikt

- **M2: CONDITIONAL PASS.** Kód drží všechna pravidla (identita a+b+c, 4-tier, hierarchie, NaN/CFrame stropy, kalibrační prahy, I-1 propagace). Podmínky nejsou v kódu: (1) před mergem ještě jeden sériový `run_all.py` (flaky historie z paralelní vlny); (2) `git status` uklidit — untracked `reports/M2-M3/INTEGRATION-TEST-REPORT.md` + `tests/test_m2_integration.py` commitnout nebo vyřadit; (3) `float_decode_unverified` drží assess v BLOCKED i při bit-přesné Studio-shodě — konzervativní, ale text je fakticky zastaralý, aktualizovat po kalibrační vlně.
- **Brána M3: NEOTEVÍRAT.** Vstupy jsou BLOCKED/BLOCKED (inspekce BLOCKED přes assess-důvod + kalibrace BLOCKED 7.44 %); přísná VERIFIED-brána + I-1 propagace drží. M3 zůstává návrh bez kódu — správně.

## 6. Co nebylo ověřeno (limity)

Studio side (Edit-mode read-only, hash před/po), reálný Mustang (pracovní kopie je JeepTemplate — jediný distinctní model, 230 421 B, `dc8747e0…fefdf`), Play/Runtime nároky. Žádné P0/P1 v kódu; žádné runtime tvrzení v reportech.
