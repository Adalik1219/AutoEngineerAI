# AUDIT2 — Performance: ověření `reports/FINAL_PERFORMANCE_BENCHMARK.md`

- Větev `feat/m1-m2-foundation`, HEAD `6cedbe1`; audit čtením kódu + nezávislou reprodukcí, **bez změn kódu**.
- Metodika reportu: stará = `git show 0f5b923:src/Inspection/rbxm_parser.py`, nová = `ff6f266`
  (`src/Inspection/rbxm_parser.py`), read-only extrakce do scratch, reálný vstup
  `assets/chassis-original/chasis-work-copy.rbxm` (230 421 B,
  sha256 `dc8747e0…fedf` — ověřen shodný), `time.perf_counter()`, 1 warmup, medián+stdev+min/max.

## 1. End-to-end ~2× — POTVRZENO

- Nezávislá reprodukce (9 rep, stejný vstup, stejná metoda): stará medián **35.5 ms** → nová **17.4 ms** = **2.04×**.
  Report: 40.0 → 19.5 ms = 2.05×. Absolutní časy se liší strojem/zátěží, **poměr sedí**.
- Ekvivalence výstupů: obě verze 815 instancí, kanonický hash instancí shodný (moje kanonizace; report uvádí `cf28cc5c…52c` obě — IDENTICKÉ). B2 nemění chování. ✓

## 2. Hotspoty 5–240× — POTVRZENO v řádu, ne bitově

Všechny tři optimalizace doloženy diffem `0f5b923..ff6f266`:

- **LZ4 match-copy**: per-bajtová smyčka s testem délky za každý bajt → blokové slice-kopie s doubling oknem + jedna kontrola délky. Moje reprodukce platným blokem z `test_b2_lz4_block_copy_fast_and_exact`: 64 KB **122×**, 1 MB **69×** (report: 241× / 48.6×). Řádově shoda; přesná čísla závisí na n a zátěži — očekávané u mikrobenchmarku.
- **ref→type**: `next(... if ref in ref_pos[...])` za každou instanci (O(T×N)) → mapa `ref_to_type` postavená jednou (O(1) lookup, diff ř. ~+788/+839). Simulace stejného vzoru: 20×815 → **~23×** (report 31.7×), 100×2000 → **~94×** (report 144×). Řád sedí; rozdíl = harness (report měří v kontextu parse).
- **Ancestor memoizace**: `_ancestor_chain` → `cached_inside` + `chain_memo` se sdílením sufixů (diff `assess_wheel_geometry`). Kódově doloženo; D-specifika (N=1500, cold 5.5× / warm 14×) nebyla nezávisle přeměřena, ale mechanismus a řád jsou věrohodné.
- **Capy `MAX_FIELD_VALUES`**: v diffu čistě early-reject před stavbou seznamů — bezpečnostní, ne zrychlení. Report to uvádí správně.

## 3. Paměť „beze změny“ — POTVRZENO (spíše silněji než report)

- Moje `tracemalloc`: stará peak **1816.9 KiB**, nová **1816.0 KiB** — prakticky totožné.
- Report: stará 1779.8–1798.6 vs nová 1815.9–1816.0 (+2 %). Můj starý peak je o ~1 % vyšší než v reportu (šum prostředí); závěr „žádný únik ani násobný nárůst, CPU optimalizace“ platí v obou měřeních. ✓

## 4. Plošné „10–60×“ nikde — POTVRZENO

- `git grep "10-60|10–60" HEAD -- src docs tests` → **žádný výskyt**.
- Výskyt pouze: commit message `ff6f266` („10-60x rychlejsi“) + samotný benchmark report (jako opravené tvrzení) + `FINAL_INDEPENDENT_QA.md` / `FINAL_COORDINATION_REPORT.md` (odkazy na opravu). Není co patchovat v kódu. ✓
- Verdikt reportu je formulován správně po operacích (end-to-end ~2×; hotspoty dle škály; paměť beze změny).

## Drobné nálezy (neblokující)

1. Hlavička opraveného znění říká „hotspoty 5–240×“, ale tabulka B uvádí **241×** (64 KB) — překročení horní hranice o ~0.5 %, čistě zaokrouhlení. Doporučení: psát „5–250×“, nebo nechat (materiálně irelevantní).
2. Reprodukovatelnost je řádová, ne bitová (mikrobenchmarky B/C/D závisí na stroji a n). Report to řeší uvedením n/stdev/min/max — správně; moje čísla leží ve stejném řádu.
3. Bench skript `bench_b2.py` žije jen ve scratchi (v tomto prostředí nenalezen — scratch autora auditu je jiný adresář), takže kroky reprodukce v §Reprodukce jsou popisné, ne strojově ověřitelné z repa. Kryto existujícím testem `test_b2_lz4_block_copy_fast_and_exact` + mojí nezávislou reprodukcí výše.

## Verdikt

**POTVRZENO bez blokujících nálezů.** End-to-end ~2× reprodukován (2.04×), ekvivalence výstupů (815 instancí, shodný hash) reprodukována, všechny tři hotspotové mechanismy doloženy v diffu s řádově odpovídajícími zrychleními, paměť beze změny (oba ~1.8 MB), plošné „10–60×“ se v kódu/docs nevyskytuje. Jediné: zaokrouhlovací přesah 241× vs pásmo „5–240×“ — kosmetika.
