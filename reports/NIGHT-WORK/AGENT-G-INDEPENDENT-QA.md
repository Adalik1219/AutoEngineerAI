# Agent G — Nezávislá QA vlny (feat/m2-m3-geometry)

- HEAD SHA: `90a1f63c184ef4dddbc134de47bc627adc8dce46` (= výchozí SHA; změny vlny jsou **necommitnuté** v pracovním stromě)
- Datum: 2026-11-20. Runner: `unittest`. RBXM pouze čteno. M3 nedotčena.

## 1. Git status / diff

- `git status --porcelain`: `M src/Chassis/mapping/cycle_check.py`, `M tests/test_m2_scale_calibration.py`,
  `M tests/test_m5_cycle_check.py`, `?? contracts/proposed/` (4 soubory), `?? src/Chassis/mapping/validate_catalog.py`,
  `?? reports/NIGHT-WORK/` (6 nových: COORDINATOR-BASELINE, AGENT-A-S02-CATALOG-AUDIT, AGENT-C-S02-TESTS,
  AGENT-D-CHASSIS-MUSTANG-STRATEGY, AGENT-E-M2-CONTRACTS, AGENT-F-MUSTANG-PHYSICS-MAPPING).
- Trackované změny = přesně 3 soubory výše. `test_m2_scale_calibration.py` diff = **právě 2 řádky**
  (`calibrate(vehicle_id="JeepTemplate", …)` ve 2 testech, label-fix P-D1). ✅
- Existující `.md` / `docs/` / `FINAL-NIGHT-REPORT.md`: **0 úprav** (diff prázdný). ✅
- `tools/validate_contracts.py` + všech 9 existujících `contracts/*.schema.json`: **nedotčeny** (diff prázdný). ✅

## 2. S-02 — nezávislé ověření (vlastní běh, ne opsání testů)

- `parameters.json` načten nezávisle: **138 parametrů / 101 hran** (`depends_on`). Tvrzení 138/101 ✅.
- `has_cycle` nad katalogem (vlastní běh): `has_cycle=True`,
  svědek `['tcs_threshold_sps', 'tcs_gradient', 'tcs_threshold_sps']`, `checked_nodes=138`, `checked_edges=101`,
  `integrity_errors=[]`.
- Svědek ověřen hranu po hraně proti `parameters.json`:
  `tcs_threshold_sps -> ['tcs_gradient', 'tcs_limit_pct']` ✅ a `tcs_gradient -> ['tcs_threshold_sps']` ✅.
  Uzavřená cesta, každá dvojice je skutečná hrana. Jde o **reálný 2-cyklus v katalogu**, ne artefakt.
- Povinný graf `a->[b,c], b->[c], c->[a]` (vlastní běh): `has_cycle=True`, svědek `['a','b','c','a']`,
  edge-check všech dvojic ✅, uzavřenost ✅.
- Negativní sondy (vlastní běh přes `validate_records_for_mapping`):
  cyklický katalog → `BLOCKED` (`CYCLE: …`), ne `PASS` ✅;
  neexistující id → `BLOCKED` (`INTEGRITY: … (x -> ghost)`) — **jiný důvod než cyklus**, ne `PASS` ✅.
- Reálný katalog → `validate_catalog_for_mapping` = `BLOCKED` (`CYCLE: … tcs_threshold_sps -> tcs_gradient -> …`),
  `allowed=False`. Mapování je tedy **správně zablokováno**, dokud se cyklus nerozbije (test
  `test_real_catalog_blocked_for_mapping` to assertuje — konzistentní, ne rozpor).
- Poznámka k „12 cyklům" (audit §5): detektor garantuje jen **existenci + 1 svědka**; číslovku 12 jsem
  nezávisle nepřepočítával (vyžadovalo by enumeraci, kterou API záměrně nedělá — viz §3). Alespoň 1 cyklus
  je prokázán výše; auditní seznam párů k rozbití (§5, ř. 206) je manuální analýza, ne výstup detektoru.

## 3. Žádný slib nad možnosti detektoru

- `find_cycles` je `DEPRECATED` s `DeprecationWarning` a docstringem, který výslovně říká, že původní
  naivní DFS s BLACK-řezem některé cykly nenajde a jméno klamalo. ✅
- `has_cycle`/`find_witness` docstringy: „existence, NE výpočet všech cyklů", „každý dosažitelný cyklus
  je nalezen (existence…)". Žádný Johnson, žádný slib enumerace v nedeprecovaném API. ✅
- `grep` po „všechny cykly / all cycles" v `mapping/*.py`: pouze DEPRECATED kontext. ✅
- `KNOWN_DEPENDS` označen jako pomocná reference (~1 % hran), konflikty vyloučeny z grafu se zdůvodněním
  (symetrická relace → falešné 2-cykly). ✅

## 4. Strategie (Agent D) — Jeep vs. Mustang

- `grep JeepTemplate` ve `src/Inspection/scale_calibration.py` a celém `src/Chassis/`: **0 výskytů**. ✅
- `calibrate` default `vehicle_id = "ford-mustang-gt-2024-eu-manual-standard"`; `src` neobsahuje žádné
  Jeep hodnoty jako Mustang hodnoty. ✅
- Výskyty `JeepTemplate` v testech = fixture RBXM (`testgame/.../JeepTemplate.rbxm`),
  `TestJeepTemplateGroundTruth` (Jeep měření → správně BLOCKED proti mustangovským referencím, rozptyl 7.44 %),
  a default `vehicle_id` v **testovacím** helperu `_ok_report` (wheel_detect) — žádný aktivní kalibrační
  odkaz Jeep→Mustang v produkčním kódu. ✅
- A-Chassis základ: `src/Chassis/adapters/`, `base.py` beze změn (nejsou ve statusu); strategie drží
  `achassis-v1` a audit jako zdroj. Chybějící Mustang údaj = UNKNOWN (strategie ř. 15, 95, 121–122, 134–135;
  `calibrate` vrací UNKNOWN při absenci měření). ✅

## 5. M2 schémata

- `contracts/proposed/`: 4 nové návrhy (`geometry_diff`, `geometry_target`, `inspection_report`,
  `scale_calibration`), každý obsahuje PROPOSED marker (2 výskyty/soubor). ✅
- Nevstupují do validační cesty: `validate_contracts.py` + existující schémata nedotčeny (§1). ✅

## 6. Vlastní čísla (nezávislé běhy, HEAD 90a1f63 + necommitnuté změny vlny)

| Sada | Výsledek |
|---|---|
| `python -m unittest tests.test_m5_cycle_check` | **32/32 OK** |
| `python -m unittest tests.test_m2_scale_calibration` | **31/31 OK** |
| `python tests/run_all.py` | **běhů 436, PASS 432, FAIL 0, ERROR 0, PENDING 4** (4 PENDING deklarované, nejde o PASS) |
| `python tools/validate_contracts.py` | **24 kontrol, 0 chyb** |

Všechna tvrzená čísla (32/32, 436/432/0/0/4, 24/24) **souhlasí** s vlastními běhy.

## Verdikt: PASS

Se stopou: reálný katalog je dnes pro mapování **BLOCKED** (prokázaný 2-cyklus `tcs_*`) — to je správné
chování brány, ne vada vlny. Odblokování = rozbití cyklů dle auditu §5 (koordinace s M3, M3 zůstává ZAVŘENÁ).
Žádná odchylka od tvrzení vlny nenalezena; D-`.md` úpravy 0; M2 label-fix přesně 2 řádky.
