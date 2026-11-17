# A-Chassis – katalog parametrů (Agent A, FÁZE 4.1)

**Vlastník:** Agent A – Parameter Intelligence.
**Vlastněné soubory (POUZE tyto):** `docs/A-CHASSIS-PARAMETER-CATALOG.md`,
`src/Chassis/catalog/parameters.json`, `src/Chassis/catalog/loader.py`,
`src/Chassis/catalog/__init__.py`.
**Zdroje (čteno, nezapisováno):** `docs/A-CHASSIS-AUDIT.md` (celý),
`src/Chassis/adapters/achassis_v1.py` (125 položek), `src/Chassis/base.py`,
`src/Chassis/registry.py`, `docs/AGENT-RULES.md`, `docs/ARCHITECTURE.md` §5.4.
**READ-ONLY:** `C:/.DATA/RobloxSimulator`, `C:/Users/adamr/Downloads/chasis.rbxm`
(nesaháno). **Pravidla:** česky; Python 3 stdlib; žádné git operace; nic se
nedomýšlí – názvy klíčů, jednotky a rozsahy pouze z auditu/kódu; UNKNOWN
zůstává UNKNOWN; chyby se dokumentují, neopravují; žádná Studio automatizace,
žádné geometrické změny.

Značení: **[F]** = ověřený fakt (audit/kód), **[P]** = předpoklad,
**[N]** = neznámé (postup ověření uveden).

---

## 1. Co katalog je a jaké rozhraní je zmrazené

`parameters.json` = **seznam 125 záznamů**, 1:1 k položkám `PARAMETERS`
adaptéru `achassis-v1` (Agent D). Každý záznam má **PŘESNĚ těchto 19 polí**
(zmrazené rozhraní, neměnit bez koordinátora):

`id, tune_key, category, config_path, value, unit, value_type, min, max,
default, function, physical_effect, used_in, depends_on[], conflicts[],
change_method, source, confidence, verification_status`

`category ∈ {MUTABLE_TUNE, SCRIPT_CONTROLLED, STRUCTURE_CONTROLLED,
READ_ONLY, UNKNOWN}` – každá doložena důkazem z auditu/kódu (pole `source`).
`loader.py`: načtení (`load`), validace zmrazeného rozhraní (`validate`),
dotazy `get_by_id` / `by_category` / `by_config_path` a akceptační
`run_selftest` (CLI `python3 src/Chassis/catalog/loader.py --selftest`,
exit 0). Mapování kategorií adaptéru → katalogu:

| Adaptér (`base.py` provenance) | Katalog `category` | Počet | `change_method` |
|---|---|---|---|
| `measured` + `mutable` | `MUTABLE_TUNE` | 79 | `tune` |
| `script-coded` | `SCRIPT_CONTROLLED` | 14 | `script` |
| `unknown` + geometrie (§1, §16) | `STRUCTURE_CONTROLLED` | 2 | `geometry` |
| `unknown` + mrtvý kód / mismatch (§14, §15, §17) | `READ_ONLY` | 3 | `none` |
| `unknown` + zbytek | `UNKNOWN` | 27 | `pending-studio` |

Důkazy pro výjimky: `wheelbase_etc`, `wheel_radius` = STRUCTURE **[F]** –
rozvor/rozchod/poloměry ze souboru nevyčteny (float/CFrame gap §1), rozměr =
geometrie dílu, parametrem nelze (§16). `legacy_wheel_density_f/r` =
READ_ONLY **[F]** – klíče v Tune neexistují, odkazuje je jen mrtvá non-PGS
větev `Simulated`, a bez PGS `Initialize` skončí chybou dřív (§14, §17.4).
`electric_gauge_names` = READ_ONLY **[F]** – `Gauges_AC6:62` čte
`ElecRedline/ElecTransition2`, Tune má `E_Redline/E_Trans2`; projeví se jen
při `Electric=true`, zde mrtvé (§15, §17.3).

---

## 2. Úplnost vs audit a vs adaptér

- **125/125 položek adaptéru pokryto** (`loader` selftest: `n_records == 125`,
  `EXPECTED_COUNT`). Kontrolní součty: MUTABLE_TUNE 79 = `measured` 79;
  SCRIPT_CONTROLLED 14 = `script-coded` 14; UNKNOWN + STRUCTURE + READ_ONLY
  27+2+3 = 32 = `unknown` 32. **[F]**
- **Nevypsané Tune položky:** audit (§4) uvádí Tune-tabulku „~150 parametrů",
  rozepsáno je v něm ≈ 125 klíčů; adaptér sám deklaruje, že zbytek
  ~150členné tabulky v auditu rozepsán není a `apply_config` je odmítá jako
  neznámé. Katalog proto **nepřidává žádný klíč nad adaptér** – cokoli mimo
  těchto 125 je pro FÁZI 4.1 explicitně mimo rozsah (ne vymýšlet). **[F]**
- **Script-coded (14):** `curve_shape_func` (CurveN), `shift_logic` (Auto/LC),
  `center_diff_logic`, `arm_kinematics`, `camber_caster_toe`,
  `target_friction` (.7+Heat, min .1), `wheel_lock_ratio`, `wheelspin_ratio`,
  `wear_speed` (.4/3.6/.5), `abs_pulse_logic`, `drag_coeff` (.34),
  `downforce_f` (125), `downforce_r` (150), `wind_volume` (1). Hodnoty-literaly
  pouze tam, kde je audit uvádí doslovně (§10, §13); jinak `value: null. **[F]**
- **Nepoužívané / konfliktní / podmíněné parametry [F]:**
  - Neaktivní procedurální větev (custom `SuspensionGeometry` ji přebíjí):
    `front_wishbone_len`, `rear_wishbone_len`, `sus_angle`, `anchor_offset`
    → UNKNOWN, `conflicts: [arm_kinematics]`, hodnoty z auditu nepřevzaty.
  - Starý dif (`SlipThres`/`LockThres`): ignorovány při
    `DifferentialType=New` → UNKNOWN, podmíněné (`depends_on:
    [differential_type]`, `conflicts: [differential_type]`).
  - `rear_diff_power` / `rear_diff_coast`: audit zná jen hodnoty „zadek
    40/30" **bez názvů klíčů** → `tune_key` s otazníkem (`RDiffPower?`),
    UNKNOWN, hodnoty nepřevzaty (adaptér: „odvozen, nepotvrzen").
  - `pbrake_bias`: hodnota 0 ověřena (§12), **název klíče nepotvrzen**
    (kvalifikovaný odhad QA vlny 2) → UNKNOWN, `tune_key: Bias(PBrake)?`.
  - `final_drive_mult ≠ 1` vs `Gauges` max-rychlosti: konflikt jen vizuální,
    fyziku neovlivňuje → `conflicts: [gauge_max_speed_display]`. **[F]**
  - `compression_ratio`: klíč auditem nepotvrzen (jen ve vzorci HP_T) →
    UNKNOWN. `spring_color`: §16 ji uvádí jako Tune-měnitelnou, ale **klíč
    ani hodnota v auditu nejsou** → UNKNOWN, `tune_key: null`.
- **Mrtvé větve [F]** (READ_ONLY, `change_method: none`, nikdy nezapisovat):
  `legacy_wheel_density_f/r` (non-PGS větev, §17.4), `electric_gauge_names`
  (mismatch, §17.3), celá elektro-větev (`electric_enabled=false`, 9
  `electric_*` UNKNOWN) a `StAxisOffset` (chybí v Tune, §17.1 – viz kap. 5).

---

## 3. Seznam UNKNOWN (37) – zůstává UNKNOWN

F4.3 (Agent R): 19 fantomů opraveno na live-klíče (`Bias→BrakeBias`,
`Stiffness/Damping/SusLength/PreCompress/ExtensionLim/CompressLim/SusAngle/AnchorOffset→F*/R*`,
`Preload→FDiffPreload/RDiffPreload`, `SlipThres/LockThres→F/R/C Diff*Thres`,
`RDiffPower?/RDiffCoast?→RDiffPower/RDiffCoast`, `Bias(PBrake)?→PBrakeBias`;
`StAxisOffset/FWLgcyDensity/RWLgcyDensity/ElecRedline-ElecTransition2→tune_key null`).
Důvod je vždy v `physical_effect` / `source` záznamu; společný jmenovatel:
klíč nebo hodnota v auditu chybí, větev je mrtvá/neaktivní, nebo jde o
kvalifikovaný odhad. **Není dovoleno je hádat ani zapisovat do Tune.**

Elektro (mrtvá větev, 9): `electric_trans1`, `electric_trans2`,
`electric_redline`, `electric_front_mult`, `electric_end_mult`,
`electric_end_percent`, `electric_torque`, `electric_torque_end_mult`,
`electric_torque_end_percent`. Motor (2): `supercharger_sensitivity`,
`compression_ratio`. Převodovka (1): `tq_lock`. Dif (8): `rear_diff_power`,
`rear_diff_coast`, `slip_thresh_f/r/c`, `lock_thresh_f/r/c`. Podvozek (14):
`sus_length_f/r`, `pre_compress_f/r`, `extension_lim_f/r`, `compress_lim_f/r`,
`front_wishbone_len`, `rear_wishbone_len`, `sus_angle_f/r`, `anchor_offset_f/r`
(14). Řízení (1):
`steer_axis_offset`. Brzdy (1): `pbrake_bias`. Vzhled (1): `spring_color`.

---

## 4. Seznam pro měření ve Studiu – F4 PENDING, ne PASS (31)

`verification_status: PENDING` = fakt čeká na Studio/odečet z Tune, **nesmí se
použít jako ověřený vstup optimalizace**. (PASS = ověřeno auditem/kódem [F].)

| # | Parametr | Co odečíst / změřit | Zdroj postupu |
|---|---|---|---|
| 1–2 | `spring_stiffness`, `damper` | Skutečné `Stiffness/Damping` template (kandidátní dekód 20000/500, symetrie kol nevychází → `value: null`, `default` = kandidát) | §1, §8 |
| 3–6 | `sus_length`, `pre_compress`, `extension_lim`, `compress_lim` | Čtyři délky z Tune (audit zná jen odvozené Free/Max/Min) | §8 |
| 7–8 | `wheelbase_etc`, `wheel_radius` | `Position` FL–RL (rozvor), FL–FR (rozchod), výška DriveSeat; `Size` kol → `vehicle-data/analyzed/` | §1, §3 |
| 9 | `steer_axis_offset` | Existuje-li `Tune.StAxisOffset`; první spuštění potvrdí/vyvrátí runtime error `Initialize:171` | §9, §17.1 |
| 10–11 | `compression_ratio`, `supercharger_sensitivity` | Odečet z Tune (vzorec HP_T / `_SBoost`) | §5 |
| 12–20 | 9× `electric_*` | Odečet z Tune (mrtvá větev – nízká priorita, jen pokud se elektro oživí) | §5 |
| 21 | `tq_lock` | Odečet z Tune (větev měniče) | §6 |
| 22–25 | `rear_diff_power/coast`, `slip_thresh_old`, `lock_thresh_old` | Skutečné názvy klíčů + hodnoty v Tune | §7 |
| 26–29 | `front/rear_wishbone_len`, `sus_angle`, `anchor_offset` | Potvrdit neaktivnost (procedurální větev se nestaví) | §8 |
| 30 | `pbrake_bias` | Skutečný název klíče v Tune (hodnota 0 známa) | §12 |
| 31 | `spring_color` | Název klíče + hodnota v Tune | §16 |

**Před měřením V-max nejdřív oprava `magnitude` bugu** (kap. 5, chyba č. 2) –
jinak je maximálka měřena bez odporu vzduchu.

---

## 5. Závislosti, omezení a dopad známých chyb + bezpečný postup

**Závislosti (pole `depends_on`):** turbo-lagy → `turbo_count` (=2 pro 2.
stupeň); všech 9 `electric_*` → `electric_enabled`; `shift_up/down_time` →
`auto_shift_type` (DCT); prahy řazení → `auto_shift_mode`; `tq_lock` →
spojková větev; dif-váhy/preload → `differential_type`; `torque_vector` →
`drive_config`; délky pružin navzájem (`FreeLength=SusLength+PreCompress`,
`Max=+ExtensionLim`, `Min=−CompressLim`); ABS/TCS prahy → gradient/limit;
`flywheel` ↔ `rev_accel`/`clutch_engage`; `pbrake_force` → `pbrake_bias`.

**Tvrdé limity [F]** (§16, též `limits()` adaptéru): 60Hz Heartbeat +
škálování `60/RealPhysicsFPS` (závislost na FPS); kola musí být
koule jmenovitě FL/FR/RL/RR (jinak je `Drive`/`Simulated` ignorují);
`DriveSeat` povinný; PGS povinné; fyzika běží na klientu řidiče (testy
s lokálním řidičem). Bezpečná pásma: tuhosti 0.25–4×, `CGHeight ≤ ~1.2`,
`WeightDist` 30–70, prahy ABS/TCS ≥ ~5 SPS, `FDMult = 1`.

**Dopad chyb kódu [F]** (§17, dokumentováno, NEopravováno – mimo rozsah Agenta A):
1. `StAxisOffset` (`Initialize:171`, katalog `steer_axis_offset`): klíč
   v Tune chybí → podezření na runtime error při stavbě nápravy; **blokuje
   první spuštění** – ověřit ve Studiu (PENDING č. 9), neobcházet.
2. `Velocity.magnitude` (`Aerodynamics:21`, katalog `drag_coeff`): odpor se
   nikdy neaplikuje (přítlak ano); dopad = **maximálka kitu je bez odporu**;
   V-max měřit až po opravě (oprava = 1 znak, provede Engineering).
3. `ElecRedline/ElecTransition2` vs `E_Redline/E_Trans2` (katalog
   `electric_gauge_names`): jen při `Electric=true` (zde mrtvé); dopad dnes
   nulový, při oživení elektra povinný převod názvů.
4. `FWLgcyDensity/RWLgcyDensity` (katalog `legacy_*`): mrtvý kód, bez PGS
   končí `Initialize` chybou dřív; dopad nulový, **nikdy nezapisovat**.

**Bezpečný postup pro FÁZI 4 / Engineering:** (a) ladit POUZE `MUTABLE_TUNE`
s `verification_status: PASS` (77 záznamů); `spring_stiffness`/`damper` až po
odečtu ve Studiu; (b) `UNKNOWN`/`PENDING` nikdy nezapisovat do Tune –
nejdřív odečet dle tabulky kap. 4; (c) `SCRIPT_CONTROLLED`/`READ_ONLY`/
`STRUCTURE_CONTROLLED` neměnit parametrem (skript/geometrie/nikdy);
(d) před V-max kampaní oprava chyby č. 2; před prvním během verdikt k chybě
č. 1; (e) `min`/`max` v katalogu jsou jen tam, kde je audit dává doslovně
(`curve_mult` 0–1, `torque_vector` −1..1, dif-váhy/preload 0–100, přední bias
0–1, `weight_dist` 0–100) – jinde `null`, **žádné limity se nedomýšlejí**.

---

## 6. Ověření (akceptace Agenta A)

`python3 src/Chassis/catalog/loader.py --selftest` → exit 0; raw výstup:
`n_records: 125`, všech 5 kategorií zastoupeno (79/14/2/3/27), žádný
`MUTABLE_TUNE` bez ověřeného `tune_key`, `n_pending_studio: 31` se jmenným
seznamem. Selftest dále validuje: přesně 19 polí na záznam, unikátní `id`
i `config_path`, `confidence ∈ 0..1`, `verification_status ∈ {PASS,PENDING}`.
Soubor `parameters.json` je seřazen (MUTABLE → SCRIPT → STRUCTURE →
READ_ONLY → UNKNOWN). Nevytvořen ani upraven žádný soubor mimo 4 vlastněné;
`git` operace neprovedeny (zakázáno); READ-ONLY zdroje nedotčeny.
