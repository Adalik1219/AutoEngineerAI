# REMEDIATION-BASELINE — uzavírací vlna S-02

**Datum:** 20. 11. 2026 · **Koordinátor:** Hermes Agent
**Větev:** `feat/m2-m3-geometry` · **HEAD:** `0f4670a3c98ed378d8424585d00305e85cfcdf11`
**Strom:** čistý · **`main`:** `5b673155e3b7b78ed2cf826814e57be433349681f` (beze změny)
**PR #2:** OPEN, base `main`, head `feat/m1-m2-foundation` (`ab840a92…`) — nesloučeno
**RobloxSimulator:** čistý (READ-ONLY)

## Referenční body (ověřeny)
- Integrační commit: `bc6f955976ece9901d2209a819d021e8841049b0`
- Remediation kód: `0f7c968f4e2da33f105244e13efac25515216fdd` (5 souborů: test_f4_integration, test_f4_mapping, 3 reporty E/F/FINAL; BEZ produkčního kódu/katalogu/RBXM)
- Doc tip: `0f4670a3c98ed378d8424585d00305e85cfcdf11`
- CI run `44737468908`: success, 4/4 joby (3.11–3.14), 443/438/0/0/5 (CI), kontrakty 24/24
- Baseline local (tato kontrola): 443/439/0/0/4, kontrakty 24/24, `git diff --check` čistý
- CI-vs-local rozdíl: `test_limit_single_distinct_model` (CI PENDING — 1 kopie RBXM; local PASS — 2 kopie). Prostředí se uvádí u každého čísla.

## RBXM (ověřeno)
- `testgame/src/ServerStorage/VehicleTemplates/JeepTemplate.rbxm`, 230 421 B
- git blob `417b9f43833c8c8b059212bb84e02b163dc09d08` = zadání §10 ✓
- sha256 `dc8747e0…fefdf` (shodný s evidencí minulých vln) ✓
- blob identický v `bc6f955`, `0f7c968`, `0f4670a` (průkaz napříč vlnou) — historický stav před `bc6f955` se nedokládá (uvedeno poctivě)
- Soubor během této kontroly nezměněn; zákaz změny platí.

## Kontrolované reporty (stav k HEAD)
- Agent C `AGENT-C-S02-INTEGRATION-TESTS.md` — 39 testů, Test G, nulová změna; C1–C3 z této vlny v něm CHYBÍ (řeší Agent C)
- Agent E `AGENT-E-MUSTANG-DATA-AUDIT.md` — tabulka 65 řádků; rozpor 60/78 + 7/3/22/28 nedoložen (řeší Agent E)
- Agent F `AGENT-F-MUSTANG-PHYSICS-MAPPING.md` — 103 parametrů (59/8/31/12+2+1); NENÍ implementace RBXM
- Agent G `AGENT-G-INDEPENDENT-QA.md` — CONDITIONAL PASS na `bc6f955`+dirty; NENÍ QA finálního SHA (řeší Agent G ve fázi 4)

## Otevřené problémy
O1 per-parametrické odmítnutí neprokázáno (C1) · O2 Sim-na-patchnuté slabý důkaz config-předání (C2, `test_sim_runs_on_patched_config_not_original`) · O3 FinalDrive fixture křehká ruční hrany (C3) · O4 hranice `apply_config` nerozhodnuta (B4) · O5 normalizace 60/78 nedoložena (E) · O6 3 vakuové testy (G) · O7 StAxisOffset + magnitude bugy (mimo rozsah, §12) · O8 katalog cyklický (záměrně BLOCKED, mimo rozsah vlny).

## Zakázané změny (bez samostatného schválení)
Katalog · RBXM · `main` · PR #2 · veřejná schémata (PROPOSED zůstává) · pravidla S-02 (fail-closed, CYCLE/INTEGRITY/INVALID) · stav M3 (CLOSED) · produkční fyzikální model · obcházení gate · mazání hran pro zelený test · přepis historie reportů · Python simulace jako runtime důkaz.

## Pracovní prostory fáze 2 (oddělené worktrees z `0f4670a`)
- `C:/.DATA/AE-WORK-B` (větev `wave-b-s02`) — Agent B
- `C:/.DATA/AE-WORK-C` (větev `wave-c-tests`) — Agent C
- `C:/.DATA/AE-WORK-E` (větev `wave-e-norm`) — Agent E
Integrace: merge větví koordinátorem (disjunktní soubory), 1 kódový commit → CI → G QA na přesném SHA → doc closeout (oddělený commit).
