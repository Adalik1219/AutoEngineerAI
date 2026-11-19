# M2 WHEEL-GEOMETRY-REPORT (Agent B — Wheel & Geometry)

Větev `feat/m2-m3-geometry` (HEAD `a7e89e5`, historie: `ab840a9` →
`c1a138b` Agent-A audit §8 → `a7e89e5` Agent-B sync; PR #2 OPEN jinde,
NEMERGOVAT), zpráva ke kontraktu
`reports/M2-M3-CONTRACTS-FREEZE-v1.md` §inspection_report.json (tvar ZÁVAZNÝ).

## 1. Cíl

Identifikace 4 kol + writer `inspection_report.json` dle kontraktu + testy.
Vlastněné soubory: `src/Inspection/wheel_detect.py`,
`tests/test_m2_wheel_detect.py`, tento report. `rbxm_parser.py` (assess)
se NEMĚNÍ — jen se čte.

## 2. Empirická data (parser vs Studio — POTVRZENO)

Pracovní kopie `assets/chassis-original/chasis-work-copy.rbxm`,
SHA-256 `dc8747e0…fefdf` (před/po shodné, read-only).
Zdroj: `reports/STUDIO_GROUND_TRUTH.md` §3 (Studio Edit, read-only) +
vlastní běh `parse_rbxm` + `assess_wheel_geometry` nad kopií.

| Kolo | id | Střed (x, y, z) | Size | Shape |
|---|---|---|---|---|
| FL | 3 | (-45.18788909, 23.62214279, -203.25036621) | 2.7³ | Ball |
| FR | 52 | (-51.17855072, 23.62214279, -203.25039673) | 2.7³ | Ball |
| RL | 101 | (-45.18785858, 23.62214279, -213.77316284) | 2.7³ | Ball |
| RR | 150 | (-51.17858124, 23.62214279, -213.77316284) | 2.7³ | Ball |

Odvozeno (float32, přesně): rozchod př./zad. **5.99066162109375 /
5.99072265625** (Δ≈6.1e-05, float32 šum — shoda, ne asymetrie),
rozvor **10.5227813720703125** (průměr L/R párů), pneumatiky **2.7**,
Y-spread **0.0**. Souhlasí se Studio `version()` měřením na 8 desetinných
míst (Size `2.700000047683716³` = float32 2.7).

## 3. Souřadnicový rámec — ROZPOR s návrhem příkazu (explicitní záznam)

Návrh příkazu: `X=vpřed / Y=vlevo / Z=vzhůru`. **Na datech NEPLATÍ:**

- osa rozchodu (L/R, 5.99) = **X** (FL.x≠FR.x), ne Y;
- osa rozvoru (F/R, 10.52) = **Z** (FL.z≠RL.z), ne X;
- **Y je konstantní 23.622142791748047** na všech kolech = výška, ne vlevo.

Implementováno skutečné mapování (Roblox Y-up), kódováno v
`COORDINATE_FRAME_ACTUAL` (`wheel_detect.py`):

- `x = lateral: left/right` (L = větší X, R = menší X),
- `y = up: výška` (konstantní),
- `z = longitudinal: front/rear` (F = větší Z, R = menší Z),
- `verified_in_studio = true`.

Slepé převzetí návrhu by prohodilo rozchod/rozvor/výšku. Rohová kontrola
writeru (`F=větší Z, L=větší X`) je na tomto rámci; záměny stran/náprav
detekuje jako `side_or_axle_swap` → BLOCKED. Záměna je kryta testem
`test_coordinate_frame_is_actual_not_command_convention`.

## 4. 44 dílů podvozku ve Wheels — KNOWN_NON_WHEEL (4-tier, NEBLOKUJE)

`Model:Wheels` (id 2) obsahuje **48** Partů: 4 kola (Ball FL/FR/RL/RR) +
**44 dílů podvozku** (`SpringBottom/CLower/CUpper/SpringTop/LowerArmB/
LowerArmF/Hub/LowerArm/UpperArmF/UpperArmB/UpperArm` × 4, shape Block,
ověřeno parserem na pracovní kopii — 11 názvů × 4 instance).
Pravidlo identity (a)+(b)+(c) je legitimně neklasifikuje jako kola;
nově spadají do tieru **KNOWN_NON_WHEEL** (`CHASSIS_PART_ALLOWLIST`):
neblokují, zůstávají evidovány v `known_non_wheels` (detect i writer).
Ověřeno end-to-end na reálné kopii (`dc8747e0…fefdf`, read-only,
hash před/po shodný):
`detect_wheels` → 4× VALID_WHEEL + 44× KNOWN_NON_WHEEL, 0 unidentified,
`blocked = false`; `assess` 4× GEOMETRY_OK, `blocked` (kalibrace
`float_decode_unverified` — 44 dílů už jako unidentified nefiguruje);
`report_from_assess` překlápí allowlistové záznamy na known_non_wheels a
propaguje assess-BLOCKED (I-1) → `overall_status = BLOCKED`, číselně
`wheelbase 10.52278`, rozchod 5.99066/5.99072, Y-spread 0.0 — vše souhlasí s §2.
Neznámý kandidát vedle allowlistu (např. Spare) blokuje jako dosud.

Poznámka pro M3: důvod `float_decode_unverified` v assess je zastaralý —
Studio ground-truth od jeho napsání existuje (tento report §2). Vymazání
tohoto důvodu po ověření kalibrace je věc vlastníka `rbxm_parser.py`,
ne tohoto modulu.

## 5. Writer `inspection_report.json`

`build_inspection_report(...)` + `report_from_assess(...)` v
`src/Inspection/wheel_detect.py`; schema `INSPECTION_REPORT_SCHEMA`
přepsáno ze starého "návrhu M2 spike" na ZÁVAZNÝ tvar kontraktu
(`report_id / vehicle_id / source_file / source_sha256 /
parser_version / code_version / wheels[] / axles / wheelbase_studs /
tire_diameters_studs / coordinate_frame / method / warnings[] /
overall_status`). Pravidla: chybějící kolo (count≠4) / UNKNOWN ve Wheels /
swap / asymetrie → BLOCKED; chybějící geometrie nebo
`verified_in_studio=false` → strop UNKNOWN; jinak GEOMETRY_OK.
Deterministické (`report_id = vehicle_id@sha256[:12]`, žádné časy),
žádný odhad — chybějící hodnota je `None` + reason.

## 6. Testy — 53/53 OK v modulu, 110/110 s parserem (18 povinných 4-tier v `TestWheelFourTier`)

`python3 -m unittest tests.test_m2_wheel_detect tests.test_m2_rbxm_parser`
→ **110 testů, OK** (z toho `test_m2_wheel_detect`: 53 — 35 původních
pravidel identity/writeru beze změny chování + 18 nových 4-tier):
4 kola VALID_WHEEL (Studio id 3/52/101/150); 44 dílů allowlistu neblokuje
+ evidováno 44× KNOWN_NON_WHEEL; allowlist mimo Wheels neplatí; chybějící
kolo (`missing_wheel`); duplicitní designace (`duplicate_designation`,
tier INVALID_WHEEL); špatný tvar kola (`bad_shape` → INVALID_WHEEL);
pátý Ball Spare (`bad_designation` → UNKNOWN_CANDIDATE); hierarchie
(`parent_cycle` → BLOCKED); determinismus detect+writer; writer GEOMETRY_OK
se Studio čísly; prohození stran/náprav (`side_or_axle_swap`); asymetrie
průměru (`diameter_asymmetry`) a výšek (`height_asymmetry`); neověřený
rámec → UNKNOWN; chybějící geometrie → UNKNOWN (`missing_position`);
`report_from_assess` s 44 díly → BLOCKED (I-1 propagace assess BLOCKED,
per-kolo detaily 4× GEOMETRY_OK) + 44 evidováno, Spare vedle
allowlistu stále BLOCKED.

## 7. Shrnutí (§16)

- **Hotovo:** 4-tier klasifikace (VALID_WHEEL / KNOWN_NON_WHEEL +
  allowlist 11 názvů / UNKNOWN_CANDIDATE / INVALID_WHEEL); identifikace
  4 kol (Ball 2.7³, id 3/52/101/150) potvrzena parser↔Studio; 44 dílů
  podvozku ověřeno na reálné kopii (`dc8747e0…fefdf`, hash před/po
  shodný, read-only) → NEBLOKUJE, evidováno; writer kontraktu +
  `known_non_wheels` nadstavba; 53/53 testů v modulu, 110/110 s parserem.
- **Rozpor zdokumentován:** konvence X=vpřed/Y=vlevo/Z=vzhůru neplatí;
  platí x=lateral / y=up / z=longitudinal (důkaz v §2–3, test v §6).
- **BLOCKED drží kde má:** UNKNOWN_CANDIDATE / INVALID_WHEEL ve Wheels,
  hierarchie, swapy, asymetrie; KNOWN_NON_WHEEL je jediná neblokující
  výjimka (model-specificky, jen uvnitř Wheels).
- **Nevyřízeno (mimo vlastnictví):** `float_decode_unverified` v assess
  (vlastník `rbxm_parser.py`); `scale_calibration.json` (Agent C);
  práh M3 brány. Cizí test `test_four_wheels_honest_partial`
  (`test_m2_rbxm_parser.py`) aktualizován na novou sémantiku (nutná
  změna: starý assertoval BLOCKED na reálné kopii) — ke kontrole
  vlastníkem.
- **Neznámé:** nic nového; všechny numerické výroky kryty během (§2).
- **Rizika:** allowlist je model-specifický (A-Chassis 6C) — na jiném
  vozidle by 44 dílů padlo do UNKNOWN_CANDIDATE → BLOCKED (bezpečný
  směr); rozšíření allowlistu je věc M3 s vlastníkem parseru.
- **Další krok:** M3 kalibrace (Agent C) → vymazání
  `float_decode_unverified`; práh brány ponechán.

## 8. Read-only audit klasifikace (Agent A, 2026-11-19, HEAD `c1a138b`, strom čistý)

Rozsah: `src/Inspection/wheel_detect.py` + `tests/test_m2_wheel_detect.py` +
tento report. Kód ani testy se neměnily (pouze append této sekce).

- **4 tiery:** `classify_candidate` vrací `VALID_WHEEL / KNOWN_NON_WHEEL /
  UNKNOWN_CANDIDATE / INVALID_WHEEL` — pravdivostní tabulka kryta testem
  `test_classify_four_tiers`. OK.
- **Allowlist:** `CHASSIS_PART_ALLOWLIST` má přesně **11** názvů
  (`CLower/CUpper/Hub/LowerArm/LowerArmB/LowerArmF/SpringBottom/
  SpringTop/UpperArm/UpperArmB/UpperArmF`); `KNOWN_NON_WHEEL` platí **jen
  uvnitř Wheels** (`Hub` mimo Wheels → `UNKNOWN_CANDIDATE`, test_04). OK.
- **44 dílů neblokuje:** syntetický model 11×4 → `blocked=false`,
  44× `KNOWN_NON_WHEEL`, 0 unidentified (test_02); reálná kopie
  (815 instancí) → `detect_wheels`: **4 VALID_WHEEL + 44 KNOWN_NON_WHEEL +
  0 unidentified, `blocked=false`**. OK.
- **BLOCKED drží:** chybějící `Model:Wheels` / 3 kola (`!= 4`) /
  duplicita designace / `bad_shape` → `INVALID_WHEEL` / `Spare` Ball →
  `UNKNOWN_CANDIDATE` / prohození stran i náprav (`side_or_axle_swap`) /
  `diameter_asymmetry` / `height_asymmetry` (`Y+0.5`) / cyklus
  (`parent_cycle`) / chybějící parent / duplicitní id / les / duplicitní
  `Model:Wheels` — vše `blocked=true`, kryto testy. Ball mimo Wheels se
  kolem nikdy nestane (`INVALID_WHEEL`, neblokuje). OK.
- **Reálná kopie:** `assets/chassis-original/chasis-work-copy.rbxm`,
  SHA-256 `dc8747e016e1…fefdf` — hash před/po shodný (read-only);
  `assess_wheel_geometry` → `blocked=true`
  (`float_decode_unverified`), per-kolo detaily 4× GEOMETRY_OK. OK.
- **Testy:** `python -m unittest tests.test_m2_wheel_detect` → **53/53
  OK**; s parserem `tests.test_m2_wheel_detect
  tests.test_m2_rbxm_parser` → **110/110 OK**.
- **Nálezy (report zastaralý, kód/testy správně):**
  1. §4 věta "`report_from_assess` … → `overall_status = GEOMETRY_OK`"
  je nepravdivá — I-1 propagace `assess BLOCKED` dává **BLOCKED**
  (kód `build_inspection_report` + test_18/`test_report_from_assess…`
  to vyžadují; popis testů v §6 BLOCKED jinde uvádí správně).
  2. §6 "109 testů" nesouhlasí — aktuálně **110** (53 + 57;
  parser-suite má 57, ne 56). Doporučeno opravit obě věty vlastníkem
  reportu (Agent B).
