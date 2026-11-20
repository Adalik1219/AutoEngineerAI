# VALIDATOR-REMEDIATION-BASELINE (Fáze 0)
Vlastník: Hermes · Datum: 2026-11-20 · Větev: fix/normalization-evidence-integrity

## 1. Výchozí HEAD
- `72c16c278f2d7555fe17afd8354e744a6d04d8c1`
- Odpovídá očekávanému HEAD ze zadání. `git status --short` čistý, `git diff --stat` prázdný.
- `git checkout -b fix/normalization-evidence-integrity` proveden z tohoto HEAD (stejné SHA, viz `git log --graph -8`).

## 2. Kódový SHA
- `405db4b53998c332dc193c8bae753ad841efbc67` (merge nw-g-qa, ověřen `git rev-parse`).

## 3. Výchozí CI run
- `44767371214`, success, 4/4 joby (zdroj: NEXT-WAVE-FINAL-CLOSEOUT.md ř.5).
- CI běžel na přesném kódovém SHA 405db4b.

## 4. Stav pracovního stromu
- Před větví: čistý. Po založení větve: beze změn (HEAD shodný s feat/m2-m3-geometry).

## 5. SHA souborů k úpravě (git hash-object, pracovní strom)
- `tools/validate_normalization.py`: `c62a20dbc952727fcdb27f56bf32507965a6dea2`
- `tests/test_normalization_validation.py`: `02c350a1a86fee92d5c91ec86bbe2f345a8cdf37`
- `reports/NIGHT-WORK/AGENT-E-NORMALIZED-CATALOG-AUDIT.md`: `bfacf847f006822aad5a63f280d07ec88ab19da9`
- `reports/NIGHT-WORK/normalized_ids.json`: `fd2578c7812eaa2699fac26af5634716a9b932f8`
- Autoritativní pravidla R1–R8: AGENT-E-NORMALIZED-CATALOG-AUDIT.md ř.48–64; normalized_ids.json `meta.rules` ř.51–58.

## 6. Chráněné soubory (beze změny v této vlně)
- `src/` (produkce), `src/Chassis/catalog/parameters.json`, `testgame/src/ServerStorage/VehicleTemplates/JeepTemplate.rbxm`, `main`, PR #2, `contracts/proposed/` (4 schémata), S-02, M3, fyzikální model, zdroj Agent F bez svolení vlastníka.

## 7. Výchozí výsledky testů (lokálně, 2026-11-20)
- `python -m unittest tests.test_normalization_validation`: 14 testů, OK. Vedlejší nález: `ResourceWarning: unclosed file ... AGENT-F-MUSTANG-PHYSICS-MAPPING.md` — `tools/validate_normalization.py:70` používá `open(...)` bez `with` (N-2 je reálný, ne vyřešený; `load_doc` ř.128–138 `with` používá).
- `python tests/run_all.py`: běhů 458, PASS 454, FAIL 0, ERROR 0, PENDING 4.
- `python tools/validate_contracts.py`: 24 kontrol, 0 chyb — ÚSPĚCH.

## 8. Aktuální výstup validátoru
```
KONTROLY E1–E4 (zdroj: reports/NIGHT-WORK/AGENT-F-MUSTANG-PHYSICS-MAPPING.md, blob 4d4d7650ba4a):
  [PENDING] PENDING: ORIGINAL_LOGICAL_IDS=PENDING — ORIGINAL_60_SET=NOT_RECONSTRUCTABLE — seznam 60 ID neexistuje v žádném commitu/souboru (Varianta B); 94 normalizovaných ID se za 60 nevydává
AGREGACE (E4, vše vypočteno):
  SOURCE_TABLE_ROWS=78 ORIGINAL_LOGICAL_IDS=PENDING NORMALIZED_IDS=94
  EXPANDED_SKUPINY=9 EXPANDED_CLENI=28 ALIASY=46 UNRESOLVED=4
  RADKY: 78 {'ESTIMATED': 7, 'UNKNOWN': 45, 'PENDING': 20, 'VERIFIED': 6}
  ID: 94 {'UNKNOWN': 54, 'PENDING': 25, 'ESTIMATED': 8, 'VERIFIED': 7}
  NEPOKRYTE_RADKY=0 DUPLICITY=0
VERDIKT_DAT=PENDING: ORIGINAL_LOGICAL_IDS=PENDING — ORIGINAL_60_SET=NOT_RECONSTRUCTABLE — seznam 60 ID neexistuje v žádném commitu/souboru (Varianta B); 94 normalizovaných ID se za 60 nevydává
```

## 9. Exit kód validátoru
- `2` (PENDING — historická množina 60 nedoložena). Správně ≠ 0.

## 10. PENDING (5 dle closeoutu; lokálně 4 + 1 CI-specifické)
1. `test_studio_mereni_pending_ne_pass` — vyžaduje Roblox Studio (StAxisOffset §17.1).
2. `test_schema_conformance_pending` — shoda example-vehicle.json vs reference_profile.schema.json (Fáze 5).
3. `test_baseline_exists` — baseline best_variant Fáze 9/10 neexistuje.
4. `test_variant_store_append_only` — VariantStore bez regresního napojení.
5. `2nd-copy` — pouze CI (1 kopie RBXM vs 2 lokálně); zdroj NEXT-WAVE-FINAL-CLOSEOUT.md ř.24. SKIP: 2 pre-existing (Studio).

## Závěr fáze 0
Baseline ověřen na přesném SHA, strom čistý, izolovaná větev založena. Známé mezery validátoru (R7 status-dědění, R8 L/R, R3/R6 aliasy u 1-řádkových záznamů, E3 `je_dukaze()` přijme libovolný neprázdný text, E1 `bool`⊂`int` + chybějící úplnost vazby) jdou do fází 1–10. N-2 `open()` ř.70 potvrzen jako otevřený.
