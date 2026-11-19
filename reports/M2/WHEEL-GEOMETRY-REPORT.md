# M2 WHEEL-GEOMETRY-REPORT (Agent B — Wheel & Geometry)

Větev `feat/m2-m3-geometry` (HEAD `ab840a9`), zpráva ke kontraktu
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

## 4. 44 dílů podvozku ve Wheels — BLOCKED drží

`Model:Wheels` (id 2) obsahuje **48** Partů: 4 kola (Ball FL/FR/RL/RR) +
**44 dílů podvozku** (`SpringBottom/CLower/CUpper/SpringTop/LowerArmB/
LowerArmF/Hub/LowerArm/UpperArmF/UpperArmB/UpperArm` × 4, shape None).
Pravidlo identity (a)+(b)+(c) je legitimně neklasifikuje jako kola →
UNKNOWN uvnitř Wheels → **BLOCKED drží** (ověřeno end-to-end:
`assess` 4× GEOMETRY_OK, ale `blocked = [UNKNOWN…44,
float_decode_unverified]`; `report_from_assess` → `overall BLOCKED`,
geometrie 4 kol přitom číselně souhlasí s §2).

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

## 6. Testy — 34/34 OK

`python3 -m unittest tests.test_m2_wheel_detect` → **34 testů, OK**
(21 původních pravidel identity beze změny + 13 nových):
4 kola se Studio čísly, chybějící kolo, pátý Ball (Spare),
duplicitní designace, záměna stran, záměna náprav, asymetrie průměru,
asymetrie výšek, neověřený rámec → UNKNOWN, chybějící geometrie →
UNKNOWN, determinismus + JSON round-trip, `report_from_assess` s 44 díly
podvozku → BLOCKED.

## 7. Shrnutí (§16)

- **Hotovo:** identifikace 4 kol (Ball 2.7³, id 3/52/101/150) potvrzena
  parser↔Studio; writer kontraktu implementován; 13 testů přidáno, 34/34 OK.
- **Rozpor zdokumentován:** konvence X=vpřed/Y=vlevo/Z=vzhůru neplatí;
  platí x=lateral / y=up / z=longitudinal (důkaz v §2–3, test v §6).
- **BLOCKED drží:** 44 dílů podvozku ve Wheels = legitimní podvozek,
  ne kola; plná data → report BLOCKED s číselně správnou geometrií.
- **Nevyřízeno (mimo vlastnictví):** vymazání `float_decode_unverified`
  po M3 kalibraci (vlastník `rbxm_parser.py`); `scale_calibration.json`
  (Agent C); práh M3 brány.
