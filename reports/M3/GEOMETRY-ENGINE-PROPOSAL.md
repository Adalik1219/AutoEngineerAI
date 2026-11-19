# M3 Geometry Engine — návrhový dokument (FÁZE A, NÁVRH ONLY)

> Status: **NÁVRH v1 (2026-11-19, větev `feat/m2-m3-geometry`, HEAD `ab840a9`) — žádná implementace.**
> Produkce (`geometry_target.json` / `diff.json`, jakýkoli kód v `src/`) je **BLOKOVÁNA do brány M2**
> (kalibrace `studs_per_meter` M2.9/M2.10 NOT IMPLEMENTED; měření M2.4–M2.8 BLOCKED).
> Tento dokument pouze navrhuje; nic nepočítá za produkci.
> Vlastněný soubor Agenta E: `reports/M3/GEOMETRY-ENGINE-PROPOSAL.md` (nový).

Zdroje (čteno): `docs/IMPLEMENTATION_ROADMAP.md` §M3 (body 1–14),
`reports/M2-M3-CONTRACTS-FREEZE-v1.md` (zmrazeno 2026-11-19),
`src/common/units.py` (konstanty `METERS_PER_STUD=0.28`, `STUDS_PER_METER`, `m_to_studs`),
profil `vehicle-data/references/ford-mustang-gt-2024-eu-manual-standard.json`
(EUROPEAN FACTORY STANDARD SPECIFICATION),
`reports/STUDIO_GROUND_TRUTH.md` (rozvor ≈10.52 / rozchod ≈5.99 / Ball 2.7³),
`reports/AUDIT-geometry.md` (P0 `isfinite` díry, P1 rotace/CFrame).

Cíl dle ROADMAP M3: cílová geometrie Mustangu v studs + rozdílový report proti
vstupnímu modelu, bez zásahu do originálu.

---

## 1. Vstupy (ověřená fakta)

| Vstup | Zdroj | Stav |
|---|---|---|
| Profil M1: rozvor 2719 mm, rozchod P 1585 mm, rozchod Z 1642 mm (VERIFIED, conf 0.9, `[1b]` Ford EU tech specs) | profil `dimensions` | VERIFIED |
| Profil M1: pneu P 255/40 R19 → D 686,6 mm; pneu Z 275/40 R19 → D 702,6 mm (`D = R·25,4 + 2·W·A/100`, nominální nezatížené, tolerance dezénu ±5 mm) | profil `wheels_tires.*.diameter_mm` | ODHAD (conf 0.6, `source_type: estimate`) |
| `src/common/units.py`: `m_to_studs(m) = m / 0.28`, `METERS_PER_STUD = 0.28` | `src/common/units.py` ř. 20–42 | VERIFIED |
| M2 `inspection_report.json` (kola FL/FR/RL/RR, středy, size, `overall_status`) | Agent B (kontrakt FREEZE) | PŘEDPOKLAD formátu — dosud BLOCKED |
| M2 `scale_calibration.json` (`studs_per_meter` + nejistota, `overall_status`) | Agent C (kontrakt FREEZE) | PŘEDPOKLAD — dosud BLOCKED / NOT IMPLEMENTED |
| Studio ground-truth: rozvor ≈10.5228 / rozchod ≈5.9907 / Ball 2.7³, Y identické | `STUDIO_GROUND_TRUTH.md` §3–4 | VERIFIED (referenční čísla, ne produkční vstup) |

Neznámé (nesmí se vymýšlet): výška těžiště, rozložení hmotnosti, Cd/čelní plocha,
stálý převod, bias — M3 je nepotřebuje a nesmí je odvozovat.

## 2. Nepředpoklady / co M3 nedělá

- Žádný zápis do RBXM ani originálu (G-01); M3 je čistá funkce M1+M2 → JSON.
- Žádné odhady při nekonzistentním měřítku — viz §7 BLOCKED propagace.
- Žádná orientace kol z CFrame matic bez validace (AUDIT P1: matice se nevaliduje;
  M3 používá **pouze středy**, orientaci ignoruje / přebírá jako `unverified`).
- Nominální průměry ≠ zatížené poloměry; strukturální posuny kol jsou
  `STRUCTURE_CONTROLLED` (hranice M5 — M3 je jen spočítá, neaplikuje).

## 3. Datové struktury (návrh)

Vše studs, každá hodnota `{value, unit, status, source_ref}`.
Statusy: `VERIFIED | ESTIMATED | UNKNOWN | BLOCKED` (shodně s M1/M2 kontrakty).

```python
@dataclass(frozen=True)
class WheelTarget:
    designation: str            # "FL" | "FR" | "RL" | "RR"
    center_studs: tuple[float, float, float]  # (x, y, z), rámec z inspection_report
    diameter_studs: float
    status: str                 # VERIFIED | ESTIMATED | BLOCKED
    source_ref: str             # např. "profile:dimensions.wheelbase"

@dataclass(frozen=True)
class GeometryTarget:
    vehicle_id: str             # "ford-mustang-gt-2024-eu-manual-standard"
    scale_ref: str              # id scale_calibration.json + code_version
    inspection_ref: str         # report_id + source_sha256
    wheelbase_studs: float
    track_f_studs: float
    track_r_studs: float
    tire_d_f_studs: float       # ESTIMATED (profil conf 0.6)
    tire_d_r_studs: float       # ESTIMATED
    wheel_centers_studs: dict[str, tuple[float, float, float]]  # FL/FR/RL/RR
    units: str = "studs"
    sources: list[str] = ...
    status_per_value: dict[str, str] = ...

@dataclass(frozen=True)
class GeometryDiffRow:
    param: str                  # "wheelbase" | "track_f" | ... | "FL.center.x" | ...
    source_value: float | None
    source_unit: str
    target_value: float | None
    target_unit: str
    delta: float | None         # target - source, stejná jednotka; None při BLOCKED
    method: str                 # "measured" | "computed"
    status: str
    source_ref: str
```

Modulové rozdělení (názvy dle ROADMAP §M3 bod 6, ověřit proti realitě před kódem —
`src/autoengineer/` neexistuje, viz ROADMAP mapování; alternativně `src/Geometry/`):
`dimensions.py` (mm→studs převody) · `wheel_geometry.py` (průměry + středy) ·
`axle_geometry.py` (rozvor/rozchody, symetrie) · `geometry_diff.py` (diff + L/R posunutí) ·
`geometry_validator.py` (všechny brány, jediný vstup pro BLOCKED).

## 4. Rozhraní M2 → M3

```
inspection_report.json ──┐
  (kola, středy, statusy) ├─→ geometry_validator.precheck() ──→ dimensions/wheel/axle ──→ geometry_target.json
scale_calibration.json ──┘    (GATE: viz §7)                   (čisté funkce)              geometry_diff.json
  (studs_per_meter, nejistota, overall_status)
         +
profile M1 (mm hodnoty + statusy)
```

Kontrakt vstupu (FREEZE, neměnit bez nové verze):
- `inspection_report.overall_status == "GEOMETRY_OK"` **a** všechna 4 kola `status == GEOMETRY_OK`, jinak STOP.
- `scale_calibration.overall_status ∈ {VERIFIED, ESTIMATED}` + `studs_per_meter` konečné kladné + `uncertainty` přítomna, jinak STOP.
- `coordinate_frame.verified_in_studio == true`, jinak STOP (rámec x-vpřed/y-vlevo/z-vzhůru z `units.py` by byl neověřený předpoklad).
- Každé M2 měření bez statusu = odmítnuto (G-02/G-03).

Převodní pravidlo: `target_studs = value_mm / 1000 × studs_per_meter`
(kde `studs_per_meter` pochází **výhradně** z M2 kalibrace, nikdy z konstanty `1/0.28`
— ta je definiční pro opačný směr SI→Roblox a nesmí se zaměnit za měřené měřítko modelu).

## 5. Výpočty (specifikace, ne implementace)

1. **M3.1 převod rozměrů:** `wb = 2719/1000·k`, `tf = 1585/1000·k`, `tr = 1642/1000·k`
   (`k = studs_per_meter`). Vstupy VERIFIED → výstupy `method: computed`, status dědí
   nižší z (profil-status, scale-status).
2. **M3.2–M3.4 cílový rozvor/rozchody:** viz M3.1. Kontrola P≠Z záměny: `track_f < track_r`
   (1585 < 1642); prohození → odmítnuto (M3-T09).
3. **M3.5 průměry pneu:** `686,6/1000·k` (P), `702,6/1000·k` (Z); status ESTIMATED
   (profil conf 0.6, nominální nezatížené, ±5 mm dezén) — nikdy VERIFIED.
4. **M3.6 pozice středů kol:** symetrický obdélník odvozený z cílového rozvoru/rozchodů,
   kotvený na **zadní nápravu zdrojového modelu** (stabilní referenční bod; přední náprava
   se posouvá o Δ rozvoru). Absolutní Y/Z se přebírají z inspekce (kola leží v rovině,
   ground-truth Y identické); M3 nemění světlou výšku. Každá souřadnice `isfinite`
   (reakce na AUDIT P0 — validace před každým výpočtem, ne až agregátně).
5. **M3.7 geometrický rozdíl:** řádky `{wheelbase, track_f, track_r, tire_d_f, tire_d_r}` +
   per-kolo `center.{x,y,z}`: `delta = target − source` (studs), `method: measured|computed`.
6. **M3.8 posunutí L/R kol:** vektor `target_center − source_center` po složkách (studs),
   označen `STRUCTURE_CONTROLLED` (M5 hranice — návrh posunu, ne příkaz k posunu).
7. **M3.9 symetrie a kolize:** |L−R| odchylka od středové roviny ≤ tolerance (návrh 0,5 %
   rozchodu, ke schválení); kolize kolo–karoserie: `tire_radius + rezerva < min_clearance`
   jinak `WARNING` (kolize sama o sobě neblokuje, blokuje až neřešitelný průnik —
   rozhodnutí M5/M7). Šířka/délka/výška karoserie se nekontrolují (profil je zná, model
   karoserie není v M3 rozsahu — evidováno jako neznámé).
8. **M3.10 report:** `geometry_target.json` + `geometry_diff.json` dle schémat §6;
   deterministické (stejný vstup + verze = stejný výstup, G-10); bez `scale_ref`/`inspection_ref`
   (hash + verze) je report neplatný.

## 6. JSON schémata (návrh, kompatibilní s FREEZE)

`geometry_target.json` (rozšíření FREEZE §geometry_target o statusy a verze):

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

`geometry_diff.json` (dle FREEZE §geometry_diff, `delta` v `target_unit`):

```json
[{"param": "wheelbase", "source_value": 10.52, "source_unit": "studs",
  "target_value": 0.0, "target_unit": "studs", "delta": 0.0,
  "method": "computed", "status": "VERIFIED|ESTIMATED|BLOCKED", "source_ref": "inspection:rep_xxx"}]
```

Při BLOCKED: `overall_status: BLOCKED`, `blocked_reason` povinný, všechny `value: null`
(G-04 — žádná čísla při nekonzistentním měřítku, ROADMAP M3 bod 4/11).

## 7. BLOCKED propagace (brána)

`geometry_validator.precheck()` vrací BLOCKED (a zastavuje vše pod ním), pokud platí
**koli** z: `inspection.overall_status != GEOMETRY_OK` · počet kol ≠ 4 / kterékoli kolo
UNKNOWN · `scale.overall_status == BLOCKED|UNKNOWN` · `studs_per_meter` není konečné
kladné (`isfinite`, reakce na AUDIT P0) · < 2 nezávislé reference · `coordinate_frame`
neověřen · `source_sha256` inspekce ≠ hash pracovní kopie RBXM (G-01).
BLOCKED se propaguje: celý `geometry_target.json` + celý `geometry_diff.json` BLOCKED,
žádné částečné číselné výstupy (M3-T09, G-04/G-05). Důvod + která podmínka selhala
vždy v `blocked_reason`.

## 8. Testovací scénáře (návrh; M3-T01…M3-T09)

| ID | Scénář | Očekáváno |
|---|---|---|
| M3-T01 | Převod 2719/1585/1642 mm přes `k` | studs hodnoty ± tolerance `uncertainty` |
| M3-T02 | Průměry 686,6 / 702,6 mm | ESTIMATED, dezén ±5 mm evidován |
| M3-T03 | Symetrie L/R cílového obdélníku | PASS ≤ 0,5 % rozchodu |
| M3-T04 | Prohození P/Z nápravy ve vstupu | odmítnuto |
| M3-T05 | Měřítko BLOCKED / UNKNOWN | celý report BLOCKED, `value: null` |
| M3-T06 | Kolo UNKNOWN / ≠4 kola | STOP, BLOCKED |
| M3-T07 | `size/position = +Inf/NaN` ve vstupu | per-hodnota UNKNOWN, BLOCKED (AUDIT P0) |
| M3-T08 | Diff proti reálné inspekci (ground-truth 10.5228/5.9907) | deterministický diff, G-10 |
| M3-T09 | Kolize kolo–karoserie | WARNING (průnik → eskalace M5) |

Integration: diff report proti M2 inspekci reálného RBXM; `tools/validate_contracts.py` PASS
(G-02/G-03); hash originálu RBXM beze změny (G-01).

## 9. Závislosti a rizika

- **Závislosti:** M1 DONE (profil čitelný) · M2 kalibrace M2.9/M2.10 NOT IMPLEMENTED =
  produkce M3 BLOKOVÁNA (očekávaný stav, ne selhání). M4/M5 čekají na M3 (milník M1–M3).
- **R1 kalibrace měřítka** (největší; ROADMAP M2 bod 13): bez `k` nelze nic — mitigace:
  pořadí implementace `validator → dimensions → diff`, vše za bránou.
- **R2 nominální ≠ zatížené průměry:** mitigace ESTIMATED + tolerance, M4/M7 kalibrují.
- **R3 CFrame orientace nevalidována** (AUDIT P1): mitigace — M3 orientaci nepoužívá.
- **R4 `isfinite` díry v M2 vstupu** (AUDIT P0): mitigace — `precheck` validuje každý
  float před výpočtem; neplatný vstup → UNKNOWN/BLOCKED, nikdy GEOMETRY_OK.
- **R5 EU/US a GT/Dark Horse záměna** (1585 vs 1595 / 1642 vs 1643): mitigace —
  `vehicle_id` + `scale_ref`/`inspection_ref` v každém artefaktu.
- **R6 duplicitní modul:** `src/autoengineer/` neexistuje — před kódem ověřit proti
  `src/Inspection/`, `src/common/units.py`, `PROJECT_STATUS.md` §2 (AGENTS.md pravidlo 4).

## 10. Nevyřešené otázky (fronta, neblokují návrh)

1. Tolerance symetrie (návrh 0,5 % — schválit s Agentem B/C?).
2. Kotevní bod cílových středů (návrh: zadní náprava — potvrdit).
3. Prahová hodnota kolizní rezervy kola (do M5/M7?).
4. Kam s modulem fyzicky (`src/Geometry/` vs `src/autoengineer/geometry/`) — rozhodne
   inventura D3 + vlastník repozitáře ve FÁZI B.
5. Verze kontraktů: návrh počítá s `contracts/geometry_target.schema.json` v1 dle FREEZE;
   změna jen novou verzí se zdůvodněním (koordinátor).

## 11. Doporučené další kroky (po odblokování M2)

1. FÁZE B: `geometry_validator.precheck()` + testy M3-T05…T07 první (brána dřív než čísla).
2. Poté `dimensions.py` + M3-T01/T02 proti syntetickým fixture (determinismus G-10).
3. `wheel/axle/diff` + M3-T03/T04/T08/T09; validace `validate_contracts.py`.
4. Milník M1–M3: tabulka zdroj/Mustang/rozdíl jako první skutečný výstup projektu.
