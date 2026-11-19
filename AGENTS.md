# AGENTS.md – instrukce pro agenty AutoEngineerAI

> Česky. Identifikátory, názvy tříd a kód anglicky. Podrobnosti: `docs/AGENT-RULES.md` (FÁZE 0 pravidla, stále platná).

## Co je AutoEngineerAI

Hybridní inženýrský systém pro Roblox vozidla: stroj počítá a připravuje, člověk testuje ve Studiu.
Vize: `docs/PRODUCT_VISION.md`. Proces: `docs/HYBRID_WORKFLOW.md`. Architektura: `docs/ARCHITECTURE.md`.
Aktuální stav: `docs/PROJECT_STATUS.md`. Co stavět a v jakém pořadí: `docs/IMPLEMENTATION_ROADMAP.md`.
Měřitelné brány: `docs/ACCEPTANCE_CRITERIA.md`. Cílové auto: `docs/VEHICLE-SPECIFICATIONS.md`.

## Závazná pravidla (porušení = zastavit a hlásit)

1. Originální `chasis.rbxm` / `JeepTemplate.rbxm` se nikdy nepřepisují; `RobloxSimulator` je read-only (žádný commit/branch/PR).
2. Pracuj na samostatné větvi, nikdy přímo na `main`. Merge jen se souhlasem uživatele.
3. Nezačínej implementaci modulu bez přečtení jeho sekce v `IMPLEMENTATION_ROADMAP.md` a stavu v `PROJECT_STATUS.md`.
4. Existující implementaci ověř čtením a rozšiřuj ji — nezakládej duplicitní moduly.
5. Každá hodnota má jednotku. Každý cíl má zdroj nebo označený odhad. UNKNOWN (`value: null`) se nevymýšlí.
6. PENDING není PASS. CODE-VERIFIED není RUNTIME-VERIFIED. Python simulace není důkaz Roblox runtime.
7. Jedna iterace/změna = jedna logická skupina parametrů. Každá změna má původní hodnotu a rollback.
8. Rozlišuj ověřená fakta / předpoklady / neznámé; uváděj absolutní cesty a zdroje.
9. Nepřepisuj historii F4–F7 na tvrzení o kompletním úspěchu — je experimentální a validační.
10. Před commitem: testy modulu + `python tests/run_all.py`; 4 PENDING testy se neobcházejí.

## Co agent smí / nesmí

- **Smí:** číst cokoli v repu; vytvářet/upravovat soubory ve svém rozsahu; přidávat testy; zakládat dokumentační PR.
- **Nesmí:** push na `main`; merge bez schválení; měnit cizí moduly mimo svůj úkol; zapisovat do originálních RBXM;
  vydávat simulaci za runtime důkaz; míchat EU/US a GT/Performance-Pack data.
