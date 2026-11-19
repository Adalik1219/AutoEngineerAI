# M2.9/M2.10 — Scale Calibration Report (Agent C)

Větev `feat/m2-m3-geometry`, HEAD `ab8409a`. Tvar `scale_calibration.json`
dle `reports/M2-M3-CONTRACTS-FREEZE-v1.md` (závazný, dodržen přesně).
Cíl: `ford-mustang-gt-2024-eu-manual-standard` (EUROPEAN FACTORY STANDARD).

## 1. Metoda

`src/Inspection/scale_calibration.py::calibrate()` — čistá funkce, stdlib only.
Pro každý použitelný pár (reference SI + měření studs) odhad
`studs_per_meter = meas_studs / value_si_m`; kombinace inverse-variance
z nejistot referencí a měření (`u_studs`, default 0,05 studs) + poloviční
rozpyl odhadů. Deterministické (řazené parametry, pevné pořadí součtů).

## 2. Reference (profil M1, SI metry; rozchod/průměr nejsou automaticky přesné)

| param | value_si | status | zdroj | nejistota |
|---|---|---|---|---|
| wheelbase | 2,719 m | VERIFIED | [1b] + [3] shodně 2719 mm | ±0,003 m |
| track_f | 1,585 m | VERIFIED | [1b], sloupec Mustang GT | ±0,003 m |
| track_r | 1,642 m | VERIFIED | [1b], sloupec Mustang GT | ±0,003 m |
| tire_d_f | 0,6866 m | ESTIMATED | nominální výpočet z 255/40 R19 (`tire_diameter_mm`) | ±0,005 m |
| tire_d_r | 0,7026 m | ESTIMATED | nominální výpočet z 275/40 R19 (`tire_diameter_mm`) | ±0,005 m |

Průměry pneu jsou nominální (nevýpočtový, nezatížený) průměr z designace —
ODHAD s tolerancí dezénu, nikdy VERIFIED. Ověřeno: `tire_diameter_mm(255,40,19)
= 686,6`, `(275,40,19) = 702,6` (test).

## 3. Nezávislost a BLOCKED podmínky (pořadí závazné)

Rodiny: `wheelbase | track (track_f+track_r) | tire_diameter (tire_d_f+tire_d_r)`.
Dva údaje ze stejné rodiny = 1 nezávislá reference.

1. Měření zcela chybí (vše `None`) → `UNKNOWN` (není co kalibrovat).
2. < 2 nezávislé použitelné rodiny → `BLOCKED` (i track_f+track_r samotné,
   i oba průměry samotné).
3. Relativní rozptyl odhadů > 5 % → `BLOCKED` (nekonzistence, M2.10).
4. Jinak: vše použité VERIFIED a max |odchylka| ≤ 2 % → `VERIFIED`,
   jinak `ESTIMATED`.

Neplatný vstup (nula/zápor/nonn-finite u `value_si` či měření, jiná jednotka
než `m`, chybějící zdroj, `value_si: null` bez statusu UNKNOWN, neznámý nebo
duplicitní parametr) → `CalibrationError` (výjimka, ne tichý odhad).
`value_si: null` + `UNKNOWN` je poctivé "nevím" a z kalibrace vypadává.

## 4. Brána do M3

Neověřené měřítko se nesmí dostat do M3: `usable_for_m3()` je `True` jen pro
`VERIFIED`; `require_verified_for_m3()` jinak zvedne `CalibrationBlockedError`.
ESTIMATED / UNKNOWN / BLOCKED do M3 neprojdou (testováno).

## 5. Verifikace

- Nový `tests/test_m2_scale_calibration.py`: **18/18 OK** (převody, determinismus
  včetně přehozeného pořadí klíčů, nula/zápor, nekonzistence, UNKNOWN,
  <2 reference, M3 brána, tvar kontraktu).
- Plná sada `python tests/run_all.py`: PASS 312, 4 PENDING (očekávané),
  **1 FAIL v `test_m2_wheel_detect.py` (Agent B, mnou nedotčeno) — předexistující
  a nestabilní mezi běhy** (střídá `test_schema_has_required_top_level_keys` /
  `test_missing_wheel_blocked`; selhává na `INSPECTION_REPORT_SCHEMA`, nikoli na
  kalibraci). K tomu kolísá celkový počet běhů (297–317) — flaky F4 část sady,
  mimo můj rozsah.
- Změna `src/common/units.py` je čistě aditivní (`mm_to_m`, `m_to_mm`,
  `tire_diameter_mm`, konstanty `MM_PER_INCH`/`MM_PER_M`); žádný existující
  podpis nesáhnut.

## 6. Soubory (vlastněné)

- `src/common/units.py` — jen rozšíření (viz §5).
- `src/Inspection/scale_calibration.py` — nový (kalibrace + M3 brána).
- `tests/test_m2_scale_calibration.py` — nový (18 testů).
- `reports/M2/SCALE-CALIBRATION-REPORT.md` — tento report.

## 7. Shrnutí

- Hotovo: kalibrace `studs/m` s BLOCKED podmínkami, testy i report; kontrakt
  `scale_calibration.json` dodržen bez odchylek.
- Ověřeno: 18/18 nových testů PASS; determinismus a M3 brána prokázány.
- Nevytvářen duplicitní modul: `units.py` pouze rozšířen.
- Otevřené / mimo rozsah: skutečná kalibrační čísla čekají na měření z RBXM
  (Agent B) a Studio ground-truth; do té doby je každý reálný výstup
  UNKNOWN/BLOCKED a do M3 nic neprojde. Flaky FAIL v `test_m2_wheel_detect.py`
  patří Agentu B — neopravován (cizí vlastnictví).
