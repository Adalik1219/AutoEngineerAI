# Agent E — normalizovaný katalogový audit (60 ID / 78 řádků)

**Větev:** `wave-e-norm` · **HEAD:** `0f4670a` (strom čistý před prací) · **Datum:** 2026-11-20
**Pravidla:** česky; identifikátory anglicky. M3 CLOSED, main/PR#2 tabu.
Produkční katalog/RBXM/schémata/`tools/validate_contracts.py`/CI NEMĚNĚNY.
Zapsány pouze 3 soubory: tento report, `reports/NIGHT-WORK/normalized_ids.json`,
`tools/validate_normalization.py` (nový, jen stdlib).

## 1. Zdroj 60 ID a 78 řádků (soubor + SHA)

- **Soubor:** `reports/NIGHT-WORK/AGENT-F-MUSTANG-PHYSICS-MAPPING.md`
  (Agent F — Mapování fyziky Mustang GT 2024 EU)
- **Blob SHA:** `4d4d7650ba4ad095815d3b5caaca711b62138c31`
- **Commit souboru:** `0f7c968` (poslední změna; HEAD worktree `0f4670a`)
- **Původní deklarace v souboru (§1):** 60 mapovaných parametrů (výběr ze 138
  záznamů katalogu); stavový rozpad 7/3/21/28
  (VERIFIED/ESTIMATED/PENDING/UNKNOWN); 78 řádků tabulek §2.1–§2.10.
- **Doplňkové vstupy (čteny, neměněny):**
  `reports/NIGHT-WORK/AGENT-E-MUSTANG-DATA-AUDIT.md`
  (blob `c99af17d33ff3da501f64162515a42140a1f8e2e`),
  `src/Chassis/catalog/parameters.json` (blob `8f4d6bd1edcffd9121d0c6bad87fbd97b5285d0b`, 138 záznamů),
  `vehicle-data/references/ford-mustang-gt-2024-eu-manual-standard.json`
  (blob `68832c3462fecbcb5fe5c27759574a0399e0e6a7`),
  `docs/VEHICLE-SPECIFICATIONS.md`.

### Co je / není doloženo

- **78 řádků DOLOŽENO:** strojový počet tabulek §2.1–§2.10 = **78** (deklarace sedí).
- **60 ID NEDOLOŽENO:** seznam 60 logických ID není uveden v žádném souboru.
  F §1 deklaruje jen agregát; výběr 60 ze 138 katalogu je v §4 popsán neúplně
  („elektro-větev 9×" vs skutečných 11 `electric_*`; 138−60=78 vyloučených,
  §4 jmenuje jen ~21). Agregát 60 ani rozpad 7/3/21/28 proto **nelze reprodukovat**
  — viz U3. Žádná umělá ID nebyla vytvořena.

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

Rozbalené skupinové buňky (9 řádků → 34 ID): `rev_accel/decay/bounce` (3),
`throttle_accel/decel` (2), `turbo_count/boost` (2), `shift_up/down_time` (2),
`clutch_*` → jen katalogově doložené 3 (`enabled/engage/kick`),
`front_diff_power/coast` (2), `slip+lock` (6), `downforce_f/r` (2),
`wear/lock/spin` trio (3). Pseudo-ID (`wheelbase_etc`, `wheel_radius`,
`camber_caster_toe`) ponechána nerozbalená (R4 — katalog je zná pod těmito ID).

## 3. Normalizovaná data (tabulka / odkaz)

Plný seznam: `reports/NIGHT-WORK/normalized_ids.json` (klíč `ids`, 94 záznamů;
pole `logical_id/source_rows/primary_name/aliases/source_reference/status/evidence/notes`).
Každý záznam nese `source_reference` ve tvaru
`…MUSTANG-PHYSICS-MAPPING.md@blob:4d4d765…#L<řádka>`.

## 4. Agregace (reprodukovatelná, z validátoru)

- **Řádky F §2 (78):** VERIFIED **6** · ESTIMATED **7** · PENDING **20** · UNKNOWN **45**.
- **ID po normalizaci (94):** VERIFIED **7** · ESTIMATED **8** · PENDING **25** · UNKNOWN **54**.

Pozn.: součet PENDING/UNKNOWN řádků (20/45) se liší o 1 od F §1 (21/28-sloupec)
i od přepočtu E auditu (21/44): `compression_ratio` (L135) je v tabulce UNKNOWN,
součty 21/… nebyly po překlasifikaci aktualizovány. Detail v U4.

## 5. Validační výstup (`tools/validate_normalization.py`, exit 2)

```
[OK] pocet radku F == deklarovano (78) — nacteno 78
[OK] pocet radku F == odvozeno — 78
[OK] kazdy radek mapovan >=1 ID — nepokryto: zadne
[OK] source_rows ukazuji na skutecne radky — vadne: zadne
[OK] bez duplicit ID — unikatnich 94/94
[OK] prave 1 stav/ID z mnoziny — mnozina ['ESTIMATED', 'PENDING', 'UNKNOWN', 'VERIFIED']
[OK] soucet stavu radku == pocet radku — {'ESTIMATED': 7, 'UNKNOWN': 45, 'PENDING': 20, 'VERIFIED': 6}
[OK] soucet stavu ID == pocet ID — {'UNKNOWN': 54, 'PENDING': 25, 'ESTIMATED': 8, 'VERIFIED': 7}
[OK] odvozene stavy radku sedi s JSON meta — {'ESTIMATED': 7, 'UNKNOWN': 45, 'PENDING': 20, 'VERIFIED': 6}
[OK] odvozene stavy ID sedi s JSON meta — {'UNKNOWN': 54, 'PENDING': 25, 'ESTIMATED': 8, 'VERIFIED': 7}
[PENDING] deklarovanych 60 ID dolozeno seznamem — deklarovano 60, odvozeno 94
[OK] unresolved evidovany — 4 polozky
INFO clutch rpm/speed/stall bez ID (R4): ano

AGREGACE radky: 78 VERIFIED=6 ESTIMATED=7 PENDING=20 UNKNOWN=45
AGREGACE id: 94 VERIFIED=7 ESTIMATED=8 PENDING=25 UNKNOWN=54
NEVYRESENE: 4 / NEPOKRYTE RADKY: 0 / VADNE ODKAZY: 0 / DUPLICITY: 0
VERDIKT_DAT=PENDING: deklarovanych 60 ID dolozeno seznamem
```

## 6. Nevyřešené (z `unresolved`)

- **U1** `clutch_rpm / clutch_speed / clutch_stall` — bez katalogového ID
  (katalog zná jen `clutch_enabled/engage/kick`). Stav UNKNOWN, žádná umělá ID.
- **U2** `weight_box_size` (L55) má 10 sloupců místo 11 (chybí oddělovač
  Ověření/Riziko). Stav PENDING jednoznačný; formální vada.
- **U3** Seznam 60 ID nedoložen (viz §1). Stav UNKNOWN.
- **U4** Součty 7/3/21/28 (F §1) ani 6/7/21/44 (E audit) neodpovídají strojovému
  stavu tabulky 6/7/20/45. Stav PENDING (čeká na opravu součtů u vlastníků).

## 7. Závěr — lze-li rozpor uzavřít

Rozpor **nelze uzavřít** na PASS: každá doložená řádka (78/78) je mapována a
agregace jsou reprodukovatelné, ale deklarace „60 ID" nemá doložený seznam a
její stavový rozpad nesedí se strojovým počtem. Verdikt: **PENDING** (poctivý —
zdroje nestačí; nic nepodloženo). Cesta k PASS: Agent F zveřejní explicitní
seznam 60 katalogových ID (výběr ze 138) s jedním stavem na ID; pak se tento
audit přepočítá 1:1. FAIL se nekoná — žádné ID ani stav nebyly vymyšleny.
