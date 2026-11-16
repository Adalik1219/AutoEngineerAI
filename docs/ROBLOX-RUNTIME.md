# Roblox Runtime integrace – AutoEngineerAI

**Vlastněný soubor:** `docs/ROBLOX-RUNTIME.md`
**Fáze:** FÁZE 9 (Test Environment + Autonomous Driver), vazba na FÁZE 12 (validace) a FÁZE 13 (export)
**Jazyk:** česky. Identifikátory a kód anglicky.
**Zásada:** lokální matematická simulace ≠ důkaz. Důkaz je pouze měření v Roblox runtime.

---

## 1. Účel a rozsah

Tento dokument navrhuje, jak bude AutoEngineerAI bezpečně komunikovat s Roblox Studiem:

1. Načítat modely vozidel a vyvážet upravené varianty.
2. Provádět automatické úpravy (Instances, constraints, skripty, geometrie).
3. Spouštět fyzikální testy s automatickým řidičem.
4. Měřit pozici, rychlost, zrychlení a rotaci.
5. Sbírat telemetrii v opakovatelném prostředí.
6. Ukládat výsledky tak, aby každý výsledek šel přiřadit ke konkrétní variantě vozidla.

Mimo rozsah: návrh celkové architektury (`ARCHITECTURE.md`), audit A-Chassis (`A-CHASSIS-AUDIT.md`), testovací strategie a optimalizátor (`TESTING-OPTIMIZATION.md`). Tento dokument definuje pouze runtime vrstvu a její bezpečnostní hranice.

---

## 2. Požadavky na runtime vrstvu

| ID | Požadavek | Zdůvodnění |
|----|-----------|------------|
| R1 | Testy běží ve skutečném Roblox physics enginu, ne v aproximaci | PROJECT-PLAN §5.14, §5.10 |
| R2 | Každý test je opakovatelný v definované toleranci | PROJECT-PLAN §5.11 |
| R3 | Každá změna vozidla je verzovaná a vratná | PROJECT-PLAN §2, §5.8 |
| R4 | Originál modelu se nikdy nepřepisuje | AGENT-RULES §6 |
| R5 | Telemetrie je strojově vyhodnotitelná (CSV/JSON + manifest) | PROJECT-PLAN §5.12 |
| R6 | Lokální simulace a runtime test jsou oddělené a označené | PROJECT-PLAN §5.14, princip č. 10 |
| R7 | Nebezpečné změny vyžadují karanténu nebo schválení | Tento dokument §7 |

---

## 3. Přístupy k integraci externí nástroj ↔ Studio

### Přístup A – Studio Plugin (doporučené jádro)

Vlastní plugin v `RobloxRuntime/` nainstalovaný do Studia. Plugin obsahuje tlačítka/příkazy:
`ImportVehicle`, `ApplyVariant`, `RunTestSuite`, `ExportTelemetry`, `RevertToBackup`.
Externí orchestrátor (Python/Luau tooling mimo Studio) s pluginem komunikuje přes soubory na disku
(`vehicle-data/configurations/<variant>/`, `vehicle-data/telemetry/<run>/`) nebo přes `HttpService` na localhost.

- Výhody: plný přístup k `DataModel`, `Selection`, `ChangeHistoryService`, `PhysicsService`; běží v Edit i Play; nejmenší latence; umí import `.rbxm` nativně.
- Nevýhody: vyžaduje instalaci pluginu uživatelem; plugin běží s právy Studia (nutná sebekázeň, viz §9); automatizace bez otevřeného Studia není možná.

### Přístup B – Rojo + externí runner

Zdrojáky harnessu (`ServerScriptService/TestHarness`, `ReplicatedStorage/Telemetry`) se synchronizují přes Rojo ze souborů na disku. Externí skript edituje `.lua` soubory, Rojo je promítne do Studia.

- Výhody: změny harnessu jsou verzované v Gitu; code-review možné; dobrá pro vývoj samotného testovacího prostředí.
- Nevýhody: Rojo synchronizuje skripty a strukturu, **ne** fyzikální chování ani `.rbxm` modely; pro samotné testy je stále potřeba Play session ve Studiu; složitější pro netechnického uživatele.

### Přístup C – Open Cloud API (dlouhodobý doplněk)

Roblox Open Cloud (`Place Publishing`, `DataStores`, `MessagingService`) pro nahrávání výsledků a stahování konfigurací bez otevřeného Studia.

- Výhody: CI-přívětivé, auditovatelné, funguje bez lokálního Studia.
- Nevýhody: neřeší fyzikální test (ten musí běžet v engine); vyžaduje API klíče a publikované place; latence; kvóty.

### Přístup D – Manuální Play-test harness (minimální start)

Testovací place s vestavěným `ServerScript` harnessem: uživatel otevře place, stiskne Play, harness sám provede scénář a zapíše telemetrii do `ServerStorage` / výstupního souboru.

- Výhody: nulová instalace navíc; funguje okamžitě; dobrá pro první funkční test (§10).
- Nevýhody: žádná skutečná autonomie (člověk mačká Play); škálování na stovky variant je pracné.

### Přístup E – Čistě externí lokální simulace (NEruntime)

Python/Lua fyzikální model mimo Roblox (převzaté principy z RobloxSimulatoru).

- Výhody: rychlé, deterministické, vhodné pro předfiltrování kandidátů optimalizátoru.
- Nevýhody: **není důkazem chování v Robloxu**; rozdílný integrátor, jednotky, solver constraints. Smí se použít pouze jako pre-screening (viz §8).

### Srovnání

| Kritérium | A Plugin | B Rojo | C Open Cloud | D Manuální harness | E Lokální sim |
|-----------|:---:|:---:|:---:|:---:|:---:|
| Skutečný physics engine | ano | ano | ne (transport) | ano | ne |
| Autonomie (bez klikání) | částečná* | částečná | ano (data) | ne | ano |
| Verzování změn | ano | ano (nejlepší) | ano | slabé | ano |
| Náročnost instalace | střední | vyšší | vyšší | nízká | nízká |
| Vhodnost pro FÁZI 9 | **vysoká** | střední | doplněk | start | pre-screen |

\* Plnou bezobslužnou autonomii (spuštění Play, sběr dat, zastavení) dává až kombinace A+D: plugin + harness script uvnitř place.

### Doporučená architektura (kombinace A + D, Rojo a Open Cloud později)

1. **Krátkodobě (první funkční test):** přístup D — testovací place + harness `ServerScript`, manuální Play.
2. **Střednědobě (FÁZE 9–10):** přístup A — plugin `AutoEngineerRuntime` automatizuje import/varianty/testy/telemetrii nad harnessem.
3. **Dlouhodobě:** B pro vývoj harnessu v Gitu, C pro archivaci výsledků a případné cloud CI.

---

## 4. Doporučená runtime architektura

```
[Externí orchestrátor]  (Python, mimo Studio; plánuje varianty, vyhodnocuje)
        ↕  soubory na disku (configurations/, telemetry/) nebo localhost HTTP
[Studio Plugin: AutoEngineerRuntime]
        ↕  DataModel API
[Test Place]  (samostatné .rbxl, verzované; obsahuje tratě + harness)
  ├── ServerScriptService/AE_Harness   (řídí scénář, reset, start/stop měření)
  ├── ServerScriptService/AE_Driver    (autonomní řidič: throttle/steer/brake)
  ├── ServerScriptService/AE_Telemetry (vzorkování, zápis logu)
  ├── ServerStorage/AE_VehicleSlot    (sem se klonuje testovaná varianta)
  ├── Workspace/AE_Track              (rovinka, zatáčky, brzdiště, nerovnosti)
  └── ReplicatedStorage/AE_Config     (aktivní konfigurace testu)
```

Pravidla:

- Testovací place je **samostatný soubor**, nikdy ne pracovní place uživatele.
- Vozidlo se do `AE_VehicleSlot` vždy **klonuje z verzované varianty**; test nikdy nemutuje uloženou variantu in-place.
- Harness, driver a telemetrie jsou oddělené `ModuleScript`/`Script` objekty s jasným API (§6), aby je bylo možné testovat izolovaně.
- Externí orchestrátor nikdy nezapisuje přímo do živého place; zapisuje pouze soubory variant, které plugin/harness explicitně načte.

Navržené Luau API harnessu (anglické identifikátory):

```lua
-- AE_Harness (ModuleScript)
Harness.LoadVariant(variantId: string) -> Model
Harness.ResetVehicle() -> ()
Harness.RunScenario(scenarioId: string, timeoutSec: number) -> RunResult
Harness.GetRunManifest() -> { variantId, scenarioId, placeVersion, physicsSettings, seed }
```

```lua
-- AE_Driver (ModuleScript)
Driver.SetThrottle(v: number)      -- -1..1
Driver.SetSteer(v: number)         -- -1..1
Driver.SetBrake(v: number)         -- 0..1
Driver.FollowWaypoints(wps: {Vector3}, targetSpeed: number) -> ()
Driver.Stop() -> ()
```

```lua
-- AE_Telemetry (ModuleScript)
Telemetry.Start(rateHz: number) -> ()
Telemetry.Stop() -> TelemetryLog
Telemetry.Sample() -> Sample  -- time, pos, vel, accel, rot, inputs, wheelData
```

---

## 5. Načítání a export modelů

- **Import:** `.rbxm` / `.rbxmx` přes plugin (`game:GetService("InsertService")` nebo drag-drop ekvivalent v pluginu). Po importu se spočítá hash struktury (názvy + třídy + Parent cesty) a uloží vedle varianty. Originál `chasis.rbxm` zůstává nedotčen (AGENT-RULES §6); pracuje se s kopiemi v `assets/chassis-original/` nebo scratchi.
- **Varianta = adresář:** `vehicle-data/configurations/<variantId>/` obsahuje `model.rbxm` (export klonem), `config.json` (parametry), `changes.json` (seznam změn proti rodiči), `parent.txt` (rodičovská varianta). Každá varianta je neměnná (immutable) po vytvoření.
- **Export:** plugin serializuje klon z `AE_VehicleSlot` zpět do `.rbxm` + doprovodný `report.json` (viz §5.15 PROJECT-PLANu). Před exportem kontrola integrity: počet kol, přítomnost hnacího systému, žádné `Missing` script reference.
- Externí `.rbxm` se nikdy neparsuje jako binárka vlastní logikou; autoritou je vždy živý strom ve Studiu (stejná zásada jako v praxi ověřených Studio workflow).

---

## 6. Měření: pozice / rychlost / zrychlení / rotace

Zdroj pravdy je `BasePart` podvozku (typicky `Chassis` / `PrimaryPart` / sedečka vozidla — určí Analyzer, zdokumentuje se ve variantě).

| Veličina | Luau zdroj | Poznámka |
|----------|-----------|----------|
| Pozice | `part.Position` / `CFrame` | studs; logovat plný `CFrame` (12 čísel) pro rotaci |
| Rychlost | `part.AssemblyLinearVelocity` | studs/s; preferovat před derivací pozice (méně šumu) |
| Zrychlení | derivace `AssemblyLinearVelocity / dt` + vyhlazení | klouzavý průměr přes ≥5 vzorků; surová i filtrovaná hodnota do logu |
| Rotace / úhlová rychlost | `CFrame` + `part.AssemblyAngularVelocity` | rad/s; náklon karoserie (roll/pitch) počítat z `CFrame:ToEulerAnglesYXZ()` |
| Kola | `AngularVelocity` constraints / otáčky os | prokluz = rozdíl obvodové rychlosti kola a podélné rychlosti vozidla |
| Vstupy | `Driver` stav (throttle/steer/brake) + čas | nutné pro reprodukovatelnost |

Vzorkování:

- Frekvence **60 Hz** (každý `Heartbeat`), minimálně 20 Hz. Čas = `os.clock()` + `workspace:GetServerTimeNow()` pro korelaci.
- Zrychlení se nikdy neloguje jako jediný vzorek; vždy okno + filtr (šum physics solveru).
- Jednotky: studs, sekundy. Převod na metry/km-h **až při vyhodnocení** mimo runtime, s explicitním převodním koeficientem v manifestu (žádné tiché převody uvnitř harnessu).

---

## 7. Bezpečnost změn: pět úrovní

| Úroveň | Co se mění | Příklady | Riziko | Pravidlo |
|--------|-----------|----------|:------:|----------|
| L1 Konfigurace | hodnoty existujících parametrů | tuhost pružin, převodové poměry, brzdný moment, `NumberValue`/`Attributes` | nízké | povoleno autonomně; každá změna do `changes.json`; auto-rollback při regresi |
| L2 Skripty | zdrojáky chassis (bez změny API) | ladění řadiče, úprava křivky plynu | střední | pouze na klonu; diff + parse-check před Play; zákaz změny `Require` cest bez schválení; po testu code-review záznam |
| L3 Hierarchie | Parent, názvy, přidání/odebrání instancí | nový `Attachment`, přesun senzoru, přidání `NumberValue` | střední–vysoké | snapshot před změnou; kontrola referencí (`FindFirstChild`/`WaitForChild` cíle existují); zákaz mazání bez zálohy |
| L4 Geometrie | `Size`, `CFrame`, `Position`, mesh | posun kol, rozvor, camber natočením | vysoké | pouze s předchozím měřením (baseline); jedna geometrická změna na test (žádné balíky); povinný screenshot/záznam bbox před/po |
| L5 Konstrukce | constraints, joints, pohonný systém | výměna `SpringConstraint` za jiný systém, změna FWD→AWD, náhrada A-Chassis | kritické | nikdy plně autonomně v FÁZI 9–10; vyžaduje schválení člověka + izolační test place; rollback klonem |

Obecná pravidla pro všechny úrovně:

1. Nikdy neměnit originál ani aktivně testovanou instanci — vždy klon → změna → test → vyhodnocení → přijetí/zahození.
2. Každá varianta zná svého rodiče (`parent.txt`); strom variant umožňuje návrat k nejlepší známé (`best-known` tag).
3. Před každým Play testem: `ServerStorage` záložní klon (`AE_Backup_<variantId>`), nikdy v `Workspace` (duplicitní skripty by běžely dvakrát).
4. Po neúspěšném testu: nulový diff proti záloze před pokračováním (žádné přenášení dvou mutací do jednoho testu).
5. Zákaz destruktivních operací bez zálohy (`ClearAllChildren`, mazání constraints za běhu testu, přepis `ModuleScript.Source` bez diffu).

---

## 8. Oddělení lokální simulace od Roblox runtime testů

Tři striktně oddělené úrovně důkazu (názvosloví povinné ve všech reportech):

1. **`SIM` (lokální matematická simulace):** Python/Lua model mimo Roblox. Slouží k pre-screeningu kandidátů optimalizátoru a k diagnostice („který parametr má největší vliv"). Výsledek se označuje `SIM-prediction`, nikdy `verified`.
2. **`INT` (integrační test mimo engine):** jednotkové testy konfiguračních funkcí, parse-check skriptů, kontrola integrity varianty. Neříká nic o jízdě.
3. **`RUN` (Roblox runtime test):** měření v Play session testovacího place. Jediné, co smí nést značku `verified-in-roblox` s odkazem na run manifest.

Pravidla oddělení:

- Složky `tests/physics/` (SIM) a `tests/runtime/` (RUN) se nikdy nemíchají; runtime výsledky mají vlastní manifest (§9).
- Optimalizátor smí v SIM vyřadit 90 % kandidátů, ale vítěz kola musí vždy projít RUN testem, než se stane `best-known`.
- Každý graf/srovnání v reportu uvádí zdroj dat (`SIM` / `RUN:<runId>`); graf bez zdroje je neplatný.
- Fyzikální konstanty SIM (timestep, grip model) se kalibrují **proti** RUN datům, nikdy naopak.

---

## 9. Opakovatelné prostředí a ukládání výsledků

Opakovatelnost:

- Fixní testovací place s verzí (`placeVersion` hash v manifestu); tratě: rovinka ≥500 studs, konstantní zatáčka (R=100), brzdiště, úsek nerovností, dva povrchy (`Asphalt` + `Grass`/`Gravel` materiál).
- Fyzikální nastavení place se loguje (`PhysicsSteppingMethod`, gravitace, `SleepAllowed`); testy běží na serveru (Play Solo, server-side čtení), bez GUI a bez lidského inputu během scénáře.
- Reset procedura před každým během: vozidlo na startovní `CFrame`, nulové rychlosti, stejná konfigurace, `task.wait()` na ustálení (≥1 s), teprve pak start měření.
- Každý scénář se jede **3×**; reportuje se medián + rozptyl. Rozptyl nad tolerancí (např. brzdná dráha ±5 %) = test neplatný, ne vozidlo špatné.

Manifest běhu (`vehicle-data/telemetry/<runId>/manifest.json`):

```json
{
  "runId": "RUN-2026-11-16-001",
  "level": "RUN",
  "variantId": "v042",
  "parentVariant": "v041",
  "scenarioId": "straight-accel-0-100",
  "placeVersion": "sha1:…",
  "physicsSettings": { "gravity": 196.2, "stepping": "Fixed" },
  "driver": "AE_Driver 0.1, throttle=1.0",
  "seed": 1,
  "repetitions": 3
}
```

Vedle manifestu: `telemetry.csv` (surové vzorky), `events.json` (start/cíl/prokluz/anomálie), `summary.json` (agregace: 0–100 čas, max rychlost, brzdná dráha, max roll). CSV sloupce minimálně:
`t, posX, posY, posZ, velX, velY, velZ, accX, accY, accZ, roll, pitch, yaw, throttle, steer, brake`.

---

## 10. Návrh prvního funkčního testu (RUN-001)

**Cíl:** ověřit, že řetězec varianta → place → driver → telemetrie → vyhodnocení funguje end-to-end, dříve než se začne optimalizovat.

- **Scénář `straight-accel-0-100`:** rovinka, start z klidu, `throttle=1.0`, `steer=0`, měřit čas do 100 studs/s (≈ převodní referenční rychlost, koeficient v manifestu) a ujetou vzdálenost. 3 opakování.
- **Scénář `straight-brake-100-0`:** ze 100 studs/s plné brzdy, měřit brzdnou dráhu a směrovou stabilitu (max |yaw rate|).
- **Pass kritéria RUN-001:** (a) všechny 3 běhy dokončeny bez zaseknutí/rozpadu; (b) rozptyl času 0–100 do ±5 %; (c) telemetrie kompletní (žádné chybějící vzorky >100 ms); (d) manifest + variantId spárovatelné; (e) návrat k záloze po testu s nulovým diffem.
- **Očekávaný výstup:** adresář `vehicle-data/telemetry/RUN-001/` + jednostránkový report s tabulkou mediánů. Neúspěch je platný výsledek — určí, která část řetězce se musí opravit.

---

## 11. Bezpečnostní omezení (závazná)

1. `C:/.DATA/RobloxSimulator` je read-only (AGENT-RULES §5); ověřit `git status --short` prázdný před i po práci.
2. Originál `chasis.rbxm` se nikdy nepřepisuje; pouze kopie.
3. Plugin/harness nikdy nespouští cizí kód zvenčí bez kontroly (žádné `loadstring` z neověřeného HTTP v testovacím place).
4. Změny L4/L5 pouze po baseline měření a se schválením; L5 (výměna chassis) až po FÁZI 9.
5. Žádná telemetrie s osobními údaji; logy obsahují pouze fyzikální data a ID variant.
6. Publikování do cloudu / přepis uživatelského place pouze s explicitním souhlasem uživatele.

---

## 12. Fakta / předpoklady / neznámé

**Ověřená fakta:**
- Projektový kontext: `C:/.DATA/AutoEngineerAI/docs/PROJECT-PLAN.md` (FÁZE 9, moduly 5.10–5.12, 5.14) a `docs/AGENT-RULES.md` — přečteny celé.
- Pracovní stav: repozitář `C:/.DATA/AutoEngineerAI` existuje (docs, assets, vehicle-data); `C:/.DATA/RobloxSimulator` existuje jako read-only zdroj (ověřen `rev-parse --show-toplevel`).
- Ověřené Studio postupy pro měření/editaci přes kód (MCP `execute_luau`, `inspect_instance`, Play readback) — zdroj: skill `roblox-studio-automation` SKILL.md (ověřené persistující vs. neperzistující operace, §1).

**Předpoklady (neověřené, nutno potvrdit ve FÁZI 1/9):**
- A-Chassis vystavuje laditelné parametry přes `Attributes`/`ValueBase` objekty (úroveň L1) — potvrdí `A-CHASSIS-AUDIT.md`.
- Testovací place poběží stabilně v Play Solo se server-side čtením `AssemblyLinearVelocity` na 60 Hz bez významných dropů.
- Převodní koeficient studs↔metry pro konkrétní vozidlo lze stanovit z rozměrů referenčního vozu (dořeší `VEHICLE-DATA.md`).

**Neznámé:**
- Skutečná hierarchie a názvy instancí v `chasis.rbxm` (dosud neauditováno v tomto úkolu).
- Chování A-Chassis driver inputu při scriptovaném řízení (zda `throttle` půjde nastavit bez boje s klientským inputem — riziko „dvojího řidiče").
- Přesná reprodukovatelnost physics solveru mezi běhy na tomto hardwaru (tolerance se stanoví až z RUN-001).

---

## 13. Rizika

| Riziko | Dopad | Mitigace |
|--------|-------|----------|
| Solver nedeterminismus → rozptyl nad tolerancí | falešné „zhoršení" variant | 3 opakování, medián, neplatnost testu při velkém rozptylu |
| Dvojí řidič (harness vs. vestavěný input) | auto nejede / jede křivě | v testovacím place vypnout stock input; logovat skutečné aktuátory |
| Tichá neperzistence editů (např. `ModuleScript.Source` přes runtime) | „opravená" varianta se neprojevila | editovat skripty pouze souborem/pluginem s nezávislým readbackem |
| Záměna SIM za důkaz | špatné rozhodnutí AI | povinné značení SIM/INT/RUN; report bez RUN = nevalidovaný |
| Smazání/rozbití varianty bez zálohy | ztráta práce | immutable varianty + `AE_Backup_*` + nulový diff po revertu |
| Závislost na jednom Studiu/PC | neškáluje | dlouhodobě Open Cloud archiv + verzovaný place |

---

## 14. Další kroky

1. Koordinátor: zkontrolovat kompatibilitu s `ARCHITECTURE.md` a `TESTING-OPTIMIZATION.md` (API harnessu vs. scénáře optimalizátoru).
2. Po auditu A-Chassis: doplnit do §6–7 konkrétní názvy instancí (který `Part` je měřicí, kde jsou L1 parametry).
3. Vytvořit minimální testovací place + `AE_Harness`/`AE_Driver`/`AE_Telemetry` skeleton (FÁZE 9 implementace).
4. Spustit RUN-001, stanovit reálné tolerance opakovatelnosti, teprve pak stavět optimalizátor.
5. Rozhodnout o Rojo/Open Cloud až po zeleném RUN-001 (nepředbíhat).

---

*Stav: návrh k připomínkám. Ověřeno: `git -C 'C:/.DATA/RobloxSimulator' status --short` prázdný (pouze čtení adresářové struktury); žádný zápis mimo tento soubor.*
