# Mapping Engine – mapování VehicleConfig → Tune (Agent B)

**Vlastník:** Agent B (FÁZE 4.2). Vlastněné soubory: `src/Chassis/mapping_engine.py`,
`src/Chassis/mapping/**`, tento dokument. READ-ONLY mimo ně (zvlášť `src/Optimizer/**`
– wiring dělá Agent D).
**Pravidla:** `docs/AGENT-RULES.md`. Česky; identifikátory anglicky; Python 3 stdlib;
žádné git operace.

Zdroje: `docs/A-CHASSIS-AUDIT.md` (§5–§13, chyby §17), `docs/ARCHITECTURE.md` (§3.3, §4,
§5.2), `contracts/vehicle_config.schema.json`, `src/Chassis/base.py`,
`src/Chassis/registry.py`, `src/Chassis/adapters/achassis_v1.py`,
`src/Optimizer/search_space.py`, `src/Optimizer/backend.py`, `autoengineer.py`.

---

## 1. Účel

VehicleConfig (`parameters.engine/transmission/…`, obecný popis „co se nastavuje“)
a Tune (`A-Chassis Tune` ModuleScript, konkrétní klíče `Horsepower`, `FinalDrive`, …)
jsou **dva různé jmenné prostory**. Tento engine je jediný most mezi nimi:

- `map_config` – překlad požadavku z VehicleConfig na Tune změny + strukturované
  odmítnutí všeho, co přeložit nelze (žádná tichá ignorace);
- `build_search_space` – seznam Tune klíčů, které smí ladit Optimizer.

Katalog `parameters.json` (Agent A, 19 polí) je zdrojem pravdy; engine ho jen čte.
Než bude katalog hotový, pracuje se proti formátu ze zadání – selftest nese
vlastní ukázkové záznamy (viz §7).

---

## 2. Zmrazené API (neměnit)

```python
def map_config(vehicle_config: dict, catalog_path: str, adapter_id: str) -> dict:
    # -> {"tune_changes": [{"tune_key", "value", "unit", "reason"}],
    #     "rejected": [{"param", "reason"}],
    #     "warnings": [str]}

def build_search_space(catalog_path: str, backend_caps: list[str]) -> list[str]:
    # -> seřazené Tune klíče (5 filtrů, viz §5)
```

---

## 3. Formát katalogového záznamu (19 polí)

| Pole | Význam |
|---|---|
| `id` | stabilní identifikátor záznamu |
| `tune_key` | klíč v Tune (`null` = mimo Tune) |
| `category` | MUTABLE_TUNE \| SCRIPT_CONTROLLED \| STRUCTURE_CONTROLLED \| READ_ONLY \| UNKNOWN |
| `config_path` | tečková cesta ve VehicleConfig (`engine.horsepower`) |
| `value` / `default` | naměřená / výchozí hodnota (`null` = neznámá, nevymýšlí se) |
| `unit` | jednotka Tune hodnoty (`hp`, `rpm`, `%`, `0-1`, …) |
| `value_type` | `number` \| `bool` \| `string` \| `list` |
| `min` / `max` | ověřený rozsah (`null` = bez rozsahu → mimo prostor) |
| `function` | co parametr dělá (krátce) |
| `physical_effect` | fyzikální účinek změny |
| `used_in` | scénáře/měření, kde se projevuje (vztah k měření) |
| `depends_on` | seznam závislostí (string id/tune_key/config_path, nebo `{param, min?, max?, equals?, reason?}`) |
| `conflicts` | seznam kolidujících id/tune_key/config_path |
| `change_method` | `tune` \| `script` \| `geometry` \| `unknown` |
| `source` | auditní odkaz, např. `A-CHASSIS-AUDIT.md §5` |
| `confidence` | 0–1 |
| `verification_status` | `verified` \| jiné (jen `verified` jde do prostoru) |

---

## 4. Kategorie a pravidla odmítnutí

| Kategorie | Akce | Důvod |
|---|---|---|
| MUTABLE_TUNE | apply (při splnění rozsahu/závislostí) | ověřený Tune klíč |
| SCRIPT_CONTROLLED | rejected | hodnota žije ve skriptu mimo Tune – změna jen kódem |
| STRUCTURE_CONTROLLED | rejected | hodnota dána konstrukcí modelu – parametrem nelze |
| READ_ONLY | rejected | pouze ke čtení |
| UNKNOWN | rejected | klíč/hodnota auditem nepotvrzeny – nikdy se nevymýšlejí |

Další důvody `rejected`: neznámý `config_path` (bez katalogového záznamu),
hodnota mimo `[min, max]`, nesplněná závislost, konflikt s již aplikovaným
parametrem (vítězí abecedně první `config_path` – deterministicky).
`verification_status ≠ verified` → `warnings` (mapuje se s výhradou).
`adapter_id` se ověřuje proti registru; neznámý/rezervovaný adaptér → `warnings`,
nikdy tichý pád ani tiché přeskočení. Hodnota `None` (např. povinné
`geometry_overrides: null`) není požadavek na změnu a přeskočí se bez záznamu.

Závislosti jsou strukturované datové tabulky, ne volný text:
`src/Chassis/mapping/dependencies.py` (`CATEGORY_RULES`, `KNOWN_DEPENDS`,
`KNOWN_CONFLICTS`). Známý konflikt: `transmission.final_drive_mult` ×
`transmission.final_drive` (multiplikativní nejednoznačnost; `FDMult≠1` rozhodí
Gauges jen vizuálně – audit §6). Známá závislost: `engine.turbo.boost` vyžaduje
`engine.turbo.count ≥ 1` (audit §5).

---

## 5. `build_search_space`: 5 filtrů (všechny musí platit)

1. `category == MUTABLE_TUNE` (měnitelné),
2. `verification_status == "verified"` (ověřené),
3. číselné `min < max` (s rozsahem),
4. neprázdné `used_in` (se vztahem k měření),
5. `tune_key ∈ backend_caps` (podporované backendem).

Výstup: seřazený `list[str]` Tune klíčů. Prázdné `backend_caps` → prázdný prostor.
Volba Tune klíčů (ne config cest): backend aplikuje Tune změny; převod
`tune_key → config_path` dá katalog Agentovi D při wiringu do Optimizeru.

---

## 6. Audit nesouladů VehicleConfig ↔ search_space ↔ Tune

**Ověřená fakta čtením souborů** (ne odhadem):

| # | Obecná vlastnost (VehicleConfig) | Tune klíč | Stav | Jednotka / pravidlo |
|---|---|---|---|---|
| 1 | `engine.peak_torque_nm` (dříve statický prostor search_space 180–250 Nm — odstraněn ve F4.2.1; config 205; Physics/Sim vstup `engine_torque`) | **žádný** – Tune má jen `Horsepower` + křivku (`PeakRPM`, `PeakSharpness`, `CurveMult`, `EqPoint`) | **NESOULAD – nemapovat** | Momentový skalár v Tune neexistuje. Převod Nm→hp vyžaduje otáčky (P = M·ω) a křivku; bez definovaného převodu se `peak_torque_nm` na `Horsepower` **nepřepisuje**. `map_config` ho odmítne jako neznámý. |
| 2 | `engine.peak_power_kw` (config 135; Physics cap `P·1000/ω`) | **žádný** (`Horsepower` = 200 hp, jiná veličina i jednotka) | **NESOULAD – nemapovat** | Zásada: `engine.peak_power_kw ≠ engine.horsepower` bez definovaného převodu (hp↔kW faktor × jiný referenční bod křivky). Odmítnout s důvodem, ne tiše převést. |
| 3 | `engine.horsepower` (cesta adaptéru, Tune 200) | `Horsepower` | OK v adaptéru, **chybí ve VehicleConfig** (schéma-příklad, `normalize_config` ani `Sim/config` cestu neznají) | `hp`; rozsah dle katalogu. Jediná legitimní motorová cesta pro Tune dnes. |
| 4 | `transmission.final_drive` (search_space 2.5–4.2; config 2.866; profilový `powertrain.final_drive`) | `FinalDrive` (3.545) × `FDMult` (1.1) | **shoda** (s výhradou konfliktu FD×FDMult, viz §4) | bezrozměrné; `FDMult` měnit jen samostatně |
| 5 | `brakes.bias_front` (config 0.62/0.65; search_space 0.55–0.70) | `BrakeBias` (0.6, live-klíč F4.3) | **shoda** | podíl 0–1; extrémy 0/1 rizikové [P] |
| 6 | `tires.grip_long/lat` (config 1.0; Optimizer předpoklad) | **žádný** – grip je `_WHEELTUNE` v `Simulated` (mimo Tune) | **NESOULAD – read-only** | Jediný Tune parametr kol je hustota (`FWheelDensity/RWheelDensity`); adheze se ladí skriptem (§10, §16) |
| 7 | `brakes.torque_Nm` (config 4000) | `BrakeForce` (2500, vzorec `#BV`) | **NESOULAD jednotek** | `BrakeForce` není moment v Nm (škáluje se FPS a režimy); rovnítko zakázáno |
| 8 | `suspension.spring_f_Npm` (config 28000/24000) | `FSusStiffness`/`RSusStiffness` (20000/20000, kandidátní dekód; F/R rozděleno F4.3) | **podmíněně** | `N/m` až po Studio-verifikaci float-lane (audit §1, §8); symetrie kol nevychází |
| 9 | `steering.max_angle_deg` (config 35) | `LockToLock` (2.6) + `SteerRatio` (15) → `SteerOuter` 31.2° | **odvozeno, ne 1:1** | `°`; nelze mapovat přímo, jen přepočtem |
| 10 | `transmission.gears` (config list) | `Ratios` (dict R/N/1–6) | **strukturální nesoulad** | list ≠ dict s R/N; mapování až po definici konverze |
| 11 | `parameters.tune` (čte `apply_config`) vs `parameters.engine/…` (schéma §3.3) | – | **dva jmenné prostory** | `tune` = klíče adaptéru; `engine/…` = VehicleConfig. Most = tento engine + katalog |
| 12 | `mass.total_kg` (profil) | `Weight` (3439 lb) | **převod jednotek** | lb→kg řeší až adaptér/runtime vrstva, nikdy úložiště (CONTRACTS §8) |
| 13 | motorové `idle/peak/redline_rpm`, turbo/sání (`T_Boost`, `Turbochargers`, …) | `IdleRPM`/`PeakRPM`/`Redline`/`T_Boost`/… (audit §5) | **OK v adaptéru, chybí ve VehicleConfig** | `rpm`, `hp`, … – kandidáti na rozšíření schématu (rozhodne Agent D) |

Důsledek pro Optimizer (wiring Agent D): `search_space` dnes obsahuje
`engine.peak_torque_nm`, který **nemá Tune protějšek** – ladění této cesty dnes
končí v `rejected`. Oprava patří Agentu D (ne sem): buď cesta z prostoru ven,
nebo definovaný převod přes katalog.

---

## 7. Obecná vlastnost → Tune klíč (mapovací tabulka)

| Obecná vlastnost | Tune klíč | Jednotka | Pravidla | Zdůvodnění |
|---|---|---|---|---|
| výkon motoru | `Horsepower` | hp | rozsah z katalogu; `peak_power_kw` se sem **nepřevádí** | audit §5: jediný výkonový skalár Tune |
| stálý převod | `FinalDrive` | – | 2.5–4.2 (kalibrace SIM); konflikt s `FDMult` | audit §6; hrany prostoru ověřeny kampaní |
| škálování převodu | `FDMult` | – | jen samostatně (konflikt výše); =1 pro Gauges | audit §6 |
| brzdný bias | `BrakeBias` (live-klíč F4.3) | 0–1 | 0–1; extrémy rizikové | audit §12 |
| počet turbodorů | `Turbochargers` | ks | 0–4 | audit §5 |
| plnicí tlak | `T_Boost` | – | vyžaduje `turbo.count ≥ 1` | audit §5 (vzorec HP_T) |
| odpor vzduchu | — (`Drag` je konstanta ve skriptu) | – | SCRIPT_CONTROLLED → rejected | audit §13 + chyba `magnitude` (§17.2) |
| kompresní poměr | `CompressionRatio`? | – | UNKNOWN → rejected (název nepotvrzen) | audit §5 (jen ve vzorci) |
| tuhost pružin | `FSusStiffness`/`RSusStiffness` (F/R rozděleno F4.3) | N/m | bez ověřeného rozsahu → mimo prostor (mapovat ano, ladit ne) | audit §8, float-gap §1 |

---

## 8. Selftest (akceptace)

Běh: `python3 src/Chassis/mapping_engine.py` (z kořene `C:/.DATA/AutoEngineerAI`).
Ověřuje: mapování 3 vlastností vč. motoru (`Horsepower` 210 + `FinalDrive` +
`Bias`); odmítnutí unknown (`engine.warp_drive`) + read-only (`aero.drag_coeff`,
SCRIPT_CONTROLLED) + mimo rozsah (`horsepower` 5000) + konflikt (FD×FDMult) +
závislost (boost bez turba); zásadu `peak_power_kw ≠ horsepower` (odmítnuto);
prostor jen z MUTABLE_TUNE s rozsahem (`[Bias, FDMult, FinalDrive, Horsepower,
T_Boost, Turbochargers]` – bez `Stiffness` bez rozsahu, bez script/unknown);
filtr `backend_caps`; determinismus (opakovaný běh, identické JSON).
Tiskne raw JSON výsledek + `SELFTEST OK`, exit 0 (assert selže → exit 1).

---

## 9. Ověřená fakta / předpoklady / neznámé

**Ověřená fakta:** Tune klíče a hodnoty výše opsány z auditu (§5, §6, §12) a
`achassis_v1.py` (`Horsepower`=200 hp, `FinalDrive`=3.545, `Bias`=0.6);
`peak_torque_nm`/`peak_power_kw` žijí jen v Optimizer/Sim/config vrstvě
(`search_space.py`, `fallback_sim.py`, `Physics/api.py`, `Sim/config.py`,
`autoengineer.py`) a Tune protějšek nemají; registr zná `achassis-v1` (ready)
a `future-custom-v1` (reserved).
**Předpoklady:** katalog Agenta A dodrží 19 polí a 5 kategorií ze zadání;
`used_in` ponese scénáře měření; `backend_caps` ponese Tune klíče.
**Neznámé (mimo rozsah B):** skutečný `parameters.json`; wiring do Optimizeru
(Agent D); Studio-verifikace float hodnot (audit §1, §19).

---

## 10. Brána S-02 (Agent B, 2026-11-20)

Oba veřejné vstupy (`map_config`, `build_search_space`) procházejí před
jakoukoli prací společnou bránou `src/Chassis/mapping/gate.py`
(`gate_catalog_records` / `gate_catalog_file`) v pořadí načtení katalogu →
struktura → integrita → detekce cyklu → OK/BLOCKED (nad neměnným API
`cycle_check` + `validate_catalog`; slovníkové závislosti `{'param': …}`
se normalizují na hrany, viz `_normalize_for_detector`).
Při BLOCKED: `map_config` vrací `tune_changes: []` + `rejected:
[{param: *catalog*, reason: CYCLE/INTEGRITY/INVALID…}]` (vstup nezměněn);
`build_search_space` vrací `[]` (důvod přes `gate_catalog_file`).
Skutečný `parameters.json` je cyklický (12 SCC, svědek
`tcs_threshold_sps -> tcs_gradient -> tcs_threshold_sps`) → reálné
mapování vrací BLOCKED; to je správně, brána se neobchází.
