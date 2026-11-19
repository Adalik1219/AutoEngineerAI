# AUDIT bezpečnosti parseru — `src/Inspection/rbxm_parser.py`

Rozsah: FÁZE A = pouze audit, kód neměněn. Revize `0f5b923` (PR #2), čteno
`src/Inspection/rbxm_parser.py` (1172 řádků) + `tests/test_m2_rbxm_parser.py`
celé. Metoda: čtení kódu + runtime důkazy (měření níže, ne jen konstanty).

## Shrnutí

- **P0: 0 — P1: 5 — P2: 2.** Žádný tichý průchod / integritní P0 nenalezen.
- Všech 7 nálezů je DoS (přealokace/CPU) nebo robustnost výjimek; každý má
  section "Důkaz" s naměřenou hodnotou a "Repro".
- K opravě větami: (1) v `parse_bytes` kontroluj `len()` před `bytes()`;
  (2) v `parse_rbxm` čti `read(MAX_FILE_BYTES + 1)` místo `read()` a zruš
  závislost na `getsize`; (3) přepiš LZ4 match-copy z append-po-bajtu na
  blokové kopie; (4) zaveď per-pole cap počtu (řádově 10⁵, ne 10⁷) před
  stavbou Python seznamů, nebo dekóduj streamovaně; (5) postav mapu
  `ref→type_id` jednou místo `next()` v cyklu; (6) na vstupu `parse_bytes`
  odmítni ne-bytes `RbxmCorruptError`; (7) v `assess_wheel_geometry`
  memoizuj hloubku/kořen místo chain-walku za každý Part.

## Ověřeno bez nálezu (požadované checkpointy)

- `MAX_TOTAL_UNCOMPRESSED`: součet se hlídá **před** každou alokací
  (ř. 377–380 před `bytes(...)`/dekompresí na ř. 381–385) a sčítá se za
  každý chunk (ř. 386). Obchvat součtem malých chunků není možný.
- `MAX_CHUNKS` (ř. 353): kontrola je na začátku iterace, smyčka bez `END`
  končí `RbxmCorruptError` (useknutá hlavička), nekonečná smyčka možná není.
- Jednotkový `MAX_UNCOMPRESSED_BYTES` (ř. 364) + `body_start + stored`
  proti `len(data)` (ř. 374): `comp_len` velkých těl se do paměti nevejde
  nad rámec 8MB souboru. Zbytkové riziko je **výška** limitů (viz P1-4),
  ne jejich umístění.
- `struct.unpack`/`IndexError` úniky: všechna `body[pos]` čtení mají
  délkový guard (`INST` ř. 439/447, `Name` ř. 474/478, `PROP` ř. 599/602;
  druhý průchod ř. 688–691 je krytý prvním — stejné tělo, stejný parse).
  `StopIteration` z `next()` na ř. 780 a `KeyError` z `parent_of[ref]` na
  ř. 913 jsou nedosažitelné (množiny `seen_ids`/`kids` se rovností
  vynucují na ř. 752). Jediný potvrzený únik mimo `RbxmError` je P2-6.

---

## P1-1 — `parse_bytes` kopíruje vstup před kontrolou velikosti

- **Řádky:** 560–566 (`data = bytes(data)` na ř. 562, kontrola až ř. 563).
- **Problém:** `bytes(bytearray/memoryview)` alokuje celou kopii dřív, než
  se limit vůbec vyhodnotí. Útočník s 256MB vstupem vynutí ~512MB špičky
  před odmítnutím. `len()` přitom kopii nepotřebuje.
- **Důkaz:** `parse_bytes(bytearray(9 MiB))` → `tracemalloc` peak
  **18,9 MB** (2× vstup 9,4 MB), pak teprve `RbxmCorruptError`.
- **Repro:** `python -c "import sys; sys.path.insert(0,'.'); from src.Inspection.rbxm_parser import parse_bytes; parse_bytes(bytearray(9*1024*1024))"` + `tracemalloc`.
- **Oprava:** pořadí otočit — nejdřív `if len(data) > MAX_FILE_BYTES:
  raise`, pak teprve `data = bytes(data)` (resp. `bytes(memoryview)` jen
  pro kratší než limit). Žádná změna sémantiky pro validní vstupy.

## P1-2 — `parse_rbxm`: TOCTOU `getsize` vs `read` + neomezené `read()`

- **Řádky:** 961–966 (`os.path.getsize` ř. 961, `handle.read()` bez limitu
  ř. 966; `parse_bytes` na ř. 967 limit znovu vymáhá).
- **Problém:** soubor může mezi `getsize` a `read` narůst (TOCTOU) —
  `read()` pak alokuje celé tělo (klidně GB) a teprve `parse_bytes` ho
  odmítne. Kontrola před načtením je tak jen poradní.
- **Důkaz:** kódová cesta — `read()` nemá žádný `size` argument, takže
  horní mez alokace je velikost souboru v okamžiku čtení, ne limit.
- **Repro:** připrav soubor těsně pod limitem, mezi `getsize` a `read`
  ho prodluž (smyčka na pozadí), nebo přímo soubor > limit + `parse_rbxm`
  — odmítnutí přijde až po alokaci celého `data`.
- **Oprava:** `handle.read(MAX_FILE_BYTES + 1)` a odmítnout při
  `len(data) > MAX_FILE_BYTES`; `getsize` ponechat jen jako rychlou cestu
  (ne jako bezpečnostní kontrolu).

## P1-3 — LZ4 match-copy kopíruje po jednom bajtu v Pythonu (CPU)

- **Řádky:** 205–209 (`for _ in range(match_len): out.append(...)`).
- **Problém:** každý výstupní bajt z matche projde Python iterací vč.
  `len(out) > expected_len` testu. Malý komprimovaný vstup expandující na
  desítky/stovky MB = desítky sekund CPU na jednom jádře.
- **Důkaz:** blok 8230 B expandující přes `offset=1` na 2 MiB se dekóduje
  **0,16 s** → lineárně ~**20 s na 256MB** limit. Literálová cesta je
  přitom rychlá (5 MiB za 0,01 s), takže bottleneck je výhradně tato smyčka.
- **Repro:** sestav token `0x2F` + literály `AB` + `offset=1` + extenty do
  `expected_len=2*1024*1024`, změř `lz4_decompress` (viz auditní skript).
- **Oprava:** blokové kopie (`out += out[len-out-offset : ...]` po segmentech
  / `bytearray.extend` s překryvem po mocninách dvou) + jedna kontrola
  délky na konci místo testu za každý bajt. Limit `expected_len` zůstává.

## P1-4 — Python-objektová expanze: limit 10M instancí je řádově mimo

- **Řádky:** dekodéry 218–236 (`_decode_referents`), 239–248
  (`_decode_enum_lanes`), 251–273 (`_decode_float_lanes`); capy 68–70
  (`MAX_INSTANCES = 10_000_000`), 457.
- **Problém:** 1 vstupní bajt → 1 Python `int`/`float` (~28–32 B + slot
  seznamu). Dekompresní bomba (KB komprimovaně → 100+ MB) se tak změní v
  GB Python objektů + minuty CPU, **uvnitř** povolených limitů.
- **Důkaz:** `_decode_float_lanes` pro `n=200 000` (2,4 MB vstup):
  **1,15 s / peak 19,3 MB** → extrapolace na povolených 10M:
  **~58 s / ~964 MB**. (Enum/referent lanes mají stejný poměr.)
- **Repro:** `_decode_float_lanes(b"\x00"*(12*200000), 200000, "probe")`
  pod `tracemalloc` + `time.perf_counter`.
- **Oprava:** per-pole cap počtu v řádu 10⁵ (reálná kopie má 815 instancí;
  cokoli nad ~10⁵ je mimo formátový účel) vynucený **před** stavbou seznamů,
  nebo dekódovat do `array('I'/'f')`/`memoryview` bez Python objektu na prvek.

## P1-5 — Kvadratický lookup `ref→type` ve finální smyčce

- **Řádky:** 778–782 (`for ref in sorted(seen_ids)` + `next(... for entry
  in inst_list if ref in ref_pos[...])` za každou instanci).
- **Problém:** `O(num_types × num_instances)` dict-lookupů. Dekompresní
  bomba s tisíci typy × desetitisíci instancemi = sekundy–minuty CPU.
- **Důkaz:** syntetika 400 typů / 10k instancí **0,10 s**; 2000 typů /
  50k instancí **3,15 s** (škáluje kvadraticky, reálná kopie 37/815 je
  0,001 s a problém skryje).
- **Repro:** sestav `ref_pos`/`inst_list` daných rozměrů a změř smyčku
  z ř. 780–782 izolovaně.
- **Oprava:** postavit `ref_to_type = {}` jednou při zpracování `INST`
  (ř. 596–597) a na ř. 780 jen `type_id = ref_to_type[ref]`
  (+ `RbxmCorruptError` při miss místo `StopIteration`).

---

## P2-6 — `parse_bytes(str/None)` uniká jako `TypeError`, ne `RbxmError`

- **Řádek:** 562 (`data = bytes(data)`; `bytes(str)` bez kódování).
- **Důkaz:** `parse_bytes("<roblox!")` → `TypeError: string argument
  without an encoding`; `parse_bytes(None)` → `TypeError`; volající
  chytající `RbxmError` (vč. fuzz-testu) takovou chybu nečeká.
  (`parse_bytes(123)` projde jako `bytes(123)` → `RbxmCorruptError`, OK.)
- **Repro:** tři jednolinkové volání výše, `except RbxmError` nezachytí.
- **Oprava:** na vstupu `if not isinstance(data, (bytes, bytearray,
  memoryview)): raise RbxmCorruptError(...)`.

## P2-7 — `assess_wheel_geometry`: chain-walk za každý Part je kvadratický

- **Řádky:** volání 1028–1031, `_ancestor_chain` 526–546.
- **Problém:** pro každý `Part` se jde celý řetěz ke kořeni. Hluboký
  (legální!) řetěz `PRNT` délky *d* s *d* Party = `O(d²)`. Konstrukční
  matematika: `PRNT` stojí 8 B/instanci, takže 8MB soubor pojme ~1M článků.
- **Důkaz:** syntetický `parent_of` řetěz: 200 walků při hloubce 8000 =
  **0,19 s** → všech 8000 walků **~7 s**; při hloubce 20000 **~53 s**.
  Škáluje kvadraticky, měřeno na `_ancestor_chain` přímo.
- **Repro:** `parent_of = {0: None} | {i: i-1}` + 200× `_ancestor_chain(i,
  parent_of)` u konce řetězu, stopky.
- **Oprava:** memoizace (hloubka/kořen spočtená jednou v `_check_hierarchy`
  nebo `functools.lru_cache` nad neměnným parent-mapem), případně cap
  hloubky.
