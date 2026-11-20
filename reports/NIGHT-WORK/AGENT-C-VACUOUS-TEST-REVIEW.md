# Agent C — Vacuous-test review (identifikace + negativní ověření)

- Větev: `nw-c-tests`, workdir `C:/.DATA/AE-NW-C`, base HEAD `57043ee`.
- Prostředí: Windows 11, CPython 3.14.9, runner `unittest` (stdlib), Sim seed 7.
- Rozsah zápisu dodržen: měněn POUZE tento report. Produkční kód, katalog, RBXM, testy, `main`/PR#2, M3 — nedotčeny.
- Metoda: každý údajně vakuový test (a) pojmenován s přesným původem tvrzení, (b) spuštěn bez sabotáže (musí PASS), (c) spuštěn se sabotovaným vstupem v izolovaném `mock.patch` wrapperu mimo repo (musí FAIL). Wrapper nemění produkci ani `tests/` — pouze paměťová injekce jedné chyby do skutečné testovací metody.

## 1. Úplný seznam (historie označení)

| # | Test | Soubor | Kdo označil jako slabý/vakuový |
|---|---|---|---|
| V1 | `test_sim_runs_on_patched_config_not_original` (TestF4Integration) | `tests/test_f4_integration.py:421` | S02-INTEGRATION-TESTS §7.2 („prázdný tune → rovnosti triviální"); G-INDEPENDENT-QA §3c (2 potvrzená vakuua: „Sim se vůbec nespouští, jen file round-trip"); closeout rizika §12/§14 („3 vakuové testy") |
| V2 | `test_f4_11_neoverene_hodnoty_se_neaplikuji` (TestF4Safety) | `tests/test_f4_mapping.py:572` | S02-INTEGRATION-TESTS §7.2 („`len(rejected)==1` platí shodou pro `*catalog*`"); G-INDEPENDENT-QA §3c (druhé potvrzené vakuum); closeout rizika §12/§14 |
| V3 | `test_final_drive_change_moves_metric_or_unsupported` (TestF4Integration) | `tests/test_f4_integration.py:251` | G-INDEPENDENT-QA §3c („třetí částečné vakuum: mapovací noha za BLOCKED mrtvá, proteče passthrough, ne mappingem; Sim-noha pravá"); closeout rizika §12/§14 |
| R | `test_f4_07_per_param_rejection_acyclic_fixture` (TestF4Mapping, C1) | `tests/test_f4_mapping.py:369` | Nikdy označen jako vakuový — nový test (C1). Zařazen jen jako nosič negativních kontrol „ztracený validní parametr" a „odmítnutý unikl do tune". |

Jiný test nebyl v historii nikdy označen jako slabý/vakuový (ověřeno fulltextem `vaku*|slab*|triviál*` přes `reports/`, `tests/`, `docs/`). F4.3 test `test_map_config_odmitne_neexistujici_klic_s_duvodem` byl přepsán na BLOCKED v rámci 19 padajících, ale vakuum mu nikdy nikdo nevytkl — není součástí seznamu.

## 2. Stav + negativní kontroly

| Test | Soubor | Původní problém (chybějící aserce) | Stav | Negativní kontrola (sabotáž → čím selže) | Výsledek |
|---|---|---|---|---|---|
| V1 `test_sim_runs_on_patched_config_not_original` | `tests/test_f4_integration.py:421` | Prázdný tune → `captured==sim_cfg`/`!=original` triviální; Sim se nespouštěl | **OPRAVEN** (C2, `e0c7a75`): originál bias 0.62 ≠ cíl 0.70; reálný `run_scenario` + metriky; `captured==sim_cfg` + `captured!=original` + bias≠; rozsah downstream-izolace přiznán v docstringu | **S1 Sim-originál→selhání**: projekce `sim_input_from_patched` vrácena na originál (bias 0.62, bez tune) → `AssertionError` na `bias_front==0.70` (krok 5) | Selhává → **opraven (důkaz)** |
| V2 `test_f4_11_neoverene_hodnoty_se_neaplikuji` | `tests/test_f4_mapping.py:572` | `len(rejected)==1` platilo shodou pro `*catalog*` BLOCKED, ne pro per-klíč odmítnutí | **OPRAVEN** (`0f7c968`, WAVE-REPORT §51): izolovaný acyklický fixture z reálného záznamu `compression_ratio` (`depends_on=[]`); `param=="engine.compression_ratio"` + `"kategorie UNKNOWN"` + `"pending-studio"` v důvodu | **S3a stará shoda→selhání**: `map_config` vrácen jako BLOCKED `*catalog*`/CYCLE (přesně starý vakuový výstup) → `AssertionError` na `param` (není `engine.compression_ratio`). **S3b odmítnutý-v-tune→selhání**: únik do `tune_changes` → `AssertionError` na `tune_changes==[]` | Selhává → **opraven (důkaz)** |
| V3 `test_final_drive_change_moves_metric_or_unsupported` | `tests/test_f4_integration.py:251` | Částečné vakuum: mapovací noha mrtvá (passthrough za BLOCKED), jen Sim-noha měřila | **OPRAVEN** (C3, `e0c7a75`): deterministický 2-záznamový fixture (FinalDrive 2.5–4.2 + BrakeBias), auto-validace integritou + `gate==allowed` (jinak FAIL s důvodem); přesně 1 `tune_change` FinalDrive se správnou hodnotou; RAW `2.6→9.528 s / 3.2→9.160 s`, Δ=0.368 s > 0.05 | **S4a FinalDrive-ignorováno→selhání**: oběma běhům vnuceny shodné metriky → `AssertionError` na `\|Δt\|>0.05 s`. **S4b mapování-BLOCKED→selhání**: `map_config` vrácen jako `*catalog*` → `AssertionError` na `rejected==[]` + `len(tune)==1` | Selhává → **opraven (důkaz)** |
| R C1 `test_f4_07_per_param_rejection_acyclic_fixture` | `tests/test_f4_mapping.py:369` | N/A — nikdy vakuový (nový test C1) | Nový, plnohodnotný PASS (G-FINAL-QA §3/C5) | **S2a validní-parametr-ztracen→selhání**: `Horsepower` vyhozen z `tune_changes` → `AssertionError` na množině `{Horsepower, FinalDrive, Bias}`. **S2b odmítnutý-v-tune→selhání**: `warp_drive` propašován do `tune_changes`, `rejected=[]` → `AssertionError` na `len(rejected)==1` | Selhávají → kontrolní svědek funkční |

## 3. Rozhodnutí

- **Opravené (důkaz výše): V1, V2, V3** — všechny tři historicky označené testy dnes měří reálně: Sim běží (V1 RAW bias 0.7/0.62; V3 RAW Δ 0.368 s), důvody se kontrolují doslovně (`pending-studio`, `CYCLE`+svědek), každá sabotáž shodí konkrétní aserci.
- **Stále slabé: ŽÁDNÉ** (0).
- Závěr pro closeout: formulace „3 vakuové testy" bez jmen je od tohoto reportu zakázaná — seznam je uzavřený (V1–V3, vše opraveno) a každý řádek má dohledatelný důkaz selhání při chybě.

## 4. Běhy (vlastní, nepřevzatá čísla)

- Negativní wrapper (`mock.patch` v paměti, produkce/testy neměněny): **4/4 baseline PASS** (V1, V2, V3, R) + **7/7 sabotáží FAIL-as-expected** (S1, S2a, S2b, S3a, S3b, S4a, S4b, vesměs `AssertionError` na konkrétní aserci).
- `python -m unittest tests.test_f4_mapping tests.test_f4_integration`: **36 testů, OK (skipped=1)** — skip je pre-existing `test_studio_mereni_pending_ne_pass` (PENDING: vyžaduje Roblox Studio).
- `python -m unittest tests.test_module_contracts`: **45 testů, OK (skipped=1)** (pre-existing PENDING).
- `python tests/run_all.py`: **běhů=444 PASS=439 FAIL=0 ERROR=0 PENDING=5** — všech 5 PENDING pre-existing a zdokumentovaných (Studio-měření; 2. RBXM kopie chybí v tomto klonu; schema-conformance F5; 2× regresní baseline F9/10). Žádný nový FAIL/ERROR/PENDING.

## 5. SHA

Report zapsán jako jediná změna pracovního stromu; commit následuje. Kódový důkaz v CI zůstává `44758473223` (SHA `8fd23cb`, 444/439/0/0/5).
