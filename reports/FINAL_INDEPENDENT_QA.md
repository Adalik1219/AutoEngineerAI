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
