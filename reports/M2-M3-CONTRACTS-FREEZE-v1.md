# Zmrazené datové kontrakty M2/M3 v1 (2026-11-19, větev feat/m2-m3-geometry)

Koordinátor zmrazil před vlnou 1. Změna jen novou verzí se zdůvodněním.
Variantní korekce: cíl = EUROPEAN FACTORY STANDARD SPECIFICATION
(rozhodnutí uživatele 2026-11-19); hlavička příkazu „bez Performance Packu"
je zastaralá US logika a neplatí. Větve agentů sloučeny do jedné
integrační větve s disjunktním vlastnictvím souborů (praktická náhrada §14).

## inspection_report.json (M2, producent Agent B)

`{report_id, vehicle_id, source_file, source_sha256, parser_version,
code_version, wheels: [{designation, instance_id, class_name, center_studs:
{x,y,z}, size_studs: {x,y,z}, shape, status, reason}],
axles: {front: {wheel_L, wheel_R, track_studs}, rear: {...}},
wheelbase_studs, tire_diameters_studs: {FL,FR,RL,RR},
coordinate_frame: {x: "...", y: "...", z: "...", verified_in_studio: bool},
method, warnings[], overall_status: GEOMETRY_OK | UNKNOWN | BLOCKED}`.
Vše studs; status povinný u každého měření.

## scale_calibration.json (M2, producent Agent C)

`{vehicle_id, inspection_ref, references: [{param, value_si, unit, source,
status}], measurements_studs: {wheelbase, track_f, track_r, tire_d_f, tire_d_r},
estimates: [{param, studs_per_meter}], deviations_pct, uncertainty,
overall_status: VERIFIED | ESTIMATED | UNKNOWN | BLOCKED, blocked_reason}`.
Méně než 2 nezávislé reference → BLOCKED. Jednotky SI + studs.

## geometry_target.json (M3, producent Agent E — až po bráně)

`{vehicle_id, scale_ref, wheelbase_studs, track_f_studs, track_r_studs,
tire_d_f_studs, tire_d_r_studs, wheel_centers_studs: {FL,FR,RL,RR},
units: "studs", sources[], status_per_value}`.

## geometry_diff.json (M3 — až po bráně)

`[{param, source_value, source_unit, target_value, target_unit, delta,
method, status, source_ref}]`. Při BLOCKED vstupu M2 → celý report BLOCKED.
