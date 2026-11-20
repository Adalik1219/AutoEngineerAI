# Agent D — Architektura A-Chassis + Mustang GT 2024 EU (NÁVRH, žádná destrukce)

Větev `feat/m2-m3-geometry` @ `557ee39` (ověřen, strom čistý). Role: Agent D.
Pravidla: čtení repa + RBXM metadata POUZE čtením; ZÁPIS pouze tento report.
RBXM neměněn, žádné modely nevytvořeny, žádné kopie nemazány.
`C:/.DATA/RobloxSimulator` READ-ONLY (pouze listing, bez zápisu).
M3 CLOSED, `main`/PR#2 tabu. Předchozí vstupy: `AGENT-D-CHASSIS-MUSTANG-STRATEGY.md`
(vrstvy A/B/C), `AGENT-F-MUSTANG-PHYSICS-MAPPING.md` (60 parametrů),
`vehicle-data/references/ford-mustang-gt-2024-eu-manual-standard.json`.
Doporučené cílové členění ze zadání (`chassis/original-analyzed-adapters`,
`vehicles/ford-mustang-gt-2024-eu/...`) je CÍL, ne povolení tvořit prázdné
složky — ověřeno, že neexistuje (§7). Čeština; identifikátory anglicky.

## 0. Shrnutí rozhodnutí

1. Výchozím technickým základem zůstává původní A-Chassis (AC6C 1.5 U2.1,
   kit 'Jeep'). Nic se nemění, nic se nemaže, nic se nepřestavuje.
2. Karoserie Jeep se v této fázi NEODDĚLUJE — níže je pouze NÁVRH postupu
   pro pracovní kopii (§3), destrukce se NEPROVÁDÍ.
3. Mustang karoserie v repu NEEXISTUJE (`find -iname "*mustang*"` vrací jen
   profil, M1 test a reporty). Chybějící údaj = UNKNOWN, nikdy Jeep hodnota.
4. Tento report je jediný zapsaný soubor; je připraven k realizaci po dodání
   assetu (§8).

## 1. Inventář původního A-Chassis (ze skutečných souborů/RBXM)

Zdroje: `docs/A-CHASSIS-AUDIT.md` (815 instancí / 37 typů / 17 Luau zdrojů),
`reports/M2/RBXM-INSPECTOR-REPORT.md` (census 37/815/928 PROP, hash
`dc8747e0…fefdf`, 230 421 B), `src/Chassis/adapters/achassis_v1.py`,
`src/Chassis/catalog/parameters.json` (138 záznamů),
`src/Inspection/*`, `testgame/src/ServerStorage/VehicleTemplates/JeepTemplate.rbxm`
(distinctně shodný s `assets/chassis-original/chasis-work-copy.rbxm`).

Kategorie: `CORE_CHASSIS` = přenositelný podvozkový základ · `VEHICLE_SPECIFIC` =
hodnoty vázané na Jeep/kit, pro Mustang přepsat · `BODY_VISUAL` = Jeep vizuál
k oddělení · `BODY_COLLISION` = Jeep kolize k oddělení · `WHEEL_SYSTEM` =
kola+trakce · `SUSPENSION_SYSTEM` = zavěšení · `UNKNOWN` = neověřeno / k Studio-odečtu.

| # | Komponenta | Soubor / RBXM cesta | Kategorie | Důvod zařazení |
|---|---|---|---|---|
| 1 | `Drive` (LocalScript, 42 093 B, hlavní fyzika: řízení, motor, převodovka, dify, TCS/ABS, brzdy) | `chasis-work-copy.rbxm` id 424 (text extrahován auditem, kap. 4) | CORE_CHASSIS | Podvozková logika nezávislá na tvaru karoserie; klientský kontext řidiče |
| 2 | `Initialize` (Script, 20 403 B, runtime stavba podvozku: kola, nápravy, motory #AV/#BV, gyra, váha, weldy) | `chasis-work-copy.rbxm` id 426 | CORE_CHASSIS | Staví simulaci za běhu; karoserii pouze weldí (`ModelWeld`), netvaruje ji |
| 3 | `A-Chassis Tune` (ModuleScript, 16 808 B, ~150 parametrů, jediná autoritativní konfigurace) | `chasis-work-copy.rbxm` id 211 | CORE_CHASSIS (struktura) + VEHICLE_SPECIFIC (hodnoty, viz ř. 22) | Mechanismus přenositelný; hodnoty kit/Jeep → pro Mustang nová sada |
| 4 | `README` (ModuleScript, 11 259 B, verze AC6C 1.5 U2.1) | `chasis-work-copy.rbxm` id 425 | CORE_CHASSIS | Verzování; `Drive` ji `require` pro tisk verze |
| 5 | `MiscWeld` (ModuleScript, 1 271 B, prázdná šablona uživatelských weldů) | `chasis-work-copy.rbxm` id 427 | CORE_CHASSIS | Rozšiřovací bod pro Mustang mounty bez zásahu do `Initialize` |
| 6 | `Controls_AC6` (6 074 B, přemapování ovládání) | `chasis-work-copy.rbxm` id 214 | CORE_CHASSIS | Vstupní vrstva nezávislá na karoserii |
| 7 | `Ignition` (667 B, klávesa F) + `LocalScript` spojka myši (681 B) + `AC6_MSteer_Camera` (1 101 B) | ids 368 / 366 / 305 | CORE_CHASSIS | Ovládání/kamera; bez vazby na tvar vozu |
| 8 | `Server` ×2 (2 337 B / 1 342 B, zvukové RemoteEvent servery) | ids 380 / 383 | CORE_CHASSIS | Síťový model zvuků; emitory se přemapují (§4) |
| 9 | `HP/TQ Reader` (1 197 B, čtení `Values` pro GUI) | id 376 | CORE_CHASSIS | Telemetrický čtecí bod, tvarově neutrální |
| 10 | `Gauges_AC6` (9 831 B, přístroje + max-rychlosti z převodů) | id 352 | CORE_CHASSIS | Po přepnutí `FDMult=1` a převodech MT-82 počítá správně; vizuální konflikt `FDMult≠1` evidován |
| 11 | `Simulated` (5 677 B, SS6 pneumatiky: tření/opotřebení/kluz, `_WHEELTUNE` MIMO Tune) | id 326 | WHEEL_SYSTEM | Jediný vlastník adheze; změna grip/wear jen kódem, ne Tune |
| 12 | `Aerodynamics` (788 B, přítlak + odpor natvrdo, bug `magnitude` → odpor se nikdy neaplikuje) | id 377 | CORE_CHASSIS (s vadou) | Síly působí na `Body` kotevní díly; oprava 1 znaku PŘED V-max kampaní, jinak maximálka bez odporu |
| 13 | `Engine_Sounds` (5 556 B) / `Induction_Sounds` (4 412 B) | ids 378 / 381 | BODY_VISUAL (audio) | Asset ID + EQ křivky; V8 zvuk patří k Mustang cestě, ne k základu |
| 14 | `Wheels` (Model) → `FL`/`FR`/`RL`/`RR` (Part, `shape=Ball`, `Size=(2.7,2.7,2.7)`) | ids 2 / 3 / 52 / 101 / 150 | WHEEL_SYSTEM | Koule = tvrdý limit (`Drive`/`Simulated` ignorují jiné tvary); 2.7 studs = Jeep rozměr, pro Mustang PŘEPSAT geometrií |
| 15 | `WheelFixed` + `SuspensionFixed` + `Parts` (vizuál kola) na každém kole | pod ids 3/52/101/150 | WHEEL_SYSTEM | Fixace a vizuál kola; přemapovat na Mustang disky/pneu |
| 16 | 4× `SuspensionGeometry` (custom větev: SpringBottom/CLower/CUpper/SpringTop/LowerArmB/LowerArmF/Hub/LowerArm/UpperArmF/UpperArmB/UpperArm, Weld, Spring, 8× Hinge, ~18× Attachment) | pod koly (audit kap. 3/8) | SUSPENSION_SYSTEM | Aktivní kinematika všech 4 kol; parametrem NELZE (jen přestavbou dílů/kloubů) |
| 17 | 4× `SpringConstraint` template `Spring` (runtime přepis: Stiffness/Damping/FreeLength/Max/Min; F/R: 20000/500/2.7/3.2/2.35) | pod koly | SUSPENSION_SYSTEM | Jediný ladicí bod podvozku; hodnoty PENDING na Studio-odečet (kandidátní dekód, Agent F §2.4) |
| 18 | `BodyGyro Stabilizer` na kole i tlumiči + `BodyGyro Steer` na `Arm` (P 100000/D 1000/50 kNm) | runtime z `Initialize` | SUSPENSION_SYSTEM + CORE_CHASSIS (Steer) | Tlumené klopení kol; řízení drží `Arm` — pár `Steer↔kola` nerozdělit (§2) |
| 19 | Hinge `#AV` (trakce) + `#BV` (brzda) na kolo, `ActuatorType=Motor`, tvoří `Initialize:440–462` | runtime | WHEEL_SYSTEM + CORE_CHASSIS | Pohon je Hinge-motorový (ne `VehicleSeat`, ne `Motor6D`); pár `pohon↔kolo` a `brzda↔kolo` nerozdělit |
| 20 | `Arm`/`Base`/`Axle`/`AxleP` (1.5³, `AxleDensity`), `#SA`/`#SB` + Spring (jen bez custom geometrie — NEAKTIVNÍ větev) | runtime | SUSPENSION_SYSTEM | Procedurální wishbone (`FWsBoneLen=4`, `SusAngle=80`, `AnchorOffset`) v tomto kitu neaktivní; parametry v Tune zůstávají mrtvé |
| 21 | `#Weight` (váhový kvádr, `WeightBSize={7.03,5.35,18.11}`, `WeightDist=55 %`, `CGHeight=.8`, dopočet hustoty na `Weight=3439 lb`) | runtime v `Body` (`Initialize:473–541`) | VEHICLE_SPECIFIC | Jediný hmotnostní model; vše massless kromě kol/náprav; pro Mustang 1808 kg + nové rozměry kvádru |
| 22 | Tune HODNOTY kit/Jeep (`Horsepower=200`, `Ratios={R:3.28…}`, `FinalDrive=3.545`, `FDMult=1.1`, `Config=AWD`, `TorqueVector=0`, `Turbochargers=2/T_Boost=7`, dify, brzdy, tuhosti…) | `A-Chassis Tune` id 211, katalog 138 záznamů | VEHICLE_SPECIFIC | 60 mapovaných parametrů (Agent F): 10 s doloženým Mustang cílem, 50 UNKNOWN; hodnoty se NEPŘENÁŠEJÍ |
| 23 | `Body` (Model: `DownforceF`, `DownforceR`, `Drag` BodyThrust „T", `Engine`, `Exhaust` zvukové emitory) | id 199 | CORE_CHASSIS (kotvy sil) + BODY_VISUAL (emitory) | Aero síly potřebují kotevní díly v `Body`; `Engine`/`Exhaust` jsou zvukové emitory k přemapování |
| 24 | `JeepBodyVisual` (`Brakes`/`G1`/`Hazards`/`Left`/`Light`/`Right` modely, světla, zrcátka) | id 429 | BODY_VISUAL | Čistě vizuál Jeepu; první kandidát oddělení (§3) |
| 25 | `CollisionParts` (11 dílů: Front/Kapota/Roof/Back/BackWheel/Left/Left2/Right2/Right/Sklo/Spodek) | id 792 | BODY_COLLISION | Kolizní model Jeepu; oddělit jako celek, nikdy po částech bez náhrady |
| 26 | UnionOperation, SurfaceGui, Decal, BlockMesh, PointLight/SpotLight (vizuální vrstva nad rámec Novema kopie) | rozptýleno ve stromu | BODY_VISUAL | Chybí v chudší Novema kopii — důkaz, že patří ke karoserii, ne k základu |
| 27 | `DriveSeat` (`VehicleSeat`, Torque/MaxSpeed/Steer 0 — jen sedadlo, NEPOHÁNÍ) + `Misc` (sedadla, volant, `MiscWeld`) | ids 428 / 1 | CORE_CHASSIS | Povinný kotevní bod (`Drive` očekává `script.Parent.Car`, `ModelWeld(Body,DriveSeat)`); sedadlo zůstává, přesouvá se (§4 poloha řidiče) |
| 28 | `A-Chassis Interface` ScreenGui (`Values` 31× NumberValue + 14× BoolValue + TransmissionMode + 4× OriginalSize + Velocity + `Car` ObjectValue, `Controls…`) | mimo `Car` model (PlayerGui po usednutí) | CORE_CHASSIS | Stav distribuuje `Initialize`; telemetrie `Values.RPM/Horsepower/Torque` = měřicí body testů |
| 29 | Sériové constrainty: 108× `WeldConstraint`, 72× `Attachment`, 32× `HingeConstraint` (24× `LimitsEnabled`), 3× `BodyThrust`, PGS-only, `ModelWeld(Body,DriveSeat)`, `UnAnchor` všeho | celý strom | CORE_CHASSIS (skeleton) | Kostra simulace; `Attachment0/1` 32/32 do existujících attachmentů (audit kap. 1) |
| 30 | Float-lane hodnoty (`Part.Size`/`CFrame`, `SpringConstraint.*`, `NumberValue.Value`, `HingeConstraint` úhly) — kandidátní dekód NEpotvrzen (symetrie kol nevychází) | PROP lane souboru | UNKNOWN | Čeká na Studio ground-truth (odečet `Size`/`CFrame` kol + kalibrační díl); do té doby mimo prostor i mimo zápis |
| 31 | `Tune.StAxisOffset` CHYBÍ, `Initialize:171` ho čte (`CFrame.new(0,nil,0)` → hrozí runtime error) | Tune id 211 × `Initialize:171` | UNKNOWN (blokující podezření) | Verdikt prvním spuštěním ve Studiu PŘED jakoukoli přestavbou (Agent F riziko č. 5) |
| 32 | Elektro-větev 9× (`electric_*`, `Electric=false` mrtvá), `FWLgcyDensity` (mrtvý kód), `Gauges:62` jména `ElecRedline/ElecTransition2` vs Tune `E_Redline/E_Trans2` | Tune + `Simulated` + `Gauges_AC6` | UNKNOWN (mrtvý kód) | Neaktivní; nemazat bez rozhodnutí, nezapisovat |
| 33 | Adaptér `achassis_v1.py` (kit 'Jeep' = vrstva A), `live-tune-keys.txt`, katalog 138 záznamů, `mapping/dependencies.py` + `cycle_check.py` (0 cyklů) | `src/Chassis/*`, `vehicle-data/analyzed/*` | CORE_CHASSIS (nástroje) | Zdroj pravdy Tune+geometrie ramen; `check_known_tables()` = 0 cyklů |

Počty komponent v kategoriích (ř. 1–33, component = řádek inventáře):

| Kategorie | Počet | Řádky |
|---|---|---|
| CORE_CHASSIS | 14 | 1–10, 12, 27–29, 33 (ř. 3, 23 částečně) |
| VEHICLE_SPECIFIC | 2 | 21, 22 |
| BODY_VISUAL | 3 | 13, 24, 26 (23 částečně) |
| BODY_COLLISION | 1 | 25 |
| WHEEL_SYSTEM | 4 | 11, 14, 15, 19 (částečně) |
| SUSPENSION_SYSTEM | 3 | 16, 17, 18 (částečně), 20 |
| UNKNOWN | 4 | 30, 31, 32 (+ PENDING hodnoty v ř. 17/22) |
| **Celkem** | **31 inventárních položek** (815 instancí / 37 typů / 17 skriptů v RBXM) | |

## 2. Mapa závislostí (co musí zůstat spolu)

Pravidlo: přenositelnost VŽDY jen s důkazem (Studio-běh nebo auditní citace).
Rozdělení páru bez důkazu = BLOCKED.

| Pár / skupina | Drží pohromadě | Důkaz (zdroj) | Důsledek rozdělení |
|---|---|---|---|
| Wheel controller ↔ 4 kola | `Drive` + `Simulated` + `#AV/#BV` + kola `FL/FR/RL/RR` (jména POVINNÁ, tvar Ball) | Audit kap. 4/10/12/16: kola musí být koule a jmenovitě FL-FR-RL-RR, jinak je `Drive`/`Simulated` ignorují | Přejmenování / jiný tvar = mrtvá kola bez chyby |
| Řízení ↔ kola | `BodyGyro Steer` na `Arm` + `Arm.Steer.CFrame` vs `Base` + `SteerOuter/Inner` (31.2°, Ackerman .9) + decay 330 SPS | Audit kap. 9 (`Drive` 322–431, Tune 108–143, `Initialize` 145–159) | Oddělený `Arm`/`Base` = neřiditelné auto; camber/caster/toe jsou jen vizuální natočení, ne fyzika |
| Pohon ↔ kola | `#AV` Hinge-motor na kolo + `_spLimit` z `Drive` + `SpeedEngage=20` SPS spojky | Audit kap. 5/6/14; kap. 19: pohon je HingeConstraint-motorový | Pohon bez kola = točící se motor naprázdno; `VehicleSeat` NEPOHÁNÍ (Torque/MaxSpeed 0) |
| Motor ↔ převodovka | `NCache/ECache/TCache/SCache` (RPM×převod) + `Ratios` + `FinalDrive×FDMult` + `_GoalRPM↔_WheelRPM` přes `_Clutch`/`Flywheel` | Audit kap. 5/6 (`Drive` 435–650, 653–732, 784–930) | Změna poměrů bez křivky (nebo naopak) = klepání o omezovač / mrtvé stupně; `FDMult≠1` rozhodí `Gauges` |
| Brzdy ↔ kola | `#BV` na kolo + `BrakeForce=2500/Bias=.6` + `PBrake` jen zadek + ABS on/off práh 20 SPS + gradientní TCS | Audit kap. 12 (`Drive` 999–1077, Tune 329–338) | Brzda bez kola = nebrzdí; práh → 0 = brzdy téměř nebrzdí |
| Seat ↔ celá stavba | `DriveSeat` + `ModelWeld(Body,DriveSeat)` + `Initialize` stavba + `Drive` očekává `script.Parent.Car`/`IsOn`/`Values` + `SetNetworkOwner(hráč)` + klientská fyzika | Audit kap. 4/14/16 | Bez sedadla se nic nepostaví a fyzika neběží; sedadlo = spouštěč, nepohání |
| Suspension ↔ geometrie | `SuspensionGeometry` custom modely + template `Spring` + `Stiffness/Damping/FreeLength/Max/Min` + `Stabilizer` gyra + `Hub→Base`/`SpringTop→DriveSeat` weldy | Audit kap. 8 (`Initialize` 207–365): kinematika ramen parametrem NELZE | Nová karoserie bez přemapovaných `Hub`/`SpringTop` kotev = zavěšení ve vzduchu; tuhosti mimo 0.25–4× = dosedání/houpání |
| Hmotnost ↔ geometrie | `#Weight` kvádr + `WeightDist` + `CGHeight` + dopočet hustoty na `Weight` | Audit kap. 11 (`Initialize` 473–541) | `CGHeight` > ~2 = převracení; kvádr musí odpovídat karoserii 4810×1916 mm |
| Aero ↔ `Body` kotvy | `DownforceF/R` + `Drag` BodyThrust + konstanty mimo Tune + `magnitude` bug | Audit kap. 13 | Bez kotevních dílů v `Body` není kam síly pověsit; V-max až PO opravě |
| Zvuk ↔ emitory | `Engine`/`Exhaust` v `Body` + `Plugins` RemoteEvents + asset ID | Audit kap. 4/15 | Odtržené emitory = tiché auto (funkčně jede, ale bez zpětné vazby) |

## 3. Návrh oddělení Jeep karoserie (pracovní kopie, BEZ destrukce)

Stav: NEPROVEDENO, pouze navrženo. Destrukce je přípustná VÝHRADNĚ na pracovní
kopii `assets/chassis-original/chasis-work-copy.rbxm` (nikdy na
`testgame/.../JeepTemplate.rbxm`, nikdy na originál mimo repo) a VÝHRADNĚ
s kopií + rollbackem (SHA-256 před/po + `git status` čistý kromě tohoto reportu).
Play test až pozdější fáze (§6).

### 3.1 Inventář: co lze oddělit (vizuál, bez vazeb logiky)

| Substrom | Kořen (id) | Proč je bezpečný k oddělení |
|---|---|---|
| `JeepBodyVisual` (Brakes/G1/Hazards/Left/Light/Right, světla, zrcátka) | 429 | Čistě vizuál, žádný skript na něj neodkazuje jménem kromě světelných režimů |
| `CollisionParts` 11 dílů (Front/Kapota/Roof/Back/BackWheel/Left/Left2/Right2/Right/Sklo/Spodek) | 792 | Kolizní model; `Drive`/`Initialize` ho nečtou (hmotnost = `#Weight` kvádr, ne díly) |
| UnionOperation / SurfaceGui / Decal / BlockMesh / PointLight / SpotLight vrstva | rozptýleno | Důkaz vizuální příslušnosti: chybí v Novema kopii (§1 ř. 26) |
| `Engine_Sounds` / `Induction_Sounds` + asset ID | ids 378 / 381 | Zvuk V8 patří k nové cestě; odpojení = ticho, ne nefunkčnost |

### 3.2 Co NESMÍ být odděleno / poškozeno (kostru drží)

1. `DriveSeat` (428) + `Misc` (1) + `ModelWeld(Body,DriveSeat)` — spouštěč stavby.
2. `Body` kotvy (199: `DownforceF/R`, `Drag`, `Engine`/`Exhaust` emitory) — aero a zvuk.
3. `Wheels` (2) + vše pod koly + runtime `#AV/#BV`, `Arm/Base/Axle`, gyra — §2.
4. `A-Chassis Tune` (211) + `Initialize` (426) + `Drive` (424) + `Values`/GUI — logika.
5. Všech 108 `WeldConstraint` / 72 `Attachment` / 32 `HingeConstraint` mimo §3.1.
6. `WeightBSize`/`WeightDist`/`CGHeight`/`Weight` — hmotnostní model (§2).

### 3.3 Postup (návrh, kroky provede člověk ve Studiu nebo pozdější fáze)

1. Ověřit SHA-256 pracovní kopie = `dc8747e0…fefdf`; pořídit zálohu
   `chasis-work-copy.pre-jeep-sep.rbxm` (mimo repo nebo scratch) + zapsat hash.
2. Otevřít POUZE pracovní kopii ve Studiu (Edit, NE Play); potvrdit strom §1.
3. Skrýt (Visible=false, NE mazat) `JeepBodyVisual` → Edit kontrola: stavba
   (`Initialize`) proběhne, kola/řízení na místě, chyby v Outputu = STOP.
4. Skrýt `CollisionParts` → Edit kontrola: constrainty beze změny počtu
   (108/72/32), `DriveSeat` weld drží.
5. Teprve s kopií + hashem: smazat §3.1 z pracovní kopie → diff instancí
   (815 − N), export nové kopie, hash zapsat; rollback = návrat k záloze z kroku 1.
6. Rollback brána: jakýkoli error `StAxisOffset` (ř. 31) nebo pád stavby =
   nefuknční základ, NE karoserie → obnovit zálohu, evidovat, STOP.

## 4. Mustang body interface (cílové rozhraní karoserie)

Konvence: každá hodnota = jednotka + zdroj + status (`VERIFIED` / `ESTIMATED` /
`PENDING` / `UNKNOWN`). Neznámá = `UNKNOWN`, nikdy Jeep hodnota (Agent D
strategie vrstvy A/B/C; Agent F mapa 60 parametrů).

| Parametr rozhraní | Jednotka | Zdroj | Status | Hodnota / poznámka |
|---|---|---|---|---|
| Referenční bod karoserie (střed `Body`, původ souřadnic) | studs | Studio-odečet z Mustang assetu | UNKNOWN | `null` — Jeep střed NEPŘEBÍRAT (jiný vůz, jiný rozvor) |
| Osy (`+X` příčná / `+Y` svislá / `+Z` podélná, forward = −Z konvence) | — | A-Chassis skripty + Studio | PENDING | Konvenci potvrdit odečtem `CFrame` kol FL–FR/FL–RL na Mustang assetu |
| Axle reference (výšky os náprav nad zemí) | studs | Studio-odečet | UNKNOWN | `null` — odvozeno z poloměrů kol až po dodání assetu |
| Wheel center FL / FR / RL / RR | studs (Vector3) | Studio-odečet `Position` | UNKNOWN | `null` — Jeep FL–RL 10.5228 / FL–FR 5.9907 jsou JEEP_MEAS (BLOCKED 7,44 %), float-lane navíc neověřena |
| Rozvor | mm → studs | Profil `dimensions.wheelbase` [1b] | VERIFIED (mm) / PENDING (studs) | 2719 mm; převod na studs až s VERIFIED měřítkem (M3 brána) |
| Rozchod F / R | mm → studs | Profil `dimensions.track_front/track_rear` [1b] | VERIFIED (mm) / PENDING (studs) | 1585 / 1642 mm |
| Poloměr kola F / R (nominální, nezatížené) | mm | Výpočet z 255/40 R19, 275/40 R19 (VEHICLE-SPEC §2) | ESTIMATED | 686.6 / 702.6 mm (±5 mm dezén); staggered F≠R promítnout |
| Attachmenty kol (`Hub`, `SpringTop`, `SpringBottom`, ~18× na kolo) | — | Mustang asset + `Initialize` | UNKNOWN | `null` — přemapovat 1:1 jména, jinak `Initialize` nestaví |
| Mount points karoserie (`MiscWeld` body, zrcátka, světla, nárazníky) | — | Mustang asset | UNKNOWN | `null` — uživatelské weldy přes `MiscWeld` (prázdná šablona připravena) |
| Světelné režimy (Brakes/G1/Hazards/Left/Right) | — | Mustang asset | UNKNOWN | `null` — struktura dle `JeepBodyVisual` jako šablona členění, ne hodnot |
| Kolizní zóny (11: Front/Kapota/Roof/Back/BackWheel/Left/Left2/Right2/Right/Sklo/Spodek) | — | Mustang asset | UNKNOWN | `null` — 11 zón Jeepu = šablona POKRYTÍ, každá zóna přeměřit na 4810×1916×1404 mm |
| Poloha řidiče (`DriveSeat` + volant, výhled, dosah) | studs | Studio + jízdní test | UNKNOWN | `null` — sedadlo zůstává kotevním bodem stavby (§2), posouvá se jako celek |
| Světlá výška (clearance, difuzér/výfuk) | mm → studs | Studio-odečet | UNKNOWN | `null` — kritické pro `MinLength` dosednutí |
| Obálka karoserie (délka/šířka/výška) | mm | Profil `dimensions` [1b] | VERIFIED | 4810 / 1916 (2080 se zrcátky) / 1404 mm |
| Hmotnost / rozložení / CG výška | kg / % / mm | Profil `mass` (1808 kg ESTIMATED; distribuce a CG CHYBÍ) | ESTIMATED / UNKNOWN / UNKNOWN | `#Weight` kvádr přepočítat; `CGHeight ≤ ~1.2` bezpečné pásmo |
| Zvukové emitory (`Engine`/`Exhaust` pozice) | studs | Mustang asset | UNKNOWN | `null` — V8 emitory vpředu/vzadu dle skutečné zástavby |

## 5. Tři cesty k Mustang karoserii

| | A — Vlastní model (doporučeno) | B — Legální asset s licencí | C — Označený placeholder |
|---|---|---|---|
| Popis | Nový `Body` + vizuál + kolize modelované z profilu (4810×1916×1404, rozvor 2719) | Existující S650/Fastback asset s prokazatelnou licencí (nákup, open-licence, zakázka) | Průhledný box-model 4810×1916×1404 s 11 kolizními zónami a 4 válcovými koly, jasně označený `MUSTANG-PLACEHOLDER` |
| Výhody | Čistá licence; přesné VERIFIED rozměry; žádné Jeep reziduum; TOP-dopad na M4 kalibraci | Rychlost (dny); hotová topologie světel/interiéru | Okamžité testy ROZHRANÍ (§4) bez čekání; nulové licenční riziko; odhalí chyby kostry (`StAxisOffset`, `magnitude`) |
| Rizika | Čas (týdny); kvalita vizuálu závisí na modeláři; nutná kontrola proporcí | Licenční past (většina marketplace assetů bez jasné licence); skryté skripty v assetu; špatné měřítko/topologie | Nulová vizuální hodnota; riziko záměny za finál (mitigace: název + watermark + report) |
| Vstupy | Profil + [1b] tech specs + fotodokumentace S650 + modelář (Blender/Studio) | Licenční smlouva/důkaz + audit assetu (žádné skripty, měřítko, polycount) | Profil rozměry + 1 den práce ve Studiu |
| Ověření | Rozměry ±10 mm; 11 zón pokrytí; světelné režimy; Studio Edit kontrola §6 | Licence v repu (`vehicle-data/license/`); skript-scan; měřítko vs 2719 mm | Označení viditelné; brány G1–G6 §6 procházejí; NIKDY do prezentace jako Mustang |

## 6. Plán sestavení (14 kroků, pracovní kopie → Edit kontrola; Play až pozdější fáze)

Legenda bran: každá brána = podmínka postupu; nesplnění = STOP + evidence, ne obcházení.

| Krok | Akce (Edit režim, pracovní kopie) | Brána |
|---|---|---|
| 1 | Záloha + hash: SHA-256 `chasis-work-copy.rbxm` = `dc8747e0…fefdf`, kopie `.pre-mustang.rbxm`, hash zapsat | G1: hash shodný, `git status` čistý kromě tohoto reportu |
| 2 | Otevřít kopii ve Studiu (Edit, NE Play); potvrdit strom 815/37, AC6C 1.5 U2.1 z `README` | G2: counts shodné s auditem; odchylka = STOP (jiný soubor) |
| 3 | Odečet `Size`/`Position`/`CFrame` kol FL/FR/RL/RR + `DriveSeat` + `#Weight` kvádru → `vehicle-data/analyzed/` | G3: symetrie L/R ±1 %; neshoda s kandidátním dekódem = evidovat, float-lane zůstává UNKNOWN |
| 4 | První Edit stavba: potvrdit/vyvrátit `StAxisOffset` (Initialize:171), `magnitude`, `Gauges` jména, `FWLgcyDensity` | G4: verdikt ke všem 4 chybám auditu kap. 17 zapsán; `StAxisOffset` error = STOP pro přestavbu |
| 5 | Oprava `magnitude` → `Magnitude` na KOPIÍ skriptu (1 znak, mimo originál) | G5: diff 1 znak; odpor se vyhodnocuje bez erroru |
| 6 | Skrytí (NE mazání) `JeepBodyVisual` + `CollisionParts` → Edit kontrola stavby a constraintů 108/72/32 | G6: stavba bez errorů, počty constraintů shodné |
| 7 | Import Mustang karoserie (cesta A/B/C z §5) jako SOUROZENECKÝ model vedle Jeep stromu, NE místo něj | G7: licence/důvod cesty evidován; import bez skriptů (scan čistý) |
| 8 | Přemapování kotev: `Hub`/`SpringTop`/`SpringBottom` + `Arm`/`Base` na Mustang geometrii; `MiscWeld` mounty | G8: jména attachmentů 1:1, `Attachment0/1` všechny do existujících |
| 9 | Nová sada Tune (Mustang): `Config=RWD`, `Turbochargers=0`, převody MT-82 (3.237/2.104/1.422/1.0/0.814/0.622), `FDMult=1`, `FWSteer=None`, `Weight=1808 kg` | G9: každá hodnota jednotka+zdroj+status; UNKNOWN zůstává UNKNOWN; `final_drive`/bias/křivka NEdomyšleny |
| 10 | `#Weight` kvádr: rozměry z 4810×1916 mm, `WeightDist`/`CGHeight` = UNKNOWN do kalibrace (bezpečné pásmo) | G10: součet `GetMass` ≈ 1808 kg ±5 %; `CGHeight ≤ ~1.2` |
| 11 | Světla/režimy + `Engine`/`Exhaust` emitory + zvuková cesta na Mustang pozice | G11: režimy Brakes/G1/Hazards/Left/Right funkční v Editu |
| 12 | Kolizní model 11 zón na Mustang obálku; Jeep `CollisionParts` stále skryté (NE smazané) | G12: pokrytí 11/11, žádné díly s `CanCollide` konfliktem se zavěšením |
| 13 | Destrukční krok (POUZE s kopií+hashem z kroku 1): smazat Jeep §3.1 z pracovní kopie → diff instancí, nový hash | G13: diff = přesně §3.1; rollback k záloze funkční (ověřit obnovením) |
| 14 | Edit finále: kompletní kontrola stromu, constraintů, Tune, dokumentace změn + rollback-postup | G14: `Initialize` stavba čistá v Editu; Play test VÝSLOVNĚ až pozdější fáze (M4+) |

Play (jízda, V-max, brzdy, slalom) = pozdější fáze po G14, nikdy v tomto plánu.

## 7. Migrační plán k cílovému členění

Cílové členění ze zadání (CÍL, dnes NEEXISTUJE — ověřeno `ls`: ani `chassis/`,
ani `vehicles/` v repu není; `grep -rn "chassis/original\|vehicles/ford"` = 0 výskytů):

```text
chassis/original/          # zamrzlý základ (kopie dnešních vstupů, read-only)
chassis/analyzed/          # výstupy měření (Studio-odečty, vehicle-data/analyzed)
chassis/adapters/          # dnešní src/Chassis/adapters (achassis_v1.py, kit 'Jeep')
vehicles/ford-mustang-gt-2024-eu/  # NOVÁ větev cíle (Tune sada, body interface, asset)
```

| Cíl | Co EXISTUJE (zdroj k přesunu odkazem, NE kopírovat binárky) | Co CHYBÍ (vytvořit až po dodání assetu / Studio-měření) | Co NEVYTVOŘET (zakázáno) |
|---|---|---|---|
| `chassis/original/` | `assets/chassis-original/chasis-work-copy.rbxm`, `testgame/.../JeepTemplate.rbxm` (hash `dc8747e0…fefdf`) | Manifest původu (cesta, hash, datum, AC6C verze) — 1 malý `.md`/`.json` | Duplicitní třetí kopie RBXM; prázdné složky předem |
| `chassis/analyzed/` | `vehicle-data/analyzed/live-tune-keys.txt`, `reports/M2/*.md`, `reports/STUDIO_GROUND_TRUTH.md` | Studio-odečty kol/sedadla/kvádr (krok 3), symetrie-protokol | Odhady vydávané za měření; Jeep→Mustang přenosy |
| `chassis/adapters/` | `src/Chassis/adapters/achassis_v1.py`, `catalog/parameters.json` (138), `mapping/*` (0 cyklů) | Strukturální konverze `Ratios` list→dict, `TransModes` Manual-first (návrh Agent F, až M4) | Duplicitní moduly; přepis `achassis_v1.py` na Mustang (adaptér zůstává kitový, cíl = nová sada) |
| `vehicles/ford-mustang-gt-2024-eu/` | Profil `vehicle-data/references/ford-mustang-gt-*.json`, tento report, Agent F mapa | Tune sada Mustang, body interface naplněný (§4), karoserie (cesta A/B/C), licence-důkaz, kolizní model | Prázdný skeleton složek; `final_drive`/bias/křivka bez zdroje; Dark Horse díly (T18 zákaz) |

Pravidla migrace: (a) nic se nepřesouvá, dokud G1–G4 neprojdou; (b) RBXM se
nekopíruje do nové struktury (odkaz + hash stačí); (c) první skutečný soubor
v `vehicles/` vzniká až s dodaným assetem (krok 7); (d) M3 zůstává ZAVŘENÁ do
VERIFIED měřítka (`require_verified_for_m3`).

## 8. Předání: počty, rizika, připravenost

Počty komponent (§1): CORE_CHASSIS 14 · VEHICLE_SPECIFIC 2 · BODY_VISUAL 3 ·
BODY_COLLISION 1 · WHEEL_SYSTEM 4 · SUSPENSION_SYSTEM 3 · UNKNOWN 4 =
31 inventárních položek (podklad: 815 instancí / 37 typů / 17 skriptů / 138 katalogových parametrů / 60 mapovaných parametrů, z toho 50 UNKNOWN).

Klíčová rizika (top 5):
1. `StAxisOffset` CHYBÍ v Tune, `Initialize:171` ho čte — hrozí runtime error při první stavbě; verdikt krok 4, do té doby žádná přestavba.
2. Float-lane (`Size`/`CFrame`/tuhosti) neověřena — kandidátní dekód (20000/500) mimo prostor i mimo zápis do Studio-odečtu.
3. `Config` AWD→RWD + turbo 2→0 + nedefinovaný převod 328 kW→`Horsepower` — motorová kalibrace zablokovaná (křivka `points: []`, M1.9).
4. Stálý převod 3.15 vs 3.55 nerozhodnut (GUARD T17) — stojí kalibrace převodovky.
5. `magnitude` bug — V-max (250 km/h) měřit až PO opravě, jinak bez odporu.

Připraveno k realizaci po dodání assetu: inventář §1 (co držet/oddělit) ·
závislosti §2 s důkazy · návrh oddělení §3 (kopie+rollback, ne destrukce) ·
rozhraní §4 (tabulka k naplnění) · cesty §5 (doporučena A, okamžitě schůdná C) ·
14 kroků §6 s branami G1–G14 (Edit kontrola, Play až M4+) · migrace §7
(bez prázdných složek, bez třetích kopií RBXM).

Zapsán pouze tento soubor. RBXM neměněn, strom jinak čistý.
