# STUDIO GROUND TRUTH — Chassis Wheels

> Status: **DONE** — measured live in Roblox Studio (read-only), 2026-11-19.

| Meta | Value |
|---|---|
| Branch | `feat/m1-m2-foundation` |
| HEAD | `6cedbe1` (PR #2 OPEN, NEMERGOVAT) |
| Studio instance | `ae_test.rbxlx`, mode **Edit** |
| Studio version | `0.748.0.7481526` (`version()`) |
| Rojo serve | `localhost:34872`, serverVersion `7.7.1`, project `AutoEngineerTestGame` |
| File to open | `assets/chassis-original/chasis-work-copy.rbxm` (**work copy only, never the original**) |
| SHA-256 (before) | `dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf` |
| SHA-256 (after) | `dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf` (unchanged — read-only session) |
| Parser reference | Model `Wheels` id 2; wheels FL=3 / FR=52 / RL=101 / RR=150; Ball 2.7³ |
| Date | 2026-11-19 |
| Measured by | Studio & Rojo Runtime Engineer (MCP, read-only) |
| Status | **DONE** |

## (1) Studio instance (read-only)

- `list_roblox_studios` → 2 instances: one `Unavailable` (no place open), one `ae_test.rbxlx` / mode `Edit`.
- `get_studio_state` → Current Studio Mode: Edit; Available DataModels: Edit.
- No apply, no play — inspection only.

## (2) Rojo sync check — OK (in sync)

- Disk: `testgame/src/ServerScriptService/AutoEngineer/VehicleManager.lua` — 802 lines, 31977 bytes, last line 802 = `-- F6 sync-anchor: plny re-sync po castecne aplikaci Rojo pluginem (chimera 5e003fe+823585d).`
- Studio: `game.ServerScriptService.AutoEngineer.VehicleManager` via `script_read` — lines 1–802 identical (same header, MUTABLE_TUNE set, `return VehicleManager` L801 + sync-anchor L802); L803 is only the trailing-newline artifact.
- Tree mapping matches `default.project.json`: `ServerScriptService.AutoEngineer`, `Workspace.TestTrack/TestSpawn/TestEnvironment` ← `src/Workspace/*.rbxmx`, `ServerStorage.VehicleTemplates` present.
- Verdict: **Rojo sync OK** — synced script content matches disk.

## (3) Wheels measurement (read-only `inspect_instance`)

Source: `ServerStorage.VehicleTemplates.JeepTemplate.Wheels` (Model, 4 children FL/FR/RL/RR, each a Part with 6 children and 48 descendants). All four: ClassName Part, Anchored=true, CanCollide=true, Material Rubber, BrickColor Black, Transparency 0, children CylinderMesh + SuspensionGeometry + WheelFixed + SuspensionFixed + Parts + OriginalSize.

| Wheel | Parser id | Size X | Size Y | Size Z | CFrame Pos X | CFrame Pos Y | CFrame Pos Z | Shape | Orientation notes |
|---|---|---|---|---|---|---|---|---|---|
| FL | 3 | 2.700000047683716 | 2.700000047683716 | 2.700000047683716 | -45.187889099121094 | 23.622142791748047 | -203.2503662109375 | Enum.PartType.Ball | Rotation 90, 0, -90 |
| FR | 52 | 2.700000047683716 | 2.700000047683716 | 2.700000047683716 | -51.178550720214844 | 23.622142791748047 | -203.25039672851562 | Enum.PartType.Ball | Rotation 90, 0, 90 |
| RL | 101 | 2.700000047683716 | 2.700000047683716 | 2.700000047683716 | -45.18785858154297 | 23.622142791748047 | -213.77316284179688 | Enum.PartType.Ball | Rotation 90, 0, -90 |
| RR | 150 | 2.700000047683716 | 2.700000047683716 | 2.700000047683716 | -51.17858123779297 | 23.622142791748047 | -213.77316284179688 | Enum.PartType.Ball | Rotation 90, 0, 90 |

## (4) Parser comparison — POTVRZENO

- Size: parser `Ball 2.7³` vs measured `2.700000047683716³` → **match** (float32 2.7).
- Shape: parser `Ball` vs measured `Enum.PartType.Ball` (all 4) → **match**.
- Rozchod (track, |FL.x − FR.x|): `|-45.187889099121094 − (-51.178550720214844)|` = **5.99066162109375** → parser `≈5.99` **match** (rear pair 5.99072265625, consistent).
- Rozvor (wheelbase, |FL.z − RL.z|): `|-203.2503662109375 − (-213.77316284179688)|` = **10.522796630859375** → parser `≈10.52` **match** (right pair 10.52276611328125, consistent).
- Y identical on all 4: 23.622142791748047.

Verdict: **parser claims CONFIRMED with exact numbers above — no PENDING remainder.**

## Notes

- Wheels live in the live `JeepTemplate` in `ServerStorage.VehicleTemplates` (Rojo-synced template), NOT in Workspace — keyword search `wheel` under Workspace returned no match. Work-copy rbxm on disk untouched (hash identical before/after).
- Session was strictly read-only: `search_game_tree`, `inspect_instance`, `script_read`, `execute_luau("return version()")` only. No apply, no play.
