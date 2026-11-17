# GAME-ARCHITECTURE — testovací place AutoEngineerAI (FÁZE 9)

**Vlastník (Agent A – Game Environment):** `testgame/src/Workspace/**`,
`testgame/src/ServerStorage/VehicleTemplates/JeepTemplate.rbxm`,
tento dokument. Jazyk: česky; identifikátory anglicky.

Značení: **[F]** = ověřený fakt (vlastní měření/čtení souboru),
**[P]** = předpoklad, **[N]** = neznámé s postupem ověření.

Zdroje: `docs/AGENT-RULES.md`, `docs/A-CHASSIS-AUDIT.md` (§3 hierarchie),
`docs/ROBLOX-RUNTIME.md`, `docs/TESTING-OPTIMIZATION.md` (§3 scénáře S1–S8),
`testgame/src/ReplicatedStorage/AutoEngineer/Shared/ScenarioDefinitions.lua`
(definice T01–T07, `SCENARIO_VERSION = "1.0.0"`).

---

## 1. Soubory a jejich role

| Soubor (abs. cesta) | Obsah | Konzument |
|---|---|---|
| `C:/.DATA/AutoEngineerAI/testgame/src/Workspace/TestTrack.rbxmx` | Model `TestTrack`: rovinka 1500 + brzdná zóna 200 (7 dílů) | B (project.json), C (harness spawn/waypointy) |
| `C:/.DATA/AutoEngineerAI/testgame/src/Workspace/TestSpawn.rbxmx` | Model `TestSpawn`: garáž 40×30 + `SpawnPad` (6 dílů) | C (spawn vozidla) |
| `C:/.DATA/AutoEngineerAI/testgame/src/Workspace/TestEnvironment.rbxmx` | Model `TestEnvironment`: skidpad-kruh, slalom, nerovnosti, 2 povrchy + split-mu (46 dílů) | C, D (waypointy), E (zóny měření) |
| `C:/.DATA/AutoEngineerAI/testgame/src/ServerStorage/VehicleTemplates/JeepTemplate.rbxm` | Šablona vozidla, prostá kopie work-copy (230 421 B) | C (`VehicleManager` klonuje do testu) |
| `C:/.DATA/AutoEngineerAI/testgame/docs/GAME-ARCHITECTURE.md` | Tento dokument | všichni |

**[F]** Všechny díly mapy: `Anchored = true`, `CanCollide = true`
(zapsáno v XML, ověřeno parse-skriptem). Opakovatelnost polohy je tím
dána geometrií souboru — žádné díly se za běhu nehýbou ani negenerují.
Seed nerovností je pevný geometrií (žádný generátor): T07 používá seed
107 dle `ScenarioDefinitions`, hrboly jsou identické pro každou variantu.

Formát `.rbxmx`: ručně psané minimální XML
(`roblox > Item class="Model" > Item class="Part"`),
vlastnosti: `Name`, `Anchored`, `size`, `CFrame` (pozice + rotace),
`Material` (číselný enum), `Color3` (0–1), `Shape`, `TopSurface/BottomSurface`.
**[F]** Všechny 3 soubory procházejí `python xml.etree parse` bez chyby.
Materiálové enumy dle Creator Hub: Asphalt=1376, Grass=1280,
Concrete=816, Plastic=256, SmoothPlastic=272, Neon=288.

---

## 2. Souřadnicový systém a konvence

- Jednotky: **studs**, osa **+X = směr jízdy** na rovinkách.
- Povrch vozovek má horní hranu v **y = 0** (střed 1-studs desky v y = −0.5).
- Spawn čelem k **+X** (otevřená strana garáže).
- Barvy jsou orientační; fyzikální friken nenastavuje geometrie —
  nastavuje ji harness (agent C) přes `CustomPhysicalProperties`
  (viz §5). To platí hlavně pro `WetPad` (vizuálně modrá).

---

## 3. TestTrack — rovinka + brzdná zóna (T01, T03; částečně T02)

Model `TestTrack`, jízdní pruh šířky 12 (z −6…6). **[F]** souřadnice z XML:

| Díl | Size (x,y,z) | Střed (x,y,z) | Materiál | Význam |
|---|---|---|---|---|
| `StraightLane` | 1500, 1, 12 | 750, −0.5, 0 | Asphalt | rovinka x 0…1500 |
| `BrakeZone` | 200, 1, 12 | 1600, −0.5, 0 | Concrete | brzdná zóna x 1500…1700 |
| `StartLine` | 2, 1.1, 12 | 2, −0.45, 0 | SmoothPlastic bílá | start (T01/T03) |
| `BrakeLine` | 2, 1.1, 12 | 1500, −0.45, 0 | Neon červená | začátek brzdění (T03) |
| `EndWall` | 4, 10, 16 | 1704, 5, 0 | Plastic tmavá | záchytná bariéra |
| `RailLeft` / `RailRight` | 1704, 2, 1 | 852, 1, ∓7 | Concrete | boční mantinely |

Celková délka: 1700 studs vozovky + bariéra. Start vozidla: x ≈ 10
(za `StartLine`, prostor pro `settle_s = 1.0 s`).

Vazba na scénáře: **T01** (800 studs) a **T03** (800 studs) se vejdou
s rezervou; brzdění z 100 studs/s má k dispozici 200 studs `BrakeZone`
+ nouzově mantinely a `EndWall`.

**[N] → otevřený bod pro koordinátora / agenta B:** T02 (`straight`,
3000 studs) se do 1500-studové rovinky **nevejde**. Tento soubor drží
zadaných 1500 m; možnosti: (a) v revizi prodloužit `StraightLane` na
3000, (b) T02 jako více kol / ovál, (c) snížit délku T02. Bez rozhodnutí
je T02 na této mapě neproveditelný — ostatních 6 scénářů je pokryto.

---

## 4. TestSpawn — garáž (spawn všech scénářů)

Model `TestSpawn`, garáž 40×30, otevřená strana +X:

| Díl | Size | Střed | Význam |
|---|---|---|---|
| `GarageFloor` | 40, 1, 30 | 0, −0.5, 0 | podlaha |
| `SpawnPad` | 8, 0.2, 8 | 0, 0.1, 0 | Neon zelená značka (střed spawn [P] doporučený bod; přesnou pozici/natáčení vozidla určuje `ScenarioRunner` agenta C) |
| `BackWall` | 1, 12, 30 | −19.5, 6, 0 | zadní stěna |
| `SideWallLeft/Right` | 40, 12, 1 | 0, 6, ∓14.5 | boční stěny |
| `Roof` | 40, 1, 30 | 0, 12, 0 | střecha (světlá výška 11.5) |

**[P]** Garáž je parkoviště/příprava, nikoli startovní čára — harness
vozidlo přemístí na start scénáře. Pokud agent C zvolí spawn přímo na
trati, garáž slouží jako záložní/neutralní pozice.

---

## 5. TestEnvironment — okruh, slalom, nerovnosti, povrchy (T04–T07)

Všechny zóny v jednom modelu, footprinty se **[F]** nepřekrývají
(ověřeno skriptem nad bounding-boxy). Přehled:

| Zóna | Díly | Rozsah (x / z) | Scénář |
|---|---|---|---|
| Skidpad-kruh | 16× `Ring_Seg_01–16` (42.02×1×12, tečna kruhu), `SkidInfield` (190×0.9×190 tráva, top −0.1), `SkidCenter` | kruh R=100, vozovka ±6 kolem poloměru (cca ±106) | **T04** |
| Slalom | `SlalomPad` (600×1×16, x 140…740) + 10× `Cone_01–10` (2×4×2, x = 180+i·60 → 180…720, z = 0) | x 140…740, z ±8 | **T06** (+T05 koridor) |
| Nerovnosti | `BumpRoad` (400×1×10, x 140…540, z 55…65) + 12× `Bump_01–12` (4×h×10, x = 160+i·32 → 160…512, h střídavě 0.5/1.0) | x 140…540, z 55…65 | **T07** |
| Suchý povrch | `DryPad` (200×1×60, x 750…950, z ±30), Asphalt | x 750…950 | T03b/T08 budoucn. |
| Mokrý povrch | `WetPad` (200×1×60, x 750…950, z 50…110), SmoothPlastic modrá | x 750…950 | S8a budoucn. |
| Split-mu | `SplitLeft_Grass` (100×1×30, x 1000…1100, z −30…0) + `SplitRight_Asphalt` (x 1000…1100, z 0…30) | x 1000…1100 | S8b budoucn. |

Konstrukční detaily:

- **Skidpad (T04):** 16 tětivových segmentů aproximuje kružnici R=100
  (tětiva 39.02 + přesah 3 → délka 42.02, rotace Ry(−θ−π/2), 6 desetinných
  míst). Šířka vozovky 12 pokrývá požadovaný koridor ±2 m s rezervou.
  Jízdní kruh R=100: `CFrame` středu (0, 0, 0); nájezd ze slalomové strany
  řeší `AutonomousDriver` (agent D).
- **Slalom (T06):** rozteč přesně **60** dle `ScenarioDefinitions`
  (`spacing_studs = 60`, 10 kuželů). Značky jsou bloky 2×4×2 (nikoli
  mesh kužele — záměrně jednoduché, placeholder; vizuální mesh může
  doplnit agent C mimo vlastněné soubory, geometrie tím není dotčena).
- **Nerovnosti (T07):** deterministické střídání výšek 0.5/1.0 nad
  vozovkou; délka pole 400 dle definice (`length_studs = 400`).
- **T05 (losí test):** nemá vlastní geometrii — jede se jako
  `straight_cones` koridor na `SlalomPad` (400 studs se vejde do
  600-studového padu); kužely ISO-rozestavení staví harness z definice
  replay-profilu, ne geometrie.
- **Povrchy:** `WetPad` a `SplitLeft_Grass` jsou pouze vizuálně odlišné
  materiály; **frikci musí nastavit harness** (`CustomPhysicalProperties`
  na dílech zóny před během, po běhu obnovit). Bez toho je S8/T-mokré
  varianty neplatné — **[N]** kalibrace frikčních koeficientů je na
  agentu C + FÁZI 9 měření.

---

## 6. JeepTemplate — integrita šablony

- **[F]** `JeepTemplate.rbxm` = bitová kopie
  `C:/.DATA/AutoEngineerAI/assets/chassis-original/chasis-work-copy.rbxm`:
  SHA-256 obou `dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf`
  (230 421 B). Originál `C:/Users/adamr/Downloads/chasis.rbxm` nebyl
  čten ani zapisován — kopie pochází z work-copy, jejíž shoda s originálem
  je doložena v `docs/A-CHASSIS-AUDIT.md` §1.
- Hierarchie šablony = A-Chassis 6C + Jeep karoserie + kolizní díly, viz
  audit §3 (kořen `0:Model`, `Misc`/`Wheels`/`Body`/`DriveSeat`/
  `JeepBodyVisual`/`CollisionParts`). Agent A obsah neanalyzuje ani nemění.
- Použití: `VehicleManager` (agent C) klonuje šablonu do testu; šablona
  sama se nikdy nemutuje (AGENT-RULES §6, ROBLOX-RUNTIME §4/§7).

---

## 7. Rozhraní pro ostatní agenty (nezávazné návrhy, rozhodnutí je jejich)

- **B (project.json):** očekávané `$path` mapování —
  `Workspace/TestTrack → src/Workspace/TestTrack.rbxmx`,
  `Workspace/TestSpawn → src/Workspace/TestSpawn.rbxmx`,
  `Workspace/TestEnvironment → src/Workspace/TestEnvironment.rbxmx`,
  `ServerStorage/VehicleTemplates/JeepTemplate → .../JeepTemplate.rbxm`.
  Aktuální `default.project.json` je stub bez `$path` (stav k 17. 11. 2026)
  — build projde, ale place je prázdný.
- **C (harness):** startovní pozice T01/T03 x≈10 na `TestTrack`;
  střed kruhu T04 (0,0,0) R=100; slalom T06 od x=180; hrboly T07 od x=160,
  z=60; friken `WetPad`/split zón před během.
- **D (driver):** waypoints: rovinka (0→1500, z=0), kruh R=100,
  slalom x 180…720.
- **E (telemetrie):** měřicí zóny = `BrakeLine` (vstup T03),
  cíl T06 x=720, konec hrbolů x=512.

---

## 8. Brány a raw výstupy

- `rojo build testgame/default.project.json` → **exit 0**
  (`Built project to ae_test.rbxl`, Rojo 7.7.1). Place je zatím stub bez
  `$path` (vlastnictví B) — build validuje projekt, ne obsah mapy.
- `stylua`: **N/A** — agent A nevlastní žádný `.lua` soubor.
- XML validace: `xml.etree parse` všech 3 `.rbxmx` → OK
  (TestTrack 7, TestSpawn 6, TestEnvironment 46 dílů).
- SHA: `sha256sum` work-copy i JeepTemplate =
  `dc8747…fefdf`, shoda s `A-CHASSIS-AUDIT.md` §1.
- `git -C C:/.DATA/RobloxSimulator status --short` → prázdné (nedotčeno).
  `testgame/` je untracked (`?? testgame/`) — očekáváno, commit je mimo
  rozsah agenta A (AGENT-RULES: žádné git operace).
- Originál `C:/Users/adamr/Downloads/chasis.rbxm` nedotčen (pouze
  `shutil.copyfile` z work-copy; žádný zápis do `Downloads/`).

---

## 9. Předpoklady, neznámé, rizika, další kroky

- **[P]** 1 stud ≈ 0.28 m se v mapě nikde nepřepočítává; rychlosti scénářů
  jsou ve studs/s dle `ScenarioDefinitions`. Převodní koeficient patří do
  manifestu běhu (ROBLOX-RUNTIME §6), ne do geometrie.
- **[N]** T02 délka (viz §3) — rozhodnutí koordinátora.
- **[N]** Frikční koeficienty povrchů — změří/zkalibruje FÁZE 9 (agent C+E).
- **[N]** Nájezd na skidpad-kruh a návrat (D); přesná spawn-orientace (C).
- Riziko: ručně psané XML nemá Studio-validaci do prvního otevření ve
  Studiu — doporučený další krok: agent B/C otevře place ve Studiu,
  zkontroluje vizuál a `Anchored` stav, případně nahlásí korekce mapy.
- Riziko: polygonalní kruh (16 segmentů, přesahy) má v místě spojů
  dvojitou tloušťku hran — pro T04 koridor ±2 to nevadí (spoje mimo
  ideální stopu lze projet středem segmentu), ale E by měl v telemetrii
  sledovat vertikální špičky v místech spojů.
