# F6-CLOSURE — Vehicle Runtime Recovery & Collision Validation

**Verdikt: F6 PASS s výhradou (b09 repeatabilita).**
Aparatura dodává platné jízdy; první platná T03 kampaň v historii projektu.

## Mapování požadavků (brief F6 §2 body 1–6 + §7)

| # | Požadavek | Verdikt | Důkaz |
|---|-----------|---------|-------|
| C | Orientace vozu | PASS | facing 0.993/0.985, čumák +X (2× živě); fix yaw(−90°) |
| A | Drive lifecycle | PASS | rebind Car.Value + cleanup; konzole 0 chyb (2 kampaně) |
| B | Kola se točí | PASS | W≈74 = valení; E3 spin-fail vysvětlen (mrtvý Drive + bok) |
| D | Prostor/kolize | PASS | Blockcast: kužely přesunuty z=-10; dráha volná |
| T | Průjezd + brake smoke | PASS | coast drží; brzda 100→0/144 m; 6/6 completed+stopped |
| E | QA + logy | PASS | F6-QA; run-001..004 kompletní (6× plná telemetrie) |

## Kampaně

- b06 (Bias 0.6): 3/3 completed, delta 0.73 % → PASS.
- b09 (Bias 0.9): 3/3 platných jízd, delta 5.99 % → repeatabilita FAIL
  (pouze statistická brána; fyzika ani aparatura nechybí). r2 outlier
  evidován v run-004, příčina otevřená (fps-hitch/settle), potřeba větší n.

## Kořenové příčiny F5 (uzavřeny)

1. Vůz stál čelem +Z napříč tratí, rychlost +X → jízda bokem (ne 90°,
   ale −90° yaw od look −Z; operátorův směr potvrzen měřením).
2. `_PBrake` latch z Initialize-defaultu 5000 (bez klávesy P navždy).
3. Za server-nil ownership se motorové zápisy klienta neaplikují —
   brzdy F5 byl scrub zamčených kol. Oprava: server-autoritativní brzda.
4. Kužely slalomu stály v ose T03 (x=180–720) — přesunuty z=−10.

## Změněné soubory (commity 4cab440, 57f2cbe, 5e003fe, 823585d, 6a1ec54, 3572295)

- `TestHarness.server.lua`: yaw(−90°) spawn, TRACK_DIR rychlost.
- `ScenarioRunner.lua`: TRACK_DIR, vehicle-facing gate, ApplyServerBrake hák.
- `VehicleManager.lua`: Car.Value rebind, CleanupStaleClientInterfaces, bridge V2.
- `TestTrack/TestEnvironment`: kužely z=−10 (revertovatelné).
- `reports/F6/`: PLAN, QA, CLOSURE, runs/run-001..004.

## Známá omezení

Viz F6-QA §4. Pro další práci: větší-n kampaň T03, ABS-emulace na serveru,
throttle-cesta, sladit Rojo plugin 7.7.x, vrátit kužely pro slalom.
