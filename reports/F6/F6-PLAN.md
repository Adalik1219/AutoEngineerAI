# F6-PLAN — Vehicle Runtime Recovery & Collision Validation

## 0. Výchozí stav (audit, commit `c990629`, 2026-11-18)

- Disk čistý, `reports/F6/` založen tímto dokumentem. Šablona `JeepTemplate.rbxm` nedotčena.
- Studio `17ce64ee…` (Place1) v Edit módu, obsahuje `TestTrack`/`TestSpawn`/`TestEnvironment`,
  `ServerStorage.VehicleTemplates.JeepTemplate`, `ServerScriptService.AutoEngineer`.
- F5 verdikt: BLOCKED (0/6 platných). Přebrány nálezy F5-QA §E-final-II/G/H/I.

## 1. Potvrzené příčiny (F6-run-001, Edit read-only + čtení kódu)

1. **C — špatná orientace (kritická).** Čumák vozu sleduje `LookVector` spawnCFrame
   (run-002 živě: `seatLook≈+Z`, `frontD≈+Z 8.5`). `findT03StartCFrame` vracel
   `StartLine.CFrame` beze změny (look −Z) → vůz stál čelem +Z napříč tratí,
   rychlost +X ho tlačila bokem. Facing-gate četl `RightVector` spawnCFrame
   (vždy +X → vždy PASS) a maskoval to. Oprava: `StartLine.CFrame * yaw(−90°)`
   (čumák → +X), rychlost `TRACK_DIR`, gate z čumáku vozu.
2. **A — stale `Car.Value` (potvrzena).** `Drive` (l.21) čte `Car.Value` jednou při startu,
   `Initialize` klonuje Interface do PlayerGui při Situ (l.639–647) a po
   `DestroyVehicle` ho nikdy nemaže → mrtvý Drive, `#BV` na parkovacím defaultu 5000,
   spam `DriveSeat is not a valid member` každý frame. Motorové zápisy mrtvého Drive
   (#AV vel 0/torque 0, #BV přepočet) navíc mažou ruční povely každý frame.
3. **B — kola.** E3 „#AV=2000 nehne“ je vysvětleno bodem 2 (přepis mrtvým Drive),
   ne prokázaným overconstraintem. Dual-hinge `#AV`+`#BV` zůstává podezřelý č. 2
   až po fixu A+C.
4. **D — kolize.** StartLine kolizní (top y=0.1), spawn +3 y OK. Dráha: StartLine x=2
   → BrakeLine x=3000 → EndWall x=3804, šířka 12, koleje ±z. Prostor před kapotou
   po yaw-fixu = +X; Blockcast-scan se provede v Play-smoke (run-002).

## 2. Pořadí prací a závislosti

1. run-001 audit (hotovo, tento adresář) — A+C+D read-only.
2. Fix C (orientace + TRACK_DIR + vehicle-facing gate) → Fix A (rebind Car.Value,
   cleanup stale PlayerGui) — oba bez závislosti na Play, ověřeno suite + lint.
3. run-002 Play-smoke: spin-hold + coast bez brzdy + collision Blockcast (C+D live).
4. B izolace jen pokud smoke selže (jinak B=PASS pozorováním).
5. Full-lane 3× + brake smoke → run-003..005 → QA → F6-CLOSURE.

## 3. Akceptace (z briefu F6 §7, beze změn)

Aktuální vůz, čistá konzole, 4 kola rotují, +X facing, volná kapota, průjezd bez
zastavení, brake smoke, nulová rezidua, kompletní logy, nezávislé QA.
