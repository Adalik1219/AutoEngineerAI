# F4.4 – Full T03 Autonomous Braking Validation: CLOSURE (koordinátor, FINAL)

**Repo:** `Adalik1219/AutoEngineerAI` main. **QA základ:** H suite 151/156 PASS, 1 systematický FAIL, 4 PENDING.
**Originál `chasis.rbxm`:** nedotčen. **RobloxSimulator:** read-only.

## IMPLEMENTED

- Atributový můstek AE_Brake/Throttle/Steer → Drive vstupy (server poroučí, klient provádí stejnou fyzikální cestou vč. ramp a ABS logiky).
- Harness: slot auto-fill, start +X s clearance +3y, T03-only inbox (`scenario_ids`), `brake_distance_studs` + ABS kanál v outboxu, decimace pod 200kB limit.
- 6 platných jízd T03 přes inbox (0 voidů), surová telemetrie v `vehicle-data/telemetry/f44/` (8 JSON), regresní test `test_f44_regression.py`.

## VERIFIED

- Smyčka end-to-end funguje: inbox → spawn → build → 100 studs/s → brzda → telemetrie → outbox → cleanup. Místo uklizeno, šablona netknuta.
- Tune hodnota v kauzálním řetězci (readback 0.6/0.9 před buildem).
- Směr efektu fyzikálně správný: 0.9 → 30.31 studs vs 0.6 → 41.81 studs.

## MĚŘENÍ (neprošlo barem — PENDING jako důkaz, ne PASS)

- 06: mean 41.81, std 4.09 (22.6 %). 09: mean 30.31, std 5.34 (40.4 %). Δ=11.49 < 3σ=14.28. Repeatability >5 %.
- Příčiny (vše doloženo): locknutá kola bez ABS (bounce/rock loterie, 4/6 timeout místo settle); klientský Drive přepisuje `Values.Brake` proti server-můstku (flapping); startovní rychlost 94.5–100 (2× mimo toleranci ±1).

## BLOCKED / NOT IMPLEMENTED (vstup F5)

- `test_summary_aggregate` systematicky FAIL: SUMMARY agreguje z full-sample, run-docs nesou decimované (design F3 vs test). Řešení: agregovat z kept-vzorků.
- `roll_deg` kanál chybí (rollover nedetekovatelný, Evaluate větev mrtvá).
- `RepairStructure` čte `init.Source` — v herním server-threadu bez PluginOrOpenCloud capability padá (auto-fill funguje jen přes MCP). Pro produkci přepsat bez čtení Source.
- Arbitrace `Values.Brake` (server autoritativně).
- Plná T03 smyčka přes `Drive` s ABS (vyžaduje rozhodnutí o `ABSEnabled` + 3 opakování).

## Verdikt

**F4.4 smyčka DODÁNA a průchozí; přesnost měření NEDOSAHUJE laťky (FAIL poctivě).** Neuzavírám jako PASS. F5 návrh: výše + opakovací kampaň s ABS.
