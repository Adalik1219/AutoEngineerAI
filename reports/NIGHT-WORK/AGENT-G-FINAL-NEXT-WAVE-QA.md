# AGENT-G-FINAL-NEXT-WAVE-QA — finální nezávislá QA next-wave

- SHA: `405db4b53998c332dc193c8bae753ad841efbc67` (detached, read-only; nic neměněno, nic commitnuto)
- Datum: 2026-11-20
- Prostředí: Windows 11, Python 3.14.9, runner `unittest`, worktree `C:/.DATA/AE-NW-G`
- Hlavní klon `C:/.DATA/AutoEngineerAI`, katalog/RBXM/`src/main`/PR#2: tabu, nedotčeno

## 1. Povinné běhy (vše na 405db4b)

| Příkaz | Výsledek | Exit |
|---|---|---|
| `python -m unittest tests.test_normalization_validation -v` | 14/14 OK (negativní E1–E6 + meta) | 0 |
| `python -m unittest tests.test_f4_mapping tests.test_f4_integration -v` | 36 testů OK, 1 skip | 0 |
| `python tests/run_all.py` | běhů=458 PASS=454 FAIL=0 ERROR=0 PENDING=5 local (5 zdokumentovaných: studio-měření, 2nd model copy, schema-conformance F5, 2× VariantStore F9/10); CI 458/453/5 | 0 |
| `python tools/validate_contracts.py` | 24 kontrol, 0 chyb (vč. example-vehicle + 3 vehicle-data) | 0 |
| `python tools/validate_normalization.py` | VERDIKT_DAT=PENDING, exit 2; agregace 78 řádků (V6/E7/P20/U45), 94 ID (U54/P25/E8/V7), skupiny 9/členové 28/aliasy 46/unresolved 4, NEPOKRYTE_RADKY=0 DUPLICITY=0 | 2 |

Sémantika exitu validátoru: 0=OK / 1=FAIL / 2=PENDING (data). Exit 2 zde = **očekávaný stav**, důvod jediný:
`ORIGINAL_LOGICAL_IDS=PENDING — ORIGINAL_60_SET=NOT_RECONSTRUCTABLE — seznam 60 ID neexistuje
v žádném commitu/souboru (Varianta B); 94 normalizovaných ID se za 60 nevydává`.
Zdroj: `reports/NIGHT-WORK/AGENT-F-MUSTANG-PHYSICS-MAPPING.md`, blob `4d4d7650ba4a`
(`git hash-object` = `4d4d7650ba4ad095815d3b5caaca711b62138c31`, shoda).

## 2. Výroky po oblastech (12 bodů)

| # | Oblast | Výrok | Důkaz |
|---|---|---|---|
| 1 | S-02 cesty | PASS | `src/Chassis/mapping/gate.py:108,122`, verdikt `validate_catalog.py:46`, detektor `cycle_check.py:226,278`, hook `mapping_engine.py:164-185,276-284,399-405`. Obě cesty (`map_config`→`tune_changes=[]`+`rejected=[*catalog*]`, `build_search_space`→`[]`), vstup neměněn. `test_m5_cycle_check` OK; vlastní sonda: cyklus a↔b → BLOCKED se svědkem, acyklický → OK |
| 2 | Adapter Varianta A | PASS | Platí **A**: `achassis_v1.py:465-535 apply_config(model_copy_dir, config)` bez `catalog_path`; grep `gate`/`parameters.json` v adaptéru negativní (sondou False/False); rozhodnutí `AGENT-B-S02-SECURITY-AUDIT.md:31-34`. Řetěz kryt shora, při BLOCKED `applied==[]`; sonda `WarpDrive` → rejected |
| 3 | Per-parametrické odmítnutí | PASS | `mapping_engine.py:311-367` (5 větví: unknown / non-MUTABLE / rozsah / depends / conflicts). `test_f4_mapping.py:323-369` OK (28 testů, 1 skip); vlastní acyklická sonda: 5 důvodů doloženo, validní projdou |
| 4 | Sim swap (C2) | PASS | `test_f4_integration.py:421` OK (8 testů); RAW `patched==captured: True; captured!=original: True; bias 0.70 vs 0.62`. Vlastní sonda: sim běží nad patchnutým souborem |
| 5 | FinalDrive fixture+negativa | PASS | Fixture `test_f4_integration.py:251` (fd 2.5–4.2, auto-validace bránou); směr účinku: 2.6→9.528 s, 3.2→9.160 s (Δ=0.368 s > 0.05). Negativa `test_module_contracts.py:111` + `gearbox.py:44-57,82,75`; 58 testů OK, 1 skip; sonda: 5/5 → ValueError |
| 6 | Sémantika normalizace | PASS (nástroj) / PENDING (data) | Nástroj: 14/14 OK exit 0; validátor exit 2 s důvodem (viz §1). Sémantika 0/1/2 dodržena |
| 7 | Rekonstrukce 60 ID (Var. B) | PASS (claim potvrzen) | `44cc773` přidává jen F-rekonstrukční report; `1d061ac` merge `681e98f`+`44cc773`; `normalized_ids.json`: `original_60_set={NOT_RECONSTRUCTABLE, seznam: null}`; `log -S/-G`: zásahy jen report/validátor/audity, žádný seznam 60 nikdy neexistoval. První „60" = `557ee39` holá deklarace (blob `b5f95b19…`) |
| 8 | 3 vakua V1–V3 | PASS (opraveny) | V1 `test_f4_integration.py:421`, V2 `test_f4_mapping.py:572`, V3 `test_f4_integration.py:251` (dle `AGENT-C-VACUOUS-TEST-REVIEW.md` @`1ad3bfb`). Minisonda: stará aserce `len==1` prošla naprázdno, nové 3× AssertionError (fail-as-expected). Reálné běhy V1/V2/V3 OK s RAW svědky |
| 9 | Rollback postup | PASS | Worktree `C:/.DATA/AE-ROLLBACK-TEST` HEAD `1139957`, čistý; `git diff 1139957 0f4670a --stat` prázdný exit 0 (v obou klonech). Mainline `074b9d2→301ef38→c3dc380→8fd23cb→57043ee` (`8fd23cb` parenti `c3dc380`+`31f1180`) ⇒ revert merge-commitů s `-m 1` správně; CLOSEOUT §Rollback dokládá |
| 10 | Konzistence doložek | PASS s 1 evidenční poznámkou | Časová řada run_all sedí ke svým SHA (436/432/0/0/4 @`90a1f63` → 443/439 @`0f4670a` → 444/440 @`8fd23cb` → 458/454/0/0/4 @`405db4b`, +14 testů). 78/94/9/28/46/4 konzistentní všude + vlastním přepočtem. Poznámka N-1 (nízká) |
| 11 | P01–P14 / U1–U6 | PASS (Neschváleno) | `CATALOG-PROPOSALS-AND-USER-INPUTS.md`: P01–P14 Neschváleno, U1–U6 bez definice; `grep src/`: P01–P14 0 výskytů; katalog blob beze změny. (U1–U4 v `normalized_ids.json` = technické unresolved ≠ uživatelské U1–U6) |
| 12 | Nezměněnost chráněných oblastí | PASS | RBXM `hash-object`==HEAD==`417b9f43…` (`JeepTemplate.rbxm`), diff vs `57043ee` prázdný. Katalog `hash-object`==HEAD==`8f4d6bd1…`, diff prázdný. `git diff 57043ee HEAD -- src/ testgame/` prázdný exit 0. main/PR#2 nedotčeny |

M3 CLOSED respektováno; test runner výhradně `unittest`.

## 3. Adversariální scénáře 1–8: 8/8 PASS

1. Sim-originál → C2 selže (sabotáž bias 0.62 → AssertionError) · 2. Gate-bez-grafu (`[]`, `allowed=False`, CYCLE důvod)
· 3. Cyklus → BLOCKED + uzavřený witness `[tcs_threshold_sps, tcs_gradient, tcs_threshold_sps]`, hrany v `parameters.json`
· 4. Neplatná reference → INTEGRITY · 5. Odmítnut-jiný-povolen → C1 · 6. Skrytá hrana dict-form → BLOCKED (fail-closed `INVALID`)
· 7. Vstup-beze-změny (snapshot-identický) · 8. Adaptér-mimo-hranici (`WarpDrive` rejected, model soubory nedotčeny).

## 4. Výběr datových případů

Přímý (1:1) · skupina (9→28) · alias (46, nesmí figurovat jako ID) · unresolved 4 (bez umělých ID, PENDING-větev)
· F-R pár se statusem · konflikt 12× (P14, kryt S-02, ne normalizací) · okrajové: reference, source_rows, metadata, JSON, cyklus.
Plná auto-kontrola: `run_all` 458 + validátor E1–E4 + `validate_contracts` 24.

## 5. Nálezy

- N-1 evidenční / nízká: `AGENT-G-INDEPENDENT-REVIEW.md:66 (N2)` — E-report cituje `372/368/4` místo tehdejších `410/406/4`; reportem již přiznáno jako zastaralá citace. Bez dopadu.
- N-2 nízká: `tools/validate_normalization.py:70` nezavírá soubor (`ResourceWarning: unclosed file`); bez dopadu na výsledky; doporučeno `with open(...)` v další vlně (záměrně NEopraveno zde, aby zůstal kódový SHA beze změny pro tuto QA).

## 6. VERDIKT: CONDITIONAL

Vše spustitelné je PASS (12/12 oblastí, 8/8 scénářů, 0 FAIL/ERROR). Podmínka jediná a datová:
`validate_normalization` zůstává PENDING (exit 2), protože deklarace „60" z `557ee39` nemá
seznam v žádném commitu (Varianta B, NOT_RECONSTRUCTABLE) — nelze opravit kódem, pouze
rozhodnutím uživatele: (a) akceptovat NOT_RECONSTRUCTABLE a 94 ID jako výchozí stav, nebo
(b) dodat původní seznam 60. Do té doby gate normalizace = PENDING, nikoli PASS.

*(Uloženo koordinátorem z předaného obsahu G; G do checkoutu nic nezapsal — ověřeno `git status`.)*
