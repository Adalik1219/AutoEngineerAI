# F4.3 – Live Tune diff (Agent R, 2026-11-17)

**Vlastník:** Agent R (vlna 1). Ground truth: `vehicle-data/analyzed/live-tune-keys.txt`
(167 živých klíčů, `require()` Tune v Play Solo) + běhové hodnoty
`FinalDrive=3.545`, `Horsepower=200`, `BrakeBias=0.6`, `PBrakeBias=0`.
Katalog: `src/Chassis/catalog/parameters.json` (138 záznamů po opravě).

## 1. Souhrn

| Stav | Počet |
|---|---|
| OK (live klíč = katalog `tune_key`) | 89 |
| PŘEJMENOVÁN (fantom → live klíč) | 28 |
| CHYBÍ_V_KATALOGU (live klíč bez záznamu) | 50 |
| FANTOM (katalog klíč mimo live) | 0 |
| Live klíčů celkem | 167 |
| Katalog záznamů s `tune_key: null` (mimo Tune) | 21 |
| Katalog UNKNOWN celkem | 37 |

## 2. Úplný diff 167 live klíčů vs katalog

| Tune klíč (live) | live_typ | katalog `id` | stav |
|---|---|---|---|
| `ABSEnabled` | boolean | `—` | CHYBÍ_V_KATALOGU |
| `ABSThreshold` | number | `abs_threshold_sps` | OK |
| `Ackerman` | number | `ackermann` | OK |
| `AutoDownThresh` | number | `auto_down_thresh` | OK |
| `AutoFlip` | boolean | `—` | CHYBÍ_V_KATALOGU |
| `AutoShiftMode` | string | `auto_shift_mode` | OK |
| `AutoShiftType` | string | `auto_shift_type` | OK |
| `AutoShiftVers` | string | `—` | CHYBÍ_V_KATALOGU |
| `AutoStart` | boolean | `—` | CHYBÍ_V_KATALOGU |
| `AutoUpThresh` | number | `auto_up_thresh` | OK |
| `AxleDensity` | number | `axle_density` | OK |
| `AxleSize` | number | `axle_size` | OK |
| `BrakeAccel` | number | `brake_accel` | OK |
| `BrakeBias` | number | `brake_bias_front` | PŘEJMENOVÁN (dříve `Bias`) |
| `BrakeDecel` | number | `brake_decel` | OK |
| `BrakeForce` | number | `brake_force` | OK |
| `CDiffLockThres` | number | `lock_thresh_c` | PŘEJMENOVÁN (dříve `LockThres`) |
| `CDiffSlipThres` | number | `slip_thresh_c` | PŘEJMENOVÁN (dříve `SlipThres`) |
| `CGHeight` | number | `cg_height` | OK |
| `Clutch` | boolean | `clutch_enabled` | OK |
| `ClutchEngage` | number | `clutch_engage` | OK |
| `ClutchKick` | boolean | `clutch_kick` | OK |
| `ClutchMode` | string | `—` | CHYBÍ_V_KATALOGU |
| `ClutchRPMMult` | number | `—` | CHYBÍ_V_KATALOGU |
| `ClutchRel` | boolean | `—` | CHYBÍ_V_KATALOGU |
| `ClutchType` | string | `—` | CHYBÍ_V_KATALOGU |
| `CompressionRatio` | number | `compression_ratio` | OK |
| `Config` | string | `drive_config` | OK |
| `Controls` | table | `—` | CHYBÍ_V_KATALOGU |
| `CurveMult` | number | `curve_mult` | OK |
| `CustomSuspensionDensity` | number | `—` | CHYBÍ_V_KATALOGU |
| `DifferentialType` | string | `differential_type` | OK |
| `EBrakeForce` | number | `engine_brake_force` | OK |
| `EH_EndMult` | number | `electric_end_mult` | OK |
| `EH_EndPercent` | number | `electric_end_percent` | OK |
| `EH_FrontMult` | number | `electric_front_mult` | OK |
| `ET_EndMult` | number | `electric_torque_end_mult` | OK |
| `ET_EndPercent` | number | `electric_torque_end_percent` | OK |
| `E_Horsepower` | number | `—` | CHYBÍ_V_KATALOGU |
| `E_Redline` | number | `electric_redline` | OK |
| `E_Torque` | number | `electric_torque` | OK |
| `E_Trans1` | number | `electric_trans1` | OK |
| `E_Trans2` | number | `electric_trans2` | OK |
| `Electric` | boolean | `electric_enabled` | OK |
| `Engine` | boolean | `engine_enabled` | OK |
| `EqPoint` | number | `eq_point` | OK |
| `FAnchorOffset` | table | `anchor_offset_f` | PŘEJMENOVÁN (dříve `AnchorOffset`) |
| `FCamber` | number | `—` | CHYBÍ_V_KATALOGU |
| `FCaster` | number | `—` | CHYBÍ_V_KATALOGU |
| `FCompressLim` | number | `compress_lim_f` | PŘEJMENOVÁN (dříve `CompressLim`) |
| `FDMult` | number | `final_drive_mult` | OK |
| `FDiffCoast` | number | `front_diff_coast` | OK |
| `FDiffLockThres` | number | `lock_thresh_f` | PŘEJMENOVÁN (dříve `LockThres`) |
| `FDiffPower` | number | `front_diff_power` | OK |
| `FDiffPreload` | number | `diff_preload_f` | PŘEJMENOVÁN (dříve `Preload`) |
| `FDiffSlipThres` | number | `slip_thresh_f` | PŘEJMENOVÁN (dříve `SlipThres`) |
| `FExtensionLim` | number | `extension_lim_f` | PŘEJMENOVÁN (dříve `ExtensionLim`) |
| `FGyroDamp` | number | `front_gyro_damp` | OK |
| `FGyroDampening` | number | `front_gyro_dampening` | OK |
| `FPreCompress` | number | `pre_compress_f` | PŘEJMENOVÁN (dříve `PreCompress`) |
| `FSpringOffset` | table | `—` | CHYBÍ_V_KATALOGU |
| `FSusAngle` | number | `sus_angle_f` | PŘEJMENOVÁN (dříve `SusAngle`) |
| `FSusDamping` | number | `damper_f` | PŘEJMENOVÁN (dříve `Damping`) |
| `FSusLength` | number | `sus_length_f` | PŘEJMENOVÁN (dříve `SusLength`) |
| `FSusStiffness` | number | `sus_stiffness_f` | PŘEJMENOVÁN (dříve `Stiffness`) |
| `FToe` | number | `—` | CHYBÍ_V_KATALOGU |
| `FWSteer` | string | `front_wheel_steer` | OK |
| `FWheelDensity` | number | `front_wheel_density` | OK |
| `FWsBoneAngle` | number | `—` | CHYBÍ_V_KATALOGU |
| `FWsBoneLen` | number | `front_wishbone_len` | OK |
| `FinalDrive` | number | `final_drive` | OK |
| `Flywheel` | number | `flywheel` | OK |
| `Horsepower` | number | `horsepower` | OK |
| `IdleRPM` | number | `idle_rpm` | OK |
| `IdleThrottle` | number | `idle_throttle` | OK |
| `InclineComp` | number | `incline_comp` | OK |
| `KickMult` | number | `—` | CHYBÍ_V_KATALOGU |
| `KickRPMThreshold` | number | `—` | CHYBÍ_V_KATALOGU |
| `KickSpeedThreshold` | number | `—` | CHYBÍ_V_KATALOGU |
| `LimitClutch` | boolean | `—` | CHYBÍ_V_KATALOGU |
| `LoadDelay` | number | `—` | CHYBÍ_V_KATALOGU |
| `LockToLock` | number | `lock_to_lock` | OK |
| `MSteerExp` | number | `mouse_steer_exp` | OK |
| `MinSteer` | number | `min_steer` | OK |
| `NeutralLimit` | boolean | `—` | CHYBÍ_V_KATALOGU |
| `NeutralRevRPM` | number | `—` | CHYBÍ_V_KATALOGU |
| `PBrakeBias` | number | `pbrake_bias` | PŘEJMENOVÁN (dříve `Bias(PBrake)?`) |
| `PBrakeForce` | number | `pbrake_force` | OK |
| `PeakRPM` | number | `peak_rpm` | OK |
| `PeakSharpness` | number | `peak_sharpness` | OK |
| `Peripherals` | table | `—` | CHYBÍ_V_KATALOGU |
| `RAnchorOffset` | table | `anchor_offset_r` | PŘEJMENOVÁN (dříve `AnchorOffset`) |
| `RCamber` | number | `—` | CHYBÍ_V_KATALOGU |
| `RCaster` | number | `—` | CHYBÍ_V_KATALOGU |
| `RCompressLim` | number | `compress_lim_r` | PŘEJMENOVÁN (dříve `CompressLim`) |
| `RDiffCoast` | number | `rear_diff_coast` | PŘEJMENOVÁN (dříve `RDiffCoast?`) |
| `RDiffLockThres` | number | `lock_thresh_r` | PŘEJMENOVÁN (dříve `LockThres`) |
| `RDiffPower` | number | `rear_diff_power` | PŘEJMENOVÁN (dříve `RDiffPower?`) |
| `RDiffPreload` | number | `diff_preload_r` | PŘEJMENOVÁN (dříve `Preload`) |
| `RDiffSlipThres` | number | `slip_thresh_r` | PŘEJMENOVÁN (dříve `SlipThres`) |
| `RExtensionLim` | number | `extension_lim_r` | PŘEJMENOVÁN (dříve `ExtensionLim`) |
| `RGyroDamp` | number | `rear_gyro_damp` | OK |
| `RGyroDampening` | number | `rear_gyro_dampening` | OK |
| `RPMEngage` | number | `rpm_engage` | OK |
| `RPreCompress` | number | `pre_compress_r` | PŘEJMENOVÁN (dříve `PreCompress`) |
| `RSpringOffset` | table | `—` | CHYBÍ_V_KATALOGU |
| `RSteerD` | number | `—` | CHYBÍ_V_KATALOGU |
| `RSteerDecay` | number | `—` | CHYBÍ_V_KATALOGU |
| `RSteerInner` | number | `—` | CHYBÍ_V_KATALOGU |
| `RSteerMaxTorque` | number | `—` | CHYBÍ_V_KATALOGU |
| `RSteerOuter` | number | `—` | CHYBÍ_V_KATALOGU |
| `RSteerP` | number | `—` | CHYBÍ_V_KATALOGU |
| `RSteerSpeed` | number | `—` | CHYBÍ_V_KATALOGU |
| `RSusAngle` | number | `sus_angle_r` | PŘEJMENOVÁN (dříve `SusAngle`) |
| `RSusDamping` | number | `damper_r` | PŘEJMENOVÁN (dříve `Damping`) |
| `RSusLength` | number | `sus_length_r` | PŘEJMENOVÁN (dříve `SusLength`) |
| `RSusStiffness` | number | `sus_stiffness_r` | PŘEJMENOVÁN (dříve `Stiffness`) |
| `RToe` | number | `—` | CHYBÍ_V_KATALOGU |
| `RWheelDensity` | number | `rear_wheel_density` | OK |
| `RWsBoneAngle` | number | `—` | CHYBÍ_V_KATALOGU |
| `RWsBoneLen` | number | `rear_wishbone_len` | OK |
| `Ratios` | table | `gear_ratios` | OK |
| `Redline` | number | `redline_rpm` | OK |
| `ReturnSpeed` | number | `return_speed` | OK |
| `RevAccel` | number | `rev_accel` | OK |
| `RevBounce` | number | `rev_bounce` | OK |
| `RevDecay` | number | `rev_decay` | OK |
| `S_Boost` | number | `—` | CHYBÍ_V_KATALOGU |
| `S_Sensitivity` | number | `supercharger_sensitivity` | OK |
| `ShiftDnTime` | number | `shift_down_time` | OK |
| `ShiftThrot` | number | `—` | CHYBÍ_V_KATALOGU |
| `ShiftUpTime` | number | `shift_up_time` | OK |
| `SpeedEngage` | number | `speed_engage` | OK |
| `Stall` | boolean | `stall_enabled` | OK |
| `SteerD` | number | `—` | CHYBÍ_V_KATALOGU |
| `SteerDecay` | number | `steer_decay` | OK |
| `SteerInner` | number | `—` | CHYBÍ_V_KATALOGU |
| `SteerMaxTorque` | number | `—` | CHYBÍ_V_KATALOGU |
| `SteerOuter` | number | `—` | CHYBÍ_V_KATALOGU |
| `SteerP` | number | `—` | CHYBÍ_V_KATALOGU |
| `SteerRatio` | number | `steer_ratio` | OK |
| `SteerSpeed` | number | `steer_speed` | OK |
| `SteeringType` | string | `steering_type` | OK |
| `Superchargers` | number | `supercharger_count` | OK |
| `SusCoilCount` | number | `—` | CHYBÍ_V_KATALOGU |
| `SusColor` | string | `—` | CHYBÍ_V_KATALOGU |
| `SusRadius` | number | `sus_radius` | OK |
| `SusThickness` | number | `—` | CHYBÍ_V_KATALOGU |
| `SusVisible` | boolean | `—` | CHYBÍ_V_KATALOGU |
| `SuspensionEnabled` | boolean | `—` | CHYBÍ_V_KATALOGU |
| `T2_BoostLag` | number | `turbo2_boost_lag` | OK |
| `TCSEnabled` | boolean | `—` | CHYBÍ_V_KATALOGU |
| `TCSGradient` | number | `tcs_gradient` | OK |
| `TCSLimit` | number | `tcs_limit_pct` | OK |
| `TCSThreshold` | number | `tcs_threshold_sps` | OK |
| `TQLock` | boolean | `tq_lock` | OK |
| `T_Boost` | number | `turbo_boost` | OK |
| `T_BoostLag` | number | `turbo_boost_lag` | OK |
| `ThrotAccel` | number | `throttle_accel` | OK |
| `ThrotDecel` | number | `throttle_decel` | OK |
| `TorqueVector` | number | `torque_vector` | OK |
| `TransModes` | table | `trans_modes` | OK |
| `Turbochargers` | number | `turbo_count` | OK |
| `WBVisible` | boolean | `—` | CHYBÍ_V_KATALOGU |
| `Weight` | number | `weight_lb` | OK |
| `WeightBSize` | table | `weight_box_size` | OK |
| `WeightDist` | number | `weight_dist_pct` | OK |

## 3. Opravené fantomy (19)

| Fantom (před F4.3) | Oprava | Kategorie | Poznámka |
|---|---|---|---|
| `Bias` | `BrakeBias` | MUTABLE_TUNE | priorita; hodnota 0.6 live-ověřena |
| `Damping` | `FSusDamping` + `RSusDamping` | MUTABLE_TUNE | kandidát 500/500 z auditu §8, PENDING |
| `Stiffness` | `FSusStiffness` + `RSusStiffness` | MUTABLE_TUNE | kandidát 20000/20000 z auditu §8, PENDING |
| `Preload` | `FDiffPreload` (20, PASS) + `RDiffPreload` (null, PENDING) | MUTABLE_TUNE | jen F doloženo §7; R odečíst ve Studiu |
| `SlipThres` | `FDiffSlipThres` + `RDiffSlipThres` + `CDiffSlipThres` | UNKNOWN | F/R/C varianty auditem nepopsány |
| `LockThres` | `FDiffLockThres` + `RDiffLockThres` + `CDiffLockThres` | UNKNOWN | viz SlipThres |
| `CompressLim` | `FCompressLim` + `RCompressLim` | UNKNOWN | jen odvozené Min 2.35 |
| `ExtensionLim` | `FExtensionLim` + `RExtensionLim` | UNKNOWN | jen odvozené Max 3.2 |
| `PreCompress` | `FPreCompress` + `RPreCompress` | UNKNOWN | jen odvozené Free 2.7 |
| `SusLength` | `FSusLength` + `RSusLength` | UNKNOWN | jen odvozené délky |
| `SusAngle` | `FSusAngle` + `RSusAngle` | UNKNOWN | 80 = neaktivní větev |
| `AnchorOffset` | `FAnchorOffset` + `RAnchorOffset` (`object`) | UNKNOWN | neaktivní větev |
| `RDiffPower?` | `RDiffPower` (=40) | UNKNOWN | název live-potvrzen; párování 40 odvozeno |
| `RDiffCoast?` | `RDiffCoast` (=30) | UNKNOWN | viz RDiffPower |
| `Bias(PBrake)?` | `PBrakeBias` (=0) | UNKNOWN | název+hodnota live-ověřeny → PASS |
| `StAxisOffset` | `tune_key: null` | UNKNOWN | klíč v live Tune chybí (chyba č.1 trvá) |
| `ElecRedline/ElecTransition2` | `tune_key: null` | READ_ONLY | názvy jen v Gauges kódu (chyba č.3) |
| `FWLgcyDensity` | `tune_key: null` | READ_ONLY | mrtvá non-PGS větev (chyba č.4) |
| `RWLgcyDensity` | `tune_key: null` | READ_ONLY | viz FWLgcyDensity |

Zásady: žádné vymyšlené `min`/`max` (chybí → `null`, kategorie zůstává);
formát 19 polí neměněn; F/R varianty jako samostatné záznamy;
`change_method: tune` u opravených MUTABLE záznamů (Tune-`require()` pre-spawn).

## 4. Zbývající UNKNOWN (37) s důvodem

| `id` | `tune_key` | důvod |
|---|---|---|
| `anchor_offset_f` | `FAnchorOffset` | Neaktivní procedurální větev. PENDING. RO-DŮVOD: hodnota v auditu neuvedena. |
| `anchor_offset_r` | `RAnchorOffset` | Neaktivní procedurální větev. PENDING. RO-DŮVOD: hodnota v auditu neuvedena. |
| `compress_lim_f` | `FCompressLim` | Vstup MinLength vzorce F; mimo FreeLength = trvalé dosednutí. RO-DŮVOD: audit zná jen odvozené MinLength 2.35. |
| `compress_lim_r` | `RCompressLim` | Vstup MinLength vzorce R; mimo FreeLength = trvalé dosednutí. RO-DŮVOD: audit zná jen odvozené MinLength 2.35. |
| `compression_ratio` | `CompressionRatio` | Vstup vzorce turba; hodnota PENDING. Vstup vzorce turba: HP_T z T_Boost × počet × CompressionRatio/10 / 7.5. RO-DŮVOD: Klíč v Tune auditem nepotvrzen (jen ve vzorci HP_T); hodnota neuvedena. |
| `electric_end_mult` | `EH_EndMult` | Neověřeno; mrtvá větev. RO-DŮVOD: Hodnota v auditu neuvedena (mrtvá větev). |
| `electric_end_percent` | `EH_EndPercent` | Neověřeno; mrtvá větev. RO-DŮVOD: Hodnota v auditu neuvedena (mrtvá větev). |
| `electric_front_mult` | `EH_FrontMult` | Neověřeno; mrtvá větev. RO-DŮVOD: Hodnota v auditu neuvedena (mrtvá větev). |
| `electric_redline` | `E_Redline` | Gauges čte ElecRedline místo E_Redline (chyba č.3). RO-DŮVOD: Hodnota v auditu neuvedena; Gauges čte ElecRedline (mismatch, viz limity). |
| `electric_torque` | `E_Torque` | Neověřeno; mrtvá větev. RO-DŮVOD: Hodnota v auditu neuvedena (mrtvá větev). |
| `electric_torque_end_mult` | `ET_EndMult` | Neověřeno; mrtvá větev. RO-DŮVOD: Hodnota v auditu neuvedena (mrtvá větev). |
| `electric_torque_end_percent` | `ET_EndPercent` | Neověřeno; mrtvá větev. RO-DŮVOD: Hodnota v auditu neuvedena (mrtvá větev). |
| `electric_trans1` | `E_Trans1` | Neověřeno; aktivní jen při Electric=true. Lichoběžník elektro-křivky. RO-DŮVOD: Hodnota v auditu neuvedena (Electric=false, mrtvá větev). |
| `electric_trans2` | `E_Trans2` | Gauges čte ElecTransition2 místo E_Trans2 (chyba č.3). RO-DŮVOD: Hodnota v auditu neuvedena; Gauges čte ElecTransition2 (mismatch, viz limity). |
| `extension_lim_f` | `FExtensionLim` | Vstup MaxLength vzorce F; mimo FreeLength = trvalé propnutí. RO-DŮVOD: audit zná jen odvozené MaxLength 3.2. |
| `extension_lim_r` | `RExtensionLim` | Vstup MaxLength vzorce R; mimo FreeLength = trvalé propnutí. RO-DŮVOD: audit zná jen odvozené MaxLength 3.2. |
| `front_wishbone_len` | `FWsBoneLen` | Custom větev v tomto kitu ji nepoužívá; hodnota nepřevzata. PENDING. Bez SuspensionGeometry by skript stavěl procedurální wishbone – v tomto kitu neaktivní. RO-DŮVOD: Hodnota 4 patří procedurální (neaktivní) větvi; custo |
| `lock_thresh_f` | `FDiffLockThres` | Podmíněný parametr difu F. PENDING. RO-DŮVOD: audit zná jen staré LockThres (ignorováno při DifferentialType=New); F/R/C varianty auditem nepopsány. |
| `lock_thresh_r` | `RDiffLockThres` | Podmíněný parametr difu R. PENDING. RO-DŮVOD: audit zná jen staré LockThres (ignorováno při DifferentialType=New); F/R/C varianty auditem nepopsány. |
| `lock_thresh_c` | `CDiffLockThres` | Podmíněný parametr difu C. PENDING. RO-DŮVOD: audit zná jen staré LockThres (ignorováno při DifferentialType=New); F/R/C varianty auditem nepopsány. |
| `pbrake_bias` | `PBrakeBias` | PBrake brzdí jen zadek (bias 0). Živá hodnota šablony 0 (ověřeno během F4.3). |
| `pre_compress_f` | `FPreCompress` | Vstup FreeLength vzorce F. PENDING. RO-DŮVOD: audit zná jen odvozené FreeLength 2.7. |
| `pre_compress_r` | `RPreCompress` | Vstup FreeLength vzorce R. PENDING. RO-DŮVOD: audit zná jen odvozené FreeLength 2.7. |
| `rear_diff_coast` | `RDiffCoast` | Váha násobiče zadku bez plynu. PENDING: párování 30↔coast odvozeno z paralelní struktury auditu. |
| `rear_diff_power` | `RDiffPower` | Váha násobiče zadku pod plynem; vysoký preload = nedotáčivost + odpor v rejdu. PENDING: párování 40↔power odvozeno z paralelní struktury auditu. |
| `rear_wishbone_len` | `RWsBoneLen` | Viz front_wishbone_len. PENDING. RO-DŮVOD: Viz front_wishbone_len – neaktivní větev. |
| `slip_thresh_f` | `FDiffSlipThres` | Podmíněný parametr difu F. PENDING. RO-DŮVOD: audit zná jen staré SlipThres (ignorováno při DifferentialType=New); F/R/C varianty auditem nepopsány. |
| `slip_thresh_r` | `RDiffSlipThres` | Podmíněný parametr difu R. PENDING. RO-DŮVOD: audit zná jen staré SlipThres (ignorováno při DifferentialType=New); F/R/C varianty auditem nepopsány. |
| `slip_thresh_c` | `CDiffSlipThres` | Podmíněný parametr difu C. PENDING. RO-DŮVOD: audit zná jen staré SlipThres (ignorováno při DifferentialType=New); F/R/C varianty auditem nepopsány. |
| `spring_color` | `None` | Nevymýšlím; PENDING Studio. Matice 'co lze měnit čím': Karoserie / barva pružin / MiscWeld / díly… RO-DŮVOD: Audit uvádí 'barva pružin' jako Tune-měnitelnou, ale název klíče ani hodnotu neuvádí – nevymýšlím. |
| `steer_axis_offset` | `None` | CHYBA č.1: CFrame.new(0,nil,0) → podezření na runtime error. PENDING Studio. Chyba kódu č. 1 – viz limits(). RO-DŮVOD: Klíč v Tune CHYBÍ, ale Initialize:171 ho čte (CFrame.new(0, nil, 0) → podezření na runtime error). Nu |
| `supercharger_sensitivity` | `S_Sensitivity` | Neověřeno; nutno odečíst z Tune ve Studiu (F4 PENDING). _SBoost z otáček × S_Sensitivity. RO-DŮVOD: Hodnota v auditu neuvedena – nevymýšlím, nutno odečíst z Tune ve Studiu. |
| `sus_angle_f` | `FSusAngle` | Custom větev parametr nepoužívá. PENDING. RO-DŮVOD: hodnota 80 patří neaktivní větvi – nepřevzata. |
| `sus_angle_r` | `RSusAngle` | Custom větev parametr nepoužívá. PENDING. RO-DŮVOD: hodnota 80 patří neaktivní větvi – nepřevzata. |
| `sus_length_f` | `FSusLength` | FreeLength=FSusLength+FPreCompress; Max=+FExtensionLim; Min=−FCompressLim. Limity mimo FreeLength = dosednutí/propnutí. RO-DŮVOD: audit zná jen odvozené Free 2.7/Max 3.2/Min 2.35. |
| `sus_length_r` | `RSusLength` | FreeLength=RSusLength+RPreCompress; Max=+RExtensionLim; Min=−RCompressLim. Limity mimo FreeLength = dosednutí/propnutí. RO-DŮVOD: audit zná jen odvozené Free 2.7/Max 3.2/Min 2.35. |
| `tq_lock` | `TQLock` | PENDING; jen pro TorqueConverter větev. RO-DŮVOD: Hodnota v auditu neuvedena (parametr měniče). |

## 5. Poznámky k CHYBÍ_V_KATALOGU (78)

Mimo rozsah Agenta R (jen fantomy). Patří Agentu A/B: zejména
`FCamber/RCamber`, `FCaster/RCaster`, `FToe/RToe`, `F/RSteer*` (řízení),
`ClutchMode/Type`, `S_Boost`, `ShiftThrot`, `SusColor/CoilCount/Thickness/Visible`,
`TCSEnabled`, `AutoFlip/Start`, přepínače `NeutralLimit/LimitClutch`,
tabulky `Controls/Peripherals/FSpringOffset/RSpringOffset/FAnchorOffset/RAnchorOffset`.


## 6. Akceptace – raw výstupy (Agent R, 2026-11-17)

- `python3 src/Chassis/catalog/loader.py --selftest` → exit 0, `SELFTEST OK`
  (`n_records: 138`, kategorie 82/14/2/3/37, `n_pending_studio: 43`).
- `python3 src/Chassis/adapters/achassis_v1.py` → exit 0, `SELFTEST OK`
  (measured/script-coded/unknown zastoupeny; `Horsepower` 200 apply OK;
  `Drag` i `StAxisOffset` rejected s důvodem).
- Diff-kontrola (python, ekvivalent node-skriptu — `node` v prostředí není):
  `FANTOMU: 0 []`, `MUTABLE: 82, vsechny-live: True`.
- `python3 tests/run_all.py` (H suite): `behu=141 PASS=124 FAIL=10 ERROR=3 PENDING=4`,
  `VYSLEDEK: FAIL`. Všech 13 selhání = zastaralé aserce v testech jiných agentů
  (pevné `125`/`79`/`27`/`31`, klíče `Bias`/`Preload`/`FWLgcyDensity`,
  prostor `[Bias, CurveMult, FDiffCoast, FDiffPower, Preload, TorqueVector, WeightDist]`)
  v `tests/test_f4_mapping.py`, `tests/test_f4_integration.py`,
  `tests/test_f4_optimizer_effect.py` — tyto soubory Agent R nevlastní a needituje.
  Seznam: `test_f4_01_uplnost_125_a_19_poli`, `test_f4_01_kategorie_pocty`,
  `test_f4_03_unknown_zustava_unknown`, `test_f4_04_overene_tune_klice_spot_check_12`,
  `test_f4_04_readonly_chranena`, `test_f4_08_realny_katalog_prostor_sedm_klicu`,
  `test_f4_09_backend_caps_ze_simu_a_prostor_bez_peak_torque`,
  `test_retezec_map_config_az_adapter`, `test_f4_11_neoverene_hodnoty_se_neaplikuji`,
  `test_f4_12_selftesty_zelene`, `test_chain_vehicleconfig_to_testresult`,
  `test_brakes_bias_change_moves_stopping_distance`,
  `test_prostor_bias_uvnitr_peak_torque_venku`.
  K nápravě vlastníkem testů po vlně 1 (koordinátor).
- Git operace: žádné. rbxm: nesaháno. Změněné soubory pouze vlastněné (viz §7).

## 7. Změněné soubory (pouze vlastněné)

- `src/Chassis/catalog/parameters.json` (125 → 138 záznamů; 19 fantomů opraveno)
- `src/Chassis/catalog/loader.py` (`EXPECTED_COUNT` 125 → 138)
- `src/Chassis/adapters/achassis_v1.py` (tune_key sladěny s live; 138 parametrů)
- `testgame/src/ServerScriptService/AutoEngineer/VehicleManager.lua`
  (MUTABLE set 79 → 82, pouze live klíče; DENY důvody aktualizovány)
- `reports/F43-LIVE-DIFF.md` (tento report)
- `docs/A-CHASSIS-PARAMETER-CATALOG.md` (pouze §3 fantomová sekce)
- `docs/MAPPING.md` (pouze Bias/F-R řádky §6.5, §6.8, §7 bias/tuhost)

