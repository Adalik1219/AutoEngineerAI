# Agent E — Mustang data audit + konzistence PROPOSED schémat (AUDIT, žádné schválení)

**Větev:** `feat/m2-m3-geometry` · **HEAD:** `557ee39` (ověřen, strom čistý) · **Datum:** 2026-11-20
**Pravidla:** česky; identifikátory anglicky. M3 CLOSED, main/PR#2 tabu. RBXM jen čteno (výpis adresáře),
Simulator READ-ONLY (nespuštěn, nebyl potřeba). Schémata v `contracts/proposed/` NEMĚNĚNA, zůstávají PROPOSED.
`contracts/`, `tools/validate_contracts.py`, kód, katalog — nedotčeny. Zapsán pouze tento soubor.

**Čteno:** `vehicle-data/references/ford-mustang-gt-2024-eu-manual-standard.json` (celý profil, strojově),
`docs/VEHICLE-SPECIFICATIONS.md`, `contracts/proposed/*.schema.json` (4 návrhy, celé znění),
`reports/NIGHT-WORK/AGENT-F-MUSTANG-PHYSICS-MAPPING.md` (celé), `reports/NIGHT-WORK/AGENT-E-M2-CONTRACTS.md` (celé),
producenti `src/Inspection/wheel_detect.py` (`build_inspection_report`, ř. 472–760) a
`src/Inspection/scale_calibration.py` (`calibrate`, `default_references`, `usable_for_m3`, `require_verified_for_m3`).

**Zdroje zkráceně:** [1] Ford EU tech specs PDF · [1b] Ford EU tech specs mirror (fromtheroad.ford.com) ·
[2] Ford "Icon Reborn" článek · [3] ADAC Autokatalog (Mustang GT Fastback 5.0 V8 manuál).
Všechny ověřeny 2026-11-19 (M1.5). Katalogy ≠ měření: níže je `factory` vždy katalogový údaj výrobce,
nikoli měření konkrétního vozu.

---

## 1. Ověření klíčových hodnot Mustangu (katalog ≠ měření)

| # | Parametr | Hodnota v profilu | Status auditu | Zdroj | Komentář |
|---|---|---|---|---|---|
| 1 | Rozvor | 2719 mm | VERIFIED | [1b] + [3] (Radstand 2719), conf 0.9 | Sloupec Mustang GT, ne Dark Horse. Katalog, ne měření RBXM. |
| 2 | Rozchod F / R | 1585 / 1642 mm | VERIFIED | [1b], conf 0.9 | Dark Horse 1595/1643 — nezaměnit. Katalog. |
| 3 | Pneu F / R | 255/40 R19 / 275/40 R19 Y (summer-only) | VERIFIED | [1b] + [3], conf 0.9 | Designace ano; průměry 686.6 / 702.6 mm jsou VÝPOČET (ESTIMATED, ±5 mm). |
| 4 | Výkon | 328 kW (446 PS) @ 7250 rpm | VERIFIED | [1b] + [3], conf 0.9 | V PDF jen PS; kW = 446×0.7355. Katalog. Převod do `Horsepower` (kit) NEDEFINOVÁN — nepřepisovat. |
| 5 | Moment | 540 Nm @ 5100 rpm | VERIFIED | [1b] + [2]/[3], conf 0.9 | Bez rozporu s výkonem (540 Nm @ 5100 = 288.4 kW < 328 kW; moment při 7250 ≈ 432 Nm). Nemá Tune protějšek. |
| 6 | Převodovka + poměry | 6MT Getrag MT-82, 3.237 / 2.104 / 1.422 / 1.000 / 0.814 / 0.622 | VERIFIED | [1]/[1b], conf 0.9 | Zpátečka v [1b] NENÍ → UNKNOWN (ne 3.28 z kitu). Kit `Ratios` list≠dict — strukturální konverze, ne 1:1. |
| 7 | Stálý převod | null | UNKNOWN | [1b] uvádí 3.15:1 i 3.55:1 bez přiřazení k EU 6MT | Oba kandidáti, žádný výběr. GUARD platí: null nesmí do M3/M4 jako definitiva. |
| 8 | Hmotnost | 1808 kg | ESTIMATED | [1b] "Est. kerbweight" + [3] 1808 kg, conf 0.5 | Ford sám uvádí "Est." (řidič 75 kg, plné kapaliny, 90 % paliva). Ponecháno ESTIMATED — správně. |
| 9 | Rozložení hmotnosti | null | UNKNOWN | továrně nepublikováno | Postup: nápravové váhy / dílenský manuál S650. Nic nedopočítávat. |
| 10 | Brzdy | 390×36 / 355×28 mm ventilované, Brembo 6-píst / 4-píst | VERIFIED | [1]/[1b], conf 0.9 | EU factory standard (Pack je standardem EU GT). Bias účinku UNKNOWN. `BrakeForce` (kit škála) ≠ Nm — rovnítko zakázáno. |

**Dodatky k §1:** výška 1404 mm = střed rozpětí [1b] 1394–1414, [3] potvrzuje 1404 → VERIFIED s poznámkou (ne bodové měření);
délka 4810 / šířka 1916 / se zrcátky 2080 → VERIFIED; 0–100 5.3 s a V-max 250 km/h → VERIFIED, ale **validační cíle, ne vstupy**
(správně odděleno); vrtání 93.0 / zdvih 92.7 / objem 5038 cm³ → VERIFIED; LSD potvrzeno obecně ("Front-engine, RWD with LSD"),
přesný typ UNKNOWN (Torsen = Dark Horse, do EU profilu nepatří); kola 19×9.0J / 19×9.5J → VERIFIED (INFO pro mapping, bez Tune protějšku).

---

## 2. Kompletní tabulka parametrů

Legenda: `M3` = nutnost pro milník M3 (cílová geometrie) · `MAP` = nutnost pro mapping (Agent F / Agent D wiring).
`KRIT` = kritické · `POTŘ` = potřebné · `NEPOTŘ` = nepotřebné · `INFO` = jen informace bez protějšku.

### 2.1 Geometry (cíle M3 — vše studs až po kalibraci)

| ID | Název | Hodnota (SI ref) | Jedn. | Status | Zdroj | Poznámka | M3 | MAP |
|---|---|---|---|---|---|---|---|---|
| G-01 | wheelbase | 2719 | mm | VERIFIED | [1b]+[3] | GT sloupec | KRIT | KRIT |
| G-02 | track_front | 1585 | mm | VERIFIED | [1b] | GT, ne Dark Horse | KRIT | KRIT |
| G-03 | track_rear | 1642 | mm | VERIFIED | [1b] | dtto | KRIT | KRIT |
| G-04 | length | 4810 | mm | VERIFIED | [1b]+[3] | validační obálka | POTŘ | POTŘ |
| G-05 | width_excl_mirrors | 1916 | mm | VERIFIED | [1b]+[3] | dtto | POTŘ | POTŘ |
| G-06 | height | 1404 | mm | VERIFIED | [1b] rozpětí + [3] bod | střed rozpětí, ne bodové měření | POTŘ | POTŘ |
| G-07 | width_incl_mirrors | 2080 | mm | VERIFIED | [1b]+[3] | | NEPOTŘ | NEPOTŘ |
| G-08 | tire_diameter_front | 686.6 | mm | ESTIMATED | výpočet z 255/40 R19 | nominální, nezatížený, ±5 mm | KRIT | KRIT |
| G-09 | tire_diameter_rear | 702.6 | mm | ESTIMATED | výpočet z 275/40 R19 | staggered F≠R povinně | KRIT | KRIT |

### 2.2 Wheels & Tires

| ID | Název | Hodnota | Jedn. | Status | Zdroj | Poznámka | M3 | MAP |
|---|---|---|---|---|---|---|---|---|
| W-01 | tire_front_designation | 255/40 R19 Y | — | VERIFIED | [1b]+[3] | summer-only | POTŘ | POTŘ |
| W-02 | tire_rear_designation | 275/40 R19 Y | — | VERIFIED | [1b]+[3] | summer-only | POTŘ | POTŘ |
| W-03 | wheel_front | 19×9.0J | in | VERIFIED | [1]/[1b] | INFO — bez Tune protějšku | NEPOTŘ | INFO |
| W-04 | wheel_rear | 19×9.5J | in | VERIFIED | [1]/[1b] | INFO — dtto | NEPOTŘ | INFO |
| W-05 | rim_diameter | 19 | in | VERIFIED | [1b]+[3] | | NEPOTŘ | POTŘ |
| W-06 | wheel_inertia_F/R | null | kg·m² | UNKNOWN | neměřeno | moment setrvačnosti kol na stolici | NEPOTŘ | POTŘ |
| W-07 | target_friction | null | — | UNKNOWN | kit 0.7 = konstanta, ne cíl | skidpad / brzdný test letní pneu; SCRIPT_CONTROLLED | NEPOTŘ | KRIT |
| W-08 | camber_caster_toe | null | ° | UNKNOWN | geometrie S650 nepublikována | skript/díly, ne Tune | NEPOTŘ | POTŘ |

### 2.3 Suspension (vše PENDING na Studio-odečet; bez něj mimo zápis)

| ID | Název | Hodnota | Jedn. | Status | Zdroj | Poznámka | M3 | MAP |
|---|---|---|---|---|---|---|---|---|
| S-01 | spring_stiffness_F | null | N/m | UNKNOWN | kandidát 20000 = neověřený předpoklad | bezpečné pásmo 0.25–4× | NEPOTŘ | KRIT |
| S-02 | spring_stiffness_R | null | N/m | UNKNOWN | dtto | dtto | NEPOTŘ | KRIT |
| S-03 | damper_F | null | — | UNKNOWN | kandidát 500 = neověřený předpoklad | Bump/rebound test | NEPOTŘ | KRIT |
| S-04 | damper_R | null | — | UNKNOWN | dtto | dtto | NEPOTŘ | KRIT |
| S-05 | sus_length_F/R | null | — | UNKNOWN | Studio-odečet chybí | závislost Free = Length + PreCompress | NEPOTŘ | POTŘ |
| S-06 | pre_compress_F/R | null | — | UNKNOWN | dtto | | NEPOTŘ | POTŘ |
| S-07 | extension_lim_F/R | null | — | UNKNOWN | dtto | | NEPOTŘ | NEPOTŘ |
| S-08 | compress_lim_F/R | null | — | UNKNOWN | dtto | | NEPOTŘ | NEPOTŘ |
| S-09 | sus_angle_F/R | null | — | UNKNOWN | neaktivní větev (80) | nezapisovat bez potvrzení | NEPOTŘ | NEPOTŘ |
| S-10 | anchor_offset_F/R | null | — | UNKNOWN | potvrdit neaktivnost | | NEPOTŘ | NEPOTŘ |
| S-11 | wishbone_len_F/R | null | — | UNKNOWN | neaktivní (konflikt arm_kinematics) | | NEPOTŘ | NEPOTŘ |

### 2.4 Steering

| ID | Název | Hodnota | Jedn. | Status | Zdroj | Poznámka | M3 | MAP |
|---|---|---|---|---|---|---|---|---|
| R-01 | steer_ratio | null | — | UNKNOWN | rejstřík S650 nepublikován | s LockToLock dává SteerOuter 31.2° | NEPOTŘ | POTŘ |
| R-02 | lock_to_lock | null | ot. | UNKNOWN | dtto | | NEPOTŘ | POTŘ |
| R-03 | min_steer | null | % | UNKNOWN | jízdní test | parkování / V-max | NEPOTŘ | NEPOTŘ |
| R-04 | steer_speed / return_speed | null | °/tick | UNKNOWN | slalom / subjektivně | | NEPOTŘ | NEPOTŘ |
| R-05 | steer_decay | null | SPS | UNKNOWN | vysokorychlostní test | práh ≥ ~5 SPS | NEPOTŘ | POTŘ |
| R-06 | ackermann | null | — | UNKNOWN | geometrie přední nápravy S650 | | NEPOTŘ | POTŘ |
| R-07 | rear_steer_4WS | none | — | ESTIMATED | odvozeno z konstrukce (S650 nemá 4WS) | ponechat None | NEPOTŘ | NEPOTŘ |
| R-08 | steering_type | null | — | UNKNOWN | kit-vnitřní přepínač | Studio test obou větví | NEPOTŘ | POTŘ |
| R-09 | steer_axis_offset | null | — | UNKNOWN | klíč v live Tune CHYBÍ (`Initialize:171` ho čte) | chyba č. 1 — verdikt před prvním během | NEPOTŘ | KRIT |

### 2.5 Engine

| ID | Název | Hodnota | Jedn. | Status | Zdroj | Poznámka | M3 | MAP |
|---|---|---|---|---|---|---|---|---|
| E-01 | engine_code | 5.0 Ti-VCT V8 | — | VERIFIED | [1b] | atmosféra → turbo 0 / kompresor 0 | NEPOTŘ | KRIT |
| E-02 | displacement | 5038 | cm³ | VERIFIED | [1b]+[3] | | NEPOTŘ | INFO |
| E-03 | bore × stroke | 93.0 × 92.7 | mm | VERIFIED | [1b] | | NEPOTŘ | INFO |
| E-04 | max_power | 328 @ 7250 | kW @ rpm | VERIFIED | [1b]+[3] | ≠ `Horsepower` bez převodu; přepis zakázán | NEPOTŘ | KRIT |
| E-05 | max_torque | 540 @ 5100 | Nm @ rpm | VERIFIED | [1b]+[2]/[3] | bez Tune protějšku | NEPOTŘ | KRIT |
| E-06 | compression_ratio | null | :1 | UNKNOWN | není v zadání | uživatelská příručka / [1] | NEPOTŘ | NEPOTŘ |
| E-07 | fuel_min_octane | null | RON | UNKNOWN | dtto | dtto | NEPOTŘ | NEPOTŘ |
| E-08 | idle_rpm | null | rpm | UNKNOWN | OBD log / manuál S650 | | NEPOTŘ | NEPOTŘ |
| E-09 | redline_rpm | null | rpm | UNKNOWN | [1] / OBD log | omezovač vs 7250 maxima | NEPOTŘ | POTŘ |
| E-10 | torque_curve_points | [] | — | UNKNOWN | křivka nepublikována (M1.9) | nikdy nedomýšlet body | NEPOTŘ | KRIT |

### 2.6 Drivetrain & Transmission

| ID | Název | Hodnota | Jedn. | Status | Zdroj | Poznámka | M3 | MAP |
|---|---|---|---|---|---|---|---|---|
| D-01 | layout / driven_axle | front-engine, RWD | — | VERIFIED | [1b] | kit AWD → řízený krok s testem | NEPOTŘ | KRIT |
| D-02 | differential_rear | LSD (typ neurčen) | type | VERIFIED* | [1b] | *obecně; přesný typ UNKNOWN, Torsen zakázán | NEPOTŘ | KRIT |
| D-03 | torque_split_F/R | 0/100 | % | ESTIMATED | odvozeno z RWD | u RWD k revizi s drive_config | NEPOTŘ | POTŘ |
| D-04 | final_drive | null | :1 | UNKNOWN | kandidáti 3.15 / 3.55 bez přiřazení | konfigurátor Ford CZ/DE; konflikt s FDMult | NEPOTŘ | KRIT |
| D-05 | final_drive_mult | 1 (neutrál) | — | VERIFIED | audit kódu (F4.3/§6) | neměnit samostatně (Gauges) | NEPOTŘ | NEPOTŘ |
| T-01 | gearbox_type | 6MT Getrag MT-82, rev-matching | — | VERIFIED | [1]/[1b] | Manual-first; TransModes Manual-first | NEPOTŘ | KRIT |
| T-02 | gear_ratios_1–6 | 3.237/2.104/1.422/1.0/0.814/0.622 | :1 | VERIFIED | [1]/[1b] | list→dict konverze (Agent D) | NEPOTŘ | KRIT |
| T-03 | reverse_ratio | null | :1 | UNKNOWN | není v [1b] | [1] / konfigurátor | NEPOTŘ | POTŘ |
| T-04 | shift_up/down_time | null | s | UNKNOWN | manuál řadí řidič, DCT časy neaplikovatelné | ponechat kit / měřit MT-82 | NEPOTŘ | NEPOTŘ |
| T-05 | clutch_* | null | mix | UNKNOWN | rev-matching ≠ žádná kit-větev 1:1 | test rozjezdů | NEPOTŘ | POTŘ |
| D-06 | FDiff_power/coast/preload | n/a (RWD) | — | ESTIMATED | odvozeno z RWD | u RWD ignorováno, nemazat bez D | NEPOTŘ | NEPOTŘ |
| D-07 | RDiff_power/coast/preload, slip/lock_* | null | 0–100 | UNKNOWN | live-klíče potvrzeny (F4.3), hodnoty PENDING | Studio-odečet + test svornosti | NEPOTŘ | POTŘ |

### 2.7 Brakes

| ID | Název | Hodnota | Jedn. | Status | Zdroj | Poznámka | M3 | MAP |
|---|---|---|---|---|---|---|---|---|
| B-01 | front_disc | 390×36 vent., Brembo 6-píst | mm | VERIFIED | [1]/[1b] | INFO — `BrakeForce` ≠ Nm | NEPOTŘ | POTŘ |
| B-02 | rear_disc | 355×28 vent., 4-píst | mm | VERIFIED | [1]/[1b] | INFO — dtto | NEPOTŘ | POTŘ |
| B-03 | brake_bias_front | null | % / 0–1 | UNKNOWN | nepublikováno | brzdný test / manuál S650; extrémy 0/1 rizikové | NEPOTŘ | KRIT |
| B-04 | brake_force_scale | null | — | UNKNOWN | kit 2500 = škála přes FPS a režimy | brzdný test 100–0 + `#BV` vzorec | NEPOTŘ | KRIT |
| B-05 | pbrake_force / bias | null | — | UNKNOWN | test ruční brzdy (jen zadek) | | NEPOTŘ | NEPOTŘ |
| B-06 | TCS/ABS thresholds | null | SPS / % | UNKNOWN | test prokluzu / brzdný test | prahy ≥ ~5 SPS | NEPOTŘ | POTŘ |

### 2.8 Mass

| ID | Název | Hodnota | Jedn. | Status | Zdroj | Poznámka | M3 | MAP |
|---|---|---|---|---|---|---|---|---|
| M-01 | curb_weight | 1808 | kg | ESTIMATED | [1b] Est. + [3] | Ford "Est."; převod lb↔kg až v runtime (MAPPING §6) | NEPOTŘ | KRIT |
| M-02 | weight_distribution_F | null | % | UNKNOWN | továrně nepublikováno | nápravové váhy; bez údaje nelze přetáčivost | NEPOTŘ | KRIT |
| M-03 | cog_height | null | mm | UNKNOWN | dtto | naklápěcí zkouška / M4; pásmo CGHeight ≤ ~1.2 | NEPOTŘ | KRIT |
| M-04 | yaw_inertia | null | kg·m² | UNKNOWN | dopočet v M4 + kalibrace | obdélníková aproximace z geometrie | NEPOTŘ | POTŘ |
| M-05 | fuel_tank / GVW / payload / dry | null | l / kg | UNKNOWN | není v zadání | [1] v M1.5; dry definice nesjednocená | NEPOTŘ | NEPOTŘ |

### 2.9 Aero & Electronics

| ID | Název | Hodnota | Jedn. | Status | Zdroj | Poznámka | M3 | MAP |
|---|---|---|---|---|---|---|---|---|
| A-01 | drag_coefficient_Cd | null | — | UNKNOWN | není v zadání ani zdrojích | [1] / coast-down; NE z US dat; před V-max opravit `magnitude` bug | NEPOTŘ | KRIT |
| A-02 | frontal_area | null | m² | UNKNOWN | dtto | dopočet ze šířky × výšky po M1.5 | NEPOTŘ | POTŘ |
| A-03 | downforce_F/R | null | — | UNKNOWN | tunelová data neexistují | jen kódem; kalibrace V-max 250 jako cíl | NEPOTŘ | POTŘ |
| X-01 | electronics_ABS/TCS_logic | null | — | UNKNOWN | SCRIPT — až M4/M5 | | NEPOTŘ | POTŘ |

**Součty tabulky auditu (§2, 65 řádků, některé sdružují F/R páry): VERIFIED 27 · ESTIMATED 6 · UNKNOWN 32 · BLOCKED 0.**
(BLOCKED není stav dat — je to stav výstupu; žádný parametr není blokovaný, i `final_drive` je UNKNOWN s guardem, ne BLOCKED.)

---

## 3. Kontrola mapování 60 parametrů z minulé vlny (Agent F, položka po položce)

Deklarace F §1: 60 parametrů, 7 VERIFIED / 3 ESTIMATED / 50 UNKNOWN; rozpad §1: VERIFIED 7 · ESTIMATED 3 · PENDING 22 · UNKNOWN 28.
Strojový přepočet tabulek §2.1–§2.10 (78 řádků — sloučené skupiny jako `rev_accel/decay/bounce` a `slip/lock_*`):
**VERIFIED 6 · ESTIMATED 7 · PENDING 21 · UNKNOWN 44.** Deklarace tedy NESEDLÍ se stavovým sloupcem — rozbor níže.
(Kontrola věcná, ne formální: 78 řádků ≈ 60 logických parametrů po rozbalení sloučených skupin — rozsah pokrytí sedí.)

### 3.1 Položkový verdikt

- **§2.1 Hmotnost (4 řádky): SOUHLAS.** `weight_lb` ESTIMATED (Ford "Est." — správně ne VERIFIED), `weight_dist_pct` + `cg_height` UNKNOWN (správně, továrně nepublikováno), `weight_box_size` PENDING na geometrii modelu (správně — není to mustangovský údaj).
- **§2.2 Geometrie (2 řádky): SOUHLAS.** Rozvor/rozchody VERIFIED [1b] s varováním Dark Horse (správně); poloměry ESTIMATED výpočtem ±5 mm (správně, nejde o měření).
- **§2.3 Kola/pneu (4 řádky): SOUHLAS s výhradou.** Správně: disky/hustoty jako INFO bez cíle, friction UNKNOWN + SCRIPT_CONTROLLED, camber UNKNOWN. Výhrada: u `target_friction` není zmíněn kit-původ 0.7 jako konstanta skriptu — drobnost, viz F §2.3 (uvedeno v závorce u BrakeForce, zde jen "kit-konstanta" — dohledatelné).
- **§2.4 Podvozek (16 řádků): SOUHLAS.** Vše UNKNOWN/PENDING, kandidáti 20000/500 označeni jako neověřené předpoklady (správně — nikdy ESTIMATED bez metody). Neaktivní větve (sus_angle, wishbone) správně UNKNOWN + "nezapisovat".
- **§2.5 Řízení (10 řádků): SOUHLAS.** Vše UNKNOWN kromě `front_wheel_steer` ESTIMATED (konstrukčně dáno — přijatelné, metoda uvedena). `StAxisOffset` PENDING + chyba č. 1 — správně eskalováno.
- **§2.6 Brzdy (8 řádků): SOUHLAS.** Kotouče jako INFO bez rovnítka k `BrakeForce` (správně); bias UNKNOWN (správně); prahy ABS/TCS UNKNOWN (správně).
- **§2.7 Motor (14 řádků): SOUHLAS.** Klíčový guardrail držen: 328 kW ≠ `Horsepower`, 7250 ≠ `PeakRPM`, křivka `points: []` nikdy nedomýšlet. Turbo 0 / kompresor 0 VERIFIED z kódu motoru (správně). `compression_ratio` PENDING na Studio-odečet — sporné (kompresní poměr není Tune-hodnota ke čtení ze Studia, ale tovární údaj do [1]; mělo být UNKNOWN s postupem "PDF [1]", ne PENDING). Drobná vada klasifikace, bez dopadu.
- **§2.8 Převodovka (6 řádků): SOUHLAS.** Poměry 1–6 VERIFIED [1]/[1b]; final_drive UNKNOWN s guardem (správně); FDMult=1 VERIFIED auditem (správně, neutrál); TransModes Manual-first ESTIMATED (odvozeno z typu skříně — přijatelné, metoda uvedena).
- **§2.9 Diferenciál/pohon (13 řádků): SOUHLAS s výhradou.** `drive_config` RWD VERIFIED (správně); LSD obecně VERIFIED + typ UNKNOWN + zákaz Torsen (správně, T18). Výhrada: odvozené RWD ESTIMATED (`torque_vector`, `FDiff_*`, `diff_preload_f`) jsou legitimní odhady s metodou, ale §1 je nepočítá mezi "3 ESTIMATED" — viz §3.2.
- **§2.10 Aero/ostatní (5 řádků): SOUHLAS.** Cd/plocha UNKNOWN (správně, zákaz US dat); `magnitude` bug + `StAxisOffset` eskalovány před V-max kampaní (správně).

### 3.2 Neshody v počtech (nálezy, ne fatální)

- **N-F1 (počty stavů):** deklarováno VERIFIED 7 / ESTIMATED 3 / PENDING 22 / UNKNOWN 28; v tabulkách VERIFIED 6 / ESTIMATED 7 / PENDING 21 / UNKNOWN 44 (řádky). Příčina: dvojí účetnictví — §1 počítá *doloženost mustangovského cíle* (7 VERIFIED + 3 ESTIMATED = 10 cílů z §3: rozvor, rozchody, pneu, disky-INFO, výkon, moment, převody, RWD+LSD, turbo/kompresor 0, hmotnost-EST, kotouče-INFO…), zatímco sloupec Stav počítá *stav mapování* včetně odvozených RWD/manual ESTIMATED (trans_modes, torque_vector, FDiff_*, preload_f, FWSteer = 5 navíc; 3 cílové + 5 odvozených − překryvy = 7). Chybějící 7. VERIFIED v tabulce: pravděpodobně dvojí zápočet `drive_config` + `differential_rear-LSD-obecně` jako dvou VERIFIED v §1, zatímco tabulka má LSD-typ UNKNOWN. **Doporučení:** sjednotit definici (sloupec Stav = stav cíle; odvozené RWD odhady přesunout do ESTIMATED s metodou i v §1, nebo je vést jako PENDING). Mapping jako celek tím není zpochybněn.
- **N-F2 (`compression_ratio` PENDING):** viz §3.1/§2.7 — překlasifikovat na UNKNOWN s postupem "[1] PDF". Bez dopadu na M3.
- **N-F3 (PENDING 21 vs 22):** rozdíl 1 řádku (pravděpodobně `weight_box_size` počítána v §1 mezi PENDING, v tabulce ano — nesedí o 1; nepodstatné, k vyjasnění F).
- **Guards drží:** MAPPING §6 rovnítka zakázána (kW≠hp, Nm≠BrakeForce, list≠dict), lb→kg až runtime, `points: []`, Jeep data nepřevzata (ověřeno — v použitých zdrojích nejsou), Dark Horse záměna zakázána (T18, GT sloupce důsledně).

**Verdikt k mappingu:** věcně SPRÁVNÝ, klasifikace případů N-F1/N-F2 k narovnání. Žádný parametr není vydáván za ověřený bez zdroje; žádný UNKNOWN není tiše doplněn.

---

## 4. Konzistence 4 PROPOSED schémat vs skuteční producenti

Společné: všechna 4 schémata používají POUZE podmnožinu enginu (`const/enum/required/pattern/anyOf/$ref`, top-level `type: array` u diff)
— ověřeno četbou schémat proti popisu enginu v AGENT-E-M2-CONTRACTS §1 (sondy 4/4 PASS + 8/8 REJECTED + 3/3 producenti viz §5 tamtéž;
sondy jsem neopakoval — producenti se od minula nezměnili, viz níže). Stavy sjednoceny na existující slovníky
(GEOMETRY_OK|UNKNOWN|BLOCKED; VERIFIED|ESTIMATED|UNKNOWN|BLOCKED), PASS zakázán — SOUHLAS, žádný druhý systém stavů.

### 4.1 `inspection_report.schema.json` — APPROVE WITH CHANGES

- **Producent** `build_inspection_report` (wheel_detect.py:472): emituje `report_id` (default `vehicle_id@sha256[:12]` — odpovídá popisu),
  `vehicle_id`, `source_file`, `source_sha256`, kola FL/FR/RL/RR se statusy, `axles.front/rear` + `wheelbase_studs` + `tire_diameters_studs`
  (kód: `wheelbase` průměr párů, `diameters` — přítomny), `coordinate_frame` vč. `verified_in_studio` se stropem UNKNOWN (C-IR4 logika v kódu),
  `method`, `warnings`, `overall_status` (BLOCKED > UNKNOWN > GEOMETRY_OK; missing_wheel → BLOCKED, ne tichý UNKNOWN — odpovídá C-IR5 duchu).
  `schema_version` neemituje → volitelné `const 1.0.0` ve schématu je SPRÁVNÁ volba (striktní required by lámalo producenta). Q-1: doporučuji ponechat volitelné.
- **Nálezy:** (a) `known_non_wheels.items.additionalProperties: true` — jediná díra ve schématu (jinak všude `false`); doporučuji `false` + explicitní pole, nebo zdůvodnit. (b) `warnings` bez `minItems` — C-IR1 (`BLOCKED ⇒ warnings non-empty`) nekontrolovatelné schématem → povinná kódová kontrola před schválením. (c) `reason: [string, null]` bez `minLength` — prázdný důvod projde; konzistence per-kolo vs overall (C-IR2/3) jen kódem. (d) Per-kolo `status` nemá variantu pro "neidentifikováno" — kód to řeší `missing_wheel` + BLOCKED (odpovídá schématu, OK).
- **Verdikt: APPROVE WITH CHANGES** — podmínky: (1) utěsnit `known_non_wheels` (a); (2) kódové kontroly C-IR1–C-IR5 z AGENT-E-M2-CONTRACTS §4 před schválením; (3) Q-1 rozhodnout "volitelné" (doporučení: ANO ponechat).

### 4.2 `scale_calibration.schema.json` — APPROVE WITH CHANGES

- **Producent** `calibrate` (scale_calibration.py:194): emituje přesně klíče schématu (`vehicle_id`, `inspection_ref`, `references[]`
  `{param,value_si,unit:m,source,status}`, `measurements_studs`, `estimates[]`, `deviations_pct`, `uncertainty{combined,rel_pct,method}`,
  `overall_status`, `blocked_reason`). `schema_version` neemituje → volitelné SPRÁVNĚ. Defaultní reference: wheelbase/track_f/track_r VERIFIED
  (u_si 0.003), tire_d_f/r ESTIMATED (u_si 0.005) — schéma `status: enum [VERIFIED, ESTIMATED, UNKNOWN]` bez BLOCKED je SPRÁVNĚ
  (reference se neblokuje; blokuje se výsledek). Brány v kódu: <2 rodiny → BLOCKED; rozptyl → BLOCKED; VERIFIED jen vše-VERIFIED + odchylka ≤2 %;
  `usable_for_m3`/`require_verified_for_m3` = M3 brána — schéma tomu nebrání (správně, brána je kód).
- **Nálezy:** (a) `inspection_ref: [string, null]` bez `pattern` — popis slibuje "report_id nebo sha256:hex", schéma nekontroluje tvar; doporučuji `pattern` nebo rozpad na `{report_id, source_sha256}`. (b) `blocked_reason: [string, null]` bez `minLength` — C-CAL krytí jen kódem; doporučuji `minLength: 1` při BLOCKED → nelze schématem podmíněně, takže k
...[truncated 6154 chars]