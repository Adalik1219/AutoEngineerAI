# Project Status – stav k 2026-11-19 (větev `feat/m2-m3-geometry`; PR #2 OPEN jinde)

**Aktuální stav:** M1 CODE-VERIFIED; M2 CONDITIONAL PASS (parser C05 + 4-tier
detekce CODE-VERIFIED, kalibrace BLOCKED 7,44 %, M3 brána VERIFIED-only, M3
NEOTEVŘENA) — větev `feat/m2-m3-geometry` @ `626c258` (closeout sync;
technický kód beze změny od `a7e89e5`; navazuje na PR #2
`ab840a9`; nemergováno); testy
**372 běhů, 368 PASS, 0 FAIL, 0 ERROR, 4 PENDING** (`python tests/run_all.py`,
ověřeno vlastním během 2026-11-19; historické: 279/275 @ `ff4a9d6` (PR #2),
260/256 @ `ff6f266` — viz §0.4; PENDING beze změny, PENDING≠PASS).
**RBXM hashe beze změny** (pouze čtení, žádný zápis — viz §0.4).

> **§1–§8 = HISTORICKÝ audit před implementací** (stav k `dd9efdf`, 162 PASS).
> Ponecháno NEMAZAT jako stopa; aktuální stav je pouze §0 (+ §9 kontroly M1/M2).

---

## 0. Aktuální stav po M1+M2 (tato větev)

### 0.1 M1 – profil + validace (hotovo)
- Profil Mustangu: EUROPEAN FACTORY STANDARD SPECIFICATION, `vehicle_id` beze změny;
  VERIFIED (factory, confidence ≥ 0.85, zdroj Ford EU PDF/mirror + datum): poměry 1–6
  (3.237/2.104/1.422/1.000/0.814/0.622), 0–100 5,3 s, V-max 250 km/h, kotouče
  390x36/355x28 + Brembo six-piston, LSD obecně, kola 19x9.0J/19x9.5J +
  pneu 255/40–275/40 R19.
- UNKNOWN zůstává (křivka, rozložení, bias, Cd, stálý převod s kandidáty
  3.15/3.55 v notes) + GUARD test T17 (final_drive jako definitivní hodnota → chyba).
- Validace: profil 0 errors / 0 warnings; sada M1-T01…M1-T20 20/20 PASS.
- Detail: §9 níže (kontroly Agenta D + opakování po povýšení M1.5).

### 0.2 M2 – parser C05 hotov (CODE-VERIFIED); engine hotov, měření a výsledek kalibrace BLOCKED
- Hotovo: RBXM spike (viz `reports/RBXM-SPIKE.md`, fáze B 36cbbdb: lane-order
  MSB-první doložen, Ball=0 invariantní); produkční parser **C05**
  (`src/Inspection/rbxm_parser.py`, 1352 řádků @ `36cbbdb`; fáze B: `parse_rbxm`
  OSError → `RbxmCorruptError` kontrakt + test, F8 hash přes reál): chunk reader +
  INST + PRNT + SSTR/META/Name + Shape/Size/CFrame s provenancí
  (`read/missing/unread`; floaty vždy `trusted=False`). P0 oprava: cyklus
  v parent hierarchii, chybějící parent ID i duplicitní instance ID →
  vždy BLOCKED, nikdy validní (`parent_cycle` / `missing parent id` /
  `duplicate instance id` v blocked_reasons).
- Důkazy: `reports/AUDIT-parser-security.md` (P0: 0; 5× P1 + 2× P2 vše
  OPRAVENO s regresními testy) + `reports/AUDIT-format-compat.md` (+
  `reports/AUDIT2-format-compat.md` fáze B, 36cbbdb) + `reports/AUDIT-geometry.md`
  (+ `reports/AUDIT2-geometry.md`, `AUDIT2-parser-security.md`,
  `AUDIT2-performance.md`, `AUDIT2-qa-plan.md` — 53c2e23) +
  `reports/AUDIT-qa-final.md` (7 vlastních adversarial sond vše fail-closed;
  verdikt MERGE, podmínky docs-only) + `reports/FINAL_INDEPENDENT_QA.md`
  (MERGE WITH CONDITIONS docs-only) + `reports/FINAL_COORDINATION_REPORT.md` +
  `reports/FINAL_PERFORMANCE_BENCHMARK.md` (opraveno rozsahem: hotspoty
  5–240× dle operace, end-to-end na chassis kopii ~2×, paměť beze změny).
  Stupeň: **CODE-VERIFIED, není RUNTIME** (Studio ground-truth
  `reports/STUDIO_GROUND_TRUTH.md` DONE 2026-11-19 potvrzuje pozice/Size/Shape
  kol parseru vs. Studio — viz §0.5/4; runtime jízda žádná).
- Presety CFrame **ověřené vs. unread odděleně**: id 0 = vlastní matice
  (čtena), id 2 = identita; ostatní id → `unread-preset-N` (pozice čtena,
  orientace `None`, nikdy odhad) — kryto `test_f6_cframe_preset_sweep`,
  `test_cframe_unknown_preset_unread`, `test_assess_unread_rotation_blocked`.
- Detekce kol: rozhodovací pravidlo `(a) v Model:Wheels + (b) FL/FR/RL/RR +
  (c) tvar Ball` v `src/Inspection/wheel_detect.py` (53 testů, vše PASS).
- BLOCKED (měření + výsledek kalibrace): geometrie z měření (M2.4–M2.6 rozvor/rozchody/
  průměry) — kalibrační brána drží **BLOCKED** (`float_decode_unverified`;
  reálná kopie: 4× VALID_WHEEL + 44× KNOWN_NON_WHEEL (11 jmen allowlistu × 4),
  0 unidentified — celek BLOCKED, ověřeno během). Kalibrační engine
  `src/Inspection/scale_calibration.py` (M2.9/M2.10, C06) je **IMPLEMENTED +
  CODE-VERIFIED** (31 testů); NOT IMPLEMENTED je pouze pomocné rozhraní
  `calibrate_studs_per_meter` v `rbxm_parser.py` (záměrný stub, nikdy nevrací
  ověřenou hodnotu). Výsledek kalibrace na JeepTemplate je **BLOCKED
  (rozptyl 7,44 % > 5 %)** — očekávané (jiné vozidlo), ne defekt.
  Žádné měření se neodhaduje, vše UNKNOWN/BLOCKED.

### 0.3 M3–M9 (beze změny)
- M3 Geometry Engine NOT IMPLEMENTED; M4/M5/M6/M7/M8/M9 PARTIAL dle historického
  auditu §1 (stav před implementací této větve).

### 0.4 Testy a RBXM integrita (technická verifikace @ `a7e89e5`; potvrzeno
během 2026-11-19 na stromě `626c258` — `src/`+`tests/` od `a7e89e5` beze změny;
větev feat/m2-m3-geometry)
- `python tests/run_all.py` → **372 běhů, 368 PASS, 0 FAIL, 0 ERROR, 4 PENDING**
  (vlastní běh 2026-11-19; historické: 279/275 @ `ff4a9d6` (PR #2),
  260/256 @ `ff6f266`; PENDING totožné, PENDING≠PASS).
- Sady M2 (@ `a7e89e5`): `test_m2_rbxm_parser.py` 57 testů, `test_m2_wheel_detect.py` 53,
  `test_m2_scale_calibration.py` 31, `test_m2_rbxm_inspector.py` 7,
  `test_m2_integration.py` 20; M1: `test_m1_mustang_profile.py` 22 (T01–T22);
  CI-portability 11 + loader-root 5.
- `tools/validate_contracts.py` → 24/0 ÚSPĚCH (@ `36cbbdb`, commit message;
  M1.9 výjimka i v contracts validátoru).
- CI: `53c2e23` fix (repo-relative fixture, SKIP místo ERROR, portability testy
  `tests/test_ci_portability.py`).
- RBXM: `assets/chassis-original/chasis-work-copy.rbxm` —
  `dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf`
  (před/po shodné, pouze čteno). Druhý soubor v repu
  (`testgame/.../JeepTemplate.rbxm`) má stejný hash, rovněž beze změny.

### 0.5 Otevřené body
1. Kalibrace měřítka (M2.9/M2.10, C06) + měření rozvoru/rozchodů — engine
   IMPLEMENTED + CODE-VERIFIED (`src/Inspection/scale_calibration.py`, 31 testů),
   měření a výsledek kalibrace BLOCKED (assess `float_decode_unverified`;
   JeepTemplate rozptyl 7,44 % > 5 %), největší riziko plánu. Parser C05 je hotov
   (CODE-VERIFIED, viz §0.2; jeho `calibrate_studs_per_meter` je jen záměrný
   NOT-IMPLEMENTED stub, ne engine).
2. M3 Geometry Engine NOT IMPLEMENTED — blokováno bodem 1 (bez VERIFIED měřítka
   žádné cíle; M3 brána `require_verified_for_m3`, M3 NEOTEVŘENA).
3. Rozhodnuto a uzavřeno: final drive ZŮSTÁVÁ UNKNOWN (kandidáti 3.15/3.55 jen v notes,
   rozhodnutí uživatele); trvale UNKNOWN bez nového zdroje: momentová křivka, rozložení
   hmotnosti + těžiště, brzdový bias, Cd/plocha.
4. 4× PENDING není PASS (Roblox Studio odečet, schema conformance Fáze 5, 2× regresní baseline);
   Studio ground-truth kol `reports/STUDIO_GROUND_TRUTH.md` = DONE 2026-11-19
   (rozvor ≈10.52 / rozchod ≈5.99 / Ball 2.7³ potvrzeny vs. parser — hodnoty
   potvrzeny, ale stupeň zůstává CODE-VERIFIED, není RUNTIME; runtime jízda žádná).

---

## 1. Stav modulů M1–M9 — HISTORICKÉ (audit před implementací, NEMAZAT)

| Modul | Stav | Důkaz |
|---|---|---|
| M1 Vehicle Specs | PARTIAL | `_schema.json` + `loader/validate/compare` + vozy civic, gr86, mustang GT 2024 EU factory standard (20 testů M1-T01…M1-T20 PASS) |
| M2 RBXM Inspector | NOT IMPLEMENTED | žádný RBXM parser v `src/` ani `tools/` (pouze zmínky v docs) |
| M3 Geometry Engine | NOT IMPLEMENTED | žádný modul; `src/common/units.py` existuje (rozšířit) |
| M4 Physics v2 | PARTIAL | `src/Physics/` 10 modulů + selftesty; chybí torque_curve s UNKNOWN, cíle Mustangu, nejistoty |
| M5 A-Chassis Mapping | PARTIAL | katalog **138** parametrů (82 MUTABLE_TUNE / 37 UNKNOWN / 14 SCRIPT / 3 READ_ONLY / 2 STRUCTURE) + `mapping_engine.py` + `dependencies.py`; chybí vazba cíl→Tune a change planner |
| M6 Config & Rollback | PARTIAL | `Optimizer/{change_plan,store}.py` + manifest kontrakt; chybí generátor balíčků, diff, rollback |
| M7 Test Protocol | PARTIAL | scénáře (`Sim/scenarios.py`, Lua, 11 scénářů v TESTING-OPTIMIZATION); chybí generátor lidských protokolů + formulář |
| M8 Evaluator | PARTIAL | `Telemetry/{evaluate,metrics}` + `Optimizer/{statistics,acceptance}`; chybí loader měření, opakovatelnost, advisor |
| M9 Workflow | PARTIAL | `autoengineer.py` CLI + optimizer cyklus; chybí orchestrace M1→M8, stav iterací, reporty |

## 2. Duplicity a kolize (ověřeno čtením)

1. `vehicle-data/references/_schema.json` (bohatý DB záznam) vs. `contracts/reference_profile.schema.json` (úzký pipeline profil) — **vyřešeno**: propojení `source_vehicle_id` (`CONTRACTS.md` §1.5). Neměnit.
2. `src/Physics/gearbox.py` vs. navržený `transmission_model.py`; `src/Physics/brakes.py` vs. `braking_model.py` — **rozšířit existující, nezakládat nové** (povinnost v ROADMAP M4/M6).
3. `src/Telemetry/statistics` vs. `src/Optimizer/statistics.py` — před M8 sjednotit, ne duplikovat.
4. `docs/STATUS.md` (fázový log F0–F7) vs. tento `PROJECT_STATUS.md` (maticový audit M1–M9) — koexistují, každý jiný účel.
5. `AGENTS.md` (root, nový) vs. `docs/AGENT-RULES.md` — AGENTS odkazuje na AGENT-RULES, nenahrazuje ho.

## 3. Chybějící části (must-have před implementací)

RBXM parser (M2 — největší riziko plánu) · mustang profil (M1.5) · torque_curve s UNKNOWN (M4.4) ·
vazba cíl→Tune + change planner (M5.3/M5.8) · generátor balíčků + rollback (M6) · protokol generátor +
formulář (M7) · loader měření + advisor (M8) · orchestrace M9.

## 4. Historie F4–F7 (experimentální a validační, nepřepisovat)

- **F4** ověřoval dílčí fyzikální chování v Roblox Physics Engine (parametrická inteligence, integrace, kalibrace).
- **F5** odhalil problémy životního cyklu vozidla a kol (kola zamčená, Drive stale; `F5-CLOSURE.md`).
- **F6** ověřil část brzdného chování (BrakeBias 0,6→56,53 / 0,9→40,44 studs), ne celý produkt.
- **F7.1** ověřoval vlastní ServerDrive harness (Q4 dead-man, RAW-DEFER, T01B), nikoli plný původní A-Chassis runtime.
- **F7.2** (HEAD `dd9efdf`): ServerSteer.Step + S0 snapshot + AC6 Occupant-only + review-fix (radiány, monErr, settle bez Forget, S0 identita, SitTestDriver, self-testy). **Runtime ověření AC1–AC7 je samostatný úkol** — tento dokument ho neprohlašuje za hotové.
- `reports/F7/ROJO-INCIDENT.md`, `reports/F6/`, `reports/F7/runs/` (telemetrie run-001…003) se zachovávají.

## 5. Neověřené údaje Mustangu (z `VEHICLE-SPECIFICATIONS.md`)

Stálý převod (kandidáti 3.15:1/3.55:1 bez přiřazení) · momentová křivka · rozložení hmotnosti a těžiště ·
bias · Cd/čelní plocha. Vše UNKNOWN (převody 1–6, brzdy Brembo, kola, 0–100 5,3 s, V-max 250 km/h jsou od M1.5 VERIFIED).

## 6. Konzistence dokumentace (kontrola této branche)

- Cíle/ID úkolů (M1.1–M9.12, M1-T01–M4-T10, AE-001–AE-021 níže) shodné v ROADMAP, ACCEPTANCE a HYBRID_WORKFLOW. ✓
- Odkazy na soubory ověřeny proti file listingu; neexistující moduly označeny jako navržené. ✓
- Žádný modul nemá duplicitní odpovědnost (§2). ✓
- Závislosti M1–M9 dávají smysl (M2 je kritická cesta). ✓

## 7. Pořadí GitHub issues (návrh ID, nejsou založené)

| Issue | Název | Priorita | Závislost |
|---|---|---|---|
| AE-001 | Vehicle Specification Schema | P0 | — |
| AE-002 | Mustang GT EU Profile | P0 | AE-001 |
| AE-003 | Source & Confidence Validation | P0 | AE-001 |
| AE-004 | RBXM Geometry Inspection | P0 | — |
| AE-005 | Unit Conversion System | P0 | — |
| AE-006 | Scale Calibration | P0 | AE-004, AE-005 |
| AE-007 | Geometry Target Calculator | P0 | AE-002, AE-006 |
| AE-008 | Geometry Validation | P0 | AE-007 |
| AE-009 | Physics Model Refactor | P0 | AE-002 |
| AE-010 | Engine & Transmission Models | P0 | AE-009 |
| AE-011 | Tire & Braking Models | P0 | AE-009 |
| AE-012 | A-Chassis Parameter Registry | P0 | existující katalog |
| AE-013 | Target-to-Tune Mapping | P0 | AE-007, AE-010, AE-012 |
| AE-014 | Dependency & Conflict Validation | P0 | AE-013 |
| AE-015 | Configuration Generator | P1 | AE-014 |
| AE-016 | Configuration Rollback | P1 | AE-015 |
| AE-017 | Manual Test Protocol Generator | P1 | AE-015 |
| AE-018 | Measurement Import & Validation | P1 | AE-017 |
| AE-019 | Statistical Evaluator | P1 | AE-018 |
| AE-020 | Iteration Advisor | P1 | AE-019 |
| AE-021 | End-to-End Hybrid Workflow | P1 | AE-001…AE-020 |

## 8. Pořadí commitů (návrh C01–C16)

C01 schema · C02 mustang profil · C03 validace zdrojů · C04 jednotky · C05 RBXM inspekce ·
C06 kalibrace měřítka · C07 geometry engine · C08 fyzikální modely · C09 A-Chassis registry integrace ·
C10 mapování a validace · C11 generátor konfigurací · C12 rollback a manifesty · C13 testovací protokol ·
C14 evaluator · C15 iteration advisor · C16 end-to-end workflow. Každý commit = kód + testy + výsledek.

## 9. Nezávislá kontrola M1+M2 + M1.5 (Agent D, 2026-11-19)

- **Profil vs. validátor:** všechny pokusy o obejití M1.9 odmítnuty (1 bod → minItems;
  body bez point_type → schéma+point_type; estimate bez 'ODHAD:' → chyba;
  factory bez zdroje → chyba; prázdná křivka s interpolation≠none / confidence 0.9 →
  výjimka neplatí, minItems chyba). Žádná vada validátoru nenalezena.
- **M1.5 provedeno** dle `reports/MUSTANG-SOURCE-CHECK.md`: 22 obálek povýšeno na
  factory (motor vč. vrtání/zdvihu, rozměry vč. nové šířky se zrcátky 2080 mm,
  pneu P/Z); hmotnost 1808 kg ponechána ESTIMATED (Ford sám uvádí „Est.");
  UNKNOWN zůstává (křivka, rozložení, bias, Cd, stálý převod) + kandidáti v notes
  (převody 6MT, final drive 3.15/3.55, 0–100 5,3 s, V-max 250, brzdy 390/355 mm —
  jako VERIFIED nepřidáno). Profil validuje 0 chyb / 0 varování.
- **Kola:** rozhodovací pravidlo drží (Ball mimo Wheels nikdy kolo; duplicita / 3 kola /
  2×Wheels → BLOCKED). Doplněny 2 testy (2×Wheels, cyklus v parents).
- **SPEC:** opraven překlep ADAC URL (`rund-ums-fahrzeug`) + doplněn mirror [1b].
- **Testy:** `tests/run_all.py` → 192 běhů, **188 PASS, 0 FAIL, 4 PENDING** (PENDING beze změny).
- **Otevřené body pro uživatele:** (1) varianta „standard GT bez Packu" vs. EU realita
  (Performance Pack zřejmě standardem EU GT — brzdy/LSD z [1b] proto nezamčeny);
  (2) kandidáti M1.5 (převody, final drive, 0–100, V-max, brzdy) ke schválení jako VERIFIED.

### Kontrolní opakování po povýšení M1.5 (Agent D, 2026-11-19, rozhodnutí uživatele)
- **Rozhodnutí zapracováno:** varianta přejmenována na EUROPEAN FACTORY STANDARD
  SPECIFICATION, `vehicle_id` beze změny; povýšeno na VERIFIED: poměry 1–6
  (3.237/2.104/1.422/1.000/0.814/0.622), 0–100 5,3 s, V-max 250 km/h, kotouče
  390x36/355x28 + Brembo six-piston, LSD obecně, kola 19x9.0J/19x9.5J + pneu
  255/40–275/40 R19 — vše factory, confidence ≥ 0.85, zdroj s URL [1]/[1b] + datem.
- **Zdroje:** každé VERIFIED má URL Ford EU PDF/mirror + datum 2026-11-19,
  confidence ≥ 0.8; žádné US hodnoty (Torsen/Tremec/Dark Horse/453 PS jen
  v notes-negacích a GT-vs-Dark-Horse rozlišení sloupců, nikoli jako hodnoty).
- **Stavy:** final_drive UNKNOWN s oběma kandidáty v notes + GUARD test T17
  (použití jako definitivní hodnota → chyba); křivka/rozložení/bias/Cd UNKNOWN s `CHYBÍ:`.
- **Validace:** profil 0 errors / 0 warnings; M1 sada 20/20 PASS;
  `tests/run_all.py` → 199 běhů, **195 PASS, 0 FAIL, 4 PENDING** (PENDING beze změny).
- **Návaznost M1→M2:** `contracts/` nedotčeny (jen 4 soubory M1 v diffu),
  inspection_report kontrakt beze změny; profil použitelný pro M3/M4 cíle
  (6 poměrů, Pmax/Mmax, pneu, rozměry), final_drive blokován GUARDem.
- **Opraveno touto kontrolou:** ROADMAP M1.13 (stale „převody, brzdy UNKNOWN") +
  M1.14 („profil chybí"); PROJECT_STATUS §1 a §5 (stale UNKNOWN výčty).
  Verdikt: **PASS** (otevřené body z 9. odstavce uzavřeny rozhodnutím uživatele).

## 10. Opravná vlna M2 (větev feat/m2-m3-geometry, 2026-11-19)

- Klasifikace: 4-tier (VALID_WHEEL 4× FL=3/FR=52/RL=101/RR=150 / KNOWN_NON_WHEEL
  44× = allowlist 11 dílů × 4 / UNKNOWN_CANDIDATE / INVALID_WHEEL);
  0 unidentified; KNOWN_NON_WHEEL evidováno, neblokuje (celek drží BLOCKED
  z assess + kalibrace, viz níže).
- Parser: MSB-first ověřen Studiem (4×Ball + 104×Block + 1×Cylinder, 0 nepřečtených
  shape-enumů); C05 CODE-VERIFIED (jeho `calibrate_studs_per_meter` je záměrný
  NOT-IMPLEMENTED stub, ne kalibrační engine).
- Kalibrace: engine `src/Inspection/scale_calibration.py` IMPLEMENTED +
  CODE-VERIFIED (31 testů); výsledek na JeepTemplate BLOCKED 7,44 % > 5 %
  (očekávané — jiné vozidlo, ne defekt); M3 brána pouze VERIFIED
  (`require_verified_for_m3`).
- I-1: assess-BLOCKED se propaguje do inspection_report (fail-closed).
- Studio: rozchod 5,9907 / rozvor 10,5228 potvrzeny bit-přesně (Edit, read-only).
- QA verdikt: M2 CONDITIONAL PASS; brána M3 NEOTEVŘENA.
- M3 zůstává návrh bez kódu. Detail: `reports/M2-M3/REMEDIATION-WAVE-FINAL-REPORT.md`.
- Finální closeout (tato větev): `reports/M2-M3/FINAL-CLOSEOUT-REPORT.md`,
  `reports/M2-M3/FINAL-INDEPENDENT-QA.md` (M2 CONDITIONAL PASS, M3 NEOTEVŘENA,
  runtime NOT VERIFIED).
