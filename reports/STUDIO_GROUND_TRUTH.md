# STUDIO GROUND TRUTH — Chassis Wheels

> Status: **PENDING** — no Roblox Studio access in this environment. Nothing below is invented; all measurement fields are empty until read in Studio.

| Meta | Value |
|---|---|
| Branch | `feat/m1-m2-foundation` |
| HEAD | `ff6f266` (PR #2 OPEN) |
| File to open | `assets/chassis-original/chasis-work-copy.rbxm` (**work copy only, never the original**) |
| SHA-256 (before) | `dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf` |
| SHA-256 (after) | _(fill after session — must be unchanged)_ |
| Parser reference | Model `Wheels` id 2; wheels FL=3 / FR=52 / RL=101 / RR=150; Ball 2.7³ |
| Studio version | _(fill, e.g. 0.xxx)_ |
| Date | _(fill YYYY-MM-DD)_ |
| Measured by | _(fill)_ |
| Status | **PENDING** |

## Checklist (exact steps)

1. [ ] Open Roblox Studio. **Do NOT open the original chassis file.**
2. [ ] Open/import ONLY `assets/chassis-original/chasis-work-copy.rbxm`.
3. [ ] Verify SHA-256 of the work copy before measuring: `dc8747e0…fedf`.
4. [ ] In Explorer, locate `Model: Wheels` (parser id 2).
5. [ ] For each wheel FL / FR / RL / RR (parser ids 3 / 52 / 101 / 150):
   - [ ] Select the Part, open Properties.
   - [ ] Read `Size` X, Y, Z exactly as shown.
   - [ ] Read `CFrame → Position` X, Y, Z exactly as shown.
   - [ ] Read `Shape` (expected `Ball`) and note any orientation.
   - [ ] Record into the table below — no rounding, no guessing.
6. [ ] Record Studio version (`Help → About`), date, and who measured.
7. [ ] Verify SHA-256 of the work copy after measuring (must match "before").
8. [ ] Save this file with status updated (PENDING → DONE only when all fields filled).

## Measurement table (4 wheels)

| Wheel | Parser id | Size X | Size Y | Size Z | CFrame Pos X | CFrame Pos Y | CFrame Pos Z | Shape | Orientation notes |
|---|---|---|---|---|---|---|---|---|---|
| FL | 3 | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| FR | 52 | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| RL | 101 | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| RR | 150 | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |

Parser hint (unverified until Studio confirms): Ball 2.7³.

## Notes

- _TBD — awaiting Studio session._
