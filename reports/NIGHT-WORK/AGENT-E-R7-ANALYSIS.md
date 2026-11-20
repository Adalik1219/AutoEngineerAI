# Agent E-R7 — analýza statusů (Fáze 1/4)
Vlastník: subagent E-R7 · Datum: 2026-11-20 · Větev: fix/normalization-evidence-integrity · read-only, bez změn kódu

## Autoritativní definice R7
`ids[].status` = sloupec Stav zdrojového řádku (stav mapování/připravenosti, ne čistý stav mustangovského cíle; viz N-F1: `drive_config` VERIFIED vs `differential_type` UNKNOWN). Při rozbalení skupiny (R2) dědí každé ID stav řádku. Cíl je evidován zvlášť v `evidence`.

## Ověření validátoru (před opravou)
NEKONTROLUJE rovnost. `row_stav` se parsuje, ale R7-blok testuje jen divergenci řádků pod jedním ID (`len(stavy_radku)>1`); nikde není `e.status == row_stav[ln]`. Kryty jsou jen agregace, `ALLOWED` a E3-provenance. Test `test_07` jen synteticky sloučí `weight_lb←[52,53]` — žádný test nepřepíše status jednořádkového ID.

## Skutečná data
- ŽÁDNÝ záznam nemá více `source_rows` (ověřeno strojově, test_24 to tvrdí).
- Příklady: `drive_config` VERIFIED [158] vs `differential_type` UNKNOWN [159]; `weight_lb` ESTIMATED [52]; skupina `downforce_f`+`downforce_r` UNKNOWN [173].

## Navržený algoritmus (předáno Agentu E, implementováno)
1. Načíst `row_stav[ln]` ze zdrojové tabulky (78 řádků). 2. Rozbalit skupiny dle R2. 3. `status := row_stav[ln]`; více `source_rows` jen při shodě všech. 4. `evidence` evidovat odděleně. 5. `relationship := UNRESOLVED`. 6. Per-záznam assert `e.status == row_stav[ln]` + agregace.

| # | Autoritativní definice | Současná implementace | Mezera | Navržený test |
|---|---|---|---|---|
| R7-A | Status ID = stav řádku | Žádné `status==row_stav` porovnání | Tichý posun statusu projde | `drive_config.status←UNKNOWN` → FAIL |
| R7-B | Kontrast sousedních stavů | Jen agregované čítače | Prohození drží součty | `differential_type.status←VERIFIED` → FAIL |
| R7-C | 1 řádek = 1 ID, dědičnost | Kryto jen pro multi-rows | Single-row posun bez testu | `weight_lb.status←UNKNOWN` → FAIL |
| R7-D | Rozbalená skupina dědí stav řádku | Chybí test sdíleného řádku | Multi-row v datech neexistuje | `downforce_f.status←PENDING` → FAIL; multi-row: fixture-konstatování |

## Stav
Předáno k implementaci (testy 21–24). Blokující nejasnost: žádná.
