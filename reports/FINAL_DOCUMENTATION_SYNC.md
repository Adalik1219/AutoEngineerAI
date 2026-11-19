# Final Documentation Sync — stav k HEAD `ff6f266` (2026-11-19)

Větev `feat/m1-m2-foundation`, PR #2 (OPEN, NEMERGOVAT).
Role: Documentation & Traceability. Metoda: čtení `docs/PROJECT_STATUS.md` +
`docs/IMPLEMENTATION_ROADMAP.md` + `reports/AUDIT-*.md` celé + vlastní běh
`python tests/run_all.py` @ `ff6f266`. Historie NEMAZÁNA — stará čísla zůstávají
v §9 PROJECT_STATUS s datem jako historická.

## 1. Aktuální ověřené počty (@ `ff6f266`, běh 2026-11-19)

`python tests/run_all.py` → **běhů 260, PASS 256, FAIL 0, ERROR 0, PENDING 4**,
VÝSLEDEK: PASS (s 4 PENDING). PENDING totožné (Studio odečet, schema conformance
Fáze 5, 2× regresní baseline) — není PASS.

- `tests/test_m2_rbxm_parser.py`: 53 testů (`grep "def test"`), vše PASS v rámci sady.
- `tests/test_m2_wheel_detect.py`: 21 testů, vše PASS v rámci sady.
- RBXM hash před/po shodný (`dc8747e0…fedf`, pouze čteno `rb`).

## 2. Opravené rozpory

| # | Soubor / místo | Bylo (rozpor) | Je (po syncu) | Důkaz |
|---|---|---|---|---|
| 1 | PROJECT_STATUS §0.2 | „produkční parser a měření NENÍ hotovo", „parser (C05/C06) NOT IMPLEMENTED / BLOCKED" | C05 IMPLEMENTED + CODE-VERIFIED (není RUNTIME); BLOCKED/NOT IMPLEMENTED jen měření + kalibrace | `src/Inspection/rbxm_parser.py` (1345 řádků) @ `ff6f266`; `AUDIT-parser-security.md` (P0: 0); `AUDIT-qa-final.md` (7 sond fail-closed, verdikt MERGE docs-only) |
| 2 | PROJECT_STATUS §0 / §0.4 | počty bez vazby na revizi | každé číslo s revizí: aktuální 260/256 @ `ff6f266`; historické 199/195 a 192/188 → §9 s datem | vlastní běh `tests/run_all.py` 2026-11-19 |
| 3 | PROJECT_STATUS §0.5/1 | „parser (C05/C06) + kalibrace — největší riziko" | riziko zúženo: kalibrace M2.9/M2.10 (C06) + měření BLOCKED; parser C05 hotov | `AUDIT-qa-final.md` §4/3 |
| 4 | PROJECT_STATUS §0.5/2 | duplicita s bodem 1 | přeformulováno: M3 NOT IMPLEMENTED, blokováno bodem 1 | ROADMAP M3 |
| 5 | ROADMAP M2 hlavička | „M2.3–M2.10 parser/měření/kalibrace NOT IMPLEMENTED" | parser C05 + M2.1/M2.2 CODE-VERIFIED; BLOCKED jen M2.4–M2.8; NOT IMPLEMENTED jen M2.9/M2.10 | viz ř. 1 |
| 6 | ROADMAP M2 bod 8 (M2.1) | parser uveden jako součást spike | spike = jen sonda/rozhodnutí; C05 parser samostatná HOTOVÁ položka s důkazy | commity `230cb29` (C05-A/B) + `0f5b923` (C05-C) |
| 7 | ROADMAP M2 bod 8 | chybělo oddělení presetů | doplněno: presety ověřené (id 0/2) vs. `unread-preset-N` odděleně; plná tabulka = follow-up | `test_f6_cframe_preset_sweep`; `AUDIT-format-compat.md` |
| 8 | ROADMAP M2 bod 8 (spike vs. produkce) | „parser (C05/C06) vzniká až po něm" (budoucí čas) | C05 vznikl a pravidlo převzal; C06 až po Studio ground-truth | viz ř. 1 |
| 9 | ROADMAP M2 bod 13 | „žádný RBXM parser v repu zatím neexistuje" | parser existuje a je CODE-VERIFIED; rizikem zůstává kalibrace | viz ř. 1 |
| 10 | ROADMAP M2 bod 14 | „Stav: NOT IMPLEMENTED" (rozpor s hlavičkou ČÁSTEČNĚ) | „ČÁSTEČNĚ — C05 + kola CODE-VERIFIED; měření BLOCKED; kalibrace NOT IMPLEMENTED; není RUNTIME" | viz ř. 1 |

## 3. Cílový stav (potvrzeno)

- M1: CODE-VERIFIED (profil EU factory standard, validace 0/0, M1-T01…M1-T20 20/20 PASS).
- Parser C05: IMPLEMENTED + CODE-VERIFIED, **není RUNTIME** (žádné Studio měření).
- Geometrie z měření: BLOCKED (kalibrační brána, `float_decode_unverified`).
- Presety: ověřené (id 0 matice / id 2 identita) vs. unread (`unread-preset-N`) odděleně.
- Kalibrace `studs_per_meter` (M2.9/M2.10, C06): NOT IMPLEMENTED.
- M3: NOT IMPLEMENTED. M4–M9: PARTIAL (beze změny, historický audit §1).
- P2-2 (přímé volání `detect_wheels` mimo parser) + preset-tabulka: follow-up, neblokují
  (převzato z `AUDIT-qa-final.md` §4).

## 4. Změněné / nové soubory

- `docs/PROJECT_STATUS.md` — §0 hlavička, §0.2, §0.4, §0.5/1–2.
- `docs/IMPLEMENTATION_ROADMAP.md` — M2 hlavička, body 8, 13, 14.
- `reports/FINAL_DOCUMENTATION_SYNC.md` — tento report (nový).

Žádný kód ani test měněn nebyl (docs-only sync).
