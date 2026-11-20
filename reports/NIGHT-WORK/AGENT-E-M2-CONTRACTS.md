# Agent E — M2 kontrakty a validace (NÁVRH, PROPOSED)

Větev `feat/m2-m3-geometry`, báze `90a1f63c` (strom čistý, ověřeno `git status`).
M3 ZAVŘENÁ — žádný kód, žádná produkce `geometry_target/diff`; tento dokument a
`contracts/proposed/` jsou jediný výstup. Vše níže je **PROPOSED — čeká na schválení**,
validátor nic z toho dnes nekontroluje.

## 1. Stav 4 schémat: existuje / chybí

| Výstup | `contracts/*.schema.json` | Tvar jinde | Návrh v `contracts/proposed/` | Schválená validace |
|---|---|---|---|---|
| `inspection_report.json` (M2) | **CHYBÍ** | ANO — freeze §inspection_report + in-code `INSPECTION_REPORT_SCHEMA` (`wheel_detect.py`) + producent `build_inspection_report` | `inspection_report.schema.json` PROPOSED | NE — validátor nekontroluje |
| `scale_calibration.json` (M2) | **CHYBÍ** | ANO — freeze §scale_calibration + producent `calibrate()` (`scale_calibration.py`) | `scale_calibration.schema.json` PROPOSED | NE — validátor nekontroluje |
| `geometry_target.json` (M3) | **CHYBÍ** (správně, brána zavřená) | ANO, jen návrh — freeze §geometry_target + `reports/M3/GEOMETRY-ENGINE-PROPOSAL.md` §6 | `geometry_target.schema.json` PROPOSED | NE — validátor nekontroluje |
| `geometry_diff.json` (M3) | **CHYBÍ** (správně, brána zavřená) | ANO, jen návrh — freeze §geometry_diff + M3-proposal §6 | `geometry_diff.schema.json` PROPOSED | NE — validátor nekontroluje |

Návrh vs schválená validace: schváleno a validováno je dnes 9 schémat
(`vehicle_profile`, `reference_profile`, `vehicle_config`, `change_plan`,
`test_result`, `diagnosis`, `chassis_info`, `scenario`, `manifest`) přes
`SCHEMA_FILES` + `EXAMPLE_FOR_SCHEMA` + `INVALID_SAMPLES` + kontrolu
`vehicle-data/references/`. 4 nová schémata jsou **pouze návrhy** v
`contracts/proposed/`; validátor je automaticky neobjevuje (záměrně, neměněn).

Jak validátor dnes validuje (podporovaná podmnožina draft 2020-12):
`type` (vč. seznamů typů), `const`, `enum`, `required`, `properties`,
`additionalProperties`, `pattern`, `minimum/maximum`,
`exclusiveMinimum/exclusiveMaximum`, `min/maxItems`, `min/maxLength`,
`min/maxProperties`, `items`, `anyOf/oneOf/allOf`, `$ref` lokální `#/$defs`,
`format: date` + ruční kódované pravidlo ARCH §3.2 (`$comment`
`proven-null-confidence-0`). Vše 4 návrhy jsou psány **pouze touto podmnožinou**,
takže je stávající engine umí zkontrolovat bez úprav (ověřeno sondami, §5).

## 2. Návrhová rozhodnutí (společná pro 4 schémata)

- **Žádný druhý systém stavů.** Použity pouze existující slovníky:
  inspekce `GEOMETRY_OK | UNKNOWN | BLOCKED` (freeze + `wheel_detect.py`);
  kalibrace/M3 `VERIFIED | ESTIMATED | UNKNOWN | BLOCKED` (freeze + `scale_calibration.py`).
  Vědomá ODCHYLKA od M3-proposal §6: tamní `overall_status: OK | BLOCKED` pro
  `geometry_target` **nepřebírám** (`OK` by byl nový stav). Místo něj
  `VERIFIED | ESTIMATED | UNKNOWN | BLOCKED`.
- **`PASS` zakázán v M2/M3 výstupech.** `PASS/PENDING` patří katalogu Agenta A
  (`src/Chassis/catalog/loader.py`, `mapping_engine.py`), ne M2/M3 geometrii —
  viz negativní případ N6.
- **Jednotky:** inspekce vše studs (implicitní, bez jednotkových klíčů — jako freeze);
  kalibrace reference `unit: const "m"` (SI), měření studs; target `units: const "studs"`;
  diff `source_unit/target_unit: enum ["studs", "m"]`, `delta` v `target_unit`.
- **Provenance povinná:** `source_file/sha256/parser_version/code_version/method/report_id`
  (inspekce); `source` u každé reference (kalibrace); `source_ref` u každé
  hodnoty (target) a každého řádku (diff); `scale_ref` + `inspection_ref` (target).
- **Chybějící údaj = null + UNKNOWN/BLOCKED, nikdy vymyšlené číslo**
  (analogie ARCH §3.2; viz podmíněné kontroly C-*).

## 3. Seznam chybějících kontrol (validátor dnes nekontroluje)

1. Žádné ze 4 schémat není registrováno (`SCHEMA_FILES`, `--list`, `--schema`).
2. Žádné validní/nevalidní příklady ke 4 výstupům v selftestu.
3. Podmíněné (meziklíčové) požadavky — engine-podmnožina je neumí, potřeba kód:
   C-IR1 `overall BLOCKED ⇒ warnings non-empty + důvod`; C-IR2 `GEOMETRY_OK ⇒
   center/size non-null + reason null`; C-IR3 `center/size null ⇒ status ≠
   GEOMETRY_OK`; C-IR4 `verified_in_studio=false ⇒ overall ≠ GEOMETRY_OK`
   (strop UNKNOWN); C-IR5 `rozvor/rozchod/průměr null ⇒ overall ≠ GEOMETRY_OK`.
   C-CAL1 `value_si null ⇒ status UNKNOWN`; C-CAL2 `BLOCKED ⇒ blocked_reason
   non-empty + estimates []`; C-CAL3 `UNKNOWN ⇒ estimates []`;
   C-CAL4 `overall VERIFIED/ESTIMATED ⇒ estimates non-empty`.
   C-GT1 M3 brána: číselné `value` jen při `scale_ref.calibration_status ==
   VERIFIED` (jinak vše `value: null`); C-GT2 `BLOCKED ⇒ blocked_reason
   non-empty + všechny value null`; C-GT3 `calibration_status ≠ VERIFIED ⇒
   overall_status ≠ VERIFIED` (žádné UNKNOWN-za-VERIFIED).
   C-GD1 `status BLOCKED na vstupu ⇒ všechny řádky BLOCKED + hodnoty/delta null`;
   C-GD2 `delta == target − source` (v `target_unit`) mimo BLOCKED.
4. M3 brána jako celek (`usable_for_m3` / `require_verified_for_m3` ekvivalent):
   `inspection.overall_status == GEOMETRY_OK` + `scale == VERIFIED` +
   `verified_in_studio` + shoda `source_sha256` — jinak `geometry_target/diff`
   nesmí vzniknout (dnes kryto jen nepřímo testem `test_no_m3_outputs_without_verified_scale`).
5. `contracts/proposed/` je validátorem záměrně ignorováno (žádné auto-objevování).

## 4. Návrh rozšíření `tools/validate_contracts.py` (POPIS, bez implementace)

Až po schválení návrhů (koordinátor), vše v jednom kroku, po vzoru existujícího
kódu (precedent: `_PROVEN_NULL_CONFIDENCE_COMMENT` + `_is_m19_empty_torque_curve`):
1. `SCHEMA_FILES` += `inspection_report`, `scale_calibration`, `geometry_target`,
   `geometry_diff`; `EXAMPLE_FOR_SCHEMA` += 4 nové `*.valid.json` (vytvořit v
   `contracts/examples/` — mimo scope tohoto návrhu, příklady viz §5/§6 tohoto reportu);
   `INVALID_SAMPLES` += 4 nevalidní vzorky (minimálně případy N1–N4, N6, N7 níže).
   `geometry_diff` je top-level **pole** — `run_selftest` s tím počítá (validní
   příklad je JSON array).
2. Nové kódované kontroly (funkce, ne JSON Schema — nad rámec podmnožiny):
   `check_ir_consistency` (C-IR1–C-IR5), `check_cal_consistency` (C-CAL1–C-CAL4),
   `check_m3_gate` (C-GT1–C-GT3 + brána §3-bod 4, reuse logiky
   `usable_for_m3`/`require_verified_for_m3`), `check_diff_consistency`
   (C-GD1–C-GD2). Volat ze `run_selftest` po průchodu schématem.
3. Selftest += gate testy: ESTIMATED/UNKNOWN/BLOCKED kalibrace → `check_m3_gate`
   STOP (precedent `test_non_verified_never_passes_m3_gate`); BLOCKED inspekce →
   celý target/diff BLOCKED s `value: null`.
4. `contracts/proposed/` zůstává validátorem ignorováno i nadále; schválená
   schémata se přesouvají do `contracts/` (nová verze se zdůvodněním, politika freeze).

## 5. Negativní testovací případy (POPIS + JSON)

Legenda: REJECTED = zamítne už schéma (ověřeno sondou proti stávajícímu enginu);
GATE-STOP = projde schématem, musí zastavit kódovaná kontrola z §4 (dnes neexistuje).

- **N1 chybějící klíč** — report bez `overall_status`. Očekáváno REJECTED
  (`chybí povinné pole 'overall_status'`).
  `{"schema_version":"1.0.0","report_id":"synth@abab…","vehicle_id":"synth",…}` bez klíče `overall_status`.
- **N2 špatný typ** — `"wheelbase_studs": "deset"`. Očekáváno REJECTED
  (očekáváno číslo nebo null).
- **N3 neplatná jednotka/enum** — reference `"unit": "cm"` (povoleno jen `"m"`);
  target `"units": "meters"` (povoleno jen `"studs"`). Očekáváno REJECTED.
  `{"param":"wheelbase","value_si":2.719,"unit":"cm","source":"x","status":"VERIFIED"}`
- **N4 chybějící provenance** — reference bez `source`. Očekáváno REJECTED
  (`chybí povinné pole 'source'`).
  `{"param":"track_f","value_si":1.585,"unit":"m","status":"VERIFIED"}`
- **N5 UNKNOWN za VERIFIED** — kalibrace `overall_status: ESTIMATED` (nebo UNKNOWN)
  vydávaná za vstup M3: `geometry_target` s číselnými `value` při
  `scale_ref.calibration_status: "ESTIMATED"`. Schéma projde, očekáváno
  GATE-STOP dle C-GT1/C-GT3 (brána: jen VERIFIED; precedent
  `require_verified_for_m3` zvedá `CalibrationBlockedError`).
  `{"scale_ref":{"calibration_status":"ESTIMATED","studs_per_meter":2.98,…},"wheelbase_studs":{"value":8.1,…}}`
- **N6 BLOCKED za PASS** — `"overall_status": "PASS"` (katalogový slovník Agenta A
  nepatří do M2/M3). Očekáváno REJECTED (hodnota není mezi povolenými).
  Platí pro všechna 4 schémata; sonda ověřena na `inspection_report` i `geometry_diff`.
- **N7 chybějící identifikátor** — report bez `vehicle_id` (resp. target bez
  `scale_ref` / diff řádek bez `source_ref`). Očekáváno REJECTED.
  Sondy N1–N4, N6, N7 + varianty N3b/N6b ověřeny: validní sondy PASS (4/4),
  strukturální negativy REJECTED (8/8), reálné výstupy producentů
  (`build_inspection_report`, `calibrate` OK i BLOCKED) PASS (3/3).

## 6. Ověření provedené Agentem E (read-only + nové soubory)

- Přečteno: `contracts/` (9 schémat), `tools/validate_contracts.py` (595 řádků),
  freeze `reports/M2-M3-CONTRACTS-FREEZE-v1.md`, producenti
  `src/Inspection/wheel_detect.py` + `scale_calibration.py`, M3-proposal §6–§8,
  testy `test_m2_contract_freeze.py` (+ Agent-B audit v NIGHT-WORK).
- NÁLEZ F-1: producenti M2 neemits `schema_version` (freeze ho nevyžaduje,
  in-code schéma ho nemá) — proto je v M2 návrzích `schema_version` **volitelné**
  (`const 1.0.0`, je-li přítomno); v M3 návrzích **povinné** (nové artefakty,
  konvence repozitáře). → otázka Q-1 ke schválení.
- Vytvořeny 4 soubory `contracts/proposed/*.schema.json` (pouze podmnožina
  enginu: `const/enum/required/pattern/anyOf/$ref`); sondy existujícím enginem:
  4/4 validní PASS, 8/8 negativních REJECTED, 3/3 reálné výstupy PASS.
- `tools/validate_contracts.py`, existující schémata, RBXM ani `main`/PR#2 nedotčeny.

## 7. Otázky ke schválení (neblokují návrh)

- Q-1: `schema_version` u M2 výstupů — ponechat volitelné (freeze-věrné), nebo
  vyžadovat a doplnit producenty (změna kódu Agent B/C)?
- Q-2: `status_per_value` v `geometry_target` ponecháno volitelné (redundantní
  s per-hodnota statusy) — ponechat, nebo při schválení vypustit?
- Q-3: Potvrdit odchylku od M3-proposal §6 (`overall_status` bez `OK`, §2).
