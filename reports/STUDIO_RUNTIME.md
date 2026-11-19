# STUDIO RUNTIME — A-Chassis Tune + Initialize (read-only)

> Status: **OVĚŘENO (Edit, read-only)** — 2026-11-19. Play-věci níže jako **PENDING** s postupem pro uživatele. Nic se nespouštělo, nic se nezapisovalo.

| Meta | Hodnota |
|---|---|
| Větev | `feat/m1-m2-foundation` |
| HEAD | `ff4a9d6` (PR #2 OPEN, NEMERGOVAT) |
| Studio instance | `ae_test.rbxlx`, režim **Edit** |
| Studio verze | `0.748.0.7481526` (`return version()`) |
| Rojo serve | `localhost:34872`, serverVersion `7.7.1`, project `AutoEngineerTestGame` |
| Pracovní kopie rbxm | `assets/chassis-original/chasis-work-copy.rbxm`, sha256 `dc8747e0…c1fefdf` (nezměněna — kontrolováno před/po) |
| Datum | 2026-11-19 |
| Metoda | pouze `search_game_tree`, `inspect_instance`, `script_read`, `script_grep`, `execute_luau("return version()")` |

## (1) Rojo sync — OK (v syncu)

- Serve běží: `curl 127.0.0.1:34872/api/rojo` → `serverVersion 7.7.1`, `projectName AutoEngineerTestGame`. (Pozn.: v PluginGui je vidět i `Rojo 7.2.1` panel vedle `Rojo 7.7.1` — minor mismatch panelů, sync níže přesto sedí.)
- Disk `testgame/src/ServerScriptService/AutoEngineer/VehicleManager.lua` — 802 řádků; pracovní strom čistý (`git diff HEAD -- testgame/` prázdný).
- Studio `game.ServerScriptService.AutoEngineer.VehicleManager` via `script_read` L790–802: končí `return VehicleManager` (L801) + `-- F6 sync-anchor: plny re-sync … (chimera 5e003fe+823585d).` (L802) — shodné s diskem.
- Mapování stromu odpovídá `default.project.json`: `ServerScriptService.AutoEngineer`, `ReplicatedStorage.AutoEngineer`, `ServerStorage.VehicleTemplates`, `Workspace.TestTrack/TestSpawn/TestEnvironment`.
- Šablona `JeepTemplate` (vč. `A-Chassis Tune` + `Initialize`) žije v binárním snapshotu `testgame/src/ServerStorage/VehicleTemplates/JeepTemplate.rbxm` na disku — není to live-syncovaný `.lua`, takže "sync" pro ni znamená commitnutý binární snapshot, ne řádkový diff.
- Verdikt: **Rojo sync OK.**

## (2) A-Chassis Tune + Initialize — PŘEČTENO (read-only)

Cesta: `ServerStorage.VehicleTemplates.JeepTemplate.A-Chassis Tune` (ModuleScript, 4 děti: `Plugins`, `A-Chassis Interface`, `README`, `Initialize`; 216 potomků celkem).

Suspension Tune (celý `script_read`, L49–70):

| Klíč | Hodnota F | Hodnota R | Komentář ve zdroji |
|---|---|---|---|
| `SusStiffness` | `Tune.FSusStiffness = 20000` | `Tune.RSusStiffness = 20000` | Spring Force |
| `SusDamping` | `Tune.FSusDamping = 500` | `Tune.RSusDamping = 500` | Spring Damping |
| `SusLength` / `PreCompress` | 2.5 / .2 | 2.5 / .2 | Base spring height / adds to base (studs) |
| `ExtensionLim` / `CompressLim` | .7 / .15 | .7 / .15 | Max Extension / Compression Travel (studs) |
| `SuspensionEnabled` | `true` | — | L50 |
| `GyroDampening` | F 50 | R 50 | Suspension Gyro Dampening |

`Initialize` (Script, dítě `A-Chassis Tune` + `MiscWeld` ModuleScript): mapování na `SpringConstraint` potvrzeno na dvou místech — L261–274 (první větev) a L344–357 (druhá větev), identická logika:

- `v.Name == "FL"/"FR"/"F"` → `sp.Damping = _Tune.FSusDamping`, `sp.Stiffness = _Tune.FSusStiffness`, `FreeLength = FSusLength+FPreCompress`, `MaxLength = FSusLength+FExtensionLim`, `MinLength = FSusLength-FCompressLim`; jinak R-varianty. `g.D = _Tune.F/RGyroDampening`.
- Konzistentní s `VehicleManager.lua` MUTABLE_TUNE: `FSusStiffness/RSusStiffness`, `FSusDamping/RSusDamping = true`; generické `Stiffness`/`Damping` jsou PREJMENOVANO-aliasy (F4.3 live Tune).

## (3) Co lze ověřit jen v Play — PENDING (nespouštěno)

Bez pokynu se Play nespouští. Až uživatel dá pokyn, postup:

1. V `ae_test.rbxlx` (Edit) zkontrolovat Rojo plugin Connected na portu 34872; Ctrl+S (uložit place).
2. Play (F5 / Solo). Čekat ≥ `Tune.LoadDelay` = **3.0 s** + spawn (celkem ~10–15 s).
3. Ověřit, že `Initialize` doběhl: ve stromu klonu (jméno dle `VehicleManager.DeployVehicle`, typicky SLOT) musí existovat weight brick + steering arms; `A-Chassis Interface.Values` (Throttle/Brake/SteerC/RPM…) přibývají za běhu.
4. Ověřit chování: sednout do `DriveSeat`, šipky/WASD — pružiny drží světlost, tlumení bez trvalého houpání; hodnoty `SpringConstraint.Stiffness/Damping` na klonu = 20000/500 (F i R).
5. Stop Play (Shift+F5). Pozor na dialog "script changes while playing" — odpovědět **No** (Rojo re-push šum), nikdy Always Save.

## (4) Parser / audit — stav

- `reports/AUDIT-geometry.md` (P0/P1): float-dekódování (`_decode_float_lanes`, `_parse_cframe_array`) bez `isfinite` brány; size/CFrame/pozice/matice `trusted=False`; důvod `float_decode_unverified` — rozměry a středy "přečteny, ale bez Studio ground-truth nedůvěryhodné ke kalibraci".
- `reports/STUDIO_GROUND_TRUTH.md` (DONE, 2026-11-19, stejná session-metoda): kola Ball 2.7³, rozchod ≈5.99, rozvor ≈10.52 — **parser claims CONFIRMED s přesnými čísly, bez PENDING zbytku**. Auditní výhrada je tím pro rozměry kol překonána (ground-truth existuje).
- Hodnoty Stiffness/Damping v §2 **nejsou parser-výstup** — jsou přečteny živě z Tune ModuleScriptu ve Studiu, takže se na ně parserová float/CFrame výhrada nevztahuje; jsou Studio-ověřené. Co zůstává neověřené: jejich **runtime efekt** (viz §3 PENDING).
