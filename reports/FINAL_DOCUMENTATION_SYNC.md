# Final Documentation Sync — stav k HEAD `ff4a9d6` (2026-11-19)

Větev `feat/m1-m2-foundation`, PR #2 (OPEN, NEMERGOVAT).
Předchozí sync k `36cbbdb` níže (§5 Historie); starší k `ff6f266` tamtéž. Historie NEMAZÁNA.

Větev `feat/m1-m2-foundation`, PR #2 (OPEN, NEMERGOVAT).
Role: Documentation & Traceability. Metoda: čtení `docs/PROJECT_STATUS.md` +
`docs/IMPLEMENTATION_ROADMAP.md` + `reports/AUDIT2-docs-inventory.md` +
`reports/FINAL_*.md` + `reports/STUDIO_GROUND_TRUTH.md` celé + vlastní běh
`python tests/run_all.py` @ `36cbbdb` + `grep "def test"` + `tools/validate_contracts.py`.
Historie NEMAZÁNA — starší sync k `ff6f266` (oddíl 5 níže) a stará čísla
v §9 PROJECT_STATUS zůstávají s datem jako historická.
Inventurní doporučení D1–D5 (`reports/AUDIT2-docs-inventory.md`) jsou tímto uzavřena.

## 1. Aktuální ověřené počty (@ `ff4a9d6`, vlastní běh 2026-11-19)

`python tests/run_all.py` → **běhů 279, PASS 275, FAIL 0, ERROR 0, PENDING 4**,
VÝSLEDEK: PASS (s 4 PENDING). (Předchozí: 272/268 @ `36cbbdb` — viz §5 Historie.)
PENDING totožné (Studio odečet, schema conformance Fáze 5, 2× regresní baseline) — není PASS.

- `tests/test_m2_rbxm_parser.py`: 54 testů (`grep "def test"` @ `36cbbdb`;
  +1 proti 53 @ `ff6f266`: OSError → RbxmCorruptError, fáze B 36cbbdb), vše PASS v rámci sady.
- `tests/test_m2_wheel_detect.py`: 21 testů, vše PASS v rámci sady (beze změny).
- `tests/test_m1_mustang_profile.py`: 22 testů T01–T22 (+T21/T22 fáze B 36cbbdb:
  contracts-validátor M1.9 výjimka), vše PASS v rámci sady.
- `tools/validate_contracts.py` → 24 kontrol, 0 chyb, ÚSPĚCH (M1.9 výjimka
  pro prázdnou UNKNOWN křivku i v contracts validátoru — 36cbbdb).
- `src/Inspection/rbxm_parser.py` = 1352 řádků @ `36cbbdb` (bylo 1345 @ `ff6f266`).
- RBXM hash před/po shodný (`dc8747e0…fedf`, pouze čteno `rb`).

## 2. Opravy tohoto syncu (@ `36cbbdb`)

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
| 11 | PROJECT_STATUS hlavička + §0.4; ROADMAP M2 hlavička/bod 8/bod 14 | pinováno na `ff6f266`, počty 260/256/0/4 | jednotný pin `36cbbdb`; počty 272/268/0/4 vlastním během 2026-11-19; 260/256 @ `ff6f266` ponecháno jako historické | vlastní běh `tests/run_all.py`; inventura D1+D2 (`AUDIT2-docs-inventory.md`) |
| 12 | PROJECT_STATUS §0.2 / ROADMAP M2 bod 8 | 1345 řádků, 3 důkazní reporty, „žádné Studio měření“ | 1352 řádků; fáze B: RbxmError kontrakt + lane-order MSB-první + Ball=0; doloženy `FINAL_INDEPENDENT_QA.md`, `FINAL_COORDINATION_REPORT.md`, `FINAL_PERFORMANCE_BENCHMARK.md`, `AUDIT2-*`, `STUDIO_GROUND_TRUTH.md` | `36cbbdb` diff; inventura D5 |
| 13 | ROADMAP M2 bod 6 | jen navržené cesty `src/autoengineer/…` | závorkové mapování návrh→realita (`rbxm_parser.py` 1352 ř. + `wheel_detect.py` + `__init__.py`; `src/autoengineer/` neexistuje) | inventura D3; file listing |
| 14 | ROADMAP M1 bod 14 + PROJECT_STATUS §0.4 | 20 testů M1-T01…M1-T20 | 22 testů M1-T01…M1-T22 (T21/T22 contracts-validátor M1.9); `validate_contracts` 24/0 | `grep "def test"`; běh validátoru |
| 15 | PROJECT_STATUS §0.5/4, ROADMAP M2 bod 13/14 | ground-truth PENDING / „dosud neověřeny“ | `STUDIO_GROUND_TRUTH.md` DONE 2026-11-19 (rozvor ≈10.52 / rozchod ≈5.99 / Ball 2.7³ potvrzeny); stupeň dál CODE-VERIFIED, není RUNTIME | `STUDIO_GROUND_TRUTH.md` §3–4 |
| 16 | Benchmark tvrzení „B2 10–60×“ | plošné číslo z commit message `ff6f266` | opraveno rozsahem: hotspoty 5–240× dle operace (LZ4 ~49–240×, ref→type ~32×, memoizace ~5.5–14×); end-to-end ~2×; paměť beze změny | `FINAL_PERFORMANCE_BENCHMARK.md` Verdikt |
| 17 | CI | — | `53c2e23` fix evidován (repo-relative fixture, SKIP místo ERROR, `test_ci_portability.py`) | commit `53c2e23` |

Nesaháno (inventura D4, D6, D7): §1–§8 PROJECT_STATUS (historie), hodnocení
stupňů (CODE-VERIFIED ≠ RUNTIME), M2 body z předchozího syncu níže se nemažou.

## 3. Cílový stav (potvrzeno @ `36cbbdb`)

- M1: CODE-VERIFIED (profil EU factory standard, validace 0/0, M1-T01…M1-T22 22/22 PASS).
- Parser C05: IMPLEMENTED + CODE-VERIFIED, **není RUNTIME** (žádná runtime jízda;
  Studio ground-truth potvrzuje hodnoty kol, nemění stupeň).
- Geometrie z měření: BLOCKED (kalibrační brána, `float_decode_unverified`).
- Presety: ověřené (id 0 matice / id 2 identita) vs. unread (`unread-preset-N`) odděleně.
- Kalibrace `studs_per_meter` (M2.9/M2.10, C06): NOT IMPLEMENTED.
- M3: NOT IMPLEMENTED. M4–M9: PARTIAL (beze změny, historický audit §1).
- P2-2 (přímé volání `detect_wheels` mimo parser) + preset-tabulka: follow-up, neblokují
  (převzato z `AUDIT-qa-final.md` §4).
- PENDING≠PASS; CODE≠RUNTIME; M3 NOT IMPLEMENTED — merge message/PR popis musí nést
  (podmínka `FINAL_INDEPENDENT_QA.md`).

## 4. Změněné / nové soubory (tento sync)

- `docs/PROJECT_STATUS.md` — hlavička, §0.2, §0.4, §0.5/4.
- `docs/IMPLEMENTATION_ROADMAP.md` — M1 bod 14, M2 hlavička, body 6, 8, 13, 14.
- `reports/FINAL_DOCUMENTATION_SYNC.md` — tento report (rozšířen, historie níže).

Žádný kód ani test měněn nebyl (docs-only sync; kód @ `36cbbdb` beze změny).

## 5. Historie: předchozí sync k `ff6f266` (2026-11-19, ponecháno)

Předchozí běh @ `ff6f266`: **260 běhů, 256 PASS, 0 FAIL, 4 PENDING**
(53 / 21 / 20 testů v sadách; parser 1345 řádků). Řádky 1–10 původní tabulky níže —
ponecháno jako stopa, nic se nepřepisuje.
