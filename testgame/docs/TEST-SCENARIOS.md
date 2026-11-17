# Testovaci scenare T01–T07 (Roblox runtime harness)

Vlastni: Agent E. Zdroj navrhu: `docs/TESTING-OPTIMIZATION.md` (S1–S7),
runtime zasady: `docs/ROBLOX-RUNTIME.md`. Implementace: `ScenarioDefinitions.lua`.
Stav: implementovano v harnessu, **Studio-beh PENDING** (dosud nemereno v Roblox runtime).

Konvence: jednotky studs/sekundy; prevod na m/km-h az pri vyhodnoceni mimo runtime.
Kazdy scenar: ID, pocatecni podminky, postup, completion/fail, merene veliciny, opakovatelnost.
Frekvence vzorkovani: 60 Hz. `run_id = hash(scenario_version, driver_version, variant_id, seed)`.

## T01 – Akcelerace 0–100

- Pocatecni podminky: v = 0, plyn 0, volant 0, auto-razeni, ustaleni 1 s.
- Postup: plny plyn rampou 0 → 1 za 0.2 s, volant 0; merit do 100 studs/s + 3 s dojezd.
- Completion: 100 studs/s + 3 s, nebo timeout 40 s (vlajka neuplne).
- Fail: roll > 45°, opusteni pruhu > 2 m, NaN, timeout.
- Merene: `t_0_100_s`, `t_0_60_s`, `slip_ratio_max_launch`, `gear_shift_count`, krivka `v(t)`.
- Opakovatelnost: 3×, median; rozptyl casu do ±5 %, jinak neplatny.

## T02 – Maximalni rychlost V-max

- Pocatecni podminky: v = 0, ustaleni 1 s.
- Postup: plny plyn, drzet primer, auto-razeni do ustaleni.
- Completion: ustalena rychlost (std poslednich 5 s mala), nebo timeout 90 s.
- Fail: roll > 45°, yaw-rate > 30°/s pri prime jizde, vyjeti z pruhu, NaN.
- Merene: `v_max_studs_s`, `t_to_vmax_s`, `yaw_rate_rms_high_speed`, `lat_deviation_rms`.
- Opakovatelnost: 3×, median; pri neustaleni vlajka `not_settled`.

## T03 – Brzdeni 100–0

- Pocatecni podminky: ustalenych 100 studs/s (±1 tolerance vstupu), plyn 0.
  Harness (F4.4, Agent H1): CFrame dilu `StartLine` v TestTracku (x = 2, overeno
  z `TestTrack.rbxmx`) + rychlost 100 studs/s pres `AssemblyLinearVelocity`
  vsech BasePartu (DriveSeat explicitne — Drive cte `DriveSeat.Velocity`).
  `entrySpeed` se cte z `ScenarioDefinitions` (`initial_conditions.speed_studs_s`).
  Opravy F4.4 (Agent F2, `reports/F44-T03-RUNS.md` H1): smer startu +X pres
  `RightVector` StartLine (`LookVector` -Z miril do svodidla); spawn +3 y nad
  StartLine (slab y = -0.45, sila 1.1), orientace nemenena.
- Postup: plna brzda rampou 0 → 1 za 0.15 s, volant 0. Replay brzi od t = 0
  (deterministicky, `ScenarioRunner:DriverInputs`); `BrakeLine` x = 3000
  (TestTrack) jako trigger je PENDING (nevlastnim `ScenarioDefinitions`).
- Mechanism brzdy/ABS (overeno live ctenim Drive zdroje v Play session, H1):
  brzda je SAMOSTATNY vstup `_IBrake` (0/1) vyhlazeny na `_InBrake` rampami
  `BrakeAccel`/`BrakeDecel` → `_GBrake` → `brake`; moment na kolo
  `(FBrakeForce|RBrakeForce * (60/fps) * brake * tqABS) + EBrake + PBrake`
  (`BrakeForce = 2500`, `BrakeBias = 0.6` live). ABS: `_Tune.ABSEnabled`
  (live default true, neni MUTABLE → harness nezapisuje) + toggle klavesou;
  aktivace pri prokluzu nad `ABSThreshold` (live 20) a `brake > 0` → `tqABS = 0`;
  signaly `Values.ABS` / `Values.ABSActive` (BoolValue) cte `TelemetryCollector`
  (`abs_enabled` / `abs_active`; chybi-li, null + duvod). NENI zaporny Throttle;
  predpoklad [P] v `TestClient` (`seat.Throttle = -brake`) Drive v tomto buildu
  neplati (0 vyskytu cteni seatu). Plny report: `ScenarioRunner.lua` hlavicka.
- Completion: v < 0.1 studs/s + 1 s ustaleni (hlida `ScenarioRunner:Evaluate`
  na XZ rychlosti), nebo timeout 20 s.
- Fail: protoceni (yaw > 90°), opusteni pruhu > 2 m, prevraceni, NaN.
- Merene: `brake_distance_studs`, `stopping_time_s`, `mean_decel`,
  `peak_decel`, `lat_deviation_braking`, `yaw_rate_max_braking`.
  `brake_distance_studs` = kumulativni XZ draha od t = 0 do prvniho vzorku
  s XZ-rychlosti < 0.1 (`ScenarioRunner.ComputeT03Metrics`); ABS aktivita
  (`abs.active` / `abs.active_samples`, jinak `active = null` + `reason`)
  je soucasti `summary.t03` kazdeho behu v outboxu.
- Opakovatelnost: 3×, rozptyl drahy do ±5 %. Harness bezi
  `repetitions = def.repetitions` na config a zapisuje agregat
  `SUMMARY-<config_id>-T03` (`mean`/`std` populacni/`min`/`max`/`delta_pct`,
  `repeatability_ok`) do outboxu; validuje `tests/test_f44_regression.py`
  (prazdny `vehicle-data/telemetry/f44` = SKIP, legitimni PENDING).
- Outbox limit 200 kB (F4.4, Agent F2): do outboxu se uklada decimovana kopie
  (cap 200 vzorku, adaptivni `step = ceil(n/200)` — T03 ~300 vzorku: step 2;
  T01 40 s: step 12), vzdy prvni + posledni vzorek. Plna telemetrie zustava
  v behu (navrat `runOneScenario`). Summary + `brake_distance` vzdy;
  `summary.t03` se pro outbox prepocita z ulozenych vzorku, takze nezavisly
  prepocet testu sedi. Decimace je popsana v
  `measurements.outbox_decimation` (`step`/`kept_samples`/`full_samples`).
  Mensi zasah nez podpora `scenario_ids` z inboxu (bez zmeny
  `RuntimeController`); zvolena decimace.

## T04 – Konstantni polomer / skidpad

- Pocatecni podminky: 40 studs/s, auto-razeni, kruh R = 100 studs, koridor ±2 m.
- Postup: stopar drzi kruh; rychlost po krocich do limitu (polomer nebo plateau `a_lat`).
- Completion: odjeto 25 s nebo lateralni limit s vlajkou.
- Fail: vyjeti z koridoru, smyk β > 20°, prevraceni, NaN.
- Merene: `a_lat_max_steady`, `understeer_gradient`, krivka volant–`a_lat`, `yaw_vs_steer_coherence`.
- Opakovatelnost: 3× na krok; gradient vyzaduje min. 3 platne kroky.

## T05 – Dvojita zmena pruhu (losi test)

- Pocatecni podminky: vstup 60 studs/s, tempomat.
- Postup: replay profilu volantu jako funkce drahy (1 perioda sinu od t = 5 s); identicke vstupy pro kazdou variantu.
- Completion: prujezd koridorem bez kontaktu s kuzely.
- Fail: kontakt s kuzelem, roll > 45°, hodiny (yaw > 180°), NaN.
- Merene: `passed_bool`, `yaw_rate_overshoot`, `sideslip_max`, `roll_max`, `settling_time_s`.
- Opakovatelnost: 3×; kontrola hashe vstupni sekvence (determinismus ridice).

## T06 – Slalom

- Pocatecni podminky: 40 studs/s, 10 kuzelu, roztec 60 studs.
- Postup: stopar s preview (pure-pursuit, pevne parametry `driver_version`).
- Completion: prujezd cilem; zaznamenan cas + naruseni koridoru.
- Fail: prevraceni, hodiny, NaN, timeout 30 s.
- Merene: `slalom_time_s`, `yaw_gain`, `steer_effort_rms`, `corridor_violations`.
- Opakovatelnost: 3×, median.

## T07 – Nerovnosti / rozbity povrch

- Pocatecni podminky: regulator 60 studs/s, usek 400 studs, povrch BUMP, seed 107.
- Postup: udrzet 60 studs/s pres pole nerovnosti (pevny seed → stejne hrboly pro vsechny varianty).
- Completion: dojezd 400 studs nebo 25 s.
- Fail: ztrata kontaktu vsech 4 kol > 0.5 s, prevraceni, NaN.
- Merene: `vert_accel_rms`, `susp_travel_min_max` na kolo, `tire_contact_loss_time_s`, `pitch_rms`, `roll_rms`.
- Opakovatelnost: 3× s pevnym seedem; rozptyl RMS do ±10 %.

## Mapovani na TestResult

Per-run vystup `TelemetryCollector:GetRunOutput` (`run_id`, `scenario_id`, `vehicle_id`,
`config_id`, `timestamp`, `environment`, `measurements`, `completion_status`, `errors`)
se mapuje pres `TelemetrySchema.ToTestResult` na `contracts/test_result.schema.json`
s `environment.mode = "roblox-runtime"`. Chybejici volitelne kanaly (RPM, prevod) = null.

## Brany

- `stylua --check` vsech Lua souboru: exit 0.
- `rojo build` (az bude `project.json`): exit 0.
- Studio-beh: PENDING.
