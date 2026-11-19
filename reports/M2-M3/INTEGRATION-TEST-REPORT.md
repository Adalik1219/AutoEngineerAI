# M2 Integrační test-report (Agent C)

**Vlastněný soubor:** `reports/M2-M3/INTEGRATION-TEST-REPORT.md` · **Datum:** 2026-11-19
**Větev:** `feat/m2-m3-geometry` · **HEAD:** `4cad304` (QA re-konfirmace na 32dd690)
**Režim:** READ-ONLY vůči modulům A/B (pouze čtení; měněn jen tento report + `tests/test_m2_integration.py`, nový).
**Stav stromu:** HEAD + uncommitted A+B+assess+E (PR #2 nemergován; 8 modifikovaných souborů, 1 nový).
**Prostředí:** Windows 11, Python 3.14.9, stdlib unittest, vše **sériově** (žádná paralelizace).

## 1. Rozsah a metoda

Ověřen řetězec na reálné kopii (hash `dc8747e0…fefdf`, 230 421 B, před/po):
`RBXM → parser → detect → assess → report → kalibrace`:
4 kola (rundy FL/FR/RL/RR), 44 known, report klíče dle freeze,
determinismus (dvojí běh), `null ≠ vymyšlené`, BLOCKED propagace.
Nový soubor `tests/test_m2_integration.py` (20 testů) — nic jiného neměněn.

## 2. Příkazy a výsledky (sériově)

| Příkaz | Výsledek |
|---|---|
| `python -m unittest tests.test_m2_integration` | **19 PASS, 1 FAIL**, 0 ERROR (0.3 s) |
| `python -m unittest tests.test_m2_rbxm_parser tests.test_m2_rbxm_inspector tests.test_m2_wheel_detect tests.test_m2_scale_calibration tests.test_m2_integration` | **168 běhů, 167 PASS, 1 FAIL**, 0 ERROR (18.8 s) |
| `python tests/run_all.py` (plná sada) | **372 běhů, PASS=367, FAIL=1, ERROR=0, PENDING=4** |
| `python tools/validate_contracts.py` | **24 kontrol, 0 chyb, exit 0** |

Jediný FAIL v celé sadě je `test_assess_blocked_propagates_to_report` (§4, nález I-1).
PENDING=4: beze změny očekávané (Studio/Fáze 5/Fáze 9-10), žádný se nezapočítává do PASS.

## 3. Naměřený řetěz na reálných datech

- **Hash před/po:** `dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf` shodný před i po celém řetězu, obě kopie (JeepTemplate + work-copy) shodné, 230 421 B. LIMIT: jediný distinctní model v repu.
- **Parser:** 815 instancí, 37 typů, kořen id 0, 1× `Model:Wheels`; 4× Ball (id 3/52/101/150), 104× Block + 1× Cylinder, **0 nepřečtených shape-enumů** (N1/MSB-first drží).
- **Detect:** 4× `WHEEL`/`VALID_WHEEL` (FL=3, FR=52, RL=101, RR=150), **44× `KNOWN_NON_WHEEL`** (11 jmen allowlistu × 4), `unidentified=[]`, `blocked=False`, status OK; deterministické (2× shodné).
- **Assess:** 4× `GEOMETRY_OK` se středy/rozměry, 44 known evidováno, `unidentified=[]`, celek **BLOCKED** — jediný důvod `float_decode_unverified` (kalibrace `NOT_IMPLEMENTED`). Předání `known_non_wheels` z detectu výsledek nemění.
- **Report:** klíče přesně 1:1 s freeze + nadstavba `known_non_wheels`; track_f/track_r ≈ 5.99, wheelbase ≈ 10.5228, pneu 2.7; `coordinate_frame.verified_in_studio=true`; **`overall_status: GEOMETRY_OK`** (viz nález I-1).
- **Kalibrace** (měření z reportu): **BLOCKED** — „rozdíl odhadů 7.44 % > 5 %; deformovaný model"; `estimates=[]`, `combined_studs_per_meter=null` (žádná vymyšlená čísla); `usable_for_m3=false`, `require_verified_for_m3` vyhazuje → **brána M3 ZAVŘENA** (správně).
- **Determinismus G-10:** dvojí běh celého řetězu bitově shodný (vč. JSON reportu).
- **`null ≠ vymyšlené` (G-04):** chybějící kolo → `instance_id/center/size=null` + `reason=missing_wheel`, celek BLOCKED; samé `None` v kalibraci → UNKNOWN s `estimates=[]`.

## 4. Nálezy (chyby zaznamenány, předány — moduly A/B neměněny)

- **I-1 (NOVÉ, vlastník Agent B / `wheel_detect.py::report_from_assess`): BLOCKED propagace assess→report NEFUNGUJE.** Assess na reálných datech je BLOCKED (`float_decode_unverified`), ale `report_from_assess` převádí `blocked_reasons` jen do `warnings` a report vychází `GEOMETRY_OK`. Před 4-tier změnou (QA verdikt v1) byl report na stejných datech BLOCKED — chování se tiše otočilo bez rozhodnutí. Pinováno testem `test_assess_blocked_propagates_to_report` (FAIL). Brána M3 zůstává zavřená přes kalibrační nohu (BLOCKED 7.44 %), takže bezprostřední únik nehrozí, ale inspekční noha brány je nyní zelená na datech, která assess odmítá — **B rozhodne: buď propagovat BLOCKED, nebo zdůvodnit, proč je GEOMETRY_OK správně** (pak test upraví vlastník brány, ne QA).
- **I-2 (potvrzeno, bez změny): `float_decode_unverified` je fakticky zastaralý** (Studio ground-truth existuje, bit-přesná shoda), ale drží assess v BLOCKED konzervativně — ponecháno se souhlasem koordinátora (QA verdikt dodatek §2).
- Bez nových nálezů k parseru (MSB-first, census, shape-cross-check drží) a ke kalibraci (pravidlo 2 referencí, prahy 5 %/2 %, `CalibrationError` na null/NaN/nulu/zápor/špatnou jednotku — vše PASS).

## 5. Brány G-01–G-07, G-10

| Brána | Verdikt | Důkaz |
|---|---|---|
| G-01 RBXM nezměněn | **PASS** | SHA před/po shodný, obě kopie, 230 421 B |
| G-02 jednotky | **PASS** | `validate_contracts` 24/0; kalibrační reference `value_si + unit=m`; report studs |
| G-03 provenance | **PASS** | reference `source + status`; report `method + warnings` |
| G-04 null ≠ odhad | **PASS** | testy: missing_wheel→null, UNKNOWN→`estimates=[]`, BLOCKED→null scale |
| G-05 PENDING ≠ PASS | **PASS** | 4 PENDING odděleně, nezapočítáno; chybějící fixture → SKIP |
| G-06/G-07 žádný runtime claim | **PASS** | report bez `run_id`/`roblox-runtime`/runtime statusu (jen code-verified) |
| G-10 reprodukovatelnost | **PASS** | dvojí běh řetězu bitově shodný |
| BLOCKED propagace M2→M3 | **FAIL (I-1)** / brána M3 držena kalibrací | assess BLOCKED → report GEOMETRY_OK; M3 zavřena přes `require_verified_for_m3` |

## 6. `validate_contracts` — výsledek a co nekryje

- **Výsledek:** ÚSPĚCH — 24 kontrol, 0 chyb (9 schémat × validní+nevalidní vzor, `reference_profile` null+0.5 zamítnut / null+0 prošel, 4 vehicle-data reference + example-vehicle OK).
- **Co nekryje (mezera, ne chyba nástroje):** M2/M3 freeze kontrakty — `inspection_report.json`, `scale_calibration.json`, `geometry_target.json`, `geometry_diff.json` **nemají schéma v `contracts/`** a validátor je nekontroluje. Tvar reportu kryje pouze `INSPECTION_REPORT_SCHEMA` ve `wheel_detect.py` a integrační test klíčů (§3). Doporučení koordinátorovi: zvážit doplnění schémat (vlastník Agent B/C/E dle souboru).

## 7. Shrnutí pro koordinátora

- Integrace M2 je poctivá: **367/372 PASS, 4 očekávané PENDING, 1 cílený FAIL (I-1)** — nový test pinuje regresi BLOCKED propagace ze 4-tier změny; brána M3 zůstává správně zavřená (kalibrace BLOCKED 7.44 %).
- Moduly A/B neměněny (read-only dodrženo); jediný nový soubor `tests/test_m2_integration.py` + tento report.
- Další krok: **Agent B rozhodne I-1** (propagovat BLOCKED vs. zdůvodnit GEOMETRY_OK), poté zelený sériový `run_all` bez FAIL.
