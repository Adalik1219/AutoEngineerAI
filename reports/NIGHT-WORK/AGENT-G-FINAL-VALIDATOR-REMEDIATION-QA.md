# Agent G — finální nezávislá QA remediace validátoru (Fáze 13)
Vlastník: Agent G (nezávisle; tvrzení E/C nepřevzata) · Datum: 2026-11-20 · Větev: fix/normalization-evidence-integrity
Přesný SHA: `6332a2df3c81e84cdac2a3e9835d9d03ff0e63c9` · `git status` čistý · Testovací prostředí: Win 11, Python 3.14 (stdlib only)

## 12/12 kontrolních oblastí (vše exists v kódu, 737 řádků)
1. E1 zdrojová vazba: ř.354–373 (`type(x) is not int`, duplicitní/cizí `source_rows`, ID∉buňka) + ř.459–488 (duplicity, E1-neúplná-vazba, E1-ID-bez-opory).
2. E2 pravidla R1–R8: ř.457–643. R1 pokrytí ř.634–643; R2 rozbal ř.86–120 + členy ř.489–498; R3 alias≠ID ř.375–377, 554–604; R4 unresolved U1+U3 ř.499–512; R5 duplicity ř.459–463 (Counter); R6 primary/aliasy ř.513–553; R7 `status==row_stav` ř.389–442; R8 `FR_PAIRS` 12 párů ř.134–147 + `LR_PAIRS=[]` ř.150, kontroly ř.605–632, bez univerzálního suffix-pravidla.
3. E3 evidence: `je_hodnota` ř.158, `ma_lokator` ř.174, `je_slaby_puvod` ř.186; VERIFIED-brána ř.404–412; ESTIMATED-brány ř.413–424.
4. E4 agregace vypočtena ř.645–659 (78/94/9/28/46/4; stavy řádků 6/7/20/45; stavy ID 7/8/25/54).
5. E5 exit kódy 0/1/2 ř.721–728 zachovány.
6. Negativní testy: 51/51 OK (`python -m unittest tests.test_normalization_validation`).
7. Historická 60: strict (jakýkoli neprázdný seznam → FAIL + trvalý PENDING), NOT_RECONSTRUCTABLE.
8. Rozsah 94: `ACCEPTED_MAPPED_SET` UNAPPROVED→PENDING; APPROVED větev ověřuje seznam+sha+rozhodnutí+datum.
9. Katalog: čten s `with` (ř.687–697), neměněn (diff prázdný).
10. RBXM / `src/` / `main` / PR #2: `git diff 72c16c2..HEAD -- src/ contracts/proposed/` prázdný; RBXM diff prázdný.
11. `normalized_ids.json` (ids/meta): `git diff 72c16c2..HEAD` prázdný — data nedotčena.
12. Dokumentace: docstring E1–E6 + 10 reportů vlny; rozpor V1–V3 v closeoutu opraven dodatkem (historie zachována).

## Běhy na přesném SHA
- `tools/validate_normalization.py` → exit 2, fails=[] (prázdné), 6 pendings.
- `tests.test_normalization_validation` → 51/51 OK.
- `tools/validate_contracts.py` → 24/24, 0 chyb.

## 8 vlastních mutací (deepcopy v paměti, soubory nedotčeny) — vše FAIL se správným klíčem, revert čistý
M1 prohozený status → `status-neodpovídá-zdroji`; M2 seznam 60 z 94 → `ORIGINAL_LOGICAL_IDS`; M3 falešný alias → `R6-cizí-alias`; M4 primary_name → `R6-název-nesouhlasí`; M5 VERIFIED `xxx/-/-` → `VERIFIED-bez-evidence`; M6 chybí `damper_r` → `F/R pár sloučen/chybí`; M7 `anchor_offset_l` → `neexistující ID`; M8 odběr ID po APPROVED → `ACCEPTED_MAPPED_SET`.

## PENDING (6)
ORIGINAL_60 NOT_RECONSTRUCTABLE; ACCEPTED_MAPPED_SET UNAPPROVED; 4× ESTIMATED-k-revizi (`diff_preload_f`, `front_diff_coast`, `front_diff_power`, `torque_vector`).

## Nové chyby: ŽÁDNÉ. Porovnání s baseline: 14→51 testů, exit 2 zachován, 0 FAIL v celé sadě.

## Verdikt: CONDITIONAL
Validátor je fail-těsný (8/8 mutací + 51/51). Plný PASS blokují: nedoložitelná historická 60 (by design), schválení 94 uživatelem, 4× ruční revize ESTIMATED. Neschvaluji nic, co jsem implementoval (implementace: Agent E).
