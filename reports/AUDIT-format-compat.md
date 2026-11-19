# AUDIT kompatibility formátu RBXM — parser `src/Inspection/rbxm_parser.py`

**Datum:** 2026-11-19 · **Větev:** `feat/m1-m2-foundation` · **Commit:** `0f5b923`
**Role:** RBXM Format Compatibility Engineer · **Fáze A = POUZE AUDIT** (žádné změny kódu)
**Vstupy:** `src/Inspection/rbxm_parser.py` (1172 řádků), `reports/RBXM-SPIKE.md` (§1–8 + C05-C/D), `tests/test_m2_rbxm_parser.py` (864 řádků, builder `_chunk/_inst/_prnt/_encode_*`)
**Model k dispozici:** jediný distinctní RBXM (`dc8747e0…fedf`, 230 421 B, 37 typů / 815 instancí) ve dvou kopiích — viz SPIKE LIMIT.

## 1. Verdikt (TL;DR)

Parser je **konzervativní a poctivý**: co neumí, eviduje jako `unread`/`skipped` nebo odmítne (`RbxmCorruptError` / `RbxmUnsupportedError` / `RbxmHierarchyError`), nikdy netiše neprochází. Pro auditované oblasti **nenalezena žádná fatální chyba dekódování** — všechny body níže jsou buď potvrzené, nebo vědomá omezení s doporučením pro 3. nezávislý model. Jediné **střední riziko**: kalibrace floatů (ror1/MSB-lane) je strukturálně ověřená, ale bez Studio ground-truth — proto `trusted=False` + `BLOCKED` je správně a nesmí se uvolnit před M3.

## 2. INST — referenty, nesouvislá ID, duplicity, pořadí chunků

| Bod | Stav | Nález |
|---|---|---|
| Delta-referenty (4 lane, MSB první, zigzag, akumulace) | ✅ odpovídá | `_decode_referents` (§218–236): `raw = L3\|L2<<8\|L1<<16\|L0<<24`, `acc += zigzag(raw)`. Na reálné kopii dává přesně `0..814`; syntetický round-trip (`_encode_referents` v testech) sedí. |
| Nesouvislá ID | ✅ podporována | Žádný předpoklad `0..n`: `seen_ids` je množina, `instances` řazeny `sorted(seen_ids)`, PRNT kids validovány jako **množina** proti INST (§747–754). Test `test_noncontiguous_referents` `[5,7,9]` prochází. |
| Záporný referent v INST | ✅ odmítnut | `ref < 0 → RbxmCorruptError` (§461). Správně: záporné ID v INST nemá význam (zápor je legální jen jako parent `-1`). |
| Duplicitní referent napříč INST | ✅ corrupt | `ref in seen_ids → Corrupt` (§464). Test 7 kryje. |
| Duplicitní INST `type_id` | ✅ corrupt | Nově v C05-C (§442). Test `test_inst_validation` kryje. |
| Prázdné jméno třídy / `is_service ∉ {0,1}` | ✅ corrupt | §445–453. Reálná kopie: všude `0`. |
| Pořadí chunků | ✅ libovolné | INST/PROP/PRNT se sbírají do seznamů a vyhodnocují až po všech chuncích (§667, §682). `num_types`/`num_instances` z hlavičky se kontrolují proti součtům (§638–645), ne proti pořadí. Mezera: **pořadí INST chunků vůči sobě není nijak normalizováno** — nevadí, `type_by_id` je dict. |
| `MAX_INSTANCES` na hlavičku i INST county | ✅ před alokací | §333, §458. |

**Doporučení (INST):** žádná oprava; 3. model otestovat s referenty mimo `0..n` (např. velké mezery, sestupné pořadí v PRNT kids) — viz §9 fixture F1.

## 3. PRNT — mapování, NULL_PARENT, cykly, chybějící, více kořenů

| Bod | Stav | Nález |
|---|---|---|
| Kódování kids/parents | ✅ odpovídá | Stejný lane-formát jako INST, kids = prvních `4*count` B, parents = druhých `4*count` B (§743–746). `prnt_count == num_instances` (§736), délka payloadu přesně `8*count` (§741). |
| `version != 0` | ✅ unsupported (ne corrupt) | §732–734, `RbxmUnsupportedError`. Správné rozlišení; test C4 kryje. |
| NULL_PARENT (`-1` = kořen) | ✅ správně | Zigzag `1 → -1` (§139–141 mapuje i `-1`), `parent_of[child] = None` jen pro `-1` (§760). Ostatní záporné hodnoty: projdou zigzag-dekódováním jako záporné a padnou na `parent not in seen_ids → RbxmHierarchyError` (§757). Korektní. |
| Dítě mimo referenty INST (i číselně "v rozsahu") | ✅ odmítnut | Množinová kontrola `set(kids) == seen_ids` (§752) + rodič mimo množinu → `RbxmHierarchyError` (§757). Testy 6/A2 kryjí. |
| Duplicitní dítě | ✅ corrupt | `len(set) != len → Corrupt` (§750). Test A2 kryje (kids `[0,0]`). |
| Cykly (A↔B, delší, self-loop) | ✅ BLOCKED | `_check_hierarchy` iterativní DFS s barvami O(n) (§496–523) + `_ancestor_chain` pro assess (§526–546). Self-loop `[(0,0)]`: `kids={0}==seen`, pak `parent_of[0]=0`, `_check_hierarchy` detekuje cyklus délky 1 — pokryto logikou, **ale není explicitní test self-loopu** (jen A↔B v testu 8). Doporučuji přidat do 3. modelu/syntetiky. |
| Chybějící PRNT / duplicitní PRNT | ✅ corrupt | `prnt_seen != 1 → Corrupt` (§630, §646). |
| Více kořenů | ⚠️ **mezera — nekontrolováno** | Parser vyžaduje jen `set(kids)==seen_ids` + acykličnost; les o 2+ kořenech (`parent None` u více id) **projde bez chyby**. Na reálné kopii je kořen právě `[0]` (test 1), ale formátově je les legální stav, který `detect_wheels`/`assess` neřeší. Není to chyba dekódování, ale **sémantická díra**: M2 předpokládá jeden kořen. Doporučení: 3. model + explicitní politika (BLOCKED při `roots != 1`), viz §9 F2. |
| Osiřelý parent (kid chybí v PRNT) | ✅ odmítnut | Množinová rovnost to chytí oběma směry. |

## 4. PROP — Name / shape / size / CFrame / CFrame0 / PivotOffset

| Vlastnost | type-byte | Stav | Nález |
|---|---|---|---|
| `Name` | `0x01` string, inline | ✅ | `_parse_name_prop`: počet jmen musí sedět s počtem instancí typu (§489); `type_id` musí existovat (§672); duplicita `Name` pro typ → corrupt (§677). Chybějící **celá** Name PROP → `name None / missing` + `missing_name_count/unnamed_ids` (§768–772, §916), nikdy rozpoznaný objekt. `Name` s jiným typem → corrupt (§607–612) — správně, jinak by se zamlčela identita. Testy C5/5 kryjí. |
| `shape` (PartType enum) | `0x12`, 4 lane LSB-první, bez zigzagu/delt | ✅ | `_decode_enum_lanes` (§239–248). Křížově ověřeno: `{0:4, 1:104, 2:1}` = 4× Ball (kola) dle auditu §10. Mapováno jen `0/1/2 → Ball/Block/Cylinder` (§87); **jiná hodnota → `unread`, tvar `None`, žádný odhad** (§798–806). Test E5 (enum 9) kryje. |
| `size` (Vector3) | `0x0E`, component-major, MSB-první, ror1 | ✅ strukturálně | `_decode_float_lanes` (§251–273). Kola `(2.7,2.7,2.7)`, seat `(2,1,2)`, 327/327 kladných — silný strukturální důkaz. Ale **bez Studio ground-truth** → vždy `trusted=False` (§820–826). Správně. Adversarial test E4 (prohozené lane) prokazuje, že špatné pořadí lane dá jiné hodnoty, ne tichou geometrii. |
| `CFrame` / `CFrame0` / `PivotOffset` | `0x10`: orientační bloky + pozice float-lane | ✅ strukturálně | `_parse_cframe_array` (§276–310): `u8 id [+ 9×f32 LE]` pak pozice. Part N=109: `109×(1+36)+12×109` sedí na bajt; 109/109 matic ortonormálních det +1; PivotOffset všude id 2 + pozice `(0,0,0)`. Test D (round-trip) kryje. |
| Presety id `0` / `2` | — | ✅ odpovídají předpokladům | `0` = vlastní matice 36 B (§298–304); `2` = identita bez dat (§305–306). Na reálné kopii: Part-CFrame mix `0/2`, PivotOffset 100 % `2`, Attachment 56× id `32`. |
| Neznámá orientační id (7, 32, …) | ✅ `unread`, bez odhadů | `_parse_cframe_array` vrací `matrix None` (§308); instance má `position` čtenou, `rotation None`, `rotation_status "unread-preset-N"` (§843–858). Test D2 (id 7) kryje; reálná kopie: Attachment id `32` poctivě neinterpretován. **Není odhadována ani identita** — správně. |
| `CFrame0` vs `CFrame` vs `PivotOffset` | ✅ jednotné kódování, oddělené klíče | Klíč `(type_id, prop_name)` (§695); duplicita stejné dvojice → corrupt (§696–700). `CFrame` jde do `position/rotation` instance, `CFrame0/PivotOffset` jen do `props` (§874–899). Správné: joint-offsety se nemíchají se světem. |
| Duplicitní geometrický PROP | ✅ corrupt | Test C3 kryje. |
| PROP pro neznámý typ | ✅ corrupt | §692–694. Test C3 kryje. |
| Kombinace jméno/typ mimo M2 | ✅ `skipped_props` s `unread` | §720–728. Není tichý průchod — volající vidí `skipped_props`. Test 5 (`Shape` s `0xFF`, velké `S`) kryje. Pozn.: kontrola je **case-sensitive** (`"Shape" ≠ "shape"`) — odpovídá reálnému formátu, kde záleží na velikosti písmen. |
| Chybějící geometrie u Part/Union/VehicleSeat/Attachment | ✅ `missing`, nikdy odhad | §807–872. Test E3 kryje. |

## 5. SSTR — podporováno vs nepodporováno

| Bod | Stav |
|---|---|
| Prázdná tabulka (`nshared == 0`) | ✅ podporováno; `sstr_info = {shared_strings: 0, opaque_bytes: len-4}` (§434). Reálná kopie: prázdná (§68 SPIKE). |
| Neprázdná tabulka (`nshared != 0`) | ✅ **odmítnuto jako `RbxmUnsupportedError`** (§430–433), ne corrupt — správně, protože inline-Name by pak nemusela být úplná. Test C2 kryje. |
| Chybějící SSTR chunk | ✅ tolerováno (`sstr_info` default, §648). Formátově je SSTR volitelný; správně. |
| Duplicitní SSTR | ✅ corrupt (§594). |
| Tělo kratší než 4 B | ✅ corrupt (§428). |

## 6. META / END / LZ4 / délky / duplicity / edge

| Bod | Stav |
|---|---|
| META slovník `u32 count + string páry` | ✅ `_parse_meta` (§397–420). Reálná kopie: `ExplicitAutoJoints=true`. Duplicitní klíč → corrupt (§413) místo tichého přepsání. `count > 100k` → corrupt před alokací. Přebytečná data → corrupt (§417). Test C1 kryje. Duplicitní META chunk → corrupt (§589). |
| END | ✅ `body == </roblox>` jinak corrupt (§633); data za END → corrupt (§391). `complen==0` raw cesta (§370). Testy 1/3 kryjí. |
| LZ4-block dekompresor | ✅ striktní: useknutý token/délka/literaly/offset, nulový offset, offset > len(out), překročení/přebytek → vše `RbxmCorruptError` (§149–215). Překrývající se match-copy po bajtech — legální. Test 4 kryje 4 vektory + bit-flip/usknutí v celém souboru. |
| Délky chunků | ✅ `comp_len==0 → stored=uncomp_len` jinak `comp_len` (§370); hranice `body_start+stored <= len` (§374); absurdní `>256 MiB` před alokací (§364); `total_uncompressed` průběžně před každou dekompresí (§377) — opraveno v C05-C (dřív až po). Test B kryje (8 MiB+ blob, 300 MiB `uncomp_len`). |
| `reserved` 4 B v chunku / 8 B v hlavičce | ✅ musí být nuly (§361, §331), jinak corrupt. Přísné, ale odpovídá pozorovaným datům; jiná verze formátu by stejně padla na `VERSION`/`PRNT version` jako unsupported. |
| Neznámé chunky | ✅ dekomprimovány (kontrola integrity) + evidovány v `skipped_chunks` + `chunk_census`, ne tiše zahozeny (§635–636). Test 5 (`XXXX`) kryje. |
| `MAX_CHUNKS 100k` před appendem | ✅ (§354). |
| Fuzz 200 mutací + 5 trunkací, seed `20261119` | ✅ jen `RbxmError` nebo strukturálně platný model; mutace v řetězcích detekovatelná jen hashem (formát nemá checksum) — poctivě zdokumentováno. |
| Hlavička: magic/signatura/verze/počty | ✅ corrupt na magic/signatura/usknutí (§319–323), **unsupported na verzi ≠ 0** (§326). Absurdní počty → corrupt (§333). Test 2 kryje včetně rozlišení corrupt vs unsupported. |

## 7. Tabulka: podporované vs přeskakované části formátu

### Podporováno (čteno + validováno)

| Část | Rozsah podpory |
|---|---|
| Hlavička (magic, signatura, verze 0, numTypes/numInstances, reserved) | plně |
| Rámečky chunků (jméno, comp/uncomp len, reserved, hranice, END-přesnost) | plně |
| LZ4-block (literály, match-copy, striktní délky/offsety) | plně |
| META (slovník, duplicita = corrupt) | plně |
| SSTR prázdná (`nshared == 0`) | plně |
| INST (třída, `is_service ∈ {0,1}`, referenty, duplicity) | plně |
| PRNT verze 0 (množinová validace, NULL_PARENT, cykly) | plně |
| PROP `Name` (`0x01`) | plně (vč. `missing` evidence) |
| PROP `shape` (`0x12`, enum 0/1/2) | čteno, `trusted=True` |
| PROP `size` (`0x0E`, Vector3 ror1/MSB) | čteno, `trusted=False` (čeká M3 kalibraci) |
| PROP `CFrame`/`CFrame0`/`PivotOffset` (`0x10`, id 0/2 + pozice) | čteno, `trusted=False`; neznámé presety `unread` |
| END + integrita (hash před/po mimo parser) | plně |

### Vědomě přeskakováno (evidováno, ne tiše)

| Část | Jak evidováno | Důvod |
|---|---|---|
| Neznámé chunky (`XXXX`, …) | `skipped_chunks` + `chunk_census` | dopředná kompatibilita; tělo se přesto dekomprimuje |
| Všechny ostatní PROP (booly, inty, floaty jednotlivě, Color3, UDim/UDim2, string mimo Name, reference, …) | `skipped_props[]` s `{type_id, prop_name, value_type, status: "unread", reason}` | M2 čte jen identitu + geometrii; reálná kopie: stovky takových (BoolValue, Color3, UDim2) |
| Neznámé hodnoty `shape` enum (≠ 0/1/2) | `props.shape.status "unread"`, `value None` | žádný odhad tvaru |
| Neznámá orientační id CFrame (7, 32, …) | `rotation None`, `rotation_status "unread-preset-N"` | tabulka preset bez ground-truth |
| Chybějící Name / shape / size / CFrame u relevantních tříd | `status "missing"` + `missing_name_count/unnamed_ids` | nikdy odhad z názvu |

### Odmítnuto (není podpora, je to kontrakt)

| Část | Chyba |
|---|---|
| Verze souboru ≠ 0, neprázdná SSTR, PRNT verze ≠ 0 | `RbxmUnsupportedError` (dobře formované, neumíme) |
| Vše strukturální (hlavička, délky, LZ4, duplicity, špatné počty, data za END) + hierarchie (neplatný parent, cykly) | `RbxmCorruptError` / `RbxmHierarchyError` → BLOCKED |

## 8. Minimální reprodukční fixture (popis, NE kód do testů)

> Požadavek: popisy, které 3. model (nezávislý implementátor) postaví vlastními prostředky; nic se nepřidává do `tests/`.

- **F1 — nesouvislé + nesetříděné referenty:** 2 typy (`Model` ×2 jména, `Part` ×1), referenty např. `[100, 5]` a `[42]`; PRNT kids v jiném pořadí než INST (`[42, 5, 100]`), jeden kořen. Očekáváno: parsovat, `id` = skutečné referenty, `parent_id` správně, výstup řazený. Cíl: vyloučit předpoklad `0..n` a pořadí.
- **F2 — les o dvou kořenech:** 2× `Model` bez rodiče (`parent None` u obou), každý s jedním dítětem. Očekáváno (navrhovaná politika): BLOCKED / explicitní chyba `roots != 1`, ne tichý strom. Cíl: uzavřít mezeru z §3.
- **F3 — self-loop + delší cyklus:** (a) `[(0,0)]` — self-parent; (b) `[(0,1),(1,2),(2,0)]`. Očekáváno: v obou případech hierarchická chyba. Cíl: pokrýt cyklus délky 1, který dnes kryje jen logika, ne test.
- **F4 — neznámá CFrame-preseta vedle známých:** 2× `Part` stejného typu, jeden CFrame id `0` s maticí, druhý id např. `9` bez dat, pozice různé. Očekáváno: soubor projde; u presety `rotation None` + `rotation_status "unread-preset-9"`, pozice čtena; assess BLOCKED. Cíl: ověřit "bez odhadů".
- **F5 — `shape` mimo 0/1/2 + `size` nula/zápor:** `shape` např. `9`, `size` `(0, -1, 2.7)`. Očekáváno: tvar `unread/None`, assess `bad_shape` / `nonpositive_size` + BLOCKED. Cíl: ověřit, že adversarial hodnoty neprojdou jako geometrie.
- **F6 — SSTR neprázdná + PRNT verze 1 (dva soubory):** (a) SSTR s 1 sdíleným řetězcem; (b) PRNT s prvním bajtem `1`. Očekáváno: v obou `RbxmUnsupportedError`, ne corrupt, ne tichý průchod.
- **F7 — pořadí chunků + komprese:** PRNT před INST, PROP před INST, jeden PROP chunk komprimovaný LZ4 s match-copy (ne jen literály). Očekáváno: stejný model jako v kanonickém pořadí. Cíl: vyloučit závislost na pořadí a na "literály-only" LZ4.

## 9. Doporučení pro třetí nezávislý RBXM model

1. **Vybrat model maximálně odlišný od `dc8747e0`:** jiné třídy (Gui/Constraints/Skripty dnes dominují census; nový model ideálně s `MeshPart`, boolean operacemi, `Motor6D`/klouby), neprázdná SSTR pokud možno (ověří `Unsupported` cestu na reálných datech), PRNT s více kořeny nebo hlubokým stromem, CFrame presety mimo `0/2` (ověří `unread` cestu).
2. **Nezávislý implementátor píše vlastní dekodér** (jiný jazyk nebo od nuly, bez kopírování `rbxm_parser.py`), křížová kontrola na: počty typů/instancí, `set(kids)==set(refs)`, kořen(y), jména kol, `shape/size/pozice` čtyř referenčních instancí + hash souboru před/po.
3. **Shoda se vyžaduje na:** (a) identické množině referentů a parent-mapě; (b) identických `shape` u všech Partů; (c) `size/pozice` do tolerance float-přesnosti s dokumentovaným `trusted=False`; (d) identickém seznamu `unread/missing` vlastností. Jakákoli neshoda = BLOCKED + audit, ne "průměrování".
4. **Před M3 (kalibrace) zakázat uvolnění `trusted`:** i při plné shodě 3 modelů zůstává `calibrate_studs_per_meter → NOT_IMPLEMENTED`, dokud není Studio ground-truth (kalibrační díl známé velikosti odečtený ve Studiu). Strukturální důkazy (ortonormalita, symetrie) nejsou prohlášením za ověřené.
5. **Uzavřít mezeru více kořenů (F2):** rozhodnout politiku (doporučeno BLOCKED při `roots != 1` pro M2 dráhu kol) a přidat syntetický test + kontrolu do 3. modelu dřív, než se objeví reálný les.
6. **Doplnit self-loop test (F3a)** do syntetik při nejbližší příležitosti (fáze B, ne tato audit-fáze).

---
*Fáze A audit — bez změn kódu. Soubor vlastněný rolí RBXM Format Compatibility Engineer.*
