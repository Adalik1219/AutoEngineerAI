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
