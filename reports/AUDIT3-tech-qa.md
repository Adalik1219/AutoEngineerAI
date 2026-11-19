# AUDIT3 — technická QA (Agent C, read-only)

Větev `feat/m1-m2-foundation`, HEAD `8b2d80a`, PR #2 OPEN (NEMERGOVAT).
Metoda: pouze čtení + vlastní běhy (`tests/run_all.py`, `validate_contracts.py`,
`sha256sum`, `git log/diff/status`, `grep`). Žádný kód/test/docs měněn.
Kód shodný s `ff4a9d6` (`ff4a9d6..HEAD` = 5 souborů docs-only; `src/` + `tests/` prázdný diff).

## Stav po bodech (ověřeno 2026-11-19)

1. **M1: CODE-VERIFIED** — `tests/test_m1_mustang_profile.py` 22 testů (T01–T22),
   `tools/validate_contracts.py` 24 kontrol / 0 chyb, plný běh zelený (viz bod 8).
2. **Parser C05: CODE-VERIFIED, není RUNTIME** — `src/Inspection/rbxm_parser.py`
   1352 řádků; `test_m2_rbxm_parser.py` 54 testů, vše PASS v rámci plného běhu;
   žádná runtime jízda, žádné simulační číslo jako důkaz.
3. **RBXM: 1 distinctní model (LIMIT přiznán)** — oba soubory
   (`assets/chassis-original/chasis-work-copy.rbxm`,
   `testgame/.../JeepTemplate.rbxm`) sha256
   `dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf`,
   230 421 B, shodné. Čteno pouze (`rb`); originál nedotčen.
4. **Geometrie: BLOCKED** — `detect_wheels`: 4× WHEEL, ale BLOCKED;
   44 UNKNOWN dílů podvozku ve stromě Wheels (`AUDIT-geometry.md`);
   floaty `trusted=False` (`rbxm_parser.py:35,883–952`), tvar enum `trusted=True`.
5. **Studio Edit: ověřeno read-only** — `STUDIO_RUNTIME.md`: Edit režim,
   Tune Stiffness 20000 / Damping 500 přečteny, Rojo 7.7.1 sync OK;
   nic se nespouštělo, nic se nezapisovalo.
6. **Studio Play: PENDING** — `STUDIO_RUNTIME.md` §3 (LoadDelay 3.0 s postup),
   runtime efekt Stiffness/Damping neověřen.
7. **Kalibrace + M3: NOT IMPLEMENTED** — `calibrate_studs_per_meter` stub
   (`rbxm_parser.py:1332`); `git diff main...HEAD -- src/Physics src/Sim
   src/Chassis src/Optimizer` prázdný.
8. **Plný běh @ HEAD: 279 běhů / 275 PASS / 0 FAIL / 0 ERROR / 4 PENDING** —
   PENDING totožné (Studio odečet, schema Fáze 5, 2× regresní baseline).
9. **Stupně se nemíchají** — CODE-VERIFIED ≠ RUNTIME; PENDING ≠ PASS;
   IMPLEMENTED/RUNTIME-VERIFIED nikde netvrzeno nad rámec výše.
10. **Nálezy v kódu: žádné nové** — 0 P0/P1; E1.2–E1.3 z `FINAL_INDEPENDENT_QA.md`
    (docs-piny 272/268, `86b04f2` v hlavičce STUDIO_RUNTIME) jsou docs-hygiena,
    ne kódové vady. Nic neopravováno (role read-only).

## Povinná věta

279 běhů / 275 PASS + 4 PENDING (PENDING≠PASS), CODE-VERIFIED není RUNTIME,
M3 NOT IMPLEMENTED, 1 distinctní RBXM (LIMIT přiznán).
