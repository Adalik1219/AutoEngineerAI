# Acceptance Criteria – měřitelné brány projektu

**Stav:** návrh v1 (ke schválení).
**Vazba:** `docs/IMPLEMENTATION_ROADMAP.md` (zdroj všech testovacích ID), `docs/PROJECT_STATUS.md` (plnění).
Každé kritérium má jasný PASS/FAIL a měřitelný důkaz. Vzor: F7.2 AC1–AC7 (`reports/F7/F7.2-PLAN.md`).

---

## 1. Globální brány (platí pro každý modul)

| ID | Brána | Důkaz |
|---|---|---|
| G-01 | Originální RBXM nezměněn | SHA hash vstupu před/po shodný |
| G-02 | Každá hodnota má jednotku | validace `tools/validate_contracts.py` PASS |
| G-03 | Každý cíl má zdroj nebo označený odhad | provenance `confidence` + `source` vyplněny |
| G-04 | UNKNOWN se nevydává za odhad | `value: null` tam, kde chybí data |
| G-05 | PENDING není PASS | testy s PENDING se nezapočítávají do PASS |
| G-06 | CODE-VERIFIED není RUNTIME-VERIFIED | runtime status jen s archivem ze Studia |
| G-07 | Python simulace není důkaz runtime | každý runtime verdikt odkazuje run ID |
| G-08 | Jedna iterace = jedna logická skupina parametrů | manifest iterace obsahuje právě jednu skupinu |
| G-09 | Každá změna má rollback | `rollback.json` obnoví původní (nulový diff) |
| G-10 | Reprodukovatelnost | stejný vstup + stejná verze = stejný výstup v toleranci |

## 2. Moduly (souhrn; plné sady v ROADMAP)

- **M1:** M1-T01…M1-T07 (načtení Mustangu; odmítnutí neúplné/špatné varianty; UNKNOWN drží).
- **M2:** M2-T01…M2-T08 (determinismus; 4 kola; nápravy; rozvor/rozchod; BLOCKED při nekonzistenci; zákaz zápisu).
- **M3:** M3-T01…M3-T09 (studs přepočty; 686,6/702,6 mm; symetrie; odmítnutí záměny náprav; BLOCKED propagace).
- **M4:** M4-T01…M4-T10 (jednotky; `P=T·RPM`; rychlost kola; 6 stupňů; žádné vymyšlené body; monotónnost brzd; energetická bilance; simulace ≠ runtime).
- **M5:** 7 pravidel (neznámý/READ-Only/mimo-rozsah/konflikt → odmítnuto; struktura oddělená; důvod + původní hodnota; žádná neověřená VERIFIED).
- **M6:** 7 pravidel + atomicita M6.10 (kopie+swap, kill-test, last-known-good s nulovým diffem); hash originálu; unikátní ID; žádná auto-aplikace.
- **M7:** každý test = postup + cíl s číselnou tolerancí + `verdict_rule` (explicitní nerovnost) +
  jednotky + vyhodnocení + důkazní úroveň L1/L2/L3; protokol bez čísel se zamítá;
  minima opakování z `HYBRID_WORKFLOW.md` §3; **L3 (jízdní chování) → `environment.mode:
  roblox-runtime` povinně**, jinak výsledek není runtime důkaz (G-07).
- **M8:** 8 pravidel + `n < 3 → INSUFFICIENT` (nikdy PASS); opakovatelnost `R` vs. přesnost
  `|x̄−target|/|target|` odděleně; outlier flagnut (|odchylka| > 3s), nikdy tiše smazán.
- **M9:** 9 pravidel (workflow s testovacím RBXM i Mustangem; 2 iterace; import výsledků; rollback; hash; žádné runtime PASS bez Studia).

## 3. Brána F7.2 (převzatá, neměnná)

AC1 zatáčení vlevo (|Δyaw| ≥ 0,15 rad, posun ≥ 8 coule/3 s) · AC2 vpravo + symetrie ±20 % ·
AC3 opakovatelnost R ≤ 10 % · AC4 návrat řízení (|yaw_rate| < 0,02 rad/s; úhel < 0,5°; dead-man neutral) ·
AC5 ztráta/stale příkazy · AC6 Occupant-only autorizace · AC7 anchored/dynamika. Runtime stav F7.2
se posuzuje samostatně (`PROJECT_STATUS.md` §4); tato brána se tímto dokumentem nemění.

## 4. Průchod milníky

- **Milník M1+M2:** systém zná cíle Mustangu a umí změřit výchozí model. Žádné změny auta.
- **Milník M1–M3:** první skutečný výstup — geometrický rozdílový report (tabulka zdroj/Mustang/rozdíl).
- M4 se neotvírá, dokud M1–M3 nemají akceptační testy PASS (špatné měřítko by znehodnotilo fyziku).
