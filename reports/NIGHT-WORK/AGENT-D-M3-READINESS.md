# Agent D – M3 Geometry Engine: návrh a připravenost (NEIMPLEMENTOVAT)

> Status: **NÁVRH ONLY, 2026-11-19, větev `feat/m2-m3-geometry`, HEAD `9803db3`.**
> M3 kód se **NEIMPLEMENTUJE** — tento dokument je pouze návrh + plán.
> Produkční `geometry_target.json` / `geometry_diff.json` a jakýkoli kód v `src/` jsou
> **BLOKOVÁNY do brány M2** (VERIFIED měřítko `studs_per_meter` M2.9/M2.10 nestanoveno;
> kalibrace JeepTemplate BLOCKED 7,44 %; kalibrační engine `scale_calibration.py`
> CODE-VERIFIED; měření M2.4–M2.8 BLOCKED kalibrační bránou).
> Vlastněný soubor Agenta D: `reports/NIGHT-WORK/AGENT-D-M3-READINESS.md` (nový).
> RBXM čteno pouze jako metadata/kód, `C:/.DATA/RobloxSimulator` READ-ONLY (nedotčen).
> Žádné odhadnuté měřítko pro výpočty, žádná runtime tvrzení, žádný merge PR #2/main/nový PR.

Zdroje (čteno, ne odhadnuto):
`docs/IMPLEMENTATION_ROADMAP.md` §M1–M3 · `reports/M3/GEOMETRY-ENGINE-PROPOSAL.md` (Agent E, návrh v1)
· `reports/M2-M3-CONTRACTS-FREEZE-v1.md` (FREEZE 2026-11-19) · `src/common/units.py`
· `src/common/ids.py`, `src/common/errors.py` · `src/Inspection/{rbxm_parser,wheel_detect,scale_calibration}.py`
· `src/Reference/{loader,validate,compare}.py` · `tools/validate_contracts.py`
· profil `vehicle-data/references/ford-mustang-gt-2024-eu-manual-standard.json`
(EUROPEAN FACTORY STANDARD SPECIFICATION) · `reports/STUDIO_GROUND_TRUTH.md`
· `docs/PROJECT_STATUS.md` §0.2/§10 · `docs/CONTRACTS.md`.

---

## 1. Reusovatelné moduly (existují, M3 je pouze volá / rozšiřuje — nedubluje)

| Modul | Co M3 reusuje | Stav |
|---|---|---|
| `src/common/units.py` — `m_to_studs(m)=m/0.28`, `METERS_PER_STUD=0.28`, `tire_diameter_mm(W,A,R)=R·25.4+2·W·A/100`, `_finite()` (isfinite guard) | všechny převody mm→m→studs; nominální průměry; finiteness validace před každým výpočtem | EXISTS, rozšířit místo duplikace (ROADMAP M2 bod 6 / M3 bod 6) |
| `src/common/ids.py` — prefixy `vp_/rp_/cfg_/plan_/tr_/dg_/run_`, `require_valid()` | ID artefaktů M3 (`scale_ref.calibration_id`, `inspection_ref.report_id`) | EXISTS |
| `src/common/errors.py` — `ContractError`, `format_error()` | české chyby brány M3 | EXISTS |
| `src/Inspection/rbxm_parser.py` — `parse_rbxm/parse_bytes`, `assess_wheel_geometry()`, `_is_rotation_matrix()`, záměrný stub `calibrate_studs_per_meter` (NOT IMPLEMENTED pomocné rozhraní) | M3 NIC neparsovává — bere hotový `inspection_report`; rotace/CFrame se nepoužívají (AUDIT P1) | C05 CODE-VERIFIED |
| `src/Inspection/wheel_detect.py` — `detect_wheels()`, `classify_candidate()` (4-tier VALID/KNOWN_NON/UNKNOWN_CANDIDATE/INVALID), `build_inspection_report()` (track z `\|FL.x−FR.x\|`, wheelbase průměr L/R párů z `z`, Y-spread + rectangularity kontroly), `COORDINATE_FRAME_ACTUAL {x:lateral, y:up, z:longitudinal, verified_in_studio:true}`, `is_blocked()` | kontrakt `inspection_report.json` (vstup M3); souřadnicový rámec; per-kolo statusy | CODE-VERIFIED |
| `src/Inspection/scale_calibration.py` — `calibrate()`, `usable_for_m3()` (= `overall_status==VERIFIED`), `require_verified_for_m3()` (jinak `CalibrationBlockedError`), `VERIFIED_MAX_DEV_PCT=2.0`, `default_references()` | **brána M3** — jediný zdroj `k = studs_per_meter`; M3 nesmí použít konstantu `1/0.28` jako měřené měřítko modelu | IMPLEMENTED + CODE-VERIFIED (31 testů); výsledek na JeepTemplate BLOCKED 7,44 % > 5 % |
| `src/Reference/{loader,validate,compare}.py` | čtení M1 profilu (obálka `{value,unit,source,source_type,confidence}`), VERIFIED/ESTIMATED/UNKNOWN pravidla (`value:null + confidence>0.5` = chyba; `factory` vyžaduje `confidence≥0.8`) | EXISTS (M1 CODE-VERIFIED) |
| `tools/validate_contracts.py` (stdlib only) | validace `geometry_target/diff` proti budoucím `contracts/*.schema.json` | EXISTS |
| `src/Physics/tires.py`, `src/Chassis/catalog/parameters.json` (138 záznamů), `contracts/*.schema.json` | orientační — M3 na ně nesahá (hranice M4/M5); kategorie `STRUCTURE_CONTROLLED` pro posuny kol | EXISTS (M4/M5 PARTIAL) |

Pravidlo AGENTS.md č. 4: `src/autoengineer/` **neexistuje** — před kódem (FÁZE B) ověřit proti
`src/Inspection/`, `src/common/units.py`, `PROJECT_STATUS.md` §2; navržené cesty níže jsou
návrh dle ROADMAP §M3 bod 6, fyzické umístění rozhodne inventura + vlastník ve FÁZI B
(`src/Geometry/` vs `src/autoengineer/geometry/` — otevřený bod).

## 2. M1 profil Mustang (EU factory standard) — vstupy M3

| Param | Hodnota | Status / conf | Zdroj |
|---|---|---|---|
| `dimensions.wheelbase` | 2719 mm | VERIFIED, 0.9, factory | [1b] Ford EU tech specs + [3] ADAC |
| `dimensions.track_front` | 1585 mm (Dark Horse 1595 — nezaměnit) | VERIFIED, 0.9, factory | [1b] sloupec Mustang GT |
| `dimensions.track_rear` | 1642 mm (Dark Horse 1643 — nezaměnit) | VERIFIED, 0.9, factory | [1b] sloupec Mustang GT |
| `wheels_tires.tire_front.diameter_mm` | 686,6 mm = 19·25,4+2·255·40/100 | ODHAD, 0.6, estimate | výpočet z designace 255/40 R19, tolerance dezénu ±5 mm |
| `wheels_tires.tire_rear.diameter_mm` | 702,6 mm = 19·25,4+2·275·40/100 | ODHAD, 0.6, estimate | výpočet z designace 275/40 R19, tolerance dezénu ±5 mm |
| `mass.cog_height`, `mass.weight_distribution`, `transmission.final_drive`, `torque_curve` | `null` | UNKNOWN (CHYBÍ) | M3 je nepotřebuje a nesmí je odvozovat |

Studio ground-truth (referenční čísla, ne produkční vstup): rozvor ≈10.5228 / rozchod ≈5.9907 /
Ball 2.7³, Y identické (23.622…) — `STUDIO_GROUND_TRUTH.md` §3–4, parser POTVRZEN.

## 3. Datový tok M1 → M2 → VERIFIED kalibrace → M3 target → diff → validation

```
M1 profil (mm + statusy) ──────────────┐
                                       ├─→ M3 geometry_validator.precheck() ──→ dimensions / wheel / axle ──→ geometry_target.json
M2 inspection_report.json (kola,středy) ┘         │ GATE (§7 — důkaz níže)        (čisté funkce)               geometry_diff.json
M2 scale_calibration.json (k, nejistota) ─────────┘                                                                        │
                                                                                                                           ▼
                                                                                                              tools/validate_contracts.py
                                                                                                              + hash originálu RBXM beze změny (G-01)
```

Kontrakt vstupu (FREEZE, změna jen novou verzí):
`inspection.overall_status == GEOMETRY_OK` + všechna 4 kola `GEOMETRY_OK`;
`scale.overall_status == VERIFIED` (STRICT) + `studs_per_meter` konečné kladné +
`uncertainty` přítomna; `coordinate_frame.verified_in_studio == true`
(rámec `COORDINATE_FRAME_ACTUAL`: x=lateral, y=up, z=longitudinal);
každé M2 měření bez statusu = odmítnuto (G-02/G-03).

Převodní pravidlo: `target_studs = value_mm / 1000 × studs_per_meter`,
kde `k` pochází **výhradně z M2 kalibrace**, nikdy z konstanty `STUDS_PER_METER = 1/0.28`
(ta je definiční pro opačný směr SI→Roblox a nesmí se zaměnit za měřené měřítko modelu).

## 4. Výpočty M3 — specifikace (ne implementace)

Vše studs, každá hodnota `{value, unit, status, source_ref}`.
Statusy: `VERIFIED | ESTIMATED | UNKNOWN | BLOCKED` (shodně s M1/M2).
Každá souřadnice `isfinite` před výpočtem (reakce na AUDIT P0); orientace kol z CFrame
se ignoruje / přebírá jako `unverified` (AUDIT P1 — matice se nevaliduje, M3 používá pouze středy).

| # | Výpočet | Vstupy / jednotky | Zdroj | Rovnice | Validace | Stav výstupu | Při chybějícím vstupu |
|---|---|---|---|---|---|---|---|
| M3.1 | převod rozměrů | 2719 / 1585 / 1642 mm (VERIFIED) + `k` (studs/m, VERIFIED) | profil `dimensions.*` + `scale_calibration` | `wb=2719/1000·k`, `tf=1585/1000·k`, `tr=1642/1000·k` | `k>0`, `isfinite`; `track_f < track_r` (1585<1642) | `method:computed`, status = nižší z (profil, scale) | BLOCKED, `value:null` |
| M3.2–M3.4 | cílový rozvor / rozchody | viz M3.1 | viz M3.1 | viz M3.1 | kontrola prohození P/Z → odmítnuto (M3-T09) | VERIFIED (dědí) | BLOCKED |
| M3.5 | průměry pneu | 686,6 / 702,6 mm (ESTIMATED) + `k` | profil `wheels_tires.*.diameter_mm` | `686.6/1000·k` (P), `702.6/1000·k` (Z) | nominální nezatížené, dezén ±5 mm evidován | **ESTIMATED vždy** (conf 0.6), nikdy VERIFIED | BLOCKED, `value:null` |
| M3.6 | pozice středů kol | cílový wb/tf/tr + zdrojové středy FL/FR/RL/RR | inspekce + M3.2–M3.4 | symetrický obdélník z wb/tf/tr, **kotven na zadní nápravu** zdrojového modelu (přední se posouvá o Δ rozvoru); Y/Z přebrány z inspekce (kola v rovině) | `isfinite` každé souřadnice; L/R symetrie ≤ 0,5 % rozchodu (návrh ke schválení) | `method:computed` | BLOCKED |
| M3.7 | geometrický rozdíl | target (M3.2–M3.6) + source (inspekce) | oba reporty | `delta = target − source` (studs), řádky `{wheelbase, track_f, track_r, tire_d_f, tire_d_r}` + per-kolo `center.{x,y,z}` | `method: measured\|computed`; determinismus G-10 (stejný vstup + verze = stejný výstup) | dědí nižší status | BLOCKED |
| M3.8 | posunutí L/R kol | `target_center − source_center` po složkách (studs) | M3.6 vs inspekce | vektor posunu per kolo | označeno `STRUCTURE_CONTROLLED` (hranice M5 — návrh posunu, ne příkaz) | návrh, ne aplikace | BLOCKED |
| M3.9 | symetrie a kolize | L/R odchylka od středové roviny; `tire_radius + rezerva vs min_clearance` | M3.6 + tolerance | `\|L−R\| ≤ 0,5 % rozchodu` (návrh); kolize → `WARNING` (průnik → eskalace M5/M7, blokuje až neřešitelný průnik) | šířka/délka/výška karoserie se nekontrolují (mimo rozsah M3 — evidováno jako neznámé) | PASS / WARNING | BLOCKED |
| M3.10 | report | vše výše | M3.1–M3.9 | `geometry_target.json` + `geometry_diff.json`; bez `scale_ref`/`inspection_ref` (hash + verze) je report neplatný | `validate_contracts.py` PASS (G-02/G-03); hash originálu RBXM beze změny (G-01) | `overall_status: OK \| BLOCKED` | BLOCKED |

## 5. Matice M3-T01 až M3-T09 (návrh testů, FÁZE B)

| ID | Scénář | Očekáváno |
|---|---|---|
| M3-T01 | Převod 2719/1585/1642 mm přes `k` | studs hodnoty ± tolerance `uncertainty` |
| M3-T02 | Průměry 686,6 / 702,6 mm | ESTIMATED, dezén ±5 mm evidován |
| M3-T03 | Symetrie L/R cílového obdélníku | PASS ≤ 0,5 % rozchodu (návrh ke schválení) |
| M3-T04 | Prohození P/Z nápravy ve vstupu | odmítnuto |
| M3-T05 | Měřítko BLOCKED / UNKNOWN / ESTIMATED | celý report BLOCKED, `value: null` |
| M3-T06 | Kolo UNKNOWN / ≠4 kola | STOP, BLOCKED |
| M3-T07 | `size/position = +Inf/NaN` ve vstupu | per-hodnota UNKNOWN, BLOCKED (AUDIT P0) |
| M3-T08 | Diff proti reálné inspekci (ground-truth 10.5228/5.9907) | deterministický diff, G-10 |
| M3-T09 | Kolize kolo–karoserie | WARNING (průnik → eskalace M5) |

Integration: diff proti M2 inspekci reálného RBXM; `tools/validate_contracts.py` PASS;
hash originálu RBXM beze změny (G-01).

## 6. Návrh `geometry_target.json` (rozšíření FREEZE o statusy a verze)

```json
{
  "$schema": "contracts/geometry_target.schema.json",
  "vehicle_id": "ford-mustang-gt-2024-eu-manual-standard",
  "scale_ref": {"calibration_id": "cal_xxx", "code_version": "githash", "studs_per_meter": 0.0, "uncertainty": 0.0},
  "inspection_ref": {"report_id": "rep_xxx", "source_sha256": "hex"},
  "wheelbase_studs": {"value": 0.0, "unit": "studs", "status": "VERIFIED|ESTIMATED", "source_ref": "profile:dimensions.wheelbase"},
  "track_f_studs": {"value": 0.0, "unit": "studs", "status": "...", "source_ref": "profile:dimensions.track_front"},
  "track_r_studs": {"value": 0.0, "unit": "studs", "status": "...", "source_ref": "profile:dimensions.track_rear"},
  "tire_d_f_studs": {"value": 0.0, "unit": "studs", "status": "ESTIMATED", "source_ref": "profile:wheels_tires.tire_front.diameter_mm"},
  "tire_d_r_studs": {"value": 0.0, "unit": "studs", "status": "ESTIMATED", "source_ref": "profile:wheels_tires.tire_rear.diameter_mm"},
  "wheel_centers_studs": {"FL": {"value": [0,0,0], "unit": "studs", "status": "...", "source_ref": "computed:M3.6"}},
  "overall_status": "OK | BLOCKED",
  "blocked_reason": null
}
```

Návrh `geometry_diff.json` (dle FREEZE, `delta` v `target_unit`):

```json
[{"param": "wheelbase", "source_value": 10.52, "source_unit": "studs",
  "target_value": 0.0, "target_unit": "studs", "delta": 0.0,
  "method": "computed", "status": "VERIFIED|ESTIMATED|BLOCKED", "source_ref": "inspection:rep_xxx"}]
```

Při BLOCKED: `overall_status: BLOCKED`, `blocked_reason` povinný, všechny `value: null`
(G-04 — žádná čísla při nekonzistentním měřítku, ROADMAP M3 body 4/11).

## 7. Seznam souborů k implementaci (FÁZE B, až po odblokování M2)

Pořadí: `geometry_validator` první (brána dřív než čísla), poté `dimensions`,
poté `wheel/axle/diff`; testy M3-T05…T07 před M3-T01/T02 (G-04/G-05).

1. `src/Geometry/geometry_validator.py` (nebo `src/autoengineer/geometry/` — rozhodne inventura FÁZE B) — `precheck()` jediný vstup pro BLOCKED.
2. `src/Geometry/dimensions.py` — převody mm→studs přes `k` (volá `src/common/units.py`).
3. `src/Geometry/wheel_geometry.py` — průměry + středy (M3.5/M3.6).
4. `src/Geometry/axle_geometry.py` — rozvor/rozchody, symetrie (M3.2–M3.4, M3.9).
5. `src/Geometry/geometry_diff.py` — diff + L/R posunutí (M3.7/M3.8, `STRUCTURE_CONTROLLED`).
6. `contracts/geometry_target.schema.json` + `contracts/geometry_diff.schema.json` v1 (FREEZE kompatibilní).
7. Testy `tests/.../test_m3_t01…t09.py` + fixture (syntetické, determinismus G-10).
8. `reports/M1-M3-…` — první skutečný výstup (tabulka zdroj/Mustang/rozdíl) jako milník M1–M3.

## 8. GATE — důkaz, že bez M2 VERIFIED nic nepočítá

Brána je `geometry_validator.precheck()` nad těmito existujícími zámky
(`src/Inspection/scale_calibration.py`, CODE-VERIFIED):

```python
def usable_for_m3(result: dict) -> bool:
    return result.get("overall_status") == "VERIFIED"

def require_verified_for_m3(result: dict) -> dict:
    if not usable_for_m3(result):
        raise CalibrationBlockedError(...)  # ESTIMATED | UNKNOWN | BLOCKED → STOP
    return result
```

`precheck()` vrací BLOCKED (a zastavuje vše pod ním), pokud platí **koli** z:
`inspection.overall_status != GEOMETRY_OK` · počet kol ≠ 4 / kterékoli kolo UNKNOWN ·
`scale.overall_status != VERIFIED` (tj. BLOCKED | UNKNOWN | **ESTIMATED — odhadnuté měřítko
blokuje stejně jako chybějící**, jinak by `k` vyrábělo falešně přesnou geometrii) ·
`studs_per_meter` není konečné kladné (`isfinite`, AUDIT P0) · < 2 nezávislé reference ·
`coordinate_frame` neověřen · `source_sha256` inspekce ≠ hash pracovní kopie RBXM (G-01).
BLOCKED se propaguje na **celý** `geometry_target.json` + **celý** `geometry_diff.json`,
žádné částečné číselné výstupy (M3-T05…T07, G-04/G-05); důvod + která podmínka selhala
vždy v `blocked_reason`.

Aktuální stav brány: **ZAVŘENO** — kalibrace JeepTemplate BLOCKED 7,44 % > 5 %,
VERIFIED měřítko pro M3 chybí (`PROJECT_STATUS.md` §0.2/§10); M3 proto zůstává návrh
bez kódu (očekávaný stav, ne selhání). M4/M5 čekají na M3 (milník M1–M3).

## 9. Rizika a otevřené body (fronta, neblokují návrh)

- R1 měřítko (největší): bez `k` nelze nic — mitigace pořadím `validator → dimensions → diff`.
- R2 nominální ≠ zatížené průměry → ESTIMATED + tolerance, kalibrace v M4/M7.
- R3 CFrame orientace nevalidována (AUDIT P1) → M3 orientaci nepoužívá.
- R4 `isfinite` díry v M2 vstupu (AUDIT P0) → `precheck` validuje každý float; neplatný → UNKNOWN/BLOCKED.
- R5 EU/US a GT/Dark Horse záměna → `vehicle_id` + `scale_ref`/`inspection_ref` v každém artefaktu.
- Otevřeno: tolerance symetrie 0,5 % (ke schválení) · kotevní bod zadní náprava (potvrdit) ·
  práh kolizní rezervy (do M5/M7) · fyzické umístění modulu · verze kontraktů (změna jen novou verzí).
