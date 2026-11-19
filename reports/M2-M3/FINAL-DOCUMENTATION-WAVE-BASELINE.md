# FINAL DOCUMENTATION WAVE — BASELINE (2026-11-19)

- Větev: `feat/m2-m3-geometry` · HEAD: `64be2c68cf57fad84a2e04a1ebf41a3e65827c04`
- Strom: čistý (ověřeno `git status --short` prázdný).
- PR #2: OPEN, nemergován (head `ab840a9` — tato větev není jeho součástí).
- M3: zavřená (žádný `src/Geometry/`, žádný geometry_target/diff).
- RBXM hash: `dc8747e0…2c1fefdf` (230 421 B, obě kopie shodné).

## Výchozí problémy k opravě

1. PROJECT_STATUS §0.2/§0.5 vs §10 — sjednotit engine vs výsledek kalibrace.
2. WHEEL-GEOMETRY-REPORT — ověřit GEOMETRY_OK texty po I-1 a počty testů.
3. FINAL-INDEPENDENT-QA historické podmínky — zkontrolovat uzavření.
4. INTEGRATION-TEST-REPORT — ověřit I-1 sekci + počty sad (161 vs 168 vysvětlit).
5. SCALE-CALIBRATION-REPORT hlavička vs dodatky; vysvětlit `calibrate_studs_per_meter`
   (parser, NOT IMPLEMENTED rozhraní) vs `scale_calibration.py` (engine).
6. CI run `44614661739` — ověřit vazbu na přesný finální SHA (dělá koordinátor §6).

## Rozsah vlny

Pouze dokumentace a audit. Funkční kód NEMĚNIT (výjimka jen doložená chyba
se souhlasem koordinátora). Žádný merge, žádná M3, `main` netknut.
