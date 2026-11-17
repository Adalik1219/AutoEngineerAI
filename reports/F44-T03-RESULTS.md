# F44-T03: Agent M3 — 6 běhů bias 0.6 vs 0.9 (2026-11-17)

**Verdikt: FAIL (BLOCKED) — 0 platných běhů. Kampaň neproveditelná ve stávajícím
zapojení; žádná f44 data nevznikla (`vehicle-data/telemetry/f44/` ZÁMĚRNĚ
nevytvořen — test bere absenci jako legitimní SKIP/PENDING, viz M2 precedent).
Scope M3 (freshness + diagnostika + H suite) je hotový a ověřený (níže).**

Session: `17ce64ee-a452-4e5c-b95d-45e66be3b314` (Play, cizí — lifecycle nespravuji,
`start_stop_play` nikdy nevoláno). Disk: main `19b95a7` (H1 kód).

## 1. Freshness: PASS (ověřeno živě, pouze čtení — žádný zápis/teleport/restart)

Živá `TestHarness` (Server): délka zdroje **14126 B = bajtově disk**; plain-search
`string.find(src, pat, 1, true)` (pozor: `string.find` bez `plain=true` lže —
`-`/závorky jsou pattern-magie, první měření d【falešné negativy):**
- `CODE_VERSION ae-harness-0.2.1` ✓ (`cv`+`ver` true)
- `RightVector` start +X ✓, `Vector3.new(0, 3, 0)` clearance ✓ (H1 opravy 1+2 živě)
- `DecimateForOutbox` + `OUTBOX_SAMPLE_CAP` ✓ (H1 oprava 3)
- `AE_VehicleSlot` auto-fill ✓; `VehicleManager.IsMutable('BrakeBias')=true`,
  `IsMutable('ABSEnabled')=false` ✓ (ABS default ze šablony, harness nezapisuje)
- `RuntimeController.BRIDGE_NAME AutoEngineerBridge` ✓; bridge/inbox/outbox **0/0**,
  žádný `AE_VehicleSlot`, žádné `Jeep_*` (cleanup M2 drží)
- Klient: hráč + postava existuje, parkována mimo dráhu (≈−5,−5), **nesedí**;
  ve Workspace žádný DriveSeat (žádné vozidlo) — nic k uklízení

## 2. Běhy: 0/6 (neuskutečněny — záměrně, viz diagnóza)

Plánované: `cfg_f44_b06_r1..r3` (bias 0.6), `cfg_f44_b09_r1..r3` (0.9) → outbox →
f44 JSON + `SUMMARY-<config>-T03`. Rychlost/příkaz/ABS/čas/dráha/stav + roll_max:
**žádná čísla — žádný platný běh** (void 0, náhradní běhy 0/2 na variantu —
nespotřebovány, nebylo co nahrazovat).

## 3. Statistika: N/A → FAIL (žádných 6 drah; PASS kritérium
delta > 3× pooled-std + 6 nenulových drah nevyhodnoceno)

## Diagnóza (3 blokátory kampaně, všechny ověřeny kódem + živým stavem)

1. **Rozpojený protokol server→řidič (Agent D × E).** Harness vysílá
   `AERunBrief`/`AEStatus` (`TestHarness:209,271`); `TestClient` poslouchá
   **pouze `AE_DriverCommands`** (`cmd Start/Stop/EmergencyStop/SetBrakeZone`) —
   klientský řidič se při harness-běhu **nikdy nespustí** (nikdo nesedne,
   nikdo nebrzdí). Oprava = sjednotit protokol (vlastník D+E, mimo scope M3).
2. **Fyzická brzda by stejně neúčinkovala.** I kdyby řidič běžel, píše
   `seat.Throttle = -brake` (`TestClient:102`), ale Drive tohoto buildu
   `seat` vstupy **nečte** (H1: 0 výskytů, čte jen UserInputService).
   Jediná funkční cesta je můstek `AE_Brake → Values.Brake` (M2 live-důkaz),
   ale v `runOneScenario` ho **nic nenastavuje** (replay jen loguje do telemetrie).
   Vůz by projel T03 bez brzdění → `nezastaveno_do_timeout` 6×.
3. **Inbox nemá T03-only cestu.** `main()` i `BindSubmitConfig` volají
   `runBrief(config)` bez `scenarioIds` → vždy **plný brief T01–T07**
   (≈12.5 min/konfig: T01 40s×3 + T02 90s×3 + …), tj. ~25 min blokování
   hlavního vlákna Studia přes `task.wait` smyčky s rizikem zamrznutí/MCP-dropu —
   za cenu samých timeout-garbage dat. T03-only vyžaduje změnu kódu (mimo zákazy M3).

## 4. Suite + cleanup

- **H suite (`tests/run_all.py`): ZELENÁ** — 156 běhů, PASS 144, FAIL 0, ERROR 0,
  PENDING 12 (8× f44 legitimní PENDING + 4 pre-existující). VYSLEDEK: PASS.
- **`tests/test_f44_regression.py`: SKIP 8/8 (PENDING, legitimní)** — adresář
  `f44/` neexistuje; po dodání dat musí test PASS (jinak analýza agregátu).
- **Cleanup ověřen:** disk `git status` čistý, žádný `f44/` adresář, žádný diff;
  živá session: pouze read-only `execute_luau` (Find/Get/require/string.find —
  žádné `Instance.new`, žádné zápisy, žádné teleporty); bridge 0/0 beze změny.
  Postava parkována mimo dráhu, nesedí. K úklidu nic nebylo.

## Předání koordinátorovi

Pro odblokování kampaně je potřeba (mimo mandát/zákazy M3): (a) sjednotit
server→klient protokol (harness `AE_DriverCommands Start(T03)` nebo klient na
`AERunBrief`); (b) fyzické brzdění přes `AE_Brake` můstek v běžecké smyčce
(ne `seat.Throttle`); (c) T03-only cesta z inboxu (`scenario_ids` nebo filtr).
Pak lze 6 běhů protočit a tento report doplnit o čísla + statistiku.
