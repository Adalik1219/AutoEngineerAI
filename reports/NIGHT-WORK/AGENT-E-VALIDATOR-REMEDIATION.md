# Agent E — Remediation validátoru normalizace (E1–E6)

**Větev:** `nw-e-validator` · **HEAD před prací:** `57043ee` · **Datum:** 2026-11-20
**Pravidla:** česky; identifikátory anglicky. M3 CLOSED, main/PR#2 tabu.
Katalog/RBXM/src/schémata/validate_contracts/F-mapping NEMĚNĚNY.
Test runner: unittest. Commit této remediation: viz SHA níže
(`git log -1 --format=%H` po commitu; SHA vráceno koordinátorovi).

## 1. Problém

Původní `tools/validate_normalization.py` kontroloval jen čísla
(`source_rows` ukazuje na existující číslo řádku), ne **vztah** záznamu
ke zdroji: nečetl skutečný obsah buňky Interní ID, nerozbaloval skupinové
buňky dle R1–R8, nekontroloval alias≠ID, provenance statusů (VERIFIED bez
evidence procházel), nerozlišoval tři počty (78 řádků / 60 / 94) a neměl
negativní testy. Agregát „60“ se tak tvářil jako ověřitelný, ačkoli seznam
60 ID neexistuje (Varianta B, větev `nw-f-60ids`).

## 2. Změny (pouze 5 souborů)

1. **`tools/validate_normalization.py`** — přepsán (E1–E6, jen stdlib):
   - E1: `logical_id` musí být doslovně v buňce Interní ID každého svého
     `source_rows` řádku (parser `expand_cell_ids`: `a/b`, `f/r/c` přípony,
     `clutch_*`+výčet); cizí řádek / chybějící ID / multi-přiřazení /
     alias-jako-ID / `relationship≠UNRESOLVED` / ID mimo katalog = FAIL
     ve tvaru `FAIL: logical_id=X … zdrojový řádek N … neobsahuje`.
   - E2: R1–R8 jako automatické kontroly (rozbalení úplné vč. R4-výjimek,
     duplicity, `primary_name`+aliases u rozbalených členů, F/R páry,
     pokrytí 78/78, unresolved U1+U3).
   - E3: VERIFIED vyžaduje věcný `mustang_cil`+`zdroj_cile`+`puvod`, jinak
     FAIL; ESTIMATED vyžaduje doložený původ; konkrétní cíl u UNKNOWN/
     PENDING → ruční-review PENDING.
   - E4: `SOURCE_TABLE_ROWS=78` / `ORIGINAL_LOGICAL_IDS=PENDING` /
     `NORMALIZED_IDS=94` + `EXPANDED_SKUPINY/CLENI`, `ALIASY`, `UNRESOLVED`
     — vše vypočteno (žádný počet opsán z meta bez přepočtu; nesoulad
     meta = FAIL).
   - E5: exit 0=PASS / 1=FAIL / 2=PENDING; nedoložená 60 → vždy exit≠0
     (pojistka `ORIGINAL_LOGICAL_IDS=PENDING`, 94 se za 60 nevydává).
   - Oprava: git-blob SHA se počítá s normalizací CRLF→LF (git sémantika
     při `core.autocrlf=true`); jádro `evaluate()` je importovatelné pro testy.
2. **`tests/test_normalization_validation.py`** (nový) — 14 negativních
   případů E6, každý prokazuje FAIL/PENDING (viz §3).
3. **`reports/NIGHT-WORK/normalized_ids.json`** — pouze `meta`:
   `original_60_set` (NOT_RECONSTRUCTABLE, seznam null, důvod Varianta B)
   + `validator` (E1–E6, exit sémantika). **Žádné ID přidáno/odebráno/
   změněno** (94 záznamů, pravidla, unresolved beze změny).
4. **`reports/NIGHT-WORK/AGENT-E-NORMALIZED-CATALOG-AUDIT.md`** —
   aktualizován: vstup Varianta B (§1), oprava rozbalení „34 ID“→28 členů
   (25 ID + 3 nedoložené; dřívější číslo byla koincidence 94−60) (§2),
   nové agregace E4 + výstup validátoru (§4–§5). Verdikt beze změny: PENDING.
5. **Tento soubor** (nový).

## 3. Testy (14 negativních, `python -m unittest tests.test_normalization_validation`)

| # | Případ | Očekáváno | Výsledek |
|---|---|---|---|
| 1 | špatný řádek (`source_rows=[9999]`) | FAIL cizí source_rows, exit 1 | OK |
| 2 | neexistující ID (`vymyslene_id_xyz`) | FAIL neobsahuje+katalog, exit 1 | OK |
| 3 | alias jako ID (`Weight`) | FAIL alias-jako-ID, exit 1 | OK |
| 4 | skupina+nedoložené (`clutch_rpm` jako ID) | FAIL R4, exit 1 | OK |
| 5 | vynechaný člen (`rev_decay` smazán) | FAIL R2, exit 1 | OK |
| 6 | duplicita ID | FAIL R5, exit 1 | OK |
| 7 | konfliktní statusy (záznam přes řádky 52+53) | FAIL R7, exit 1 | OK |
| 8 | VERIFIED bez evidence (`drive_config`) | FAIL E3, exit 1 | OK |
| 9 | F/R sloučení (`downforce` místo páru) | FAIL R2/R8, exit 1 | OK |
| 10 | neexistující reference (blob 40×`0`) | FAIL reference, exit 1 | OK |
| 11 | špatné source_rows (řetězec místo seznamu) | FAIL, exit 1 | OK |
| 12 | 60 bez seznamu (pristine data) | PENDING ORIGINAL_LOGICAL_IDS, exit 2 | OK |
| 13 | metadata-nesoulad (stavy ID +1) | FAIL, exit 1 | OK |
| 14 | neplatný JSON (temp soubor) | ValueError FAIL | OK |

`Ran 14 tests … OK` (exit 0 test runneru = všech 14 prošlo).

## 4. Výsledky (+/−)

- `python tools/validate_normalization.py` → **exit 2 (PENDING)**,
  jediný pending: `ORIGINAL_LOGICAL_IDS=PENDING` (Varianta B).
  Žádný FAIL na čistých datech: E1 94/94 ID sedí na buňky zdroje,
  E3 7/7 VERIFIED s evidencí, R2–R8 beze zbytku.
- `python -m unittest tests.test_normalization_validation` → **14/14 OK**.
- `python tests/run_all.py` → viz §6 (celá sada; nový soubor discovered).
- `python tools/validate_contracts.py` → PASS beze změny (24 kontrol, 0 chyb).

## 5. Agregace před / po (vše strojově)

| Metrika | Před (starý validátor) | Po (E1–E6) |
|---|---|---|
| SOURCE_TABLE_ROWS | 78 | 78 |
| ORIGINAL_LOGICAL_IDS | 60 (opsáno z deklarace) | **PENDING** (NOT_RECONSTRUCTABLE) |
| NORMALIZED_IDS | 94 | 94 |
| EXPANDED_SKUPINY / ČLENI | 9 / „34“ (neověřeno) | **9 / 28** (25 ID + 3×U1) |
| ALIASY celkem | — | 46 |
| UNRESOLVED | 4 | 4 |
| RADKY V/E/P/U | 6/7/20/45 | 6/7/20/45 |
| ID V/E/P/U | 7/8/25/54 | 7/8/25/54 |
| Exit na čistých datech | 2 (PENDING 60) | **2** (PENDING jediný: 60) |

## 6. Nevyřešené (převzato, neměněno)

U1 clutch trio bez katalogového ID · U2 formální vada L55 ·
U3 seznam 60 nedoložen · U4 součty F §1 / E-auditu vs strojový stav.

## 7. Verdikt

**PENDING** (exit 2). Mechanika normalizace je plně doložena (78/78 řádků,
94/94 ID, reference, evidence, R1–R8); jediný pending je nedoložený seznam
60, který validátor explicitně odmítá přepsat na 94. Cesta k PASS: Agent F
dodá seznam 60 katalogových ID → 1:1 přepočet.

## 8. SHA

- HEAD před prací: `57043ee`
- Zdroj F: `reports/NIGHT-WORK/AGENT-F-MUSTANG-PHYSICS-MAPPING.md`
  @blob `4d4d7650ba4ad095815d3b5caaca711b62138c31`
- Vstup F-rekonstrukce: větev `nw-f-60ids`
  (`AGENT-F-60-ID-RECONSTRUCTION.md`, Varianta B)
- Katalog: `src/Chassis/catalog/parameters.json` (138 záznamů, 11 `electric_*`)
- Commit této remediation (5 souborů): viz návratová zpráva
  (`git log -1 --format=%H` na větvi `nw-e-validator`).
