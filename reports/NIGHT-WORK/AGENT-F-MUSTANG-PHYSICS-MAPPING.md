# Agent F — Mapování fyziky Mustang GT 2024 EU (MAPA, ne implementace)

**Větev:** `feat/m2-m3-geometry` · **SHA:** `90a1f63c` (ověřen, strom čistý) · **Datum:** 2026-11-20
**Pravidla:** česky; identifikátory anglicky. Čteno: `docs/A-CHASSIS-PARAMETER-CATALOG.md`,
`docs/MAPPING.md`, `src/Chassis/catalog/parameters.json` (138 záznamů),
`src/Chassis/mapping/dependencies.py`, `src/Chassis/mapping/cycle_check.py`,
`vehicle-data/references/ford-mustang-gt-2024-eu-manual-standard.json`,
`docs/VEHICLE-SPECIFICATIONS.md`. **Zapsán pouze tento soubor.** Žádný kód, katalog,
testy ani produkční konfigurace A-Chassis měněny. M3 ZAVŘENÁ, main/PR#2 tabu —
žádný návrh změn kódu, jen mapa. RBXM nečten (mimo potřebu). **Jeep data neexistují
v použitých zdrojích a nic z nich není převzato.** Chybějící Mustang hodnota =
`UNKNOWN`, nikdy odhad vydávaný za fakt.

**Zdroj pravdy pro Mustang cíle:** výhradně referenční profil
`vehicle-data/references/ford-mustang-gt-2024-eu-manual-standard.json`
(M1.5, zdroje [1]/[1b] Ford EU tech specs + [3] ADAC, ověřeno 2026-11-19).
Původ každé hodnoty označen: `oficiální zdroj` / `měření` / `odhad` / `výpočet` /
`neověřený předpoklad`.

## 0. Brána S-02 (cykly blokují automatické mapování)

- `check_known_tables()` nad `KNOWN_DEPENDS`/`KNOWN_CONFLICTS`: **0 cyklů** (ověřeno během práce).
- Důsledek: automatické mapování (`map_config`) je přípustné **pouze** pro acyklické
  `MUTABLE_TUNE` + `PASS`; cokoli v cyklu (kdyby vznikl) → stav `BLOCKED`, pouze ruční
  převod s odůvodněním. V této mapě není žádný parametr `BLOCKED` z titulu cyklu —
  `BLOCKED` níže znamená vždy strukturní/skriptovou bariéru + případný cyklus by ji
  jen potvrdil.
- Známé konflikty respektovány: `FinalDrive × FDMult` (multiplikativní nejednoznačnost),
  `rear_diff_* × differential_type`, `turbo_boost × turbo_count`, délky pružin navzájem
  (`FreeLength = SusLength + PreCompress`, `Max = +ExtensionLim`, `Min = −CompressLim`).

## 1. Souhrn čísel

- **Mapovaných parametrů: 60** (jízdně relevantní výběr ze 138 záznamů katalogu;
  elektro-větev 9× a čistě vizuální/zvukové parametry mimo jízdu vynechány, viz §4).
- **S doloženým Mustang cílem: 10** (z toho 7 `VERIFIED` oficiálním zdrojem,
  3 `ESTIMATED` — odhad/výpočet s uvedeným postupem).
- **`UNKNOWN` (bez doloženého cíle): 50.**
- Rozpad stavů v mapě: `VERIFIED` 7 · `ESTIMATED` 3 · `PENDING` 21 (čeká na ověření; řádek `compression_ratio` překlasifikován na UNKNOWN) ·
  `UNKNOWN` 28 (stavové součty 7/3/21/28 nejsou doloženy, protože tabulky slučují ID; viz audit N-F1).

## 2. Mapovací tabulka

Legenda: `Kit` = současná hodnota v katalogu/A-Chassis (původ: audit/kód).
`Mustang` = cíl POUZE z referenčního profilu, jinak `UNKNOWN`. `Důležitost`:
geometrie / dynamika / ovládání / vizuální / podpůrný / neznámý.

### 2.1 Hmotnost a rozložení

| Interní ID | Název | Kit | Jedn. | Mustang cíl | Zdroj cíle | Stav | Původ cíle | Ověření | Riziko změny | Důležitost |
|---|---|---|---|---|---|---|---|---|---|---|
| `weight_lb` | Weight | 3439 | lb | 1808 kg | profil `mass.curb_weight` ([1b]+[3]) | ESTIMATED | odhad (Ford sám uvádí "Est.") | převážení vozu / TP | VYSOKÉ — kit ~1560 kg vs 1808 kg; převod lb↔kg řeší až adaptér/runtime, nikdy úložiště (MAPPING §6) | dynamika |
| `weight_dist_pct` | WeightDist | 55 | % | UNKNOWN | — (profil: `CHYBÍ`, továrně nepublikováno) | UNKNOWN | — | nápravové váhy / dílenský manuál S650 | VYSOKÉ — bez údaje nelze kalibrovat přetáčivost/nedotáčivost | dynamika |
| `cg_height` | CGHeight | 0.8 | — | UNKNOWN | — (profil: `CHYBÍ`) | UNKNOWN | — | naklápěcí zkouška / kalibrace modelem v M4 | VYSOKÉ — bezpečné pásmo `CGHeight ≤ ~1.2`; špatná výška = převracení/kmitání | dynamika |
| `weight_box_size` | WeightBSize | [7.03, 5.35, 18.11] | studs | UNKNOWN | — (odvozeno od geometrie modelu, ne od Mustangu) | PENDING | měření | STŘEDNÍ — váhový kvádr musí odpovídat karoserii 4810×1916 mm | geometrie |

### 2.2 Geometrie podvozku (STRUCTURE — parametrem nelze, jen přestavbou)

| Interní ID | Název | Kit | Jedn. | Mustang cíl | Zdroj cíle | Stav | Původ cíle | Ověření | Riziko změny | Důležitost |
|---|---|---|---|---|---|---|---|---|---|---|
| `wheelbase_etc` | (rozvor/rozchod/ride-height) | null | — | rozvor 2719; rozchod F 1585 / R 1642 mm | profil `dimensions.*` ([1b], sl. Mustang GT — nezaměnit Dark Horse) | VERIFIED | oficiální zdroj | RBXM odečet `Position` FL–RL / FL–FR + `vehicle-data/analyzed/` | VYSOKÉ — geometrie se ladí díly, ne Tune; špatný rozvor = špatná stabilita | geometrie |
| `wheel_radius` | (poloměr kol) | null | — | F 686.6 / R 702.6 mm (nominální, nezatížené) | výpočet z designace 255/40 R19, 275/40 R19 (VEHICLE-SPEC §2) | ESTIMATED | výpočet (±5 mm dezén) | RBXM odečet `Size` kol | VYSOKÉ — poloměr = páka všech sil; F≠R průměr (staggered) nutno promítnout | geometrie |

### 2.3 Kola a pneumatiky

| Interní ID | Název | Kit | Jedn. | Mustang cíl | Zdroj cíle | Stav | Původ cíle | Ověření | Riziko změny | Důležitost |
|---|---|---|---|---|---|---|---|---|---|---|
| `front_wheel_density` | FWheelDensity | 0.1 | — | UNKNOWN (disk 19×9.0J + 255/40 R19 doloženy, ale hustota je kit-vnitřní škálování, ne fyzikální údaj) | profil `wheels_tires.*` ([1b]) — INFO, ne cíl | UNKNOWN | — | moment setrvačnosti kol na stolici / kalibrace | STŘEDNÍ — jediný Tune parametr kol; adheze se ladí skriptem | dynamika |
| `rear_wheel_density` | RWheelDensity | 0.1 | — | UNKNOWN (disk 19×9.5J + 275/40 R19 doloženy, viz výše) | profil `wheels_tires.*` ([1b]) — INFO | UNKNOWN | — | viz výše | STŘEDNÍ | dynamika |
| `target_friction` | (F/RTargetFriction) | 0.7 + Heat (min 0.1) | — | UNKNOWN (grip 1.0 v configu je Optimizer-předpoklad bez Tune protějšku) | — | UNKNOWN | neověřený předpoklad (0.7 je kit-konstanta) | skidpad / brzdný test letní pneu | VYSOKÉ — SCRIPT_CONTROLLED (`Simulated`, mimo Tune); změna jen kódem | dynamika |
| `camber_caster_toe` | (odklon/záklon/sbíhavost) | 0° vše | ° | UNKNOWN | — | UNKNOWN | — | geometrie náprav S650 (dílenský manuál) | STŘEDNÍ — SCRIPT/díly, ne Tune | geometrie |

### 2.4 Odpružení a tlumiče

| Interní ID | Název | Kit | Jedn. | Mustang cíl | Zdroj cíle | Stav | Původ cíle | Ověření | Riziko změny | Důležitost |
|---|---|---|---|---|---|---|---|---|---|---|
| `sus_stiffness_f` | FSusStiffness | null (kandidát 20000) | N/m | UNKNOWN | — | PENDING | neověřený předpoklad (kandidátní dekód) | Studio odečet `FSusStiffness` + statický prohyb vozu | VYSOKÉ — bez Studio-verifikace float-lane mimo prostor; bezpečné pásmo 0.25–4× | dynamika |
| `sus_stiffness_r` | RSusStiffness | null (kandidát 20000) | N/m | UNKNOWN | — | PENDING | neověřený předpoklad | viz výše | VYSOKÉ | dynamika |
| `damper_f` | FSusDamping | null (kandidát 500) | — | UNKNOWN | — | PENDING | neověřený předpoklad | Studio odečet + Bump/rebound test | VYSOKÉ | dynamika |
| `damper_r` | RSusDamping | null (kandidát 500) | — | UNKNOWN | — | PENDING | neověřený předpoklad | viz výše | VYSOKÉ | dynamika |
| `sus_length_f` | FSusLength | null | — | UNKNOWN | — | PENDING | — | Studio odečet (audit zná jen odvozené Free/Max/Min) | STŘEDNÍ — závislost `FreeLength = SusLength + PreCompress` | dynamika |
| `sus_length_r` | RSusLength | null | — | UNKNOWN | — | PENDING | — | viz výše | STŘEDNÍ | dynamika |
| `pre_compress_f` | FPreCompress | null | — | UNKNOWN | — | PENDING | — | Studio odečet | STŘEDNÍ | dynamika |
| `pre_compress_r` | RPreCompress | null | — | UNKNOWN | — | PENDING | — | Studio odečet | STŘEDNÍ | dynamika |
| `extension_lim_f` | FExtensionLim | null | — | UNKNOWN | — | PENDING | — | Studio odečet | NÍZKÉ | podpůrný |
| `extension_lim_r` | RExtensionLim | null | — | UNKNOWN | — | PENDING | — | Studio odečet | NÍZKÉ | podpůrný |
| `compress_lim_f` | FCompressLim | null | — | UNKNOWN | — | PENDING | — | Studio odečet | NÍZKÉ | podpůrný |
| `compress_lim_r` | RCompressLim | null | — | UNKNOWN | — | PENDING | — | Studio odečet | NÍZKÉ | podpůrný |
| `sus_angle_f` | FSusAngle | null (80 = neaktivní větev) | — | UNKNOWN | — | UNKNOWN | — | potvrdit neaktivnost procedurální větve (custom `SuspensionGeometry` přebíjí) | NÍZKÉ — neaktivní, nezapisovat | neznámý |
| `sus_angle_r` | RSusAngle | null (dtto) | — | UNKNOWN | — | UNKNOWN | — | viz výše | NÍZKÉ | neznámý |
| `anchor_offset_f` | FAnchorOffset | null | — | UNKNOWN | — | PENDING | — | Studio: potvrdit neaktivnost | NÍZKÉ | neznámý |
| `anchor_offset_r` | RAnchorOffset | null | — | UNKNOWN | — | PENDING | — | viz výše | NÍZKÉ | neznámý |
| `front_wishbone_len` | FWsBoneLen | null (4 = neaktivní) | — | UNKNOWN | — | UNKNOWN | — | viz výše + konflikt `arm_kinematics` | NÍZKÉ — neaktivní | neznámý |
| `rear_wishbone_len` | RWsBoneLen | null | — | UNKNOWN | — | UNKNOWN | — | viz výše | NÍZKÉ | neznámý |

### 2.5 Řízení

| Interní ID | Název | Kit | Jedn. | Mustang cíl | Zdroj cíle | Stav | Původ cíle | Ověření | Riziko změny | Důležitost |
|---|---|---|---|---|---|---|---|---|---|---|
| `steer_ratio` | SteerRatio | 15 | — | UNKNOWN | — | UNKNOWN | — | rejstřík řízení S650 (dílenský manuál) | STŘEDNÍ — s `LockToLock` dává `SteerOuter` 31.2°, nelze mapovat 1:1 | ovládání |
| `lock_to_lock` | LockToLock | 2.6 | otáčky | UNKNOWN | — | UNKNOWN | — | viz výše | STŘEDNÍ | ovládání |
| `min_steer` | MinSteer | 10 | % | UNKNOWN | — | UNKNOWN | — | jízdní test (parkování / V-max stabilita) | NÍZKÉ | ovládání |
| `steer_speed` | SteerSpeed | 0.05 | °/tick | UNKNOWN | — | UNKNOWN | — | subjektivní + slalom | NÍZKÉ | ovládání |
| `return_speed` | ReturnSpeed | 0.1 | °/tick | UNKNOWN | — | UNKNOWN | — | viz výše | NÍZKÉ | ovládání |
| `steer_decay` | SteerDecay | 330 | SPS | UNKNOWN | — | UNKNOWN | — | vysokorychlostní test | STŘEDNÍ | ovládání |
| `ackermann` | Ackerman | 0.9 | — | UNKNOWN | — | UNKNOWN | — | geometrie přední nápravy S650 | STŘEDNÍ | geometrie |
| `front_wheel_steer` | FWSteer | None (4WS off) | — | None (S650 nemá 4WS) | odvozeno z konstrukce vozu | ESTIMATED | odhad (konstrukčně dáno) | vizuální kontrola specifikace | NÍZKÉ — ponechat None | ovládání |
| `steering_type` | SteeringType | New | — | UNKNOWN (kit-vnitřní přepínač, ne vlastnost vozu) | — | UNKNOWN | — | Studio test obou větví | STŘEDNÍ | podpůrný |
| `steer_axis_offset` | (StAxisOffset) | null | — | UNKNOWN — klíč v live Tune **CHYBÍ**, `Initialize:171` ho čte (chyba č. 1) | — | PENDING | — | první spuštění ve Studiu potvrdí/vyvrátí runtime error | VYSOKÉ — blokuje první spuštění | neznámý |

### 2.6 Brzdy

| Interní ID | Název | Kit | Jedn. | Mustang cíl | Zdroj cíle | Stav | Původ cíle | Ověření | Riziko změny | Důležitost |
|---|---|---|---|---|---|---|---|---|---|---|
| `brake_force` | BrakeForce | 2500 | — | UNKNOWN (kotouče F 390×36 / R 355×28 Brembo doloženy, ale `BrakeForce` není moment v Nm — škáluje se FPS a režimy; rovnítko zakázáno) | profil `brakes.*` ([1b]) — INFO | UNKNOWN | — | brzdný test 100–0 + kalibrace `#BV` vzorce | VYSOKÉ — špatná síla = nedobrzdění/přebrzdění | dynamika |
| `brake_bias_front` | BrakeBias | 0.6 | 0–1 | UNKNOWN (profil: `CHYBÍ`, rozdělení účinku EU GT nepublikováno) | — | UNKNOWN | — | brzdný test / dílenský manuál S650 | VYSOKÉ — extrémy 0/1 rizikové | dynamika |
| `pbrake_force` | PBrakeForce | 5000 | — | UNKNOWN | — | UNKNOWN | — | test ruční brzdy (jen zadek) | NÍZKÉ | ovládání |
| `pbrake_bias` | PBrakeBias | 0 | — | UNKNOWN (hodnota 0 ověřena, název live-klíče potvrzen F4.3) | audit §12 | UNKNOWN | — | Studio odečet názvu klíče | NÍZKÉ | podpůrný |
| `tcs_threshold_sps` | TCSThreshold | 20 | SPS | UNKNOWN | — | UNKNOWN | — | test prokluzu na mokru | STŘEDNÍ — prahy ABS/TCS ≥ ~5 SPS | ovládání |
| `tcs_gradient` | TCSGradient | 20 | SPS | UNKNOWN | — | UNKNOWN | — | viz výše | STŘEDNÍ | ovládání |
| `tcs_limit_pct` | TCSLimit | 10 | % | UNKNOWN | — | UNKNOWN | — | viz výše | STŘEDNÍ | ovládání |
| `abs_threshold_sps` | ABSThreshold | 20 | SPS | UNKNOWN | — | UNKNOWN | — | brzdný test | STŘEDNÍ | ovládání |

### 2.7 Motor a momentová charakteristika

| Interní ID | Název | Kit | Jedn. | Mustang cíl | Zdroj cíle | Stav | Původ cíle | Ověření | Riziko změny | Důležitost |
|---|---|---|---|---|---|---|---|---|---|---|
| `horsepower` | Horsepower | 200 | hp | UNKNOWN — 328 kW (446 PS) @ 7250 doloženo, ale `peak_power_kw ≠ horsepower` bez definovaného převodu (jiná veličina, jednotka i referenční bod křivky); přepis zakázán (MAPPING §6) | profil `engine.max_power` ([1b]+[3]) — INFO | UNKNOWN | — | definovat převod Nm→hp přes otáčky + křivku (rozhodne Agent D / M4) | VYSOKÉ — jediný výkonový skalár Tune; špatný převod = špatná V-max i akcelerace | dynamika |
| `peak_rpm` | PeakRPM | 6800 | rpm | UNKNOWN — 7250 rpm je bod maxima výkonu, ne vrchol kit-křivky `CurveN` | profil `engine.max_power_rpm` — INFO | UNKNOWN | — | viz výše + tovární křivka (nepublikována) | VYSOKÉ | dynamika |
| `peak_sharpness` | PeakSharpness | 20 | — | UNKNOWN (křivka nepublikována) | profil `torque_curve`: `points: []`, status UNKNOWN | UNKNOWN | — | tovární měření křivky (M1.9), nikdy nedomýšlet body | VYSOKÉ | dynamika |
| `curve_mult` | CurveMult | 0.5 | ~0–1 | UNKNOWN | — | UNKNOWN | — | viz výše | STŘEDNÍ | dynamika |
| `eq_point` | EqPoint | 5252 | — | UNKNOWN (kit-vnitřní převodní bod HP↔lb-ft) | — | UNKNOWN | — | neměnný převodní bod, ponechat | NÍZKÉ | podpůrný |
| `idle_rpm` | IdleRPM | 950 | rpm | UNKNOWN (profil: `CHYBÍ`) | — | UNKNOWN | — | OBD log / dílenský manuál | NÍZKÉ | podpůrný |
| `redline_rpm` | Redline | 8000 | rpm | UNKNOWN (profil: `CHYBÍ`) | — | UNKNOWN | — | Ford tech specs / OBD log | STŘEDNÍ — omezovač vs 7250 rpm maxima | dynamika |
| `compression_ratio` | CompressionRatio? | null | — | UNKNOWN (profil: `CHYBÍ`; klíč auditem nepotvrzen, jen ve vzorci HP_T) | — | UNKNOWN | — | dohledat Ford technický list [1]; Tune klíč není potvrzen | STŘEDNÍ | neznámý |
| `rev_accel` / `rev_decay` / `rev_bounce` | RevAccel/Decay/Bounce | 250/75/250 | — | UNKNOWN (setrvačnost pohonu S650 nepublikována) | — | UNKNOWN | — | OBD log náběhu otáček | NÍZKÉ | podpůrný |
| `flywheel` | Flywheel | 500 | — | UNKNOWN | — | UNKNOWN | — | viz výše (závislost `flywheel ↔ rev_accel/clutch_engage`) | NÍZKÉ | podpůrný |
| `throttle_accel` / `throttle_decel` | ThrotAccel/Decel | 0.05/0.2 | — | UNKNOWN | — | UNKNOWN | — | měření odezvy plynu | NÍZKÉ | ovládání |
| `turbo_count` / `turbo_boost` | Turbochargers/T_Boost | 2 / 7 | ks/— | 0 / n/a — Mustang GT je atmosféra (5.0 Ti-VCT V8 bez turba) | profil `engine.code` ([1b]) | VERIFIED | oficiální zdroj | vizuální kontrola motoru (triviální) | VYSOKÉ (procesní) — kit má 2 turba, Mustang 0; `boost` vyžaduje `count ≥ 1` | dynamika |
| `supercharger_count` | Superchargers | 0 | ks | 0 (atmosféra, shoda s kitem) | profil `engine.code` ([1b]) | VERIFIED | oficiální zdroj | — | NÍZKÉ — shoda, ponechat | dynamika |
| `engine_brake_force` | EBrakeForce | 500 | — | UNKNOWN | — | UNKNOWN | — | test dojížďky | NÍZKÉ | podpůrný |

### 2.8 Převodovka

| Interní ID | Název | Kit | Jedn. | Mustang cíl | Zdroj cíle | Stav | Původ cíle | Ověření | Riziko změny | Důležitost |
|---|---|---|---|---|---|---|---|---|---|---|
| `gear_ratios` | Ratios | R3.28/N0/1–6: 3.827/2.36/1.685/1.313/1.0/0.793 | — | 1: 3.237 / 2: 2.104 / 3: 1.422 / 4: 1.0 / 5: 0.814 / 6: 0.622 (Getrag MT-82); zpátečka UNKNOWN | profil `transmission.gear_ratios` ([1]/[1b]) | VERIFIED | oficiální zdroj | konfigurátor Ford CZ/DE pro R; strukturální převod list→dict s R/N definuje Agent D | VYSOKÉ — jiná skříň (kit DCT-ish vs MT-82 manuál); `TransModes`/`Auto*` větve k revizi | dynamika |
| `final_drive` | FinalDrive | 3.545 | — | UNKNOWN — kandidáti 3.15:1 / 3.55:1 bez přiřazení k EU 6MT (GUARD T17: null jako definitivu nepoužít) | profil `transmission.final_drive` | UNKNOWN | neověřený předpoklad (oba kandidáti) | konfigurátor Ford CZ/DE / workshop data S650 | VYSOKÉ — s `FDMult` konflikt; `FDMult≠1` rozhodí Gauges (vizuálně) | dynamika |
| `final_drive_mult` | FDMult | 1.1 | — | 1 (neutrál pro Gauges; měnit jen samostatně) | audit §6 | VERIFIED | oficiální zdroj (audit) | Gauges kontrola max-rychlosti | NÍZKÉ — ponechat 1 do kalibrace | podpůrný |
| `trans_modes` | TransModes | [Semi,Manual,Auto] | — | Manual-first (6MT s rev-matching) | profil `transmission.type` ([1b]) | ESTIMATED | odhad (odvozeno z typu skříně) | jízdní test manuálního režimu | STŘEDNÍ | ovládání |
| `shift_up_time` / `shift_down_time` | ShiftUp/DnTime | 0.25/0.125 | s | UNKNOWN (manuál řadí řidič; časy DCT neaplikovatelné 1:1) | — | UNKNOWN | — | měření času řazení MT-82 / ponechat kit | NÍZKÉ | ovládání |
| `clutch_*` (enabled/engage/rpm/speed/stall/kick) | Clutch… | True/10/3500/20/True/False | mix | UNKNOWN (rev-matching MT-82 ≠ žádná kit-větev 1:1) | — | UNKNOWN | — | test rozjezdů / launch | STŘEDNÍ | ovládání |

### 2.9 Diferenciál a pohon

| Interní ID | Název | Kit | Jedn. | Mustang cíl | Zdroj cíle | Stav | Původ cíle | Ověření | Riziko změny | Důležitost |
|---|---|---|---|---|---|---|---|---|---|---|
| `drive_config` | Config | AWD | FWD\|RWD\|AWD | RWD ("Front-engine, Rear-wheel drive with limited-slip differential") | profil `drivetrain` ([1b]) | VERIFIED | oficiální zdroj | — | VYSOKÉ — kit AWD vs RWD mění celé chování; `torque_vector` a dif-váhy k revizi | dynamika |
| `differential_type` | DifferentialType | New | New\|Old | UNKNOWN mapování — LSD potvrzeno obecně, přesný typ UNKNOWN (není automaticky Torsen; Torsen = Dark Horse, do EU profilu nepatří — T18) | profil `drivetrain.differential_rear` ([1b]) — INFO | UNKNOWN | — | workshop data S650 (typ + stálý převod) | VYSOKÉ — záměna Dark Horse dílů zakázána | dynamika |
| `torque_vector` | TorqueVector | 0 (50:50) | −1..1 | 0/100 → v RWD režimu irelevantní / k revizi s `drive_config` | profil `drivetrain.torque_split_f_r` (odvozeno z RWD) | ESTIMATED | odhad | jízdní test po přepnutí na RWD | STŘEDNÍ — závislost `torque_vector → drive_config` | dynamika |
| `front_diff_power` / `front_diff_coast` | FDiffPower/Coast | 20/20 | 0–100 | n/a (RWD — přední dif neexistuje) | odvozeno z RWD | ESTIMATED | odhad | — | NÍZKÉ — u RWD ignorováno, nemazat bez rozhodnutí D | podpůrný |
| `rear_diff_power` | RDiffPower | 40 | 0–100 | UNKNOWN (LSD potvrzeno, hodnoty 40/30 jen zadek-bez-klíčů → live-klíč potvrzen F4.3, hodnota PENDING) | audit §7 | PENDING | neověřený předpoklad | Studio odečet + test svornosti | STŘEDNÍ | dynamika |
| `rear_diff_coast` | RDiffCoast | 30 | 0–100 | UNKNOWN (viz výše) | audit §7 | PENDING | neověřený předpoklad | viz výše | STŘEDNÍ | dynamika |
| `diff_preload_f` | FDiffPreload | 20 | 0–100 | n/a (RWD) | odvozeno z RWD | ESTIMATED | odhad | — | NÍZKÉ | podpůrný |
| `diff_preload_r` | RDiffPreload | null | 0–100 | UNKNOWN | — | PENDING | — | Studio odečet | STŘEDNÍ | dynamika |
| `slip_thresh_f/r/c` + `lock_thresh_f/r/c` | *Diff*Thres | null ×6 | — | UNKNOWN (Starý dif ignorován při `DifferentialType=New`; live-klíče potvrzeny F4.3, hodnoty neuvedeny) | audit §7 | PENDING | — | Studio odečet + test prokluzu | STŘEDNÍ | dynamika |

### 2.10 Aero a ostatní jízdní (SCRIPT — parametrem nelze)

| Interní ID | Název | Kit | Jedn. | Mustang cíl | Zdroj cíle | Stav | Původ cíle | Ověření | Riziko změny | Důležitost |
|---|---|---|---|---|---|---|---|---|---|---|
| `drag_coeff` | (Drag) | 0.34 (konstanta ve skriptu) | — | UNKNOWN (profil: Cd `CHYBÍ`, plocha `CHYBÍ`) | — | UNKNOWN | — | Ford tech specs PDF [1] / coast-down test; PŘED V-max kampaní oprava `magnitude` bugu (Aerodynamics:21), jinak maximálka bez odporu | VYSOKÉ (procesní) | dynamika |
| `downforce_f` / `downforce_r` | — | 125/150 (konstanty) | — | UNKNOWN | — | UNKNOWN | — | tunelová data neexistují; kalibrace V-max (250 km/h VERIFIED [1b] jako validační cíl, ne vstup) | STŘEDNÍ — změna jen kódem | dynamika |
| `wear_speed` / `wheel_lock_ratio` / `wheelspin_ratio` | — | .4/3.6/.5 … | — | UNKNOWN | — | UNKNOWN | — | testy opotřebení/prokluzu | NÍZKÉ | podpůrný |

## 3. Co je zdrojem cíle a co není (guardrails)

1. **Doložené cíle (10):** rozvor 2719 · rozchod 1585/1642 · pneu 255/40 R19 + 275/40 R19 ·
   disky 19×9.0J / 19×9.5J (INFO) · výkon 328 kW @ 7250 · moment 540 Nm @ 5100 ·
   převody 1–6 (3.237/2.104/1.422/1.0/0.814/0.622) · RWD+LSD · turbo 0 / kompresor 0 ·
   pohotovostní hmotnost 1808 kg (ESTIMATED) · kotouče 390/355 (INFO, bez Tune protějšku) ·
   V-max 250 km/h + 0–100 za 5.3 s jako **validační cíle**, ne vstupy.
2. **UNKNOWN zůstává UNKNOWN (50):** rozložení hmotnosti · výška těžiště · Cd/plocha ·
   stálý převod (3.15 vs 3.55 nerozhodnuto) · zpátečka · redline · volnoběh ·
   brzdný bias · tuhosti/tlumiče/délky (vše PENDING na Studio) · řízení · adheze ·
   momentová křivka (`points: []` — nikdy nedomýšlet body, M1.9).
3. **Jeep data:** v použitých zdrojích se nevyskytují; nic nebylo převzato.
4. **Nesoulady, které mapa nepřekrývá (MAPPING §6):** `Horsepower` vs 328 kW ·
   `BrakeForce` vs Nm · `Ratios` list≠dict · `peak_torque_nm` bez Tune protějšku ·
   `FDMult≠1` jen vizuální konflikt · převod lb→kg až v runtime vrstvě.

## 4. Mimo rozsah této mapy (vědomě vynecháno)

Elektro-větev 9× (`electric_*`, mrtvá — `Electric=false`) · `legacy_wheel_density_f/r` +
`electric_gauge_names` (READ_ONLY, mrtvý kód) · `tq_lock` · `supercharger_sensitivity` ·
`spring_color` · `wind_volume` (zvuk) · `sus_radius` (vzhled) · `weight_box_size` řešen
v §2.1 · `curve_shape_func`/`shift_logic`/`abs_pulse_logic`/`center_diff_logic`/
`arm_kinematics` (SCRIPT — až M4/M5 návrh kódu, ne mapa).

## 5. Hlavní rizika (top 7)

1. **RWD vs AWD** — kit je AWD, Mustang RWD. Přepnutí mění trakci, torque-vectoring i
   dif-váhy; provést jako jeden řízený krok s testem, ne po částech.
2. **Turbo 2 → 0** — kit má 2 turba + boost 7; atmosféra je bez nich. Odstranění mění
   celou výkonovou křivku; závisí na vyřešení převodu 328 kW → `Horsepower`.
3. **Výkonový převod nedefinován** — 328 kW @ 7250 / 540 Nm @ 5100 nelze 1:1 přepsat na
   `Horsepower` 200 hp; bez křivky (`points: []`) a převodu je motorová kalibrace zablokovaná.
4. **Tužidla/tlumiče bez hodnot** — `FSusStiffness/RSusStiffness/FSusDamping/RSusDamping`
   mají jen kandidátní dekód (20000/500); do Studio-odečtu mimo prostor i mimo zápis.
5. **`StAxisOffset` chyba č. 1** — klíč v Tune chybí, `Initialize:171` ho čte;
   verdikt před prvním během, jinak hrozí runtime error.
6. **`magnitude` chyba č. 2** — odpor se nikdy neaplikuje; V-max (250 km/h) měřit až po
   opravě, jinak je maximálka bez odporu.
7. **Stálý převod nerozhodnut** — 3.15:1 vs 3.55:1; GUARD T17 zakazuje použít null jako
   definitivu; bez přiřazení k EU 6MT stojí celá kalibrace převodovky.

## 6. Předání dalším agentům / milníkům

- **M4 (kalibrace):** čeká na Studio-odečty §2.4 + rozhodnutí převodu motoru (§2.7) +
  stálý převod (§2.8); validační cíle 5.3 s / 250 km/h připraveny.
- **Agent D (wiring):** strukturální konverze `Ratios` list→dict; `TransModes` Manual-first;
  `peak_torque_nm` stále bez Tune protějšku (odmítnout, ne tiše převést).
- **Opakovatelnost:** `check_known_tables()` = 0 cyklů; katalog 138 záznamů
  (82/14/2/3/37); profil `ford-mustang-gt-2024-eu-manual-standard.json` beze změny.
