# Agent G — nezávislé QA a bezpečnostní review

- **Větev:** `feat/m2-m3-geometry` · **HEAD:** `9803db37970b940c3ceb0ef15804834efea0a99c` (ověřeno `git rev-parse HEAD`, shodné s výchozím SHA).
- **Datum:** 2026-11-19 · **Jazyk:** čeština; kód anglicky.
- **Metoda:** pouze čtení + vlastní běhy. Jediný zápis je tento report. RBXM čteno jen jako hash/velikost, `C:/.DATA/RobloxSimulator` nedotčen, žádné runtime tvrzení, žádný merge/push/PR.
- **Podklady (čteno):** `reports/NIGHT-WORK/AGENT-A` až `AGENT-F`, `src/Chassis/mapping/cycle_check.py`, `tests/test_m2_contract_freeze.py`, `tests/test_m4_oracles.py`, `tests/test_m5_cycle_check.py`, `src/Inspection/scale_calibration.py` (M3 brána), `src/Inspection/rbxm_parser.py` (blok).

## 1. Git status / diff — existující soubory nemodifikovány

- `git diff --name-only` → **prázdné**, `git diff --stat` → **prázdné**. Žádný trackovaný soubor není modifikován.
- `git status --porcelain=v1` → pouze 10 untracked položek (6 reportů + 4 nové soubory):
  `reports/NIGHT-WORK/AGENT-A..F`, `src/Chassis/mapping/cycle_check.py`,
  `tests/test_m2_contract_freeze.py`, `tests/test_m4_oracles.py`, `tests/test_m5_cycle_check.py`.
- Tvrzení o "pouze přidané soubory" **potvrzeno vlastníma očima**.

## 2. Rozsah agentů — každý jen ve svém

- A, C, D, F: pouze vlastní report, žádný kód. ✓
- B: report + `tests/test_m2_contract_freeze.py` (hlavička souboru se k B hlásí) + `tests/test_m5_cycle_check.py` (hlavička: "Agent B") + `src/Chassis/mapping/cycle_check.py` (S-02). Vše nové soubory. ✓
- E: report (inventura M4/M5 + plán T-*/S-*). S-02 (cyklus-detektor) a S-05 (M4 orákula) z jeho plánu existují jako nové soubory s hlavičkou B — viz nález N1 (evidence, ne porušení).
- C: žádný kód, jen checklisty/šablona. D: návrh only, žádný `src/Geometry/*` nevznikl (ověřeno grepem — žádný producent `geometry_target/diff` v `src/`, `tools/`, `contracts/`). F: jen report. ✓
- Žádný agent nesáhl mimo svůj rozsah (globálně garantováno prázdným `git diff`).

## 3. Bezpečnost

| Kontrolka | Vlastní ověření | Výsledek |
|---|---|---|
| RBXM hash před/po | `sha256sum` obou kopií → `dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf` shodný, 230421 B | ✓ shodné s tvrzením agentů |
| Mustang RBXM | `assets/*mustang*`, `find -iname *mustang*.rbxm` → nic | ✓ skutečně chybí (tvrzení C potvrzeno) |
| M3 brána nedotčena | `usable_for_m3` = `overall_status == "VERIFIED"`; `require_verified_for_m3` jinak `CalibrationBlockedError` (řádky 310–327 beze změny, `git diff` prázdný) | ✓ blokuje |
| Brána zvedá na všem kromě VERIFIED | vlastní běh: ESTIMATED/UNKNOWN/BLOCKED → raise; VERIFIED → průchod | ✓ |
| Bezpodmínečný assess blok | `float_decode_unverified` na `rbxm_parser.py:1372` přítomen | ✓ |
| Jednotky | nové testy: report vše studs, kalibrace `unit == "m"`; žádná nová konverze mimo `src/common/units` | ✓ |
| Provenience | nové testy používají `synthetic/no-rbxm` + `source_sha256 00*32`, nikdy hash reálného RBXM | ✓ |
| UNKNOWN/ESTIMATED/VERIFIED | VERIFIED jen jako enum/množina stavů a očekávaný stav syntetické kalibrace; `mustang` se v nových testech vyskytuje 1× (disclaimer, ne datový nárok) | ✓ žádná falešná VERIFIED fixture |
| BLOCKED propagace | assess BLOCKED → report BLOCKED; kalibrace non-VERIFIED → `usable_for_m3 == False` (vlastní negativní sonda §5) | ✓ |
| Runtime tvrzení | grep `studio_play\|run_id\|roblox-runtime` v nových souborech → 0 výskytů; žádný `run_id`/`studio_play` token | ✓ žádné |
| Monkeypatching produkce | grep `mock\|patch\|monkeypatch` v nových souborech → 0 | ✓ |
| Simulator | `C:/.DATA/RobloxSimulator` — žádný zápis z této revize (všechny změny jsou untracked v repu) | ✓ READ-ONLY dodržen |

## 4. Vlastní naměřená čísla (nezávislé běhy, tento strom)

- `python tools/validate_contracts.py` → **24 kontrol, 0 chyb**. ✓
- `python tests/run_all.py` → **běhů 410 / PASS 406 / FAIL 0 / ERROR 0 / PENDING 4** (4 původní PENDING zachovány: studio-měření, schema-conformance, 2× regresní baseline). ✓ shodné s deklarovanými.
- M2 pětice (`rbxm_parser + wheel_detect + scale_calibration + integration + rbxm_inspector`) → **168 testů, OK**. ✓
- `test_m2_contract_freeze` → **19, OK**; `test_m4_oracles` → **13, OK**; `test_m5_cycle_check` → **6, OK**. ✓ (`grep -c "def test"` = 19/13/6, sedí.)
- Kontrolní součet: 168 + 19 = 187 M2 (souhlas s B); 168 + 19 + 13 + 6 = 206 v nových + M2 rámcích, zbytek plné sady beze změny.

## 5. Falešně-pozitivní kontrola nových testů (negativní sondy, vlastní běh)

Každá sonda rozbíjí vstup a **očekává selhání** (důkaz, že testy nejsou vakuózní):

1. **cycle** (`test_m5_cycle_check`): `find_cycles({"a":["b"],"b":["a"]})` → vrátil `[["a","b"]]`, aserce na `[]` selhala (`AssertionError`). Detektor cykly skutečně hlásí; `build_known_graph()` → `[]` (známé tabulky acyklické). ✓
2. **M4 orákula** (`test_m4_oracles`): `power_w` přesně `torque*omega` (50265.48…); nárok posunutý o +1000 selhal (`AssertionError`). Invariant je ostrý, ne formální. ✓
3. **freeze/brána** (`test_m2_contract_freeze` + gate): `usable_for_m3({"overall_status":"ESTIMATED"})` → `False`; aserce na `True` selhala. ESTIMATED bránu neotevře. ✓

## 6. Přísnost kontrol nesnížena

- `git diff` prázdný ⇒ žádná existující kontrola (brána, prahy 2 %/5 %, `CalibrationError` větve, `KNOWN_*` tabulky) nebyla uvolněna ani odstraněna — formálně není co snížit.
- Nové soubory pouze **přidávají** aserce (19+13+6 testů, vše PASS) a jeden čistý analytický modul bez vedlejších efektů (`cycle_check.py`: stdlib, deterministický, konflikty záměrně mimo graf — zdůvodněno v docstringu, ověřeno: známé tabulky bez cyklu).
- `find_cycles` kanonizuje rotací na lexikografické minimum a třídí výstup → determinismus držen (test determinismu prochází).

## Nálezy (žádný blokující)

- **N1 (evidence):** E-report tvrdí "jediný zápis je tento report", ale artefakty jeho plánu S-02 (`cycle_check.py`, `test_m5_cycle_check.py`) a S-05 (`test_m4_oracles.py`) v stromu existují — s hlavičkou Agenta B. Attribution je tedy nejednoznačná, ale **bezpečnostně irelevantní** (vše nové soubory, nic trackovaného neměněno). Doporučení: sjednotit vlastnictví v hlavičkách.
- **N2 (zastaralá citace):** E-report §M5.7 uvádí "372 běhů / 368 PASS / 4 PENDING (dle M2-M3 closeoutu)" — aktuální strom má **410/406/4** (můj běh §4). Čísla v E jsou starší closeout, ne současný stav. Bez dopadu na kód.

## Verdikt: **PASS**

Všech šest tvrzení zadání ověřeno vlastníma očima a vlastními běhy: (1) trackované soubory nedotčeny; (2) rozsahy dodrženy; (3) RBXM/provenience/jednotky/BLOCKED-propagace/M3-brána bez porušení, žádné falešné VERIFIED ani runtime nároky; (4) plná sada 410/406/0/0/4 PENDING + M2 168 + nové 19/13/6 + kontrakty 24/24 — vše mnou naměřeno; (5) 3 negativní sondy selhaly dle očekávání; (6) žádná kontrola nebyla uvolněna. Dva drobné nálezy (N1, N2) jsou evidenční, neblokují.
