# FINAL_PERFORMANCE_BENCHMARK — B2: stará vs nová implementace `rbxm_parser.py`

- Datum měření: 2026-11-19
- Prostředí: Windows 11 AMD64, Python 3.14.9 (MSC v.1944 64 bit)
- Stará implementace: `0f5b923` (pre-B2, před `ff6f266`), extrahováno read-only přes
  `git show 0f5b923:src/Inspection/rbxm_parser.py`
- Nová implementace: `HEAD ff6f266` (`feat(M2): hardening fáze B+C`), `src/Inspection/rbxm_parser.py`
- Žádný zápis do repa během měření; benchmark skript pouze ve scratchi
  (`$SCRATCH/bench_b2.py` + extrahované `rbxm_old.py` / `rbxm_new.py`).
- Reálný vstup: `assets/chassis-original/chasis-work-copy.rbxm`
  (230 421 B, sha256 `dc8747e0…fedf`, pouze čtení; hash před/po shodný).
- Metoda: stejné vstupy pro obě verze, opakovaná měření, medián + stdev + min/max.
  `time.perf_counter()`, 1 warmup rep mimo statistiku.

## Shoda výstupů (korektnost zachována)

| Vstup | old instancí | new instancí | kanonický hash (sha256 JSON, sort_keys) |
|---|---|---|---|
| chasis-work-copy.rbxm | 815 | 815 | `cf28cc5c…52c` obě — **IDENTICKÉ** |

Stejné pro syntetické LZ4 bloky, ref→type sady i ancestor řetězy (assert v bench skriptu).
B2 nemění chování, jen rychlost + bezpečnostní capy (`MAX_FIELD_VALUES`).

## Měření

### A — end-to-end `parse_bytes`, reálná kopie (230 421 B, 815 instancí), n=15

| Verze | medián | průměr | stdev | min | max |
|---|---|---|---|---|---|
| stará | 40.009 ms | 40.127 ms | 1.076 ms | 38.279 ms | 41.681 ms |
| nová | 19.498 ms | 19.673 ms | 0.652 ms | 18.910 ms | 21.044 ms |
| **zrychlení (medián)** | **2.05×** | | | | |

### B — LZ4 `match-copy`, syntetický blok (1 literál + dlouhý match, offset=1)

| expected_len (blok) | stará medián | nová medián | zrychlení (medián) | n |
|---|---|---|---|---|
| 65 536 B (261 B) | 5.503 ms (stdev 0.216) | 0.023 ms (stdev 0.024) | **241×** | 7 / 11 |
| 1 048 576 B (4116 B) | 84.315 ms (stdev 7.746) | 1.734 ms (stdev 0.307) | **48.6×** | 7 / 11 |

Per-bajtová smyčka → blokové slice-kopie (O(n) → O(log n) bloků).

### C — `ref→type` resoluce (přesně nahrazený výraz `next(...)` → `ref_to_type[ref]`)

| Škála | stará medián | nová medián | zrychlení (medián) | n |
|---|---|---|---|---|
| 20 typů × 815 inst (16 300 refů, ≈ reálná kopie) | 13.143 ms (stdev 1.190) | 0.415 ms (stdev 0.038) | **31.7×** | 5 / 11 |
| 100 typů × 2000 inst (200 000 refů) | 1135.8 ms (stdev 61.9) | 7.879 ms (stdev 0.752) | **144×** | 5 / 11 |

O(T×N) scan → O(1) mapa postavená jednou.

### D — ancestor řetězy s memoizací, syntetický hluboký řetěz N=1500, dotaz všech 1500 uzlů

| Verze | medián | stdev | n |
|---|---|---|---|
| stará (bez memo) | 122.020 ms | 13.156 ms | 3 |
| nová memo (čerstvá cache / rep) | 22.178 ms | 1.004 ms | 7 |
| nová memo (teplá cache) | 8.491 ms | 1.822 ms | 7 |
| **zrychlení čerstvá / teplá** | **5.50× / 14.4×** | | |

### E — paměť, `tracemalloc` peak při parsování reálné kopie (3 replikace)

| Verze | peaky (KiB) |
|---|---|
| stará | 1798.6, 1779.8, 1779.8 |
| nová | 1816.0, 1815.9, 1815.9 |

Rozdíl ≈ +2 % (šum + jednorázová `ref_to_type` mapa). **B2 je CPU optimalizace,
paměťový profil se nemění** — žádný únik ani násobný nárůst.

## Verdikt k tvrzení „B2 10–60×“

**Tvrzení v této plošné podobě NEPROKÁZÁNO a OPRAVUJE SE rozsahem po operacích:**

- **End-to-end na reálné kopii (815 instancí): ~2×** (40.0 → 19.5 ms medián).
  Na tomto vstupu dominuje zbytek pipeline, ne tři optimalizované hotspoty.
- **Rozsah 10–60× platí pro izolované hotspoty, ne pro celý parse:**
  - LZ4 dlouhé match-copy: **~49×** (1 MB) až **~241×** (64 KB) — horní konec
    překračuje 60× u kratších bloků, dolní konec sedí v pásmu.
  - `ref→type` mapa při realistické škále (20×815): **~32×** — uvnitř pásma 10–60×;
    při větší škále roste nad něj (~144×).
  - Memoizace ancestor řetězů: **~5.5×** (čerstvá) / **~14×** (teplá) — spodní
    hranice pásma, resp. pod ní při cold-cache.
  - `MAX_FIELD_VALUES` capy: bezpečnostní (early-reject), ne zrychlení.
- Paměť: beze změny (≈1.8 MB peak obě verze).

Opravené znění: **„B2: hotspoty 5–240× dle operace a škály
(LZ4 ~49–240×, ref→type ~32× při škále reálné kopie, memoizace ~5.5–14×);
end-to-end na chassis kopii (815 instancí) ~2×; paměť beze změny; výstupy bitově shodné.“**
(Pozn.: „10–60×“ se vyskytuje pouze v commit message `ff6f266`, nikoli v kódu ani
docs — není co patchovat v repu; oprava je tímto reportem.)

## Reprodukce

1. `git show 0f5b923:src/Inspection/rbxm_parser.py` → scratch `rbxm_old.py`
   (read-only, bez zápisu do repa).
2. Spustit scratch `bench_b2.py` (komponenty A–E výše, asserty ekvivalence).
3. Skript ani extrahované moduly **nepatří do repa** — pouze scratch.
