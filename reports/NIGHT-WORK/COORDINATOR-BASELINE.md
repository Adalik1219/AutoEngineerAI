# KOORDINÁTOR — BASELINE TÉTO VLNY

**Větev:** `feat/m2-m3-geometry`
**Výchozí SHA (ověřen 2026-11-20, `git rev-parse HEAD`):** `90a1f63c184ef4dddbc134de47bc627adc8dce46`
**Odpovídá zadání:** ANO — shoduje se s výchozím commitem poslední ověřené vlny.
**Pracovní strom:** čistý (`git status --short` prázdný).
**Poslední commity:** `90a1f63` night-work(m2-m9) → `9803db3` docs → `6d421e8` docs.
**`main`:** `5b673155e3b7b78ed2cf826814e57be433349681f` — nezměněn, zákaz platí.
**PR #2:** OPEN (`feat/m1-m2-foundation` = `ab840a92…`), zákaz merge platí.
**RobloxSimulator:** `git status --short` prázdný (READ-ONLY dodrženo).
**Test runner v repu:** `unittest` + `tests/run_all.py` (nikoliv pytest — příkazy ze zadání §12 nutno mapovat na skutečné cesty).
**CI výchozího SHA:** run `44634547379` — success.

## Rozdělení úkolů (disjunktní vlastnictví souborů)

| Agent | Úkol | Smí zapisovat POUZE |
|---|---|---|
| A | audit skutečných závislostí katalogu | `reports/NIGHT-WORK/AGENT-A-S02-CATALOG-AUDIT.md` |
| B | oprava algoritmu detekce cyklů | `src/Chassis/mapping/cycle_check.py` (+ případně `reports/NIGHT-WORK/AGENT-B-…` poznámky v témže reportu C? NE — vlastní report nepíše, výsledek popíše C/G; B vrací shrnutí koordinátorovi) |
| C | testy S-02 + integrace validace | `tests/test_m5_cycle_check.py`, `reports/NIGHT-WORK/AGENT-C-S02-TESTS.md` (+ nový integrační modul, jen pokud nutný) |
| D | strategie A-Chassis/Mustang, vyřazení Jeepu | `reports/NIGHT-WORK/AGENT-D-CHASSIS-MUSTANG-STRATEGY.md` (+ přesně vyjmenované doc-úpravy) |
| E | návrhy M2 schémat PROPOSED | `reports/NIGHT-WORK/AGENT-E-M2-CONTRACTS.md` + `contracts/proposed/*.schema.json` (nové soubory; `validate_contracts.py` ani existující schémata NESMÍ měnit) |
| F | mapa A-Chassis → Mustang | `reports/NIGHT-WORK/AGENT-F-MUSTANG-PHYSICS-MAPPING.md` |
| G | nezávislé QA | `reports/NIGHT-WORK/AGENT-G-INDEPENDENT-QA.md` |

**Pořadí vln:** 1) A + D + E + F paralelně (read-only + vlastní reporty) → 2) B (oprava algoritmu, vstupem nález A) → 3) C (testy + integrace na B-rozhraní) → 4) G (QA všeho) → 5) finální report + commit + push.

**Pravidlo:** jeden agent nesmí implementovat a zároveň si udělit QA PASS. B/C/G jsou oddělené osoby. B nemění testy, C nemění `cycle_check.py` (API neshoda → hlásit koordinátorovi, ne tichá úprava).

## Rizika

1. B vs C API kontrakt — řešeno sekvenčně (B nejdřív, C na jeho rozhraní).
2. D doc-úpravy vs E/F reporty — D edituje POUZE existující `.md` dokumentaci k Jeep/Mustang formulacím, E/F píší POUZE nové reporty; kolize nehrozí.
3. E schémata v `contracts/proposed/` — validátor je neobjevuje automaticky (ověřeno: `validate_contracts.py` neglobuje `contracts/*.schema.json`), PROPOSED zůstává návrhem.
4. C integrace do validační cesty — pokud by vyžadovala edit existujícího validátoru, C připraví NOVÝ modul + testy a edit navrhne koordinátorovi ke schválení, neprovede ho sám.
5. M3 zůstává ZAVŘENÁ. Žádné Mustang hodnoty se nevymýšlejí — UNKNOWN zůstává UNKNOWN.

## Potvrzení bezpečnostních pravidel

RBXM read-only · Simulator read-only · `main`/PR#2 tabu · M3 gate platí · PENDING≠PASS · CODE≠RUNTIME · žádná Python simulace není runtime důkaz · každá změna vratná (pouze přidání souborů / cílené patche B) · cykly/závislosti se nemažou kvůli testům.
