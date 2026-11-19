# Agent B — M2 testy, kontrakty a reprodukovatelnost

Větev `feat/m2-m3-geometry`, HEAD `9803db3`. Jazyk: čeština; kód anglicky.
Pravidla dodržena: žádný existující produkční soubor neměněn, RBXM pouze
čteny, `C:/.DATA/RobloxSimulator` nedotčen, žádná VERIFIED fixture
vydávaná za měření Mustangu, PENDING nemazáno, M3 gate neměněna, žádný
merge ani nový PR.

## 1. Výsledek v kostce

- M2 testy: **187 testů, všechny PASS** (57 parser + 53 wheel_detect +
  31 scale_calibration + 20 integrace + 7 inspector + **19 nových**
  freeze-audit). `validate_contracts.py`: 24 kontrol, 0 chyb.
- Čtyři M2/M3 výstupy (`inspection_report`, `scale_calibration`,
  `geometry_target`, `geometry_diff`) **neexistují jako soubory na disku**
  — žijí jen jako in-memory tvary + závazný textový freeze. To je pro M2
  správně (žádný soubor = žádné falešné tvrzení), ale znamená to:
  **žádný z nich nemá `.schema.json` v `contracts/` a `validate_contracts.py`
  je nekontroluje**.
- Kritické stavy (jednotky, provenience, UNKNOWN/null, ESTIMATED / VERIFIED /
  BLOCKED, propagace blokací, determinismus, reprodukovatelnost) jsou
  pokryty testy; brána M3 je na reálných datech zavřená (BLOCKED 7,44 %).
- Změnu kontraktu **NENAVRHUJI k implementaci**
  (`needs-coordinator-approval` by byla vyžadována — viz §5).

## 2. Existence a validace čtyř výstupů

| Výstup | Soubor na disku | Producent (kód) | Freeze tvar | `.schema.json` | `validate_contracts.py` |
|---|---|---|---|---|---|
| `inspection_report.json` (M2) | NE (in-memory) | `build_inspection_report` / `report_from_assess` v `src/Inspection/wheel_detect.py` + in-code `INSPECTION_REPORT_SCHEMA` | ANO (`M2-M3-CONTRACTS-FREEZE-v1.md` §inspection_report) | **CHYBÍ** | NEKONTROLUJE |
| `scale_calibration.json` (M2) | NE (in-memory) | `calibrate()` v `src/Inspection/scale_calibration.py` | ANO (§scale_calibration) | **CHYBÍ** | NEKONTROLUJE |
| `geometry_target.json` (M3) | NE — správně, brána zavřená | neexistuje (až po bráně, producent Agent E) | ANO (tvar pro M3) | **CHYBÍ** | NEKONTROLUJE |
| `geometry_diff.json` (M3) | NE — správně, brána zavřená | neexistuje (až po bráně) | ANO (tvar pro M3) | **CHYBÍ** | NEKONTROLUJE |

Ověřeno: `validate_contracts.py` pokrývá pouze 9 schémat
(`vehicle_profile`, `reference_profile`, `vehicle_config`, `change_plan`,
`test_result`, `diagnosis`, `chassis_info`, `scenario`, `manifest`) +
`vehicle-data/references/*`. Tvar M2 výstupů je místo toho držen třemi
nezávislými kotvami, které jsem proti sobě zkontroloval a shodují se:
freeze-dokument, in-code `INSPECTION_REPORT_SCHEMA` (+ testy klíčů v
`test_m2_integration.py` / `test_m2_wheel_detect.py`) a skutečné výstupy
(`_ok_report()` vrací list 4 kol, klíče shodné s freeze; `calibrate()`
vrací přesně freeze-klíče, reference `{param, value_si, unit, source,
status}`, `unit == "m"`).

## 3. Freeze schémat pro M2 výstupy (potvrzeno testy)

- `inspection_report.json`: `{report_id, vehicle_id, source_file,
  source_sha256, parser_version, code_version, wheels: [{designation,
  instance_id, class_name, center_studs{x,y,z}, size_studs{x,y,z}, shape,
  status, reason}], axles{front,rear}, wheelbase_studs,
  tire_diameters_studs{FL,FR,RL,RR}, coordinate_frame{x,y,z,
  verified_in_studio}, method, warnings[], overall_status ∈
  {GEOMETRY_OK, UNKNOWN, BLOCKED}}`. Vše studs; status povinný u každého
  měření. Nadstavba `known_non_wheels` je dokumentovaná a testy povolená.
- `scale_calibration.json`: `{vehicle_id, inspection_ref,
  references[{param, value_si, unit, source, status}],
  measurements_studs{wheelbase, track_f, track_r, tire_d_f, tire_d_r},
  estimates[{param, studs_per_meter}], deviations_pct, uncertainty,
  overall_status ∈ {VERIFIED, ESTIMATED, UNKNOWN, BLOCKED},
  blocked_reason}`. Jednotky SI + studs; < 2 nezávislé rodiny → BLOCKED.
- `geometry_target.json` / `geometry_diff.json`: tvary zmrazeny pro M3,
  žádný producent v `src/`/`tools/`/`contracts/` neexistuje (ověřeno
  grepem) — konzistentní se zavřenou bránou.

## 4. Kritické stavy — pokrytí

- **Jednotky**: report vše studs; kalibrace `unit == "m"` + `value_si`,
  ne-SI `unit` odmítnuto výjimkou; `src/common/units` (mm/m, pneu
  686,6/702,6 mm, studs↔m roundtrip) testováno. ✅
- **Provenience**: `source_file + source_sha256 + parser_version +
  code_version + method + report_id` (report); `inspection_ref +
  references[].source + status` (kalibrace); M1 reference nesou zdroj
  `[1b]+[3]`. ✅
- **UNKNOWN / null**: chybějící kolo → `instance_id/center/size None` +
  `reason: missing_wheel`, nikdy vymyšlená čísla; vše-None měření →
  UNKNOWN, `estimates == []`, `blocked_reason None`; `value_si: null`
  vyžaduje status UNKNOWN (jinak `CalibrationError`). ✅
- **ESTIMATED / VERIFIED / BLOCKED**: plná sada Mustangu konzistentní →
  ESTIMATED (pneu nejsou VERIFIED reference) → brána M3 zavřená; vše
  VERIFIED + odchylky ≤ 2 % → VERIFIED (jen syntetika); rozptyl > 5 % →
  BLOCKED; JeepTemplate reálná data → BLOCKED 7,44 %, `estimates == []`,
  nejistota `None`. ✅
- **Propagace blokací**: assess BLOCKED (`float_decode_unverified`) →
  report BLOCKED (I-1 opraveno, test vymáhá); BLOCKED/ESTIMATED/UNKNOWN
  kalibrace → `usable_for_m3 == False` + `require_verified_for_m3`
  zvedá `CalibrationBlockedError`; `usable_for_m3` odmítá i ne-dict. ✅
- **Determinismus**: parse / detect / assess / report / kalibrace i celý
  řetězec (G-10) včetně JSON roundtripu a nezávislosti na pořadí klíčů. ✅
- **Reprodukovatelnost**: stejný vstup + stejná verze = stejný výstup;
  RBXM read-only (SHA před/po shodný, `dc8747e0…fefdf`, 230421 B);
  chybějící kopie → SKIP (PENDING), nikdy tichý PASS; žádný runtime
  verdikt bez Studia (G-06/G-07, žádný `run_id`/`studio_play` token). ✅

## 5. Testovací matice (vstup → očekávané → test → pokrytí / mezery)

| # | Vstup | Očekávané | Test (soubor) | Pokrytí | Chybějící test / riziko |
|---|---|---|---|---|---|
| 1 | RBXM kopie (815 inst., 37 typů) | census, 4× Ball id 3/52/101/150, MSB-first, 0 unread shape-enumů | `test_m2_rbxm_parser` (57), `test_m2_rbxm_inspector` (7) | ✅ plné | — |
| 2 | Syntetická hierarchie (a)+(b)+(c) | 4-tier VALID/KNOWN_NON_WHEEL/UNKNOWN/INVALID, BLOCKED podmínky (cyklus, les, duplicita, chybějící parent) | `test_m2_wheel_detect` (53) | ✅ plné vč. 18 testů 4-tier | — |
| 3 | Studio centra/rozměry | track ≈ 5,99, rozvor ≈ 10,52, pneu 2,7; rámec x=lateral/y=up/z=longitudinal (rozpor s příkazem zdokumentován) | wheel_detect + integrace | ✅ plné | Nízké: toleranční pásma svázána s jedním modelem (dc8747e0) — při novém modelu znovu ověřit |
| 4 | Konzistentní syntetika (scale 3,0) | ESTIMATED (plná sada) / VERIFIED (jen VERIFIED refy) | `test_m2_scale_calibration` (31) | ✅ plné | — |
| 5 | Nekonzistence / < 2 rodiny / vše-None / nula / zápor / NaN / inf / špatná jednotka / prázdný source / duplicitní param | BLOCKED+reason / UNKNOWN / `CalibrationError` | scale_calibration | ✅ plné | — |
| 6 | Celý řetězec na reálné kopii | report BLOCKED (propagace), kalibrace BLOCKED 7,44 %, M3 zavřená, determinismus, read-only | `test_m2_integration` (20) | ✅ plné | — |
| 7 | Freeze-tvary obou M2 výstupů | klíče/enumy shodné s freeze, provenience, oddělení studs/SI, JSON roundtrip, žádný M3 výstup bez brány | **nový** `test_m2_contract_freeze` (19) | ✅ nově pokryto | Zbytkové: strojové `.schema.json` + validátor — **NENAVRHUJI bez `needs-coordinator-approval`** |
| 8 | `geometry_target/diff` (M3) | neexistují, dokud brána není VERIFIED | freeze + gate testy (nepřímo) | ⚠️ částečné | Při otevření brány bude potřeba producent + schéma + testy (vlastník Agent E, až po bráně) |
| 9 | `contracts/*.schema.json` pro 4 výstupy + `validate_contracts.py` | strojová validace M2/M3 tvarů | — | ❌ chybí | Vědomě neimplementováno zde (změna kontraktu → flag koordinátora) |

## 6. Nově vytvořené soubory

- `tests/test_m2_contract_freeze.py` (19 testů, vše PASS) — freeze-audit
  M2 tvarů, provenience, jednotek, UNKNOWN/null, propagace blokací až
  k bráně M3, determinismu; pouze syntetika, žádná VERIFIED fikce.
- `reports/NIGHT-WORK/AGENT-B-M2-TEST-AND-CONTRACT-AUDIT.md` (tento report).

Žádný existující produkční/testovací soubor nebyl měněn (`git status`
čistý kromě těchto dvou nových souborů).

## 7. Ověření běhů

- `python -m unittest tests.test_m2_rbxm_parser tests.test_m2_wheel_detect
  tests.test_m2_scale_calibration tests.test_m2_integration
  tests.test_m2_rbxm_inspector tests.test_m2_contract_freeze` →
  **187 testů, OK** (57 + 168 ověřeno ve dvou bězích: 57 parser OK;
  111+19 ostatních OK).
- `python tools/validate_contracts.py` → 24 kontrol, 0 chyb.
