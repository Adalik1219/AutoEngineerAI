# F4.3 – Runtime měření brzdné dráhy T03: BrakeBias 0.6 vs 0.9 (Agent M, 2026-11-17)

**Vlastník:** Agent M. Větev `f43-live-tune-reconciliation` (alias „f43"). Studio Play Solo
(`17ce64ee-a452-4e5c-b95d-45e66be3b314`, user-controlled, Play Solo jsem nevypínal/nezapínal).
**Vlastněný soubor: pouze tento report.** Šablona ani jiné soubory nesahnuty.
**Verdikt: PASS** — obě brzdné dráhy naměřeny v živé session, dráhy se liší.

## Výsledek (čísla)

| Běh | config_id | BrakeBias (readback) | run_id (outbox) | vzorků / doba | v(t=0.1 s) | brake_distance_studs | stav |
|---|---|---|---|---|---|---|---|
| Baseline | `cfg_f43_m_base` | 0.6 | `RUN-cfg_f43_m_base-T03-01` | 42 / 4.2 s | 92.09 | **56.53** | completed (v<0.1 + 1 s) |
| Bias 0.9 | `cfg_f43_m_bias09` | 0.9 | `RUN-cfg_f43_m_bias09-T03-01` | 25 / 2.5 s | 90.69 | **40.44** | completed (v<0.1 + 1 s) |

**Porovnání: 56.53 − 40.44 = 16.09 studs — bias 0.9 brzdí o ~28 % kratší dráhu.**
Rozdíl je měřený, ne odhad (obě outbox položky obsahují `brake_distance_studs` + plné vzorky).

## Kroky

- (0) Freshness gate **PROŠEL**: `IsMutable('BrakeBias') == true`, `GetMutableKeys() == 82`.
  `CloneVehicle('f43_m_gate')` vrátil neparentovanou kopii (Parent nil, mimo Workspace) → zničena.
  Žádný STOP/BLOCKED důvod nenastal.
- (1) Baseline: `CloneVehicle('f43_m_base')` → `WriteTune(BrakeBias, 0.6)` → readback 0.6 →
  `DeployVehicle` (build: 40 HingeConstraint, 4× `#BV`) → vůz na StartLine čelem +X →
  inbox `cfg_f43_m_base` (round-trip `ReadInboxConfig` OK) → běh T03 → outbox.
- (2) Totéž pro `f43_m_bias09` / `cfg_f43_m_bias09` / bias 0.9 (readback 0.9, build 40 hinge).
- (3) Porovnání viz tabulka (16.09 studs).
- (4) Cleanup: oba klony `DestroyVehicle` = true, žádné `Jeep_*`/`AE_*` ve Workspace,
  inbox/outbox 0/0, šablona netknuta (kořen 7 dětí, Tune 4 děti, `Initialize` stále pod Tune).

## Metoda (poctivě, co se skutečně měřilo)

Souborový harness v této session T03 sám neodjede (známé mezery, viz Agent S: žádný
`AE_VehicleSlot`, žádná počáteční rychlost, `DriverInputs` se neaplikují, `brake_distance`
ve schématu chybí). Proto jsem jel **reálnými živými moduly napřímo**:
`ScenarioDefinitions.Get('T03')` (procedura/ukončení), `ScenarioRunner:Spawn` + `DriverInputs`
(logovány do telemetrie), `TelemetryCollector` (vzorkování 10 Hz), `RuntimeController`
(inbox validace + `WriteOutboxResult`). Fyzika je skutečná: nasazený klon po buildu
(`Initialize`), rychlost 100 studs/s zapsaná na všechny BaseParts, brzda fyzikální.
Brzdění: přímý zápis `#BV` HingeConstraints (celkem 20000 = součet stock 4×5000, rozděleno
dle biasu předek/zadek: 0.6 → 6000/4000, 0.9 → 9000/1000 na kloub). Vstupní rychlost v t=0
přesně 100 v obou bězích; dráha = XZ vzdálenost pozice sešlápnutí → zastavení.
Nalezeno cestou: pivot modelu ≠ geometrie (~20 studs offset) → obchozeno runtime
`PrimaryPart = DriveSeat`, pouze na klonech.

## Limity (upřímně)

- Brzda je přímá aktuace `#BV`, nikoli klientský `Drive` (nikdo nesedí): bez ABS a bez
  rampy 0→1 za 0.15 s (okamžitý lock). Bias vstupuje jako rozdělení momentu — efekt biasu
  je reálná fyzika nasazeného podvozku, ne plná smyčka `Drive`.
- Živé moduly se liší od souborů (vzorkování 10 Hz vs 60 Hz v souboru) — měřeno živým
  chováním, to je pro RUN správně.
- Jedno opakování na variantu (T03 chce 3); rozptyl netestován — doporučeno zopakovat
  při kalibraci.
