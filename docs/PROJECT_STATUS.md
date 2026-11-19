# Project Status – stav k 2026-11-19 (větev `feat/m1-m2-foundation`, PR #2)

**Aktuální stav:** M1 + M2 (profil, parser INST/PRNT/Shape/Size/CFrame, detekce kol) hotovo na této větvi; testy
**260 běhů, 256 PASS, 0 FAIL, 4 PENDING** (`python tests/run_all.py`, PENDING beze změny).
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

### 0.2 M2 – spike + detekce kol (hotovo); produkční parser a měření NENÍ hotovo
- Hotovo: RBXM spike (viz `reports/RBXM-SPIKE.md`), rozhodovací pravidlo kol
  `(a) v Model:Wheels + (b) FL/FR/RL/RR + (c) tvar Ball` v
  `src/Inspection/wheel_detect.py` (19 testů v `tests/test_m2_wheel_detect.py`, vše PASS).
- P0 oprava (tato změna): cyklus v parent hierarchii ani chybějící parent ID
  ani duplicitní instance ID se nikdy neklasifikuje jako validní — vždy BLOCKED
  (`parent_cycle` / `missing parent id` / `duplicate instance id` v blocked_reasons).
- NOT IMPLEMENTED / BLOCKED: produkční RBXM parser (C05/C06) a měření
  rozvoru/rozchodů z geometrie — žádné měření se neodhaduje, vše UNKNOWN/BLOCKED.

### 0.3 M3–M9 (beze změny)
- M3 Geometry Engine NOT IMPLEMENTED; M4/M5/M6/M7/M8/M9 PARTIAL dle historického
  auditu §1 (stav před implementací této větve).

### 0.4 Testy a RBXM integrita (nový běh 2026-11-19)
- `python tests/run_all.py` → **260 běhů, 256 PASS, 0 FAIL, 4 PENDING**
  (baseline před změnou 199/195/0/4; +6 nových adversarial testů cyklů/hierarchie,
  1 test přepsán z OK na BLOCKED; PENDING totožné).
- RBXM: `assets/chassis-original/chasis-work-copy.rbxm` —
  `dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf`
  (před/po shodné, pouze čteno). Druhý soubor v repu
  (`testgame/.../JeepTemplate.rbxm`) má stejný hash, rovněž beze změny.

### 0.5 Otevřené body
1. Produkční RBXM parser (C05/C06) + kalibrace měřítka (M2.9/M2.10) — největší riziko plánu.
2. Měření rozvoru/rozchodů — NOT IMPLEMENTED, blokuje M3 cíle.
3. Rozhodnuto a uzavřeno: final drive ZŮSTÁVÁ UNKNOWN (kandidáti 3.15/3.55 jen v notes,
   rozhodnutí uživatele); trvale UNKNOWN bez nového zdroje: momentová křivka, rozložení
   hmotnosti + těžiště, brzdový bias, Cd/plocha.
4. 4× PENDING není PASS (Roblox Studio odečet, schema conformance Fáze 5, 2× regresní baseline).

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
