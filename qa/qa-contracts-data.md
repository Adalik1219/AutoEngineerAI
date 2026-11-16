# QA vlna 2 – kontrakty / data

**Vlastněný soubor:** `qa/qa-contracts-data.md` · **Datum:** 2026-11-16 · **Jazyk:** česky
**Rozsah:** pouze audit, READ-ONLY vše kromě tohoto souboru (žádný zápis jinam, žádné git operace).
**Zdroje (vše čteno):** `docs/ARCHITECTURE.md` (§3, §5.4), `docs/A-CHASSIS-AUDIT.md`, `docs/VEHICLE-DATA.md`,
`vehicle-data/references/_schema.json` + 3 profily, `contracts/*.schema.json` + `examples/*.valid.json`,
`tools/validate_contracts.py`, `src/common/units.py|ids.py|errors.py`,
`src/Chassis/{base,registry,adapters/achassis_v1}.py`,
`C:/.DATA/RobloxSimulator/game/server/RobloxAdapter/UnitMap.luau`,
`C:/.DATA/RobloxSimulator/game/shared/vehicle/Types/SIContract.luau`,
`C:/.DATA/RobloxSimulator/game/shared/vehicle/Types/EnvironmentSI.luau`.

## 1. Kontrakty vs ARCHITECTURE §3 — PASS s 1 výhradou

Tvar každého pole ověřen čtením schémat; povinné klíče souhlasí:
- `vehicle_config.schema.json:17` — `parameters` vyžaduje přesně
  `engine/transmission/tires/suspension/steering/brakes/geometry_overrides` (§3.3). `geometry_overrides: [object,null]` ✓.
- `test_result.schema.json:16-22` — `environment` vyžaduje `mode/seed/code_version`;
  `mode ∈ {local-sim, roblox-runtime}` (§5.3/§3.5) ✓. `metrics minProperties 1`, `score 0–1`, `reproduced_runs ≥ 1` ✓.
- `reference_profile.schema.json:50` — `proven` vyžaduje `value/source/confidence` (+vol. `uncertainty`); `value: null` povolena (§3.2) ✓.
  Ale: schéma **nevynucuje** `value:null → confidence: 0` (strojně projde i 0.5) — viz nález H.
- `vehicle_profile.schema.json:33,43,64,87` — `dimensions{wheelbase_m,track_f_m,track_r_m}`,
  `mass{total_kg,center_of_mass[3]}`, `wheels[]{id,radius_m,width_m,position[3]}`,
  `powertrain{drive_type∈RWD|FWD|AWD}` — odpovídá §3.1 ✓ (povinné minimum; zbytek volný, což je záměr).
- Zbylá schémata (`change_plan` keep/adapt/replace §3.4; `diagnosis` area/symptom/probable_cause §5.1;
  `chassis_info` §2+§5.4; `scenario` 6 druhů §5.3; `manifest` code_version+seed §6) — bez rozporu s ARCH.

Vlastní nevalidní případy nad rámec dodaných (validator `tools/validate_contracts.py`, funkce `validate_against_schema`):
| # | Případ | Výsledek | Raw výstup (zkráceně) |
|---|---|---|---|
| V1 | VC bez `geometry_overrides` | INVALID ✓ | `$/parameters: chybí povinné pole 'geometry_overrides'` |
| V2 | VC s `parameters.EXTRA` | INVALID ✓ | `$/parameters: neznámé pole 'EXTRA'` (additionalProperties:false funguje) |
| T1 | TR `environment` bez `seed` | INVALID ✓ | `$/environment: chybí povinné pole 'seed'` |
| T2 | TR `mode: studio` | INVALID ✓ | `není mezi povolenými ['local-sim','roblox-runtime']` |
| T3 | TR `metrics: {}` | INVALID ✓ | `$/metrics: málo položek (0 < 1)` |
| R1 | RP `value:null, confidence:0.5` | **VALID (strojně) / VĚCNĚ ŠPATNĚ** | `[]` — mezera ve schématu, viz opravy |
| R2 | RP `source: ""` | INVALID ✓ | `řetězec je příliš krátký (0 < 1)` |
| P1 | VP bez `powertrain.drive_type` | INVALID ✓ | `$/powertrain: chybí povinné pole 'drive_type'` |

Dodaný selftest: `python3 tools/validate_contracts.py` → **21/21 OK** (9× validní+nevalidní pár, 3× profily vč. nových).

## 2. `src/common/units.py` vs RobloxSimulator — PASS (4/4 potvrzeno)

| Konstanta (`units.py:20-23`) | Zdroj pravdy | Verdikt |
|---|---|---|
| `METERS_PER_STUD = 0.28` | `UnitMap.luau:9-11` `METERS_PER_STUD = 0.28` | **POTVRZENO** |
| `KG_PER_RMU = 1000·0.28³ = 21.952` | `UnitMap.luau:11` `KG_PER_RMU = 1000*…^3` | **POTVRZENO** (výpočet 21.952 souhlasí) |
| `GRAVITY_MPS2 = 9.81` | `EnvironmentSI.luau:4` `gravityMps2 = 9.81` | **POTVRZENO** |
| `DEFAULT_DT = 1/240` | `SIContract.luau:4` `FIXED_DT = 1/240` | **POTVRZENO** |
| `n_to_roblox_force = /(KG·STUD)` | `UnitMap.luau: nToRobloxForce = force/(KG_PER_RMU*METERS_PER_STUD)` | **POTVRZENO** |
| `nm_to_roblox_torque = /(KG·STUD²)` | `UnitMap.luau: nmToRobloxTorque = torque/(KG_PER_RMU*STUD²)` (+ komentář „Do not use the force conversion") | **POTVRZENO** |
| `kmh/mps, deg/rad` | UnitMap je nedefinuje (čas v s, úhly v rad/s — bez rozporu); čistě Python-side pomoc | BEZ ROZPORU |

## 3. `src/Chassis` spot-check vs A-CHASSIS-AUDIT — PASS s 1 drobnou výhradou

Ověřeno 6 mapování Tune→VehicleConfig (název, Tune-klíč, default vs audit):
- `horsepower/Horsepower=200` (§5) ✓ · `Ratios={R:3.28,…,6:.793}` (§6) ✓ · `Config=AWD` (§7) ✓ ·
  `Stiffness=20000 / Damping=500` (§8, vč. varování o kandidátním dekódu) ✓ ·
  `Bias=0.6 / BrakeForce=2500 / ABSThreshold=20` (§12) ✓ · `Weight=3439 lb / WeightDist=55 % / CGHeight=0.8` (§11) ✓.
- Script-coded read-only s důvodem ✓ (např. `curve_shape_func`, `target_friction/_WHEELTUNE`, `drag_coeff=.34`,
  `downforce_f/r=125/150`, `abs_pulse_logic`, `arm_kinematics`, `camber_caster_toe` — vše `mutable=False` + `read_only_reason`).
- Unknown nevymyšlené ✓ (`rear_diff_power/coast` s `"RDiffPower?"`, `sus_length`, `compress_lim`, `wheelbase_etc`,
  `legacy_wheel_density_*` — vše `default=None`, `provenance="unknown"`; `base.py:64-67` to technicky vynucuje).
- `limits()` (`achassis_v1.py:509-546`) obsahuje **všechny 4 chyby kódu** (StAxisOffset §17.1, `magnitude` §17.2,
  ElecRedline §17.3, LgcyDensity §17.4) **+ FLOAT/CFRAME gap** (§1, Stiffness 2.39917 jako nepotvrzený kandidát) ✓.
- Výhrada: `pbrake_bias` (`achassis_v1.py:357`) nese `tune_key="Bias(PBrake)"` jako `_m` (měnitelný),
  ačkoli audit jméno klíče neuvádí („Bias=0" bez jména) — hodnota 0 ověřena, jméno je kvalifikovaný odhad. Doporučeno přepnout na `_u` nebo doplnit zdroj.

## 4. Referenční profily — PASS (strojně), NÁLEZ H POTVRZEN (věcně)

Vlastní skript (stdlib `json`, walk všech `valued` listů + přepočty):
- Validace všech 3 profilů proti `_schema.json` vlastním validátorem: **3/3 PASS**
  (shodné s `validate_contracts.py`: `example-vehicle + civic + gr86 → [OK]`).
- Obálky provenance: každý list má `value/unit/source/source_type/confidence` (povinné dle `_schema.json:235`);
  `torque_curve.points[].point_type ∈ factory/measured/interpolated/estimated` ✓; `meta.status: draft` u všech tří ✓.
- **Nález H POTVRZEN:** `example-vehicle.json` má **4× `value:null` s `confidence: 0.2`** místo ARCH §3.2 `confidence: 0`:
  `mass.yaw_inertia` (ř. 39), `suspension.spring_rate_front` (ř. 133), `suspension.spring_rate_rear` (ř. 134),
  `aero.drag_coefficient_cd` (ř. 145). Stejný vzor u nových profilů:
  Honda **10×** (`aero.drag_coefficient_cd`, `dimensions.{ground_clearance,turning_circle,width_incl_mirrors}`,
  `mass.{cog_height,dry_weight,yaw_inertia}`, `performance.braking_100_0`, `suspension.spring_rate_{front,rear}` —
  vše `confidence: 0.2`), Toyota **9×** (totéž minus `ground_clearance`). Kořen: `VEHICLE-DATA.md §3.2/§6`
  škálují `0.0–0.2 = neznámé/null`, což je v rozporu s přísným `ARCH §3.2 (null + confidence: 0)`.
- Konzistence `P = M·n/9549` (všechny 3 profily ✓):
  MX-5: 205 Nm@4000 → 85.9 kW (< 135 kW ✓); 135 kW@7000 → 184.2 Nm ≈ bod křivky 184 ✓.
  Civic: 400 Nm@2500 → 104.7 kW (< 235 ✓); 235 kW@6500 → 345.2 Nm = interpolovaný bod křivky 345 ✓.
  GR86: 250 Nm@3700 → 96.9 kW (< 172 ✓); 172 kW@7000 → 234.6 Nm ≈ bod 235 ✓.
- Pneu Ø z designace `25.4·rim+2·w·a/100` ✓ (MX-5 616.3→616; Civic 655.0→655; GR86 629.2→629, vše ±0.3 mm).
  V-max dosažitelná převody ✓ (teor. rychlost na top stupeň při redline > V-max: 304>219, 286>272, 283>226).
- Křivky momentu: tovární kotvy `point_type: factory` na správných otáčkách (4000/2500+4500/3700), zbytek
  `estimated/interpolated` s nízkou důvěrou ✓ (dle VEHICLE-DATA §4).

## Přesný seznam oprav

1. `vehicle-data/references/example-vehicle.json:39,133,134,145` — `confidence: 0.2 → 0` u 4 `null` hodnot (ARCH §3.2),
   **nebo** opravit ARCH §3.2 / VEHICLE-DATA §3.2, aby škála 0.0–0.2 byla legální. Totéž pro nové profily:
   `vehicle-data/references/honda-civic-fk8-20-vtec-turbo-6mt-eu.json` (10× `confidence: 0.2` s `value: null`),
   `vehicle-data/references/toyota-gr86-zn8-24-d4s-6mt-eu.json` (9×). Držitel: vlastník referenčních dat, ne QA.
2. `contracts/reference_profile.schema.json` (§defs `proven`, ř. 48-58) — zvážit strojní vynucení
   `value:null → confidence: 0` (jinak nález H projde validátorem; případ R1 výše). Držitel: vlastník kontraktů.
3. `src/Chassis/adapters/achassis_v1.py:357` — `pbrake_bias` tune_key `"Bias(PBrake)"` je odhad jména;
   přepnout na `_u` (unknown) do potvrzení ve Studiu. Držitel: vlastník adaptéru.
4. Bez opravy: `units.py`, `limits()` (4 chyby + float gap), tvary `parameters`/`environment`, konzistence P=M·n, Ø pneu, V-max — vše PASS.

## Shrnutí verdiktů po blocích

| Blok | Verdikt |
|---|---|
| (1) kontrakty vs ARCH §3 + vlastní případy | **PASS** (R1 mezera ve schématu → oprava č. 2) |
| (2) `units.py` vs UnitMap/SIContract/EnvironmentSI | **PASS 4/4** |
| (3) Chassis spot-check + script-coded/unknown + limits | **PASS** (drobná výhrada → oprava č. 3) |
| (4) profily vs `_schema.json` + provenance + H + P=M·n | **PASS strojně / FAIL věcně (H potvrzen)** → oprava č. 1 |
