# AUDIT2 kompatibility formátu RBXM — `src/Inspection/rbxm_parser.py` @ HEAD

**Datum:** 2026-11-19 · **Větev:** `feat/m1-m2-foundation` · **Commit:** `6cedbe1` (PR #2, nemergovat)
**Role:** Format Compatibility Engineer · **FÁZE A = POUZE AUDIT** (žádné změny kódu)
**Vstupy:** `src/Inspection/rbxm_parser.py` (1345 řádků), `reports/AUDIT-format-compat.md` (AUDIT1, proti `0f5b923`),
`reports/RBXM-SPIKE.md` (§1–8 + C05-C/D), `tests/test_m2_rbxm_parser.py` + `test_m2_wheel_detect.py`
**Metoda:** čtení kódu + živé sondy na pracovní kopii + běh testů. Pracovní soubory: jediný distinctní model
`dc8747e0…fedf` (230 421 B, 37 typů / 815 instancí) ve dvou kopiích — závislost na 1 modelu **trvá** (viz §7).

## 1. Verdikt (TL;DR)

- INST / PRNT / PROP / META / SSTR / END / LZ4 dekódování: **potvrzeno**, včetně nového hardeningu z `ff6f266`
  (`MAX_FIELD_VALUES` capy, TOCTOU-safe `read(MAX_FILE_BYTES+1)`, odmítnutí ne-bytes vstupu, `ref_to_type` mapa O(n)).
- Mezery z AUDIT1 **uzavřeny i s testy**: les → `RbxmHierarchyError` + BLOCKED (`test_forest_two_roots_rejected`),
  self-loop (`B1-F3a`), cykly délky 3 a 5 (F7).
- **Jeden nový podstatný nález (§2):** pořadí lane u enum PROP (`shape`, `_decode_enum_lanes`, „LSB lane první")
  je na reálném souboru **nevěrohodné** — 104× Part dává `0x01000000` a 1× Part `0x02000000` (přesné byte-swapy
  hodnot 1 = Block / 2 = Cylinder), takže padají do `unread`. Tvrzení AUDIT1 §4 „křížově ověřeno `{0:4, 1:104, 2:1}`"
  **není reprodukovatelné produkčním kódem**. Směr selhání je bezpečný (žádný odhad → assess BLOCKED), kola
  (Ball = 0, řádově invariantní) tím nejsou dotčena — ale §2 je povinná četba před M3.
- Tabulka podpora/skip (§5) jinak sedí; dvě drobné formulační odchylky opraveny tamtéž.
- Testy: `test_m2_rbxm_parser` **53 OK**, `test_m2_wheel_detect` **21 OK** (běh 2026-11-19).

## 2. NOVÝ NÁLEZ: lane-order u enum PROP nesedí na reálná data [střední; bezpečným směrem]

- `_decode_enum_lanes` (řádky 261–274): `value = lane[0] | lane[1]<<8 | lane[2]<<16 | lane[3]<<24` („LSB lane první").
- Živá sonda na pracovní kopii (109 instancí `Part`): **4× `read/Ball` (kola, hodnota 0), 104× `unread`
  („neznama hodnota enum 16777216"), 1× `unread` („neznama hodnota enum 33554432")**.
  `16777216 = 0x01000000`, `33554432 = 0x02000000` — přesné byte-swapy 1 a 2.
- Důsledek: buď jsou enum lane ve skutečnosti **MSB-první** (jako referenty i floaty — konzistentní se zbytkem
  formátu; pak by data dávala přesně spike-tabulku `{0:4, 1:104, 2:1}`), nebo soubor obsahuje absurdní enumy.
  První hypotéza je řádově pravděpodobnější, ale **audit ji nemůže rozhodnout bez ground-truth** —
  hodnota 0 (jediná `read`) je vůči pořadí lane invariantní, takže „křížová kontrola koly" o lane-order nic neříká.
- Proč to není fatální: neznámá hodnota → `status "unread"`, `value None`, nikdy odhad (§848–868); assess takové
  kolo označí `bad_shape` → BLOCKED. Žádná tichá geometrie nevzniká.
- Proč to přesto vadí: (a) AUDIT1 §4 / SPIKE C05-D prezentují `{0:4, 1:104, 2:1}` jako ověřený fakt dekodéru —
  produkční kód to nereprodukuje; (b) `trusted=True` u tvaru se fakticky opírá jen o hodnotu 0;
  (c) round-trip testy (`_encode_*` v testech) chybu lane-order **principiálně nemohou chytit** (kodér i dekodér
  sdílejí stejný předpoklad) — jediný arbitr je reálný soubor + Studio ground-truth.
- Doporučení (ne kód, politika): do M3 ground-truth zapsat očekávané `shape` všech 109 Partů z reálné kopie;
  pokud Studio potvrdí 104× Block + 1× Cylinder, je lane-order v `_decode_enum_lanes` obráceně a oprava patří
  do M3 s novým auditem. Do té doby neměnit (bezpečný směr).

## 3. Re-verifikace: INST / PRNT / META / SSTR / END / LZ4 (vše ✅, nad rámec AUDIT1)

| Bod | Stav na HEAD | Ověření |
|---|---|---|
| Delta-referenty, nesouvislá ID, duplicity, `is_service`, libovolné pořadí chunků | ✅ beze změny, potvrzeno | kód §250–258, §488–512; test `test_noncontiguous_referents` prochází |
| `MAX_FIELD_VALUES = 100_000` capy (referenty, enum/float lane, CFrame, Name, PRNT) před alokací | ✅ nově ve `ff6f266` | řádky 239–245, 263–266, 284–288, 320–324, 488–491, 512–516, 782–785; záměr P1-4 |
| `parse_bytes` odmítá ne-bytes vstup jako `Corrupt` (ne uniklý `TypeError`); délka před kopií | ✅ nově (P2-6/P1-1) | řádky 604–612 |
| `parse_rbxm` TOCTOU-safe: `read(MAX_FILE_BYTES+1)` po `getsize` | ✅ nově | řádky 1016–1040 |
| `ref_to_type` mapa O(n) místo kvadratického `next()` | ✅ nově (P1-5), sémantika stejná + `Corrupt` na interní nekonzistenci | řádky 817–825, 839–843 |
| PRNT: verze≠0 `Unsupported`; count/délka/duplicity/množina/parent/cykly | ✅ potvrzeno živě (815 vazeb, kořen `[0]`) | řádky 776–815 |
| Les (`roots != 1`) → `RbxmHierarchyError` v `parse_bytes` **a** BLOCKED `forest` v `assess` | ✅ **mezera AUDIT1 uzavřena** | řádky 812–815, 1108–1113; test `test_forest_two_roots_rejected` |
| Self-loop `[(0,0)]` → `RbxmHierarchyError` | ✅ potvrzeno živou sondou `_check_hierarchy({0:0})` | test `B1-F3a` (§1055) + F7 (cykly 3/5) |
| META (duplicita=`Corrupt`, `count>100k`), END, `reserved` nuly, neznámé chunky (dekomprimovat + evidovat) | ✅ beze změny | testy 1/3/5/C1 procházejí |
| LZ4-block: bloková match-copy (ekvivalentní po-bajtové, O(log n)), striktní délky/offsety | ✅ refaktor ověřen testy vč. bit-flip/usknutí | řádky 159–237; `test_fuzz_never_unsafe` (200 mutací + 5 trunkací, seed `20261119`) prochází |
| `assess`: `isfinite` brány size/pozice/rotace, `_is_rotation_matrix` (ortonormalita + det +1), memoizované řetězy předků | ✅ nově ve `ff6f266` (P0: inf dřív prošel jako GEOMETRY_OK) | řádky 1043–1055, 1204, 1224, 1241–1244, 1282–1285 |

## 4. Neznámá ID / presety → `unread`, žádný odhad (✅ potvrzeno živě)

- `shape` mimo 0/1/2 (vč. §2 hodnot `0x01000000/0x02000000`): `status "unread"`, `value None` s důvodem — 105× na reálné kopii.
- CFrame neznámá preseta (Attachment, id `32`, **56×**): CFrame `status "read"` (pozice čtena), ale `rotation None` +
  `rotation_status "unread-preset-32"`; assess to nově explicitně penalizuje (`unread_rotation`), dřív tichý průchod.
  **Upřesnění proti AUDIT1 §4:** signál „nečteno" je u CFrame v `rotation_status`, ne ve `status` — volající musí
  kontrolovat `rotation`, ne jen `status`.
- `PivotOffset` 100 % id 2 (identita), `CFrame0` odděleně od `CFrame`; `Name` s cizím typem → `Corrupt` (identita se nezamlčuje).
- `skipped_props` **879** záznamů s `{type_id, prop_name, value_type, status "unread", reason}` — nic se nepolyká tiše.

## 5. Tabulka podpora / skip vs realita (revize AUDIT1 §7)

Podporováno (čteno + validováno): hlavička · chunky · LZ4 · META · prázdná SSTR (`sstr = {shared_strings: 0, …}` —
pozn.: klíč modelu je **`sstr`**, ne `sstr_info` jako psala AUDIT1) · INST · PRNT vč. les-kontroly ·
`Name` · `size`/`CFrame`/`CFrame0`/`PivotOffset` (**vždy `trusted=False`**, kalibrace `NOT_IMPLEMENTED`) ·
`shape` čteno s `trusted=True`, **ale na reálné kopii jen 4/109 Partů `read`** (zbytek `unread`, viz §2) ·
END + integrita hashem mimo parser.
Vědomě přeskočeno (evidováno): 879× ostatní PROP · neznámé shape-hodnoty · neznámé CFrame-presety (rotace) ·
chybějící geometrie (`missing`, nikdy odhad z názvu).
Odmítnuto kontraktem: verze≠0 / neprázdná SSTR / PRNT verze≠0 → `Unsupported`; struktura/hierarchie/les/limity →
`Corrupt`/`HierarchyError` → BLOCKED. Floaty zůstávají `trusted=False` do M3 kalibrace — správně.

## 6. Živá čísla z reálné kopie (HEAD `6cedbe1`, `parse_rbxm` + `assess_wheel_geometry`)

- `37 typů / 815 instancí`, kořen právě `[0]`, `meta {ExplicitAutoJoints: true}`, census
  `META:1 · SSTR:1 · INST:37 · PROP:928 · PRNT:1 · END:1`.
- Kola FL/FR/RL/RR: `Part/Ball`, `size (2.7, 2.7, 2.7)`, středy symetrické (rozchod ≈ 5.99, rozvor ≈ 10.52, Y shodné),
  rotace matice (tuple). Assess: **`blocked=True`** — důvody: 44× UNKNOWN kandidátů v `Model:Wheels`
  + `float_decode_unverified` (kalibrace NOT IMPLEMENTED). Očekávaný stav pro M2.
- Třídy s největším zastoupením: Part 109, WeldConstraint 108, Attachment 72, TextLabel 60, ImageLabel 48.

## 7. Závislost na 1 distinctním modelu + doporučení pro 3. model (beze změny, zostřeno o §2)

Oba soubory v repu mají stejný SHA-256 `dc8747e0…fedf` — druhý distinctní RBXM **neexistuje**; vše výše stojí na
1 modelu + syntetice. Round-trip syntetika nemůže chytit chybu lane-order (§2) ani potvrdit floaty. Pro 3. model:
(a) maximálně odlišné třídy + neprázdná SSTR + les/hluboký strom + CFrame-presety mimo `0/2`;
(b) nezávislý implementátor bez kopírování `rbxm_parser.py`, shoda na množině referentů, parent-mapě, `shape`,
`size/pozici` v toleranci, seznamech `unread/missing`;
(c) do M3 ground-truth povinně i `shape` všech Partů reálné kopie (rozhodne §2);
(d) `trusted` u floatů uvolnit až po Studio kalibraci — do té doby BLOCKED.

## 8. DOPLNĚNÍ Fáze B (2026-11-19): oprava enum lane-order s důkazem

Nález §2 ověřen na reálné kopii při HEAD `53c2e23` (čtení pouze,
`open(rb).read()`; SHA-256 kopie před i po sondách
`dc8747e0…fedf` — G-01 drží):

- `parse_rbxm` na 109 instancích `Part`: **4× `read`/Ball (hodnota 0),
  104× `unread` („neznama hodnota enum 16777216" = `0x01000000`),
  1× `unread` („neznama hodnota enum 33554432" = `0x02000000`)**.
  Tvrzení AUDIT1 §4 / SPIKE C05-D `{0:4, 1:104, 2:1}` produkční kód
  **nereprodukuje** — je tím opraveno (SPIKE §C05-D, tato fáze).
- Surový payload `PROP/shape` typu 17 (`Part`): 436 B = 4×109.
  **lane0–2 = samé `00`, lane3 = `00 01 01 … 01 02`** (104× `01`,
  1× `02` na konci). Data tedy leží v poslední lane.
- Kontrolní přepočet obou hypotéz ze stejných bytů:
  LSB-první → `{0: 4, 16777216: 104, 33554432: 1}` (souhlas s dekodérem);
  **MSB-první → `{0: 4, 1: 104, 2: 1}`** — přesně spike-tabulka
  (4× Ball / 104× Block / 1× Cylinder). Pořadí lane u enum je tedy
  **MSB-první**, konzistentně s floaty; `_decode_enum_lanes` má lane
  obráceně. Oprava dekodéru patří do M3 s novým auditem (do té doby
  neměnit — bezpečný směr, `unread` → BLOCKED).
- Kola (Ball = 0) jsou vůči pořadí lane invariantní — nález se jich
  **netýká** (4× `read`/Ball potvrzeno i produkčním kódem).

---
*Fáze A audit — bez změn kódu. Vlastněný soubor role Format Compatibility Engineer.*
*Nález §2 (enum lane-order) je jediný bod, kde audit na HEAD rozporuje dřívější tvrzení; vše ostatní potvrzuje nebo uzavírá.*
