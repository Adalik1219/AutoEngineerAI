# Agent F — A-Chassis capability + mapovací tabulka (ANALÝZA, žádné ladění)

**Větev:** `feat/m2-m3-geometry` · **SHA:** `557ee39` (ověřen `git rev-parse --short HEAD`, strom čistý kromě tohoto souboru) · **Datum:** 2026-11-20
**Pravidla:** česky; identifikátory anglicky. **Fyzika neměněna, konfigurace neměněny, žádné hodnoty neladěny.**
**Zapsán pouze tento soubor.** RBXM pouze čteny referenčně (nedotčeny), Simulator READ-ONLY (nedotčen).
M3 CLOSED, `main`/PR#2 tabu — žádný návrh změn kódu, jen mapa.
**Žádné vymýšlení:** chybějící = `UNKNOWN` / `UNSUPPORTED` / `PENDING`; `hp ≠ Nm`; `BrakeBias ≠ důkaz fyziky`.
**Jeep data:** v použitých zdrojích se nevyskytují; nic z nich není převzato (kit je v adaptéru veden jako zdroj klíčů, ne jako zdroj cílových hodnot).

**Vstupy (čteno):** `AGENT-F-MUSTANG-PHYSICS-MAPPING.md` (60 parametrů z minula — rozsah zde rozšířen na 103, viz §0),
`AGENT-A-S02-CATALOG-AUDIT.md` (101 hran, 12 SCC), `AGENT-E-M2-CONTRACTS.md` (brány M2/M3),
`docs/A-CHASSIS-PARAMETER-CATALOG.md`, `docs/MAPPING.md`, `src/Chassis/catalog/parameters.json` (138 záznamů),
`src/Chassis/adapters/achassis_v1.py` (125+13 položek, `apply_config`, `limits()`),
`src/Chassis/mapping_engine.py` + `src/Chassis/mapping/dependencies.py`,
`src/Physics/{engine,gearbox,brakes,diff,suspension,steering,tires,api}.py`, `src/Sim/{config,physics_backend}.py`,
`vehicle-data/references/ford-mustang-gt-2024-eu-manual-standard.json` (zdroj pravdy pro Mustang cíle, M1.5).

## 0. Rozsah a počty

Rozsah = **103 parametrů**: 60 z minulé mapy + spojka/dif/auto-větve/Tune-detaily, které minulá mapa agregovala
(`clutch_*`, `slip/lock_*`, `auto_*`, `idle_throttle`, `brake_accel/decel`, `incline_comp`, gyro, `SusRadius`,
aero/script-větev). Elektro-větev 9× (`Electric=false`, mrtvá), `legacy_*`, `electric_gauge_names`,
`wind_volume` (zvuk), `spring_color` (vzhled), `tq_lock` uveden 1× — mimo jízdní tabulku, viz §7.6.

| Třída (katalog `category` + `verification_status`) | Počet | Význam pro mapu |
|---|---|---|
| `MUTABLE_TUNE` + `PASS` → **PODPOROVÁNO** (ověřený Tune klíč, zapisovatelné) | **59** | přímý zápis do Tune; z toho **8× ADAPTÉR** (nutná konverze / řízený krok, §1.2) |
| `PENDING` (nezapisovat do Studio-odečtu) | **31** | 5× MUTABLE klíč bez hodnoty · 24× UNKNOWN · 2× STRUCTURE (geometrie) |
| `SCRIPT_CONTROLLED` → **UNSUPPORTED** (parametrem nelze, jen kódem) | **12** | jízdně relevantní; §1.3 |
| `UNKNOWN` + `PASS` (`pbrake_bias`: klíč i hodnota známy, kategorie UNKNOWN) | **1** | nezapisovat do rozhodnutí koordinátora |
| **Celkem** | **103** | 59 + 31 + 12 + 1 |

Rozpad PENDING (31): `sus_stiffness_f/r`, `damper_f/r`, `diff_preload_r` (5× MUTABLE bez hodnoty) ·
`sus_length_f/r`, `pre_compress_f/r`, `extension_lim_f/r`, `compress_lim_f/r`, `sus_angle_f/r`,
`anchor_offset_f/r`, `front/rear_wishbone_len`, `slip_thresh_f/c/r`, `lock_thresh_f/c/r`,
`rear_diff_power/coast`, `compression_ratio`, `tq_lock`, `steer_axis_offset`, `spring_color` (24× UNKNOWN) ·
`wheelbase_etc`, `wheel_radius` (2× STRUCTURE).
Ověřeno skriptem nad `parameters.json` (138 záznamů): 59× MUTABLE/PASS + 31× PENDING + 12× SCRIPT/PASS +
1× UNKNOWN/PASS = 103 v rozsahu této zprávy. `spring_color` (vzhled) je započten v PENDING,
v tabulce §7.6 je jen zmíněn (mimo jízdu).

Legenda stavů v tabulkách: **PODPOROVÁNO** = Tune klíč, zápis dnes · **ADAPTÉR** = klíč existuje, nutný převod/řízený krok ·
**ODVOZENO** = hodnota odvozena z konstrukce vozu, ne měřením · **PENDING** = čeká Studio-odečet, nezapisovat ·
**UNSUPPORTED** = parametrem nelze (skript/geometrie) · **UNKNOWN** = cíl ani prostředek chybí, nevymýšlet.

## 1. Co lze v A-Chassis nastavovat (s důkazem)

### 1.1 Přímo podporované — 59× (MUTABLE_TUNE + PASS)

Důkaz mechanismu: `src/Chassis/adapters/achassis_v1.py::_m()` (provenance `measured`, `mutable=True`) +
`AChassisV1Adapter.apply_config` (neznámý klíč → `rejected`, neměnitelný → `rejected` s důvodem, binárka se nikdy
nezapisuje) + `src/Chassis/catalog/loader.py` (MUTABLE_TUNE bez `tune_key` = chyba validace).
Důkaz hodnot: `docs/A-CHASSIS-AUDIT.md` §5–§13 (citace `§N` u každého `_m()`), kontrolní součet katalogu
79 MUTABLE_TUNE = 79 `measured` v adaptéru (z toho 59 v jízdním rozsahu této zprávy).
Mapovací brána: `mapping_engine.map_config` — `MUTABLE_TUNE` + rozsah + splněné `depends_on` + bez `conflicts` → `tune_changes`;
jinak `rejected` s důvodem (žádná tichá ignorace). `build_search_space`: 5 filtrů (MUTABLE + PASS + `min<max` + `used_in` + `backend_caps`).

### 1.2 Přes adaptér / s konverzí — 8× (podmnožina z 59, stav ADAPTÉR)

| Tune klíč | Konverze / řízený krok | Důkaz |
|---|---|---|
| `Ratios` | VehicleConfig `list` → Tune `dict {R,N,1..6}`; R/N definuje Agent D; Mustang R UNKNOWN | MAPPING §6 nesoulad #10 (list≠dict s R/N) |
| `Weight` | `lb` → `kg` řeší **až adaptér/runtime vrstva, nikdy úložiště** | MAPPING §6 nesoulad #12; adapter §11 |
| `FinalDrive` × `FDMult` | multiplikativní nejednoznačnost; `FDMult≠1` rozhodí Gauges **jen vizuálně** | `KNOWN_CONFLICTS` (`mapping/dependencies.py`), MAPPING §4; katalog závislost `final_drive_mult → final_drive` + cyklus S-02 č. 10 |
| `TransModes` | výběr `Manual`-first (první = výchozí); `Auto*` větve k revizi | adapter §6 (`_m trans_modes`, „První = výchozí") |
| `BrakeForce` | **není moment v Nm** — škáluje se FPS a režimy (`#BV` vzorec); rovnítko s `brakes.torque_Nm` zakázáno | MAPPING §6 nesoulad #7; adapter §12 |
| `Config` | `AWD` (kit) → `RWD` (Mustang) = **jeden řízený krok s testem**, ne po částech | adapter §7; S-02: `torque_vector → drive_config` |
| `TorqueVector` | v RWD režimu irelevantní / k revizi s `drive_config` | adapter §7 („Rozdělení F/R u AWD není středový dif") |
| `SteerRatio`+`LockToLock` | `max_angle` se **neopisuje** — odvozuje se `SteerOuter = LockToLock×180/SteerRatio` (31.2°) | MAPPING §6 nesoulad #9; S-02 cyklus č. 12 |

### 1.3 Nepodporované parametrem — 12× UNSUPPORTED (SCRIPT_CONTROLLED) + 2× konstrukce

Důkaz: katalog `change_method: script` / adapter `_s()` (`read_only_reason`) / `map_config` → vždy `rejected`.
`curve_shape_func` (tvar `CurveN` parabola kolem `PeakRPM` — audit §5) · `shift_logic` (`Auto()`+LC kód — §6) ·
`center_diff_logic` (středový dif/vektorování — §7) · `arm_kinematics` (custom `SuspensionGeometry` přebíjí — §8/§16) ·
`camber_caster_toe` (vše 0°, jen `CFrame.Angles` — §9, fyziku nedělá) · `target_friction` (`F/RTargetFriction .7+Heat`
v `Simulated._WHEELTUNE`, mimo Tune — §10) · `wheel_lock_ratio` / `wheelspin_ratio` / `wear_speed` (režimy v `Simulated` — §10) ·
`abs_pulse_logic` (současné ABS je on/off `tqABS=0`, pulzování jen kódem — §12) · `drag_coeff` (konstanta `.34` +
**chyba `magnitude`** `Aerodynamics:21`, odpor se nikdy neaplikuje — §13/§17.2) · `downforce_f/r` (konstanty 125/150 — §13).
Konstrukcí (STRUCTURE_CONTROLLED, `change_method: geometry`): `wheelbase_etc` (rozvor/rozchod/ride-height),
`wheel_radius` — měří se ve Studiu do `vehicle-data/analyzed/`, parametrem nelze.

### 1.4 Neznámé — PENDING 30× (nezapisovat) + `steer_axis_offset` bez klíče

Společný důkaz: katalog `verification_status: PENDING` (loader selftest jmenovitě vypisuje) + adapter `_u()`
(`provenance unknown`, `mutable=False`, `default None`) + `apply_config` je odmítne.
Kritický případ: `steer_axis_offset` — klíč v live Tune **CHYBÍ**, ale `Initialize:171` ho čte
(**chyba č. 1**, `limits()` adaptéru) → podezření na runtime error; verdikt před prvním během ve Studiu.
Ostatní: délky pružin + limity (8×, jen vzorce `FreeLength=SusLength+PreCompress`, `Max=+ExtensionLim`, `Min=−CompressLim`),
ramena/úhly/kotvy (6×, neaktivní procedurální větev), `slip/lock_thresh_*` (6×, starý dif ignorován při `New`),
`rear_diff_power/coast` (klíče F4.3, hodnoty 40/30 historicky bez názvů — nepřevzato),
`diff_preload_r` (klíč F4.3, hodnota `None`), `compression_ratio` (jen ve vzorci HP_T), `tq_lock` (měnič),
`sus_stiffness_f/r` + `damper_f/r` (MUTABLE klíče F4.3, hodnoty `None` — kandidátní dekód 20000/500 nepřevzat,
symetrie kol nevychází, float-lane gap §1).

## 2. Motor

| Věc | A-Chassis (kit) | Důkaz | Mustang cíl | Status |
|---|---|---|---|---|
| Výkonový skalár | `Horsepower` = 200 `hp` | adapter §5 `_m`, audit §5 | 328 kW @ 7250 (oficiální [1b]) — **nelze přepsat 1:1** | ADAPTÉR (převod nedefinován) |
| Momentový skalár | **žádný** — Tune má jen `Horsepower` + křivku | MAPPING §6 nesoulad #1 (`peak_torque_nm` → `rejected`) | 540 Nm @ 5100 (oficiální [1b]) | UNSUPPORTED (bez Tune protějšku) |
| Křivka | `CurveN` parabola kolem `PeakRPM` (`PeakSharpness` 20, `CurveMult` 0.5, `EqPoint` 5252) | adapter §5 + `_s curve_shape_func` (tvar = kód) | `torque_curve.points: []`, `interpolation: none` — **křivka nepublikována, nikdy nedomýšlet body (M1.9)** | UNSUPPORTED (tvar) + UNKNOWN (body) |
| Interpolace | A-Chassis: parabola; Sim/`Physics`: lineární `torque_at_rpm` + `P = M·ω` | `src/Physics/engine.py` (`torque_at_rpm`, `engine_output`) | n/a (žádná tovární křivka) | INFO — `hp≠Nm`, `peak_power_kw≠horsepower` (MAPPING §6 #2) |
| Volnoběh | `IdleRPM` 950 `rpm` (+ `IdleThrottle` 3) | adapter §5 | profil: **CHYBÍ** | UNKNOWN |
| Redline / limiter | `Redline` 8000 `rpm`; omezovač `RevBounce` 250 (sráží plný/½ na posledním stupni) | adapter §5 | profil: **CHYBÍ** (známo jen 7250 = bod maxima výkonu, ne redline) | UNKNOWN |
| Setrvačnost/odezva | `RevAccel` 250 / `RevDecay` 75 / `RevBounce` 250, `Flywheel` 500, `ThrotAccel` 0.05 / `ThrotDecel` 0.2, `EBrakeForce` 500 | adapter §5 | nepublikováno | PODPOROVÁNO (klíče), cíl UNKNOWN |
| Přeplňování | `Turbochargers` 2 + `T_Boost` 7 (vzorec HP_T: `T_Boost × počet × CompressionRatio/10 / 7.5`); `Superchargers` 0 | adapter §5; `KNOWN_DEPENDS`: `engine.turbo.boost` vyžaduje `engine.turbo.count ≥ 1` | atmosféra 5.0 V8: **turbo 0 / kompresor 0** (oficiální [1b]) | PODPOROVÁNO + ODVOZENO (2→0 je procesní krok, boost vyžaduje count≥1) |
| Komprese | `CompressionRatio` — klíč nepotvrzen, jen ve vzorci HP_T | adapter §5 `_u` | profil: CHYBÍ | UNKNOWN |

Závěr motoru: jediný výkonový vstup Tune je `Horsepower` (hp); 328 kW ani 540 Nm do něj **nelze vepsat bez definovaného
převodu** (jiná veličina, jednotka i referenční bod křivky). Převod `Nm→hp` přes otáčky + křivku je úkol M4 / Agent D;
do té doby je motorová kalibrace **zablokovaná** (ne technikou, ale chybějícím převodem + prázdnou křivkou).

## 3. Převodovka (cíl = MANUÁL; automatickou Jeep logiku nepřenášet)

| Věc | A-Chassis (kit) | Důkaz | Mustang cíl (Getrag MT-82 6MT) | Status |
|---|---|---|---|---|
| Stupně 1–6 | `Ratios` dict: 3.827/2.36/1.685/1.313/1.0/0.793 (DCT-ish sada) | adapter §6 | **3.237 / 2.104 / 1.422 / 1.0 / 0.814 / 0.622** (oficiální [1]/[1b]) | ADAPTÉR (strukturální list→dict + jiné sady) |
| Zpátečka | `Ratios.R` = 3.28 | adapter §6 | profil `reverse_ratio`: **null** (CHYBÍ) | UNKNOWN (R klíč existuje, cílová hodnota ne) |
| Neutrál | `Ratios.N` = 0 | adapter §6 | 6MT má neutrál (konstrukčně dáno) | ODVOZENO (ponehat 0) |
| Stálý převod | `FinalDrive` 3.545 | adapter §6 | **null** — kandidáti 3.15:1 / 3.55:1 bez přiřazení k EU 6MT (GUARD: null nelze použít jako definitivu) | UNKNOWN (kritické — stojí na něm celá kalibrace převodovky) |
| Škálování | `FDMult` 1.1 | adapter §6 | 1 (neutrál pro Gauges) | ADAPTÉR (měnit jen samostatně; konflikt FD×FDMult) |
| Režimy | `TransModes` [Semi, Manual, Auto] (první = výchozí) | adapter §6 | **Manual-first** (6MT s rev-matching; typ v profilu oficiální) | ADAPTÉR (výběr pořadí; `Auto*` větve k revizi) |
| Časy řazení | `ShiftUpTime` 0.25 s / `ShiftDnTime` 0.125 s | adapter §6 | manuál řadí řidič — DCT časy neaplikovatelné 1:1 | PODPOROVÁNO (klíče), cíl UNKNOWN — ponechat kit do měření MT-82 |
| Auto-logika (NEPŘENÁŠET) | `AutoShiftMode` Speed / `AutoShiftType` DCT / `AutoUpThresh` −200 / `AutoDownThresh` 1400; `shift_logic` = kód (`Auto()`+LC) | adapter §6 (`_s shift_logic`) | 6MT: automatické řazení neexistuje | UNSUPPORTED-záměrně (`shift_logic` SCRIPT) + auto-prahy irelevantní pro manuál |
| Spojka | `Clutch` True / `ClutchEngage` 10 / `SpeedEngage` 20 SPS / `RPMEngage` 3500 / `Stall` True / `ClutchKick` False | adapter §6 | rev-matching MT-82 ≠ žádná kit-větev 1:1 | PODPOROVÁNO (klíče), cíl UNKNOWN — launch test |
| Měnič | `TQLock` — hodnota neuvedena | adapter §6 `_u` | manuál nemá měnič | UNKNOWN (mimo manuál) |

Cyklus S-02 č. 10 (`final_drive ↔ gear_ratios ↔ final_drive_mult`) + č. 8 (`auto_shift_type ↔ shift_up/down_time`) +
č. 9 (`auto_up_thresh ↔ peak_rpm`): převodovkové parametry se **nesmí mapovat automaticky jako celek** — ručně,
po jednom, s odůvodněním (§8).

## 4. Pohon a diferenciál (RWD)

| Věc | A-Chassis (kit) | Důkaz | Mustang cíl | Status |
|---|---|---|---|---|
| Koncepce | `Config` = AWD | adapter §7 | **RWD** („Front-engine, RWD with LSD", oficiální [1b]) | ADAPTÉR (řízený krok AWD→RWD) |
| Rozdělení | `TorqueVector` 0 (50:50); adapter: „u AWD není středový dif — obě nápravy plné tq škálované biasem" | adapter §7 | **0/100** (odvozeno z RWD) | ODVOZENO (v RWD irelevantní, k revizi s `Config`) |
| Typ difu | `DifferentialType` New (párové násobiče FR↔FL, RR↔RL, součet páru = 2) | adapter §7 | **LSD potvrzeno obecně; přesný typ UNKNOWN** (není automaticky Torsen — Torsen = Dark Horse, do EU profilu nepatří) | PODPOROVÁNO (klíč), typová kalibrace UNKNOWN |
| Přední dif | `FDiffPower/Coast` 20/20, `FDiffPreload` 20 | adapter §7 (live-klíče F4.3) | n/a (RWD — přední dif neexistuje) | ODVOZENO (u RWD ignorováno, nemazat bez D) |
| Zadní dif | `RDiffPower/RDiffCoast` — klíče F4.3, hodnoty historicky „zadek 40/30" bez názvů (nepřevzato) | adapter §7 `_u`; katalog PENDING | LSD svornost nepublikována | PENDING (Studio odečet + test svornosti) |
| Preload zadek | `RDiffPreload` — klíč F4.3, hodnota `None` | adapter §7; katalog MUTABLE/PENDING | UNKNOWN | PENDING |
| Prahy New-difu | `F/R/C DiffSlipThres`, `F/R/C DiffLockThres` — klíče F4.3, hodnoty neuvedeny (starý `SlipThres/LockThres` ignorován při `New`) | adapter §7 `_u`; katalog UNKNOWN/PENDING | UNKNOWN | PENDING |
| Střed/vektorování | `center_diff_logic` = kód | adapter §7 `_s` | žádný středový dif (RWD) | UNSUPPORTED (nepotřebné pro RWD cíl) |

A-Chassis skutečně umí: přepínač `Config` FWD/RWD/AWD + nový dif s váhami 0–100 a preloadem + prahy prokluzu/zámku.
Neumí parametrem: skutečný středový dif ani aktivní vektorování (jen skriptem). `BrakeBias ≠ důkaz pohonu` — bias dělí
brzdný požadavek, s traktem RWD nesouvisí.

## 5. Brzdy a ABS

| Věc | A-Chassis (kit) | Důkaz | Mustang cíl | Status |
|---|---|---|---|---|
| Provozní síla | `BrakeForce` 2500 (`#BV = FBrake/RBrakeForce × 60/FPS × brzda × tqABS + …`) | adapter §12; MAPPING #7 | kotouče F 390×36 / R 355×28 Brembo (oficiální [1b]) — ale `BrakeForce` **není moment v Nm**, škáluje se FPS | ADAPTÉR (kalibrace brzdným testem 100–0, rovnítko s Nm zakázáno) |
| Bias | `BrakeBias` 0.6 (podíl předku 0–1; extrémy 0/1 rizikové) | adapter §12 (live-klíč F4.3) | profil `brake_bias_front_pct`: **CHYBÍ** | PODPOROVÁNO (klíč), cíl UNKNOWN |
| Ruční brzda | `PBrakeForce` 5000 (jen zadek, bias 0); `PBrakeBias` 0 (kategorie UNKNOWN — nezapisovat) | adapter §12 | UNKNOWN | PODPOROVÁNO (`PBrakeForce`); `PBrakeBias` PENDING-rozhodnutí |
| Motorová brzda | `EBrakeForce` 500 (v redline) | adapter §5/§12 | UNKNOWN | PODPOROVÁNO (klíč), cíl UNKNOWN |
| ABS práh | `ABSThreshold` 20 SPS (`→0` = brzdy téměř nebrzdí) | adapter §12 | UNKNOWN | PODPOROVÁNO (klíč), bezpečné pásmo prahů ≥ ~5 SPS |
| ABS akce | **plné přerušení** (`tqABS=0`), ne pulzování | audit §12; adapter §12 | sériové ABS Mustang (princip mimo Tune) | PODPOROVÁNO-jako-on/off; pulzní ABS = UNSUPPORTED (`abs_pulse_logic` SCRIPT) |
| TCS | `TCSThreshold` 20 SPS / `TCSGradient` 20 SPS / `TCSLimit` 10 % (vzorec `1−min(max(0,skluz−práh)/gradient,1)×(1−limit)`) | adapter §12 | UNKNOWN | PODPOROVÁNO (klíče); S-02 cyklus č. 1 (trojúhelník prahů) → ručně |

`BrakeBias` je podíl požadavku předku, **ne důkaz brzdné fyziky** — moment určuje `#BV` vzorec s FPS škálováním;
kalibrace až testem, ne přepisem z kotoučů (390/355 jsou INFO, bez Tune protějšku).

## 6. Odpružení a řízení

| Věc | A-Chassis (kit) | Důkaz | Mustang cíl | Status |
|---|---|---|---|---|
| Tuhosti | `FSusStiffness/RSusStiffness` — klíče F4.3, hodnoty `None` (kandidátní dekód 20000, N/m až po Studio-verifikaci) | adapter §8; katalog MUTABLE/PENDING | UNKNOWN | PENDING (bezpečné pásmo 0.25–4×; `< ~5000` = dosedání) |
| Tlumiče | `FSusDamping/RSusDamping` — klíče F4.3, hodnoty `None` (kandidát 500; `Damping=0` = houpání) | adapter §8; katalog MUTABLE/PENDING | UNKNOWN | PENDING (Bump/rebound test) |
| Délky/zdvih | `FSusLength/RSusLength`, `F/RPreCompress`, `F/RExtensionLim`, `F/RCompressLim` — vše `None` (jen odvozené `Free/Max/Min`) | adapter §8 `_u`; vzorce v `notes` | UNKNOWN | PENDING + **S-02 cykly č. 3–4** (trojúhelníky délek) → jen ručně |
| Ramena/geometrie | `FWsBoneLen/RWsBoneLen`, `FSusAngle/RSusAngle` (80 = neaktivní), `F/RAnchorOffset` — neaktivní procedurální větev | adapter §8 (`_u`, „custom větev ji nepoužívá"); `arm_kinematics` `_s` | UNKNOWN (konstrukce S650, dílenský manuál) | UNSUPPORTED (kinematika ramen jen přestavbou dílů/kloubů) |
| Stabilizátory | `FGyroDampening/RGyroDampening` 50 (BodyGyro Stabilizer), `FGyroDamp/RGyroDamp` 100/… (klopení kol) | adapter §8 | UNKNOWN | PODPOROVÁNO (podpůrné, neměnit bez testu) |
| Převod řízení | `SteerRatio` 15, `LockToLock` 2.6 ot. → `SteerOuter` 31.2° | adapter §9 | rejstřík S650 nepublikován | PODPOROVÁNO (klíče), cíl UNKNOWN; **S-02 cyklus č. 12** → ručně |
| Omezení/saturation | `MinSteer` 10 %, `SteerDecay` 330 SPS (nízký = přetáčivé ve vysoké rychlosti) | adapter §9 | UNKNOWN | PODPOROVÁNO |
| Rychlosti | `SteerSpeed` 0.05 °/tick, `ReturnSpeed` 0.1 °/tick, `MSteerExp` 1 | adapter §9 | UNKNOWN (subjektivní/slalom) | PODPOROVÁNO |
| Ackermann | `Ackerman` 0.9 (`SteerInner = min(Outer−(1−A)×Outer, 1.2×Outer)`) | adapter §9 | geometrie přední nápravy S650 | PODPOROVÁNO (klíč), cíl UNKNOWN |
| Zadní řízení | `FWSteer` None (4WS off, zadek weld) | adapter §9 | S650 nemá 4WS (konstrukčně dáno) | ODVOZENO (ponehat None) |
| Typ řízení | `SteeringType` New | adapter §9 | kit-vnitřní přepínač, ne vlastnost vozu | PODPOROVÁNO (test obou větví ve Studiu) |
| Osa řízení | `StAxisOffset` — **klíč v Tune CHYBÍ** | adapter §9 `_u`; `limits()` chyba č. 1 (`Initialize:171`) | UNKNOWN | UNKNOWN-bez-prostředku (blokuje první spuštění) |
| Odklon/záklon/sbíhavost | vše 0°, jen vizuální `CFrame.Angles` | adapter §9 `_s camber_caster_toe` | UNKNOWN | UNSUPPORTED (skutečný odklon jen geometrií) |

## 7. Mapovací tabulka (Mustang parametr | A-Chassis parametr | jednotka | zdroj | status | omezení)

Zdroj cíle = výhradně referenční profil (M1.5, zdroje [1]/[1b] Ford EU tech specs + [3] ADAC, ověřeno 2026-11-19),
`oficiální` = factory, jinak `odhad`/`výpočet`/`CHYBÍ`. Zdroj prostředku = audit § / adapter / katalog / Physics / Sim.

### 7.1 Hmotnost a kola

| Mustang parametr | A-Chassis parametr | Jedn. | Zdroj | Status | Omezení |
|---|---|---|---|---|---|
| `mass.curb_weight` 1808 kg | `Weight` 3439 | lb | profil [1b] (odhad „Est.") / adapter §11 | ADAPTÉR | převod lb↔kg až runtime; cyklus S-02 č. 5 (`weight_lb ↔ weight_box_size`) → ručně |
| `mass.weight_distribution_front_pct` CHYBÍ | `WeightDist` 55 | % | — / adapter §11 | PODPOROVÁNO (klíč), cíl UNKNOWN | bez nápravových vah nelze kalibrovat přetáčivost |
| `mass.cog_height` CHYBÍ | `CGHeight` 0.8 | — | — / adapter §11 | PODPOROVÁNO (klíč), cíl UNKNOWN | bezpečně ≤ ~1.2; špatná výška = převracení |
| rozměry 4810×1916 (INFO) | `WeightBSize` [7.03,5.35,18.11] | studs | profil [1b] oficiální / adapter §11 | PODPOROVÁNO | kvádr musí odpovídat karoserii; viz cyklus č. 5 |
| pneu 255/40 R19 + 275/40 R19, disky 9.0J/9.5J (oficiální) | `FWheelDensity/RWheelDensity` 0.1 | — | profil [1b] oficiální (INFO) / adapter §10 | PODPOROVÁNO (klíč), cíl UNKNOWN | jediný Tune parametr kol je hustota; adheze = skript |
| — (grip 1.0 = Optimizer-předpoklad) | `target_friction` .7+Heat | — | — / adapter §10 `_s` | UNSUPPORTED | žije v `Simulated`, mimo Tune |
| rozvor 2719, rozchod 1585/1642 (oficiální) | `wheelbase_etc` `None` | — | profil [1b] oficiální / adapter §1/§3 | UNSUPPORTED (konstrukce) | geometrie se ladí díly; odečet `Position` do `analyzed/` |
| ⌀ F 686.6 / R 702.6 (výpočet z designace) | `wheel_radius` `None` | — | VEHICLE-SPEC §2 výpočet / adapter §1/§10 | UNSUPPORTED (konstrukce) | páka všech sil; F≠R staggered; odečet `Size` kol |

### 7.2 Motor (hp≠Nm)

| Mustang parametr | A-Chassis parametr | Jedn. | Zdroj | Status | Omezení |
|---|---|---|---|---|---|
| `engine.max_power` 328 kW @ 7250 (oficiální) | `Horsepower` 200 | hp | profil [1b] INFO / adapter §5 | ADAPTÉR | převod kW→hp přes otáčky+křivku nedefinován; přepis zakázán |
| `engine.max_torque` 540 Nm @ 5100 (oficiální) | — (bez protějšku) | Nm | profil [1b] INFO / MAPPING #1 | UNSUPPORTED | `peak_torque_nm` → `rejected`; P=M·ω (`Physics/engine.py`) |
| `torque_curve` prázdná (M1.9) | `PeakRPM` 6800 / `PeakSharpness` 20 / `CurveMult` 0.5 / `EqPoint` 5252 | rpm/— | profil UNKNOWN / adapter §5 | PODPOROVÁNO (klíče), křivka UNKNOWN | tvar = parabola kódem (`curve_shape_func` SCRIPT); body nikdy nedomýšlet |
| `engine.idle_rpm` CHYBÍ | `IdleRPM` 950 (+`IdleThrottle` 3) | rpm | — / adapter §5 | PODPOROVÁNO, cíl UNKNOWN | OBD log / manuál |
| `engine.redline_rpm` CHYBÍ | `Redline` 8000 / `RevBounce` 250 | rpm | — / adapter §5 | PODPOROVÁNO, cíl UNKNOWN | 7250 = bod maxima, ne redline; S-02 cyklus č. 2 (`redline ↔ rev_bounce`) |
| setrvačnost S650 nepublikována | `RevAccel` 250 / `RevDecay` 75 / `Flywheel` 500 | — | — / adapter §5 | PODPOROVÁNO, cíl UNKNOWN | cyklus č. 6 (`flywheel ↔ clutch_engage/rev_accel`) |
| odezva plynu nepublikována | `ThrotAccel` 0.05 / `ThrotDecel` 0.2 / `BrakeAccel` 0.2 / `BrakeDecel` 0.5 / `InclineComp` 1 | — | — / adapter §5 | PODPOROVÁNO, cíl UNKNOWN | měření odezvy plynu |
| atmosféra V8 (oficiální) | `Turbochargers` 2→**0**, `T_Boost` 7→n/a | ks | profil [1b] / adapter §5 | PODPOROVÁNO + ODVOZENO | `KNOWN_DEPENDS` (boost vyžaduje count≥1); cyklus č. 11 (`compression_ratio ↔ turbo_boost`) |
| atmosféra V8 (oficiální) | `Superchargers` 0 | ks | profil [1b] / adapter §5 | PODPOROVÁNO (shoda) | ponechat |
| `engine.compression_ratio` CHYBÍ | `CompressionRatio` (klíč nepotvrzen) | — | — / adapter §5 `_u` | UNKNOWN | jen ve vzorci HP_T; Studio odečet |
| dojížďka nepublikována | `EBrakeForce` 500 | — | — / adapter §12 | PODPOROVÁNO, cíl UNKNOWN | test dojížďky |

### 7.3 Převodovka (MANUÁL; auto-logiku nepřenášet)

| Mustang parametr | A-Chassis parametr | Jedn. | Zdroj | Status | Omezení |
|---|---|---|---|---|---|
| převody 3.237/2.104/1.422/1.0/0.814/0.622 (oficiální) | `Ratios` R3.28/N0/1–6 kit | — | profil [1]/[1b] / adapter §6 | ADAPTÉR | list→dict + jiná sada (DCT-ish vs MT-82); S-02 cyklus č. 10 |
| `reverse_ratio` CHYBÍ (null) | `Ratios.R` 3.28 | — | — / adapter §6 | PODPOROVÁNO (klíč), cíl UNKNOWN | GUARD: null není definitiva |
| `final_drive` null (3.15/3.55 bez přiřazení) | `FinalDrive` 3.545 | — | — / adapter §6 | PODPOROVÁNO (klíč), cíl UNKNOWN | kritické; konflikt FD×FDMult; cyklus č. 10 |
| — (Gauges neutrál) | `FDMult` 1.1→1 | — | audit §6 / adapter §6 | ADAPTÉR | měnit jen samostatně; jen vizuální konflikt |
| `transmission.type` 6MT MT-82 rev-match (oficiální) | `TransModes` [Semi,Manual,Auto] | — | profil [1b] / adapter §6 | ADAPTÉR | Manual-first; `Auto*` větve k revizi |
| řidič řadí (konstrukce 6MT) | `ShiftUpTime` 0.25 / `ShiftDnTime` 0.125 | s | — / adapter §6 | PODPOROVÁNO, cíl UNKNOWN | DCT časy ≠ manuál 1:1; cyklus č. 8 |
| 6MT nemá auto-režim | `AutoShiftMode/Speed`, `AutoShiftType/DCT`, `AutoUpThresh/−200`, `AutoDownThresh/1400` | mix | — / adapter §6 | PODPOROVÁNO, pro manuál IRELEVANTNÍ | nepřenášet Jeep/DCT logiku; cyklus č. 9 |
| 6MT nemá auto-režim | `shift_logic` (Auto/LC kód) | — | — / adapter §6 `_s` | UNSUPPORTED (záměrně) | mění se skriptem; pro manuál nepotřebné |
| rev-matching ≠ kit-větev | `Clutch` True / `ClutchEngage` 10 / `SpeedEngage` 20 / `RPMEngage` 3500 / `Stall` True / `ClutchKick` False | mix | — / adapter §6 | PODPOROVÁNO, cíl UNKNOWN | test rozjezdů/launch; cyklus č. 6 |
| manuál nemá měnič | `TQLock` (bez hodnoty) | — | — / adapter §6 `_u` | UNKNOWN | mimo manuál |

### 7.4 Pohon a diferenciál (RWD)

| Mustang parametr | A-Chassis parametr | Jedn. | Zdroj | Status | Omezení |
|---|---|---|---|---|---|
| RWD + LSD (oficiální) | `Config` AWD→**RWD** | FWD\|RWD\|AWD | profil [1b] / adapter §7 | ADAPTÉR | jeden řízený krok s testem |
| `torque_split_f_r` 0/100 (odhad z RWD) | `TorqueVector` 0 | −1..1 | profil odhad / adapter §7 | ODVOZENO | v RWD irelevantní; závislost `torque_vector → drive_config` |
| LSD obecně (oficiální); typ UNKNOWN (Torsen tabu) | `DifferentialType` New | New\|Old | profil [1b] INFO / adapter §7 | PODPOROVÁNO (klíč), typ UNKNOWN | workshop data S650 |
| n/a (RWD) | `FDiffPower/Coast` 20/20, `FDiffPreload` 20 | 0–100 | odvozeno z RWD / adapter §7 | ODVOZENO | u RWD ignorováno; nemazat bez D |
| svornost nepublikována | `RDiffPower/RDiffCoast` (klíče F4.3, hodnoty 40/30 nepřevzaty) | 0–100 | — / adapter §7 `_u` | PENDING | Studio odečet + test svornosti |
| UNKNOWN | `RDiffPreload` (klíč F4.3, `None`) | 0–100 | — / adapter §7 | PENDING | Studio odečet |
| UNKNOWN | `F/R/C DiffSlipThres`, `F/R/C DiffLockThres` (klíče F4.3, bez hodnot) | — | — / adapter §7 `_u` | PENDING | starý dif ignorován při `New`; konflikty se starými ID jsou neplatná |
| žádný středový dif (RWD) | `center_diff_logic` (kód) | — | — / adapter §7 `_s` | UNSUPPORTED (nepotřebné) | jen skriptem; pro RWD cíl mimo potřebu |

### 7.5 Brzdy a ABS (`BrakeBias ≠ důkaz fyziky`)

| Mustang parametr | A-Chassis parametr | Jedn. | Zdroj | Status | Omezení |
|---|---|---|---|---|---|
| kotouče 390/355 Brembo (oficiální, INFO) | `BrakeForce` 2500 (`#BV` vzorec) | — | profil [1b] INFO / adapter §12 | ADAPTÉR | není Nm; škáluje FPS; kalibrace testem 100–0 |
| `brake_bias_front_pct` CHYBÍ | `BrakeBias` 0.6 | 0–1 | — / adapter §12 | PODPOROVÁNO (klíč), cíl UNKNOWN | extrémy 0/1 rizikové; bias je podíl, ne moment |
| UNKNOWN | `PBrakeForce` 5000 (zadek) | — | — / adapter §12 | PODPOROVÁNO | test ruční brzdy |
| UNKNOWN (hodnota 0 známa, kategorie UNKNOWN) | `PBrakeBias` 0 | — | audit §12 / katalog | PENDING-rozhodnutí | nezapisovat do rozhodnutí koordinátora |
| UNKNOWN | `ABSThreshold` 20 / `TCSThreshold` 20 / `TCSGradient` 20 / `TCSLimit` 10 % | SPS/% | — / adapter §12 | PODPOROVÁNO | prahy ≥ ~5 SPS; plné přerušení `tqABS=0`; S-02 cyklus č. 1 |
| sériové ABS (princip mimo Tune) | `abs_pulse_logic` (kód) | — | — / adapter §12 `_s` | UNSUPPORTED | pulzní ABS jen kódem |

### 7.6 Podvozek, řízení, aero/script (zbytek)

| Mustang parametr | A-Chassis parametr | Jedn. | Zdroj | Status | Omezení |
|---|---|---|---|---|---|
| tuhosti S650 nepublikovány | `FSusStiffness/RSusStiffness` (`None`, kandidát 20000) | N/m | — / adapter §8 | PENDING | Studio odečet + statický prohyb; 0.25–4× |
| tlumiče S650 nepublikovány | `FSusDamping/RSusDamping` (`None`, kandidát 500) | — | — / adapter §8 | PENDING | Bump/rebound test |
| délky/zdvih S650 | `F/RSusLength`, `F/RPreCompress`, `F/RExtensionLim`, `F/RCompressLim` (vše `None`) | — | — / adapter §8 `_u` | PENDING | jen vzorce; S-02 cykly č. 3–4 → ručně |
| ramena S650 (dílenský manuál) | `FWsBoneLen/RWsBoneLen`, `FSusAngle/RSusAngle`, `F/RAnchorOffset` (neaktivní větev) | — | — / adapter §8 `_u` | UNKNOWN (nezapisovat) | custom `SuspensionGeometry` přebíjí; `arm_kinematics` UNSUPPORTED |
| — (stabilizace) | `FGyroDampening/RGyroDampening` 50, `FGyroDamp/RGyroDamp` 100, `SusRadius` 0.2 | — | — / adapter §8 | PODPOROVÁNO (podpůrné) | vzhled pružiny neměnit bez D |
| rejstřík S650 nepublikován | `SteerRatio` 15 / `LockToLock` 2.6 / `MinSteer` 10 / `SteerSpeed` 0.05 / `ReturnSpeed` 0.1 / `SteerDecay` 330 / `Ackerman` 0.9 | mix | — / adapter §9 | PODPOROVÁNO (klíče), cíl UNKNOWN | `SteerOuter` 31.2° odvozeně; S-02 cyklus č. 12 → ručně |
| S650 nemá 4WS (konstrukce) | `FWSteer` None | — | odhad konstrukcí / adapter §9 | ODVOZENO | ponechat None |
| kit-přepínač | `SteeringType` New | — | — / adapter §9 | PODPOROVÁNO | test obou větví ve Studiu |
| — | `StAxisOffset` (klíč v Tune CHYBÍ) | — | — / adapter §9 `_u` | UNKNOWN-bez-prostředku | **chyba č. 1** (`Initialize:171`); blokuje první spuštění |
| vše 0° (vizuální) | `camber_caster_toe` | ° | — / adapter §9 `_s` | UNSUPPORTED | jen `CFrame.Angles`; skutečný odklon geometrií |
| Cd/plocha CHYBÍ | `drag_coeff` .34 (konstanta) | — | — / adapter §13 `_s` | UNSUPPORTED | **chyba č. 2** (`magnitude`); V-max až po opravě |
| tunelová data neexistují | `downforce_f/r` 125/150 (konstanty) | — | — / adapter `_s` §13 | UNSUPPORTED | jen kódem; V-max 250 km/h je validační cíl, ne vstup |
| testy prokluzu/opotřebení | `wheel_lock_ratio`, `wheelspin_ratio`, `wear_speed` | — | — / adapter §10 `_s` | UNSUPPORTED | režimy v `Simulated` |
| mimo manuál / vzhled | `tq_lock`, `spring_color` | — | — / adapter `_u` | UNKNOWN / mimo rozsah | Studio odečet nízké priority |

## 8. Brána S-02 (cykly blokují auto-map)

Platí nález Agenta A: **12 komponent SCC / 19 vzájemných párů / 101 hran `depends_on`** (0 neplatných cílů v
`depends_on`, 5 neplatných cílů v `conflicts`, `KNOWN_DEPENDS` pokrývá ~1 % hran, `KNOWN_CONFLICTS` FD×FDMult
v katalogu zcela chybí a katalog místo něj tvrdí závislost opačným směrem v cyklu č. 10).
Pro tuto mapu jsou relevantní cykly: **č. 10** převodovka (`final_drive ↔ gear_ratios ↔ final_drive_mult`) ·
**č. 3–4** pružiny F/R (trojúhelníky `sus_length ↔ pre_compress/compress_lim/extension_lim`) ·
**č. 12** řízení (`lock_to_lock ↔ steer_ratio`) · **č. 2** (`redline ↔ rev_bounce`) · **č. 1** TCS trojúhelník ·
**č. 7** (`pbrake_bias ↔ pbrake_force`) · **č. 11** (`compression_ratio ↔ turbo_boost`) · **č. 6** spojka/setrvačnost ·
**č. 8–9** auto-řazení · **č. 5** hmotnost (`weight_lb ↔ weight_box_size`).
Důsledek (MAPPING §4 + `map_config`): automatické mapování je přípustné **pouze pro acyklické `MUTABLE_TUNE` + `PASS`**;
každý parametr v cyklu výše → stav faktického `BLOCKED` pro auto-map, **pouze ruční převod s odůvodněním**,
jeden parametr po druhém (konflikt FD×FDMult: `FDMult` měnit jen samostatně). `conflicts` nejsou cykly a jako cykly
se nevyhodnocují (klasifikace S-02 §6). V této zprávě není navržena žádná změna závislostí ani kódu (M3 CLOSED).

## 9. Kritické mezery pro manuální RWD Mustang (seřazeno podle blokace)

1. **Výkonový převod nedefinován** — 328 kW @ 7250 / 540 Nm @ 5100 nelze vepsat do `Horsepower` 200 hp
   (`hp≠Nm`, jiný referenční bod) + křivka `points: []` (M1.9). Bez převodu + křivky stojí motorová kalibrace. → M4 / Agent D.
2. **Stálý převod nerozhodnut** — 3.15:1 vs 3.55:1 (GUARD zakazuje null). Stojí na něm celá kalibrace převodovky. → Ford CZ/DE konfigurátor / workshop S650.
3. **Zpátečka, redline, volnoběh UNKNOWN** — profil je nemá; `Ratios.R` klíč existuje, cílová hodnota ne.
4. **RWD přepnutí + zadní dif** — `Config` AWD→RWD jako řízený krok; `RDiffPower/Coast`, `RDiffPreload`,
   prahy `Slip/LockThres` vše PENDING (Studio + test svornosti); přesný typ LSD UNKNOWN (Torsen tabu).
5. **Tuhosti/tlumiče/délky PENDING** — `FSusStiffness/Damping` klíče F4.3 bez hodnot (kandidáty 20000/500 nepřevzaty);
   délky/limity jen vzorce + cykly → ručně po Studio-odečtu.
6. **`StAxisOffset` chyba č. 1** — verdikt před prvním během ve Studiu, jinak hrozí runtime error `Initialize:171`.
7. **`magnitude` chyba č. 2** — odpor vzduchu se nikdy neaplikuje; V-max (validační cíl 250 km/h) měřit až po opravě
   (1 znak, Engineering — mimo tuto zprávu).
8. **Brzdy ke kalibraci testem** — `BrakeForce` není Nm (FPS škálování `#BV`); bias CHYBÍ v profilu; 0–100 za 5.3 s je
   validační cíl, ne vstup.
9. **Geometrie je konstrukce, ne parametr** — rozvor/rozchod/poloměry (rozměry oficiální, ⌀ výpočet) se promítají
   přestavbou dílů, ne Tune; automatická auto-map je pro ně tabu (S-02).
10. **Auto-logiku nepřenášet** — `AutoShift*`, `shift_logic`, DCT časy a Jeep-šasi předpoklady (50:50 AWD) se na MT-82
    RWD nevztahují; `TransModes` Manual-first + spojkové klíče se kalibrují jízdním testem, ne kopií kitu.

## 10. Předání

- **Agent D (wiring):** strukturální konverze `Ratios` list→dict s R/N; `TransModes` Manual-first; `peak_torque_nm` /
  `peak_power_kw` stále bez Tune protějšku (odmítnout, ne tiše převést); převod lb→kg do runtime vrstvy.
- **M4 (kalibrace):** čeká na Studio-odečty (§7.6, §7.4) + rozhodnutí převodu motoru (§7.2) + stálý převod (§7.3);
  validační cíle 5.3 s / 250 km/h připraveny (ne vstupy).
- **Opakovatelnost:** počty ověřeny skriptem nad `parameters.json` (138 záznamů: 82/14/2/3/37; PENDING kontrola);
  profil `ford-mustang-gt-2024-eu-manual-standard.json` beze změny; tento soubor je jediný výstup.
