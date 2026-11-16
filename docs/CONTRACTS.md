# Kontrakty dat AutoEngineerAI

**Vlastněný soubor agenta A (kontrakty).** Vychází z `docs/ARCHITECTURE.md` kapitol 3–7 (závazné).
Jazyk dokumentu: česky. Identifikátory a kód anglicky.

Stav: návrh v1 (vlna 1). Schémata: `contracts/*.schema.json` (draft 2020-12),
validátor: `tools/validate_contracts.py`, společný kód: `src/common/`.

---

## 1. Rozhodnutí

1. **JSON Schema draft 2020-12** pro všech 9 schémat (`$schema` v každém souboru).
   Důvod: shoda s existujícím `vehicle-data/references/_schema.json`; čitelné pro
   Luau (HttpService) i Python.
2. **Ruční validátor bez závislostí** (`tools/validate_contracts.py`, pouze stdlib).
   Důvod: zadání vlny 1 (Python, pouze stdlib) — nelze použít balíček `jsonschema`.
   Validátor pokrývá podmnožinu draftu 2020-12 (viz hlavička skriptu); co neumí,
   to ve schématech nepoužíváme.
3. **`schema_version: "1.0.0"` povinná ve všech artefaktech pipeline.**
   Důvod: verzování kontraktů nezávisle na verzování dat.
   Není v ARCH §3 výslovně, ale nemění povinná pole §3.1–§3.5 — je to nadmnožina
   s povoleným polem navíc. Ostatní agenti ji musí zapisovat.
4. **`additionalProperties: false` na kořeni a klíčových objektech**
   (parameters, environment, dimensions, mass).
   Důvod: včasný záchyt překlepů. Volná struktura zůstává tam, kde ji ARCH
   vyžaduje (vnitřky `parameters.*`, `metrics`, `suspension`).
5. **Dva různé „referenční" formáty vedle sebe** (řeší otevřený bod 1 ze STATUS):
   - `vehicle-data/references/*.json` = bohatý DB záznam (existující `_schema.json`,
     desítky polí s obálkou `{value, unit, source, source_type, confidence}`),
   - `contracts/reference_profile.schema.json` = úzký pipeline profil dle ARCH §3.2
     (`vehicle/specs/target_metrics` s provenance `{value, source, confidence, uncertainty?}`).
     Propojení polem `source_vehicle_id`. Důvod: pipeline potřebuje malý,
     optimalizací čitelný cíl; DB zůstává plným zdrojem pravdy.
6. **Provenance v ReferenceProfile je povinná** (`source` neprázdný, `confidence` 0–1),
   chybějící údaj = `value: null` + `confidence: 0`. Důvod: požadavek plánu 5.4
   (každý údaj má zdroj a důvěryhodnost), ARCH §3.2.
7. **ID mají pevné prefixy** (`vp_`, `rp_`, `cfg_`, `plan_`, `tr_`, `dg_`, `run_`;
   viz `src/common/ids.py`). Důvod: okamžitá rozpoznatelnost druhu artefaktu
   v manifestu a historii; linkování `config_id`/`scenario_id`/`diagnosis_ref`
   je pak strojově kontrolovatelné. Výjimka: `scenario_id` a `chassis_id` jsou
   volné řetězce (přebírají názvy scénářů §5.3 a detekovaných systémů).
8. **Kanonické jednotky: SI + stupně; g = 9.81; dt = 1/240 s; 1 stud = 0.28 m;
   KG_PER_RMU = 21.952** (viz `src/common/units.py`). Úložiště nikdy neobsahuje
   Roblox jednotky — převod řeší až adaptér/runtime vrstva (ARCH §3, úvod).

## 2. Mapování VehicleProfile (§3.1) ↔ vehicle-data/_schema.json (otevřený bod 1)

VehicleProfile je **naměřený stav konkrétního modelu**, DB záznam je **tovární
popis reálného vozu**. Převod DB → ReferenceProfile → (porovnání) → cíle pro
VehicleConfig. Přímé převodní vztahy:

| VehicleProfile (§3.1) | Zdroj v `_schema.json` | Převod / poznámka |
|---|---|---|
| `dimensions.wheelbase_m` | `dimensions.wheelbase` | mm → m (/1000) |
| `dimensions.track_f_m` | `dimensions.track_front` | mm → m (/1000) |
| `dimensions.track_r_m` | `dimensions.track_rear` | mm → m (/1000) |
| `mass.total_kg` | `mass.curb_weight` | kg, přímo; `confidence` DB → váha metriky |
| `mass.center_of_mass` | `mass.weight_distribution_front_pct` + `mass.cog_height` | ODHAD: `com_x = (f − 0.5) · rozvor` (x vpřed, přední náprava +L/2); `com_y = 0`; `com_z = cog_height`; obojí v DB často `null`/odhad → kalibrovat testem |
| `mass.inertia` | `mass.yaw_inertia` (typicky `null`) | Není-li: aproximace kvádru `I = m/12·(L²+W²)` jako kalibrační parametr, nikdy fakt |
| `wheels[].radius_m` | `wheels_tires.tire_{front,rear}.diameter_mm` | /2, /1000; P/Z zvlášť |
| `wheels[].position` | `dimensions.wheelbase` + `track_{front,rear}` | x = ±rozvor/2, y = ±rozchod/2, z = poloměr |
| `wheels[].camber_deg/toe_deg` | `alignment.*` | deg, přímo (v DB často odhad s nízkou důvěrou) |
| `powertrain.gears` | `transmission.gear_ratios[].ratio.value` | seřadit dle `gear`, přímo (`:1`) |
| `powertrain.final_drive` | `transmission.final_drive` | přímo |
| `powertrain.drive_type` | `drivetrain.driven_axle` | `FWD\|RWD\|AWD`, přímo |
| `brakes.bias_front` | `brakes.brake_bias_front_pct` | % → podíl (/100); v DB často `null` → kalibrovat |
| `steering.max_angle_deg` | `dimensions.turning_circle` (nepřímo) | ODHAD inverzí poloměru otáčení; jinak měřit na modelu |
| `steering.ackermann_ratio` | — (v DB není) | měřit na modelu, výchozí 1.0 |
| `suspension` | `suspension.spring_rate_{front,rear}` | N/mm → N/m (×1000); typicky `null` → měřit/kalibrovat |
| `hierarchy/scripts` | — (v DB není) | vždy z modelu (Analyzer), nikdy z DB |
| `chassis.chassis_id` | — (v DB není) | výstup ChassisIntelligence |

Provenance se do VehicleProfile **nepřenáší** (profil je měření s `source_model_hash`);
důvěryhodnost DB údajů se promítá do vah `target_metrics` v ReferenceProfile.

## 3. Přehled schémat

| Soubor | Artefakt | Odpovídá ARCH |
|---|---|---|
| `vehicle_profile.schema.json` | VehicleProfile | §3.1 |
| `reference_profile.schema.json` | ReferenceProfile | §3.2 |
| `vehicle_config.schema.json` | VehicleConfig (klíče parameters: engine/transmission/tires/suspension/steering/brakes/geometry_overrides) | §3.3 |
| `change_plan.schema.json` | ChangePlan (keep/adapt/replace) | §3.4 |
| `test_result.schema.json` | TestResult (result_id/config_id/scenario_id/environment{mode,seed,code_version}/metrics/deviations_vs_target/score/reproduced_runs/raw_telemetry_ref) | §3.5 |
| `diagnosis.schema.json` | Diagnosis (area/symptom/probable_cause) | §5.1 |
| `chassis_info.schema.json` | ChassisInfo (typ/parametry/limity) | §2, §5.4 |
| `scenario.schema.json` | Scenario (6 druhů dle §5.3 + seed) | §5.3 |
| `manifest.schema.json` | Manifest běhu (code_version + seedy) | §6 |

Vzorové platné artefakty: `contracts/examples/*.valid.json`.

## 4. Ověřená fakta / předpoklady / neznámé + zdroje

**Ověřená fakta (čtením souborů před prací):**
- ARCH §3.1–§3.5 tvary polí opsané do schémat 1:1 (povinná pole shodná; viz tabulka v kap. 3).
- `1 stud = 0.28 m`, `KG_PER_RMU = 1000·0.28³ = 21.952` —
  `C:/.DATA/RobloxSimulator/game/server/RobloxAdapter/UnitMap.luau` (řádky 3–11),
  potvrzeno `C:/.DATA/RobloxSimulator/docs/CONTROL-RESET.md` (1 RMU = 21.952 kg).
- `g = 9.81 m/s²` — `C:/.DATA/RobloxSimulator/game/shared/vehicle/Types/EnvironmentSI.luau`.
- `dt = 1/240 s` — `C:/.DATA/RobloxSimulator/game/shared/vehicle/Types/SIContract.luau`.
- `example-vehicle.json` validován proti `_schema.json` vlastním validátorem (viz výstup níže).
- RobloxSimulator nedotčen (pouze čtení přes grep; žádný zápis, žádný git příkaz).
- `python3 --version` = 3.14.9; validátor používá pouze stdlib (`json`, `re`, `argparse`, `datetime`, `pathlib`, `math`).

**Předpoklady:**
- Mini-validátor stačí: schémata používají jen jím podporovanou podmnožinu draftu 2020-12.
- Ostatní agenti budou zapisovat `schema_version` a ID s prefixy (kontrakt, ne technický zámek).
- Volné objekty (`parameters.*`, `metrics`) později zpřesní agenti D/F vlastními podschématy.

**Neznámé (mimo rozsah agenta A):**
- Skutečné parametry A-Chassis (audit FÁZE 1) — vnitřky `parameters.*` proto záměrně volné.
- Váhy `score` a tolerance reprodukovatelnosti — řeší agenti F/G/H.

**Zdroje:** `C:/.DATA/AutoEngineerAI/docs/ARCHITECTURE.md` (§3–§7),
`C:/.DATA/AutoEngineerAI/docs/PROJECT-PLAN.md` (kap. 5.4),
`C:/.DATA/AutoEngineerAI/vehicle-data/references/_schema.json` +
`example-vehicle.json`, výše citované soubory RobloxSimulatoru.
