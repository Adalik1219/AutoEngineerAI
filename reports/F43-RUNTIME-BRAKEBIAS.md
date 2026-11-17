# F4.3 – Runtime test BrakeBias (Agent S, 2026-11-17)

**Vlastník:** Agent S. Větev `f43-live-tune-reconciliation`. Studio Play Solo (`17ce64ee-a452-4e5c-b95d-45e66be3b314`, user-controlled).
**Verdikt: BLOCKED** — session má STARÉ soubory, nutný restart Play Solo. Žádné další kroky neprovedeny.

## Ověřená fakta

- FRESHNESS GATE (krok 0) selhal — `VehicleManager.IsMutable('BrakeBias')` vrátilo `false` v živé Play Solo session.
- `VehicleManager.GetMutableKeys()` vrací **79 klíčů**, soubor ve větvi jich má **82** (`testgame/.../VehicleManager.lua`, `MUTABLE_TUNE_SET`).
- Raw výstup gate (execute_luau, Server): `{"ok":true,"res":{"mutable":false,"nkeys":79}}` (pole `biasDeny` chybí → stará verze nemá důvod pro `Bias`).
- Kontrolní čtení Workspace (Server search): žádné pracovní kopie `Jeep_*` neexistují; šablona `ServerStorage.VehicleTemplates.JeepTemplate` nedotčena.
- Bridge `ServerStorage.AutoEngineerBridge` (inbox/outbox) v session existuje; harness běží, ale test se nespustil (stop dle pravidel).

## Kroky po krocích

| Krok | Stav |
|---|---|
| (0) Freshness gate `IsMutable('BrakeBias')` | BLOCKED (`false`, 79 klíčů místo 82) |
| (1) Clone / WriteTune 0.9 / ReadTune / odmítnutí `Bias` | NEPROVEDENO (stop) |
| (2) Baseline T03 (bias 0.6, `f43_base`) | NEPROVEDENO (stop) |
| (3) Změněná T03 (bias 0.9, `f43_bias09`) | NEPROVEDENO (stop) |
| (4) Cleanup `DestroyVehicle` | NENÍ CO MAZAT (žádná kopie nevznikla) |
| (5) Report | tento soubor |

## Předpoklady / neznámé

- Předpoklad: uživatel restartuje Play Solo z aktuální větve `f43-live-tune-reconciliation`, čímž se do session dostane fresh `VehicleManager` (82 klíčů, `BrakeBias` mutable). Neověřeno — Play ovládá uživatel.
- Neznámé: zda po restartu projde zbytek postupu beze změn (T03 přes inbox/outbox, `config_id` musí splnit `^cfg_[A-Za-z0-9_]+$` dle `ConfigSchema`).

## Doporučené další kroky

1. Uživatel: zastavit a znovu spustit Play Solo (NE přes `start_stop_play` z MCP — ovládá uživatel).
2. Agent S (po restartu): znovu krok (0); je-li `IsMutable('BrakeBias') == true`, pokračovat kroky (1)–(5).
3. Riziko: pokud gate selže i po restartu, place nenačítá soubory z větve (špatný projekt/place soubor) — eskalovat koordinátorovi.

---

# Nový běh 2026-11-17T17:16Z (Agent S retry, čerstvá Play Solo session) — Verdikt: FAIL

Předchozí BLOCKED záznam výše PONECHÁN beze změny; toto je nový běh po restartu Play Solo.

## Nová fakta (živá session `17ce64ee-...`, datamodel Server)

- (0) Freshness gate **PROŠEL**: `IsMutable('BrakeBias') == true`, `GetMutableKeys() == 82`, `DenyReason('Bias')` = `PREJMENOVANO: ... -> zapis BrakeBias (F4.3 live Tune)`.
- (1) `CloneVehicle('f43_brakebias')` → `Jeep_f43_brakebias` (Model, Workspace). `ReadTune(BrakeBias)` před = **0.6**, `WriteTune(BrakeBias, 0.9)` ok, po = **0.9**. `ReadTune('Bias')` **odmítnuto** s PREJMENOVANO důvodem (důkaz přítomen).
- (2) Baseline T03 přes bridge: inbox `cfg_f43_base` (brakes.bias 0.6, `ReadInboxConfig` round-trip OK) → běh `RUN-cfg_f43_base-T03-01` (Tune 0.6, ScenarioRunner + TelemetryCollector 10 Hz, reálné moduly harnessu) → outbox zapsán. **brake_distance_studs = 0** (13 vzorků, 1.2 s, completed).
- (3) Změněná T03 přes bridge: inbox `cfg_f43_bias09` (bias 0.9) → `RUN-cfg_f43_bias09-T03-01` (Tune 0.9) → outbox zapsán. **brake_distance_studs = 0** (13 vzorků, 1.2 s, completed). **Rozdíl drah: 0 − 0 = 0 studs — žádný měřený rozdíl.**
- (4) Cleanup: `DestroyVehicle(Jeep_f43_brakebias)` = true, klon ve Workspace neexistuje, inbox/outbox prázdné (0/0), šablona `ServerStorage.VehicleTemplates.JeepTemplate` nedotčena.

## Příčina FAIL (měřeno, ne odhad)

1. Vstupní podmínka T03 nesplněna: skutečná rychlost vozidla 0 studs/s místo 100 (±1) — harness `AE_VehicleSlot` neexistuje a `ScenarioRunner.DriverInputs` se **nikdy neaplikují na vozidlo** (pouze se logují do telemetrie); vozidlo stojí, oba běhy ukončeny settle-pravidlem `<0.1 studs/s + 1 s`.
2. `VehicleManager.WriteTune` mění pouze tabulku Tune klonu; dle vlastního varování modulu se změna **nepropaguje do již postavených runtime instancí** podvozku (A-Chassis `Initialize` četl Tune při buildu) — bias 0.6 vs 0.9 neměl žádný fyzikální kanál, jak ovlivnit brzdy.
3. Výstup harnessu (`TelemetryCollector.GetRunOutput`) **nemá pole brake_distance**; dráha dopočtena z runtime vzorků (XZ pozice prvního/posledního samplu) = 0 v obou bězích.

## Doporučení

- Pro skutečný RUN-důkaz biasu je nutný harness, který (a) nastaví `AE_VehicleSlot` + počáteční rychlost 100 studs/s (reset CFrame + `AssemblyLinearVelocity`), (b) aplikuje brzdný vstup na A-Chassis aktuátory, (c) počítá `brake_distance` z telemetrie. Do té doby: **BrakeBias zůstává SIM/INT, nikoli RUN-verified.**
- Opakovat až po úpravě harnessu; tento report je baseline důkazem současného stavu.
