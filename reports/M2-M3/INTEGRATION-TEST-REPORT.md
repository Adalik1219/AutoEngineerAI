# M2 Integrační test-report (Agent C)

**Vlastněný soubor:** `reports/M2-M3/INTEGRATION-TEST-REPORT.md` · **Datum:** 2026-11-19
**Větev:** `feat/m2-m3-geometry` · **HEAD:** `64be2c6` (re-verifikace §9; historické stavy: `4cad304` s nálezem I-1 FAIL, `c1a138b` s I-1 OPRAVENA — viz HISTORICKÝ STAV níže)
**Režim:** READ-ONLY vůči modulům A/B (pouze čtení; měněn jen tento report; `tests/test_m2_integration.py` existuje a NEMĚNĚN).
**Stav stromu:** na HEAD `64be2c6` jedna necommitnutá úprava mimo rozsah Agent C (`reports/M2/WHEEL-GEOMETRY-REPORT.md`, vlastník Agent B — ponecháno bez zásahu).
**Prostředí:** Windows 11, Python 3.14.9, stdlib unittest, vše **sériově** (žádná paralelizace).

> **HISTORICKÝ STAV (platil na HEAD `4cad304`):** integrační sada
> `tests.test_m2_integration` měla **19 PASS, 1 FAIL** — cílený pin-test
> `test_assess_blocked_propagates_to_report` (nález **I-1**: assess BLOCKED →
> report GEOMETRY_OK). Plná sada tehdy **372 běhů, PASS=367, FAIL=1,
> ERROR=0, PENDING=4**. Tento stav je uzavřen; aktuální
> re-verifikace na `c1a138b` je v §8 — **I-1 OPRAVEN, vše zelené.**

## 1. Rozsah a metoda

Ověřen řetězec na reálné kopii (hash `dc8747e0…fefdf`, 230 421 B, před/po):
`RBXM → parser → detect → assess → report → kalibrace`:
4 kola (rundy FL/FR/RL/RR), 44 known, report klíče dle freeze,
determinismus (dvojí běh), `null ≠ vymyšlené`, BLOCKED propagace.
Nový soubor `tests/test_m2_integration.py` (20 testů) — nic jiného neměněn.

## 2. Příkazy a výsledky (sériově, HEAD `c1a138b` — viz §8)

| Příkaz | Výsledek |
|---|---|
| `python -m unittest tests.test_m2_integration` | **20 PASS, 0 FAIL**, 0 ERROR (0.3 s) |
| `python -m unittest tests.test_m2_rbxm_parser tests.test_m2_rbxm_inspector tests.test_m2_wheel_detect tests.test_m2_scale_calibration tests.test_m2_integration` | **168 běhů, 168 PASS, 0 FAIL**, 0 ERROR (23.8 s) |
| `python tests/run_all.py` (plná sada) | **372 běhů, PASS=368, FAIL=0, ERROR=0, PENDING=4** |
| `python tools/validate_contracts.py` | **24 kontrol, 0 chyb, exit 0** |

(Historické hodnoty s I-1 FAIL na `4cad304`: viz HISTORICKÝ STAV v hlavičce.)
PENDING=4: beze změny očekávané (Studio/Fáze 5/Fáze 9-10), žádný se nezapočítává do PASS.

## 3. Naměřený řetěz na reálných datech

- **Hash před/po:** `dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf` shodný před i po celém řetězu, obě kopie (JeepTemplate + work-copy) shodné, 230 421 B. LIMIT: jediný distinctní model v repu.
- **Parser:** 815 instancí, 37 typů, kořen id 0, 1× `Model:Wheels`; 4× Ball (id 3/52/101/150), 104× Block + 1× Cylinder, **0 nepřečtených shape-enumů** (N1/MSB-first drží).
- **Detect:** 4× `WHEEL`/`VALID_WHEEL` (FL=3, FR=52, RL=101, RR=150), **44× `KNOWN_NON_WHEEL`** (11 jmen allowlistu × 4), `unidentified=[]`, `blocked=False`, status OK; deterministické (2× shodné).
- **Assess:** 4× `GEOMETRY_OK` se středy/rozměry, 44 known evidováno, `unidentified=[]`, celek **BLOCKED** — jediný důvod `float_decode_unverified` (kalibrace `NOT_IMPLEMENTED`). Předání `known_non_wheels` z detectu výsledek nemění.
- **Report:** klíče přesně 1:1 s freeze + nadstavba `known_non_wheels`; track_f/track_r ≈ 5.99, wheelbase ≈ 10.5228, pneu 2.7; `coordinate_frame.verified_in_studio=true`; **`overall_status: BLOCKED`** — I-1 opravena, assess BLOCKED se propaguje do reportu (viz §8).
- **Kalibrace** (měření z reportu): **BLOCKED** — „rozdíl odhadů 7.44 % > 5 %; deformovaný model"; `estimates=[]`, `combined_studs_per_meter=null` (žádná vymyšlená čísla); `usable_for_m3=false`, `require_verified_for_m3` vyhazuje → **brána M3 ZAVŘENA** (správně).
- **Determinismus G-10:** dvojí běh celého řetězu bitově shodný (vč. JSON reportu).
- **`null ≠ vymyšlené` (G-04):** chybějící kolo → `instance_id/center/size=null` + `reason=missing_wheel`, celek BLOCKED; samé `None` v kalibraci → UNKNOWN s `estimates=[]`.

## 4. Nálezy (chyby zaznamenány, předány — moduly A/B neměněny)

- **I-1 (OPRAVENO na `c1a138b`, původně nález na `4cad304`, vlastník Agent B / `wheel_detect.py::report_from_assess`): BLOCKED propagace assess→report NEFUNGOVALA.** Assess na reálných datech je BLOCKED (`float_decode_unverified`), ale `report_from_assess` převáděl `blocked_reasons` jen do `warnings` a report vycházel `GEOMETRY_OK`. Re-verifikace §8: assess `BLOCKED` → report **`BLOCKED`** (warnings obsahují `assess: float_decode_unverified…` + `BLOCKED: assess BLOCKED: float_decode_unverified…`); pin-test `test_assess_blocked_propagates_to_report` nyní **PASS** (20/20). Brána M3 je nově držena **oběma nohama** (inspekční BLOCKED + kalibrační BLOCKED 7.44 %). Uzavřeno.
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
| BLOCKED propagace M2→M3 | **PASS (I-1 opravena)** / brána M3 držena oběma nohama | assess BLOCKED → report BLOCKED; kalibrace BLOCKED + `require_verified_for_m3` vyhazuje |

## 6. `validate_contracts` — výsledek a co nekryje

- **Výsledek:** ÚSPĚCH — 24 kontrol, 0 chyb (9 schémat × validní+nevalidní vzor, `reference_profile` null+0.5 zamítnut / null+0 prošel, 4 vehicle-data reference + example-vehicle OK).
- **Co nekryje (mezera, ne chyba nástroje):** M2/M3 freeze kontrakty — `inspection_report.json`, `scale_calibration.json`, `geometry_target.json`, `geometry_diff.json` **nemají schéma v `contracts/`** a validátor je nekontroluje. Tvar reportu kryje pouze `INSPECTION_REPORT_SCHEMA` ve `wheel_detect.py` a integrační test klíčů (§3). Doporučení koordinátorovi: zvážit doplnění schémat (vlastník Agent B/C/E dle souboru).

## 7. Shrnutí pro koordinátora

- Integrace M2 je zelená: **368/372 PASS, 4 očekávané PENDING, 0 FAIL** — pin-test I-1 nyní PASS (BLOCKED propagace assess→report funguje); brána M3 držena oběma nohama (inspekce BLOCKED + kalibrace BLOCKED 7.44 %).
- Moduly A/B neměněny (read-only dodrženo); `tests/test_m2_integration.py` existoval a NEMĚNĚN, měněn pouze tento report.
- Další krok: I-1 uzavřena, I-2 (`float_decode_unverified` konzervativní BLOCKED) zůstává vědomé rozhodnutí koordinátora.

## 8. Final re-verification (HEAD `c1a138b`, 2026-11-19, sériově)

Vše spuštěno sériově z `C:/.DATA/AutoEngineerAI`, větev `feat/m2-m3-geometry`,
commit `c1a138b81cf82145b5995a19b73fd6e3e289e686`, čistý strom.

| # | Příkaz | Výsledek |
|---|---|---|
| 1 | `python -m unittest tests.test_m2_integration` | **20 testů, OK** (0.3 s) — vč. `test_assess_blocked_propagates_to_report` PASS |
| 2 | `python -m unittest tests.test_m2_rbxm_parser tests.test_m2_rbxm_inspector tests.test_m2_wheel_detect tests.test_m2_scale_calibration tests.test_m2_integration` | **168 testů, OK** (23.8 s) |
| 3 | `python tests/run_all.py` | **běhů=372 PASS=368 FAIL=0 ERROR=0 PENDING=4**; PENDING: Studio-měření, Fáze 5 schema-conformance, 2× Fáze 9/10 baseline/VariantStore (očekávané, nejsou PASS) |
| 4 | `python tools/validate_contracts.py` | **24 kontrol, 0 chyb, exit 0** |
| 5 | hash před/po (obě kopie čteny, žádný zápis) | `dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf`, 230 421 B, obě kopie shodné; řetěz vstup nemění (sha_before == sha_after) |
| 6 | G-brány (evidence z běhů 1–5 + cílené sondy) | **G-01 PASS** (hash před/po shodný) · **G-02 PASS** (24/0, reference `value_si + unit=m`) · **G-03 PASS** (reference `source + status`, report `method + warnings`) · **G-04 PASS** (vše-`None` → UNKNOWN + `estimates=[]`, žádná vymyšlená čísla) · **G-05 PASS** (4 PENDING odděleně) · **G-06/G-07 PASS** (report bez `run_id`/`roblox-runtime`/runtime statusu) · **G-10 PASS** (dvojí běh reportu bitově shodný) · **BLOCKED propagace PASS** (assess `BLOCKED [float_decode_unverified…]` → report `BLOCKED`; `usable_for_m3=false`, `require_verified_for_m3` vyhazuje `CalibrationBlockedError` → M3 ZAVŘENA) |

Naměřený řetěz (JeepTemplate): 815 instancí / 37 typů; detect OK (4× VALID_WHEEL FL=3/FR=52/RL=101/RR=150, 44 known, `unidentified=[]`); assess **BLOCKED** (`float_decode_unverified`); report **BLOCKED** (track_f 5.9907 / track_r 5.9907 / wheelbase 10.5228, pneu 2.7, `verified_in_studio=true`); kalibrace **BLOCKED** (rozptyl 7.44 % > 5 %).

## 9. Final re-verification (HEAD `64be2c6`, 2026-11-19, sériově, Agent C)

Rozdíl `c1a138b..64be2c6` = pouze docs commity (`e2a56ef`, `64be2c6`); `src/Inspection/`, `tests/test_m2*.py`, `tools/validate_contracts.py` beze změny → re-verifikace z §8 zůstává platná, níže čerstvý běh na aktuálním HEAD:

| # | Příkaz | Výsledek |
|---|---|---|
| 1 | `python -m unittest tests.test_m2_integration` | **20 testů, OK** (0.35 s) — vč. `test_assess_blocked_propagates_to_report` PASS (I-1 historicky uzavřena, netrvá) |
| 2 | `python -m unittest tests.test_m2_rbxm_parser tests.test_m2_rbxm_inspector tests.test_m2_wheel_detect tests.test_m2_scale_calibration tests.test_m2_integration` | **168 testů, OK** (~20 s) — rozpad 57+7+53+31+20 (viz audit §1; číslo 161 = starší součet bez inspektor-sady) |
| 3 | `python tests/run_all.py` (plná sada) | **běhů=372 PASS=368 FAIL=0 ERROR=0 PENDING=4** (PENDING očekávané: Studio-měření, Fáze 5 schema-conformance, 2× Fáze 9/10 baseline/VariantStore) |
| 4 | `python tools/validate_contracts.py` | **24 kontrol, 0 chyb, exit 0** (mezery krytí viz §6) |

G-brány na `64be2c6`: **G-01–G-07, G-10 všechny PASS; BLOCKED propagace M2→M3 PASS** (assess BLOCKED → report BLOCKED; kalibrace BLOCKED 7.44 % + `require_verified_for_m3` vyhazuje → M3 ZAVŘENA oběma nohama). Determinismus: integrační sada (dvojí běh, bitová shoda) PASS v běhu č. 1. Moduly A/B neměněny.
