# WAVE-BASELINE — implementační vlna S-02 integrace + A-Chassis/Mustang

**Datum:** 20. 11. 2026 · **Koordinátor:** Hermes Agent
**Větev:** `feat/m2-m3-geometry` · **HEAD:** `557ee39cdfe4cd558dd4a1194c81adff6a2968fa` (odpovídá zadání)
**Pracovní strom:** čistý (`git status --short` prázdný)
**`main`:** `5b673155e3b7b78ed2cf826814e57be433349681f` — beze změny (zákaz platí)
**PR #2:** `state=OPEN, closed=false`, base `main`, head `feat/m1-m2-foundation` (`ab840a92…`) — nemergováno
**Původní RBXM:** `assets/chassis-original/chasis-work-copy.rbxm`, sha256 `dc8747e0…fefdf`
**RobloxSimulator:** `git status --short` prázdný (READ-ONLY dodrženo)
**Test runner v repu:** `unittest` + `tests/run_all.py` (příkazy `pytest` ze zadání §12 se mapují na tyto)

## CI run 44713829758 (ověřen z logu, ne z reportu)
- Závěr: **success** (4 joby: tests 3.14 / 3.13 / 3.11 / 3.12, vše ✓)
- Plná sada v CI: **436 běhů / 431 PASS / 0 FAIL / 0 ERROR / 5 PENDING**
- PENDING v CI (5): `test_studio_mereni_pending_ne_pass`, **`test_limit_single_distinct_model` (druhá kopie chybí)**, `test_schema_conformance_pending`, `test_baseline_exists`, `test_variant_store_append_only`

## Oprava čísel z minulé vlny (důležité)
Minulý finální report uváděl lokální běh **432 PASS / 4 PENDING**; CI log ukazuje **431 PASS / 5 PENDING**. Rozdíl = `test_limit_single_distinct_model`: lokálně existují obě RBXM kopie (PASS), v CI jen jedna (PENDING). Obě čísla jsou pravdivá ve svém prostředí — od této vlny se u každého čísla uvádí PROSTŘEDÍ (local vs CI + SHA).

## Známé blokátory vstupu
Katalog cyklický (12 SCC, `has_cycle=True`) → mapování BLOCKED · M2 bez VERIFIED (Mustang RBXM + Studio měření chybí) · M3 CLOSED · 4 M2 schémata PROPOSED (čekají na schválení) · T-M5-01 min/max trvá.

## Rozdělení práce (disjunktní vlastnictví)
| Agent | Úkol | Smí zapisovat POUZE |
|---|---|---|
| A | katalog: SCC klasifikace + návrh nápravy | `reports/NIGHT-WORK/AGENT-A-CATALOG-REMEDIATION.md` |
| D | A-Chassis inventář + Mustang body interface + plán sestavení | `reports/NIGHT-WORK/AGENT-D-MUSTANG-ARCHITECTURE.md` |
| E | Mustang data audit + konzistence PROPOSED schémat | `reports/NIGHT-WORK/AGENT-E-MUSTANG-DATA-AUDIT.md` (schémata NEMĚNIT, status NEMĚNIT) |
| F | A-Chassis capability mapa + mapovací tabulka | `reports/NIGHT-WORK/AGENT-F-ACHASSIS-PHYSICS-MAPPING.md` (fyziku NEMĚNIT) |
| B | S-02 brána do skutečného mapovacího entry pointu | produkční mapovací soubory + `reports/NIGHT-WORK/AGENT-B-S02-INTEGRATION.md` (API detektoru NEMĚNIT) |
| C | integrační + negativní testy skutečného mapování | `tests/test_m5_cycle_check.py` (rozšíření) + `reports/NIGHT-WORK/AGENT-C-S02-INTEGRATION-TESTS.md` |
| G | nezávislá adversariální QA | `reports/NIGHT-WORK/AGENT-G-INDEPENDENT-QA.md` |

**Pořadí:** Vlna 1 (A+D+E+F, read-only) → Vlna 2 (B integrace) → Vlna 3 (C testy) → Vlna 4 (G QA na finálním SHA) → Vlna 5 (commit + CI).
B nesmí měnit API detektoru. C nesmí měnit produkci. G nesmí nic měnit.
M3 zůstává CLOSED. Žádná Mustang konfigurace z neověřených hodnot. Žádný placeholder jako VERIFIED.
