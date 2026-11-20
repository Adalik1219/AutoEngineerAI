# Agent G — Nezávislá kontrola vakuových testů (NE finální QA)

- Větev: `nw-g-qa`, workdir `C:/.DATA/AE-NW-G`, base HEAD `57043ee`.
- Prostředí: Windows 11, CPython 3.14.9, runner `unittest` (stdlib), Sim seed 7.
- Vstup: C-report `1ad3bfb:reports/NIGHT-WORK/AGENT-C-VACUOUS-TEST-REVIEW.md`
  (čten read-only přes `git show`, neměněn) + testy `tests/test_f4_mapping.py`,
  `tests/test_f4_integration.py` v tomto worktree.
- Metoda: vlastní, z C-reportu nepřevzatá. Každý test V1/V2/V3/R jsem (a) přečetl
  celý včetně fixture a všech asercí, (b) spustil bez sabotáže (musí PASS),
  (c) spustil s vlastní sabotážní sondou v `mock.patch` wrapperu mimo repo
  (paměťová injekce, produkce ani `tests/` neměněny — musí FAIL na konkrétní aserci).
  Závěr C jsem si ověřoval, ne přebíral.

## 1. Výsledky po testech

| test | vstup (fixture) | klíčové aserce | vlastní sabotáž | výsledek | shoda s C |
|---|---|---|---|---|---|
| V1 `test_sim_runs_on_patched_config_not_original` (`test_f4_integration.py:421`) | originál `demo_config(bias_front=0.62)` záměrně odlišný od cíle 0.70; explicitní tune `BrakeBias=0.70` přes adaptér (mapování je za S-02 BLOCKED — rozsah přiznán v docstringu, kroky 1–12) | `captured==sim_cfg` + bias 0.70; `captured!=original` + bias≠0.62; `sim_cfg!=original`; mutace-neměnnost; `t_0_100_s` existuje (sekundární) | **S1**: projekce `sim_input_from_patched` vrácena na originál (bias 0.62, bez `tune`) → FAIL `AssertionError: 0.62 != 0.7` (krok bias-aserce) | sabotáž selhává → test měří předání Simu | ANO |
| V2 `test_f4_11_neoverene_hodnoty_se_neaplikuji` (`test_f4_mapping.py:572`) | reálný záznam `compression_ratio` z katalogu, `depends_on=[]` (acyklická izolace); PENDING=43 ověřeno doslovně | `tune_changes==[]`; `len(rejected)==1`; `param=="engine.compression_ratio"`; `"kategorie UNKNOWN"` + `"pending-studio"` v důvodu | **S3a**: `map_config` vrácen jako starý BLOCKED `*catalog*`/CYCLE → FAIL na `param` (`*catalog*` ≠ `engine.compression_ratio`); **S3b**: odmítnutý propašován do `tune_changes` → FAIL na `tune_changes==[]` | obě sabotáže selhávají → důvod i neaplikace měřeny | ANO |
| V3 `test_final_drive_change_moves_metric_or_unsupported` (`test_f4_integration.py:251`) | deterministický 2-záznamový fixture (FinalDrive 2.5–4.2 + BrakeBias), auto-validace integritou + `gate==allowed` (jinak FAIL s důvodem); mapování 2.6 i 3.2, determinismus opakováním | přesně 1 `tune_change` FinalDrive se správnou hodnotou; `rejected==[]`; `sim` final_drive 2.6/3.2 + `sim_lo!=sim_hi`; `\|Δt_0_100\|>0.05 s`; RAW `2.6→9.528 s / 3.2→9.160 s`, Δ=0.368 s | **S4a**: oběma běhům vnuceny shodné metriky (9.500 s) → FAIL `0.0 not greater than 0.05` s konkrétními čísly; **S4b**: `map_config` vrácen jako `*catalog*` BLOCKED → FAIL na `rejected==[]` / `len(tune)==1` | obě sabotáže selhávají → citlivost Simu i mapovací noha měřeny | ANO |
| R `test_f4_07_per_param_rejection_acyclic_fixture` (`test_f4_mapping.py:369`) | acyklický `_sample_catalog()` fixture, `gate==allowed` ověřen (nejsme za bránou); vstup horsepower+warp_drive+final_drive+bias | `gate.allowed`; množina `{Horsepower, FinalDrive, Bias}`; `len(rejected)==1`, `param=="engine.warp_drive"`, `"kategorie UNKNOWN"`+`"pending-studio"`, bez `"CYCLE"`, ≠`*catalog*`; únik `WarpDrive==[]`; vstup nezměněn; determinismus JSON | **S2a**: `Horsepower` vyhozen z `tune_changes` → FAIL `Items in the second set but not the first: 'Horsepower'`; **S2b**: `warp_drive` propašován do `tune_changes` + `rejected=[]` → FAIL už na množině (`'WarpDrive'` navíc), únik detekován před `len(rejected)` | obě sabotáže selhávají → kontrolní svědek funkční | ANO |

Poznámky z vlastního čtení (ne z C):
- V1 docstring výslovně přiznává zúžený rozsah (downstream-izolace adaptér→Sim,
  ne důkaz mapování přes bránu) — krytí mapování testy C1/C4 jsem spot-checkem
  ověřil (C4 `test_retezec_map_config_az_adapter` + `test_peak_torque_path_explicitly_rejected`
  skutečně asertují `*catalog*`/CYCLE BLOCKED). Rozsah je tedy poctivý, ne vakuum.
- V2 docstring je stručný, ale tělo testu obsahuje všechny 4 klíčové aserce
  (param + 2 důvodové podřetězce + prázdné tune) — tvrzení C o opravě sedí
  s kódem, který čtu.
- S2b selhává o krok dřív, než C uvádí u své S2b (na množině tune-klíčů kvůli
  `WarpDrive` navíc, ne až na `len(rejected)==1`) — detekce úniku je tím spíš
  prokázána; rozdíl je v pořadí asercí, ne ve výsledku.

## 2. Shoda s C-reportem 1ad3bfb

- Potvrzeno: V1, V2, V3 (vše opraveno — každá sabotáž shodí konkrétní aserci), R (svědek funkční).
- Vyvráceno: nic (0). Žádné tvrzení C o stavu testů ani o negativních kontrolách
  S1–S4b se proti kódu a běhům nepotvrdilo jako nepravdivé.
- Shoda seznamu: úplný — fulltext `vaku*|slab*|triviál*` jsem neopakoval,
  ale žádný další test jsem při čtení obou souborů jako vakuový neidentifikoval;
  C-seznam V1–V3+R odpovídá historickým odkazům (S02-INTEGRATION-TESTS §7.2,
  G-INDEPENDENT-QA §3c, closeout §12/§14).

## 3. Běhy (vlastní čísla, nepřevzatá)

- Sabotážní wrapper (vlastní skript mimo repo, `mock.patch` v paměti):
  **4/4 baseline PASS** (V1, V2, V3, R) + **7/7 sabotáží FAIL-as-expected**
  (S1, S2a, S2b, S3a, S3b, S4a, S4b — vesměs `AssertionError` na konkrétní aserci).
- `python -m unittest tests.test_f4_mapping tests.test_f4_integration`:
  **36 testů, OK (skipped=1)** — skip je pre-existing
  `test_studio_mereni_pending_ne_pass` (PENDING: vyžaduje Roblox Studio).
- `python -m unittest tests.test_module_contracts`: **45 testů, OK (skipped=1)**
  (pre-existing PENDING).
- `python tests/run_all.py`: **běhů=444 PASS=439 FAIL=0 ERROR=0 PENDING=5** —
  všech 5 PENDING pre-existing a zdokumentovaných (Studio-měření; 2. RBXM kopie;
  schema-conformance F5; 2× regresní baseline F9/10). Žádný nový FAIL/ERROR/PENDING.
  Shoda s čísly C-reportu §4: ANO (všechna čtyři čísla identická).

## 4. Rozhodnutí (nezávislé)

- Stále vakuové/slabé testy v rozsahu V1–V3: **ŽÁDNÉ** (0). Potvrzuji závěr C §3.
- Toto není finální QA — pouze nezávislá kontrola testové síly V1/V2/V3/R.
