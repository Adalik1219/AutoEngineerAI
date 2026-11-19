# AUDIT — test baseline, fáze A (M2, větev feat/m1-m2-foundation @ 0f5b923)

Datum: 2026-11-19. Produkční kód NEMĚNĚN, testy NEPŘIDÁNY (fáze A).
Příkaz: `python tests/run_all.py` (stdlib unittest, exit 0/1).

## 1. Přesné počty (ověřeno během)

- Celá sada: **běhů=235, PASS=231, FAIL=0, ERROR=0, PENDING=4** → VÝSLEDEK: PASS (s 4 PENDING).
- `tests/test_m2_rbxm_parser.py`: **30 testů, vše OK** (8.5 s).
- `tests/test_m2_wheel_detect.py`: **19 testů, vše OK** (<0.1 s, 10× TestWheelDecisionRule + 9× TestInspectionReportSchema).
- M2 celkem: **49 testů**, vše zelené.

4 PENDING (jména + důvody, doslovně z výstupu):
1. `test_f4_mapping.TestF4Safety.test_studio_mereni_pending_ne_pass` — vyžaduje Roblox Studio (Stiffness/Damping, Initialize).
2. `test_module_contracts.TestReferenceProvenance.test_schema_conformance_pending` — shoda example-vehicle.json se schématem, fáze 5.
3. `test_regression.TestStoredBaseline.test_baseline_exists` — baseline best_variant z fáze 9/10 zatím neexistuje.
4. `test_regression.TestStoredBaseline.test_variant_store_append_only` — VariantStore existuje, regresní napojení neověřeno.

## 2. Mapa krytí 30 parser testů vs požadované oblasti

| Oblast | Kryto čím | Verdikt |
|---|---|---|
| Sparse/nesouvislé referenty | `test_noncontiguous_referents` (mapování referent→instance, žádný předpoklad souvislosti) + `test_adversarial_swapped_lanes_blocked` | ANO |
| Limity souboru (8 MiB) | `test_limits_refused_before_alloc` (soubor nad MAX_FILE_BYTES odmítnut) | ANO, částečně (viz mezery) |
| Agregátní dekomprese (256 MiB total) | `test_limits_refused_before_alloc` (jeden chunk s uncomp_len 300 MiB odmítnut před alokací) + `test_bad_chunk_length` (přestřelená délka 0x7FFFFFFF) | ČÁSTEČNĚ — jen jednochunkový limit, ne kumulativní součet |
| LZ4 | `test_corrupt_lz4` (useknutí/špatný offset) + `_chunk(compress=True)` fixture + `test_fuzz_never_unsafe` | ANO |
| Name (chybějící) | `test_missing_name_is_not_recognized` (name None + missing, assess BLOCKED) | ANO |
| META | `test_meta_duplicate_key` (duplicitní klíč = corrupt) | ANO (základ) |
| PROP (neznámý typ/chunk, validace) | `test_unknown_type_skipped` + `test_inst_validation` (duplicitní INST typ, is_service, PROP pro neznámý typ) | ANO |
| Parent (neplatný) | `test_invalid_parent` + `test_prnt_subset_rejected` (PRNT dítě mimo referenty INST) + `test_missing_wheels_model` | ANO |
| Cykly | `test_cycle` (A↔B = hierarchická chyba) + 4 cyklo-testy ve wheel_detect (ve Wheels, skrz kolo, dlouhý, jinde) | ANO |
| Presety (CFrame/shape) | `test_cframe_unknown_preset_unread` (preset 7: pozice čtena, orientace unread) + `test_adversarial_unknown_shape_unread` + `test_geometry_roundtrip_synthetic` | ANO |
| Hash před/po, read-only | `test_hash_before_after` (dc8747e0… před/po) + `test_second_file_same_model` (JeepTemplate stejný hash = LIMIT, 1 distinctní model) | ANO + evidovaný LIMIT |
| trusted/provenience | `test_geometry_roundtrip_synthetic` (shape trusted=True, size/CFrame trusted=False), E1/E2/E3 assess-testy, `test_calibration_not_implemented` | ANO |
| Fuzz (byte-level) | `test_fuzz_never_unsafe` (seed 20261119, 200 mutací + 5 trunkací, invariant: jen RbxmError nebo platný model se 815 instancemi) | ANO, slabý (viz mezery) |
| Data za END / useknutí | `test_bad_chunk_length` (useknutý soubor, data za END, přestřelená délka) | ANO |
| Header/verze | `test_corrupt_header` (magic/signatura corrupt vs verze unsupported) + `test_prnt_version_unsupported`, `test_sstr_shared_unsupported` | ANO |

Krytí 19 detection testů: pravidlo (a)+(b)+(c) konjunkce (`test_classify_conjunction_all_three_required`), Ball mimo Wheels nikdy kolo, špatné jméno/tvar → UNKNOWN se záznamem, chybějící/duplicitní Wheels, 3 kola, duplicita designace, libovolné UNKNOWN blokuje analýzu, determinismus, schéma reportu, 4 cyklo-případy + offchain cyklus neblokuje, chybějící parent_id, duplicitní instance_id. **Plné krytí rozhodovacího pravidla na syntetických fixturech — ANO.**

## 3. Mezery (co chybí, fáze C kandidáti)

1. **NaN/Inf floaty** — žádný test nekrmí size/CFrame NaN/±Inf. Parser značí floaty trusted=False, ale není ověřeno, že NaN/Inf → `unread` + assess BLOCKED místo propagace do `position`/`size`/středů.
2. **Agregátní dekompresní bomba v limitech** — chybí test mnoha jednotlivě legálních chunků, jejichž součet přesáhne MAX_TOTAL_UNCOMPRESSED (256 MiB). Současný test umí jen jeden obří chunk.
3. **Strukturální mutace (INST/PRNT surgery)** — fuzz je jen byte-level (1–3 náhodné byty, seed 20261119). Chybí cílené mutace: prohozené lane, useknutý referent-seznam, PRNT na neexistující referent, délková pole −1/+1, prázdný INST s nenulovým počtem.
4. **Délková pole na hraně** — `uncomp_len`/`comp_len` = 0, přesně na limitu, a `count` vs skutečný payload (PROP/META počet vs tělo).
5. **Diverzita reálných modelů** — oba RBXM soubory mají stejný hash (1 distinctní model); třetí různý model v repu neexistuje. Evidovaný LIMIT, řeší se Studiem.
6. **Wheel-detect na reálném parser-výstupu mimo happy-path** — integrační test `test_four_wheels_honest_partial` kryje jen BLOCKED-cestu s 44 díly ve Wheels; chybí syntetický strom s realistickým parent-řetězcem z parseru (id/names/shape z reálné kopie + odebrané Wheels).

## 4. Ověření PENDING historie (požadavek: existovaly před commitem)

- `git diff 230cb29..HEAD -- tests/` mění **pouze** `tests/test_m2_rbxm_parser.py` (+522/−41). Žádný ze 4 PENDING testů v tomto diffu není.
- Všechny `skipTest` výskyty v `test_f4_mapping.py`, `test_module_contracts.py`, `test_regression.py` jsou **identické na HEAD i na parentu 230cb29** (ověřeno `git show 230cb29:<soubor> | grep skipTest` — shoda 1:1).
- `test_m2_rbxm_parser.py` ani `test_m2_wheel_detect.py` neobsahují žádný `skipTest` (grep = 0) — M2 sada nemá vlastní PENDING.
- Závěr: **4 PENDING existovaly před commitem 0f5b923; commit nepřidal ani neodebral žádný PENDING.** (Většina `skipTest` větví v module_contracts se neaktivuje, protože moduly existují — proto jen 4 skipy z ~17 `skipTest` míst.)

## 5. Fuzz plán (fáze C; každý budoucí test ověřuje INVARIANT, ne jen „nespadl")

Seed strategie: pevný seed `20261119`, mutační + trunkční počty hlášeny v názvu/docstringu testu (pokračování stávajícího `FUZZ_SEED`/`FUZZ_MUT_TRIALS` vzoru). Korpus: `mini_tree()` builder + reálná kopie (read-only, hash kontrola).

| # | Mutace | Invariant (assert) |
|---|---|---|
| F1 | Strukturální INST: useknutý referent-seznam, count≠payload, duplicitní referent | `RbxmCorruptError`, nebo model kde `len(instances) == num_instances` a každý parent ∈ id-množině |
| F2 | Strukturální PRNT: dítě mimo referenty, parent na neexistující id, verze ≠ 0 | `RbxmError` (corrupt / unsupported dle případu), nikdy tichý model s visícím parentem |
| F3 | Délková pole: `uncomp_len`/`comp_len` ∈ {0, limit−1, limit, limit+1}, chunk-rámec ±1 B | odmítnutí před alokací (`RbxmError`), žádná alokace ≥ limit |
| F4 | Kompresní bomba v limitech: N chunků × legální velikost, součet > 256 MiB | `RbxmCorruptError` na agregátní limit, alokace nikdy nepřesáhne limit |
| F5 | Floaty: NaN/±Inf v size/CFrame pozici/matici, neznámá shape-hodnota | vlastnost `status=unread`, `trusted=False`, `assess_wheel_geometry → BLOCKED` (nikdy NaN v `position`/`size`) |
| F6 | CFrame presety: všechny id 0–8 + neznámé (7, 9, 255) | id 0/2 → `rotation_status=matrix`, ostatní → `unread-preset-N`, pozice vždy čtena |
| F7 | Cykly délky 2/3/N skrz Wheels i mimo | cyklus na cestě kola/Wheels → BLOCKED; offchain cyklus → neblokuje (symetricky k existujícím testům) |
| F8 | Byte-fuzz reálné kopie (rozšíření F13): 1000 trialů, stejný seed-rodina | stejný invariant jako dnes + navíc `shape ∈ známá množina` a `num_instances == 815` při akceptaci |

Pravidlo pro fázi C: každý test končí asercí invariantu z pravého sloupce; holé „prošlo bez výjimky" je zakázáno.
