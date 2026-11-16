# AutoEngineerAI

Autonomní inženýrský systém pro Roblox vozidla.

**Stav:** Fáze 0 – založení projektu, paralelní analýzy běží.
**Plán:** `docs/PROJECT-PLAN.md`
**Pravidla agentů:** `docs/AGENT-RULES.md`
**Stav prací:** `docs/STATUS.md`

## Pravidla (závazná)

1. Nový samostatný repozitář, pracovní název `Adalik1219/AutoEngineerAI`.
2. `RobloxSimulator` (C:/.DATA/RobloxSimulator) je pouze READ-ONLY zdroj znalostí — nikdy neupravovat, žádný commit/branch/PR.
3. Originál A-Chassis (`C:/Users/adamr/Downloads/chasis.rbxm`) nikdy nepřepisovat — pouze kopie.
4. AutoEngineerAI nesmí mít runtime závislost na RobloxSimulatoru.
5. Žádná změna bez měřitelných testů. Neúspěšná varianta se nesmí stát finále.
6. Matematická simulace ≠ důkaz funkčnosti v Roblox runtime.
7. Neodhadovat obsah souborů bez skutečného prozkoumání. Rozlišovat ověřená fakta / předpoklady / neznámé + uvádět zdroje a cesty.

## Struktura (tvoří se postupně, žádné prázdné adresáře bez účelu)

- `docs/` — ARCHITECTURE.md, A-CHASSIS-AUDIT.md, KNOWLEDGE-TRANSFER.md, VEHICLE-DATA.md, TESTING-OPTIMIZATION.md, ROBLOX-RUNTIME.md + PROJECT-PLAN.md, STATUS.md, AGENT-RULES.md
- `assets/chassis-original/` — pracovní kopie (ne originály)
- `vehicle-data/references/` — referenční profily reálných vozidel
