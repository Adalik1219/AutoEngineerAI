# Agent C — Integration & Calibration Audit (M2–M3)

**Větev:** `feat/m2-m3-geometry` · **HEAD:** `64be2c6` · **Datum:** 2026-11-19
**Režim:** READ-ONLY vůči `src/` (pouze čtení + běhy testů); měněny jen reporty.
**Zdroje:** `reports/M2-M3/INTEGRATION-TEST-REPORT.md` (§1–§9), `reports/M2/SCALE-CALIBRATION-REPORT.md` (§0–§9), `src/Inspection/rbxm_parser.py` (`calibrate_studs_per_meter`, assess `block(...)`), `src/Inspection/scale_calibration.py` (čtení), živé běhy níže.

## 1. Počty testovacích sad — 168 vs 161

Živý běh na `64be2c6` (sériově, každá sada zvlášť + dohromady):

| Sada | Běhů | Stav |
|---|---|---|
| `tests.test_m2_rbxm_parser` | 57 | OK |
| `tests.test_m2_rbxm_inspector` | 7 | OK |
| `tests.test_m2_wheel_detect` | 53 | OK |
| `tests.test_m2_scale_calibration` | 31 | OK |
| `tests.test_m2_integration` | 20 | OK |
| **Součet / společný běh** | **57+7+53+31+20 = 168** | **OK** |

**Vysvětlení 161:** `57+53+31+20 = 161` je součet **bez inspektor-sady** (`test_m2_rbxm_inspector`, 7 testů) — starší/oralní číslo ze 4 sad. Úplný aktuální součet všech 5 M2 sad je **168** (společný běh `Ran 168 tests … OK` to potvrzuje aritmeticky i exekučně). Žádný test nechybí ani nepřebývá; plná sada `tests/run_all.py` hlásí **372 běhů / PASS=368 / FAIL=0 / ERROR=0 / PENDING=4** (PENDING očekávané: Studio-měření, Fáze 5 schema-conformance, 2× Fáze 9/10 baseline/VariantStore — nejsou PASS).

## 2. I-1 — historicky označeno

- **Nález (HEAD `4cad304`, nálezová verze):** integrační sada 19 PASS / 1 FAIL — pin-test `test_assess_blocked_propagates_to_report` FAIL: `report_from_assess` převáděl `blocked_reasons` jen do `warnings` a report vycházel `GEOMETRY_OK`, ač assess byl BLOCKED (`float_decode_unverified`). Vlastník opravy Agent B (`wheel_detect.py::report_from_assess`).
- **Oprava (HEAD `c1a138b`):** assess BLOCKED → report **BLOCKED** (20/20 PASS). **Na `64be2c6` čerstvě potvrzeno: 20/20 OK** — I-1 je uzavřená historie, netrvá.
- **I-2 (vědomé, bez změny):** `float_decode_unverified` drží assess v BLOCKED konzervativně, ač Studio ground-truth existuje — ponecháno se souhlasem koordinátora.

## 3. `calibrate_studs_per_meter` (parser) vs kalibrační engine — rozdíl zdokumentován

Ověřeno čtením obou implementací (žádný rozpor, dvě různé vrstvy):

- **`rbxm_parser.calibrate_studs_per_meter()`** = záměrný STUB rozhraní: **vždy** vrací `status: NOT_IMPLEMENTED`, `studs_per_meter: None`, `reason` = chybí Studio ground-truth + neověřené dekódování floatů. Nikdy nevrací ověřenou hodnotu — dle designu (M2 nemá prohlašovat měřítko za ověřené).
- **`scale_calibration.calibrate()`** = skutečný ENGINE (M2.9/M2.10, IMPLEMENTED): počítá `studs_per_meter = meas_studs / value_si_m` z nezávislých rodin (wheelbase / track / tire_diameter), kombinace inverse-variance, BLOCKED-pořadí (UNKNOWN → <2 rodiny → rozptyl >5 %), VERIFIED jen vše-VERIFIED + max|odchylka| ≤2 %, jinak ESTIMATED. Brána `usable_for_m3()` / `require_verified_for_m3()` propouští **POUZE VERIFIED**.
- **Assess-důvod:** `assess` v `rbxm_parser.py` vždy končí `block("float_decode_unverified: … kalibrace NOT IMPLEMENTED")` — celek BLOCKED, dokud M3 nedodá ground-truth. To je konzistentní s oběma body výše, ne rozpor.
- Žádné NEOVĚŘENO nezbylo: rozdíl je záměrný a testy ho kryjí (stub-chování + `TestJeepTemplateGroundTruth` BLOCKED 7.44 % + `TestM3Gate`).

## 4. G-brány — verdikty na `64be2c6`

| Brána | Verdikt | Důkaz (běhy §1 + cílené sondy z integračního reportu §8–§9) |
|---|---|---|
| G-01 RBXM nezměněn | PASS | SHA před/po `dc8747e0…fefdf`, 230 421 B, obě kopie |
| G-02 jednotky | PASS | `validate_contracts` 24/0; reference `value_si + unit=m` |
| G-03 provenance | PASS | reference `source + status`; report `method + warnings` |
| G-04 null ≠ odhad | PASS | missing_wheel→null + `missing_wheel`; vše-None→UNKNOWN + `estimates=[]` |
| G-05 PENDING ≠ PASS | PASS | 4 PENDING odděleně, nezapočítáno do PASS |
| G-06/G-07 žádný runtime claim | PASS | report bez `run_id`/`roblox-runtime`/runtime statusu |
| G-10 reprodukovatelnost | PASS | dvojí běh řetězu bitově shodný (integrační sada) |
| BLOCKED propagace M2→M3 | PASS | assess BLOCKED → report BLOCKED; kalibrace BLOCKED + `require_verified_for_m3` vyhazuje → M3 ZAVŘENA |

## 5. `validate_contracts` — 24/0 a co nekryje

- **Výsledek (živý běh `64be2c6`):** 24 kontrol, 0 chyb, exit 0 (9 schémat × validní+nevalidní vzor, `reference_profile` null+0.5 zamítnut / null+0 prošel, 4 vehicle-data reference + example-vehicle OK).
- **Co nekryje (mezera, ne chyba nástroje):** M2/M3 freeze kontrakty — `inspection_report.json`, `scale_calibration.json`, `geometry_target.json`, `geometry_diff.json` **nemají schéma v `contracts/`** a validátor je nekontroluje. Tvar kryje pouze `INSPECTION_REPORT_SCHEMA` ve `wheel_detect.py` + integrační test klíčů. Doporučení koordinátorovi: zvážit doplnění schémat.

## 6. Shrnutí pro koordinátora

- Integrace M2 zelená na `64be2c6`: **168/168 M2 sad OK, plná sada 368/372 PASS + 4 očekávané PENDING, 0 FAIL**; I-1 historicky uzavřena; M3 brána držena oběma nohama (inspekce BLOCKED + kalibrace BLOCKED 7.44 %).
- Kód neměněn (read-only dodrženo); změněny jen 3 vlastněné reporty (tento audit nový).
- Otevřené: skutečná mustangovská kalibrace čeká na RBXM měření + Studio ground-truth (mimo rozsah Agent C); do té doby každý reálný výstup UNKNOWN/BLOCKED a M3 NOT READY trvá.
