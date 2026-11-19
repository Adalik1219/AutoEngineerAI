# AUDIT2 – Inventura dokumentačních rozporů (FÁZE A, needitováno)

Větev `feat/m1-m2-foundation`, PR #2 (OPEN, NEMERGOVAT).
Datum inventury: 2026-11-19. Skutečný HEAD v době inventury: `6cedbe1`.
Čteno: `docs/PROJECT_STATUS.md` + `docs/IMPLEMENTATION_ROADMAP.md` + `reports/FINAL_DOCUMENTATION_SYNC.md` celé.
FÁZE A = pouze inventura; `docs/*.md` needitovány.

## Ověřené skutečnosti (realita @ HEAD)

- `git rev-parse HEAD` → `6cedbe152d7cad35124b1e581a3a4f81b8154a7b`; `git log ff6f266..HEAD` = 2 commity, oba docs-only (`2bde563`, `6cedbe1`). Kód od `ff6f266` nezměněn kromě docstringu `src/Inspection/__init__.py`.
- `src/Inspection/rbxm_parser.py` = 1345 řádků — souhlasí s tvrzením v §0.2.
- `grep "def test"`: `test_m2_rbxm_parser.py` = 53, `test_m2_wheel_detect.py` = 21, `test_m1_mustang_profile.py` = 20 — souhlasí s tvrzením (53 / 21 / 20).
- RBXM hash `assets/chassis-original/chasis-work-copy.rbxm` = `dc8747e0…fedf` (sha256 ověřen čtením) — souhlasí.
- `src/autoengineer/` **neexistuje**; realita: `src/{Inspection,Reference,Physics,Chassis,Optimizer,Sim,Telemetry,common}/`.
- Počty 260/256/0/4 **nebyly v této fázi přeběhnuty** (inventura bez běhu testů); poslední doložený běh je @ `ff6f266` dle FINAL_DOCUMENTATION_SYNC.

## Seznam rozporů / nejasností

| # | Místo | Tvrzení v docs | Realita | Závažnost | Poznámka pro FÁZI B |
|---|---|---|---|---|---|
| D1 | PROJECT_STATUS §0 hlavička + §0.2 + §0.4; ROADMAP M2 hlavička/bod 8/bod 14 | vše pinováno na `@ ff6f266` | skutečný HEAD je `6cedbe1` (2 docs-only commity po `ff6f266`) | nízká / matoucí | Pin je obhajitelný pro **kód** (kód se od `ff6f266` nezměnil), ale nikde není věta „kód @ `ff6f266`, docs @ `6cedbe1`". Čtenář po `git rev-parse HEAD` uvidí nesoulad. FÁZE B: doplnit jednu větu o dvouúrovňovém pinování, nesahat jinam. |
| D2 | PROJECT_STATUS §0.4 „260/256/0/4 @ `ff6f266`, ověřeno během 2026-11-19" | vydáváno za aktuální stav | od té doby 2 docs commity; běh na HEAD `6cedbe1` nedoložen (jen docstring změna, ale bez běhu) | střední | FÁZE B: přeběhnout `python tests/run_all.py` na HEAD a číslo přepsat/potvrdit; do té doby ponechat s datem. Neediktovat naslepo. |
| D3 | ROADMAP M2 bod 6 (a obdobně M3–M9 bod 6) | navržené cesty `src/autoengineer/inspection/…`, `src/autoengineer/units/…` | adresář `src/autoengineer/` neexistuje; skutečné: `src/Inspection/rbxm_parser.py`, `src/Inspection/wheel_detect.py`, `src/common/units.py` (existuje) | nízká (spec je vědomě „navržené") | Text sám říká „navržené — ověřit proti repozitáři", takže nejde o lež; ale implementační agent musí znát mapování návrh→realita. FÁZE B: zvážit jednu závorkovou poznámku se skutečnými cestami jen v M2 bodu 6, ostatní moduly neměnit (historický audit). |
| D4 | PROJECT_STATUS §1 tabulka: M2 = NOT IMPLEMENTED | vs. §0.2 M2 = CODE-VERIFIED | není rozpor: §1–§8 jsou explicitně označeny HISTORICKÉ (stav k `dd9efdf`) | žádná — jen stopka editorům | FÁZE B: **neopravovat** §1; historická stopa se nemazá. Případný dodatek max. poznámkou pod čarou. |
| D5 | FINAL_DOCUMENTATION_SYNC §4 „Změněné / nové soubory" | vyjmenovává 3 soubory | po syncu vznikly další reporty (`FINAL_COORDINATION_REPORT.md`, `FINAL_INDEPENDENT_QA.md`, `FINAL_PERFORMANCE_BENCHMARK.md`, `STUDIO_GROUND_TRUTH.md`), na které §0.2/§0.4 neodkazují | nízká | FÁZE B: rozhodnout, zda §0.2 má citovat `AUDIT-qa-final.md` + nové QA reporty, nebo zda stačí současné 4 odkazy. Jen doplnění odkazů, žádný přepis hodnocení. |
| D6 | ROADMAP M2 bod 13/14 vs. hlavička | po syncu konzistentní (ČÁSTEČNĚ) | ověřeno čtením — bez rozporu | žádná | Uzavřeno syncem (řádky 9–10 sync tabulky). Uvádím, aby se znovu neotvíralo. |
| D7 | PROJECT_STATUS §0.5/1 „kalibrace … největší riziko" | vs. starší formulace „parser + kalibrace největší riziko" | aktuální znění už zúženo na kalibraci/měření; parser hotov | žádná | Uzavřeno syncem (ř. 3). Uvádím pro úplnost. |

## Co NENÍ rozpor (ověřeno, nešahat)

- 1345 řádků parseru, 53/21/20 testů, RBXM hash, M1 20/20 + validace 0/0 — vše sedí s realitou.
- `reports/AUDIT-geometry.md` hash-zkratka opravena na `…2c1fefdf` — souhlasí s plným hashem.
- §9 historická čísla 192/188 a 199/195 — ponechána s datem jako historická, správně.

## Doporučení pro FÁZI B (editace až po schválení)

1. Jedna věta o pinu: „kód @ `ff6f266`, docs @ `<HEAD>`".
2. Přeběh `tests/run_all.py` na HEAD + aktualizace §0.4 včetně data běhu.
3. Max. závorková poznámka se skutečnými cestami v ROADMAP M2 bodu 6.
4. Zvážit odkazy na nové QA/benchmark reporty v §0.2.
5. Nesahat na §1–§8 (historie) ani na hodnocení stupňů (CODE-VERIFIED vs RUNTIME).
