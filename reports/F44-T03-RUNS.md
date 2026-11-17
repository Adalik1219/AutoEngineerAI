# F44-T03: Agent M2 — 6 běhů bias 0.6 vs 0.9 (2026-11-17)

**Verdikt: BLOCKED — kampaň neproveditelná. Tři vady harnessu (H1), každá
samostatně fatální, všechny ověřeny živě v session
`17ce64ee-a452-4e5c-b95d-45e66be3b314` (Play Solo, bez restartu).**
Žádná f44 data nevznikla (adresář `vehicle-data/telemetry/f44/` ZÁMĚRNĚ
nevytvořen — test bere absenci jako legitimní SKIP/PENDING; falešné běhy
nezapisuji). Scope M2 je hotový a ověřený (níže).

## Co M2 dodal a ověřil (vše DONE)

- **Atributový můstek AE_Brake/AE_Throttle/AE_Steer → vstupy Drive**
  (`VehicleManager.ApplyDriveInputBridge`, idempotentní, kotva
  `Inputs(dt)` v Heartbeat smyčce). Kód v disku a v živé session je
  **byte-totožný (hash bloku 2636118128)**; aplikován na živou šablonu
  (nikoli `.rbxm` na disku) a volán z `CloneVehicle`.
- **Živý důkaz funkce:** usazený hráč → Drive běží (Controls, RPM 950) →
  `AE_Brake=1` → `Values.Brake=1` (klient). Můstek je jediná funkční cesta
  brzdy (Drive čte jen UserInputService; sedadlo nefunguje — potvrzeno).
- **Drive:1111 README-fallback** (živá šablona): `RepairStructure` stěhuje
  `README` zpod `Tune`, ale `Drive:1111` a `Gauges` ho čtou přes
  `car["A-Chassis Tune"].README` → Drive padal ještě před Heartbeat
  (`README is not a valid member`, chyba z konzole). Fallback hledá
  `car.README` i `car["A-Chassis Tune"].README`.
- **README vyjmuto z `REPAIR_MOVE_NAMES`** (disk): datový ModuleScript se
  stěhovat nemusí; stěhování rozbíjelo Drive i Gauges. `Interface`,
  `Initialize`, `Plugins` se stěhují dál.
- **`PrimaryPart = DriveSeat` na klonech** (disk `CloneVehicle` + živá
  šablona, dědí všechny klony): bez něj je `PivotTo` na kloubové sestavě
  (167 dílů) nedefinovaný — naměřeno rozhození sestavy, roll −85.6,
  pád světem na y=−419. S PrimaryPart je placement deterministický
  (sedadlo přesně na pivotu, roll 0.0).
- **Inbox cesta ověřena:** `AESubmitConfig:InvokeServer(cfg_f44_base)` →
  `accepted:true`; harness si vzal připravený `AE_VehicleSlot`
  (žádný auto-fill klon).

## Proč neběží T03 (3 blokující vady H1, mimo můj scope)

1. **Startovní směr −Z do svodidla.** `TestHarness.applyStartSpeed` bere
   `StartLine.CFrame.LookVector` = (0,0,−1) (StartLine je identita — live
   i `TestTrack.rbxmx`); trať a svodidla vedou podél X (BrakeLine x=3000).
   Start 100 studs/s míří napříč tratí do svodidla (~0.05 s). Oprava: použít
   `cf.RightVector` (+X).
2. **Spawn zapuštěný do vozovky.** `Spawn` pivotuje přesně na StartLine
   (y=−0.45 = uvnitř 1.1 silného slabu); kola končí pod povrchem, solver
   rychlost okamžitě sežere. Oprava: clearance +3 y (a facing +X).
3. **Outbox limit 200 kB zabíjí runBrief.** `WriteOutboxResult` padá:
   `Unable to assign property Value ... (1679011) ... max length (200000)`
   (`RuntimeController:98` ← `TestHarness:220` ← `:314`). T01-rep (40 s
   timeout, 60 Hz) má 1.68 MB → výjimka bez pcall → vlákno `runBrief`
   umírá v T01-r1 → T03 se vůbec nespustí. I kdyby T01/T02 prošly, T03
   běhy (~300 vzorků) balancují na hraně limitu. Oprava (H1): decimace
   vzorků pro outbox / chunking / pouze-T03 režim.

## Pokyny pozorovatele (splněno)

- (a) Vzpřímené umístění: ověřeno roll/pitch po každém spawnu (s PrimaryPart
  roll 0.0); incident „na boku" vysvětlen — ragdoll postavy (100+ kg) ležel
  na voze a nakláněl ho (−10.8°); po odklizení postavy mimo dráhu vůz sedí
  na 0.0°. Pro kampaň: postava park frequently na x=−30, usednutí až před
  během; práh abortu roll>45° hlídá harness.
- (b) `roll_max`: stávající telemetrie roll neobsahuje (pouze yaw); pro
  kampaň budu roll_max měřit živým pollingem (10 Hz) a evidovat v reportu
  po bězích. Žádné platné běhy → žádná čísla.
- (c) Vylučování: žádný běh k vyloučení nedošlo (žádný platný běh); postup
  pro kampaň: rollover (>45°) = void rep, celý config se po opravě příčiny
  jede znovu (3+3 platné běhy, outbox transientně čištěn, do f44/ jen
  kompletní platné submission + jejich SUMMARY).

## Statistika

Žádná (0 platných běhů). PASS kritéria (rozdíl > 3×std, 6 nenulových drah)
nevyhodnocena — pipeline k nim nedojde. Po H1 opravě je orchestrace
připravena: slot+vůz → Tune bias → seat → GUI distribuce → Drive-check →
AE watcher (arm při v>50, disarm teleportem) → InvokeServer → poll outboxu
→ fetch JSON → f44/ → statistika → H suite.

## Stav po cleanupu (ověřeno live)

- Workspace: žádné `Jeep_*`/`AE_VehicleSlot`; šablona nedotčena (disk),
  živá šablona: můstek + README-fallback + PrimaryPart (nutné pro běhy po
  H1 opravě); atributy AE_* na šabloně: žádné.
- Bridge inbox/outbox: 0/0; PlayerGui bez Interface-klonů; postava na
  x=−30 mimo dráhu.
- Disk: změněn pouze
  `testgame/src/ServerScriptService/AutoEngineer/VehicleManager.lua`
  (můstek + volání v `CloneVehicle` + PrimaryPart + README ze seznamu);
  validováno `lune` loadstring-checkem (LOAD OK). Tento report.
- `tests/test_f44_regression.py`: SKIP (PENDING, žádná data) — suite zelená.
