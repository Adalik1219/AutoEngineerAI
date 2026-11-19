# FINAL INDEPENDENT QA — PR #2 (feat/m1-m2-foundation @ 2bde563)

Scope: final independent QA before merge decision. Read-only wrt code/tests/prior reports.
Owned file: this report only. HEAD verified 2bde563, PR #2 OPEN.

## 1. Verdict: MERGE WITH CONDITIONS (docs-only, non-blocking for code)

Code (M1+M2) is independently verified: 256 passed / 4 skipped / 0 failed (re-run
~18 s, 14 files green, +45 subtests), 23 adversarial probes with 0 crashes (all
refused safely as BLOCKED). No P0/P1 in code. No M3 runtime present.
Merge conditions below are docs-only cosmetics + merge-message discipline —
no code change required before merge.

## 2. Podmínky merge (konkrétní)

1. (docs-only) Opravit stale text `src/Inspection/__init__.py:1–4` ("C05/C06
   vznikne až po spike M2.1") — C05 v tomto PR už existuje. Ponechat funkčnost,
   jen docstring. Lze follow-up commitem po mergi.
2. (docs-only) Opravit překlep hashe `reports/AUDIT-geometry.md:8`
   (`dc8747e0…1fefdf` → `dc8747e0…c1fefdf` / `…fedf`); kanonický hash jinde sedí.
3. Merge message / PR popis musí nést: "256 PASS + 4 PENDING (PENDING≠PASS),
   CODE-VERIFIED není RUNTIME, M3 NOT IMPLEMENTED, Studio ground-truth PENDING".
   Důvod: "VÝSLEDEK: PASS (s PENDING)" a "sada zelená" jsou kryté pojistkou jen
   v kontextu (run_all.py:8,36,42) — holá citace bez druhé věty by matla.
4. Nemergovat nic nad rámec tohoto diffu (22 souborů, +5355/−53); M3 zůstává
   BLOCKED/NOT IMPLEMENTED.

## 3. Diff HEAD proti main — prošlé vše (22 souborů)

- `src/Inspection/rbxm_parser.py` (NEW, 1345 ř.): produkční C05 chunk reader,
  read-only; vlastní LZ4 (stdlib-only), INST+Name PROP, `_check_hierarchy`
  (cyklus/missing/duplicate → BLOCKED), limity (8 MiB, field caps),
  `assess_wheel_geometry` s isfinite hardeningem, `calibrate_studs_per_meter`
  vždy NOT IMPLEMENTED stub (:1325–1345). Bez závislostí, nic podezřelého.
- `src/Inspection/wheel_detect.py` (NEW, 311 ř.): pravidlo kol 1:1 z ROADMAP
  M2.2 (Model:Wheels + FL/FR/RL/RR + Ball, konjunkce a+b+c); UNKNOWN se záznamem,
  BLOCKED při chybějícím/duplicitním/cyklu/≠4; :26 "žádné fyzikální jednotky".
- `src/Reference/validate.py` (MOD, +39/−3): jediná měněná src mimo Inspection;
  M1.9 empty-torque-curve výjimka (:116–136) + factory-bez-zdroje error a
  minItems-2 suprese jen při M1.9 (:178–186,193–196,280–285). Úzké, správné.
- `tests/`: `test_m1_mustang_profile.py` (383 ř., 20 testů T01–T20 vč. M1.9
  bypass-rejekce a M1.5 promoce), `test_m2_wheel_detect.py` (285 ř., 21 testů),
  `test_m2_rbxm_parser.py` (1499 ř., ~53 testů: reálná kopie jen testy
  1/9/12/12b/fuzz, zbytek syntetický `build_model` builder — poctivě odděleno).
- `docs/`: ROADMAP M1→CODE-VERIFIED, M2→ČÁSTEČNĚ (C05 hotov, M2.4–M2.8 BLOCKED,
  M2.9/M2.10 NOT IMPLEMENTED), M3 NOT IMPLEMENTED beze změny; PROJECT_STATUS §0
  nový stav (260/256/0/4 @ ff6f266), §1–8 ponechán jako označený historický audit
  ("HISTORICKÉ…NEMAZAT" — citovat jen s hlavičkou); VEHICLE-SPEC v2 EU standard.
- `reports/` (11 nových): RBXM-SPIKE, 5× AUDIT, FINAL_PERFORMANCE_BENCHMARK,
  MUSTANG-SOURCE-CHECK, STUDIO_GROUND_TRUTH, FINAL_DOCUMENTATION_SYNC.
  Vše důkazní, žádný kód.

## 4. Tvrzení 10–60×: opraveno rozsahem ✓

- Původ: pouze commit message ff6f266 ("ref->type mapa, memoizace (10-60x…)").
  V kódu/docs HEAD se plošné "10–60×" nevyskytuje mimo samotnou opravu.
- Oprava: `reports/FINAL_PERFORMANCE_BENCHMARK.md:71–91` — :73 "NEPROKÁZÁNO
  A OPRAVUJE SE rozsahem", :75 end-to-end na reálné kopii (815 instancí) **~2×**
  (40.0→19.5 ms), :77–83 hotspoty: LZ4 ~49× (1 MB)/~241× (64 KB), ref→type ~32×
  (reálná škála, ~144× při 200k), memoizace ~5.5×/~14×; :87–89 opravené znění
  "hotspoty 5–240×, end-to-end ~2×; paměť beze změny"; :90–91 původce (commit msg,
  v repu není co patchovat — historie neměnná, kryto zprávou HEAD 2bde563).

## 5. PROJECT_STATUS / ROADMAP vs realita: sedí ✓ (1 záměrná past označena)

- M1 CODE-VERIFIED (20× `def test` ověřeno), M2 C05 CODE-VERIFIED / není RUNTIME
  (53+21 testů ověřeno), měření BLOCKED, kalibrace+M3 NOT IMPLEMENTED —
  odpovídá `src/` (žádný geometry modul; `src/` = common, Chassis, Inspection,
  Optimizer, Physics, Reference, Sim, Telemetry — M3 adresáře nedotčeny).
- HEAD je docs-only (`ff6f266→HEAD` jen docs+reporty) ⇒ číslo 260/256/0/4
  @ ff6f266 se vztahuje i na HEAD; nezávislý běh níže to potvrdil na HEAD.
- Past označena: PROJECT_STATUS §1 tabulka "M2 NOT IMPLEMENTED" je HISTORICKÁ
  (:10–11, :77); aktuální stav je §0. Kdo cituje §1 bez hlavičky, lže — soubor
  to zakazuje.

## 6. PENDING≠PASS a CODE≠RUNTIME: čisté, pojistky přítomny ✓

- `STUDIO_GROUND_TRUTH.md:3,16,32,38–41,47` — PENDING, prázdná _TBD_ pole,
  "PENDING → DONE only when all fields filled". Nic nevydáváno za důkaz.
- `FINAL_DOCUMENTATION_SYNC.md:11–13` — "PASS 256…PENDING 4…není PASS" na
  stejném řádku; :37 "IMPLEMENTED + CODE-VERIFIED, **není RUNTIME**".
- `AUDIT-qa-final.md:9–11,87,92,94–96,98–104` — PENDING vyjmenovány, verdikt
  "MERGE s podmínkami (docs-only)". "Zelená" = kód po odečtení PENDING.
- `FINAL_PERFORMANCE_BENCHMARK.md` — žádné PASS/PENDING/RUNTIME tvrzení.
- Zbytkové riziko: holé citace "PASS"/"zelená"/"MERGE" bez doprovodné věty —
  v souborech vždy kryto kontextem; proto podmínka č. 3 (merge message).

## 7. RBXM hash před/po: shodný ✓ (1 distinctní model, 2 kopie — LIMIT přiznán)

- Kanonický SHA256: `dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf`,
  230 421 B (`RBXM-SPIKE.md:24`). Před/po shoda na 4 místech (SPIKE :24–26,
  :96–99, :239–242; BENCHMARK :10–11; PROJECT_STATUS §0.4). JSON kanonický hash
  `cf28cc5c…52c` obě verze IDENTICKÝ.
- LIMIT přiznán (`RBXM-SPIKE.md:114–117`, `AUDIT-format-compat.md:6`): jeden
  model ve dvou kopiích (stejný hash/velikost); třetí různý RBXM neexistuje —
  generalizace za hranici 1 modelu není prokázána a není ani tvrzena.
- Reálná geometrie citována s `trusted=False` (kola 2.7³, symetrické středy,
  VehicleSeat 2×1×2) — strukturální důkaz, ne kalibrace.

## 8. M3 nespustitelná: potvrzeno ✓

Diff obsahuje jen `src/Inspection/*` + `src/Reference/validate.py`. Žádný
`src/Physics|Sim|Chassis|Optimizer` v diffu. ROADMAP M3.1–M3.10 nezačaty
(NOT IMPLEMENTED :95,113). Výskyty "fyzika/kalibrace" v nových souborech jsou
výslovně NOT IMPLEMENTED/BLOCKED brány (`calibrate_studs_per_meter`,
`float_decode_unverified`, wheel_detect :26). Žádné simulační číslo, žádný
Studio runtime důkaz.

## 9. Testy + vlastní adversarial sondy (nezávisle spuštěno)

- `pytest tests -q` na HEAD: **256 passed, 4 skipped, 0 failed, 0 error**
  (~18 s, +45 subtests; skips 1+1+2 pre-existing). Tvrzení 260/256/0/4 POTVRZENO
  (256+4=260). M2 cíleně: 74 passed (53 parser + 21 wheel_detect).
  (Prostředí: `pytest` nebyl předinstalován — `pip install pytest` potřeba;
  `pytest -q` z home visí — spouštět cíleně na repo.)
- 10 sondových skupin / 23 běhů, 0 crashů — vše bezpečně BLOCKED:
  S1 prázdný vstup / S2 useknutá hlavička → RbxmCorruptError; S3 fuzz 5×64
  náhodných bytů → vždy "spatne magic"; S4 MAX+1 B → odmítnuto před kopií;
  S5 absurdní LZ4 délka / S6 useknutý LZ4 → Corrupt; S7 parent cyklus A↔B /
  S8 missing parent → BLOCKED (parent_cycle/missing_parent); S9 size inf/NaN/
  neg → nonfinite/nonpositive_size, UNKNOWN+BLOCKED; S10 pozice inf →
  nonfinite_position BLOCKED; kontrola S9-ok → 4× GEOMETRY_OK ale výsledek
  stále BLOCKED kvůli `float_decode_unverified` (poctivé bez Studio ground-truth).
  Reálné RBXM (815 instancí): 4 kola GEOMETRY_OK, celek BLOCKED (44 UNKNOWN
  dílů + unverified nota). Limity vymáhány: MAX_FILE_BYTES, MAX_FIELD_VALUES,
  MAX_UNCOMPRESSED_BYTES, isfinite size/position/rotation + cross-check.
- Verdikt robustnosti: parser i detekce odmítají bezpečně, nikde tichý průchod
  ani neošetřená výjimka; nefinite hodnoty nikdy neprojdou jako GEOMETRY_OK.

## 10. Proč ne čisté MERGE / proč ne DO NOT MERGE

- Proti čistému MERGE: 2 kosmetické docs-vady (stale docstring, hash překlep)
  + citovatelnost "PASS" bez kontextu — vše řešitelné podmínkami, nic
  neblokuje kód.
- Proti DO NOT MERGE: není P0/P1 v kódu, testy zelené nezávisle, sondy bez
  crashů, dokumentace opravena rozsahem, PENDING/RUNTIME kázeň držena,
  M3 poctivě NOT IMPLEMENTED. Není co vracet k přepracování kódu.

---
# Dodatek — re-QA @ `36cbbdb` + dirty docs-sync (2026-11-19, pracovní strom)

Výše (§1–§10) je verdikt k `2bde563` — NEMAZÁNO, ponecháno jako historické.
Níže nový stav: HEAD pin `36cbbdbd3466184532c811589190d02ae1d1aea3`
(PR #2 OPEN, nemergováno — ověřeno `gh pr view`), pracovní strom dirty
(3 docs soubory: `PROJECT_STATUS.md`, `IMPLEMENTATION_ROADMAP.md`,
`FINAL_DOCUMENTATION_SYNC.md` — sync na `36cbbdb`, čísla 272/268/0/4).

## A. Metodika AUDIT2-qa-plan: odchylka A4 (není docs-only)

- A1: `git rev-parse HEAD` = `36cbbdb` (plán pinoval `6cedbe1` — posun o 2
  commity + dirty strom; pin tohoto dodatku je `36cbbdb`).
- A4 NEPLATÍ: `6cedbe1..HEAD` obsahuje **kód** (`src/Inspection/rbxm_parser.py`:
  OSError→`RbxmCorruptError` kontrakt; `tools/validate_contracts.py`: M1.9
  výjimka; `tests/`: T21/T22 + CI-portability + repo-relative fixture).
  Proto níže nová re-QA kódu, ne jen docs-kontrola.
- Diff `main...HEAD`: **34 souborů, +6352/−60** (proti 22/+5355/−53 v §2 —
  delta = fáze B kód + AUDIT2-* + CI testy + dirty docs-sync; nic nad rámec
  diffu se nemerguje; M3 adresáře `src/Physics|Sim|Chassis|Optimizer`
  nedotčeny — ověřen prázdný `git diff --stat` na těchto cestách).

## B. Dispozice podmínek z §2 (opraveno / trvá)

1. Stale docstring `src/Inspection/__init__.py:1–4` — OPRAVENO (nový text
   popisuje `wheel_detect.py` + `rbxm_parser.py` s provenancí; C05 přiznán).
2. Hash-překlep `reports/AUDIT-geometry.md:8` — OPRAVENO (`…2c1fefdf`,
   kanonický hash `dc8747e0…fedf` / 230 421 B sedí všude; viz C).
3. Merge-message disciplína — TRVÁ (podmínka níže přeformulována na 268/4).
4. Rozsah diffu — TRVÁ s novým číslem (34 souborů, +6352/−60 @ `36cbbdb`).

## C. Ověřeno na tomto stavu (vlastní běhy 2026-11-19)

- Testy `python tests/run_all.py` na pracovním stromě: **272 běhů / 268 PASS /
  0 FAIL / 0 ERROR / 4 PENDING** (PENDING totožné: Studio odečet, schema
  Fáze 5, 2× regresní baseline; PENDING≠PASS). Tvrzení dirty docs-syncu
  (272/268/0/4 @ `36cbbdb`) POTVRZENO vlastním během (~19 s).
- `tools/validate_contracts.py`: **24 kontrol / 0 chyb, ÚSPĚCH** (M1.9 výjimka
  v obou validátorech konzistentní; T21 přijme prázdnou UNKNOWN křivku,
  T22 zamítne 1-bodový bypass — kryto sadou).
- RBXM hash před/po: `dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf`,
  230 421 B — shodný (fixture `JeepTemplate.rbxm` čtena, žádný zápis).
  LIMIT 1 distinctní model ve 2 kopiích dál přiznán.
- `10–60×`: v `src/tests/tools` žádný výskyt; v docs jen benchmark-rámec
  (hotspoty 5–240×, end-to-end ~2×) + citace commit message — čisté.
- M3 nespustitelná: potvrzeno (žádný `src/Physics|Sim|Chassis|Optimizer`
  v diffu; `calibrate_studs_per_meter` dál NOT IMPLEMENTED stub;
  Studio ground-truth DONE potvrzuje hodnoty kol, stupeň dál CODE-VERIFIED).
- Fáze B kód (36cbbdb): OSError→`RbxmCorruptError` (soubor/adresář/neexistující
  → kontrakt, nikdy ven); lane-order MSB-první + Ball=0 doloženy v hlavičce
  parseru (`rbxm_parser.py:21–26`); CI-portability (repo-relative fixture,
  SKIP místo ERROR). Žádný P0/P1.

## D. Adversarial sondy (12 běhů, seed `20261119` ≠ repo F8, 0 crashů)

D1a prázdný vstup → `RbxmCorruptError` ✓ · D1b useknutá hlavička →
`RbxmCorruptError` ✓ · D2 magic fuzz 5×64 B → vždy špatné magic, 0 crashů ✓ ·
D3 `MAX_FILE_BYTES+1` → odmítnuto před kopií ✓ · D4a neexistující soubor →
`RbxmCorruptError` (nový kontrakt fáze B) ✓ · D4b adresář → `RbxmCorruptError` ✓ ·
D5a size `inf` / D5b negativní / D5c `str` → `nonfinite/bad_size`, UNKNOWN+BLOCKED ✓ ·
D6a 4 kola stejný střed → agregát BLOCKED ✓ · D6b `[]` → BLOCKED ✓ ·
D7 reálná kopie (815 instancí) → per-kolo OK, celek BLOCKED ✓.
**12/12 PASS**, invarianty I1/I2/I4/I5 drží (I3 kryta sadou — cykly/missing/les,
I6 = 268+4=272 výše).

## Verdikt dodatku: MERGE WITH CONDITIONS (podmínky níže)

Kód M1+M2 @ `36cbbdb` ověřen nezávisle (268 PASS, 12/12 sond, 0 crashů,
žádný P0/P1, M3 nepřítomna). Podmínky jsou docs-commit hygiena, ne kód:

1. Commitnout dirty docs-sync (3 soubory) před mergem — nemergovat
   s neměřeným stromem; čísla v něm (272/268/0/4) jsou tímto během kryta.
2. Merge message / PR popis: „268 PASS + 4 PENDING (PENDING≠PASS),
   CODE-VERIFIED není RUNTIME, M3 NOT IMPLEMENTED, 1 distinctní RBXM
   (LIMIT přiznán)".
3. Nemergovat nic nad rámec diffu `main...36cbbdb` (34 souborů, +6352/−60).

---
# Dodatek 2 — finální QA k HEAD `ff4a9d6` (2026-11-19, čistý strom)

Výše (§1–§10 + Dodatek k `36cbbdb`) = historie — NEMAZÁNO. Níže nový stav:
HEAD pin `ff4a9d6d3b4c15390f59c87ae480aff17fb115fe` (PR #2 OPEN, nemergováno),
pracovní strom čistý (`git status`: jen větev `feat/m1-m2-foundation`,
bez dirty změn). Rozsah: `main...ff4a9d6` = 5 commitů nad `86b04f2`,
samotné `ff4a9d6` = 5 souborů (+212/−21); celý diff `main...HEAD` =
**37 souborů, +6683/−63**. Žádná git operace nad rámec read-only
(`log`/`diff`/`show`/`status`); kód/testy/reporty (cizí) neměněny.

## E1. Verdikt: MERGE WITH CONDITIONS (docs-hygiena, ne kód)

Kód M1+M2 @ `ff4a9d6` ověřen nezávisle: **279 běhů / 275 PASS / 0 FAIL /
0 ERROR / 4 PENDING** (`python tests/run_all.py`, ~desítky s, shoda
s tvrzením commit message `ff4a9d6` „Lokal 279/275/0/4“), **11/11
adversarial sond PASS, 0 crashů**, žádný P0/P1, M3 nepřítomna.
Podmínky jsou kosmetika v docs + merge-message disciplína:

1. Merge message / PR popis musí nést: „279 běhů / 275 PASS + 4 PENDING
   (PENDING≠PASS), CODE-VERIFIED není RUNTIME, M3 NOT IMPLEMENTED,
   1 distinctní RBXM (LIMIT přiznán)“. Důvod: kanonické číslo HEAD je
   279/275 (ne 272/268 z `FINAL_DOCUMENTATION_SYNC.md` — viz E5).
2. (docs-only, lze follow-up po mergi) `reports/FINAL_DOCUMENTATION_SYNC.md:14`
   uvádí 272/268/0/4 — na HEAD zastaralé o +7 (5× `test_reference_loader_root`
   + netto portability). Aktualizovat na 279/275/0/4.
3. (docs-only, lze follow-up) `reports/STUDIO_RUNTIME.md:8` hlavička uvádí
   HEAD `86b04f2` — obsahově kryto stejnou session-metodou, jen pin zastaral.
4. Nemergovat nic nad rámec diffu `main...ff4a9d6` (37 souborů, +6683/−63);
   M3 zůstává BLOCKED/NOT IMPLEMENTED.

## E2. Diff `main...ff4a9d6` — prošlo vše (37 souborů)

- `src/Reference/loader.py` (+7/−3): `project_root()` = `parents[2]`
  `loader.py` (tj. `src/Reference/loader.py` → root), env `AUTOENGINEERAI_ROOT`
  jen explicitní override. Jediný nový hardcoded-řetězec nikde; ověřeno
  grepem (žádný `[A-Za-z]:[\\/]` v loaderu). Správné a minimální.
- `tests/test_reference_loader_root.py` (NEW, 78 ř., 5 testů): default
  z umístění souboru, references uvnitř repa, env override, schema + load_all
  bez env. Cílené, bez side-effectů (`mock.patch.dict`, žádný zápis do env
  na úrovni modulu).
- `tests/test_ci_portability.py` (+82/−cca): 8 → **11 testů**
  (1 repo-relative cesty + 5 loader + 1 fixture + 2 skip + 2 runner).
  Změna = posílení, ne oslabení: odstraněn import-time `os.environ[...] = ...`,
  slabý test `test_mustang_test_unifies_root_via_env` (kontroloval jen přítomnost
  `AUTOENGINEERAI_ROOT` v mustang testu) nahrazen 3 tvrdšími
  (žádný top-level `os.environ` zápis / fixture bez env / žádný hardcoded
  default ve zdroji loaderu). Mutace prokázána:
  (a) nový zdrojový test padne na starém loaderu
  (`r"C:/.DATA/AutoEngineerAI"` matchuje `ABSOLUTE_PATH_RE` — ověřeno proti
  `86b04f2:src/Reference/loader.py:24`);
  (b) starý mustang test měl top-level `os.environ[...] = ROOT`
  (`86b04f2:tests/test_m1_mustang_profile.py:26`), na HEAD žádný top-level
  `os.environ` (grep prázdný) — maskování odstraněno.
- `tests/test_m1_mustang_profile.py` (+7/−7 v rámci `ff4a9d6`): odstranění
  import-time env sjednocení (korektní směr — viz výše).
- `reports/STUDIO_RUNTIME.md` (NEW, 59 ř.): A-Chassis Tune read-only
  (Edit režim): `FSusStiffness/RSusStiffness = 20000`,
  `FSusDamping/RSusDamping = 500`, `Initialize` mapování na SpringConstraint
  (L261–274 + L344–357), Rojo 7.7.1 sync OK; Play kroky PENDING s postupem.
  Žádný runtime důkaz netvrzen — kázeň držena.

## E3. PENDING≠PASS a CODE≠RUNTIME: čisté ✓

- Runner: `tests/run_all.py:7–8,36,42` — „PENDING není PASS“, souhrn
  `279/275/0/4`, `VÝSLEDEK: PASS (s 4 PENDING)`. PENDING totožné 4
  (Studio odečet, schema Fáze 5, 2× regresní baseline) — vyjmenovány, žádná
  není vydávána za důkaz.
- `STUDIO_RUNTIME.md:3,45` — Play věci výslovně PENDING; §2 hodnoty Tune
  označeny jako Studio-přečtené (ne parser-výstup), runtime efekt PENDING (§3).
- `FINAL_DOCUMENTATION_SYNC.md:15,56,60–61,64` — PENDING≠PASS na stejném
  řádku jako číslo; „IMPLEMENTED + CODE-VERIFIED, **není RUNTIME**“; M3 NOT
  IMPLEMENTED; merge-message disciplína vyžadována.
- `docs/PROJECT_STATUS.md:3–4,51,60–63,67` — M1/M2-C05 CODE-VERIFIED
  (není RUNTIME), kalibrace NOT IMPLEMENTED, M3 NOT IMPLEMENTED.
- Zbytkové riziko jediné: holá citace „275 PASS / zelená“ bez druhé věty —
  kryto podmínkou E1.1 (merge message).

## E4. RBXM hash před/po: shodný ✓ (1 model, 2 kopie — LIMIT přiznán)

- `sha256sum`: `JeepTemplate.rbxm` i `chasis-work-copy.rbxm` =
  `dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf`,
  230 421 B — shoda s kanonickým hashem v commit message, SPIKE, BENCHMARK
  i testu (`EXPECTED_SHA256`/`EXPECTED_SIZE` v `test_ci_portability.py:41–43`
  — test zelený). Parser čte fixture (815 instancí přes `parse_rbxm`,
  ověřeno vlastním během), žádný zápis.
- LIMIT dál platí: 1 distinctní model ve 2 kopiích; generalizace za hranici
  1 modelu není tvrzena.

## E5. M3 nespustitelná: potvrzeno ✓

- `git diff --stat main...ff4a9d6 -- src/Physics src/Sim src/Chassis
  src/Optimizer` = prázdný. Jediná měněná `src/` = `Reference/loader.py`
  + `Reference/validate.py` (M1.9, fáze B) + `Inspection/*` (C05).
- `calibrate_studs_per_meter` dál NOT IMPLEMENTED stub; `STUDIO_RUNTIME`
  runtime efekt PENDING; žádná runtime jízda, žádné simulační číslo jako důkaz.

## E6. Testy: plný běh na HEAD zelený ✓

- `python tests/run_all.py` @ `ff4a9d6` (čistý strom):
  **behů=279 PASS=275 FAIL=0 ERROR=0 PENDING=4** — shoda s tvrzením commitu.
  Delta 272→279 = nové loader-root testy (5) + netto portability (+2):
  dokumentováno v E1.2 jako docs-staleness, ne kódová vada.
- CI workflow (`.github/workflows`, `run: python tests/run_all.py`) =
  kanonický runner; test `test_workflow_runs_run_all` zelený.
- Portability sada: 11/11 PASS v rámci plného běhu; oslabení žádné (E2).

## E7. Adversarial sondy: 11/11 PASS, 0 crashů (vlastní běhy 2026-11-19)

(Pozn.: první průchod měl 2× FAIL vinou harnessu — špatná očekávaná cesta
`parents[2]` u cizí kopie a špatný typ argumentu `_check_hierarchy`;
po opravě harnessu obojí PASS — chyba byla v sondě, ne v kódu.)

- P1 loader bez env na cizí cestě: kopie `loader.py` do `TMP/x/y/src/Reference`,
  bez env → `project_root()` = `parents[2]` té kopie (nikoli repo),
  `references_dir()` neexistuje (žádný hardcoded default) ✓; s env →
  přesně override ✓.
- P2 OSError kontrakt: neexistující soubor i adresář → `RbxmCorruptError`,
  žádný leak `FileNotFoundError`/`IsADirectoryError`/`OSError` ✓
  (kontrakt v `rbxm_parser.py:1039–1045`).
- P3 prázdný vstup + useknutá hlavička → `RbxmCorruptError` ✓.
- P4 fuzz 5×64 B (seed `20261119`) → vždy „špatné magic“, 0 crashů ✓.
- P5 `MAX_FILE_BYTES+1` → odmítnuto před kopií ✓.
- P6 parent cyklus A↔B (`{0:1, 1:0}`) → `RbxmHierarchyError` ✓;
  missing parent → `detect_wheels` BLOCKED ✓.
- P7 size `inf` → `detect_wheels` BLOCKED (`is_blocked`) ✓.
- Reálná fixture: `parse_rbxm` → 815 instancí, bez výjimky ✓.

## E8. Proč ne čisté MERGE / proč ne DO NOT MERGE

- Proti čistému MERGE: 2 zastaralé docs-piny (272/268 číslo, `86b04f2`
  v hlavičce STUDIO_RUNTIME) + citovatelnost holého „PASS“ — vše kosmetika,
  nic neblokuje kód; kryto podmínkami E1.1–E1.3.
- Proti DO NOT MERGE: není P0/P1 v kódu, plná sada zelená nezávisle,
  11/11 sond bez crashů, loader-fix i OSError-kontrakt prokázány chováním
  (ne jen čtením), portability testy posíleny (mutace chytají původní chybu),
  PENDING/RUNTIME kázeň držena, M3 poctivě NOT IMPLEMENTED.
  Není co vracet k přepracování kódu.

## Dodatek 3 — duální pin (externí audit 2026-11-19, HEAD `f3223cd`)

- Poslední commit se změnou kódu: `ff4a9d6` (loader, portability, Studio runtime).
- Finální HEAD včetně dokumentační synchronizace: `f3223cd` (tento stav).
- Aktuální ověřené počty: 279 běhů / 275 PASS / 0 FAIL / 0 ERROR / 4 PENDING.
- Podmínky E1.1–E1.3 splněny v diffu; verdikt MERGE WITH CONDITIONS trvá.
- Historické sekce výše (§1–§10, Dodatky 1–2) ponechány NEMAZÁNY.

---
# Dodatek 4 — duální pin: kód `ff4a9d6` / finální HEAD `8b2d80a` (2026-11-19)

Výše (§1–§10, Dodatky 1–3) = historie — NEMAZÁNO, nic se nepřepisuje.
Staré počty (256/4 @ `2bde563`, 268/4 @ `36cbbdb`) platí jen s datem/revizí;
kanonické číslo HEAD je níže.

- Poslední commit se změnou kódu: `ff4a9d6d3b4c15390f59c87ae480aff17fb115fe`
  (loader root z umístění souboru, mutation-proven portability, Studio runtime).
- Finální HEAD včetně dokumentační synchronizace:
  `8b2d80aece258f7c13532ac36903a91584992c9c` (PR #2 OPEN, NEMERGOVAT).
  Dodatek 3 pinoval `f3223cd` — mezistav; tento dodatek ho nahrazuje pinem
  `8b2d80a` (delta `f3223cd..8b2d80a` = jen docs, žádný kód/test).
- Testy @ `8b2d80a` (vlastní běh `python tests/run_all.py` 2026-11-19):
  **279 běhů / 275 PASS / 0 FAIL / 0 ERROR / 4 PENDING** — PENDING≠PASS
  (4 totožné: Studio odečet, schema Fáze 5, 2× regresní baseline).
- CI run #94 (ID 44597270328): **4/4 zelené** (tests 3.11, 3.12, 3.13, 3.14),
  kanonický runner `python tests/run_all.py`.
- Stupeň: M1+M2-C05 IMPLEMENTED + CODE-VERIFIED, **není RUNTIME**
  (CODE≠RUNTIME); M3 NOT IMPLEMENTED; 1 distinctní RBXM (LIMIT přiznán).
- Verdikt trvá: MERGE WITH CONDITIONS (E1.1–E1.3 splněny v diffu).

## Finální dodatek – synchronizace na HEAD `2155dfe` (2026-11-19)

- Poslední commit se změnou kódu: `ff4a9d6`.
- Předchozí dokumentační HEAD: `8b2d80a` (historický snapshot, ponechán výše).
- Aktuální finální HEAD: `2155dfe29a4a20bfffd32976beb79b1274a52c00`.
- Commit `2155dfe` obsahuje pouze dokumentační změny (diff `ff4a9d6..2155dfe`
  bez změn zdrojových souborů a testů).
- CI k finálnímu HEAD: run `44598711818` na `2155dfe` — 4/4 success
  (Python 3.11–3.14). CI run #94 (`44597270328`) k `8b2d80a` zůstává
  historickým důkazem pro nezměněný kód.
- Testy: 279 / 275 PASS / 0 FAIL / 0 ERROR / 4 PENDING (PENDING≠PASS).
  `tools/validate_contracts.py` 24/0 je lokální výsledek, ne CI.
- Stupeň: M1 CODE-VERIFIED; parser C05 CODE-VERIFIED (není RUNTIME);
  geometrie BLOCKED; kalibrace + M3 NOT IMPLEMENTED; 1 distinctní RBXM.
- PR #2 OPEN, NEMERGOVAT bez souhlasu. Formální GitHub reviews: 0
  (interní QA reporty nejsou formální reviews).
