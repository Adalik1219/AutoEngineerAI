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
