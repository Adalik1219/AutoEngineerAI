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
