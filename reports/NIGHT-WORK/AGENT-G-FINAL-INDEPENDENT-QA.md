# Agent G — finální nezávislá QA k SHA 8fd23cb

- SHA: `8fd23cb4f8b04a018ea6f57748554d4de5000ecc` (merge wave-e-norm)
- Rodiče: `c3dc380` (wave-c-tests) + `31f1180` (wave-e-norm)
- Větev: `feat/m2-m3-geometry`, klon `C:/.DATA/AutoEngineerAI`, strom čistý (`status` prázdný)
- Datum běhů: 2026-11-20, prostředí: Windows, Python 3.14.9, unittest (stdlib)
- CI k SHA: run `44758473223` (`headSha == 8fd23cb`), `success`, 2026-11-20T14:57:39Z
- M3: CLOSED (neměněno). RBXM/katalog/main/PR#2: tabu, nedotčeno.

## 1. Identita a diff bc6f955 → 8fd23cb

`git diff --name-only bc6f955..8fd23cb` = 11 souborů, **výhradně**:
`reports/NIGHT-WORK/*` (6× report/audit/baseline + `normalized_ids.json`),
`tests/test_f4_integration.py`, `tests/test_f4_mapping.py`, `tools/validate_normalization.py`.
`src/`, katalog, RBXM, `main`: **0 změn**. Žádná změna mimo rozsah vln B/C/E → **žádný nález**.
Mezilehlé commity: baseline `0f4670a` → B (audit, beze změn kódu) → C (testy C1–C3) → E (normalizace) → merge `8fd23cb`.

## 2. S-02 (nezávisle, vlastní sondy)

- Katalog: **138 záznamů / 101 hran `depends_on`** (53 bez hran, 85 čistě string; 0 visících hran v plném katalogu).
- Reálný verdikt: `BLOCKED / CYCLE: tcs_threshold_sps -> tcs_gradient -> tcs_threshold_sps`, `witness_path` uzavřená, `integrity_errors: []`. Svědek platí hrana po hraně (ověřeno proti `parameters.json`).
- Sondy: minimální cyklus → `BLOCKED/CYCLE` + svědek; dict-forma `{'param': 'y'}` cyklus → `BLOCKED/CYCLE` (skrytá hrana kryta normalizací v `gate.py`); visící id → `BLOCKED/INTEGRITY` s hranou; chybějící soubor i ne-seznam → `BLOCKED/INVALID` (výjimka nepropaguje). Pořadí brány: načtení → struktura → integrita → cyklus.
- Oba entry pointy: `map_config` → atomický `*catalog*` + CYCLE + vstup snapshot-identický; `build_search_space` → `[]` na BLOCKED katalogu.
- Obchvat: **žádný**. `apply_config` bránu nevolá záměrně (Varianta A — katalog vůbec nečte; neznámý klíč `WarpDrive` → `rejected` s důvodem, ověřeno během; binárka nedotčena). `backend_caps` = jen kandidáti (6 klíčů), vždy filtrováno gatovaným `build_search_space`. `optimizer.py` katalog nečte vůbec (statické `PARAM_DEFS`); `_dynamic_specs` je budoucí wiring F4.3. Poznámka (info, ne nález): `build_search_space` vrací `[]` bez důvodu — důvod si volající bere z `gate_catalog_file`, je to dokumentováno v docstringu.

## 3. Testy C (vlastní běhy)

- **C1** (`test_f4_07_per_param_rejection_acyclic_fixture`): PASS. Fixture prošla bránou OK; přesně 1 `rejected` (`engine.warp_drive`, důvod `kategorie UNKNOWN … pending-studio`, bez `CYCLE`, param ≠ `*catalog*`); `tune_changes == {Horsepower, FinalDrive, Bias}`; vstup nezměněn; determinismus opakováním (identické JSON).
- **C2** (`test_sim_runs_on_patched_config_not_original`): PASS. Reálný `run_scenario` + metriky; `captured == sim_cfg`, bias 0.70 vs originál 0.62. **Negativní kontrola experimentálně ověřena**: prohození (Sim dostane originál) shodí 3 aserce (`captured==sim_cfg`, `captured!=original`, `bias!=`) → test by selhal, kontrola funguje. Rozsah přiznán v docstringu (downstream-izolace, ne důkaz mapování — kryjí C1/C4).
- **C3** (`test_final_drive_change_moves_metric_or_unsupported`): PASS. Fixture (2 záznamy) auto-validovaná bránou + integritou (žádný ruční seznam hran); RAW: `fd 2.6 → t_0_100 9.528 s; fd 3.2 → 9.160 s` (Δ = 0.368 s > 0.05); přesné `tune_changes` (1× FinalDrive se správnou hodnotou), nerovnost metrik, determinismus mapování.
- **C4** (katalog-BLOCKED zachován): PASS (`test_retezec_map_config_az_adapter` + `test_f4_08_realny_katalog_prostor_sedm_klicu`). Reálný katalog → `*catalog*` + CYCLE + vstup nezměněn; adaptér: 138 parametrů, živý klíč projde, unknown odmítnut s důvodem; prostor `[]`, ne 7 klíčů.
- **C5**: každý C-test nese konkrétní aserce na hodnoty/důvody (žádný holý `PASS`, žádný skip jako jediná pojistka); 3 dříve vakuové testy nyní měří reálně (Sim běží, důvody kontrolovány doslovně).

## 4. E — normalizace (vlastní běh `tools/validate_normalization.py`)

11/12 OK + `PENDING`: deklarováno 60 ID, odvozeno **94** (předoručení, ne poddodávka). Agregace: řádky 78 (V6/E7/P20/U45), ID 94 (V7/E8/P25/U54); nevyřešené 4; nepokryté řádky 0; vadné odkazy 0; duplicity 0. **Verdikt PENDING potvrzuji** — důvodem je nesoulad deklarace (60) s odvozením (94), ne chybějící důkaz. Doporučení (nízká priorita): deklaraci srovnat na 94 nebo vymezit rozsah.

## 5. Adversariální scénáře 1–8

1. Sim-originál → C2 by selhal na 3 asercích (experiment §3). 2. Gate-bez-grafu → `build_search_space == []`, důvod jen přes `gate_catalog_file` (dokumentováno; optimizer hlavní smyčkou katalog nečte). 3. Cyklus → BLOCKED + uzavřený svědek. 4. Neplatná reference → BLOCKED/INTEGRITY s hranou. 5. Parametr-odmítnut-jiný-povolen → C1 (1 vs 3, důvod doslovně). 6. Skrytá hrana (dict-form) → cyklus i dangling zachyceny. 7. Test-beze-změny → snapshot-rovnost ověřena u `map_config` i C1/C2/C3. 8. Adaptér-mimo-hranici → unknown klíč odmítnut s důvodem, `touched_model_files == []`. Všech 8: **bez obchvatu**.

## 6. Vlastní běhy vs CI

| sada | lokálně (py 3.14.9) | CI 44758473223 (py 3.11–3.14) |
|---|---|---|
| `run_all` | 444 / **440** / 0 / 0 / **4** | 444 / **439** / 0 / 0 / **5** |
| S-02 (`test_m5_cycle_check`) | 39/39 OK | OK (součást run_all) |
| kontrakty (`validate_contracts`) | 24/24, 0 chyb | — (CI běží unittest sadu) |
| normalizace | 11/12 + PENDING(60→94) | — |

Delta 440/4 vs 439/5 = `test_limit_single_distinct_model` (druhá RBXM kopie je v tomto klonu přítomna → PASS; v CI chybí → SKIP). Prostředí, ne regrese. RBXM sha v CI sedí (`dc8747e0…`, PASS).

## 7. Pět PENDING jednotlivě

1. `test_studio_mereni_pending_ne_pass` — chybí Roblox Studio (Stiffness/Damping odečet). Dopad: F4-Safety měření neprokázáno. Podmínka: běh ve Studiu. Neuzavřeno, **neblokuje** (mimo runtime důkaz, evidováno).
2. `test_limit_single_distinct_model` — chybí 2. RBXM kopie v daném prostředí. Dopad: hash-před/po jen na 1 kopii. Podmínka: přítomnost obou kopií. Neuzavřeno, **neblokuje** (read-only zásada dodržena).
3. `test_schema_conformance_pending` — Fáze 5 (shoda example-vehicle se schématem). Neuzavřeno, **neblokuje** tuto vlnu.
4. `test_baseline_exists` — baseline Fáze 9/10 neexistuje. Neuzavřeno, **neblokuje** (regrese jinak zelená).
5. `test_variant_store_append_only` — VariantStore bez napojení na reálná data. Neuzavřeno, **neblokuje**.
(+ datový PENDING normalizace §4 — důvod k nápravě deklarace, ne k blokaci.)

## Nálezy

**Kritické: žádné.** 0 FAIL / 0 ERROR lokálně i v CI (4× Python verze).
Nekritické (info): (a) `build_search_space` mlčí důvod BLOCKED — dokumentováno, acceptor pattern; (b) C2 rozsah omezen na downstream — přiznáno v docstringu; (c) normalizační deklarace 60 vs odvozených 94 — srovnat.

## VERDIKT: PASS (s PENDING)

S-02 PASS · C1–C5 PASS · E PENDING (potvrzen, důvod popsán) · adversarial 1–8 bez obchvatu · běhy 444/440/0/0/4 + CI 444/439/0/0/5 (delta vysvětlena prostředím) · 0 kritických nálezů. M3 zůstává CLOSED; odblokování čehokoli dalšího podmiňuji acyklickým katalogem (náprava Agent A), ne touto vlnou.
