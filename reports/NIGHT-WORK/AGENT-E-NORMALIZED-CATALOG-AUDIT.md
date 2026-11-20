# Agent E — normalizovaný katalogový audit (60 ID / 78 řádků)

**Větev:** `nw-e-validator` · **HEAD před prací:** `57043ee` (strom čistý) · **Datum:** 2026-11-20
**Pravidla:** česky; identifikátory anglicky. M3 CLOSED, main/PR#2 tabu.
Produkční katalog/RBXM/schémata/`tools/validate_contracts.py`/CI NEMĚNĚNY.
Tato remediation zapsala pouze: tento report,
`reports/NIGHT-WORK/normalized_ids.json` (jen `meta`, žádná umělá ID),
`tools/validate_normalization.py` (zesílen E1–E6),
`tests/test_normalization_validation.py` (nový, 14 negativních případů),
`reports/NIGHT-WORK/AGENT-E-VALIDATOR-REMEDIATION.md` (nový).

## 1. Zdroj 60 ID a 78 řádků (soubor + SHA)

- **Soubor:** `reports/NIGHT-WORK/AGENT-F-MUSTANG-PHYSICS-MAPPING.md`
  (Agent F — Mapování fyziky Mustang GT 2024 EU)
- **Blob SHA:** `4d4d7650ba4ad095815d3b5caaca711b62138c31`
  (ověřeno `git rev-parse HEAD:<cesta>` i `git hash-object`;
  validátor normalizuje CRLF→LF dle git-blob sémantiky při
  `core.autocrlf=true`)
- **Commit souboru:** `0f7c968` (poslední změna; HEAD této práce `57043ee`)
- **Původní deklarace v souboru (§1):** 60 mapovaných parametrů (výběr ze 138
  záznamů katalogu); stavový rozpad 7/3/21/28
  (VERIFIED/ESTIMATED/PENDING/UNKNOWN); 78 řádků tabulek §2.1–§2.10.
- **Doplňkové vstupy (čteny, neměněny):**
  `reports/NIGHT-WORK/AGENT-E-MUSTANG-DATA-AUDIT.md`,
  `src/Chassis/catalog/parameters.json` (138 záznamů, z toho 11 `electric_*`),
  `vehicle-data/references/ford-mustang-gt-2024-eu-manual-standard.json`,
  `docs/VEHICLE-SPECIFICATIONS.md`,
  `reports/NIGHT-WORK/AGENT-F-60-ID-RECONSTRUCTION.md`
  (větev `nw-f-60ids` — čtena přes `git show`, neměněna).

### Co je / není doloženo

- **78 řádků DOLOŽENO:** strojový počet tabulek §2.1–§2.10 = **78** (deklarace sedí).
- **60 ID NEDOLOŽENO — Varianta B potvrzena:**
  `ORIGINAL_60_SET=NOT_RECONSTRUCTABLE`.
  Seznam 60 logických ID není uveden v žádném commitu/souboru.
  Číslo 60 vzniklo v `557ee39` (`AGENT-F-MUSTANG-PHYSICS-MAPPING.md`
  řádky 34–40, blob `b5f95b19…`) jako textová deklarace bez seznamu;
  `138−78=60` i `94−34=60` jsou koincidence (míchají jednotky);
  elektro-větev je v katalogu 11×, ne 9×. F-rekonstrukce vztah každé
  doložené položky k „original_60“ vede jako `UNRESOLVED` — stejně činí
  tento validátor: `relationship ≠ UNRESOLVED` je FAIL.
  Žádná umělá ID nebyla vytvořena.

## 2. Pravidla normalizace (z `normalized_ids.json`, klíč `rules`)

- **R1** Stejné ID = stejný řetězec v buňce Interní ID. Jeden řádek = jeden
  zdrojový záznam; skupinová buňka se rozbalí, neruší.
- **R2** Skupinová buňka (`a / b`, `a + b`, `f/r/c`, `clutch_*`) se rozbaluje na
  jednotlivá katalogová ID; každé dědí stav řádku s poznámkou. Neslučuje se.
- **R3** Alias ≠ parametr: sloupec Název (Tune klíč) a `tune_key` z katalogu jsou
  `aliases`; samostatné ID jen pro Interní ID / jeho doložené členy.
- **R4** Chybějící ID: podnázev bez katalogového ID (`clutch` rpm/speed/stall)
  nedostane žádné ID (žádná umělá ID); veden v `unresolved` (U1).
- **R5** Duplicity: stejné `logical_id` ve více řádcích = jeden záznam s více
  `source_rows`. Ověřeno: žádné (94/94 unikátních).
- **R6** Konfliktní názvy: `primary_name` je Název z řádku; při rozbalení je
  `primary_name` = ID a původní Název je alias. Názvy se nepřepisují.
- **R7** Jeden primární stav na ID = sloupec Stav řádku (stav mapování /
  připravenosti, **ne** čistý stav mustangovského cíle — viz N-F1: např.
  `drive_config` VERIFIED vs `differential_type` UNKNOWN). Cíl je evidován
  zvlášť v `evidence` (mustang_cil / zdroj_cile / puvod).
- **R8** F/R a L/R páry jsou odlišné parametry (odlišné Tune klíče) —
  neslučují se podle podobnosti.

Rozbalené skupinové buňky (9 řádků → **28 členů**: `rev_accel/decay/bounce` (3),
`throttle_accel/decel` (2), `turbo_count/boost` (2), `shift_up/down_time` (2),
`clutch_*` → 6 členů, z toho katalogově doložené 3
(`enabled/engage/kick`), `front_diff_power/coast` (2), `slip+lock` (6),
`downforce_f/r` (2), `wear/lock/spin` trio (3) — tj. **25 ID + 3 nedoložené**
(U1). Oprava: dřívější audit uváděl „→ 34 ID“ (převzato z koincidence
94−60); strojově je členů 28. Pseudo-ID (`wheelbase_etc`, `wheel_radius`,
`camber_caster_toe`) ponechána nerozbalená (R4 — katalog je zná pod těmito ID;
všech 94 ID je v katalogu).

## 3. Normalizovaná data (tabulka / odkaz)

Plný seznam: `reports/NIGHT-WORK/normalized_ids.json` (klíč `ids`, 94 záznamů;
pole `logical_id/source_rows/primary_name/aliases/source_reference/status/evidence/notes`).
Každý záznam nese `source_reference` ve tvaru
`…MUSTANG-PHYSICS-MAPPING.md@blob:4d4d7650…#L<řádka>`
(soubor + skutečný blob + řádek). Vztah k nedoložené množině 60 je
implicitně `UNRESOLVED` (množina není definována; explicitní jiné
`relationship` validátor odmítá). Změna JSON v této remediation: pouze klíče
`meta.original_60_set` (NOT_RECONSTRUCTABLE, seznam null) a `meta.validator`
(E1–E6); **žádné ID přidáno/odebráno/změněno**.

## 4. Agregace (reprodukovatelná, z validátoru — vše vypočteno, nic opsáno)

- **SOURCE_TABLE_ROWS = 78** (strojově z tabulek §2.1–§2.10).
- **ORIGINAL_LOGICAL_IDS = PENDING** (`ORIGINAL_60_SET=NOT_RECONSTRUCTABLE`,
  seznam nedoložen — validátor MUSÍ vrátit PENDING, nesmí přepsat na 94).
- **NORMALIZED_IDS = 94** (strojově z `ids`).
- **EXPANDED:** 9 skupinových řádků → 28 členů (25 ID + 3 nedoložené U1).
- **ALIASES:** 46 řetězců celkem (strojově sečteno).
- **UNRESOLVED:** 4 (U1–U4).
- **Řádky F §2 (78):** VERIFIED **6** · ESTIMATED **7** · PENDING **20** · UNKNOWN **45**.
- **ID po normalizaci (94):** VERIFIED **7** · ESTIMATED **8** · PENDING **25** · UNKNOWN **54**.

Pozn.: součet PENDING/UNKNOWN řádků (20/45) se liší o 1 od F §1 (21/28-sloupec)
i od přepočtu E auditu (21/44): `compression_ratio` (L135) je v tabulce UNKNOWN,
součty 21/… nebyly po překlasifikaci aktualizovány. Detail v U4.

## 5. Validační výstup (`tools/validate_normalization.py`, exit 2)

```
KONTROLY E1–E4 (zdroj: reports/NIGHT-WORK/AGENT-F-MUSTANG-PHYSICS-MAPPING.md, blob 4d4d7650ba4a):
  [PENDING] PENDING: ORIGINAL_LOGICAL_IDS=PENDING — ORIGINAL_60_SET=NOT_RECONSTRUCTABLE — seznam 60 ID neexistuje v žádném commitu/souboru (Varianta B); 94 normalizovaných ID se za 60 nevydává

AGREGACE (E4, vše vypočteno):
  SOURCE_TABLE_ROWS=78 ORIGINAL_LOGICAL_IDS=PENDING NORMALIZED_IDS=94
  EXPANDED_SKUPINY=9 EXPANDED_CLENI=28 ALIASY=46 UNRESOLVED=4
  RADKY: 78 {'ESTIMATED': 7, 'UNKNOWN': 45, 'PENDING': 20, 'VERIFIED': 6}
  ID: 94 {'UNKNOWN': 54, 'PENDING': 25, 'ESTIMATED': 8, 'VERIFIED': 7}
  NEPOKRYTE_RADKY=0 DUPLICITY=0
VERDIKT_DAT=PENDING: ORIGINAL_LOGICAL_IDS=PENDING — …
```

E1 (vztah záznam→zdroj): každé `logical_id` je doslovně v buňce Interní ID
svého `source_rows` řádku (rozbalení dle R2 strojově), žádné ID k cizímu
řádku, žádný odkaz na neexistující řádek, žádná multi-přiřazení, aliasy
nejsou ID, všechna ID jsou v katalogu. E3: všech 7 VERIFIED má věcnou
evidenci; všech 8 ESTIMATED má doložený původ. E5: exit 2 = PENDING
(mechanika sedí, 60 nedoloženo); exit 0 by vyžadoval doložený seznam 60.

## 6. Nevyřešené (z `unresolved`)

- **U1** `clutch_rpm / clutch_speed / clutch_stall` — bez katalogového ID
  (katalog zná jen `clutch_enabled/engage/kick`). Stav UNKNOWN, žádná umělá ID.
- **U2** `weight_box_size` (L55) má 10 sloupců místo 11 (chybí oddělovač
  Ověření/Riziko). Stav PENDING jednoznačný; formální vada.
- **U3** Seznam 60 ID nedoložen (viz §1, Varianta B). Stav UNKNOWN.
- **U4** Součty 7/3/21/28 (F §1) ani 6/7/21/44 (E audit) neodpovídají strojovému
  stavu tabulky 6/7/20/45. Stav PENDING (čeká na opravu součtů u vlastníků).

## 7. Závěr — lze-li rozpor uzavřít

Rozpor **nelze uzavřít** na PASS: každá doložená řádka (78/78) je mapována a
agregace jsou reprodukovatelné, ale deklarace „60 ID“ nemá doložený seznam a
její stavový rozpad nesedí se strojovým počtem. Verdikt: **PENDING** (poctivý —
zdroje nestačí; nic nepodloženo). Cesta k PASS: Agent F zveřejní explicitní
seznam 60 katalogových ID (výběr ze 138) s jedním stavem na ID; pak se tento
audit přepočítá 1:1. FAIL se nekoná — žádné ID ani stav nebyly vymyšleny.

## Doložka 2026-11-20 — navazující vlna (nepřepisovat výše uvedené)
F-rekonstrukce rozhodla Variantu B: `ORIGINAL_60_SET=NOT_RECONSTRUCTABLE` (AGENT-F-60-ID-RECONSTRUCTION). Validátor zesílen E1–E6 + 14 negativních testů (AGENT-E-VALIDATOR-REMEDIATION, `tests/test_normalization_validation.py` 14/14, exit kódy 0/1/2). Tři počty odděleny: SOURCE_TABLE_ROWS=78 / ORIGINAL_LOGICAL_IDS=PENDING / NORMALIZED_IDS=94. Aktualizováno: `normalized_ids.json` (jen meta), `tools/validate_normalization.py`.
