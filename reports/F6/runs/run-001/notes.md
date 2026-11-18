# run-001 — audit A+C+D (Edit read-only, bez Play)

Měřeno živě v Edit: pivoty/rotace `TestSpawn`, `TestTrack` a všech dílů dráhy,
`JeepTemplate` (pivot, DriveSeat, kola, čelní/zadní díly, Interface), čtení
`Drive` (l.21 `local car`) a `Initialize` (l.569, l.639–647, #AV/#BV l.441–467).

## Rozhodující výpočet (C)

- Čelo vozu v lokálních souřadnicích: `Collision_Front` rel. pivot
  (−0.3, 1.4, +7.7) světově při pivot-rotaci R0 → lokálně (−7.7, −0.3, −1.4).
- Čelo = **lokální −X**. `DriveSeat.LookVector` (+Z světově u šablony) je po přepočtu
  stejný směr (−X lokálně) — konzistentní.
- `findT03StartCFrame` vrací `StartLine.CFrame` (identita) + 3 y. `PivotTo` protočí
  vůz o R = Rs·R0⁻¹ a čelo skončí na **−X** (k BackWall x=−19.5).
- Rychlost se přitom dává +X. Vůz stojí příčně/proti směru a je tlačen bokem —
  to samo vysvětluje scrub, roztáčení (yaw), roll loterii i „ztrátu rychlosti“.
- Facing-gate četl `RightVector` **spawnCFrame** (vždy +X → vždy PASS), nikdy vůz.
- Oprava: `StartLine.CFrame * Angles(0, π, 0)` (čelo → +X), rychlost explicitně
  `Vector3.xAxis` (TRACK_DIR), gate z čumáku vozu (`Collision_Front` vs. pivot).

## A — Drive lifecycle

- Stale reference potvrzena kódem: jednorázové `local car`, klon Interface při Situ,
  žádný cleanup při odchodu/zničení. Mrtvý Drive každým framem přepisuje motory
  (#AV vel/torque 0, #BV brzda) — vysvětluje i E3 „kola se netočí ani povelem“.
- Oprava ve `VehicleManager` (repo-strana, šablona `.rbxm` nedotčena):
  `DeployVehicle` přebinduje serverový `Car.Value`; `DestroyVehicle` + `DeployVehicle`
  mažou stale PlayerGui Interface (cizí/neplatné `Car.Value`).

## B, D

- B: po fixu A+C se v run-002 změří spin; dual-hinge overconstraint zatím neprokázán.
- D: geometrie dráhy zaměřena (viz `spawn.json`); Blockcast před kapotou až po
  yaw-fixu v Play (jinak by měřil špatný směr).

## Stav souborů

Žádný kód v run-001 měněn nebyl. `console.log`: v Edit bez Play-konzole — neuveden,
protože neexistuje (žádný prázdný důkaz). Telemetry: N/A (bez Play).
