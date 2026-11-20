# Agent E — finální remediace validátoru (Fáze 3–10)
Vlastník: Agent E · Datum: 2026-11-20 · Větev: fix/normalization-evidence-integrity
Výchozí SHA: 72c16c278f2d7555fe17afd8354e744a6d04d8c1 · Kódový SHA: 405db4b53998c332dc193c8bae753ad841efbc67

## Změněné soubory (jiné soubory nedotčeny; chráněné oblasti beze změny)
- `tools/validate_normalization.py` (+339/−49 řádků s testy; viz diff):
  - N-2: `open()` → `with` na 3 místech (`parse_f_rows`, `run` fbytes, `run` katalog). `load_doc` už `with` měl.
  - E1: `type(x) is not int` (odmítá `True`/`False`); `duplicitní source_rows`; úplnost vazby `E1-neúplná-vazba` / `E1-ID-bez-opory` pro všech 78 řádků.
  - R7: `status-neodpovídá-zdroji` — per-záznam rovnost `status == row_stav` (prohození dvou statusů při stejných součtech selže).
  - R8: `FR_PAIRS` (12 doložených) + `LR_PAIRS` (prázdná, větev připravena); konec univerzálního suffix-pravidla; kontrola sloučeného kmene + shodného `tune_key`.
  - R3/R6: `R6-název-nesouhlasí` (běžné záznamy), `R6-cizí-alias`, `alias-je-ID`, `duplicitní-alias`; `rec_by_id` místo lineárního `next()`; `Counter` místo `id_list.count()`.
  - E3: `je_hodnota` + `ma_lokator` + `je_slaby_puvod`; VERIFIED vyžaduje hodnotu+lokátor+původ; ESTIMATED nové `ESTIMATED-bez-zdroje` a `ESTIMATED-k-revizi` (PENDING); exit kódy 0/1/2 zachovány.
  - 60/94: libovolný neprázdný `original_60_set.seznam` → FAIL+P umbrella PENDING (výběr 60 z 94 se nepřijímá); nové `ACCEPTED_MAPPED_SET` (default UNAPPROVED → PENDING; APPROVED větev ověřuje seznam+sha_data+rozhodnutí+datum).
- `tests/test_normalization_validation.py`: 14 → **51 testů** (E1 6, R7 4, R8 5, R3/R6 8, E3 8, 60/94 6 nových; `catalog_tune` mapa v `evaluate`).
- `normalized_ids.json`: **neměněn** (žádné ID přidáno/odebráno/změněno, žádné stavy měněny).

## Výsledky (lokálně, 2026-11-20)
- `python tools/validate_normalization.py` → exit **2**, fails `[]`, pendings: ORIGINAL_60 (NOT_RECONSTRUCTABLE) + ACCEPTED_MAPPED_SET (UNAPPROVED) + 4× ESTIMATED-k-revizi (`diff_preload_f`, `front_diff_coast`, `front_diff_power`, `torque_vector`).
- `python -m unittest tests.test_normalization_validation` → **51/51 OK**.
- `python tests/run_all.py` → 495 běhů, 491 PASS, 0 FAIL, 0 ERROR, 4 PENDING (stejné 4 jako baseline).
- `python tools/validate_contracts.py` → 24/24 OK.

## Vědomé odchylky (zdůvodněné)
1. Holé `odhad` u ESTIMATED s nekonkrétním cílem → PENDING-k-revizi, ne FAIL (4 reálné záznamy; FAIL by zlomil pristine strom; flag je jmenovitý, ne tichý PASS).
2. `alias=placeholder —` se nepočítá jako duplicitní kolize (sdílený Název-placeholder 5 záznamů); původ-alias kontrola zůstává.
3. `tune_key ∈ aliases` se pozitivně nevynucuje (reálná data mají u běžných záznamů `aliases=[]`); vynucuje se negativně (cizí tune_key / cizí ID → FAIL).

## Otevřené body
- `ACCEPTED_MAPPED_SET` čeká na rozhodnutí uživatele (UNAPPROVED).
- 4× ESTIMATED-k-revizi čeká na ruční review.
- `main`, PR #2, `src/`, katalog, RBXM, `contracts/proposed`, S-02, M3: nedotčeny.
