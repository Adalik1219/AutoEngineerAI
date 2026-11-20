# Agent D — strategie A-Chassis / Mustang: vyřazení Jeepu z Mustang workflow

Větev `feat/m2-m3-geometry` @ `90a1f63` (strom čistý). Rozsah: pouze čtení +
tento report; žádné změny kódu, testů, katalogů ani RBXM. M3 ZAVŘENÁ, main/PR#2 tabu.

## 0. Závěr (rozhodnutí)

1. **Výchozím technickým základem zůstává původní A-Chassis.** Cílovým vozidlem je
   Ford Mustang GT 2024 EU Fastback. **JeepTemplate není součástí aktivní Mustang
   kalibrace ani cílové konfigurace.**
2. **Žádná věta typu „JeepTemplate je reference/základ Mustangu" v repozitáři
   neexistuje** — proto bylo upraveno **0 .md souborů** (pravidlo: nic jiného v .md neměnit).
3. **Jeep není nikde aktivní kalibrační referencí** (0 výskytů). Návrh kalibrační
   větve Jeep→Jeep (Agent A §P2(a)/P12, REMEDIATION-WAVE, FINAL-NIGHT-REPORT)
   se pro Mustang workflow **ZAMÍTÁ** — chybějící Mustang = UNKNOWN, M3 zůstává ZAVŘENÁ.
4. Datová cesta vstup→konfigurace je čistá: **žádné Jeep hodnoty se nepřenášejí
   jako Mustang hodnoty**. Jediná díra je popisná (label `vehicle_id` na BLOCKED
   výsledku) → patch-návrhy P-D1/P-D2 pro koordinátora, BEZ implementace.

## 1. Úplný seznam výskytů (205 řádků s „jeep", case-insensitive, bez .git/__pycache__)

Metoda: `grep -rni "jeep" src tests vehicle-data docs reports AGENTS.md`
(204 řádků) + AGENTS.md 1 řádek = **205**. Binárky: 2× RBXM, 1 distinctní model
(`dc8747e016e1…fefdf`, 230 421 B) — `JEEP_COPY == WORK_COPY`, evidovaný LIMIT, ne defekt.
`contracts/` + `tools/`: 0 výskytů. Mustang RBXM v repu neexistuje (pouze
`testgame/.../JeepTemplate.rbxm`; `find -iname "*mustang*"` vrací jen profil,
M1 test a reporty).

| Soubor | Řádků | Kategorie |
|---|---|---|
| tests/test_ci_portability.py | 15 | aktivní testovací model (fixture SHA/size, read-only) |
| tests/test_m2_rbxm_parser.py | 11 | aktivní testovací model (čtení fixture, hash před/po) |
| tests/test_m2_scale_calibration.py | 7 | **aktivní vstup do výpočtu** (JEEP_MEAS → calibrate → BLOCKED) |
| tests/test_m2_integration.py | 5 | aktivní testovací model (fixture + label; měřicí dict bez slova jeep) |
| tests/test_m2_wheel_detect.py | 5 | aktivní testovací model (label `vehicle_id`/`report_id`) |
| tests/test_m2_rbxm_inspector.py | 3 | aktivní testovací model (čtení kopií) |
| tests/test_f4_mapping.py + test_f4_integration.py | 4 | aktivní testovací model (PENDING skip bez fixture) |
| src/Chassis/adapters/achassis_v1.py:430 | 1 | dokumentační zmínka (kit 'Jeep' = vrstva A) |
| vehicle-data/analyzed/live-tune-keys.txt:2 | 1 | archivní záznam (zdroj klíčů F4.3, vrstva A) |
| AGENTS.md:14 + docs/ (5 souborů) | 13 | dokumentační zmínka (read-only pravidla, BLOCKED status) |
| reports/M2/SCALE-CALIBRATION-REPORT.md | 11 | historický report (BLOCKED 7,44 % = správné chování) |
| reports/M2/STUDIO-GROUND-TRUTH.md | 3 | historický report (měření 5.9907/10.5228/2.7) |
| reports/M2/RBXM-INSPECTOR-REPORT.md + SHAPE-CROSS-CHECK.md | 4 | historický report (vstup + křížová kontrola) |
| reports/M2-M3/FINAL-INDEPENDENT-QA.md | 19 | historický report (19×; obsahuje matoucí zkratku — viz P-D4) |
| reports/M2-M3/ostatní (9 souborů) | 22 | historický report (audity, verdikt, integrace, remediace) |
| reports/M3/GEOMETRY-ENGINE-PROPOSAL.md | 2 | historický report (M3 BLOKOVÁNA kalibrací) |
| reports/AUDIT-test-baseline, AUDIT3-tech-qa, FINAL_INDEPENDENT_QA | 4 | historický report |
| reports/STUDIO_GROUND_TRUTH, STUDIO_RUNTIME, RBXM-SPIKE, ROBLOX-TEST-ENV-CLOSURE | 8 | historický/archivní (měření, snapshot, šablona) |
| reports/F43–F7 (F43-QA/RUNFIX/BRAKEBIAS/MEASURE/STRUCTURE, F44×3, F5-QA/CLOSURE, F6-PLAN/QA/runs×2, F7-PLAN/console) | 35 | archivní záznam (běhové klony `Jeep_*`, cleanup, šablona nedotčena) |
| reports/NIGHT-WORK (A-diagnostic 10, C-requirements 9, B-audit 1, D-readiness 3, F-mapping 2, COORDINATOR 2, FINAL-NIGHT 5) | 32 | pracovní reporty dnešní noci (kontext, nemazat) |

### Součty dle kategorií

| Kategorie | Počet | Verdikt |
|---|---|---|
| Aktivní vstup do výpočtu | **7** | JEEP_MEAS (10.5228/5.9907/2.7) krmená do `calibrate()` proti mustangovským referencím → BLOCKED 7,44 %; správně, ponechat |
| Aktivní kalibrační reference | **0** | klíčový nález: `default_references()` = Mustang M1, Jeep v referencích nikde |
| Aktivní testovací model | **43 řádků + 2 binární RBXM** | fixture/labely, read-only, PENDING fallback; správně, ponechat |
| Dokumentační zmínka (aktivní docs/src/data) | **15** | vše formulováno správně (Jeep = měřený vstup/jiné vozidlo) → **0 .md úprav** |
| Archivní záznam | **35** | uzavřené runtime vlny F43–F7; nemazat, needitovat |
| Historický / pracovní report | **105** (z toho NIGHT-WORK dnešní noci 32) | nemazat; matoucí zkratky evidovat, neopravovat přepsáním (P-D4) |
| **Celkem** | **205** | |

## 2. Kde je Jeep aktivním prvkem Mustang workflow? (jediné dvě místa — obě správně blokovaná)

1. `tests/test_m2_scale_calibration.py :: TestJeepTemplateGroundTruth` (ř. 197–221):
   `JEEP_MEAS = {wheelbase 10.522796630859375, track_f 5.99066162109375,
   track_r 5.99072265625, tire_d_f/r 2.7}` → `calibrate(measurements_studs=… jeden
   proti `default_references()` (Mustang: 2.719 / 1.585 / 1.642 VERIFIED, pneu
   ESTIMATED) → rozptyl 7,44 % > 5 % → BLOCKED, `estimates=[]`, brána
   `require_verified_for_m3()` vyhazuje. Jeep zde figuruje jako **měřený vstup,
   ne reference** — vyřazení by znamenalo smazat negativní test; **NEDOPORUČUJI**.
2. `tests/test_m2_integration.py :: _full_chain` (ř. 86): měření z reportu +
   `calibrate(meas)` proti mustangovským referencím → BLOCKED propagace M2→M3.
   Label `vehicle_id="JeepTemplate"` je správně na straně měření. Ponechat.

## 3. Patch-návrhy pro koordinátora (NEPROVÁDĚT — kód/testy neměnit)

- **P-D1 (test, nízké riziko):** `tests/test_m2_scale_calibration.py`, ř. 210–221 —
  obě volání `calibrate(measurements_studs=dict(self.JEEP_MEAS))` přebírají default
  `vehicle_id="ford-mustang-gt-2024-eu-manual-standard"`, takže BLOCKED výsledek
  spočtený z Jeep měření nese mustangovské ID (popisná díra, ne datový přenos —
  `estimates` je prázdné). Návrh: `calibrate(vehicle_id="JeepTemplate",
  inspection_ref="studio-ground-truth", measurements_studs=dict(self.JEEP_MEAS))`
  v obou testech. Tím bude i BLOCKED výstup pravdivě labelován.
- **P-D2 (test, návrh k rozhodnutí):** `tests/test_m2_integration.py`, ř. 86 —
  `def _full_chain(path, vehicle_id="JeepTemplate"):` ponechat funkčně; zvážit
  odstranění defaultu (povinný parametr), aby budoucí mustangovský RBXM nedostal
  omylem label JeepTemplate. Nesmí změnit chování brány.
- **P-D3 (strategie, ZAMÍTNUTÍ větve):** návrhy „doložit referenční rozměry Jeepu a
  kalibrovat Jeep→Jeep" (`reports/NIGHT-WORK/AGENT-A-M2-DIAGNOSTIC.md` §P2 návrh (a),
  §P12, §12-bod 2; `reports/M2-M3/REMEDIATION-WAVE-FINAL-REPORT.md:67`;
  `reports/NIGHT-WORK/FINAL-NIGHT-REPORT.md:101,155` „Jeep reference sada") —
  pro Mustang workflow **ZAMÍTNUTO**: referenční sada Jeepu by vytvořila paralelní
  kalibrační cíl mimo cílové vozidlo. Chybějící Mustang měření = UNKNOWN, M3 ZAVŘENÁ.
  (Samostatná Jeep→Jeep větev by vyžadovala lidské schválení + vlastní M1-profil
  Jeepu; není součástí M1–M3.)
- **P-D4 (koordinátor, terminologie):** zkratka „reálný Mustang (pracovní kopie je
  JeepTemplate…)" v `reports/M2-M3/FINAL-INDEPENDENT-QA.md` (ř. 60, 147, 217, 231,
  286) a obdobně `INDEPENDENT-QA-VERDICT.md:60` — historické reporty **needitovat**;
  případné upřesnění pouze novým reportem ve znění §0-bod 1. Riziko: čtenář si
  vyloží Jeep jako náhradu Mustangu.
- **P-D5 (ověřeno, bez akce):** `src/Inspection/scale_calibration.py`
  `default_references()` (ř. 78–110) = výhradně Mustang M1 reference; žádný kód
  Jeep hodnoty do referencí nevkládá; `contracts/` + `tools/` 0 výskytů; adaptér
  `achassis-v1` kit 'Jeep' je vrstva A (zdroj pravdy Tune+geometrie), ne cíl.

## 4. Mapa vrstev

- **A — původní A-Chassis (výchozí technický základ, read-only):**
  `assets/chassis-original/chasis-work-copy.rbxm` + `testgame/.../JeepTemplate.rbxm`
  (AC6C kit 'Jeep', karoserie Jeep, `A-Chassis Tune`, 815 instancí / 37 typů),
  `src/Chassis/adapters/achassis_v1.py` (kit 'Jeep'), `vehicle-data/analyzed/live-tune-keys.txt`.
  Vše měřeno čteno, nikdy zapisováno (hash `dc8747e0…fefdf` před/po shodný).
- **B — cíl Mustang (neměřený, referenční):** `docs/VEHICLE-SPECIFICATIONS.md`,
  `vehicle-data/references/ford-mustang-gt-2024-eu-manual-standard.json`,
  `default_references()` (rozvor 2.719 / track_f 1.585 / track_r 1.642 VERIFIED,
  pneu ESTIMATED). Žádný Mustang RBXM v repu; žádná Studio Mustang měření.
- **C — výsledná konfigurace: NEEXISTUJE.** M3 NOT IMPLEMENTED, brána
  `require_verified_for_m3()` drží (pouze VERIFIED). Každý reálný výstup je
  UNKNOWN/BLOCKED. Sloučená konfigurace A→B nesmí vzniknout bez VERIFIED měřítka;
  do té doby platí: chybějící Mustang údaj = UNKNOWN, ne odhad, ne Jeep hodnota.

## 5. Ověření datové cesty vstup→konfigurace

- Vstup: Jeep měření (Studio ground-truth 10.5228/5.9907/2.7 = JEEP_MEAS bit-přesně,
  `reports/M2/STUDIO-GROUND-TRUTH.md:49–60` vs test ř. 202–208) → parser →
  `detect_wheels` (4× VALID_WHEEL) → `assess` BLOCKED (`float_decode_unverified`) →
  `report` BLOCKED → `calibrate` BLOCKED (7,44 %) → M3 brána vyhazuje.
- Na žádném kroku se Jeep číslo nezapisuje do Mustang profilu ani do
  `default_references()`; `vehicle-data/references/ford-mustang-*.json` obsahuje
  pouze M1 ověřené hodnoty. Výjimka: label `vehicle_id` na BLOCKED výsledku P-D1
  (kosmetické, bez přenosu hodnot).
- Chybějící Mustang (měřítko, torque_curve, final drive, bias) = UNKNOWN — potvrzeno
  v profilu i kódu (`calibrate` vrací UNKNOWN při absenci měření).

## 6. Co bylo upraveno / co ne

- **Upraveno 0 .md souborů.** Systematicky prověřeny všechny věty o Jeep/Mustang
  v `docs/` (12), `AGENTS.md` (1), `src` docstring (1): žádná netvrdí, že JeepTemplate
  je reference/základ Mustangu — všechny správně (read-only pravidla, BLOCKED status,
  „jiné vozidlo"). Dle kontextu („nic jiného v .md neměň") proto žádná editace.
- Historické reporty nedotčeny (ani mazány). Jediný zapsaný soubor: tento report.
- Potvrzení základu: `chasis.rbxm` = AC6C kit + karoserie „Jeep" + kolizní model +
  světla + 4× custom zavěšení (`docs/A-CHASSIS-AUDIT.md:68`); adaptér `achassis-v1`
  je postaven na tomto základu (Tune + geometrie ramen jako zdroj pravdy).
