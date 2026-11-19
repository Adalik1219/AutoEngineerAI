# Agent D — Adversarial review closeoutu (M2 closeout vlna, 2026-11-19)

**Větev:** `feat/m2-m3-geometry` · **HEAD v čase review:** `66c27e9`
**PR #2:** OPEN, NEMERGOVAT · **Režim:** READ-ONLY (pouze `git log/diff/status/rev-parse`, `gh run view`, `grep`, `sha256sum`; žádné mutující git operace, žádná změna kódu ani testů, žádné vlastní běhy testů).
**Vlastněný soubor:** `reports/M2-M3/AGENT-D-CLOSEOUT-ADVERSARIAL.md` (nový).
**Revizní podklady:** `FINAL-CLOSEOUT-REPORT.md` (koordinátor), `FINAL-CLOSEOUT-BASELINE.md` (+ staged delta), `FINAL-INDEPENDENT-QA.md` §9, `AGENT-A/B/C` reporty, `INTEGRATION-TEST-REPORT.md`, stav PR #2, `main`, CI runy.

## Verdikty po bodech (PASS / FAIL / NOT VERIFIED)

| # | Kontrolní bod | Verdikt | Důkaz / nález |
|---|---|---|---|
| D-01 | Diff `a7e89e5..HEAD` = pouze docs | **PASS** | 8 souborů, vše `docs/` + `reports/` (`PROJECT_STATUS`, `ROADMAP`, `AGENT-A/B` reporty, `FINAL-CLOSEOUT-*`, `FINAL-INDEPENDENT-QA`, `WHEEL-GEOMETRY-REPORT`). Žádný `src/`, `tests/`, `tools/`, `contracts/`, žádný RBXM. |
| D-02 | Finální SHA v `FINAL-CLOSEOUT-REPORT.md` §1 | **FAIL (minor)** | Report uvádí `dfb2e55 (+ tento report)`; skutečný HEAD je `66c27e9`, jehož jediný obsah je právě tento report (`git diff dfb2e55..66c27e9` = 1 soubor). Tvrzení bylo pravdivé v čase psaní, po commitu je zastaralé o jeden vlastní commit. Oprava: přepsat §1 na `66c27e9`. |
| D-03 | CI vazba v `FINAL-CLOSEOUT-BASELINE.md` (staged sekce) | **FAIL** | Sekce tvrdí: run `44617147977` má head_sha `66c27e9`. Ověřeno `gh run view`: `44617147977` → headSha **`a7e89e5`**. Run ID je opsané ze staršího commitu. Správné vazby (ověřeno živě): `a7e89e5`→`44617147977` success; `dfb2e55`→`44618936864` success; **`66c27e9`→`44618988364` success**. Realita je zelená, zápis je špatně. Oprava: nahradit ID `44617147977` → `44618988364`. |
| D-04 | CI dodatek k finálnímu SHA v `FINAL-CLOSEOUT-REPORT.md` §4 | **FAIL (minor)** | §4 končí „CI běh k němu: viz dodatek po pushi" — dodatek nebyl doplněn. Přitom run existuje a je zelený (`44618988364`, success, viz D-03). Oprava: doplnit jednu větu s run ID. |
| D-05 | „Strom čistý" (baseline + report) | **FAIL** | `git status --short` → `M  reports/M2-M3/FINAL-CLOSEOUT-BASELINE.md` (staged, necommitnuto — právě sekce hodnocená v D-03). Tvrzení „strom čistý" je v tomto okamžiku nepravdivé. Oprava: sekci opravit (D-03) a commitnout, nebo unstagingnout. |
| D-06 | PR #2 OPEN, jiná větev, nemergováno | **PASS** | `gh pr view 2`: state OPEN, head `feat/m1-m2-foundation` @ `ab840a9`, base `main`. M2 vlna v PR není. |
| D-07 | `main` netknut | **PASS** | `git rev-parse main` = `5b67315`, shoduje se s deklarací. |
| D-08 | M3 neotevřena (bez kódu) | **PASS** | `src/Geometry/`, `geometry_target.json`, `geometry_diff.json` neexistují; existuje pouze `reports/M3/GEOMETRY-ENGINE-PROPOSAL.md`. |
| D-09 | 161 vs 168 (rozpor součtů M2 sad) | **PASS** | `grep -c "def test"`: 57+53+7+31+20 = **168**; 161 = součet bez inspector-sady (57+53+31+20). Aritmetika sedí, vysvětlení je ve všech vlnách konzistentní. |
| D-10 | 110/110 (wheel + parser, Agent B) | **PASS** | 53 + 57 = 110. Parser-suite má 57, ne 56 — opraveno a doloženo během. |
| D-11 | 372 / 368 / 0 / 0 / 4 (plná sada) | **PASS (křížově), viz D-12** | Čísla identická v Agent-A re-syncu, Agent-C §1/§9, QA §9.1, closeout §3. Aritmetika M2 sad (168) + zbytek repa (204) = 372; 372−4 PENDING = 368. |
| D-12 | Vlastní živý běh testů Agentem D této vlny | **NOT VERIFIED** | Agent D této closeout-vlny testy nespouštěl (read-only review). Čísla v D-11 jsou křížově konzistentní přes 4 nezávislé zdroje + aritmetika sedí, ale bez vlastního běhu je nelze označit za nezávisle verifikované. Před mergem platí dřívější podmínka: jeden sériový `run_all.py` na finálním HEAD. |
| D-13 | PENDING vydáván za PASS | **PASS** | Nikde: všude „368 PASS + 4 PENDING", PENDING taxativně vypsány (Studio-měření, Fáze 5, 2× Fáze 9/10), „žádný se nezapočítává do PASS". |
| D-14 | Historický test vydáván za nový | **PASS** | V `a7e89e5..HEAD` žádný test nepřibyl ani se nezměnil; žádný report netvrdí nové testy v této vlně. |
| D-15 | Změněný soubor mimo deklarovaný diff | **PASS** | Všech 8 změněných souborů je v deklarovaném rozsahu docs+audit; `INTEGRATION-TEST-REPORT.md` / `SCALE-CALIBRATION-REPORT.md` se v této vlně neměnily (jejich sync proběhl dříve, v `64be2c6..a7e89e5`). |
| D-16 | BLOCKED vydáván za VERIFIED / M3 otevřena zadními vrátky | **PASS** | Kalibrace na reálných datech BLOCKED (7,44 % > 5 %), assess BLOCKED (`float_decode_unverified`), brána `require_verified_for_m3` drží, M3 bez kódu. I-1 CLOSED (oprava `34a4994`, pin-test 20/20). |
| D-17 | Engine vs stub záměna | **PASS** | Agent A (§zdroj pravdy) i Agent C (§3) explicitně rozlišují: `rbxm_parser.calibrate_studs_per_meter` = záměrný NOT-IMPLEMENTED stub rozhraní vs `scale_calibration.calibrate` = IMPLEMENTED engine. `PROJECT_STATUS`/`ROADMAP` po syncu „kalibrace NOT IMPLEMENTED" netvrdí (ověřeno grepem). |
| D-18 | `float_decode_unverified` zamlčen / svévolně odstraněn | **PASS** | Ponechání je ve všech zprávách přiznané jako vědomé konzervativní rozhodnutí koordinátora s odkladem na kalibrační vlnu. Žádné tiché odstranění. |
| D-19 | RBXM beze změny (G-01) | **PASS** | `sha256sum` obou kopií shodný: `dc8747e0…2c1fefdf`, 230 421 B. Jediný distinctní model = přiznaný LIMIT, ne FAIL. |
| D-20 | Hlavičky dokumentů vs HEAD (`@ a7e89e5`) | **NOT VERIFIED (stale-minor)** | `PROJECT_STATUS` §0, WHEEL-report hlavička i QA §9 uvádějí HEAD `a7e89e5` — o 2 commity pozadu (`dfb2e55`, `66c27e9`). Obsahově nezávadné (delta je čistě dokumentační, kód nedotčen), ale údaj neodpovídá HEAD. Doporučení: při opravách D-02–D-05 sjednotit hlavičky na `66c27e9`, nebo větu „docs-only delta beze změny výroků". |
| D-21 | QA §9 „diff `64be2c6..HEAD` = 11 souborů" vs realita 13 | **PASS (s vysvětlením)** | V čase psaní §9 (@ `a7e89e5`) bylo 11 správně; +2 soubory přidaly commity `dfb2e55` (`FINAL-CLOSEOUT-BASELINE`) a `66c27e9` (`FINAL-CLOSEOUT-REPORT`). Není rozpor, jen stáří textu. |
| D-22 | `validate_contracts` 24/0 + přiznaná mezera freeze schémat | **PASS** | Výsledek 24/0 konzistentní v C/QA/closeoutu; mezera (freeze kontrakty bez schémat v `contracts/`) je explicitně přiznaná, ne zamlčená. |
| D-23 | G-01–G-07 + G-10 PASS, G-08/G-09 mimo rozsah | **PASS** | Brány doloženy živou evidencí v QA §9.2; vyloučení G-08/G-09 je deklarované, ne skryté. |

## Nálezy (seřazeno dle závažnosti)

1. **F-1 (D-03): Špatné CI run ID v baseline.** Staged sekce `FINAL-CLOSEOUT-BASELINE.md` přiřazuje run `44617147977` k HEAD `66c27e9`; run patří k `a7e89e5`. Správný run k HEAD je `44618988364` (success). Faktická chyba v auditní stopě — opravit před uzavřením.
2. **F-2 (D-05): Nepravdivý „čistý strom".** Ve stromě je staged necommitnutá změna (nositelka F-1). Tvrzení baseline je aktuálně nepravdivé. Vyřeší se opravou F-1 + commitem.
3. **F-3 (D-02/D-04): Zastaralý finální SHA a chybějící CI dodatek v closeout reportu.** §1 uvádí `dfb2e55`, chybí věta o runu k `66c27e9`. Realita je přitom zelená (`44618988364` success) — jde o nedoplněný text, ne o skrytý problém.
4. **N-1 (D-20): Hlavičky `@ a7e89e5` o 2 commity pozadu.** Kosmetické; výroky nejsou dotčeny.
5. **N-2 (D-12): Chybí vlastní běh testů na finálním HEAD.** Křížová konzistence 4 zdrojů + aritmetika drží, ale nezávislá exekuce na `66c27e9` v této vlně neproběhla. Podmínka sériového `run_all.py` před případným mergem trvá (flaky historie z paralelní vlny).

**Nenalezeno:** starý kód vydávaný za nový, změna `src/`/`tests/` mimo diff, PENDING→PASS, BLOCKED→VERIFIED, engine↔stub záměna, otevřená M3, sáhnutí na PR #2 / `main`. Všechny tyto adversarial hypotézy jsou **vyvráceny**.

## Celkový verdikt Agenta D

- **M2 CONDITIONAL PASS — potvrzuji** (podmínky: uklidit `float_decode_unverified` text po kalibrační vlně; sériový běh před mergem).
- **M3 NEOTEVÍRAT — potvrzuji** (vstupy BLOCKED/BLOCKED, brána drží, bez kódu).
- **Closeout jako celek: CONDITIONAL PASS s opravami F-1–F-3.** Po opravě tří bodů (správné run ID, finální SHA + CI dodatek, commit čistého stromu) a sjednocení hlaviček (N-1) je vlna uzavíratelná. Na FAIL M2 není důvod; nálezy jsou dokumentační, nikoli funkční.
