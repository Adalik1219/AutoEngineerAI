# Agent A — Documentation sync report (M2/M3, 2026-11-19)

Větev `feat/m2-m3-geometry` @ `64be2c6` (PR #2 OPEN jinde, nemergováno).
Rozsah: pouze `docs/PROJECT_STATUS.md`, `docs/IMPLEMENTATION_ROADMAP.md` + tento report.
Kód ani testy neměněny.

## Zdroj pravdy (ověřeno čtením kódu a reportů vlny)

- `src/Inspection/rbxm_parser.py:1378` — `calibrate_studs_per_meter` je záměrný
  NOT-IMPLEMENTED stub (nikdy nevrací ověřenou hodnotu). Není to kalibrační engine.
- `src/Inspection/scale_calibration.py` (327 řádků) — kalibrační engine M2.9/M2.10
  IMPLEMENTED; 31 testů PASS; pravidla: < 2 nezávislé rodiny → BLOCKED,
  rozptyl > 5 % → BLOCKED, brána `require_verified_for_m3` (pouze VERIFIED do M3).
- Reálná kopie: 4× VALID_WHEEL (FL=3/FR=52/RL=101/RR=150) + 44× KNOWN_NON_WHEEL
  (allowlist 11 jmen × 4), 0 unidentified (`INTEGRATION-TEST-REPORT.md` §detect).
  Celek BLOCKED: assess `float_decode_unverified` + kalibrace BLOCKED
  (rozptyl 7,44 % > 5 %, JeepTemplate = jiné vozidlo, očekávané).
- Studio ground-truth DONE: Ball 2.7³, rozvor ≈10.5228, rozchod ≈5.9907
  (`STUDIO_GROUND_TRUTH.md`); MSB-first 4×Ball + 104×Block + 1×Cylinder,
  0 nepřečtených shape-enumů (`AUDIT2-format-compat.md`, QA verdikt).
- QA verdikt: M2 CONDITIONAL PASS; M3 NEOTEVŘENA (`REMEDIATION-WAVE-FINAL-REPORT.md` §8).

## Opravy

`docs/PROJECT_STATUS.md`
1. §0.2 nadpis: „měření/kalibrace BLOCKED / NOT IMPLEMENTED" →
   „engine hotov, měření a výsledek kalibrace BLOCKED".
2. §0.2 odrážka: „44 dílů → BLOCKED … kalibrace NOT IMPLEMENTED" →
   „4× VALID_WHEEL + 44× KNOWN_NON_WHEEL, 0 unidentified — celek BLOCKED;
   engine IMPLEMENTED + CODE-VERIFIED (31 testů); NOT IMPLEMENTED pouze stub
   `calibrate_studs_per_meter`; JeepTemplate BLOCKED 7,44 %".
3. §0.5 bod 1: stejné rozlišení (engine vs měření vs výsledek); stub výslovně zmíněn.
4. §0.5 bod 2: „bez kalibrace" → „bez VERIFIED měřítka; brána M3 NEOTEVŘENA".
5. §10: klasifikace doplněna o počty (4× VALID + 44× KNOWN_NON_WHEEL, 0 unidentified);
   parser + stub vs engine (31 testů) vs JeepTemplate BLOCKED 7,44 % odděleny.

`docs/IMPLEMENTATION_ROADMAP.md`
6. M2 hlavička: beze změny (již správně: CONDITIONAL PASS, engine IMPLEMENTED,
   JeepTemplate BLOCKED 7,44 %, M3 NEOTEVŘENA).
7. M2.8 spike-vs-produkce: „(C06/kalibrace vzniká až po M3 ground-truth)" →
   engine C06 IMPLEMENTED + CODE-VERIFIED, stub vs výsledek BLOCKED rozlišeny.
8. M2.13: „kalibrace NOT IMPLEMENTED / až po ground-truth" →
   engine IMPLEMENTED, výsledek BLOCKED 7,44 %, VERIFIED měřítko chybí.
9. M2.14 stav: „ČÁSTEČNĚ … kalibrace M2.9/M2.10 NOT IMPLEMENTED" →
   „CONDITIONAL PASS … engine CODE-VERIFIED … výsledek BLOCKED (7,44 %)".
10. M3 (hlavička + §14) NOT IMPLEMENTED beze změny — M3 NEOTEVŘENA, držíno.
11. M4–M9 beze změny (PARTIAL dle historického auditu).

## Sjednocené výskyty (kontrola po opravě)

- „NOT IMPLEMENTED" v obou souborech zůstává pouze tam, kde patří:
  stub `calibrate_studs_per_meter`, M3 (x2), historická tabulka §1 (NEMAZAT).
  Žádný výskyt „kalibrace/engine NOT IMPLEMENTED" nezbyl.
- „BLOCKED": měření (assess `float_decode_unverified`) + výsledek kalibrace
  7,44 % + brána M3; KNOWN_NON_WHEEL výslovně neblokuje.
- „CONDITIONAL PASS": M2 v hlavičce ROADMAP, M2.14 i §10 jednotně.
- „44": vždy 44× KNOWN_NON_WHEEL (11 × 4) + 4× VALID_WHEEL; „M3 NEOTEVŘENA"
  v hlavičce ROADMAP M2, M2.14-stavu nepřímo (VERIFIED měřítko chybí),
  §0.2/§0.5/§10.

## Ověření

- `grep NOT IMPLEMENTED docs/PROJECT_STATUS.md docs/IMPLEMENTATION_ROADMAP.md` —
  pouze legitimní výskyty (viz výše).
- Změněny jen 2 vlastněné soubory + tento nový report; `git status` jinak ukazuje
  pouze souběžnou práci jiných agentů (WHEEL-GEOMETRY-REPORT, AGENT-B audit),
  do té nebylo saháno.

## Zbývá

- Nic v rozsahu Agenta A. Otevřené body zůstávají v §0.5 (kalibrace BLOCKED,
  M3 zavřená, final-drive UNKNOWN rozhodnutím uživatele, 4× PENDING ≠ PASS).

---

## Vlna 2026-11-19, HEAD `a7e89e5` (re-sync; PR #2 OPEN jinde, nemergováno)

Výchozí stav: opravy z předchozí vlny (výše, @ `64be2c6`) drží — §0.2/§0.5/§10
i ROADMAP M2/M3 byly již konzistentní (engine IMPLEMENTED + CODE-VERIFIED,
stub NOT IMPLEMENTED, JeepTemplate BLOCKED 7,44 %, M2 CONDITIONAL PASS,
M3 NOT IMPLEMENTED / NEOTEVŘENA, M4–M9 PARTIAL). Kód ani testy neměněny.

Ověřeno vlastním během 2026-11-19: `python tests/run_all.py` →
**372 běhů, 368 PASS, 0 FAIL, 0 ERROR, 4 PENDING** (shodné s §0.4;
PENDING totožné, PENDING≠PASS). RBXM hash
`dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf`
beze změny (pouze čteno). `src/Inspection/scale_calibration.py` existuje;
grep `def test_`: `test_m2_wheel_detect.py` = 53, `test_m2_scale_calibration.py` = 31.

Opravy této vlny:
1. `docs/PROJECT_STATUS.md` hlavička §0 + §0.4 (nadpis + Sady M2):
   `@ e2a56ef` → `@ a7e89e5` (HEAD dle zadání; bez git operací, neověřeno
   proti `git rev-parse` — ke konfirmaci koordinátorem).
2. `docs/PROJECT_STATUS.md` §0.2 + `docs/IMPLEMENTATION_ROADMAP.md` M2.8 mapa:
   `wheel_detect.py` „21 testů" → **53 testů** (grep + běh sady vše PASS).

Grep kontrola po opravě (`NOT IMPLEMENTED` / `BLOCKED` / `44` / `M3`):
- „kalibrace/engine NOT IMPLEMENTED" — žádný výskyt. NOT IMPLEMENTED zůstává
  jen: stub `calibrate_studs_per_meter`, M3 (hlavička + §14), historická §1.
- „44" — vždy 44× KNOWN_NON_WHEEL (11 × 4) + 4× VALID_WHEEL, 0 unidentified.
- „BLOCKED" — měření (`float_decode_unverified`) + výsledek kalibrace
  (7,44 % > 5 %) + brána M3 (`require_verified_for_m3`); KNOWN_NON_WHEEL
  výslovně neblokuje.
- „CONDITIONAL PASS" — M2 v hlavičce ROADMAP, M2.14 i §10 jednotně.

Zbývá: nic v rozsahu Agenta A.

---

## Vlna 2026-11-19, HEAD `66c27e9` (Agent A, formát bod 1–10; PR #2 OPEN jinde, nemergováno, žádné git operace)

1. **Identifikace:** větev `feat/m2-m3-geometry`; auditní základ
   `a7e89e5c6a35245f72b5bb3e141dd33da41f09d5`; sync
   `dfb2e55a032e863a784ea9ddaaaa44926d9212af`; finální
   `66c27e963dd62deb2b07967b820a96644ff71dcd`. Finální je vždy `66c27e9`
   — nikdy netvrdit, že finální = starší commit.
2. **Režim a rozsah:** pouze dokumentace + audit. Vlastněné soubory této vlny:
   `reports/M2-M3/FINAL-DOCUMENTATION-WAVE-REPORT.md` (oprava) a tento report
   (nová sekce). Kód ani testy neměněny; žádný merge, žádná M3, `main` netknut.
3. **Zdroj pravdy (beze změny z předchozích vln):** engine
   `src/Inspection/scale_calibration.py` IMPLEMENTED + CODE-VERIFIED (31 testů);
   stub `rbxm_parser.py:1378 calibrate_studs_per_meter` trvale NOT IMPLEMENTED;
   4× VALID_WHEEL + 44× KNOWN_NON_WHEEL, 0 unidentified; celek BLOCKED
   (assess `float_decode_unverified` + kalibrace BLOCKED 7,44 % > 5 %,
   JeepTemplate = jiné vozidlo).
4. **Opravy této vlny ve `FINAL-DOCUMENTATION-WAVE-REPORT.md`:** (a) identifikace
   `64be2c6`/`7761ef9` → auditní základ `a7e89e5` / sync `dfb2e55` / finální
   `66c27e9`; (b) CI sekce → historický run `44617147977` k `a7e89e5` +
   aktuální run `44618988364` k `66c27e9` (4/4, push, ověřeno koordinátorem);
   (c) nová tabulka souborů (ZMĚNĚN vs NE); (d) testovací souhrn s příkazy/SHA/výsledky;
   (e) verdict: M2 CONDITIONAL PASS, kalibrace BLOCKED, M3 NEOTEVŘENA.
5. **`docs/` a ostatní reporty v této vlně:** NE — neměněny. Opravy z předchozích
   synců drží (§0.2/§0.5/§10 + ROADMAP M2: engine vs stub vs BLOCKED 7,44 %;
   WHEEL §4/§6; INTEGRATION I-1 + 161/168). Ověřeno `git status --short`:
   mimo vlastněné soubory pouze pracovní `FINAL-CLOSEOUT-BASELINE.md`
   (closeout-vlna, ne tato).
6. **Testy (vlastní živé běhy na `66c27e9`, sériově):**
   `python tests/run_all.py` → **372/368/0/0/4, exit 0**;
   5 M2 sad společně → **Ran 168 tests, OK** (57+7+53+31+20);
   `python tools/validate_contracts.py` → **24 kontrol, 0 chyb, exit 0**.
   PENDING=4 očekávané, PENDING≠PASS.
7. **CI:** historický `44617147977` = `a7e89e5`; aktuální `44618988364` =
   `66c27e9` (push, `feat/m2-m3-geometry`, 4/4 — ověřeno koordinátorem).
   Docs-only delta, testy nedotčeny.
8. **G-brány:** G-01–G-07 + G-10 PASS (důkazy viz QA §9: hash RBXM, jednotky 24/0,
   provenance, null≠odhad, PENDING≠PASS, CODE≠RUNTIME, simulace≠runtime,
   determinismus); G-08/G-09 mimo rozsah.
9. **Verdikt:** M2 CONDITIONAL PASS (popáté v řadě); kalibrace BLOCKED
   (7,44 % > 5 % + stub NOT IMPLEMENTED); brána M3 NEOTEVŘENA.
10. **Zbývá:** nic v rozsahu Agenta A. Otevřené body: kalibrační vlna
    s VERIFIED měřítkem; `float_decode_unverified` text až po kalibrační vlně;
    3. distinctní RBXM; Play/runtime důkazy.

---

## Vlna 2026-11-19, HEAD `626c258` (Agent A, formát bod 1–10; PR #2 OPEN, nemergováno, žádné git operace)

1. **Identifikace:** větev `feat/m2-m3-geometry`; auditní základ
   `a7e89e5c6a35245f72b5bb3e141dd33da41f09d5`; sync
   `dfb2e55a032e863a784ea9ddaaaa44926d9212af`; předchozí finální
   `66c27e963dd62deb2b07967b820a96644ff71dcd`. TATO vlna: výchozí
   `626c25859cbd143662013930123611c82be4c00f`, finální = nový
   docs-only commit (hash doplní koordinátor). Nikdy netvrdit, že
   finální = starší commit.
2. **Režim a rozsah:** pouze dokumentace + audit. Vlastněné soubory této vlny:
   `reports/M2-M3/FINAL-CLOSEOUT-REPORT.md` (oprava: §1, §3, §4, §4b, §5)
   a tento report (nová sekce). Kód ani testy neměněny; žádný merge,
   žádná M3, `main` netknut (`5b67315`).
3. **Zdroj pravdy (beze změny z předchozích vln):** engine
   `src/Inspection/scale_calibration.py` IMPLEMENTED + CODE-VERIFIED (31 testů);
   stub `rbxm_parser.py:1378 calibrate_studs_per_meter` trvale NOT IMPLEMENTED;
   4× VALID_WHEEL + 44× KNOWN_NON_WHEEL, 0 unidentified; celek BLOCKED
   (assess `float_decode_unverified` + kalibrace BLOCKED 7,44 % > 5 %,
   JeepTemplate = jiné vozidlo).
4. **Opravy této vlny ve `FINAL-CLOSEOUT-REPORT.md`:** (a) §1 → plný řetězec
   auditní základ `a7e89e5` / sync `dfb2e55` / předchozí finální `66c27e9` /
   TATO vlna výchozí `626c258` + finální docs-only commit (koordinátor);
   (b) CI sekce → historický run `44617147977` k `a7e89e5` +
   run `44618988364` k `66c27e9` (4/4, push, ověřeno koordinátorem) +
   nový run k finálnímu commitu doplní koordinátor;
   (c) nová §4b tabulka souborů (ZMĚNĚN vs NE);
   (d) §3 testovací souhrn tabulkou s příkazy/SHA/výsledky;
   (e) §5 + §7 verdikt: M2 CONDITIONAL PASS, kalibrace BLOCKED, M3 NEOTEVŘENA.
5. **`docs/` a ostatní reporty v této vlně:** NE — neměněny. Opravy z předchozích
   synců drží (§0.2/§0.5/§10 + ROADMAP M2: engine vs stub vs BLOCKED 7,44 %;
   WHEEL §4/§6; INTEGRATION I-1 + 161/168; proposal §4/§9).
   `git status --short` před editací čistý (HEAD `626c258`).
6. **Testy (vlastní živé běhy na `626c258`, sériově, exit 0):**
   `python tests/run_all.py` → **372/368/0/0/4, exit 0**;
   `python -m unittest tests.test_m2_rbxm_parser tests.test_m2_rbxm_inspector tests.test_m2_wheel_detect tests.test_m2_scale_calibration tests.test_m2_integration` → **Ran 168 tests, OK** (57+7+53+31+20);
   `python tools/validate_contracts.py` → **24 kontrol, 0 chyb, exit 0**.
   PENDING=4 očekávané, PENDING≠PASS.
7. **CI:** historický `44617147977` = `a7e89e5`; `44618988364` =
   `66c27e9` (push, `feat/m2-m3-geometry`, 4/4 — ověřeno koordinátorem).
   Nový run k finálnímu commitu této vlny (docs-only, na `626c258`)
   doplní koordinátor po pushi. Docs-only delta, testy nedotčeny.
8. **G-brány:** G-01–G-07 + G-10 PASS (důkazy viz QA §9: hash RBXM, jednotky 24/0,
   provenance, null≠odhad, PENDING≠PASS, CODE≠RUNTIME, simulace≠runtime,
   determinismus); G-08/G-09 mimo rozsah.
9. **Verdikt:** M2 CONDITIONAL PASS (pošesté v řadě); kalibrace BLOCKED
   (7,44 % > 5 % + stub NOT IMPLEMENTED); brána M3 NEOTEVŘENA.
10. **Zbývá:** nic v rozsahu Agenta A. Otevřené body: kalibrační vlna
    s VERIFIED měřítkem; `float_decode_unverified` text až po kalibrační vlně;
    3. distinctní RBXM; Play/runtime důkazy.
