# M2.9/M2.10 — Scale Calibration Report (Agent B: kalibrace + M3 brána)

> **HISTORIE vs AKTUÁLNÍ STAV (Agent C, 2026-11-19):** tělo reportu (§0–§8) psáno na HEAD `4cad304` — historické. §9 (read-only audit na `c1a138b`) potvrdil beze změny kódu. Aktuální HEAD **`64be2c6`**: rozdíl `c1a138b..64be2c6` = pouze docs commity, `src/Inspection/scale_calibration.py` ani `tests/test_m2_scale_calibration.py` neměněny; Agent C čerstvě ověřil čtením + během **`31/31 OK`** (6 tříd, determinismus vč. přehozeného pořadí klíčů, JeepTemplate BLOCKED 7.44 %, M3 brána POUZE VERIFIED). Kalibrační engine beze změny, M3 NOT READY trvá.

Větev `feat/m2-m3-geometry`, historický HEAD `4cad304` (PR #2 NEMERGOVAT, žádné git
operace). Tvar `scale_calibration.json`
dle `reports/M2-M3-CONTRACTS-FREEZE-v1.md` (závazný, dodržen přesně).
Cíl: `ford-mustang-gt-2024-eu-manual-standard` (EUROPEAN FACTORY STANDARD).

## 0. Sjednocené statusy

| Položka | Status | Význam |
|---|---|---|
| Kalibrační engine (`scale_calibration.py`) | IMPLEMENTED | kód napsán, kontrakt dodržen |
| Testy (`test_m2_scale_calibration.py`, 31 testů) | CODE-VERIFIED | 31/31 PASS; není RUNTIME-VERIFIED (AGENTS.md pravidlo 6) |
| JeepTemplate (reálná měření, Studio ground-truth) | BLOCKED (rozptyl 7,44 %) | nekonzistentní vůči mustangovským referencím M1 — očekáváno (jiné vozidlo), kalibrace se nesmí použít |
| M3 Geometry Engine | NOT READY | brána propouští pouze VERIFIED; žádný reálný vstup dosud VERIFIED není |

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
   i oba průměry samotné, i samotný rozvor).
3. Relativní rozptyl odhadů > 5 % → `BLOCKED` (nekonzistence, M2.10).
4. Jinak: vše použité VERIFIED a max |odchylka| ≤ 2 % → `VERIFIED`,
   jinak `ESTIMATED`.

Neplatný vstup (nula/zápor/NaN/Inf u `value_si` či měření, záporná
`uncertainty_si` či `u_studs`, jiná jednotka
než `m`, chybějící zdroj, `value_si: null` bez statusu UNKNOWN, neznámý nebo
duplicitní parametr) → `CalibrationError` (výjimka, ne tichý odhad).
`value_si: null` + `UNKNOWN` je poctivé "nevím" a z kalibrace vypadává.

## 4. Brána do M3 — POUZE VERIFIED

Neověřené měřítko se nesmí dostat do M3: `usable_for_m3()` je `True` jen pro
`VERIFIED`; `require_verified_for_m3()` jinak zvedne `CalibrationBlockedError`.
ESTIMATED / UNKNOWN / BLOCKED do M3 neprojdou (testováno — včetně
explicitního testu, že konzistentní ESTIMATED z plné sady referencí bránou
neprojde).

### NÁLEZ pro koordinátora (kód NEMĚNĚN — dokumentační rozpor, vlastník Agent E)

Návrh `reports/M3/GEOMETRY-ENGINE-PROPOSAL.md` §4 (kontrakt vstupu) uvádí
`scale_calibration.overall_status ∈ {VERIFIED, ESTIMATED}` jako podmínku
průchodu do M3. To je v rozporu s pravidlem kalibrace (tento report §4,
kontrakt FREEZE, `usable_for_m3`): **do M3 smí pouze VERIFIED**.
ESTIMATED měřítko obsahuje nominální odhady pneu (conf 0,6) a nesmí škálovat
cílovou geometrii. Doporučení: Agent E v návrhu zpřísní bránu na
`overall_status == VERIFIED` (ESTIMATED → STOP/BLOCKED). Kód kalibrace se
kvůli návrhu nemění — brána je záměrně přísnější strana.

## 5. JeepTemplate: BLOCKED 7,44 % (očekáváno)

Reálná měření `JeepTemplate` (Studio ground-truth, Agent B/D — jiné vozidlo
než mustangovské reference M1, takže BLOCKED je správný výsledek, ne chyba):

| param | měření (studs) | reference SI (m) | odhad studs/m |
|---|---|---|---|
| wheelbase | 10,5228 | 2,719 | 3,87 |
| track_f | 5,9907 | 1,585 | 3,78 |
| track_r | 5,9907 | 1,642 | 3,65 |
| tire_d_f | 2,7 | 0,6866 | 3,93 |
| tire_d_r | 2,7 | 0,7026 | 3,84 |

Rozptyl odhadů **7,44 % > 5 %** → `BLOCKED` (`nekonzistentní měřítko …`),
`estimates: []`, `uncertainty: null`, brána do M3 uzavřena. Kryto testy
`TestJeepTemplateGroundTruth` (BLOCKED + `7.44` v `blocked_reason` + M3 stop).

## 6. Verifikace

- `tests/test_m2_scale_calibration.py`: **31/31 OK** (převody, determinismus
  včetně přehozeného pořadí klíčů, nula/zápor/NaN/Inf, záporné nejistoty,
  chybějící zdroj/jednotka, `null` bez UNKNOWN, neznámý/duplicitní parametr,
  1 rodina BLOCKED (pneu / rozchody / rozvor), stejná rodina 2× neplatí,
  nekonzistence 20 % i JeepTemplate 7,44 %, UNKNOWN, M3 brána
  VERIFIED-projde / ESTIMATED-UNKNOWN-BLOCKED-neprojdou / non-dict odmítnut,
  nejistota přítomna na úspěchu, tvar kontraktu).
- Plná sada `python tests/run_all.py`: **PASS, 4 PENDING** (očekávané),
  0 FAIL v tomto běhu. (Historicky flaky: `test_m2_wheel_detect.py`
  Agent B — předexistující, nestabilní mezi běhy, mimo můj rozsah;
  v tomto běhu nepadl.)

## 7. Soubory (vlastněné)

- `src/Inspection/scale_calibration.py` — beze změny (brána POUZE VERIFIED
  již v kódu; potvrzena testy, neměněna kvůli návrhu M3).
- `tests/test_m2_scale_calibration.py` — rozšířen 18 → 31 testů
  (`TestM3Gate` +2, `TestJeepTemplateGroundTruth` +2, `TestEdgeCases` +9).
- `reports/M2/SCALE-CALIBRATION-REPORT.md` — tento report (statusy §0,
  NÁLEZ §4, JeepTemplate §5).

NEMĚNĚNO: `docs/*.md` (sync dělá koordinátor), cizí moduly, návrh M3.

## 8. Shrnutí

- Hotovo: kalibrace `studs/m` s BLOCKED podmínkami, 31 testů CODE-VERIFIED,
  report; kontrakt `scale_calibration.json` dodržen bez odchylek.
- Ověřeno: 31/31 nových testů PASS; plná sada PASS + 4 PENDING;
  determinismus a M3 brána (POUZE VERIFIED) prokázány; JeepTemplate
  BLOCKED 7,44 % prokázán na reálných číslech.
- Nález: rozpor VERIFIED-vs-ESTIMATED v návrhu M3 §4 — předáno koordinátorovi,
  kód neměněn.
- Otevřené / mimo rozsah: skutečná mustangovská kalibrační čísla čekají na
  měření z RBXM (Agent B) a Studio ground-truth; do té doby je každý reálný
  výstup UNKNOWN/BLOCKED a do M3 nic neprojde. M3 NOT READY trvá.

## 9. Read-only audit 2026-11-19 (HEAD c1a138b, větev feat/m2-m3-geometry)

- `src/Inspection/scale_calibration.py::calibrate()` ověřen čtením: rodiny wheelbase/track/tire_diameter, BLOCKED pořadí (UNKNOWN → <2 rodiny → rozptyl >5 %), VERIFIED jen vše-VERIFIED + max|odchylka| ≤2 %, jinak ESTIMATED. Kód ani testy NEMĚNĚNY.
- Reference: wheelbase/track_f/track_r VERIFIED (±0,003 m), tire_d_f 0,6866 / tire_d_r 0,7026 m ESTIMATED (±0,005 m, nominální výpočet z designace) — sedí s §2.
- JeepTemplate (přesná čísla z `TestJeepTemplateGroundTruth`: 10.522796630859375 / 5.99066162109375 / 5.99072265625 / 2.7 / 2.7): `BLOCKED`, `blocked_reason` obsahuje `7.44`, `estimates: []`, `uncertainty: null`, brána `usable_for_m3()=False` + `require_verified_for_m3()` zvedá `CalibrationBlockedError` — sedí s §5.
- Brána M3: V→projde; E/U/B→neprojdou (vč. konzistentní ESTIMATED z plné sady a non-dict odmítnut) — kryto `TestM3Gate` (4 testy), ověřeno živým během.
- Návrh M3 §4/§7: NÁLEZ z §4 tohoto reportu je VYŘEŠEN — proposal nyní STRICT `overall_status == VERIFIED` (§4: "pouze VERIFIED; ESTIMATED STOP"; §7: `!= VERIFIED` → BLOCKED vč. ESTIMATED). Zbývající výskyty ESTIMATED v proposal jsou statusy per-hodnota/outputů (M3.5, schémata, M3-T02), ne díra v bráně.
- Testy: `python -m unittest tests.test_m2_scale_calibration` → **31/31 OK** (6 tříd: UnitConversions 4, Shape 4, Blocked 7, M3Gate 4, JeepTemplate 2, EdgeCases 10 — viz `grep def test` = 31).
