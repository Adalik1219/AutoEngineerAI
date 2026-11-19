# AUDIT2 — Bezpečnostní audit RBXM parseru (FÁZE A, pouze audit)

- HEAD: `6cedbe1` (větev `feat/m1-m2-foundation`, PR #2, NEMERGOVAT)
- Předmět: `src/Inspection/rbxm_parser.py` (1345 řádků), `tests/test_m2_rbxm_parser.py`
- CI: `gh run view 44581124660 --log-failed`
- Metoda: čtení kódu + cílené sondy na HEAD + lokální běh `python tests/run_all.py`
- Výsledek lokálně: **PASS (s 4 PENDING)** — všechny M2 parser testy včetně F1–F8 a fuzz 1000 mutací procházejí.

## Verdikt

Žádný P0 ani P1. Parser je fail-closed: všech 88 `raise` v souboru je
`Rbxm*` (grep `raise` bez `Rbxm` = prázdný), jediný `open()` je `'rb'`
(ř. 1034). Corrupt vstup → vždy `RbxmError`, nikdy tichý model.
3 nálezy P2 (kontrakt/robustnost, žádný tichý průchod, žádná záměna corrupt→valid).

## Ověřeno — bod po bodu

| Požadavek | Kde | Důkaz / sonda |
|---|---|---|
| size-před-kopií | ř. 608–612 | `len(data) > MAX_FILE_BYTES` **před** `bytes(data)`; `len()` kopii nepotřebuje. Test `test_b2_len_before_bytes` (< 5 s i pro 8 MiB+1 `bytearray`). |
| read(MAX+1) | ř. 1034–1039 | `handle.read(MAX_FILE_BYTES + 1)`, pak `len > MAX` → reject. Test `test_b2_parse_rbxm_read_cap`. |
| TOCTOU | ř. 1025–1028, 1019–1023 | `getsize` jen rychlá cesta s komentářem že může být zastaralé; autoritativní je read-cap. Růst souboru mezi `getsize` a `read` → odmítnuto po alokaci ≤ 8 MiB+1. |
| Agregátní dekomprese | ř. 398–402, 411–414 | Per-chunk cap před alokací + průběžný `total_uncompressed + uncomp_len` check **před** `lz4_decompress`. Test `test_f4_aggregate_bomb_scaled` (monkeypatch 4 KiB). |
| Limity před alokací | ř. 242, 262–266, 284–287, 320–323, 437, 491, 782 | `MAX_FIELD_VALUES` (100k) cap vždy **před** `len()`-checkem a stavbou seznamů; META/PRNT/INST county též. Testy `test_b2_field_value_cap`, `test_f3_length_fields_edge`. |
| LZ4 blokové kopie + překryvy | ř. 218–227 | Slice-kopie s rostoucím oknem (ekvivalent kopie po bajtech, O(log n)). Sonda: offset=1, `b'\x2FAB\x01\x00\x00'` → `AB`+`B`*19 bitově přesně; test 1 MiB expanze < 2 s. Striktní: overrun/underrun/nulový offset/trailing → `RbxmCorruptError` (ř. 174–232). |
| Limity instancí/polí | ř. 68–79 | `MAX_FILE_BYTES` 8 MiB, `MAX_UNCOMPRESSED_*` 256 MiB, `MAX_INSTANCES` 10M, `MAX_CHUNKS` 100k, `MAX_META_ENTRIES` 100k, `MAX_FIELD_VALUES` 100k. Agregátní strop instancí je fakticky PRNT cap 100k (sonda: 200k referentů → `PRNT: absurdni pocet`, 100k → parse 6.4 s / peak 131 MB — viz P2-3). |
| Corrupt délky | ř. 123–143, 389–410, 645–651, 776–792, 528–531, 325–343 | `_u32`/`_read_string` hranice; chunk rámec (useknutí/přestřelení/END+data); PROP < 8 B; PRNT payload `!= 8*count`; Name počet; CFrame orient-bloky. Testy 3, 4, F1–F3. |
| Duplicity | ř. 447–449, 476, 499–500, 634–635, 639–640, 675–676, 723–725, 741–745, 800–804 | META klíč, INST typ, referent id, META/SSTR/PRNT chunk, PROP/Name a geom PROP (klíč typ+jmeno), PRNT dup dítě + množina dětí == referenty. Les ≠ 1 kořen → `RbxmHierarchyError` (ř. 812–815); cykly iterativní DFS bez rekurze (ř. 535–562, testy 8/F7/self-loop). |
| RbxmError kontrakt | ř. 103–120, 601–607 | Hierarchie Corrupt/Unsupported/Hierarchy ⊂ RbxmError; ne-bytes vstup (str/None/int/…) → `RbxmCorruptError`, žádný únik `TypeError` (test `test_b2_input_type_check`). Fuzz 200 + 1000 mutací: jen `RbxmError` nebo platný model se stejnými počty (testy 13/F8). |
| Neznámé PROP tiše neinterpretovány | ř. 664–672, 766–774 | Neznámý chunk → `skipped_chunks`; neznámý PROP / špatný vtype u shape-size-CFrame → `skipped_props` status `unread`, nikdy odhad. `Name` s ne-string typem naopak tvrdý reject (identita, ř. 652–658). Test `test_unknown_type_skipped`. |

## Nálezy

### P2-1: `parse_rbxm` propouští `OSError` mimo `RbxmError` kontrakt
- Ř. 1033–1035: `with open(path, "rb")` není obaleno; chybějící soubor →
  holé `FileNotFoundError` (součást `OSError`, ne `RbxmError`).
- Repro: `parse_rbxm('C:/nonexistent-xyz.rbxm')` → `FileNotFoundError(2, …)`
  (ověřeno sondou na HEAD). Volající chytající jen `RbxmError` ho nezachytí.
- Fail-closed (žádný tichý model), proto P2, ne P1. Oprava ve FÁZI B mimo
  tento audit (např. `except OSError → RbxmCorruptError`).

### P2-2: SSTR s `shared==0` toleruje trailing bajty
- Ř. 464–468: kontroluje se jen první u32; zbytek těla se eviduje jako
  `opaque_bytes` bez validace (sonda: `u32(0)+b'GARBAGE'` → přijato).
- Bez dopadu na geometrii/identitu (SSTR se dál nepoužívá), ale striktní
  varianta (`len(body) != 4` → `RbxmCorruptError`) by byla konzistentní
  s META/PROP politikou přesných délek. Rozhodnutí ponecháno FÁZI B.

### P2-3: Worst-case paměť ~131 MB při 100k instancích (lokální DoS strop)
- Sonda: 2 typy × 50k referentů → parse 6.4 s, tracemalloc peak 131 MB
  (per-instance dict). Větší (200k) už odmítne PRNT cap 100k.
- Vstup je ohraničen 8 MiB souborem a jde o offline audit-tool, ne server;
  riziko jen lokální. Poznamenáno jako strop, ne chyba.

## CI log 44581124660 — není parser

Všech 10 `errors` v `tests (3.14)` je `FileNotFoundError`, žádný `Rbxm*`:
chybí LFS assety v runneru (`assets/chassis-original/chasis-work-copy.rbxm`)
a testy s absolutními Windows cestami (`C:/Users/adamr/Downloads/chasis.rbxm`,
`C:/.DATA/AutoEngineerAI/vehicle-data/...`). Parser logika v CI nespadla —
selhalo jen načtení fixture. Doporučení (mimo vlastněný soubor): fixture
vendorizovat nebo `skipIf` při absenci; absolutní cesty nahradit repo-root.

## Repro (vše na HEAD, lokálně)

- `python tests/run_all.py` → `VYSLEDEK: PASS (s 4 PENDING)`
- `parse_rbxm('C:/nonexistent-xyz.rbxm')` → `FileNotFoundError`, ne `RbxmError`
- `lz4_decompress(b'\x2FAB\x01\x00\x00', 21)` → `b'AB'+b'B'*19` (překryv OK)
- `_parse_sstr(u32(0)+b'GARBAGE')` → přijato (`opaque_bytes: 7`)
- 200k referentů → `RbxmCorruptError (PRNT cap)`; 100k → OK, 6.4 s / 131 MB
