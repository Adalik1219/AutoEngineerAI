# Agent C — Studio a Mustang vstupy / lidské blokace

**Větev:** `feat/m2-m3-geometry` · **HEAD:** `9803db37970b940c3ceb0ef15804834ea0a99c`
**Datum:** 2026-11-19 · **Jazyk:** čeština · **Režim:** pouze čtení, žádný kód neměněn, žádné měření nepředstíráno
**Podklady:** `reports/STUDIO_GROUND_TRUTH.md`, `reports/STUDIO_RUNTIME.md`, `docs/VEHICLE-SPECIFICATIONS.md`, `docs/IMPLEMENTATION_ROADMAP.md` (M2, M3), `docs/ACCEPTANCE_CRITERIA.md`, `docs/HYBRID_WORKFLOW.md`

---

## 1. Co současný ground-truth POTVRZUJE (JeepTemplate, Edit, read-only)

Zdroj: `reports/STUDIO_GROUND_TRUTH.md` (stav DONE, 2026-11-19, session read-only) + `reports/STUDIO_RUNTIME.md` (Edit, read-only).

| # | Fakt | Hodnota / stav |
|---|---|---|
| 1 | Model a kola | `ServerStorage.VehicleTemplates.JeepTemplate.Wheels` (Model), 4 děti FL/FR/RL/RR, každé Part + 6 dětí, 48 potomků |
| 2 | Parser ID kol | FL=3 / FR=52 / RL=101 / RR=150 (Model `Wheels` id 2) |
| 3 | Tvar všech 4 kol | `Enum.PartType.Ball` — shoda s parserem `Ball` |
| 4 | Velikost všech 4 kol | `2.700000047683716³` (float32 reprezentace 2.7) — shoda s parserem `Ball 2.7³` |
| 5 | Rozchod (track, \|FL.x − FR.x\|) | **5.99066162109375** studs (zadní pár 5.99072265625, konzistentní) — shoda s parserem `≈5.99` |
| 6 | Rozvor (wheelbase, \|FL.z − RL.z\|) | **10.522796630859375** studs (pravý pár 10.52276611328125, konzistentní) — shoda s parserem `≈10.52` |
| 7 | Výška Y všech 4 kol | identická `23.622142791748047` |
| 8 | Shoda parseru | Size + Shape + rozchod + rozvor = **CONFIRMED s přesnými čísly, bez PENDING zbytku** |
| 9 | Hash pracovní kopie před/po | `dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf` před = po (nezměněna, read-only session); ověřeno 2026-11-19 i v této úloze — `assets/chassis-original/chasis-work-copy.rbxm` a `testgame/src/ServerStorage/VehicleTemplates/JeepTemplate.rbxm` mají **stejný hash** |
| 10 | Režim Studia | **Edit**, instance `ae_test.rbxlx`; Rojo serve `localhost:34872`, serverVersion `7.7.1`, projekt `AutoEngineerTestGame`; Studio verze `0.748.0.7481526` (`return version()`) |
| 11 | Metoda | pouze `search_game_tree`, `inspect_instance`, `script_read` (+ `execute_luau("return version()")`); **žádný apply, žádný Play** |
| 12 | Rojo sync | OK — `VehicleManager.lua` 802 řádků shodně disk vs. Studio (sync-anchor L802); mapování stromu dle `default.project.json` |
| 13 | A-Chassis Tune (čteno živě ze Studia, NENÍ parser-výstup) | `FSusStiffness/RSusStiffness = 20000`, `FSusDamping/RSusDamping = 500`, `SusLength 2.5 / PreCompress .2`, `ExtensionLim .7 / CompressLim .15`, `GyroDampening 50/50`, `SuspensionEnabled = true`; mapování na `SpringConstraint` v `Initialize` L261–274 a L344–357 |

## 2. Co ground-truth NEPOTVRZUJE (co NENÍ)

| # | Není | Důsledek |
|---|---|---|
| 1 | **Mustang kalibrace** — žádný Mustang RBXM v repozitáři neexistuje (viz §5), žádné Mustang rozměry ve Studiu neměřeny | `studs_per_meter` pro M3 **VERIFIED chybí**; kalibrace na JeepTemplate je BLOCKED (rozptyl 7,44 % > 5 % — viz ROADMAP M2 §13); M3 brána NEOTEVŘENA |
| 2 | **Runtime test** — Play se nikdy nespustil, žádná jízda, žádná telemetrie | Vše jízdní (T-ACC/T-BRK/T-STEER/T-REL/T-STAB) je PENDING; Dle ACCEPTANCE_CRITERIA G-06/G-07 a M7: L3 vyžaduje `environment.mode: roblox-runtime`, jinak to není runtime důkaz; Studio hodnoty Tune (§1 ř. 13) jsou **Studio-ověřené, ale runtime efekt neověřen** |
| 3 | **Měření M2.4–M2.8 nad rámec kol** | Kalibrační brána drží BLOCKED; nápravy/inventář/hmotnosti/Tune-parametry z parseru nejsou ground-truth kryty |
| 4 | **CFrame preset-tabulka** | Mimo M2 (follow-up); `unread-preset-N` se nikdy neodhaduje |

## 3. Blokující vstupy (souhrn pro koordinátora)

1. **Mustang RBXM v repozitáři CHYBÍ** — bez něj nelze M2.4–M2.10 pro Mustang ani M3 (viz §5 checklist k získání).
2. **VERIFIED `studs_per_meter` pro M3 chybí** — JeepTemplate výsledek BLOCKED (7,44 % > 5 %); M3 NOT READY trvá.
3. **Runtime (Play) měření chybí** — L3 testy (T-ACC-01, T-BRK-01, T-STEER-01/02, T-REL-01, T-STAB-01) bez `roblox-runtime` telemetrie; G-06/G-07.
4. **Opakovaná Studio ground-truth pro nový RBXM** — až bude Mustang RBXM, je třeba nové měření dle checklistu §4 (1× T-GEO-01/02 + hash před/po).

## 4. Praktický checklist pro nové Studio měření (člověk ve Studiu)

Předpoklad: měří se **nový RBXM** (typicky Mustang, až bude dodán). Postup je L2 (měření ve Studiu bez jízdy) dle ROADMAP M7 §11.

### 4.1 Příprava (před otevřením Studia)
- [ ] Zjistit přesnou cestu RBXM souboru v repu (např. `assets/<…>/<název>.rbxm`) a zapsat ji.
- [ ] Vyrobit **pracovní kopii** (`…-work-copy.rbxm`); **nikdy neměřit / neotevírat originál k zápisu**.
- [ ] Spočítat **SHA-256 pracovní kopie PŘED** (`sha256sum <kopie>`) a zapsat.
- [ ] Zapsat větev + HEAD (`git rev-parse --abbrev-ref HEAD`, `git rev-parse HEAD`).
- [ ] Zapsat verzi Studia (ve Studiu `return version()` přes command bar / MCP `execute_luau`) a verzi Rojo pluginu + serve portu.

### 4.2 Režim a sync
- [ ] Otevřít `ae_test.rbxlx` (nebo aktuální place) v režimu **Edit** — zapsat název place a režim (screenshot `get_studio_state` / status bar).
- [ ] Ověřit Rojo serve běží (`localhost:34872` / aktuální port, serverVersion, projectName) a zapsat.
- [ ] Ověřit Rojo sync: porovnat klíčový soubor disk vs. Studio (`VehicleManager.lua` řádky/head + sync-anchor) — shoda ANO/NE.
- [ ] Importovat **pouze pracovní kopii** RBXM do `ServerStorage` (ne do Workspace, nepřepisovat `JeepTemplate`); zapsat cílovou cestu (např. `ServerStorage.VehicleTemplates.<ModelName>`).

### 4.3 Objekty k naměření (každé kolo + model)
- [ ] Najít `Model:Wheels` (celá cesta) — pokud chybí → STOP, stav BLOCKED.
- [ ] Pro každé kolo FL/FR/RL/RR zapsat: celou cestu instance, ClassName, `Shape`, `Size` (X/Y/Z v **studs**, plná float přesnost), `CFrame` pozici (X/Y/Z v **studs**), `Orientation`/`Rotation`, `Anchored`, `CanCollide`, `Material`, `BrickColor`, počet dětí/potomků.
- [ ] Zapsat parser-ID kol (INST id z `rbxm_parser.py`), pokud je známé — pro párování parser ↔ Studio.
- [ ] Naměřit též: `SuspensionGeometry`, `WheelFixed`/`SuspensionFixed` přítomnost (ANO/NE), `CylinderMesh`, `OriginalSize` — ANO/NE + hodnoty.
- [ ] Zapsat Y-konzistenci všech 4 kol (shodné / rozdílné + čísla).

### 4.4 Výpočty (jednotky: studs, 6+ desetinných míst)
- [ ] Rozchod přední = \|FL.x − FR.x\|; rozchod zadní = \|RL.x − RR.x\|.
- [ ] Rozvor levý = \|FL.z − RL.z\|; rozvor pravý = \|FR.z − RR.z\|.
- [ ] Průměr kola = `Size.x` největšího hnacího kola (dle A-CHASSIS-AUDIT pravidla; křížová kontrola vs. `wDia`).
- [ ] Zapsat všechny 4 hodnoty + rozdíl párů (konzistence ANO/NE).

### 4.5 Důkazy a uložení
- [ ] **Screenshoty**: Explorer strom `Model:Wheels` + FL/FR/RL/RR; Properties panel každého kola (Size/CFrame/Shape); `get_studio_state` (Edit); Rojo panel (Connected).
- [ ] **Exporty**: `inspect_instance` výpis každého kola (JSON/text) přiložit k reportu; `version()` výstup.
- [ ] **Hash pracovní kopie PO** (`sha256sum`) — musí se rovnat hashi PŘED (G-01); při neshodě STOP a hlásit.
- [ ] Place **neukládat přes originál**; při dialogu „script changes while playing" (pokud by se Play omylem spustil) odpovědět **No**.
- [ ] Výsledek zapsat do `reports/STUDIO_GROUND_TRUTH_<model>_<datum>.md` ve struktuře šablony §6 (pole NEVYPLNĚNÁ = prázdná, ne odhadnutá).

## 5. Checklist pro získání Mustang RBXM — V REPOZITÁŘI CHYBÍ

**Výslovně: Mustang RBXM v repozitáři NENÍ.** Nalezené RBXM soubory (2026-11-19, tato úloha):

- `assets/chassis-original/chasis-work-copy.rbxm` (sha256 `dc8747e0…c1fefdf`)
- `testgame/src/ServerStorage/VehicleTemplates/JeepTemplate.rbxm` (stejný hash `dc8747e0…c1fefdf` — kopie téhož JeepTemplate)

Žádný soubor `*mustang*.rbxm` / `*Mustang*.rbxm` neexistuje; žádný obsahový odkaz „mustang RBXM" v `.md` není (pouze profil JSON `vehicle-data/references/ford-mustang-gt-2024-eu-manual-standard.json`, což je datový profil, ne 3D model).

K odblokování M2.4–M2.10 / M3 je třeba (člověk dodá):

- [ ] **Soubor**: A-Chassis kompatibilní Mustang GT 2024 EU Fastback model jako `.rbxm` ( Muzem být i generický Mustang-like A-Chassis model, ale pak zapsat, že není 1:1 EU GT).
- [ ] **Umístění**: `assets/mustang-gt-2024-eu/<název>.rbxm` (originál, read-only) + pracovní kopie `…-work-copy.rbxm`.
- [ ] **Hash**: SHA-256 originálu + pracovní kopie zapsat při dodání.
- [ ] **Původ a licence**: zdroj (URL / autor / self-made), verze A-Chassis, datum stažení/vytvoření — zapsat (provenance pro M1 `source_type`).
- [ ] **Struktura**: obsahuje `Model:Wheels` + přesně 4 kola FL/FR/RL/RR tvaru Ball? (ANO/NE — pokud NE, M2 pravidlo konjunkce selže → UNKNOWN/BLOCKED).
- [ ] **Potvrzení**: kdo dodal, kdy, na jaké větvi commitnuto.
- [ ] Po dodání: spustit checklist §4 (Studio ground-truth) + strojový `rbxm_parser.py` + `scale_calibration.py` proti profilu `ford-mustang-gt-2024-eu-manual-standard.json`.

## 6. Šablona ground-truth záznamu (NEVYPLNĚNÁ pole nechat prázdná / null)

Markdown šablona pro nový report (`reports/STUDIO_GROUND_TRUTH_<model>_<RRRR-MM-DD>.md`):

```markdown
# STUDIO GROUND TRUTH — <název modelu>
> Status: **PENDING** — šablona, NEVYPLNĚNO.

| Meta | Hodnota |
|---|---|
| Branch |  |
| HEAD |  |
| Studio instance |  |
| Studio verze (`return version()`) |  |
| Rojo serve (port / serverVersion / projekt) |  |
| Rojo sync OK? |  |
| Soubor (pracovní kopie, nikdy originál) |  |
| SHA-256 (před) |  |
| SHA-256 (po) |  |
| Hash shodný (G-01)? |  |
| Parser reference (Model id; kola id) |  |
| Datum |  |
| Měřil |  |
| Režim (Edit / Play) | Edit |

## Kola (inspect_instance, jednotky: studs)
| Wheel | Parser id | Size X | Size Y | Size Z | CFrame X | CFrame Y | CFrame Z | Shape | Anchored | CanCollide | Material | Poznámka |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FL |  |  |  |  |  |  |  |  |  |  |  |  |
| FR |  |  |  |  |  |  |  |  |  |  |  |  |
| RL |  |  |  |  |  |  |  |  |  |  |  |  |
| RR |  |  |  |  |  |  |  |  |  |  |  |  |

## Odvozené rozměry (studs)
| Veličina | Vzorec | Hodnota | Konzistence párů |
|---|---|---|---|
| Rozchod přední | \|FL.x − FR.x\| |  |  |
| Rozchod zadní | \|RL.x − RR.x\| |  |  |
| Rozvor levý | \|FL.z − RL.z\| |  |  |
| Rozvor pravý | \|FR.z − RR.z\| |  |  |

## Parser srovnání
- Size: parser `` vs měřeno `` → **…**
- Shape: parser `` vs měřeno `` → **…**
- Rozchod: parser `` vs měřeno `` → **…**
- Rozvor: parser `` vs měřeno `` → **…**
- Verdikt: **…**

## Důkazy
- Screenshoty: …
- Exporty inspect_instance: …
- Poznámky (Workspace vs ServerStorage, Y-konzistence, …): …
```

JSON šablona (`inspection_ground_truth_<model>.json`, UNKNOWN = `null`, nic neodhadovat):

```json
{
  "model": null,
  "branch": null,
  "head": null,
  "date": null,
  "measured_by": null,
  "studio": { "instance": null, "version": null, "mode": "Edit" },
  "rojo": { "port": null, "serverVersion": null, "project": null, "in_sync": null },
  "rbxm": { "work_copy_path": null, "sha256_before": null, "sha256_after": null, "hash_match_g01": null },
  "wheels": {
    "FL": { "parser_id": null, "size": [null, null, null], "cframe_xyz": [null, null, null], "shape": null, "anchored": null, "can_collide": null, "material": null },
    "FR": { "parser_id": null, "size": [null, null, null], "cframe_xyz": [null, null, null], "shape": null, "anchored": null, "can_collide": null, "material": null },
    "RL": { "parser_id": null, "size": [null, null, null], "cframe_xyz": [null, null, null], "shape": null, "anchored": null, "can_collide": null, "material": null },
    "RR": { "parser_id": null, "size": [null, null, null], "cframe_xyz": [null, null, null], "shape": null, "anchored": null, "can_collide": null, "material": null }
  },
  "derived_studs": { "track_front": null, "track_rear": null, "wheelbase_left": null, "wheelbase_right": null },
  "parser_comparison": { "size": null, "shape": null, "track": null, "wheelbase": null, "verdict": null },
  "evidence": { "screenshots": [], "inspect_exports": [], "notes": null }
}
```

## 7. Původ každé reference (Ford dokumentace / Studio / Mustang RBXM / runtime test)

| Reference | Původ | Stav |
|---|---|---|
| Motor 5.0 Ti-VCT V8, 5 038 cm³, 328 kW/446 PS @ 7 250, 540 Nm @ 5 100 | **Ford dokumentace** [1]/[1b]/[2]/[3] (MUSTANG-SOURCE-CHECK POTVRZENO → SPEC VERIFIED) | VERIFIED (profil M1) |
| Rozvor 2 719 mm, rozchody 1 585 / 1 642 mm, rozměry karoserie, kola/pneu, převody 1–6, brzdy Brembo 390/355, 0–100 5,3 s, V-max 250 km/h | **Ford dokumentace** [1]/[1b]/[3] | VERIFIED (profil M1) |
| Stálý převod, momentová křivka (body), brzdový bias, rozložení hmotnosti + CG, Cd/plocha | **žádný zdroj — UNKNOWN** (v [1b]/[2]/[3] nepublikován; kandidáti převodu 3.15/3.55 bez přiřazení) | UNKNOWN, GUARD: nepoužívat |
| JeepTemplate kola Ball 2.7³, rozchod ≈5.9907, rozvor ≈10.5228, parser shoda, hash před/po | **Studio (Edit, read-only)** + RBXM pracovní kopie | DONE (ground-truth) |
| Tune hodnoty Stiffness 20000 / Damping 500 / délky / limity | **Studio (Edit, read-only čtení ModuleScriptu)** — NENÍ parser-výstup | Studio-ověřené; runtime efekt PENDING |
| Mustang rozměry ve studs, `studs_per_meter` VERIFIED | **Mustang RBXM + Studio** — CHYBÍ obojí | BLOCKED |
| Jízdní chování (akcelerace, brzdy, zatáčení, stabilita, T-ACC/T-BRK/… telemetrie) | **runtime test (Play)** — NESPUSŤENO | PENDING (L3 vyžaduje `roblox-runtime`) |
| Nominální průměry 686,6 / 702,6 mm z `D = 19·25,4 + 2·W·A/100` | **výpočet z Ford pneu-označení** (není měření ani zatížený průměr) | computed, není ground-truth |

## 8. Odpověď na zadání (stručně)

- **Mustang RBXM v repozitáři existuje? NE.** Jsou pouze 2 soubory se stejným hashem `dc8747e0…c1fefdf` (JeepTemplate / chasis-work-copy). Hledáno `*.rbxm` + `*mustang*` + obsahový grep — bez nálezu.
- **Blokující vstupy:** (1) chybějící Mustang RBXM, (2) chybějící VERIFIED `studs_per_meter` pro M3, (3) chybějící runtime (Play) telemetrie pro L3, (4) chybějící nové Studio měření pro nový RBXM dle §4.
- Tento soubor je jediný zápis úlohy; kód neměněn, PR #2 / main / merge nedotčeny.
