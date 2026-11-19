# Fáze D — finální nezávislé QA review stavu M2 (B1+B2+C)

**Větev:** `feat/m1-m2-foundation` (PR #2, OPEN) · **revize:** `0f5b923` + necommitnuté
B1+B2+C (`src/Inspection/rbxm_parser.py`, `src/Inspection/wheel_detect.py`,
`tests/test_m2_rbxm_parser.py`, `tests/test_m2_wheel_detect.py` — `git status`,
883 insertions/43 deletions) · **datum:** 2026-11-19 · **role:** QA final,
bez změn kódu/testů · **metoda:** čtení diffu + vlastní sondy + plný běh sady.

**Sada:** `python tests/run_all.py` → **běhů=260, PASS=256, FAIL=0, ERROR=0,
PENDING=4** (4 totožné pre-existing PENDING: Studio odečet, schema Fáze 5,
2× regresní baseline). M2 podsada: 49 + B1/B2/C přírůstky, vše zelené.

## 1. Dispozice P0/P1 nálezů z fáze A — vše opraveno nebo zdůvodněno

### AUDIT-parser-security (5× P1, 2× P2) — vše OPRAVENO, s regresními testy
| Nález | Stav ve finálním kódu |
|---|---|
| P1-1 `parse_bytes` kopie před kontrolou | OPRAVENO (`len()` před `bytes()`, ř. ~605) + `test_b2_len_before_bytes` |
| P1-2 TOCTOU `getsize`/`read()` | OPRAVENO (`read(MAX_FILE_BYTES+1)` + re-check, ř. ~1035) + `test_b2_parse_rbxm_read_cap` |
| P1-3 LZ4 match-copy po bajtu | OPRAVENO (blokové kopie) + `test_b2_lz4_block_copy_fast_and_exact` |
| P1-4 cap 10M Python objektů | OPRAVENO (`MAX_FIELD_VALUES=100_000` před stavbou seznamů) + `test_b2_field_value_cap` |
| P1-5 kvadratický `ref→type` lookup | OPRAVENO (`ref_to_type` mapa) + `test_b2_ref_to_type_correct` |
| P2-6 `parse_bytes(str/None)` → `TypeError` | OPRAVENO (isinstance brána → `RbxmCorruptError`) + `test_b2_input_type_check` |
| P2-7 chain-walk O(d²) v assess | OPRAVENO (memoizace `chain_memo`) + `test_b2_assess_deep_chain_fast` |

### AUDIT-geometry (3× P0, 3× P1, 2× P2)
| Nález | Stav |
|---|---|
| P0 `+Inf` size → GEOMETRY_OK | OPRAVENO (`nonfinite_size` → UNKNOWN + BLOCKED; ověřeno S1/S2 níže i `test_assess_inf_size_blocked`) |
| P0 `+Inf`/`NaN` pozice → GEOMETRY_OK | OPRAVENO (`nonfinite_position`; `test_assess_inf_nan_position_blocked`) |
| P0 chybějící `isfinite` v geometrické cestě | OPRAVENO (brány size/position/rotation: ř. ~1204/1224/1241/1282) |
| P1 rotační matice bez validace | OPRAVENO (ortonormalita/det: `invalid_rotation`; `test_assess_invalid_rotation_blocked`) |
| P1 presety mimo id 0/2 neověřené | ZDŮVODNĚNO — zůstává `unread-preset-N`, nikdy odhad (`test_assess_unread_rotation_blocked`); plné ověření tabulky presetů mimo M2 |
| P1 shape `unread` enum 16777216 (44 dílů) | ZDŮVODNĚNO — správné fail-closed chování, význam enum mimo M2 |
| P2 magické tolerance / P2 `position` bez typové kontroly | OPRAVENO `position` část (`bad_position`/typová kontrola); tolerance zůstávají nekalibrované = přijatý limit (viz §3, kalibrační brána drží BLOCKED) |

### AUDIT-format-compat — mezera F2 (les) + F3a (self-loop) OPRAVENY
Les o 2 kořenech: parser nyní `RbxmHierarchyError` (`roots != 1`, ř. ~812),
`detect_wheels` i `assess` explicitní `forest` BLOCKED (ř. ~1110, wheel_detect).
Self-loop `[(0,0)]` → `RbxmHierarchyError` (`test_forest_two_roots_rejected`,
`test_self_loop_rejected`, wheel_detect `test_forest_two_roots_blocked` /
`test_self_loop_on_wheel_blocked`). Doporučení F1–F8 pro 3. model trvá;
politika `roots != 1 → BLOCKED` je rozhodnuta a implementována.

### AUDIT-qa-adversarial — P1-1/P1-2 (docs) TRVAJÍ (viz §3 níže); P2-1 OPRAVENO
P2-1 (NaN label): opraveno — `nonfinite_size`, `test_assess_nan_size_label`
assertuje i nepřítomnost `nonpositive_size`. P2-2 (`detect_wheels` cykly
non-Part při přímém volání): částečně — forest politika přidána; přímé volání
mimo parser-cestu zůstává follow-up, neblokuje (parser-cesta cykly chytá vždy).

### AUDIT-test-baseline — mezery F1–F8 OPRAVENY testy
`test_f1_inst_structural`, `test_f2_prnt_structural`, `test_f3_length_fields_edge`,
`test_f4_aggregate_bomb_scaled`, `test_f5_nonfinite_matrix`,
`test_f6_cframe_preset_sweep`, `test_f7_long_cycles`, `test_f8_byte_fuzz_1000`
(1000 trialů, invariantní aserce). Diverzita reálných modelů = přijatý LIMIT
(1 distinctní model, druhý soubor stejný hash `dc8747e0…fedf`).

### Přijaté limity (neměnné, brány drží)
Kalibrace `studs/m` = NOT IMPLEMENTED; floaty `trusted=False`;
BLOCKED na reálné kopii (44 dílů + `float_decode_unverified`) — ověřeno během.

## 2. Vlastní adversarial sondy (7 nových, mimo testy v repu) — vše fail-closed

| # | Sonda | Výsledek |
|---|---|---|
| S1 | size `(inf, 2.7, 2.7)` (parciální inf) | BLOCKED, FL UNKNOWN `nonfinite_size` ✓ |
| S2 | size `(-inf, 2.7, 2.7)` | BLOCKED, FL UNKNOWN `nonfinite_size` ✓ |
| S3 | všechna 4 kola stejný střed (nulová plocha) | BLOCKED (`wheel layout not rectangular` + kalibrační brána); per-kolo GEOMETRY_OK je správně (každé kolo jednotlivě bez vady, zamítá agregát) ✓ |
| S4 | duplicitní `Name` PROP pro typ 0 | `RbxmCorruptError` ✓ |
| S5 | `assess_wheel_geometry([])` | BLOCKED `missing Model:Wheels` ✓ |
| S6 | `rotation` délky 8 (místo 9) | BLOCKED, FL UNKNOWN `bad_rotation` ✓ |
| S7 | `size` jako string `"2.7"` | BLOCKED, FL UNKNOWN `bad_size` ✓ |

Žádná sonda neprošla neplatnou geometrií, žádný crash mimo `RbxmError`,
žádný tichý průchod.

## 3. Shoda dokumentů s realitou — NESHODA (2 soubory zastaralé)

1. **`docs/PROJECT_STATUS.md` zastaralý:** §0 hlásí **205 běhů / 201 PASS**
   (realita **260 / 256**, 0 FAIL, 4 PENDING); §0.2 tvrdí „produkční RBXM
   parser (C05/C06) … NENÍ hotovo", ač větev implementuje C05-C parser
   (30+ testů + B1/B2/C); §0.4 opakuje 205/201. (Shodné s P1-1 z fáze A,
   neopraveno.)
2. **`docs/IMPLEMENTATION_ROADMAP.md` §M2 zastaralý:** „M2.3–M2.10 parser/
   měření/kalibrace NOT IMPLEMENTED", „žádná čtečka neexistuje" (M2.1/M2.8),
   „Stav: NOT IMPLEMENTED". Realita: parser C05-C existuje a je testovaný
   (CODE-VERIFIED); NOT IMPLEMENTED zůstává správně jen pro
   kalibraci/měření (M2.9/M2.10).
3. `reports/RBXM-SPIKE.md` = spike-snapshot, není rozpor (historický vstup).
   Hash `dc8747e0…fedf` před/po shodný (testy čtou `rb`, beze změny).

## 4. Verdikt: MERGE s podmínkami (docs-only)

**Žádný P0/P1 v kódu; sada 260/256/0/0+4 zelená; všech 7 vlastních sond
fail-closed.** merge PR #2 nezastavovat kvůli kódu. Podmínky (před nebo
těsně po mergi, stejná větev nebo follow-up commit):

1. Synchronizovat `docs/PROJECT_STATUS.md` §0/§0.2/§0.4: 260 běhů / 256 PASS,
   přiznat hotový C05-C parser při trvajícím NOT IMPLEMENTED kalibrace/měření.
2. Synchronizovat `docs/IMPLEMENTATION_ROADMAP.md` §M2: parser CODE-VERIFIED,
   NOT IMPLEMENTED jen M2.9/M2.10 + kalibrační brána BLOCKED.
3. Bez kódu: kalibrace zůstává NOT IMPLEMENTED do M3 Studio ground-truth;
   P2-2 (přímé volání `detect_wheels` mimo parser) a preset-tabulka jako
   follow-up, neblokují.

*Vlastněno QA-final. Soubor sond: scratch `qa_probes.py` / `qa_probes2.py`
(nejsou součástí repa).*
