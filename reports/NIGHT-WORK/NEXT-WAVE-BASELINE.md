# NEXT-WAVE-BASELINE — důkazní integrita, normalizace, rollback, QA

**Datum:** 20. 11. 2026 · **Koordinátor:** Hermes Agent
**Větev:** `feat/m2-m3-geometry` · **HEAD (doc):** `57043ee6369a968cc0714288d954c79b2c195eeb`
**Kódový SHA:** `8fd23cb4f8b04a018ea6f57748554d4de5000ecc` (rodiče `c3dc380` + `31f1180`; ověřeno `git show --pretty=raw`)
**Strom na začátku:** čistý · **`main`:** `5b673155e3b7b78ed2cf826814e57be433349681f` (beze změny)
**PR #2:** OPEN, base `main`, head `feat/m1-m2-foundation` (`ab840a92…`) — nesloučeno
**CI run `44758473223`:** success, 4/4 joby (3.11–3.14), kódový SHA 8fd23cb
**Změny `0f4670a..57043ee`** (10 souborů, `diff --check` čistý): 6 nových reportů (B, C-remediation, E-normalized, G-final, closeout, baseline) + `normalized_ids.json` + `tools/validate_normalization.py`; M `test_f4_integration.py`, `test_f4_mapping.py`. `src/`, katalog, schémata: 0 změn.

## RBXM a katalog (ověřeno)
- `testgame/.../JeepTemplate.rbxm`: blob `417b9f43…` (worktree = `8fd23cb` = zadání §10); 230 421 B. Historie před `bc6f955` se nedokládá.
- `src/Chassis/catalog/parameters.json`: blob `8f4d6bd1…` shodný v `0f4670a` i `57043ee` (beze změny).
- RobloxSimulator: čistý (READ-ONLY).

## Otevřené body (číslování této vlny)
N1 původních 60 ID nedoloženo (E: PENDING) · N2 validátor bez sémantiky (E1–E6) · N3 rollback `-m` neověřen · N4 tři vakuové testy bez identifikace · N5 reporty míchají historii s verdiktem · N6 14 katalogových návrhů bez inventáře · N7 U1–U6 bez definice · N8 StAxisOffset/magnitude (mimo rozsah).

## Vlastníci
Fáze 1 Agent F (rekonstrukce 60 ID) · Fáze 2 Agent E (validátor E1–E6 + testy) · Fáze 3 Hermes (rollback simulace) · Fáze 4 Agent C (identifikace vakuí) + Agent G (nezávislá kontrola) · Fáze 5 Hermes (sjednocení reportů) · Fáze 6 Hermes (návrhy+U1–U6 inventář) · Fáze 7 Agent G (finální QA na přesném SHA) · Fáze 8 Hermes (closeout).

## Worktrees (vše z `57043ee`)
- `C:/.DATA/AE-NW-F` (větev `nw-f-60ids`) — Agent F
- `C:/.DATA/AE-NW-E` (větev `nw-e-validator`) — Agent E
- `C:/.DATA/AE-NW-C` (větev `nw-c-tests`) — Agent C
- `C:/.DATA/AE-NW-G` (větev `nw-g-qa`) — Agent G (finální QA až po integraci)
