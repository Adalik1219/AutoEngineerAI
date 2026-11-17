# RUNTIME-API — A-Chassis integrace ve Studiu (Agent C)

**Vlastník:** Agent C – A-Chassis Runtime Integration.
**Vlastněné soubory:** `testgame/src/ServerScriptService/AutoEngineer/VehicleManager.lua`,
`testgame/docs/RUNTIME-API.md` (tento dokument).
**Jazyk:** česky. Identifikátory a kód anglicky.
**Zdroje:** `docs/A-CHASSIS-AUDIT.md`, `docs/ROBLOX-RUNTIME.md` (§7 matice L1–L5, §8),
`docs/AGENT-RULES.md`, `src/Chassis/catalog/parameters.json`.

---

## 1. Klientský vs. serverový kontext (důkaz z auditu)

**Ověřená fakta** (`docs/A-CHASSIS-AUDIT.md`, §4):

- Fyziku A-Chassis 6C počítá **klient** — `Drive` (LocalScript, id 424, 42 093 B).
  Hlavní smyčky: `Heartbeat` (~60 Hz) + 15 Hz větev. Obsah: vstupy, řízení,
  motor, převodovka, diferenciály, TCS/ABS, brzdy, flip.
- Server **pouze staví** podvozek — `Initialize` (Script, id 426, 20 403 B).
  Za běhu staví: kola, nápravy, odpružení, motory `#AV`/`#BV`, gyra, váhu,
  weldy, sedadla.
- Síťový model: **server staví / klient počítá**.
  `DriveSeat:SetNetworkOwner(hráč)` — fyziku řídí klient sedícího hráče.
- Zvuky přes `RemoteEvent` (`Plugins`: Engine, Induction) + dva serverové zvukové
  skripty (`Server` id 380/383).
- GUI a telemetrie: `A-Chassis Interface` (ScreenGui v PlayerGui po usednutí —
  distribuuje `Initialize`), `Values`/`Controls`/`Car` ObjectValues,
  `AC6_Controls` (přemapování), `Gauges_AC6` (přístroje + max. rychlosti),
  `HP/TQ Reader`, `Simulated` (SS6 pneumatiky, `while wait()`),
  `Aerodynamics` (přítlak + odpor, obsahuje `magnitude` bug — audit §13, §17.2).
- Řídicí parametry: `Controllers`/`Gauges` ObjectValues; `Drive` očekává
  `script.Parent.Car` (ObjectValue), `IsOn`, `ControlsOpen`, `Values`.

**Důsledek pro testy:** automatické testy musí běžet s lokálním „řidičem"
(klientský kontext — Play Solo s usednutým hráčem), nikoli čistě na serveru.
Serverový `VehicleManager` připraví variantu (naklonuje, nastaví Tune),
ale jízdu a měření v Play řídí klientský `Drive`.

**Předpoklad [P]:** harness testovacího place umí posadit lokálního hráče
do `DriveSeat` a tím předat network ownership (ověří první Play test).

**Neznámé [N]:** runtime chyba `Initialize:171` (`Tune.StAxisOffset` v Tune chybí —
audit §9, §17.1) — potvrdí/vyvrátí první spuštění ve Studiu.

---

## 2. Odkud se berou vstupy řidiče

**Ověřený fakt** (audit §4, §15): vstupy čte klientský `Drive` z `Controls`
a `Values` (NumberValue/BoolValue), které vytváří `Initialize`/GUI.
`DriveSeat` je typu `VehicleSeat` s nulovým výkonem
(`Torque 0, MaxSpeed 0, Steer 0` — audit §3) — **nepohání**, slouží pouze
jako sedadlo + network-owner kotva. Skutečný pohon jsou Hinge-motory
`#AV` (trakce) a `#BV` (brzda), které staví serverový `Initialize`
(audit §12, §14).

Řetězec vstupů:

```text
sedící hráč (VehicleSeat) → Controls/Values → Drive (klient, Heartbeat)
  → #AV.AngularVelocity (trakce) / #BV (brzda) → HingeConstraint motory
```

Autonomní řidič testovacího place proto **nenahrazuje** `Drive` —
buď zapisuje do stejných `Controls`/`Values` objektů, nebo řídí
`VehicleSeat` (throttle/steer) stejně jako hráč. Dvojímu řízení
(harness vs. vestavěný input) se zabrání vypnutím stock inputu
v testovacím place (`ROBLOX-RUNTIME.md` §13, riziko „dvojí řidič").

---

## 3. VehicleManager API

Serverový ModuleScript
(`testgame/src/ServerScriptService/AutoEngineer/VehicleManager.lua`).
Vyžaduje se přes `require` ze serverového Scriptu. Nikdy nemutuje šablonu.

| Funkce | Vstup | Výstup |
|---|---|---|
| `CloneVehicle(configId)` | `configId: string` | `Model, nil` / `nil, reason` — klon `JeepTemplate` z `VehicleTemplates` do `Workspace`, název `Jeep_<configId>` |
| `DestroyVehicle(vehicle)` | `Instance` | `true` / `false, reason` — smaže pouze pracovní kopii ve `Workspace`; šablonu a obsah `VehicleTemplates` odmítne |
| `ResolveTune(vehicle)` | `Instance` | `ModuleScript, nil` / `nil, reason` — najde `A-Chassis Tune` v kopii |
| `ReadTune(vehicle, key)` | `Instance, string` | `true, value` / `false, reason` — pouze `MUTABLE_TUNE` |
| `WriteTune(vehicle, key, value)` | `Instance, string, any` | `true` / `false, reason` — pouze `MUTABLE_TUNE`; první zápis klíče si pamatuje pro rollback |
| `Rollback(vehicle)` | `Instance` | `count` — obnoví všechny změněné klíče do původních hodnot |
| `GetMutableKeys()` | — | seřazený seznam 79 `MUTABLE_TUNE` klíčů |
| `IsMutable(key)` / `DenyReason(key)` | `string` | `bool` / `string` — klasifikace klíče |

Pravidla Tune:

- Allowlist = 79 klíčů kategorie `MUTABLE_TUNE`
  (`src/Chassis/catalog/parameters.json`).
- `READ_ONLY` (3), `SCRIPT_CONTROLLED` (14), `STRUCTURE_CONTROLLED` (2),
  `UNKNOWN` (27) → odmítnuto s důvodem (`DenyReason`).
- Hodnoty tabulek (`Ratios`, `WeightBSize`, `TransModes`) se kopírují hlubokou
  kopií — rollback vrací skutečný originál, ne referenci.
- Zápis mění živou Tune tabulku (`require`); projeví se při stavbě podvozku
  (`Initialize` čte Tune přes `require`). Zápis do již postavených runtime
  instancí (kola, motory) se nepropaguje automaticky — varianta se staví
  v pořadí klon → Tune → build → Play.

---

## 4. Komunikace Python ↔ Studio

### 4.1 Primární cesta: souborová výměna (MIMO Rojo sync)

Python orchestrátor a Studio plugin/harness si vyměňují práci přes soubory
na disku — **nikoli přes Rojo sync** (Rojo synchronizuje skripty a strukturu,
ne fyzikální chování ani `.rbxm` modely — `ROBLOX-RUNTIME.md` §3):

```text
testgame/bridge/inbox/*.json    Python → Studio (požadavky: clone, apply-tune, run, revert)
testgame/bridge/outbox/*.json   Studio → Python (výsledky: manifest, summary, chyby)
```

- Jeden soubor = jeden příkaz / jeden výsledek; názvy souborů obsahují
  `config_id` + `run_id` pro párování.
- Formát zpráv a telemetrie: CSV/JSON + manifest (`ROBLOX-RUNTIME.md` §6, §9).
- Plugin/harness soubory pouze čte/zapisuje; nikdy nespouští cizí kód
  z neověřeného obsahu (žádný `loadstring` z inboxu — §11).

**Ověřený fakt:** oddělení vrstev `SIM` / `INT` / `RUN`
(`ROBLOX-RUNTIME.md` §8) — důkazem je pouze `RUN` měření v Play session;
souborová výměna je transport, ne důkaz.

### 4.2 Hodnocená alternativa: HttpService na localhost

Volitelný doplněk pro nižší latenci (plugin jako HTTP klient vůči
lokálnímu Python serveru, nebo naopak):

- Vyžaduje `HttpEnabled = true` v testovacím place.
- Studio omezení: `HttpService` povoluje pouze whitelisted endpointy
  v publikovaných hrách; localhost volání z pluginu v Edit/Play Solo
  podléhají bezpečnostním dialogům a limitům requestů.
- **Stav validace: PENDING ve Studiu** — nutno ověřit prvním Play testem
  (průchodnost localhost, latence, stabilita při 60 Hz telemetrii).
- Bezpečnostní výhrady: žádná autentizace na localhost zvenčí,
  bind pouze na `127.0.0.1`, žádný `loadstring` z HTTP odpovědi,
  timeout + retry s idempotentními příkazy (`config_id`/`run_id`).
- Do validace platí souborová výměna (§4.1) jako jediná podporovaná cesta.

---

## 5. Bezpečnostní matice L1–L5

Převzato z `docs/ROBLOX-RUNTIME.md` §7 (závazné pro `VehicleManager`):

| Úroveň | Co se mění | Příklady | Riziko | Pravidlo |
|---|---|---|---|---|
| L1 Konfigurace | hodnoty existujících parametrů | tuhost pružin, převody, `BrakeForce`, Tune hodnoty | nízké | povoleno autonomně (`WriteTune` pouze `MUTABLE_TUNE`); každá změna do `changes.json`; auto-rollback při regresi (`Rollback`) |
| L2 Skripty | zdrojáky chassis (beze změny API) | ladění řadiče, křivka plynu | střední | pouze na klonu; diff + parse-check před Play; zákaz změny `Require` cest bez schválení; po testu code-review záznam |
| L3 Hierarchie | Parent, názvy, přidání/odebrání instancí | nový `Attachment`, přesun senzoru, `NumberValue` | střední–vysoké | snapshot před změnou; kontrola referencí (`FindFirstChild`/`WaitForChild` cíle existují); zákaz mazání bez zálohy |
| L4 Geometrie | `Size`, `CFrame`, `Position`, mesh | posun kol, rozvor, camber natočením | vysoké | pouze s předchozím měřením (baseline); jedna geometrická změna na test; povinný screenshot/záznam bbox před/po |
| L5 Konstrukce | constraints, joints, pohonný systém | výměna `SpringConstraint`, FWD→AWD, náhrada A-Chassis | kritické | nikdy plně autonomně; vyžaduje schválení člověka + izolační test place; rollback klonem |

Obecná pravidla (§7): nikdy neměnit originál ani aktivně testovanou instanci
(vždy klon → změna → test → přijetí/zahození); každá varianta zná rodiče
(`parent.txt`); před Play záložní klon v `ServerStorage`
(`AE_Backup_<variantId>`), nikdy ve `Workspace`; po neúspěchu nulový diff
proti záloze; zákaz destruktivních operací bez zálohy.

`VehicleManager` pokrývá **L1** (Tune čtení/zápis/rollback) a bezpečné
základy L3 (klon/mazání kopií). L2/L4/L5 řeší jiné vrstvy
(plugin/harness) mimo tento modul.

---

## 6. Fakta / předpoklady / neznámé

**Ověřená fakta [F]:**

- Síťový model a role skriptů — `docs/A-CHASSIS-AUDIT.md` §4
  (`Drive` id 424 klient, `Initialize` id 426 server).
- Katalog 125 parametrů: 79 `MUTABLE_TUNE`, 3 `READ_ONLY`,
  14 `SCRIPT_CONTROLLED`, 2 `STRUCTURE_CONTROLLED`, 27 `UNKNOWN` —
  `src/Chassis/catalog/parameters.json` (ověřeno skriptem).
- Originál `C:/Users/adamr/Downloads/chasis.rbxm` není ve stromu hry;
  `VehicleManager` pracuje pouze s klony `JeepTemplate` ve `Workspace`.

**Předpoklady [P]:**

- Ve stromu Studia existuje `VehicleTemplates/JeepTemplate`
  (primárně `ServerStorage`, záložně `ReplicatedStorage`).
- Harness umí posadit lokálního hráče a převzít network ownership.

**Neznámé [N] (postup ověření):**

- `StAxisOffset` runtime chyba — první Play test (audit §17.1).
- Povolení `HttpEnabled` + průchodnost localhost — první Play test (§4.2).
- Přesné tolerance opakovatelnosti solveru — stanoví RUN-001
  (`ROBLOX-RUNTIME.md` §10).
