# Agent F — Rekonstrukce puvodnich 60 ID (verdikt: varianta B)

**Vetev:** `nw-f-60ids` - **HEAD:** `57043ee` (vychozi bod prace; strom cisty, overeno `git status`) - **Datum:** 2026-11-20
**Pravidla:** cesky; identifikatory anglicky. Cteno vse, meneno nic - krome tohoto souboru.
Katalog / RBXM / schemata / `src` / `main` / PR#2 / M3: nedotceny. Zadna odhadnuta ID: zadne `original_id` nebylo vymysleno.

## 1. Verdikt

**Varianta B - `ORIGINAL_60_SET=NOT_RECONSTRUCTABLE`.**

Seznam "puvodnich 60 ID" neexistuje v zadnem commitu, souboru ani schematu teto historie.
Jediny vyskyt cisla 60 je deklarativni agregat v S1 mapovaciho reportu Agenta F (prvni vyskyt commit `557ee39`, viz S2) - bez seznamu ID, bez metody vyberu, bez stavu na ID.
Strojove dolozeno je pouze: **78 radku** tabulek (S2.1-S2.10) -> **94 normalizovanych ID** (audit Agenta E, validator PASS na vse krome "60 dolozeno seznamem").
Zadny matematicky reprodukovatelny prevod 78/94/138 -> prave 60 se nepodarilo dolozit zdrojem (vsechny pokusy viz S4 - kazdy aritmeticky sedi jen nahodou a micha jednotky).
Nezavisly ctenar z tohoto reportu zjisti: (a) kde se cislo 60 vzalo a co o nem tvrdil zdroj, (b) proc z nej nelze sestavit seznam ID, (c) co presne chybi a jaky rozsah ho nahrazuje.

Klicovy dukaz v jedne vete: cislo 60 vzniklo v commitu `557ee39` (`wave(s02-mustang)`), soubor `reports/NIGHT-WORK/AGENT-F-MUSTANG-PHYSICS-MAPPING.md`, radky 34-40 (blob `b5f95b1...`), jako textova deklarace bez seznamu - a v cele nasledujici historii (`0f7c968`, `31f1180`, `57043ee`) uz ho zadny commit seznamem nedoplnil, naopak audity E/E-norm ho oznacily za nedolozeny (U3).

## 2. Kde se cislo 60 vzalo (git historie, jen fakta)

| Krok | Commit | Soubor@radky | Blob SHA | Co se stalo s cislem 60 |
|---|---|---|---|---|
| 1. vznik | `557ee39` `wave(s02-mustang)` (2026-11-20 10:48) | `reports/NIGHT-WORK/AGENT-F-MUSTANG-PHYSICS-MAPPING.md` L34-40 (tehdy cely soubor 224 radku) | `b5f95b1946efc8ace0e68662b76e31b292726c91` (`git rev-parse 557ee39:<cesta>`) | Prvni a jediny puvod: "Mapovanych parametru: 60 (jizdne relevantni vyber ze 138 zaznamu katalogu; elektro-vetev 9x a vizualni/zvukove vynechany, viz S4)" + "S dolozenym cilem 10 (7 VERIFIED / 3 ESTIMATED)" + "UNKNOWN 50" + rozpad "7 / 3 / 22 / 28". Zadny seznam ID, zadna metoda vyberu 60 ze 138 v souboru neni. Overeno `git log --diff-filter=A` (soubor predtim neexistoval) a `git show 557ee39:<cesta>` L32-42. |
| 2. uprava | `0f7c968` `qa: remediate S-02 tests and audit counts` (2026-11-20 13:38) | tyz soubor, L39-40 + L135 | `b5f95b1... -> 4d4d7650ba4ad095815d3b5caaca711b62138c31` | Jen oprava souctu: PENDING 22->21, `compression_ratio` PENDING->UNKNOWN (stav cile). Cislo 60 beze zmeny, seznam nedoplnen. Diff 6 radku, overeno `git show 0f7c968 -- <cesta>`. |
| 3. audit | `31f1180` `e(data): normalizace 60/78 + validace` | `reports/NIGHT-WORK/AGENT-E-NORMALIZED-CATALOG-AUDIT.md` (119 radku) + `reports/NIGHT-WORK/normalized_ids.json` (94 zaznamu) | audit-blob viz S3 | 60 **nepotvrzeno**: "60 ID NEDOLOZENO... Agregat 60 ani rozpad 7/3/21/28 nelze reprodukovat - viz U3. Zadna umela ID nebyla vytvorena." Strojove dolozeno 78 radku / 94 ID; validator hlasi `[PENDING] deklarovanych 60 ID dolozeno seznamem - deklarovano 60, odvozeno 94`. |
| 4. stav | `57043ee` (HEAD teto prace) | beze zmeny | F-blob stale `4d4d7650...` | 60 zustava holou deklaraci. `git log -S"Mapovanych parametru"` ani `-G"60"` neodhalily zadny starsi ani paralelni zdroj cisla 60 (pred `557ee39` soubor neexistoval; ostatni vyskyty "60" v historii jsou nesouvisejici pocty). |

Pozn.: F-report sam sebe v L3 pinoval na vetev `feat/m2-m3-geometry` @ `90a1f63` - tento pin je dobovy udaj zdroje, ne tvrzeni teto rekonstrukce (overeno, ze soubor vznikl az v `557ee39`; rozpor pinu ponechan jako fakt k auditu, neopravovan - cizi soubor).

## 3. Vstupni zdroje (kazdy: blob SHA, cesta, radky, primarni/odvozeny)

| # | Soubor | Blob SHA (`git hash-object`, pracovni strom @57043ee) | Rozsah | Role | Co z nej pochazi |
|---|---|---|---|---|---|
| [F] | `reports/NIGHT-WORK/AGENT-F-MUSTANG-PHYSICS-MAPPING.md` | `4d4d7650ba4ad095815d3b5caaca711b62138c31` | 224 radku; deklarace L34-40, vyluky S4 L192-199, tabulky L50-174 | **primarni** (deklarace 60) | cislo 60, rozpad 7/3/21/28, 78 radku tabulek, S4-vyluky |
| [E1] | `reports/NIGHT-WORK/AGENT-E-MUSTANG-DATA-AUDIT.md` | `c99af17d33ff3da501f64162515a42140a1f8e2e` (shodny s blobem citovanym v [E2] - soubor se od auditu nezmenil) | 228 radku; prepocet S3 L172-199 | **primarni** (nezavisly prepocet) | 78 radku strojove; stavovy prepocet radku 6/7/21/44; nalezy N-F1 az N-F3 (60 vs 78, agregaty nedolozeny) |
| [E2] | `reports/NIGHT-WORK/AGENT-E-NORMALIZED-CATALOG-AUDIT.md` | `90b17a00a783a2221451dd97e2b989bac376aeac` | 119 radku; pravidla R1-R8 L35-61, verdikt L112-119 | **primarni** (metoda) + odvozena data | pravidla normalizace R1-R8; vyrok U3 (60 nedolozeno); agregace radky 6/7/20/45, ID 7/8/25/54 |
| [N] | `reports/NIGHT-WORK/normalized_ids.json` | `7a46818c07ac2f2ad65af1c1db899c42900a0c30` | 1648 LF-radku (1 JSON dok.); klice `meta/rules/ids(94)/unresolved(4)` | **odvozeny** (strojovy, validovany) | 94 `logical_id` + `source_rows` + `primary_name` + `aliases` + `status` + `evidence`; `unresolved` U1-U4 |
| [K] | `src/Chassis/catalog/parameters.json` | `8f4d6bd1edcffd9121d0c6bad87fbd97b5285d0b` | 3444 LF-radku; **138 zaznamu** (list objektu `id/tune_key/...`) | **primarni** (katalog) | 11x `electric_*` (ne 9 - viz S4/C2); 44 katalogovych ID mimo normalizaci (vycet S4/C3); kandidati `clutch_*` jen 3 ze 6 |
| [M] | `vehicle-data/references/ford-mustang-gt-2024-eu-manual-standard.json` | `68832c3462fecbcb5fe5c27759574a0399e0e6a7` | 1 LF-radek (single-line JSON, 27750 znaku); 14 top-level klicu | **primarni** (zdroj pravdy cilu) | mustangovske cile (rozvor, vykon, prevody...); sam o sobe zadne "60" neobsahuje |
| [V] | `docs/VEHICLE-SPECIFICATIONS.md` | `26f5bb4a5b4cddf3faa7c6ef4af0e6dba6ca5d96` | 92 LF-radku | **odvozeny** (kompilat M1.5) | lidsky citelny souhrn k [M]; zadne "60" |

Overeni shody: `git hash-object` vsech sedmi cest spusten v tomto worktree; [F] a [E1] bloby se shoduji s citacemi v [E2] (tj. audity cetly presne tyto verze). `parameters.json` je list o 138 prvcich (overeno `json.load`), `electric_*` = 11 (vycet: `electric_enabled, electric_gauge_names, electric_end_mult, electric_end_percent, electric_front_mult, electric_redline, electric_torque, electric_torque_end_mult, electric_torque_end_percent, electric_trans1, electric_trans2`).

## 4. Proc ani varianta C neobstoji (vsechny reprodukovatelne prevody vyzkouseny a zamitnuty)

Pozadavek varianty C: prevod musi byt nejen aritmeticky presny, ale dolozeny zdrojem (tj. zdroj musi rikat, ze TATO uroven je tech 60). Kazdy pokus nize je strojove spocten z [N]/[K]/[F] a kazdy selhava na chybejicim dolozeni:

| Hypoteza | Vypocet (overeno skriptem) | Vysledek | Proc zamitnuto |
|---|---|---|---|
| C1: 60 = 138 - 78 (katalog minus radky) | 138 - 78 = 60 presne | aritmetika sedi | micha jednotky: 78 jsou **radky**, ne vyloucena katalogova ID (radky obsahuji pseudo-ID `wheelbase_etc`, `wheel_radius`, `camber_caster_toe`, jez v [K] nejsou). [F] S4 navic 78 vyloucenych nepopisuje - jmenuje jen ~21. Zdroj rovnost nikdy netvrdi. |
| C2: 60 = 94 - 34 (ID minus expandovani clenove skupin) | 94 - 34 = 60 presne (34 = soucet clenu 9 skupinovych bunek dle R2) | aritmetika sedi | operace "odecti vsechny expandovane cleny" nema oporu v zadnem zdroji; je to ucelove zvolena mnozina prave tak, aby vyslo 60. |
| C3: 60 = 138 - 78 vyloucenych (vyber z katalogu) | katalogovych ID mimo [N] je **44** (vycet nize), ne 78 | **nesedi ani aritmeticky** (138 - 44 = 94) | [F] S4 tvrdi vylouceni "elektro-vetve 9x", ale [K] obsahuje 11x `electric_*`; ani opraveny pocet (11) rovnici na 78 vyloucenych nedotahne. Vyber 60 ze 138 je popsan neuplne ([E2] S1). |
| C4: 60 = slouceni F/R-L/R paru a skupin do "logickych parametru" | [E1] S3: "78 radku je priblizne 60 logickych parametru" - ale bez seznamu, ktery radek se s jakym slucuje | nedolozeno | samotne [E1] N-F1/N-F3 tento prevod stahuje jako nedolozeny; smer je navic podezrely (rozbaleni skupin pocet **zvysuje** 78->94, ne snizuje na 60). |
| C5: 60 = 78 radku minus ~18 ne-katalogovych | pseudo-ID bez [K]-protejsku jsou 3 (`wheelbase_etc`, `wheel_radius`, `camber_caster_toe`), ne 18; 78 - 3 = 75, ne 60 | **nesedi** | - |

44 katalogovych ID mimo normalizaci [N] (tj. skutecne "vynechana" dle [K] prunik [N], overeno skriptem): `abs_pulse_logic, arm_kinematics, auto_down_thresh, auto_shift_mode, auto_shift_type, auto_up_thresh, axle_density, axle_size, brake_accel, brake_decel, center_diff_logic, curve_shape_func, electric_enabled, electric_end_mult, electric_end_percent, electric_front_mult, electric_gauge_names, electric_redline, electric_torque, electric_torque_end_mult, electric_torque_end_percent, electric_trans1, electric_trans2, engine_enabled, front_gyro_damp, front_gyro_dampening, idle_throttle, incline_comp, legacy_wheel_density_f, legacy_wheel_density_r, mouse_steer_exp, rear_gyro_damp, rear_gyro_dampening, rpm_engage, shift_logic, speed_engage, spring_color, stall_enabled, supercharger_sensitivity, sus_radius, tq_lock, turbo2_boost_lag, turbo_boost_lag, wind_volume`.
Zaver S4: zadna hypoteza nema oporu ve zdroji -> varianta C se nekoná; plati B. (Dve presne shody C1/C2 eviduji jako numericke koincidence, ne jako dukaz.)

## 5. Mapovaci tabulka (94 dolozenych ID; `original_id` = NEDOLOZENO u vsech - nic nevymysleno)

Sloupce: `original_id` (clen "puvodnich 60" - pro vsechna ID hodnota `-`, protoze seznam neexistuje) | `logical_id` ([N], totiz presny retezec z bunky Interni ID po R2-rozbaleni) | `source_file` | `source_line` (1. `source_rows` z [N]) | `catalog_id` ([K], shoda retezce) | `tune_key` ([K]/alias [F]) | `relationship` | `status` ([N] R7 - stav mapovani, ne cisty stav cile) | `evidence` | `notes`.
`relationship` je u vsech 94 radku `UNRESOLVED` (vztah k "original_60" nelze urcit, protoze mnozina "original_60" neni definovana). `catalog_id` = `-` tam, kde ID v [K] neni (pseudo-ID, R4).

| original_id | logical_id | source_file | source_line | catalog_id | tune_key | relationship | status | evidence | notes |
|---|---|---|---|---|---|---|---|---|---|
| - | `abs_threshold_sps` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L122 | abs_threshold_sps | ABSThreshold | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `ackermann` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L106 | ackermann | Ackerman | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `anchor_offset_f` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L91 | anchor_offset_f | FAnchorOffset | UNRESOLVED | PENDING | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `anchor_offset_r` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L92 | anchor_offset_r | RAnchorOffset | UNRESOLVED | PENDING | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `brake_bias_front` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L116 | brake_bias_front | BrakeBias | UNRESOLVED | UNKNOWN | UNKNOWN (profil: `CHYBÍ`, rozdělení účinku EU GT nepublikováno); —; — | 1 řádek = 1 ID (R1). |
| - | `brake_force` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L115 | brake_force | BrakeForce | UNRESOLVED | UNKNOWN | UNKNOWN (kotouče F 390×36 / R 355×28 Brembo doloženy, ale `BrakeForce` není moment v Nm — škáluje se FPS a rež | 1 řádek = 1 ID (R1). |
| - | `camber_caster_toe` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L71 | camber_caster_toe | (odklon/záklon/sbíhavost) | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `cg_height` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L54 | cg_height | CGHeight | UNRESOLVED | UNKNOWN | UNKNOWN; — (profil: `CHYBÍ`); — | 1 řádek = 1 ID (R1). |
| - | `clutch_enabled` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L152 | clutch_enabled | Clutch | UNRESOLVED | UNKNOWN | UNKNOWN (rev-matching MT-82 ≠ žádná kit-větev 1:1); —; — | Skupinový řádek Clutch; na ID mapovány jen podnázvy s katalogovým ID. Podnázvy rpm/speed/stall katalogové ID n |
| - | `clutch_engage` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L152 | clutch_engage | ClutchEngage | UNRESOLVED | UNKNOWN | UNKNOWN (rev-matching MT-82 ≠ žádná kit-větev 1:1); —; — | Skupinový řádek Clutch; na ID mapovány jen podnázvy s katalogovým ID. Podnázvy rpm/speed/stall katalogové ID n |
| - | `clutch_kick` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L152 | clutch_kick | ClutchKick | UNRESOLVED | UNKNOWN | UNKNOWN (rev-matching MT-82 ≠ žádná kit-větev 1:1); —; — | Skupinový řádek Clutch; na ID mapovány jen podnázvy s katalogovým ID. Podnázvy rpm/speed/stall katalogové ID n |
| - | `compress_lim_f` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L87 | compress_lim_f | FCompressLim | UNRESOLVED | PENDING | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `compress_lim_r` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L88 | compress_lim_r | RCompressLim | UNRESOLVED | PENDING | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `compression_ratio` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L135 | compression_ratio | CompressionRatio | UNRESOLVED | UNKNOWN | UNKNOWN (profil: `CHYBÍ`; klíč auditem nepotvrzen, jen ve vzorci HP_T); —; — | 1 řádek = 1 ID (R1). |
| - | `curve_mult` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L131 | curve_mult | CurveMult | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `damper_f` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L79 | damper_f | FSusDamping | UNRESOLVED | PENDING | UNKNOWN; —; neověřený předpoklad | 1 řádek = 1 ID (R1). |
| - | `damper_r` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L80 | damper_r | RSusDamping | UNRESOLVED | PENDING | UNKNOWN; —; neověřený předpoklad | 1 řádek = 1 ID (R1). |
| - | `diff_preload_f` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L164 | diff_preload_f | FDiffPreload | UNRESOLVED | ESTIMATED | n/a (RWD); odvozeno z RWD; odhad | 1 řádek = 1 ID (R1). |
| - | `diff_preload_r` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L165 | diff_preload_r | RDiffPreload | UNRESOLVED | PENDING | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `differential_type` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L159 | differential_type | DifferentialType | UNRESOLVED | UNKNOWN | UNKNOWN mapování — LSD potvrzeno obecně, přesný typ UNKNOWN (není automaticky Torsen; Torsen = Dark Horse, do  | 1 řádek = 1 ID (R1). |
| - | `downforce_f` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L173 | downforce_f | — | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | Buňka slučuje přítlak přední/zadní nápravy; odlišné skriptové konstanty. Stav děděn z řádku (mapovací stav, vi |
| - | `downforce_r` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L173 | downforce_r | — | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | Buňka slučuje přítlak přední/zadní nápravy; odlišné skriptové konstanty. Stav děděn z řádku (mapovací stav, vi |
| - | `drag_coeff` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L172 | drag_coeff | (Drag) | UNRESOLVED | UNKNOWN | UNKNOWN (profil: Cd `CHYBÍ`, plocha `CHYBÍ`); —; — | 1 řádek = 1 ID (R1). |
| - | `drive_config` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L158 | drive_config | Config | UNRESOLVED | VERIFIED | RWD ("Front-engine, Rear-wheel drive with limited-slip differential"); profil `drivetrain` ([1b]); oficiální z | 1 řádek = 1 ID (R1). |
| - | `engine_brake_force` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L141 | engine_brake_force | EBrakeForce | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `eq_point` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L132 | eq_point | EqPoint | UNRESOLVED | UNKNOWN | UNKNOWN (kit-vnitřní převodní bod HP↔lb-ft); —; — | 1 řádek = 1 ID (R1). |
| - | `extension_lim_f` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L85 | extension_lim_f | FExtensionLim | UNRESOLVED | PENDING | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `extension_lim_r` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L86 | extension_lim_r | RExtensionLim | UNRESOLVED | PENDING | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `final_drive` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L148 | final_drive | FinalDrive | UNRESOLVED | UNKNOWN | UNKNOWN — kandidáti 3.15:1 / 3.55:1 bez přiřazení k EU 6MT (GUARD T17: null jako definitivu nepoužít); profil  | 1 řádek = 1 ID (R1). |
| - | `final_drive_mult` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L149 | final_drive_mult | FDMult | UNRESOLVED | VERIFIED | 1 (neutrál pro Gauges; měnit jen samostatně); audit §6; oficiální zdroj (audit) | 1 řádek = 1 ID (R1). |
| - | `flywheel` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L137 | flywheel | Flywheel | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `front_diff_coast` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L161 | front_diff_coast | FDiffCoast | UNRESOLVED | ESTIMATED | n/a (RWD — přední dif neexistuje); odvozeno z RWD; odhad | Buňka slučuje 2 Tune klíče předního diferenciálu; u RWD irelevantní, stav ESTIMATED (odvozeno z RWD). Stav děd |
| - | `front_diff_power` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L161 | front_diff_power | FDiffPower | UNRESOLVED | ESTIMATED | n/a (RWD — přední dif neexistuje); odvozeno z RWD; odhad | Buňka slučuje 2 Tune klíče předního diferenciálu; u RWD irelevantní, stav ESTIMATED (odvozeno z RWD). Stav děd |
| - | `front_wheel_density` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L68 | front_wheel_density | FWheelDensity | UNRESOLVED | UNKNOWN | UNKNOWN (disk 19×9.0J + 255/40 R19 doloženy, ale hustota je kit-vnitřní škálování, ne fyzikální údaj); profil  | 1 řádek = 1 ID (R1). |
| - | `front_wheel_steer` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L107 | front_wheel_steer | FWSteer | UNRESOLVED | ESTIMATED | None (S650 nemá 4WS); odvozeno z konstrukce vozu; odhad (konstrukčně dáno) | 1 řádek = 1 ID (R1). |
| - | `front_wishbone_len` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L93 | front_wishbone_len | FWsBoneLen | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `gear_ratios` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L147 | gear_ratios | Ratios | UNRESOLVED | VERIFIED | 1: 3.237 / 2: 2.104 / 3: 1.422 / 4: 1.0 / 5: 0.814 / 6: 0.622 (Getrag MT-82); zpátečka UNKNOWN; profil `transm | 1 řádek = 1 ID (R1). |
| - | `horsepower` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L128 | horsepower | Horsepower | UNRESOLVED | UNKNOWN | UNKNOWN — 328 kW (446 PS) @ 7250 doloženo, ale `peak_power_kw ≠ horsepower` bez definovaného převodu (jiná vel | 1 řádek = 1 ID (R1). |
| - | `idle_rpm` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L133 | idle_rpm | IdleRPM | UNRESOLVED | UNKNOWN | UNKNOWN (profil: `CHYBÍ`); —; — | 1 řádek = 1 ID (R1). |
| - | `lock_thresh_c` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L166 | lock_thresh_c | CDiffLockThres | UNRESOLVED | PENDING | UNKNOWN (Starý dif ignorován při `DifferentialType=New`; live-klíče potvrzeny F4.3, hodnoty neuvedeny); audit  | Buňka slučuje 6 prahových klíčů (slip ×3 + lock ×3); každý je vlastní katalogové ID. Stav děděn z řádku (mapov |
| - | `lock_thresh_f` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L166 | lock_thresh_f | FDiffLockThres | UNRESOLVED | PENDING | UNKNOWN (Starý dif ignorován při `DifferentialType=New`; live-klíče potvrzeny F4.3, hodnoty neuvedeny); audit  | Buňka slučuje 6 prahových klíčů (slip ×3 + lock ×3); každý je vlastní katalogové ID. Stav děděn z řádku (mapov |
| - | `lock_thresh_r` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L166 | lock_thresh_r | RDiffLockThres | UNRESOLVED | PENDING | UNKNOWN (Starý dif ignorován při `DifferentialType=New`; live-klíče potvrzeny F4.3, hodnoty neuvedeny); audit  | Buňka slučuje 6 prahových klíčů (slip ×3 + lock ×3); každý je vlastní katalogové ID. Stav děděn z řádku (mapov |
| - | `lock_to_lock` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L101 | lock_to_lock | LockToLock | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `min_steer` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L102 | min_steer | MinSteer | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `pbrake_bias` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L118 | pbrake_bias | PBrakeBias | UNRESOLVED | UNKNOWN | UNKNOWN (hodnota 0 ověřena, název live-klíče potvrzen F4.3); audit §12; — | 1 řádek = 1 ID (R1). |
| - | `pbrake_force` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L117 | pbrake_force | PBrakeForce | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `peak_rpm` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L129 | peak_rpm | PeakRPM | UNRESOLVED | UNKNOWN | UNKNOWN — 7250 rpm je bod maxima výkonu, ne vrchol kit-křivky `CurveN`; profil `engine.max_power_rpm` — INFO;  | 1 řádek = 1 ID (R1). |
| - | `peak_sharpness` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L130 | peak_sharpness | PeakSharpness | UNRESOLVED | UNKNOWN | UNKNOWN (křivka nepublikována); profil `torque_curve`: `points: []`, status UNKNOWN; — | 1 řádek = 1 ID (R1). |
| - | `pre_compress_f` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L83 | pre_compress_f | FPreCompress | UNRESOLVED | PENDING | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `pre_compress_r` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L84 | pre_compress_r | RPreCompress | UNRESOLVED | PENDING | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `rear_diff_coast` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L163 | rear_diff_coast | RDiffCoast | UNRESOLVED | PENDING | UNKNOWN (viz výše); audit §7; neověřený předpoklad | 1 řádek = 1 ID (R1). |
| - | `rear_diff_power` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L162 | rear_diff_power | RDiffPower | UNRESOLVED | PENDING | UNKNOWN (LSD potvrzeno, hodnoty 40/30 jen zadek-bez-klíčů → live-klíč potvrzen F4.3, hodnota PENDING); audit § | 1 řádek = 1 ID (R1). |
| - | `rear_wheel_density` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L69 | rear_wheel_density | RWheelDensity | UNRESOLVED | UNKNOWN | UNKNOWN (disk 19×9.5J + 275/40 R19 doloženy, viz výše); profil `wheels_tires.*` ([1b]) — INFO; — | 1 řádek = 1 ID (R1). |
| - | `rear_wishbone_len` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L94 | rear_wishbone_len | RWsBoneLen | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `redline_rpm` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L134 | redline_rpm | Redline | UNRESOLVED | UNKNOWN | UNKNOWN (profil: `CHYBÍ`); —; — | 1 řádek = 1 ID (R1). |
| - | `return_speed` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L104 | return_speed | ReturnSpeed | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `rev_accel` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L136 | rev_accel | RevAccel | UNRESOLVED | UNKNOWN | UNKNOWN (setrvačnost pohonu S650 nepublikována); —; — | Buňka slučuje 3 samostatné Tune klíče (RevAccel/Decay/Bounce); každý je vlastní katalogové ID s odlišnou funkc |
| - | `rev_bounce` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L136 | rev_bounce | RevBounce | UNRESOLVED | UNKNOWN | UNKNOWN (setrvačnost pohonu S650 nepublikována); —; — | Buňka slučuje 3 samostatné Tune klíče (RevAccel/Decay/Bounce); každý je vlastní katalogové ID s odlišnou funkc |
| - | `rev_decay` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L136 | rev_decay | RevDecay | UNRESOLVED | UNKNOWN | UNKNOWN (setrvačnost pohonu S650 nepublikována); —; — | Buňka slučuje 3 samostatné Tune klíče (RevAccel/Decay/Bounce); každý je vlastní katalogové ID s odlišnou funkc |
| - | `shift_down_time` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L151 | shift_down_time | ShiftDnTime | UNRESOLVED | UNKNOWN | UNKNOWN (manuál řadí řidič; časy DCT neaplikovatelné 1:1); —; — | Buňka slučuje časy řazení nahoru/dolů; odlišné Tune klíče. Stav děděn z řádku (mapovací stav, viz R7). |
| - | `shift_up_time` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L151 | shift_up_time | ShiftUpTime | UNRESOLVED | UNKNOWN | UNKNOWN (manuál řadí řidič; časy DCT neaplikovatelné 1:1); —; — | Buňka slučuje časy řazení nahoru/dolů; odlišné Tune klíče. Stav děděn z řádku (mapovací stav, viz R7). |
| - | `slip_thresh_c` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L166 | slip_thresh_c | CDiffSlipThres | UNRESOLVED | PENDING | UNKNOWN (Starý dif ignorován při `DifferentialType=New`; live-klíče potvrzeny F4.3, hodnoty neuvedeny); audit  | Buňka slučuje 6 prahových klíčů (slip ×3 + lock ×3); každý je vlastní katalogové ID. Stav děděn z řádku (mapov |
| - | `slip_thresh_f` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L166 | slip_thresh_f | FDiffSlipThres | UNRESOLVED | PENDING | UNKNOWN (Starý dif ignorován při `DifferentialType=New`; live-klíče potvrzeny F4.3, hodnoty neuvedeny); audit  | Buňka slučuje 6 prahových klíčů (slip ×3 + lock ×3); každý je vlastní katalogové ID. Stav děděn z řádku (mapov |
| - | `slip_thresh_r` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L166 | slip_thresh_r | RDiffSlipThres | UNRESOLVED | PENDING | UNKNOWN (Starý dif ignorován při `DifferentialType=New`; live-klíče potvrzeny F4.3, hodnoty neuvedeny); audit  | Buňka slučuje 6 prahových klíčů (slip ×3 + lock ×3); každý je vlastní katalogové ID. Stav děděn z řádku (mapov |
| - | `steer_axis_offset` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L109 | steer_axis_offset | (StAxisOffset) | UNRESOLVED | PENDING | UNKNOWN — klíč v live Tune **CHYBÍ**, `Initialize:171` ho čte (chyba č. 1); —; — | 1 řádek = 1 ID (R1). |
| - | `steer_decay` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L105 | steer_decay | SteerDecay | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `steer_ratio` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L100 | steer_ratio | SteerRatio | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `steer_speed` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L103 | steer_speed | SteerSpeed | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `steering_type` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L108 | steering_type | SteeringType | UNRESOLVED | UNKNOWN | UNKNOWN (kit-vnitřní přepínač, ne vlastnost vozu); —; — | 1 řádek = 1 ID (R1). |
| - | `supercharger_count` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L140 | supercharger_count | Superchargers | UNRESOLVED | VERIFIED | 0 (atmosféra, shoda s kitem); profil `engine.code` ([1b]); oficiální zdroj | 1 řádek = 1 ID (R1). |
| - | `sus_angle_f` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L89 | sus_angle_f | FSusAngle | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `sus_angle_r` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L90 | sus_angle_r | RSusAngle | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `sus_length_f` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L81 | sus_length_f | FSusLength | UNRESOLVED | PENDING | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `sus_length_r` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L82 | sus_length_r | RSusLength | UNRESOLVED | PENDING | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `sus_stiffness_f` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L77 | sus_stiffness_f | FSusStiffness | UNRESOLVED | PENDING | UNKNOWN; —; neověřený předpoklad (kandidátní dekód) | 1 řádek = 1 ID (R1). |
| - | `sus_stiffness_r` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L78 | sus_stiffness_r | RSusStiffness | UNRESOLVED | PENDING | UNKNOWN; —; neověřený předpoklad | 1 řádek = 1 ID (R1). |
| - | `target_friction` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L70 | target_friction | (F/RTargetFriction) | UNRESOLVED | UNKNOWN | UNKNOWN (grip 1.0 v configu je Optimizer-předpoklad bez Tune protějšku); —; neověřený předpoklad (0.7 je kit-k | 1 řádek = 1 ID (R1). |
| - | `tcs_gradient` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L120 | tcs_gradient | TCSGradient | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `tcs_limit_pct` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L121 | tcs_limit_pct | TCSLimit | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `tcs_threshold_sps` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L119 | tcs_threshold_sps | TCSThreshold | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | 1 řádek = 1 ID (R1). |
| - | `throttle_accel` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L138 | throttle_accel | ThrotAccel | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | Buňka slučuje 2 Tune klíče (ThrotAccel/Decel); odlišné směry odezvy plynu. Stav děděn z řádku (mapovací stav,  |
| - | `throttle_decel` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L138 | throttle_decel | ThrotDecel | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | Buňka slučuje 2 Tune klíče (ThrotAccel/Decel); odlišné směry odezvy plynu. Stav děděn z řádku (mapovací stav,  |
| - | `torque_vector` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L160 | torque_vector | TorqueVector | UNRESOLVED | ESTIMATED | 0/100 → v RWD režimu irelevantní / k revizi s `drive_config`; profil `drivetrain.torque_split_f_r` (odvozeno z | 1 řádek = 1 ID (R1). |
| - | `trans_modes` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L150 | trans_modes | TransModes | UNRESOLVED | ESTIMATED | Manual-first (6MT s rev-matching); profil `transmission.type` ([1b]); odhad (odvozeno z typu skříně) | 1 řádek = 1 ID (R1). |
| - | `turbo_boost` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L139 | turbo_boost | T_Boost | UNRESOLVED | VERIFIED | 0 / n/a — Mustang GT je atmosféra (5.0 Ti-VCT V8 bez turba); profil `engine.code` ([1b]); oficiální zdroj | Buňka slučuje počet turbodmychadel a plnicí tlak; odlišné veličiny, společný stav VERIFIED (atmosféra). Stav d |
| - | `turbo_count` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L139 | turbo_count | Turbochargers | UNRESOLVED | VERIFIED | 0 / n/a — Mustang GT je atmosféra (5.0 Ti-VCT V8 bez turba); profil `engine.code` ([1b]); oficiální zdroj | Buňka slučuje počet turbodmychadel a plnicí tlak; odlišné veličiny, společný stav VERIFIED (atmosféra). Stav d |
| - | `wear_speed` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L174 | wear_speed | — | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | Buňka slučuje 3 podpůrné skriptové parametry opotřebení/prokluzu. Stav děděn z řádku (mapovací stav, viz R7). |
| - | `weight_box_size` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L55 | weight_box_size | WeightBSize | UNRESOLVED | PENDING | UNKNOWN; — (odvozeno od geometrie modelu, ne od Mustangu); měření | 1 řádek = 1 ID (R1). |
| - | `weight_dist_pct` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L53 | weight_dist_pct | WeightDist | UNRESOLVED | UNKNOWN | UNKNOWN; — (profil: `CHYBÍ`, továrně nepublikováno); — | 1 řádek = 1 ID (R1). |
| - | `weight_lb` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L52 | weight_lb | Weight | UNRESOLVED | ESTIMATED | 1808 kg; profil `mass.curb_weight` ([1b]+[3]); odhad (Ford sám uvádí "Est.") | 1 řádek = 1 ID (R1). |
| - | `wheel_lock_ratio` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L174 | wheel_lock_ratio | — | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | Buňka slučuje 3 podpůrné skriptové parametry opotřebení/prokluzu. Stav děděn z řádku (mapovací stav, viz R7). |
| - | `wheel_radius` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L62 | wheel_radius | (poloměr kol) | UNRESOLVED | ESTIMATED | F 686.6 / R 702.6 mm (nominální, nezatížené); výpočet z designace 255/40 R19, 275/40 R19 (VEHICLE-SPEC §2); vý | 1 řádek = 1 ID (R1). |
| - | `wheelbase_etc` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L61 | wheelbase_etc | (rozvor/rozchod/ride-height) | UNRESOLVED | VERIFIED | rozvor 2719; rozchod F 1585 / R 1642 mm; profil `dimensions.*` ([1b], sl. Mustang GT — nezaměnit Dark Horse);  | 1 řádek = 1 ID (R1). |
| - | `wheelspin_ratio` | AGENT-F-MUSTANG-PHYSICS-MAPPING.md | L174 | wheelspin_ratio | — | UNRESOLVED | UNKNOWN | UNKNOWN; —; — | Buňka slučuje 3 podpůrné skriptové parametry opotřebení/prokluzu. Stav děděn z řádku (mapovací stav, viz R7). |

Strojova kontrola teto tabulky: 94 radku, vsechna `logical_id` unikatni (R5), kazdy radek ma >=1 `source_rows` ukazujici na skutecny radek [F] (kontroly validatoru [E2] S5: pokryti 78/78, duplicity 0, vadne odkazy 0). Nezahrnuto (R4, `unresolved` U1): `clutch_rpm / clutch_speed / clutch_stall` - podnazvy radku L152 bez katalogoveho ID; umela ID nevytvorena.

## 6. Co chybi a navrh noveho rozsahu (cesta od B k PASS)

Chybi jedina vec, ale je to ta podstatna: **explicitni seznam 60 katalogovych ID** (vyber ze 138 [K]) s jednim stavem na ID, publikovany vlastnikem deklarace (Agent F) nebo rozhodnutim koordinatora. Bez nej nelze 60 zrekonstruovat - a jak ukazuje S4, nelze ho ani odvodit zadnou dolozenou operaci.
Navrhovany novy rozsah (nenahrazuje katalog, jen uzavira tento rozpor bez vymysleni):
1. `MAPPED_SET` = 94 normalizovanych ID z [N] (dolozeno, validovano) jako jediny normativni rozsah mapovani; stavove soucty 7/8/25/54 (VERIFIED/ESTIMATED/PENDING/UNKNOWN).
2. `ORIGINAL_60_SET=NOT_RECONSTRUCTABLE` ponechat jako historicky vyrok o [F] S1, dokud Agent F seznam nedoda.
3. Doda-li Agent F seznam 60: 1:1 prepocet proti [N] (ocekavany vysledek: podmnozina 94, rozdil = sloucene/aliasove polozky) a oprava souctu 7/3/21/28; teprve pak lze vyrok B revokovat.
4. Opravit [F] S4 "elektro-vetev 9x" na 11x (fakticka chyba proti [K]) a opravit [F] S1 soucty na strojovy stav tabulek 6/7/20/45 - to jsou opravy vlastniku souboru, ne teto rekonstrukce (cizi soubory nemenim).

## 7. Jak overit (reprodukce pro nezavisleho ctenare)

```
git log --all --oneline --diff-filter=A -- reports/NIGHT-WORK/AGENT-F-MUSTANG-PHYSICS-MAPPING.md  # -> jen 557ee39
git rev-parse 557ee39:reports/NIGHT-WORK/AGENT-F-MUSTANG-PHYSICS-MAPPING.md  # -> b5f95b1...
git show 557ee39:reports/NIGHT-WORK/AGENT-F-MUSTANG-PHYSICS-MAPPING.md | sed -n "32,42p"  # -> deklarace 60
git show 0f7c968 -- reports/NIGHT-WORK/AGENT-F-MUSTANG-PHYSICS-MAPPING.md  # -> jen PENDING 22->21
git hash-object reports/NIGHT-WORK/AGENT-F-MUSTANG-PHYSICS-MAPPING.md reports/NIGHT-WORK/AGENT-E-MUSTANG-DATA-AUDIT.md reports/NIGHT-WORK/AGENT-E-NORMALIZED-CATALOG-AUDIT.md reports/NIGHT-WORK/normalized_ids.json src/Chassis/catalog/parameters.json vehicle-data/references/ford-mustang-gt-2024-eu-manual-standard.json docs/VEHICLE-SPECIFICATIONS.md
python tools/validate_normalization.py  # -> [PENDING] deklarovanych 60 ID dolozeno seznamem
```
Strojove citelny seznam `original_60_ids.*` **nevytvarim** zamerne: zadani ho podminuje dolozenim a 60 neni dolozeno (vytvorit ho by znamenalo vymyslet ID - zakazano). Jedinym strojovym seznamem zustava [N] (94 ID).
