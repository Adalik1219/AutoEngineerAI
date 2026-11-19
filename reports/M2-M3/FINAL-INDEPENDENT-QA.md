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

---

## 7. Final QA – post remediation verification (Agent D, 2026-11-19, HEAD `c1a138b`)

**Režim:** READ-ONLY vůči kódu i testům (měněn pouze tento soubor, append). Báze: `4cad304..c1a138b` — čistě M2 vlna (6 souborů: `src/Inspection/{wheel_detect,rbxm_parser}.py` + 4 test soubory; `src/Inspection/scale_calibration.py` beze změny; `src/Geometry/`, `geometry_target.json`, `geometry_diff.json` neexistují — M2-only potvrzeno, M3 bez kódu).
**Předchozí sekce §1–§6** = QA stav k pracovnímu stromu před remediation-committy; níže je finální verifikace na HEAD `c1a138b` (committy `34a4994` M2 vlna + `a94e4a2`/`c1a138b` docs).

### 7.1 Vlastní běhy (živě, sériově, tento stroj)
- `python tests/run_all.py`: **372 běhů, PASS=368, FAIL=0, ERROR=0, PENDING=4** (4 PENDING očekávané: Studio/Fáze 5/Fáze 9-10, žádný se nezapočítává do PASS). → shoda s §2.
- Cílené M2 `test_m2_rbxm_parser + test_m2_wheel_detect + test_m2_scale_calibration + test_m2_integration`: **161 testů OK** (~20 s).
- `python tools/validate_contracts.py`: **24 kontrol, 0 chyb — ÚSPĚCH** (všechny kontrakty + vzorové artefakty + example-vehicle.json).

### 7.2 Adversariální sondy 15/15 + I-1 (vlastní skript, stdlib, bez zápisu do repa; fixture formát `{id,name,class_name,shape,parent_id}` dle testů)
| # | Sonda | Výsledek |
|---|---|---|
| T01 | zdravá hierarchie 4× Ball FL/FR/RL/RR | OK (4× VALID_WHEEL) ✓ |
| T02 | chybějící RR | BLOCKED ✓ |
| T03 | duplicitní FL | BLOCKED ✓ |
| T04 | Block se jménem FL ve Wheels | BLOCKED (INVALID_WHEEL) ✓ |
| T05 | Spare Ball ve Wheels | BLOCKED (UNKNOWN_CANDIDATE) ✓ |
| T06 | Ball FR mimo Wheels (duplicita) | neblokuje, FR=id 52 drží ✓ |
| T07 | známý díl Hub (Block) ve Wheels | neblokuje, 1× KNOWN_NON_WHEEL ✓ |
| T08 | prohozené strany FL↔FR | BLOCKED ✓ |
| T09 | výšková asymetrie Y +0.38 | BLOCKED ✓ |
| T10 | NaN střed kola | BLOCKED ✓ |
| T11 | `verified_in_studio=false` + zdravá geometrie | strop **UNKNOWN** ✓ (via `build_inspection_report`, `coordinate_frame`) |
| T12 | cyklus Wheels→FL | BLOCKED (`parent_cycle`) ✓ |
| T13 | kalibrace ESTIMATED | `usable_for_m3=false`, `require_verified_for_m3` vyhazuje ✓ |
| T14 | kalibrace UNKNOWN (bez měření) | `usable_for_m3=false`, brána vyhazuje ✓ |
| T15 | kalibrace BLOCKED (JeepTemplate rozptyl / 1 rodina) | BLOCKED + brána vyhazuje ✓ |
| T16 | **I-1**: assess BLOCKED → `report_from_assess` | report **BLOCKED** ✓ (propagace drží; ověřeno i na syntetickém `float_decode_unverified` důvodu) |
Pozn.: identitní sondy T01–T07/T12 = 8/8 vlastní sondou; geometrické T08–T10 potvrzeny přes `assess_wheel_geometry` (všechny BLOCKED; i zdravá báze je v M2 BLOCKED — viz `float_decode_unverified` níže, očekávané).

### 7.3 Kalibrační brána V / E / U / B (vlastní sonda, `calibrate` + `usable_for_m3` + `require_verified_for_m3`)
- **VERIFIED** (3× VERIFIED ref + konzistentní měření, k=1.42): `overall_status=VERIFIED`, `usable_for_m3=true`, brána **OTEVŘENA** — jediný propuštěný stav ✓
- **ESTIMATED** (default refs s pneu-odhandle + konzistentní měření): `usable_for_m3=false`, `CalibrationBlockedError` ✓
- **UNKNOWN** (bez měření): `usable_for_m3=false`, brána vyhazuje ✓
- **BLOCKED** (nekonzistentní měření, rozptyl > 5 %): `overall_status=BLOCKED`, `usable_for_m3=false`, brána vyhazuje ✓
- Nezávislý přepočet JeepTemplate drží z §4 (rozptyl 7.44 % > 5 % → BLOCKED je správné chování, ne defekt).

### 7.4 `float_decode_unverified` ponechán — důvod
`src/Inspection/rbxm_parser.py:1372`: assess blokuje i při bit-přesné Studio-shodě středů/rozměrů, dokud float-decode není ověřen proti Studio ground-truth + ověřená kalibrace (M3). Konzervativní, ale **záměrné**: bez něj by M2 mohl vydat GEOMETRY_OK na neověřeném řetězci a M3-brána by neměla co držet. Text je fakticky zastaralý (shoda potvrzena, chybí jen formální kalibrační vlna) → aktualizovat po kalibrační vlně, ne teď.

### 7.5 Verdikt
- **M2: CONDITIONAL PASS** (potvrzeno na HEAD `c1a138b`). Kód drží všechna pravidla: identita (a)+(b)+(c), 4-tier, hierarchie, NaN/CFrame stropy, kalibrační prahy 5 %/2 % + pravidlo 2 rodin, I-1 propagace assess→report. Podmínky nejsou v kódu: (1) před mergem ještě jeden sériový `run_all.py` (flaky historie z paralelní vlny); (2) pracovní strom uklidit — necommitnuté delty v `reports/M2-M3/INTEGRATION-TEST-REPORT.md`, `reports/M2/SCALE-CALIBRATION-REPORT.md`, `reports/M2/WHEEL-GEOMETRY-REPORT.md` (vznikly mimo Agent D, nalezeny při final QA) commitnout nebo vyřadit; (3) `float_decode_unverified` aktualizovat po kalibrační vlně (§7.4).
- **Brána M3: NEOTEVÍRAT.** Vstupy BLOCKED/BLOCKED (assess-důvod + kalibrace 7.44 %), přísná VERIFIED-brána + I-1 propagace drží; M3 zůstává návrh bez kódu — správně. Otevření až po: Studio ground-truth + VERIFIED kalibrace + GEOMETRY_OK report.

---

## 8. Final Documentation Wave — finální nezávislé QA (Agent D, 2026-11-19, HEAD `64be2c6`)

**Režim:** READ-ONLY vůči kódu i testům (měněn pouze tento soubor, append). Historické sekce §1–§7 nemazány, neměněny.
**Větev:** `feat/m2-m3-geometry` · **HEAD:** `64be2c68cf57fad84a2e04a1ebf41a3e65827c04` · **PR #2:** OPEN, nemergován, žádné git operace.
**Strom:** v čase běhů (§8.1) jediný untracked soubor `reports/M2-M3/FINAL-DOCUMENTATION-WAVE-BASELINE.md` (pracovní soubor této dokumentační vlny — uklidit commitem nebo vyřazením, viz podmínky níže); ostatní modifikace ve stromě patří paralelním agentům vlny, ne Agentu D. Kód/testy žádný agent nemění.
**Diff `c1a138b..HEAD`:** pouze dokumentace, 6 souborů (`docs/PROJECT_STATUS.md`, tento soubor, `INTEGRATION-TEST-REPORT.md`, `REMEDIATION-WAVE-FINAL-REPORT.md`, `reports/M2/SCALE-CALIBRATION-REPORT.md`, `reports/M2/WHEEL-GEOMETRY-REPORT.md`). Žádný funkční kód ani test se nezměnil — M2-only potvrzeno.
**M3 bez kódu:** `src/Geometry/`, `geometry_target.json`, `geometry_diff.json` neexistují (ověřeno `ls`) — M3 zůstává návrh, správně.

### 8.1 Vlastní sériové běhy (živě, sériově, tento stroj)

| # | Příkaz (2026-11-19 ~21:10–21:11 UTC) | Běhy | PASS | FAIL | ERROR | PENDING | Návratový kód |
|---|---|---|---|---|---|---|---|
| 1 | `python -m unittest tests.test_m2_rbxm_parser` | 57 | 57 | 0 | 0 | 0 | 0 |
| 2 | `python -m unittest tests.test_m2_rbxm_inspector` | 7 | 7 | 0 | 0 | 0 | 0 |
| 3 | `python -m unittest tests.test_m2_wheel_detect` | 53 | 53 | 0 | 0 | 0 | 0 |
| 4 | `python -m unittest tests.test_m2_scale_calibration` | 31 | 31 | 0 | 0 | 0 | 0 |
| 5 | `python -m unittest tests.test_m2_integration` | 20 | 20 | 0 | 0 | 0 | 0 |
| 6 | `python tests/run_all.py` (plná sada) | 372 | 368 | 0 | 0 | 4 | 0 |
| 7 | `python tools/validate_contracts.py` | 24 kontroly | 24 | 0 | 0 | — | 0 |

Pozn. k číslům: součet sad 1–5 = **168** (57+7+53+31+20). Hodnota **161** v §2/§7 je součet 4 sad bez inspectora (57+53+31+20) — vysvětlení rozporu 161 vs 168 z BASELINE bodu 4: nejde o nesrovnalost v datech, jen o jiný rozsah součtu. PENDING=4 beze změny očekávané (Studio-měření, Fáze 5 schema-conformance, 2× Fáze 9/10 baseline/VariantStore), žádný se nezapočítává do PASS.

### 8.2 Brány G-01–G-07 + G-10 (vlastní evidence na HEAD `64be2c6`)

| Brána | Verdikt | Důkaz (živě ověřeno) |
|---|---|---|
| G-01 originál nedotčen | **PASS** | SHA-256 obou kopií shodný před i po bězích: `dc8747e0…2c1fefdf`, 230 421 B (`JeepTemplate.rbxm` + `chasis-work-copy.rbxm`). Jediný distinctní model = zdokumentovaný LIMIT, ne FAIL. |
| G-02 jednotky | **PASS** | `validate_contracts` 24/0; kalibrační reference `value_si + unit` (SI), report ve studs. |
| G-03 provenance | **PASS** | Reference nesou `source + status`; report nese `method + warnings` (kontrakt klíčů 1:1 + nadstavba `known_non_wheels`, ověřeno testy). |
| G-04 null ≠ odhad | **PASS** | Testy zelené: chybějící kolo → `instance_id/center/size=null` + `reason=missing_wheel` (celek BLOCKED); samé `None` v kalibraci → UNKNOWN + `estimates=[]`; BLOCKED kalibrace → `combined=null`. Žádná vymyšlená čísla. |
| G-05 PENDING ≠ PASS | **PASS** | 4 PENDING v `run_all.py` odděleně, nezapočítány do PASS; chybějící fixture → SKIP, nikdy ERROR. |
| G-06 CODE ≠ RUNTIME | **PASS** | Report neobsahuje `run_id`/`roblox-runtime`/runtime status (jen code-verified); M2 hlásí `code` nálezy, ne runtime. |
| G-07 simulace ≠ runtime | **PASS** | Žádná simulace není vydávána za runtime měření; Studio-PENDING vázané na Play zůstávají PENDING. |
| G-10 reprodukovatelnost | **PASS** | Dvojí běh `build_inspection_report` bitově shodný (vlastní sonda, `json sort_keys`); determinismus kryt i testy. |
| BLOCKED propagace M2→M3 | **PASS** | assess BLOCKED → report BLOCKED (I-1, viz §8.3); kalibrace BLOCKED + `require_verified_for_m3` vyhazuje → M3 ZAVŘENA oběma nohama. |

NEOVĚŘENO (mimo dosah tohoto QA, beze změny z §6): Studio side (Edit-mode read-only, hash před/po), reálný Mustang (pracovní kopie je JeepTemplate), Play/Runtime nároky.

### 8.3 I-1 nezávisle (assess→report BLOCKED; pokus o obejití jen čtením, beze změny kódu)

- **Kanonický řetěz:** syntetický assess se 4× GEOMETRY_OK koly (zdravá geometrie 2×2) + `blocked=True, status=BLOCKED, blocked_reasons=["float_decode_unverified: test"]` → `report_from_assess` vrací `overall_status: BLOCKED`. I-1 propagace drží na HEAD `64be2c6`.
- **Pokus o obejití (pouze čtení API):** přímé volání `build_inspection_report` se stejnou zdravou geometrií a bez `assess_blocked_reasons` vrací `GEOMETRY_OK`. Obejití je tedy možné **jen vynecháním kanonické funkce** `report_from_assess`, tj. misuse volajícího mimo řetěz — v kanonickém řetězu (`detect → assess → report_from_assess`) cesta k zelenému reportu z BLOCKED assess neexistuje. Není to díra v kódu; integrační pin-test `test_assess_blocked_propagates_to_report` kryje kanonickou cestu (20/20 PASS).
- Stav nálezu: **I-1 CLOSED** (oprava z `34a4994` drží, potvrzeno na třetím HEAD v řadě: `c1a138b` i `64be2c6`).

### 8.4 Kalibrační brána V / E / U / B (vlastní živá sonda, `calibrate` + `usable_for_m3` + `require_verified_for_m3`)

- **VERIFIED** (3× VERIFIED ref + konzistentní měření): `overall_status=VERIFIED`, `usable_for_m3=true`, brána **OTEVŘENA** — jediný propuštěný stav. ✓
- **ESTIMATED** (default refs + konzistentní měření): `usable_for_m3=false`, `CalibrationBlockedError`. ✓
- **UNKNOWN** (bez měření): `usable_for_m3=false`, brána vyhazuje. ✓
- **BLOCKED** (track_f +12 %, rozpor): `overall_status=BLOCKED`, `usable_for_m3=false`, brána vyhazuje. ✓
- Reálná data (JeepTemplate): rozptyl **7.44 % > 5 %** → BLOCKED je správné chování (deformovaný model, ne Mustang), ne defekt. Brána M3 držena.

### 8.5 `float_decode_unverified` ponechán — důvod ověřen

`src/Inspection/rbxm_parser.py:1372` blokuje assess i při bit-přesné Studio-shodě středů/rozměrů, dokud float-decode není ověřen proti Studio ground-truth + ověřená kalibrace (M3). Text důvodu zmiňuje „kalibrace NOT IMPLEMENTED" — vztahuje se k `calibrate_studs_per_meter` stubu v parseru (M2 rozhraní, trvale NOT IMPLEMENTED), ne k enginu `scale_calibration.py` (ten existuje a funguje, viz §8.4). Ponechání je **záměrné a konzervativní** (bez něj by M2 mohl vydat GEOMETRY_OK na neověřeném řetězu a M3-brána by neměla co držet), se souhlasem koordinátora. Aktualizace textu až po kalibrační vlně — podmínka zůstává otevřená (viz níže).

### 8.6 Podmínky — CLOSED / otevřené s důkazem

1. **N1 MSB-first: CLOSED.** `git diff c1a138b..HEAD` neobsahuje `rbxm_parser.py`; 0 nepřečtených shape-enumů drží (census 4× Ball + 104× Block + 1× Cylinder, ověřeno v §8.1 během 57 parser testů).
2. **Sériový `run_all.py` před mergem: CLOSED pro tento HEAD.** Běh §8.1: 372/368/0/0/4, exit 0, sériově, na `64be2c6`. (Před případným dalším mergem po nových změnách běh zopakovat — flaky historie z paralelní vlny.)
3. **Uklizený strom: TÉMĚŘ CLOSED.** Delty `INTEGRATION-TEST-REPORT.md`, `SCALE-CALIBRATION-REPORT.md`, `WHEEL-GEOMETRY-REPORT.md` z §7.5 bodu (2) jsou nyní **commitnuty** (`e2a56ef`/`64be2c6`, viz diff). Zbývá jediný untracked soubor této vlny: `FINAL-DOCUMENTATION-WAVE-BASELINE.md` — commitnout nebo vyřadit.
4. **`float_decode_unverified` aktualizace po kalibrační vlně: OTEVŘENO.** Vědomé rozhodnutí koordinátora, beze změny (§8.5).

### 8.7 Verdikt

- **M2: CONDITIONAL PASS** (potvrzeno na HEAD `64be2c6`, potřetí v řadě). Kód drží všechna pravidla: identita (a)+(b)+(c), 4-tier, hierarchie, NaN/CFrame stropy, kalibrační prahy 5 %/2 % + pravidlo 2 rodin, I-1 propagace assess→report. Otevřené podmínky nejsou v kódu: uklidit 1 untracked soubor vlny; `float_decode_unverified` aktualizovat po kalibrační vlně. Na FAIL není důvod.
- **Brána M3: NEOTEVÍRAT.** Vstupy BLOCKED/BLOCKED (assess-důvod + kalibrace 7.44 %), přísná VERIFIED-brána + I-1 propagace drží; M3 zůstává návrh bez kódu — správně. Otevření až po: Studio ground-truth + VERIFIED kalibrace + GEOMETRY_OK report.

---

## 9. FINAL CLOSEOUT — finální nezávislé QA (Agent D, 2026-11-19, HEAD `a7e89e5`)

**Režim:** READ-ONLY vůči kódu i testům (měněn pouze tento soubor, append). Historické sekce §1–§8 nemazány, neměněny.
**Větev:** `feat/m2-m3-geometry` · **HEAD:** `a7e89e5c6a35245f72b5bb3e141dd33da41f09d5` · **PR #2:** OPEN, nemergován, žádné git operace.
**Strom v čase běhů:** jediný untracked soubor `reports/M2-M3/FINAL-CLOSEOUT-BASELINE.md` (pracovní soubor této closeout-vlny — uklidit commitem nebo vyřazením, viz podmínky §9.6); `FINAL-DOCUMENTATION-WAVE-BASELINE.md` z §8 je již commitnut (viz diff níže).
**Diff `64be2c6..HEAD`:** pouze dokumentace, 11 souborů (`docs/IMPLEMENTATION_ROADMAP.md`, `docs/PROJECT_STATUS.md`, 3 audity Agent-A/B/C, `FINAL-DOCUMENTATION-WAVE-*`, tento soubor, `INTEGRATION-TEST-REPORT.md`, `reports/M2/SCALE-CALIBRATION-REPORT.md`, `reports/M2/WHEEL-GEOMETRY-REPORT.md`). Žádný funkční kód ani test se nezměnil — M2-only potvrzeno.
**M3 bez kódu:** `src/Geometry/`, `geometry_target.json`, `geometry_diff.json` neexistují (ověřeno `ls` na HEAD) — M3 zůstává návrh, správně.

### 9.1 Vlastní sériové běhy (živě, sériově, tento stroj, 2026-11-19 ~21:25–21:40 UTC)

| # | Příkaz | Běhy | PASS | FAIL | ERROR | PENDING | Návratový kód |
|---|---|---|---|---|---|---|---|
| 1 | `python -m unittest tests.test_m2_rbxm_parser` | 57 | 57 | 0 | 0 | 0 | 0 |
| 2 | `python -m unittest tests.test_m2_rbxm_inspector` | 7 | 7 | 0 | 0 | 0 | 0 |
| 3 | `python -m unittest tests.test_m2_wheel_detect` | 53 | 53 | 0 | 0 | 0 | 0 |
| 4 | `python -m unittest tests.test_m2_scale_calibration` | 31 | 31 | 0 | 0 | 0 | 0 |
| 5 | `python -m unittest tests.test_m2_integration` | 20 | 20 | 0 | 0 | 0 | 0 |
| 6 | `python tests/run_all.py` (plná sada) | 372 | 368 | 0 | 0 | 4 | 0 |
| 7 | `python tools/validate_contracts.py` | 24 kontroly | 24 | 0 | 0 | — | 0 |

Součet sad 1–5 = **168** (57+7+53+31+20); hodnota 161 v §2/§7 je součet 4 sad bez inspectora — beze změny z §8.1. PENDING=4 očekávané (Studio-měření, Fáze 5 schema-conformance, 2× Fáze 9/10 baseline/VariantStore), žádný se nezapočítává do PASS.

### 9.2 Brány G-01–G-07 + G-10 (vlastní evidence na HEAD `a7e89e5`; G-08/G-09 mimo rozsah tohoto QA)

| Brána | Verdikt | Důkaz (živě ověřeno na tomto HEAD) |
|---|---|---|
| G-01 originál nedotčen | **PASS** | SHA-256 obou kopií shodný: `dc8747e016e1402c…`, 230 421 B (`assets/chassis-original/chasis-work-copy.rbxm` + `testgame/src/ServerStorage/VehicleTemplates/JeepTemplate.rbxm`, `match: True`). Jediný distinctní model = zdokumentovaný LIMIT, ne FAIL. |
| G-02 jednotky | **PASS** | `validate_contracts` 24/0; test `test_contract_keys` zelený (reference `value_si` + `unit: m` SI, report ve studs). Kód od `64be2c6` nezměněn, sady 1–5 zelené. |
| G-03 provenance | **PASS** | Reference nesou `source + status`, report nese `method + warnings` (kontrakt klíčů 1:1 + nadstavba `known_non_wheels`); kryto zelenými testy sad 1–5. |
| G-04 null ≠ odhad | **PASS** | Kryto zelenými testy: chybějící kolo → `null` + `reason=missing_wheel` (celek BLOCKED); kalibrace UNKNOWN → `estimates=[]`; BLOCKED → `combined=null`. Žádná vymyšlená čísla. |
| G-05 PENDING ≠ PASS | **PASS** | 4 PENDING v `run_all.py` odděleně vypsány (§9.1 ř. 6), nezapočítány do PASS; FAIL=0, ERROR=0, exit 0. |
| G-06 CODE ≠ RUNTIME | **PASS** | Vlastní sonda: klíče reportu `axles, code_version, coordinate_frame, known_non_wheels, method, overall_status, parser_version, report_id` — žádný `run_id`/runtime status; `grep run_id\|roblox-runtime` v `wheel_detect.py`/`rbxm_parser.py` prázdný. |
| G-07 simulace ≠ runtime | **PASS** | Žádná simulace není vydávána za runtime měření; Studio-PENDING zůstává PENDING (viz výpis PENDING v §9.1). |
| G-10 reprodukovatelnost | **PASS** | Vlastní sonda: dvojí běh `build_inspection_report` bitově shodný (`json sort_keys`); determinismus kryt i zelenými testy (`test_determinism`). |
| BLOCKED propagace M2→M3 | **PASS** | assess BLOCKED → report BLOCKED (I-1, §9.3); kalibrace BLOCKED + `require_verified_for_m3` vyhazuje (§9.4) → M3 ZAVŘENA oběma nohama. |

NEOVĚŘENO (mimo dosah tohoto QA, beze změny z §6/§8): Studio side (Edit-mode read-only, hash před/po), reálný Mustang (pracovní kopie je JeepTemplate), Play/Runtime nároky.

### 9.3 I-1 nezávisle (assess→report BLOCKED; pokus o obejití jen čtením, beze změny kódu)

- **Kanonický řetěz:** syntetický assess se 4× GEOMETRY_OK koly + `blocked=True, status=BLOCKED, blocked_reasons=["float_decode_unverified: test"]` → `report_from_assess` vrací `overall_status: BLOCKED`. I-1 propagace drží na HEAD `a7e89e5`.
- **Pokus o obejití (pouze čtení API):** přímé volání `build_inspection_report` se stejnou geometrií a bez `assess_blocked_reasons` nevrací BLOCKED (vlastní sonda s minimálním fixture: `UNKNOWN` — strop neověřeného rámce/geometrie, nikoli převzatý BLOCKED). Obejití je tedy možné **jen vynecháním kanonické funkce** `report_from_assess`, tj. misuse volajícího mimo řetěz — v kanonickém řetězu (`detect → assess → report_from_assess`) cesta k zelenému reportu z BLOCKED assess neexistuje. Není to díra v kódu; integrační pin-test `test_assess_blocked_propagates_to_report` kryje kanonickou cestu (20/20 PASS).
- Stav nálezu: **I-1 CLOSED** (oprava z `34a4994` drží, potvrzeno na čtvrtém HEAD v řadě: `c1a138b`, `64be2c6` i `a7e89e5`).

### 9.4 Kalibrační brána V / E / U / B (vlastní živá sonda na tomto HEAD, `calibrate` + `usable_for_m3` + `require_verified_for_m3`)

- **VERIFIED** (3× VERIFIED ref + konzistentní měření k=3.0): `overall_status=VERIFIED`, `usable_for_m3=true`, brána **OTEVŘENA** — jediný propuštěný stav. ✓
- **ESTIMATED** (default refs + konzistentní měření): `overall_status=ESTIMATED`, `usable_for_m3=false`, `CalibrationBlockedError`. ✓
- **UNKNOWN** (vše `None`): `overall_status=UNKNOWN`, `usable_for_m3=false`, brána vyhazuje. ✓
- **BLOCKED** (wheelbase +20 %, rozpor): `overall_status=BLOCKED`, `usable_for_m3=false`, brána vyhazuje. ✓
- Reálná data (JeepTemplate): rozptyl **7.44 % > 5 %** → BLOCKED je správné chování (deformovaný model, ne Mustang), ne defekt — převzato z §4/§8.4 (nezávislý přepočet drží, kód nezměněn). Brána M3 držena.

### 9.5 `float_decode_unverified` ponechán — důvod ověřen

`src/Inspection/rbxm_parser.py:1372` blokuje assess i při bit-přesné Studio-shodě středů/rozměrů, dokud float-decode není ověřen proti Studio ground-truth + ověřená kalibrace (M3). Text důvodu zmiňuje „kalibrace NOT IMPLEMENTED" — vztahuje se k `calibrate_studs_per_meter` stubu v parseru (M2 rozhraní, trvale NOT IMPLEMENTED), ne k enginu `scale_calibration.py` (ten existuje a funguje, viz §9.4). Ponechání je **záměrné a konzervativní** (bez něj by M2 mohl vydat GEOMETRY_OK na neověřeném řetězu a M3-brána by neměla co držet), se souhlasem koordinátora. Aktualizace textu až po kalibrační vlně — podmínka zůstává otevřená.

### 9.6 Staré podmínky — CLOSED / otevřené s důkazem

1. **N1 MSB-first: CLOSED.** Diff `64be2c6..HEAD` neobsahuje `rbxm_parser.py` (pouze dokumentace, §9.0); 0 nepřečtených shape-enumů drží (census 4× Ball + 104× Block + 1× Cylinder, kryto 57 zelenými parser testy v §9.1).
2. **Sériový `run_all.py` před mergem: CLOSED pro tento HEAD.** Běh §9.1 ř. 6: 372/368/0/0/4, exit 0, sériově, na `a7e89e5`. (Před případným dalším mergem po nových změnách běh zopakovat — flaky historie z paralelní vlny.)
3. **Uklizený strom: TÉMĚŘ CLOSED.** `FINAL-DOCUMENTATION-WAVE-BASELINE.md` z §8 je nyní commitnut (v diffu `64be2c6..HEAD`). Zbývá jediný untracked soubor této vlny: `FINAL-CLOSEOUT-BASELINE.md` — commitnout nebo vyřadit.
4. **`float_decode_unverified` aktualizace po kalibrační vlně: OTEVŘENO.** Vědomé rozhodnutí koordinátora, beze změny (§9.5).

### 9.7 Verdikt

- **M2: CONDITIONAL PASS** (potvrzeno na HEAD `a7e89e5`, počtvrté v řadě). Kód drží všechna pravidla: identita (a)+(b)+(c), 4-tier, hierarchie, NaN/CFrame stropy, kalibrační prahy 5 %/2 % + pravidlo 2 rodin, I-1 propagace assess→report. Otevřené podmínky nejsou v kódu: uklidit 1 untracked soubor vlny (§9.6 bod 3); `float_decode_unverified` aktualizovat po kalibrační vlně (§9.6 bod 4). Na FAIL není důvod.
- **Brána M3: NEOTEVÍRAT.** Vstupy BLOCKED/BLOCKED (assess-důvod + kalibrace 7.44 %), přísná VERIFIED-brána + I-1 propagace drží; M3 zůstává návrh bez kódu — správně. Otevření až po: Studio ground-truth + VERIFIED kalibrace + GEOMETRY_OK report.

---

## 10. FINAL CLOSEOUT RE-VERIFICATION (Agent B, 2026-11-19 ~21:45–21:46 UTC, HEAD `66c27e9`)

**Režim:** READ-ONLY vůči kódu i testům (měněn pouze tento soubor, append). Historické sekce §1–§9 nemazány, neměněny.
**Větev:** `feat/m2-m3-geometry` · **HEAD:** `66c27e963dd62deb2b07967b820a96644ff71dcd` · **PR #2:** OPEN, nemergován, žádné git operace (pouze read-only `rev-parse/log/status/ls-files/diff/grep/ls`).
**Diff `a7e89e5..66c27e9`:** pouze dokumentace, 8 souborů (`docs/IMPLEMENTATION_ROADMAP.md`, `docs/PROJECT_STATUS.md`, `AGENT-A-DOCUMENTATION-REPORT.md`, `AGENT-B-WHEEL-REPORT-AUDIT.md`, `FINAL-CLOSEOUT-BASELINE.md`, `FINAL-CLOSEOUT-REPORT.md`, tento soubor, `reports/M2/WHEEL-GEOMETRY-REPORT.md`). Diff `src/**` + `tests/**` = prázdný — M2-only potvrzeno, kód/testy od `a7e89e5` nezměněny.
**M3 bez kódu:** `src/Geometry/`, `geometry_target.json`, `geometry_diff.json` neexistují (ověřeno `ls`) — M3 zůstává návrh, správně.

### 10.1 Vlastní sériové běhy (živě, sériově, tento stroj)

| # | Příkaz | Běhy | PASS | FAIL | ERROR | PENDING | Návratový kód |
|---|---|---|---|---|---|---|---|
| 1 | `python -m unittest tests.test_m2_rbxm_parser` | 57 | 57 | 0 | 0 | 0 | 0 |
| 2 | `python -m unittest tests.test_m2_rbxm_inspector` | 7 | 7 | 0 | 0 | 0 | 0 |
| 3 | `python -m unittest tests.test_m2_wheel_detect` | 53 | 53 | 0 | 0 | 0 | 0 |
| 4 | `python -m unittest tests.test_m2_scale_calibration` | 31 | 31 | 0 | 0 | 0 | 0 |
| 5 | `python -m unittest tests.test_m2_integration` | 20 | 20 | 0 | 0 | 0 | 0 |
| 6 | `python tests/run_all.py` (plná sada) | 372 | 368 | 0 | 0 | 4 | 0 |
| 7 | `python tools/validate_contracts.py` | 24 kontroly | 24 | 0 | 0 | — | 0 |

Součet sad 1–5 = **168** (57+7+53+31+20); hodnota 161 v §2/§7 = součet 4 sad bez inspectora — beze změny z §8.1/§9.1. PENDING=4 očekávané (Studio-měření, Fáze 5 schema-conformance, 2× Fáze 9/10 baseline/VariantStore), žádný se nezapočítává do PASS.

### 10.2 Brány G-01–G-07 + G-10 (vlastní evidence na HEAD `66c27e9`; G-08/G-09 mimo rozsah)

| Brána | Verdikt | Důkaz (živě ověřeno na tomto HEAD) |
|---|---|---|
| G-01 originál nedotčen | **PASS** | I-1 sonda četla `JeepTemplate.rbxm`, sha `dc8747e016e1402c…` (prefix shodný s `dc8747e0…fefdf`), 230 421 B; `_full_chain` hash před/po kryt zeleným `test_chain_does_not_modify_input` (sada 5, 20/20). |
| G-02 jednotky | **PASS** | `validate_contracts` 24/0; kód od `a7e89e5` nezměněn, sady 1–5 zelené. |
| G-03 provenance | **PASS** | Kryto zelenými testy sad 1–5 (kontrakt klíčů 1:1 + nadstavba `known_non_wheels`); kód nezměněn. |
| G-04 null ≠ odhad | **PASS** | Kryto zelenými testy (missing_wheel → `null` + BLOCKED; UNKNOWN → `estimates=[]`; BLOCKED → `combined=null`). |
| G-05 PENDING ≠ PASS | **PASS** | 4 PENDING v `run_all.py` odděleně vypsány, nezapočítány do PASS; FAIL=0, ERROR=0. |
| G-06 CODE ≠ RUNTIME | **PASS** | `grep run_id\|roblox-runtime` v `wheel_detect.py`/`rbxm_parser.py` = 0 výskytů (živě na tomto HEAD). |
| G-07 simulace ≠ runtime | **PASS** | Žádná simulace není vydávána za runtime měření; Studio-PENDING zůstává PENDING. |
| G-10 reprodukovatelnost | **PASS** | Dvojí běh `_full_chain(JEEP_COPY)` → report bitově shodný (`json sort_keys`, živá sonda). |
| BLOCKED propagace M2→M3 | **PASS** | Assess BLOCKED → report BLOCKED (§10.3) + kalibrace BLOCKED/`require_verified_for_m3` vyhazuje (§10.4) → M3 ZAVŘENA oběma nohama. |

NEOVĚŘENO (mimo dosah, beze změny z §6/§8/§9): Studio side, reálný Mustang (pracovní kopie je JeepTemplate), Play/Runtime nároky.

### 10.3 I-1 kanonickou cestou (beze změny kódu: fixture → funkce → výstup → test)

- **Fixture (pouze čtení):** `testgame/src/ServerStorage/VehicleTemplates/JeepTemplate.rbxm`, 230 421 B, sha `dc8747e016e1402c…`.
- **Funkce:** `_full_chain` z `tests/test_m2_integration.py` (parse → `detect_wheels` → `assess_wheel_geometry` → **`report_from_assess`**) — kanonický řetěz, žádná alternativní cesta.
- **Výstup (živě):** assess `blocked=True`, `blocked_reasons=['float_decode_unverified: velikosti a stredy kol potvrzeny Studiem, ale tvary dilu, rotace a kalibrace studs/m nejsou overeny (kalibrace NOT IMPLEMENTED)']` → `report_from_assess` vrací `overall_status: BLOCKED`. Propagace drží.
- **Test:** pin-test `test_assess_blocked_propagates_to_report` (`tests/test_m2_integration.py:275`) kryje kanonickou cestu, sada 5 zelená 20/20.
- Stav nálezu: **I-1 CLOSED** (oprava z `34a4994` drží, potvrzeno na pátém HEAD v řadě: `c1a138b`, `64be2c6`, `a7e89e5` i `66c27e9`).

### 10.4 Kalibrační brána V / E / U / B (živá sonda na tomto HEAD)

- **VERIFIED** (3× VERIFIED ref + konzistentní měření k=3.0): `overall_status=VERIFIED`, `usable_for_m3=true`, `require_verified_for_m3` prochází — jediný propuštěný stav. ✓
- **ESTIMATED** (default refs + konzistentní měření): `usable_for_m3=false`, `CalibrationBlockedError`. ✓
- **UNKNOWN** (vše `None`): `usable_for_m3=false`, brána vyhazuje. ✓
- **BLOCKED** (wheelbase +20 %, rozptyl > 5 %): `overall_status=BLOCKED`, `usable_for_m3=false`, brána vyhazuje. ✓
- Reálná data (JeepTemplate): rozptyl **7.44 % > 5 %** → BLOCKED je správné chování, ne defekt (nezávislý přepočet drží z §4, kód nezměněn).

### 10.5 `float_decode_unverified` ponechán — důvod potvrzen

`src/Inspection/rbxm_parser.py:1372` blokuje assess i při bit-přesné Studio-shodě středů/rozměrů, dokud float-decode není ověřen proti Studio ground-truth + ověřená kalibrace. Vztahuje se k `calibrate_studs_per_meter` stubu v parseru (M2 rozhraní, trvale NOT IMPLEMENTED), ne k enginu `scale_calibration.py` (funguje, viz §10.4). Ponechání je **záměrné a konzervativní** se souhlasem koordinátora — bez něj by M2 mohl vydat GEOMETRY_OK na neověřeném řetězu a M3-brána by neměla co držet. Aktualizace textu až po kalibrační vlně — podmínka zůstává otevřená.

### 10.6 Stará podmínka „uklizený strom: TÉMĚŘ CLOSED" — historický záznam + nový stav

- Historie: §7.5(2) → §8.6(3) → §9.6(3) `TÉMĚŘ CLOSED` (vždy zbýval 1 pracovní soubor vlny). Tímto se tyto výroky uzavírají jako **historické** — platily pro HEAD `c1a138b` / `64be2c6` / `a7e89e5`.
- Nový stav na `66c27e9`: **stále TÉMĚŘ CLOSED.** Ověřeno `git ls-files`: oba baseline-soubory jsou trackovány (`FINAL-CLOSEOUT-BASELINE.md` — commitem `dfb2e55` sync na `a7e89e5` potvrzen — i `FINAL-DOCUMENTATION-WAVE-BASELINE.md`). Pracovní strom ale hlásí staged modifikaci `M reports/M2-M3/FINAL-CLOSEOUT-BASELINE.md` (nevznikla tímto QA, pouze pozorováno read-only) — uklidit commitem nebo vyřazením.

### 10.7 Verdikt

- **M2: CONDITIONAL PASS** (potvrzeno na HEAD `66c27e9`, popáté v řadě). Kód drží všechna pravidla: identita (a)+(b)+(c), 4-tier, hierarchie, NaN/CFrame stropy, kalibrační prahy 5 %/2 % + pravidlo 2 rodin, I-1 propagace assess→report. Otevřené podmínky nejsou v kódu: uklidit 1 baseline-deltu ve stromě (§10.6); `float_decode_unverified` aktualizovat po kalibrační vlně (§10.5). Na FAIL není důvod.
- **Brána M3: NEOTEVÍRAT.** Vstupy BLOCKED/BLOCKED (assess-důvod + kalibrace 7.44 %), přísná VERIFIED-brána + I-1 propagace drží; M3 zůstává návrh bez kódu — správně. Otevření až po: Studio ground-truth + VERIFIED kalibrace + GEOMETRY_OK report.

---

## 11. FINAL CLOSEOUT — finální nezávislé QA (Agent D, 2026-11-19 ~21:52 UTC, HEAD `626c258`)

**Režim:** READ-ONLY vůči kódu i testům (měněn pouze tento soubor, append; žádné mutující git operace, žádný vlastní běh testů). Historické sekce §1–§10 nemazány, neměněny.
**Větev:** `feat/m2-m3-geometry` · **HEAD:** `626c25859cbd143662013930123611c82be4c00f` (= `origin/feat/m2-m3-geometry`, ověřeno `rev-parse`) · **Strom:** čistý (`status --short` prázdný) · **PR #2:** OPEN, nemergován (`feat/m1-m2-foundation` @ `ab840a9`, base `main`).
**Diff `66c27e9..HEAD`:** pouze dokumentace, 8 souborů (`AGENT-A/C/D` reporty, `FINAL-CLOSEOUT-BASELINE.md`, `FINAL-CLOSEOUT-REPORT.md`, `FINAL-DOCUMENTATION-WAVE-REPORT.md`, tento soubor, `reports/M3/GEOMETRY-ENGINE-PROPOSAL.md`). `diff src tests tools contracts '*.rbxm' main` = prázdný — M2-only potvrzeno, kód/testy od `a7e89e5` bitově nezměněny.
**M3 bez kódu:** `src/Geometry/`, `geometry_target.json`, `geometry_diff.json` neexistují (ověřeno `ls`) — M3 zůstává návrh, správně.
**CI k HEAD (živě `gh run view`):** run `44623140872` → headSha `626c258…`, branch `feat/m2-m3-geometry`, event push, conclusion success. Starší řetěz zelený: `66c27e9`→`44618988364`, `dfb2e55`→`44618936864`, `a7e89e5`→`44617147977` (vše success).
**Pozn. k běhům:** Agent D v této closeout-vlně testy neexekuuje (read-only); body Q-09/Q-11/Q-12 se opírají o běhy §10 na `66c27e9` (přenositelné — kód/testy nezměněny, D-25/D-26) + křížovou konzistenci a aritmetiku; chybějící exekuce na finálním HEAD je explicitně vedena jako NOT VERIFIED (Q-10), nikoli zamlčena.

| # | Kontrolní bod | Verdikt | Důkaz (živě ověřeno na `626c258`, není-li uvedeno jinak) |
|---|---|---|---|
| Q-01 | HEAD pin + branch/origin + čistý strom | **PASS** | `626c258…` = `origin/feat/m2-m3-geometry`; `status --short` prázdný. Podmínka „uklizený strom“ z §7.5/§8.6/§9.6/§10.6 je tímto **CLOSED** (oba baseline-soubory trackovány, žádná delta). |
| Q-02 | Diff `66c27e9..626c258` docs-only | **PASS** | 8 souborů, vše `reports/`; žádný funkční kód ani test. |
| Q-03 | Zákazový diff (`src/tests/tools/contracts/RBXM/main`) | **PASS** | Prázdný (vč. trackovaného `JeepTemplate.rbxm`); `main` = `5b67315` netknut; PR #2 OPEN na jiné větvi (`ab840a9`). |
| Q-04 | CI run k finálnímu HEAD | **PASS** | `44623140872` → `626c258`, success (realita zelená). Dodatek: žádný dokument ho zatím neuvádí — vedeno jako Q-14 (FAIL-minor dokumentu, ne reality). |
| Q-05 | PR #2 nemergován, M2 vlna mimo PR | **PASS** | OPEN, head `feat/m1-m2-foundation` @ `ab840a9`; M2 commity (`a7e89e5`…`626c258`) v PR nejsou. |
| Q-06 | M3 bez kódu, brána drží | **PASS** | Bez kódu (Q-03); proposal NÁVRH v1 s BLOKACÍ produkce; vstupy BLOCKED/BLOCKED (assess-důvod + kalibrace 7.44 %), VERIFIED-only brána + I-1 propagace (kód nezměněn, evidence §10.3/§10.4 platí). **M3 NEOTEVÍRAT.** |
| Q-07 | RBXM G-01 originál nedotčen | **PASS** | `sha256sum` obou kopií `dc8747e0…2c1fefdf`, 230 421 B — shoda s baseline i §10.2. Jediný distinctní model = LIMIT, ne FAIL. |
| Q-08 | Počty sad 168 vs 161 | **PASS** | `def test`: 57+7+53+31+20 = **168**; 161 = součet 4 sad bez inspectora — vysvětlení konzistentní (§8.1/§9.1/§10.1). |
| Q-09 | Plná sada 372/368/0/0/4 + 24/0 | **PASS (křížově)** | 372 = 168+204, 372−4 PENDING = 368; PENDING taxativní, žádný v PASS; `validate_contracts` 24/0. Identické napříč Agent-A re-syncem, Agent-C, §10.1, closeout §3. Bez vlastní exekuce v této vlně (viz Q-10). |
| Q-10 | Vlastní živý běh na `626c258` | **NOT VERIFIED** | Neproběhl (read-only režim). Přenositelnost z §10 dána neměnností kódu/testů, formální běh na finálním HEAD chybí. Podmínka sériového `run_all.py` před mergem trvá (flaky historie z paralelní vlny). |
| Q-11 | G-02–G-07 + G-10 + BLOCKED propagace | **PASS (přenositelně)** | Kód nezměněn od `a7e89e5` → živá evidence §10.2/§10.4 v platnosti: jednotky, provenance, null≠odhad, PENDING≠PASS, CODE≠RUNTIME, simulace≠runtime, reprodukovatelnost, M3 ZAVŘENA oběma nohama. |
| Q-12 | I-1 assess→report BLOCKED | **PASS (přenositelně)** | Oprava z `34a4994` v kódu (nezměněn); pin-test `test_assess_blocked_propagates_to_report` kryje kanonickou cestu (sada 5: 20/20 v §10.1); potvrzeno na pěti HEAD v řadě. **I-1 CLOSED.** |
| Q-13 | Poctivost příznaků (grep kontrola) | **PASS** | `NOT IMPLEMENTED` (stub `calibrate_studs_per_meter` odlišen od enginu `scale_calibration.py`), `CONDITIONAL`, `BLOCKED`, `GEOMETRY_OK`, `float_decode_unverified` (`rbxm_parser.py:1372`, přiznané konzervativní rozhodnutí), `TÉMĚŘ` jen v historických §8.6/§9.6/§10.6. Žádné PENDING→PASS, BLOCKED→VERIFIED, engine↔stub záměna. |
| Q-14 | Dokumentační piny vs HEAD + CI dodatek | **FAIL (minor)** | `626c258` se v repu nevyskytuje 0×; hlavičky: `PROJECT_STATUS`/`WHEEL`/Agent-B @ `a7e89e5`, Agent-A/Agent-C @ `64be2c6`, QA §10 @ `66c27e9`, baseline §0 @ `a7e89e5` + sekce @ `66c27e9`, closeout §1 bez explicitního finálního SHA, doc-wave „vždy `66c27e9`“ nepravdivé, CI dodatek k `44623140872` chybí (run přitom zelený). Pouze docs, nikoli funkční vada. |
| Q-15 | M2 verdikt | **PASS** | **M2: CONDITIONAL PASS** (pošesté v řadě). Pravidla drží: identita (a)+(b)+(c), 4-tier, hierarchie, NaN/CFrame stropy, prahy 5 %/2 % + 2 rodiny, I-1. Otevřené podmínky nejsou v kódu: (1) sériový `run_all.py` před mergem (Q-10); (2) `float_decode` text po kalibrační vlně. Na FAIL není důvod. |

### Verdikt §11

- **M2: CONDITIONAL PASS** (podmínky Q-15(1)(2)).
- **Brána M3: NEOTEVÍRAT** (Q-06).
- **Closeout jako CLOSED: NE — CONDITIONAL.** Nesplněno pravidlo „CLOSED jen když vše sedí“: Q-14 FAIL (minor), Q-10 NOT VERIFIED. Funkčně je vlna CLOSED (Q-01–Q-09, Q-11–Q-13, Q-15 PASS); dokumentačně zbývá 1-commit sync dluh (pin `626c258` + CI dodatek `44623140872`). Doporučení Agentu D: sjednotit v příští vlně jedním docs-committem s větou „docs-only delta beze změny výroků“.
- NEOVĚŘENO (beze změny z §6/§8/§9/§10): Studio side, reálný Mustang, Play/Runtime nároky.


---

## 12. Závěrečná synchronizace — QA dokumentace na `f60ec9b` (2026-11-19)

**Účel:** uzavřít pouze dokumentační nesoulad zaznamenaný v historické §11 (Q-10/Q-14); historické verdikty zůstávají zachovány.
**Větev:** `feat/m2-m3-geometry` · **Technický verifikační SHA:** `626c25859cbd143662013930123611c82be4c00f` · **Dokumentační finální SHA:** `f60ec9b6837659a2e6b907bd5b862fbe6dfbdd43`.
**Rozsah delta:** docs-only. Soubory kódu, testů, nástrojů, kontraktů, RBXM a `main` nebyly změněny.
**CI:** run `44627333247` má `head_sha=f60ec9b6837659a2e6b907bd5b862fbe6dfbdd43`, event `push`, conclusion `success`; jobs `tests (3.11)`, `tests (3.12)`, `tests (3.13)`, `tests (3.14)` všechny `success`.

### Rozsah ověření a poctivost běhů

Koordinátorovy sériové běhy (`tests/run_all.py`: 372/368/0/0/4; cílená M2 pětice: 168 OK; `validate_contracts.py`: 24/0) byly spuštěny na `626c258`, nikoli na `f60ec9b`. Agent D tyto běhy neprovedl ani na `626c258`, ani na `f60ec9b`. V rozsahu `626c258..f60ec9b` se kód a testy nezměnily, což podporuje přenositelnost předchozích výsledků, ale není to nezávislé opakování Agentem D na výsledném SHA. CI run na `f60ec9b` je samostatný GitHub CI důkaz a nenahrazuje chybějící nezávislý sériový běh.

### Oprava nesouladu CLOSED vs. CONDITIONAL

Historická §11 zůstává pravdivým záznamem QA stavu při `626c258`: Agent D vydal **M2 CONDITIONAL PASS**, označil vlastní běh za **NOT VERIFIED** a dokumentační closeout jako **CONDITIONAL**, nikoli CLOSED. Koordinátorova formulace “DOCUMENTATION WAVE: CLOSED” se proto zužuje na **dokumentační synchronizace dokončena**; nejde o změnu Agent-D verdictu ani o nepodmíněné uzavření M2. Stav zůstává **M2 CONDITIONAL PASS · kalibrace BLOCKED · M3 NEOTEVŘENA · runtime NOT VERIFIED · PR #2 OPEN / NOT MERGED**.

### Uzavření původního dokumentačního dluhu

- **Q-14 (piny a CI dodatek):** opraveno — closeout uvádí `f60ec9b` jako docs SHA, `626c258` jako technický verifikační SHA a run `44627333247`.
- **Q-10 (Agent-D běh):** zůstává **NOT VERIFIED** jako vlastní exekuce Agentem D; CI success a nezměněný kód/testy tuto skutečnost nemažou.
- **Celkový závěr:** dokumentační synchronizace dokončena; nezávislý verdikt zůstává **CONDITIONAL**. M2 ani M3 stav není tímto commitem povýšen.
