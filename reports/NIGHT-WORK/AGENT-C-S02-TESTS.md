# Agent C — S-02: testy a integrace validace cyklu

- Repo: `C:/.DATA/AutoEngineerAI`, větev `feat/m2-m3-geometry`, výchozí SHA `90a1cf3`
- Datum: 2026-11-20. Čeština; kód anglicky.
- Omezení dodržena: čten celý repozitář; zapsány pouze `tests/test_m5_cycle_check.py`,
  tento report a JEDEN nový integrační modul `src/Chassis/mapping/validate_catalog.py`;
  `cycle_check.py`, validátory a mapovače NEEDITOVÁNY. RBXM jen čtena, M3/main/PR#2 nedotčeny.

## 1. Co bylo uděláno

1. Migrace starých testů na nové API Agenta B (`CycleResult` sémantika) —
   rozbitý `test_known_tables_acyclic` opraven (`check_known_tables()` vrací
   `CycleResult`, ne list).
2. Přidán povinný překryvový graf `a->[b,c], b->[c], c->[a]` s ověřením svědka
   hranu po hraně (uzavřená cesta v grafu, ne jen non-None).
3. Přidány všechny požadované případy (viz §3).
4. Vytvořen JEDEN nový tenký modul `src/Chassis/mapping/validate_catalog.py`
   + jeho testy (integrační třída v testovacím souboru).
5. Spuštěny všechny tři sady, čísla zaznamenána (viz §5).

## 2. Stav integrace: PROVEDENA (tenký modul) + NAVRŽENA (hook do mapování)

**Provedena:** nový modul `src/Chassis/mapping/validate_catalog.py`:
- `validate_catalog_for_mapping(path) -> MappingCatalogVerdict`
- `validate_records_for_mapping(records) -> MappingCatalogVerdict`
- `MappingCatalogVerdict(status, reason, witness_path, integrity_errors)`,
  `status ∈ {OK, BLOCKED}`, `allowed == (status == OK)`.
- Cyklus → `BLOCKED`, důvod `CYCLE: …` + konkrétní cesta svědka.
- Chyba integrity → `BLOCKED`, důvod `INTEGRITY: …` (JINÝ důvod než cyklus,
  svědek prázdný, `integrity_errors = [(source, missing)]`).
- Čistý katalog → `OK`.
- Modul pouze čte (deleguje na `check_catalog_file/records`), katalog nemění.

**Zjištění, kde se validuje mapování:** `src/Chassis/mapping_engine.py`
- `map_config()` a `build_search_space()` načítají katalog přes `_load_catalog()`
  a kontrolují `depends_on`/`conflicts` JEN per-parametr při mapování
  (nesplněná závislost → `rejected`); **globální kontrola cyklů se nikde nevolá**
  (grep `cycle_check|check_catalog|has_cycle` v `src|tests|tools`: jen
  `cycle_check.py` + tento test). API `map_config`/`build_search_space` je
  navíc ZMRAZENÉ a soubor vlastní Agent B — proto **needito­váno**.

**Navrženo (ke schválení koordinátorem / Agentem B):** na začátek `map_config()`
i `build_search_space()` přidat bránu:

```python
from src.Chassis.mapping.validate_catalog import validate_catalog_for_mapping

verdict = validate_catalog_for_mapping(catalog_path)
if not verdict.allowed:
    # map_config: vrátit {"tune_changes": [], "rejected": [...], "warnings": [verdict.reason]}
    # build_search_space: raise ValueError(verdict.reason)
```

Důvod návrhu místo editu: zmrazené API + cizí vlastnictví souboru; změna chování
při cyklickém katalogu (dnes se mapuje, po patchi BLOCKED) je rozhodnutí
koordinátora. Do té doby je brána k dispozici jako volání nového modulu.

## 3. Pokrytí testů (32 testů, všechny PASS)

- `TestMigratedCore` (6): acyklický, self-loop, 2-cyklus, 3-cyklus, determinismus
  (výsledek i svědek), known-tables bez cyklu (opravená `CycleResult` sémantika).
- `TestOverlapWitness` (1): `a->[b,c],b->[c],c->[a]` → `has_cycle=True` + svědek
  ověřen hranu po hraně.
- `TestExtraCases` (15): self-loop ve větším grafu; 2 samostatné cykly;
  cykly se společným uzlem; cykly se společnou hranou; delší cyklus (5+);
  velký acyklický graf (500 uzlů, statistika 500/500); duplicitní hrana
  (není cyklus, hrany se počítají unikátně); neexistující cíl = chyba integrity,
  NE cyklus (`check_integrity == [("a","ghost")]`, `has_cycle == False`,
  `CatalogCheckResult.valid == False`); prázdný graf; **5 neplatných struktur**
  (graf není dict; nestringový uzel; sousedi nejsou list; nestringový cíl hrany;
  duplicitní `id` v záznamech); stejný graf v různém pořadí hran
  (stejný výsledek i svědek).
- `TestRealCatalog` (4): načtení **138 parametrů / 101 hran**; `has_cycle=True`
  na reálných datech; svědek přesně
  `["tcs_threshold_sps", "tcs_gradient", "tcs_threshold_sps"]` = cyklus č. 1
  auditu Agenta A (ověřen hranu po hraně + členství v 19 známých párech);
  `integrity depends_on` čistá (`[]`).
- `TestValidationIntegration` (6): čistý katalog → `OK`; cyklický → `BLOCKED`
  s konkrétní cestou (`CYCLE` v důvodu, svědek platný); integrita → `BLOCKED`
  s JINÝM důvodem (`INTEGRITY`, bez `CYCLE`); **negativní sonda: katalog
  s cyklem NESMÍ projít PASS**; **negativní sonda: katalog s neexistujícím id
  NESMÍ projít PASS** (obě přes souborovou cestu `validate_catalog_for_mapping`);
  reálný katalog → `BLOCKED` s platným svědkem (očekáváno, katalog je cyklický).

## 4. Blocker pro mapovací cestu

Reálný katalog je dnes CYKLICKÝ (12 komponent / 19 párů dle Agenta A), takže
`validate_catalog_for_mapping(parameters.json)` vrací `BLOCKED` — po nasazení
navrženého hooku by `map_config`/`build_search_space` nad aktuálním katalogem
odmítly pracovat, dokud se cykly v datech nevyřeší (rozhodnutí koordinátora:
opravit katalog, nebo povolit mapování s varováním). Testy tento stav
explicitně pokrývají (`test_real_catalog_blocked_for_mapping`).

## 5. Čísla

- `python -m unittest tests.test_m5_cycle_check`: **32 testů, PASS 32 / FAIL 0**.
- `python tests/run_all.py`: **běhů 436, PASS 432, FAIL 0, ERROR 0, PENDING 4**
  (4 pending jsou předchozí: Studio-měření, schema-conformance Fáze 5,
  2× regresní baseline Fáze 9/10 — nesouvisí s S-02).
- `python tools/validate_contracts.py`: **24 kontrol, 0 chyb — ÚSPĚCH**.

## 6. Soubory

- Zapsán: `tests/test_m5_cycle_check.py` (32 testů, 5 tříd).
- Zapsán: `src/Chassis/mapping/validate_catalog.py` (jediný nový modul,
  ~100 řádků, stdlib only).
- Zapsán: tento report.
- Needito­váno: `src/Chassis/mapping/cycle_check.py`, `mapping_engine.py`,
  `dependencies.py`, katalog, RBXM.
