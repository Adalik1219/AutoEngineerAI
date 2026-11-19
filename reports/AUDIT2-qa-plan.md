# AUDIT2 — QA metodika pro finální review PR #2 (M1+M2 foundation)

**Větev:** `feat/m1-m2-foundation` · **HEAD pin:** `6cedbe1` · **PR #2: OPEN, NEMERGOVAT**
**Role:** Independent QA — POUZE metodika + read-only příprava. ŽÁDNÁ schválení, ŽÁDNÉ změny kódu/testů.
**Vlastněný soubor:** tento soubor (`reports/AUDIT2-qa-plan.md`) — jediný soubor, který tato role smí zapisovat.
**Vstupy:** `reports/AUDIT-qa-final.md` (revize `0f5b923`+dirty), `reports/FINAL_INDEPENDENT_QA.md` (revize `2bde563`),
diff `main...HEAD` (23–24 souborů, +5537/−53), `tests/run_all.py`.
**Poznámka k posunu HEAD:** oba vstupní reporty vznikly na starších revizích (`0f5b923`, `2bde563`); HEAD je `6cedbe1`
(`docs(qa): final QA podminky + koordinacni report`, docs-only dle message — OVĚŘIT v §A, ne předpokládat).
Tento soubor **nevydává verdikt MERGE / DO NOT MERGE** — pouze postup, podle kterého se finální review provede.

## A. Předběžné kontroly (pin + rozsah, bez čtení kódu)

- [ ] A1. `git rev-parse HEAD` == `6cedbe1`; `git status --short` čistý (žádné dirty soubory jako u `0f5b923`).
- [ ] A2. `git log --oneline main..HEAD` = 10 commitů končících `6cedbe1`; `2bde563..HEAD` = právě 1 commit.
- [ ] A3. `git diff main...HEAD --stat` proti §3 ve FINAL_INDEPENDENT_QA (22 souborů, +5355/−53):
  aktuální stat hlásí 24 souborů / +5537/−53 — vysvětlit deltu (nové: `FINAL_COORDINATION_REPORT.md`,
  `FINAL_DOCUMENTATION_SYNC.md` + změny docs mezi `2bde563→6cedbe1`). Nic nad rámec diffu se nemerguje.
- [ ] A4. Potvrdit, že `2bde563→6cedbe1` je docs-only: `git diff 2bde563..HEAD --stat` smí obsahovat
  jen `docs/*` + `reports/*`. Jakýkoli `src/*` / `tests/*` v tomto rozsahu = STOP, metodika neplatí, review se opakuje.
- [ ] A5. PR #2 stále OPEN a nemergnutý (kontrola v okamžiku finálního běhu, ne teď).

## B. Kontrolní seznam finálního review (co se čte, v jakém pořadí)

- [ ] B1. **Pokrytí diffu soubor po souboru** (podle `git diff main...HEAD --name-only`, aktuálně 23 jmen):
  `src/Inspection/rbxm_parser.py` (NEW), `src/Inspection/wheel_detect.py` (NEW), `src/Inspection/__init__.py`,
  `src/Reference/validate.py` (jediná měněná src mimo Inspection), `tests/test_m1_mustang_profile.py`,
  `tests/test_m2_rbxm_parser.py`, `tests/test_m2_wheel_detect.py`, 3× `docs/*`, 11–13× `reports/*`,
  1× `vehicle-data/*json`. Každý soubor: přečten ANO/NE + jedna věta, co tvrdí.
- [ ] B2. **Shoda docs s realitou** (regrese na §3 AUDIT-qa-final: PROJECT_STATUS 205/201 vs 260/256,
  ROADMAP "žádná čtečka neexistuje"): ověřit, zda `6cedbe1` podmínky splnil — PROJECT_STATUS §0/§0.2/§0.4
  = 260 běhů / 256 PASS / 4 PENDING; ROADMAP §M2 = parser CODE-VERIFIED, NOT IMPLEMENTED jen M2.9/M2.10.
  Dále 2 kosmetické podmínky z FINAL_INDEPENDENT_QA §2: `src/Inspection/__init__.py:1–4` stale docstring,
  překlep hashe `reports/AUDIT-geometry.md:8`.
- [ ] B3. **PENDING≠PASS kázeň:** `tests/run_all.py:8,36,42` — 4 PENDING vyjmenovány jménem na stejném místě
  jako číslo 256; grep `PENDING` vs `PASS` v `FINAL_*` + `PROJECT_STATUS §0` — holé "PASS/zelená" bez
  doprovodné věty = nález (docs-only).
- [ ] B4. **CODE-VERIFIED≠RUNTIME kázeň:** grep `RUNTIME|NOT IMPLEMENTED|BLOCKED` — kalibrace
  `calibrate_studs_per_meter` stub, `float_decode_unverified`, M3.1–M3.10 NOT IMPLEMENTED beze změny,
  `src/{Physics,Sim,Chassis,Optimizer}` nedotčeny (`git diff --stat src/` smí ukázat jen Inspection+Reference).
- [ ] B5. **Hash integrita:** kanonický RBXM SHA256 `dc8747e0…fedf` (230 421 B) shodný na všech citovaných
  místech (SPIKE :24–26/:96–99/:239–242, BENCHMARK :10–11, PROJECT_STATUS §0.4); JSON `cf28cc5c…52c` obě verze
  identický. LIMIT "1 distinctní model ve 2 kopiích" přiznán (SPIKE :114–117, AUDIT-format-compat §6).
- [ ] B6. **Výkonová tvrzení:** plošné "10–60×" se smí vyskytovat jen jako citace commit message `ff6f266`;
  normativní znění = BENCHMARK :87–89 ("hotspoty 5–240×, end-to-end ~2×"). Jakýkoli nový výskyt plošného
  "10–60×" mimo tento rámec = nález.
- [ ] B7. **Plný běh sady na HEAD:** `python tests/run_all.py` (očekávání dle obou reportů: 260 běhů /
  256 PASS / 0 FAIL / 0 ERROR / 4 PENDING; paralelně `pytest tests -q`: 256 passed / 4 skipped).
  Odchylka = STOP, verdikt se nevydává, jde se do triáže.

## C. Invarianty (musí držet po každé sondě; porušení = P0/P1)

- I1 **Fail-closed:** žádný neplatný vstup neprojde jako `GEOMETRY_OK` / `DETECTED`; výsledek je
  `BLOCKED`/`UNKNOWN` nebo `RbxmError` (`RbxmCorruptError`, `RbxmHierarchyError`). Žádný `TypeError`/`KeyError`/
  traceback ven, žádný tichý průchod.
- I2 **Nonfinite:** `size`/`position`/`rotation` s `inf`/`nan` → `nonfinite_*`, `GEOMETRY UNKNOWN`, `BLOCKED`.
  Platí i parciálně (jedna složka `inf`), i pro `−inf`, i pro špatný typ (`str`) → `bad_size`/`bad_position`/`bad_rotation`.
- I3 **Forest:** `roots != 1` (les o 2 kořenech) a self-loop `[(0,0)]` → `RbxmHierarchyError` v parseru,
  `forest` BLOCKED v `detect_wheels` i `assess`. Přímé volání `detect_wheels` mimo parser-cestu je známý
  follow-up (P2-2), neblokuje — ale parser-cesta cykly chytá VŽDY.
- I4 **Limity vymáhány před alokací:** `MAX_FILE_BYTES` (read `MAX+1` + re-check, `len()` před `bytes()`),
  `MAX_FIELD_VALUES=100_000` před stavbou seznamů, `MAX_UNCOMPRESSED_BYTES` u LZ4. Ověřuje se chováním
  (odmítnutí MAX+1), ne čtením konstanty.
- I5 **Kalibrační brána:** `calibrate_studs_per_meter` vždy NOT IMPLEMENTED; reálná geometrie vždy
  `trusted=False` + `float_decode_unverified`; celek na reálné kopii (44 dílů) je BLOCKED i když
  jednotlivá kola jsou GEOMETRY_OK (agregát zamítá, ne per-kolo chyba).
- I6 **Čísla sady:** 256+4=260; PENDING jsou 4 totožné pre-existing (Studio odečet, schema Fáze 5,
  2× regresní baseline). Nový SKIP/FAIL bez záznamu = porušení.

## D. Adversarial plán (vlastní sondy mimo repo; cíl: vyvrátit I1–I5)

Každá sonda: vstup → očekávaný výsledek → porušuje který invariant při odchylce. Sondy se píší do scratch
(`qa_probes*.py`, NE do repa) a spouští proti HEAD. Stop-kritérium: první sonda, která projde neplatnou
geometrií / crashne mimo `RbxmError` / projde tiše → konec, nález P0, dál se nepokračuje.

- [ ] D1 **Truncation:** prázdný vstup; useknutá hlavička; useknutý LZ4 payload → `RbxmCorruptError` (I1).
- [ ] D2 **Magic fuzz:** 5×64 náhodných bytů (jiný seed než F8-1000 v repu) → vždy "špatné magic", 0 crashů (I1).
- [ ] D3 **Limity:** soubor `MAX_FILE_BYTES+1` odmítnut před kopií; absurdní LZ4 délka → Corrupt (I4).
- [ ] D4 **Hierarchie:** parent cyklus A↔B; missing parent; les 2 kořenů; self-loop → BLOCKED/HierarchyError (I3).
- [ ] D5 **Nonfinite sweep (S1/S2 + rozšíření):** size `(inf,2.7,2.7)` / `(-inf,2.7,2.7)` / `(nan,…)` / negativní /
  nulová; pozice `inf`; rotace délky 8; rotace neortonormální; size jako `"2.7"` → `nonfinite_*`/`bad_*`,
  UNKNOWN+BLOCKED (I2). Kontrolní sonda: validní kolo → GEOMETRY_OK per-kolo, ale celek stále BLOCKED
  přes `float_decode_unverified` (I5).
- [ ] D6 **Agregát:** 4 kola se shodným středem (nulová plocha) → per-kolo OK, agregát BLOCKED
  (`wheel layout not rectangular` + kalibrační brána) (I5). `assess_wheel_geometry([])` → BLOCKED
  `missing Model:Wheels` (I1). Duplicitní `Name` PROP pro typ 0 → `RbxmCorruptError` (I1).
- [ ] D7 **Reálná kopie:** 815 instancí → 4 kola GEOMETRY_OK, celek BLOCKED (44 UNKNOWN dílů + unverified nota) (I5).
- [ ] D8 **Opakovatelnost:** celý adversarial běh 2×; druhý běh jiný fuzz seed. Shoda výsledků, jinak flake-nález.

## E. Zápis výsledku (co finální review odevzdá — ne tento soubor)

1. Tabulka dispozic P0/P1 z obou vstupních reportů (opraveno/zdůvodněno/trvá) s řádkovými odkazy na HEAD.
2. Tabulka sond D1–D8: vstup → výsledek → který invariant drží. Soubory sond ve scratch, ne v repu.
3. Seznam docs-neshod s přesnými `soubor:řádky` (formát podmínek z FINAL_INDEPENDENT_QA §2).
4. Číslo sady z re-běhu na `6cedbe1` (běhy/PASS/FAIL/ERROR/PENDING + jména 4 PENDING).
5. Verdikt až ve finálním reportu, ne zde; tento plán verdikt nepředjímá.

## F. Výslovné ne-cíle (mimo scope, nezkoumat / neměnit)

- Žádné změny `src/*`, `tests/*`, existujících reportů. Žádné schvalování PR.
- Preset-tabulka rotací, kalibrace `studs/m`, M3 runtime, diverzita reálných modelů (>1 distinctní RBXM),
  kalibrace tolerancí — přijaté limity / follow-upy, ne blokátory (viz AUDIT-qa-final §1–§4).
- Historie commitů se nepřepisuje (commit message `ff6f266` "10–60×" zůstává, kryta BENCHMARK zprávou).
