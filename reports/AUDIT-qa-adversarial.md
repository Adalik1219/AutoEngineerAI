# Nezávislý adversarial audit M2 (QA) — FÁZE A, bez změn kódu

**Větev:** `feat/m1-m2-foundation` · **commit:** `0f5b923` · **datum:** 2026-11-19
**Role:** nezávislý QA / adversarial reviewer. Žádný kód ani test nebyl měněn.
**Metoda:** vlastní přepočet z `parse_rbxm` instancí (ruční ancestor-walk, vlastní
sféricita/obdélník — **ne** voláním `assess_wheel_geometry`), vlastní adversarial
sondy `parse_bytes`/`detect_wheels`, běh celé sady `tests/run_all.py`.

## Verdikty po oblastech

| Oblast | Verdikt | Důkaz |
|---|---|---|
| Limity paměti | **PASS** | `MAX_FILE_BYTES` 8 MiB (getsize + len), `MAX_TOTAL_UNCOMPRESSED` 256 MiB průběžně v `_read_chunks`, `MAX_UNCOMPRESSED_BYTES` 256 MiB, `MAX_CHUNKS` 100 000, `MAX_INSTANCES` 10M, `MAX_META_ENTRIES` 100k; test B odmítá 8MiB+ blob i 300MiB chunk bez alokace |
| Referenty INST/PRNT | **PASS** | Nesouvislé referenty `[5,7,9]` projdou (test A1); PRNT kids = množina referentů, duplicita/mimo-množinu = `Corrupt`; parent mimo referenty = `HierarchyError`; duplicitní INST type_id / referent = `Corrupt` |
| Shape/Size/CFrame + trusted | **PASS** | Neznámý enum (9) → `unread`, `None`, žádný odhad; neznámý PROP typ → `skipped_props` `unread`; `Name` s jiným typem = `Corrupt`; `shape` jediné `trusted=True`, floaty vždy `trusted=False`; orient-id ≠ 0/2 → `unread-preset-N`, pozice čtena |
| Geometrie (vlastní přepočet) | **PASS** | FL/FR/RL/RR = Ball, size `(2.7,2.7,2.7)`, sféricita 0.0; středy (−45.1879/−51.1786, 23.6221, −203.2504/−213.7732); rozchod ≈ 5.99, rozvor ≈ 10.52, Y-spread 0.0; shoda s `RBXM-SPIKE.md` §C05-D; dílů ve stromě Wheels 48 (4 kola + 44 ostatních — shoda s „44 díly") |
| BLOCKED podmínky | **PASS** (1× P2 níže) | Cyklus / missing parent / duplicitní id / chybějící Wheels / 2×Wheels / ≠4 kola / UNKNOWN ve Wheels / asymetrie / missing geometrie / kalibrace — vše BLOCKED; reálná kopie: `detect_wheels` 4× WHEEL + BLOCKED, `assess` 4× GEOMETRY_OK + BLOCKED |
| Fuzz pokrytí | **PASS** | Seed `20261119`, 200 mutací (1–3 B) + 5 trunkací; jen `RbxmError` nebo strukturálně platný model; deklarace v testu = implementace |
| Shoda report↔kód | **PASS** | Census `META:1 SSTR:1 INST:37 PROP:928 PRNT:1 END:1`, 815 instancí, hash `dc8747e0…fedf`, oba soubory stejný model — vše potvrzeno během |
| Shoda PROJECT_STATUS↔realita | **FAIL** (P1) | §0 hlásí **205 běhů / 201 PASS**, realita **`235 / 231 / 0 FAIL / 4 PENDING`**; §0.2 tvrdí „produkční RBXM parser NOT IMPLEMENTED", ač ho větev implementuje (30+ testů C05-A/B/C/D v `test_m2_rbxm_parser.py`) |
| M2 dokončené? | **NE** (očekávané) | Kalibrace `studs/m` = `NOT_IMPLEMENTED`, geometrie reálné kopie vždy BLOCKED (44 dílů + `float_decode_unverified`); měření rozvoru/rozchodu jako ověřená čísla neexistuje — jen surové pozice `trusted=False`. C05 (čtení) hotovo, M2.9/M2.10+M3 nikoli |

## Adversarial sondy (vlastní, mimo testy v repu)

- **A. Neplatný RBXM** (rozbité magic) → `RbxmCorruptError`. OK
- **B. Neplatný float** (size = NaN) → parsováno strukturálně, `assess` = BLOCKED (`nonpositive_size`). OK, ale label pro NaN je zavádějící (P2-1)
- **C. Neznámá vlastnost** (`FooBar` 0x01) → `skipped_props`, `unread`, neinterpretováno. OK
- **D. Neúplná hierarchie** (PRNT bez dítěte) → `RbxmCorruptError`. OK
- **E. Špatné orientační id** (5) → rotace `None`, `unread-preset-5`, pozice čtena, soubor neodmítnut. OK (poctivé `unread`)
- **F. Nulový size** → BLOCKED (`nonpositive_size`). OK
- **G. Duplicitní Model:Wheels** → BLOCKED (`ambiguous`). OK
- **H. Ball mimo Wheels** → `UNKNOWN` (`not_in_wheels`), neblokuje cizí duplicita. OK

## Nálezy

- **P0: žádný.** Nenašel jsem cestu, kterou by prošel neplatný RBXM, falešná geometrie z názvů, tichá interpretace neznámých dat, nebo validní výsledek z neúplné hierarchie.
- **P1-1 (docs):** `docs/PROJECT_STATUS.md` §0.2/§0.4 je zastaralý — počty běhů (205/201 vs 235/231) i výrok o nehotovém produkčním parseru. Synchronizovat před/po merge PR #2.
- **P1-2 (docs):** M2 jako milník není dokončený (kalibrace + ověřené měření chybí) — status to na jednom místě říká, na jiném je matoucí; explicitně ponechat `NOT IMPLEMENTED / BLOCKED` až po M3 ground-truth.
- **P2-1:** NaN ve `size` padne do `nonpositive_size` — BLOCKED správně, ale label mate; zvážit `bad_size`/`nonfinite_size`.
- **P2-2:** `detect_wheels` na syntetickém vstupu nekontroluje cykly mezi non-Part uzly (parser-cesta cykly chytá vždy v `_check_hierarchy`; týká se jen přímého volání `detect_wheels` mimo parser). Zvážit stejný `_check_hierarchy` i zde.

## Verdikt

**MERGE s podmínkou** (žádný P0 v kódu; sada **235 běhů: 231 PASS, 0 FAIL, 0 ERROR, 4 PENDING**;
RBXM hashe beze změny, čtení pouze `rb`): před mergem PR #2 synchronizovat
`docs/PROJECT_STATUS.md` (P1-1: počty + přiznat hotový C05 parser při trvajícím
`NOT IMPLEMENTED` kalibrace/měření). P2-1/P2-2 jako follow-up, neblokují.
