# Nezávislý QA verdikt vlny 1 — M2 + brána M3 (Agent F)

**Datum:** 2026-11-19 · **Větev:** `feat/m2-m3-geometry` · **HEAD:** `8b30447`
**Režim:** READ-ONLY vůči kódu i testům (měněn pouze tento soubor).
**Zdroje (čteno):** diff `8b30447`, `reports/M2/*.md` (4 reporty),
`reports/M3/GEOMETRY-ENGINE-PROPOSAL.md`, `reports/M2-M3-CONTRACTS-FREEZE-v1.md`,
`reports/M2-M3/INDEPENDENT-QA-PLAN.md`, + untracked `reports/M2/SHAPE-CROSS-CHECK.md` (Agent D, follow-up k N1).

## Verdikt M2: CONDITIONAL PASS (podmíněné ANO)

## Brána M3: NEOTEVÍRAT (zůstává zavřená — správně)

---

## 1. Plný běh testů (ověřeno živě)

- `python tests/run_all.py`: **317 běhů, PASS=313, FAIL=0, ERROR=0, PENDING=4** (4 PENDING očekávané, žádný se nezapočítává do PASS).
- Cílené M2 sady: `test_m2_rbxm_parser` + `test_m2_rbxm_inspector` + `test_m2_wheel_detect` + `test_m2_scale_calibration` = **113/113 OK** (54+7+34+18).
- Flaky FAIL z paralelní vlny (`test_m2_wheel_detect`, hlášen Agentem C) **nereprodukován** — plná sada i cílená sada prošly sériově bez chyby. Potvrzen závěr commitu (artefakt souběžných editů). Před mergem doporučuji ještě jeden sériový běh.

## 2. Bloky dle QA plánu

| Blok | Verdikt | Důkaz |
|---|---|---|
| P1–P6 Parser/hierarchie | **PASS s výhradou** (N1) | 54 testů OK; hash `dc8747e0…fefdf` (230 421 B) shodný; census 37/815/928; 879 `skipped_props`; read-only drží. Výhrada = N1 níže. |
| W1–W6 Kola / strany / nápravy | **PASS** | 34 testů OK; 4× Ball 2.7³ id 3/52/101/130→150 potvrzena; rámec x=lateral/y=up/z=long. proti návrhu příkazu (rozpor explicitně zdokumentován, test `test_coordinate_frame_is_actual_not_command_convention`); 44 dílů podvozku → BLOCKED drží (ověřeno end-to-end, §4). |
| K1–K6 Kalibrace | **PASS** | 18 testů OK; pravidlo 2 referencí/rodin, prahy 5 %/2 %, `CalibrationError` na null/NaN/nulu/zápor/špatnou jednotku — vše ověřeno vlastními sondami (A6–A9 níže). `usable_for_m3` jen pro VERIFIED. |
| S1–S4 Studio ground-truth | **PASS s výhradou** | Bit-přesná shoda Studio↔parser ve 13 řádcích (rozchod 5.99066162109375 / 5.99072265625, rozvor 10.522796630859375 / 10.52276611328125, Y-spread 0.0); P1–P3 PENDING vázané na Play, nezapočítáno do PASS. Výhrada = zastaralý důvod `float_decode_unverified` (§4). |
| M1–M5 M3 | **PASS (návrh) / produkce BLOKOVÁNA** | Pouze `GEOMETRY-ENGINE-PROPOSAL.md`, žádný kód (`src/Geometry/` ani `geometry_target.json` neexistují — ověřeno). Návrh konzistentní s FREEZE (§7 brána, `value: null` při BLOCKED). |
| A1–A8 Adversarial | **8/8 dle očekávání** | viz §3. |

## 3. Adversarial sondy (vlastní skript, stdlib, bez zápisu do repa)

- **A1 prohozené strany (FL↔FR instance):** `detect_wheels` je jménová identita → tiše přeřadí (OK, FL→id52). Není to díra: rohová kontrola ve writeru (`F=větší Z, L=větší X`) hlásí `side_or_axle_swap` → **BLOCKED**. Vrstvená obrana, zdokumentováno.
- **A2 Block se jménem FL:** FL=UNKNOWN (`bad_shape`), celek **BLOCKED**, záznam v `unidentified`.
- **A3 duplicitní FL:** **BLOCKED** (`duplicate designation FL: 2 candidates`).
- **A4 chybějící kolo:** **BLOCKED** (`missing_wheel`).
- **A5/A5b Wheels chybí / přejmenován:** **BLOCKED** (`missing Model:Wheels`), nikdy 4× WHEEL.
- **A6 kalibrace s 1 referencí:** **BLOCKED** + `blocked_reason` (< 2 nezávislé rodiny).
- **A7 rozporná měřítka (track_f +12 %):** **BLOCKED** (rozptyl 14.97 % > 5 %).
- **A8 `value_si: null` + status VERIFIED:** `CalibrationError` (výjimka, ne tichý odhad). **A9 NaN měření:** `CalibrationError`.
- **NaN CFrame ve writeru:** kolo UNKNOWN (`missing_geometry`), report strop **UNKNOWN** — žádné číslo z NaN.
- **Neověřený rámec (`verified_in_studio=false`):** strop **UNKNOWN**, nikdy GEOMETRY_OK.
- **Parser kontrakty:** prázdný/zkrácený blob → `RbxmCorruptError`.
- **Schema writeru:** klíče přesně 1:1 s FREEZE (`report_id … overall_status`).

## 4. Nezávislý přepočet měřítka (parserová čísla)

Z parseru/ground-truth: rozvor 10.5227813720703125, track_f 5.99066162109375, track_r 5.99072265625, pneu 2.7.
Proti M1 referencím (2.719 / 1.585 / 1.642 / 0.6866 / 0.7026 m):

| pár | studs/m |
|---|---|
| wheelbase | 3.870092 |
| track_f | 3.779597 |
| track_r | 3.648430 |
| tire_d_f | 3.932421 |
| tire_d_r | 3.842869 |

Rozptyl **7.44 % > 5 %** → `calibrate()` vrací **BLOCKED** („nekonzistentní měřítko… model je deformovaný"). **To je správné chování, ne defekt:** pracovní kopie je JeepTemplate, ne Mustang — kalibrace to poctivě odmítla místo tichého průměru. End-to-end na reálných datech: `assess` BLOCKED (44 UNKNOWN ve Wheels + `float_decode_unverified`), `report_from_assess` → `overall_status: BLOCKED`. **BLOCKED propagace M2→M3 funguje.**

## 5. Podmínky CONDITIONAL PASS (držitelé = vlastníci souborů, ne QA)

1. **N1 lane-pořadí enum (vlastník `src/Inspection/rbxm_parser.py`):** untracked `SHAPE-CROSS-CHECK.md` (Agent D) potvrzuje hypotézu MSB-first — parser dekóduje Block=1 jako `16777216` → `unread` (104× Part + 1× Cylinder). Chování je **fail-safe** (nikdy špatný tvar, kola Ball=0 invariantní), ale 105 dílů je slepých. Rozhodnout: MSB-first dekodér s re-verifikací, nebo ponechat + opravit dokumentaci. **Do vyřešení se nesmí věřit žádnému non-Ball tvaru z parseru.**
2. **Zastaralý `float_decode_unverified` (vlastník `rbxm_parser.py`):** Studio ground-truth od jeho napsání existuje (bit-přesná shoda, §S). Důvod drží reálnou inspekci v BLOCKED spolu s legitimními 44 díly podvozku — konzervativní, ale text je fakticky zastaralý. Aktualizovat/odstranit po kalibrační vlně.
3. **Před mergem:** jeden sériový `run_all.py` (flaky historie) + `git status` uklidit (untracked `SHAPE-CROSS-CHECK.md` buď commitnout, nebo vyřadit).
4. **Tire designace** (ověřeno: `19·25.4+2·255·40/100=686.6`, `275/40 R19=702.6`) zůstávají ESTIMATED s tolerancí dezénu — nikdy je nepovýšit na VERIFIED bez měření.

## 6. Brána M3: NEOTEVÍRAT — důvody

1. `inspection_report` na reálných datech = **BLOCKED** (požadováno GEOMETRY_OK).
2. `scale_calibration` na reálných datech = **BLOCKED** (požadováno VERIFIED/ESTIMATED; rozptyl 7.44 %).
3. Rámec `verified_in_studio=true` sice drží, ale brána vyžaduje všechny tři podmínky.
4. M3 je správně jen návrh bez kódu — otevření brány by dnes znamenalo cíle z nekonzistentního měřítka. **M3 fáze B až po splnění podmínek §5 + GEOMETRY_OK/VERIFIED na datech.**

## 7. Shrnutí pro koordinátora

- M2 vlna 1 je poctivá práce: testy 313/0/4 PENDING, adversarial sada 8/8, nezávislý přepočet souhlasí s producentem (BLOCKED při 7.44 %), propagace BLOCKED ověřena end-to-end.
- Jediné věcné nálezy (N1/MSB-first, zastaralý důvod) jsou zdokumentované, fail-safe a mimo kritickou cestu kol; proto **CONDITIONAL PASS**, ne FAIL.
- **M3 neotevírat.** Další krok: vlastník parseru rozhodne N1 → poté re-verifikace a nová kalibrační data.
