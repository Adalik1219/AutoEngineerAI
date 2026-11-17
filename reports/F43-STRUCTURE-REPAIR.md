# F4.3 – Oprava struktury šablony za běhu (Agent HR, 2026-11-17)

**Vlastník:** Agent HR. Větev `f43-live-tune-reconciliation` (v repu `f43` neexistuje;
koordinátorův název beru jako alias této větve). Studio Play Solo
(`17ce64ee-a452-4e5c-b95d-45e66be3b314`, user-controlled, Play Solo jsem
nevypínal/nezapínal).
**Verdikt: HOTOVO** — souborová část + živý důkaz startu Initialize/Drive;
plná aktivace přes souborový `VehicleManager` vyžaduje restart Play Solo (ovládá uživatel).

## 1. Diagnóza (execute_luau, Server)

- `JeepTemplate` (Model): kořen `Misc, Wheels, Body, A-Chassis Tune(ModuleScript),
  DriveSeat, JeepBodyVisual, CollisionParts`.
- Pod `A-Chassis Tune` visí celá logika: `A-Chassis Interface` (**ScreenGui**),
  `Initialize` (**Script**), `Plugins` (**Folder**, 9 dětí), `README` (ModuleScript).
  Všech 17 `LuaSourceContainer` šablony je pod Tune → engine je nespouští
  (`lacking capability`). Skriptů mimo Tune (TestHarness, sondy) se to netýká.
- Závislosti (hlavičky zdrojů):
  - `Initialize`: `require(script.Parent.README)`, `WaitForChild(Interface/Plugins/README)`
    pod `script.Parent` (= Tune); `local car=script.Parent.Parent`;
    `local _Tune=require(script.Parent)`; dále `script.Parent["A-Chassis Interface"]`,
    `script.Parent.Plugins` (reparent + `Destroy`).
  - `Drive` (LocalScript pod Interface): `script.Parent:WaitForChild(Car/Values/IsOn/…)` +
    `local car = script.Parent.Car.Value` + `require(car["A-Chassis Tune"])` — na Tune
    jako rodiče **nezávislý**, přesun celého Interface ho nedotkne.
  - `MiscWeld` (ModuleScript pod Initialize): `car = script.Parent.Parent.Parent`
    (MiscWeld→Initialize→Tune→vůz) + `car:WaitForChild("Misc")`.
  - Audit všech `script.Parent` (hloubka ≥ 2) v 17 kontejnerech: jediné kotvy ukazující
    mimo přesouvanou množinu jsou `Initialize L52/L53` a `MiscWeld L25`. Vše ostatní
    (Drive, Controls_AC6, Ignition, Gauges, Simulated, zvuky, HP/TQ…) čte sourozence
    platné až po runtime-reparentingu Initialize do Interface — ten je před/po
    přesunu totožný.

## 2. Změna souborů (vlastněné: 1 soubor)

`testgame/src/ServerScriptService/AutoEngineer/VehicleManager.lua`:
- `RepairStructure(vehicle)`: přesune celé podstromy `A-Chassis Interface`,
  `Initialize`, `Plugins`, `README` zpod Tune na kořen kopie (sourozenecké vazby
  zachovány, nic se nemazne, Tune tabulka netknuta); odmítne šablonu/její potomky;
  idempotentní; každý přesun `print`. Překotví 3 externí kotvy **pouze na klonu**:
  `Initialize`: `script.Parent.Parent→script.Parent` (car),
  `require(script.Parent)→require(script.Parent["A-Chassis Tune"])`;
  `MiscWeld`: `Parent.Parent.Parent→Parent.Parent`. Bez nich build neprojde
  (důkaz: první pokus bez MiscWeld-fixu visel na `Workspace:WaitForChild("Misc")`
  a `Plugins:Destroy()` se neprovedl).
- `CloneVehicle(configId)`: klon → `RepairStructure` → vrátí **neparentovanou**
  kopii (aby šlo před buildem zapsat Tune). Nové `DeployVehicle(vehicle)` parentuje
  do Workspace (= start buildu). Pořadí: Clone → WriteTune → Deploy.
  **Změna kontraktu** oproti `testgame/docs/RUNTIME-API.md` (dosud parentoval rovnou)
  — v `testgame/src` neexistuje žádný volající, docs nejsou vlastněné (ke koordinaci).
- Šablona/originál: NESAHNUTO (ověřeno: kořen 7 dětí, Tune zpět 4 děti).

## 3. Důkazy běhu (živá session, klon `Jeep_hr_verify`, algoritmus totožný se souborem)

Souborový modul se do běžící Play Solo nedostal (Rojo nesyncnul do Play;
`RepairStructure` v session `false`, session drží 82-klíčovou verzi) — proto důkaz
proběhl inline execute_luau se stejnými přesuny + stejnými 3 náhradami řetězců,
bez dotyku šablony. Po restartu Play Solo uživatelem poběží tatáž logika ze souboru.
- Přesun: 4/4 (`Interface:ScreenGui, Initialize:Script, Plugins:Folder,
  README:ModuleScript`); kotvy: Initialize 2/2, MiscWeld 1/1; Tune prázdný ModuleScript.
- `WriteTune(BrakeBias, 0.9)` → `ReadTune` = 0.9 na opraveném klonu (ResolveTune OK).
- Deploy → build: svary 0→**32**, `#BV` 0→**4**, HingeConstraint 0→**40** (šablona 0/0);
  Interface dostal `Car/IsOn/ControlsOpen/Version/Values` + všech 9 pluginů;
  `Plugins:Destroy()` proběhlo (složka pryč). `DriveSeat` existuje.
- Konzole: server `LogService` 0× `capability`; **klient 0× `capability` z 512 záznamů**.
- Usednutí hráče (BEZ plynu/brzdy): `DriveSeat:Sit(humanoid)` → occupant ✓ →
  `PlayerGui` nově `A-Chassis Interface` s `Car→Jeep_hr_verify`, 15 dětí, Version 2.1.
- Zbytkové hlášky: zvukové assety `rbxassetid://188608071` (není schválen pro requestera,
  prostředí, nesouvisí); starý spam `DriveSeat is not a valid member of "AE_VehicleSlot"`
  = pozůstatek HS-běhu (cizí `PlayerGui` klon, můj klon s ním nesouvisí).
- Cleanup: hráč vysazen (`Sit=false`), klon zničen, `_G.HR_CLONE=nil`; Workspace bez
  `Jeep_*/AE_*`; šablona netknuta (viz výše).

## 4. Akceptace / zbytková rizika

- H suite `python tests/run_all.py`: **148 běhů, 144 PASS, 0 FAIL, 4 PENDING**
  (PENDING totožné s baseline před změnou).
- Živý důkaz startu: Initialize postavil (svary/Hinge/#BV rostou z 0), Drive(Interface)
  běží v PlayerGui, 0 capability chyb na serveru i klientu.
- Rizika: (a) souborový `VehicleManager` se projeví až po restartu Play Solo —
  po restartu zopakovat freshness gate + jeden spawn; (b) `CloneVehicle` už neparentuje
  (viz kontrakt výše); (c) klientský main-loop Drive (jízda) nebyl předmětem —
  plyn/brzda až měření; (d) `StAxisOffset` (Initialize:171, audit §17.1) nebyl
  v tomto běhu zasažen, ale zůstává otevřený bod auditu.
