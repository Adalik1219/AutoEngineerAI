# A-Chassis – technický audit (FÁZE 1)

**Vlastník:** specialista na Roblox vehicle physics a Luau
**Datum:** 2026-11-16
**Vstup:** `C:/Users/adamr/Downloads/chasis.rbxm` (originál, READ-ONLY, neměněn)
**Pracovní kopie:** `C:/.DATA/AutoEngineerAI/assets/chassis-original/chasis-work-copy.rbxm`
**Referenční kopie (pouze čtení):** `C:/Users/adamr/Downloads/A-Chasis 6C by Novema.rbxm`
**Kontext:** `C:/.DATA/AutoEngineerAI/docs/PROJECT-PLAN.md`, `C:/.DATA/AutoEngineerAI/docs/AGENT-RULES.md`

Značení v celém dokumentu: **[F]** = ověřený fakt (vlastní inspekce souboru/kódu),
**[P]** = předpoklad (nejlepší dostupný odhad, nutno ověřit), **[N]** = neznámé (postup ověření uveden).

---

## 1. Metoda a integrita vstupu

**[F]** Pracovní kopie pořízena prostou kopií originálu, SHA-256 obou souborů je shodná:
`dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf` (230 421 B).
Originál nebyl modifikován.

**[F]** Formát souboru: binární Roblox `rbxm` (magic `<roblox!`, signatura `89 FF 0D
0A 1A 0A`, verze 0). Hlavička: `numTypes = 37`, `numInstances = 815`.
Struktura chunků (vlastní dekodér, Python + `lz4`):
`META` (ExplicitAutoJoints=true) → `SSTR` (prázdná, 0 sdílených řetězců) →
37× `INST` → 927× `PROP` → 1× `PRNT` (815 vazeb) → `END`. Všechny chunky se
podařilo dekomprimovat (LZ4 block) a sparsovat.

**[F]** Rozluštěné kódování (verifikováno křížovou konzistencí, viz níže):
referenty instancí v `INST` = prokládané (interleaved) bajty, pořadí MSB-first,
zigzag + kumulativní součet → ID 0–814 beze zbytku; `PRNT` = dvě prokládaná pole
(potomci, rodiče), stejné kódování → 815 unikátních potomků, 260 unikátních
rodičů + `NULL` kořen. Jedno ID = přesně jedna instance, kořen = `0:Model` (jméno prázdné, viz kap. 3).

**Co se podařilo plně [F]:** hierarchie + jména všech 815 instancí, třídy a počty,
všech 17 zdrojáků Luau (kompletní text), kompletní Tune-tabulka, bool/enum/int/
string/referenční property (vč. `Attachment0/1` constraintů – 32/32 zásahů do
množiny existujících attachmentů), barvy, materiály, tvary dílů, stav schránky
(vše nemodifikováno – neukotvené? viz kap. 14), BoolValue/NumberValue jména.

**Co se nepodařilo a proč [F]:** bitově přesné hodnoty float/double/CFrame/Vector3
propert (`Part.size`, `Part.CFrame`, `SpringConstraint.Stiffness/Damping/...`,
`NumberValue.Value`, `HingeConstraint` úhly). Float-lane jsou prokládané +
rotované po bajtech; bez ground-truth (známé referenční hodnoty v souboru nejsou
– všechny `Values` jsou nulové, auto uloženo v klidu) nelze rotaci jednoznačně
potvrdit. Kandidátní schéma (LE-deinterleave + rotL8, tj. postup referenční
implementace `rbx-binary`) dává „čisté" hodnoty (např. `Stiffness = 0x40198C00 =
2.39917`), ale symetrie kol pod ním nevychází, takže ho **nepovažuji za
potvrzené**. **Postup:** otevřít kopii ve Studiu, odečíst `Size`/`CFrame` kol
(FL/FR/RL/RR) a porovnat s hrubými dekódy; případně vložit kalibrační díl známé
velikosti a ověřit schéma. Pro účely FÁZE 1 to neblokuje nic podstatného –
veškerá logika je ve zdrojácích a Tune-tabulce (100 %).

---

## 2. Identifikace verze

**[F]** Hlavičky zdrojáků + `README` (ModuleScript id 425, 11 259 B):
`A-Chassis 6C (AC6C), Build 6C, Version 1.5, Update 2.1`, autoři
pointclouded | NVNA, úpravy LuaInt. `Drive` tiskne verzi z `README` při startu.
Poslední changelog: 07/09/24 (1.5 Update 2.1).

**[F]** Srovnání s `A-Chasis 6C by Novema.rbxm` (94 111 B, SHA
`9d835265…`, 29 typů / 434 instancí): stejná rodina (stejné skripty co do
názvů – 12 LocalScriptů, 3 ModuleScripty), ale chudší obsah: chybí celá vizuální
vrstva (UnionOperation, SurfaceGui, světla PointLight/SpotLight, Decal,
BlockMesh) a **custom `SuspensionGeometry` modely** (WeldConstraint 12 vs 108,
Model 24 vs 38, Part 53 vs 109). Zkoumaný `chasis.rbxm` = AC6C kit + karoserie
„Jeep" + kolizní model + světla + 4× custom zavěšení. Pro AutoEngineerAI je
`chasis.rbxm` reprezentativnější (obsahuje obě větve tvorby odpružení, viz kap. 8).

---

## 3. Hierarchie (zkráceně, plný strom: 815 uzlů)

**[F]** Kořen `0:Model` (jméno prázdné) obsahuje:

```
0:Model (A-Chassis 6C by Novena – jméno nese potomek, kořen je bezejmenný)
├─ 1:Model:Misc                  (sedadla, volant – přes MiscWeld)
├─ 2:Model:Wheels                → 3:Part:FL, 52:Part:FR, 101:Part:RL, 150:Part:RR
│   └─ každé kolo: Model:SuspensionGeometry (SpringBottom/CLower/CUpper/
│     SpringTop/LowerArmB/LowerArmF/Hub/LowerArm/UpperArmF/UpperArmB/UpperArm,
│     Weld, Spring, 8× Hinge, ~18× Attachment) + Model:WheelFixed +
│     Model:SuspensionFixed + Model:Parts (vizuál kola)
├─ 199:Model:Body                → DownforceF, DownforceR, Drag (BodyThrust „T"),
│                                  Engine, Exhaust (zvukové emitory)
├─ 211:ModuleScript:A-Chassis Tune (+ Plugins, A-Chassis Interface ScreenGui,
│                                  README, Initialize)
├─ 428:VehicleSeat:DriveSeat     (Torque 0, MaxSpeed 0, Steer 0 – jen sedadlo,
│                                  NEpohání; vše řídí skripty)
├─ 429:Model:JeepBodyVisual      (Brakes/G1/Hazards/Left/Light/Right modely,
│                                  světla, zrcátka – čistě vizuál)
└─ 792:Model:CollisionParts      (11 kolizních dílů: Front/Kapota/Roof/Back/
                                   BackWheel/Left/Left2/Right2/Right/Sklo/Spodek)
```

**[F]** Klíčová instance mimo strom číslování: `Drive` (LocalScript id 424) a
`Values`/`Controls…` objekty žijí v `A-Chassis Interface` (ScreenGui v
PlayerGui po usednutí – distribuuje `Initialize`), nikoli v `Car` modelu.
`Drive` očekává `script.Parent.Car` (ObjectValue), `IsOn`, `ControlsOpen`,
`Values` – vše vytváří `Initialize`/GUI.

**[P]** Rozvor/rozchod/ride-height: ze souboru nevyčteno (float-CFrame gap, kap. 1).
**[N] → postup:** Studio: změřit `Position` FL–RL (rozvor), FL–FR (rozchod),
výšku DriveSeat/difuzéru; zapsat do `vehicle-data/analyzed/`.

---

## 4. Skripty a moduly (17 souborů, všechny extrahovány 1:1)

**[F]** Kompletní texty jsou v externím scratchi (ne součást vlastněných souborů);
níže inventura s rolemi a přesnými cestami původu:

| Zdroj (id, bajty) | Typ spouštění | Role |
|---|---|---|
| `Drive` (424, 42 093 B) | LocalScript (řidič) | **hlavní fyzika**: vstupy, řízení, motor, převodovka, diferenciály, TCS/ABS, brzdy, flip; smyčky Heartbeat (~60 Hz) + 15 Hz |
| `Initialize` (426, 20 403 B) | Script (server) | stavba podvozku za běhu: kola, nápravy, odpružení, motory #AV/#BV, gyra, váha, weldy, sedadla |
| `A-Chassis Tune` (211, 16 808 B) | ModuleScript | **jediná autoritativní konfigurace** (~150 parametrů) |
| `README` (425, 11 259 B) | ModuleScript | verze + changelog (Drive ji `require` pro tisk verze) |
| `MiscWeld` (427, 1 271 B) | ModuleScript | uživatelské weldy (prázdné – šablona; volá `Initialize`) |
| `Server` (380, 2 337 B) / `Server` (383, 1 342 B) | Script | zvukové RemoteEvent servery (motor, sání) |
| `Controls_AC6` (214, 6 074 B) | LocalScript | přemapování ovládání (GUI) |
| `AC6_MSteer_Camera` (305, 1 101 B) | LocalScript | kamerový režim při mouse-steer |
| `Simulated` (326, 5 677 B) | LocalScript | **SS6 pneumatiky**: tření/opotřebení/kluz (běží `while wait()`) |
| `Gauges_AC6` (352, 9 831 B) | LocalScript | přístroje + výpočet max. rychlostí |
| `LocalScript` (366, 681 B) | LocalScript | spojkový posuvník myši |
| `Ignition` (368, 667 B) | LocalScript | klávesa F – start/vypnutí |
| `HP/TQ Reader` (376, 1 197 B) | LocalScript | čtení HP/TQ z `Values` (GUI) |
| `Aerodynamics` (377, 788 B) | LocalScript | přítlak + odpor (BodyThrust), **obsahuje bug** (kap. 13) |
| `Engine_Sounds` (378, 5 556 B) / `Induction_Sounds` (381, 4 412 B) | LocalScript | zvuky motoru/sání (asset ID + EQ křivky) |

**[F]** Síťový model: server staví (`Initialize`), klient počítá fyziku
(`Drive` + `Simulated` + `Aerodynamics`) jako `LocalScript` řidiče; zvuky přes
`RemoteEvent` (`Plugins`: Engine/Induction). `DriveSeat:SetNetworkOwner(hráč)`.
Důsledek pro AutoEngineerAI: **automatické testy musí běžet s lokálním
„řidičem"** (klientský kontext), nikoli čistě na serveru.

---

## 5. Motor

**[F]** (`Drive` 435–650, 784–930; Tune 144–208.) Kapalinou chlazený model křivky:
předpočítaná keš `NCache/ECache/TCache/SCache` pro každý převod × otáčky 0–redline
(po 100 ot.). Základ: `CurveN(RPM)` – parabola kolem `PeakRPM` × korekce
strmosti `PeakSharpness`, tvar `CurveMult ∈ ~0–1`, škálování přes `EqPoint =
5252` (HP↔lb-ft). Turbo: `HP_T` z `T_Boost × počet × CompressionRatio/10 / 7.5`,
dynamický `_TBoost 0.05–2` s `T_BoostLag` (u dvojitého turba druhý stupeň
`T2_BoostLag`); kompresor: `_SBoost` z otáček × `S_Sensitivity`. Elektrika:
lichoběžník `E_Trans1/E_Trans2/E_Redline` s exponenty `EH_FrontMult/EH_EndMult/
EH_EndPercent`, moment `E_Torque/ET_EndMult/ET_EndPercent`.

**[F]** Aktuální Tune: `Engine=true`, `Horsepower=200`, `IdleRPM=950`,
`PeakRPM=6800`, `Redline=8000`, `PeakSharpness=20`, `CurveMult=.5`,
`Turbochargers=2, T_Boost=7, T_BoostLag=125, T2_BoostLag=250`,
`Superchargers=0`, `Electric=false` (elektro-větev mrtvá),
`ThrotAccel=.05/ThrotDecel=.2`, `BrakeAccel=.2/BrakeDecel=.5`,
`RevAccel=250/RevDecay=75/RevBounce=250`, `IdleThrottle=3`, `Flywheel=500`
(vyšší = rychlejší reakce), `InclineComp=1` (násobič momentu do kopce
`1+lookVector.y×g×…`, zpátečka invertována).

**[F]** Rozsah otáček kola → `_WheelRPM = maxSpin × Ratio × fFDr`
(`fFDr = FinalDrive×FDMult×30/π`, `wDRatio = wDia×π/60`), spojka mísí
`_GoalRPM` a `_WheelRPM` přes `_Clutch` + setrvačnost `Flywheel`; omezovač
sráží `RevBounce` (plný/½ na posledním stupni). `_spLimit` (rad/s motoru kola)
se posílá do `#AV.AngularVelocity`.

**Co lze měnit:** vše parametrem v Tune (bezpečné v rozsazích reálných aut;
`CurveMult>~1`, `PeakSharpness` extrémy → nerealistická špička/„díra" –
**[P]** nestabilita jen jízdní, ne simulační). Skriptem: tvar křivky
(`CurveN`…), přidání map (E85 apod.). Geometrií: nic. Test: ustálené RPM vs.
rychlost na stupeň + čas 0–100 z telemetrie `Values.RPM/Horsepower/Torque`.

---

## 6. Převodovka a spojka

**[F]** (Tune 240–328; `Drive` 653–732 + 809–842.) `Ratios = {R:3.28, N:0,
1:3.827, 2:2.36, 3:1.685, 4:1.313, 5:1, 6:.793}`, `FinalDrive=3.545`,
`FDMult=1.1`. Režimy `TransModes={Semi,Manual,Auto}` (první = výchozí),
`AutoShiftMode=Speed`, `AutoShiftType=DCT` (`ShiftUpTime=.25/ShiftDnTime=.125`),
`AutoUpThresh=-200` (rel. peak), `AutoDownThresh=1400`. Spojka
(`Clutch=true`, typ `Clutch`; alternativy `TorqueConverter`/`CVT` + `TQLock`,
`RPMEngage=3500`): `ClutchEngage=10`, `SpeedEngage=20` SPS, `Stall=true`
(chcípnutí; vyžaduje ignition plugin), `ClutchKick` (launch control,
standardně off). Neutrální limiter off.

**Co lze měnit:** poměry + `FinalDrive/FDMult` parametrem (pozor: `FDMult≠1`
rozhodí `Gauges` max-rychlosti jen vizuálně, fyziku ne – ta čte stejný Tune).
Typ spojky parametrem. Skriptem: logika řazení (`Auto()`), Launch Control.
Test: čas na 400 m, klepání omezovače, rozjezd do kopce (stall).

---

## 7. Pohon a diferenciály

**[F]** (`Drive` 290–304, 937–993; Tune 210–239.) `Config=AWD`,
`TorqueVector=0` (50:50; -1 = 100 % předek). „Driven" kola = podle jména
FL/FR/RL/RR (`Drive` tabulka). Nový dif (`DifferentialType=New`): párové
násobiče FR↔FL, RR↔RL kolem 1 (součet páru = 2), váha plynem
(`FDiffPower=20/FDiffCoast=20`, zadek `40/30`, `Preload=20`); starý dif
(SlipThres/LockThres) ignorován. Rozdělení F/R u AWD **není** středový dif –
předek i zadek dostanou plné `tq` škálované jen `TorqueVector` biasem, tj.
záběr 4 kol bez mezinápravového prokluzu (zjednodušení!).

**Co lze měnit:** `Config`, `TorqueVector`, Power/Coast/Preload parametrem
(bezpečné 0–100; `Preload` vysoký = nedotáčivost + odpor v rejdu).
Skriptem: skutečný středový dif / aktivní vektorování. Test: protáčející se
jedno kolo (zvednuté) vs. přenos – měřit `RotVelocity` kol.

---

## 8. Odpružení

**[F]** Dvě větve (`Initialize` 207–365). V tomto kitu je u všech 4 kol
`SuspensionGeometry` → **custom větev**: `SpringTop→DriveSeat`,
`Hub→Base` weldy, template `SpringConstraint` (4× sériové, jméno `Spring`) se
za běhu přepíše: `Stiffness/Damping/FreeLength=SusLength+PreCompress/
MaxLength=SusLength+ExtensionLim/MinLength=SusLength-CompressLim` (F: 20000/500/
2.7/3.2/2.35; R: stejné), + `BodyGyro Stabilizer` (MaxTorque 0,0,1; D =
`FGyroDampening/RGyroDampening = 50`) + vzhled (`SusRadius=.2` …).
Bez `SuspensionGeometry` by skript stavěl procedurální wishbone (`#SA/#SB`,
`F/RWsBoneLen=4`, `SusAngle=80`, `AnchorOffset`) – v tomto kitu neaktivní,
ale parametry v Tune zůstávají.

**[F]** Kola navíc nesou `BodyGyro Stabilizer` (MaxTorque 1,0,1; D =
`FGyroDamp/RGyroDamp = 100) – tlumení klopení kol; řízení drží `BodyGyro
Steer` na `Arm` (P=100000, D=1000, torque 50000).

**Co lze měnit:** tuhost/tlumení/zdvihy parametrem (bezpečné cca 0.25–4×;
`Stiffness` < ~5000 = dosedání, `Damping` = 0 = houpání; limity
`Min/MaxLength` mimo `FreeLength` = trvalé dosednutí/propnutí). Kinematiku ramen
(custom geometrie) parametrem **nelze** – jen přestavbou dílů/kloubů (kap. 16).
Test: průjezd nerovností – rozkmit, kontakt kol, náklon.

---

## 9. Řízení a geometrie

**[F]** (`Drive` 322–431; Tune 108–143; `Initialize` 145–159, 400–428.)
`SteeringType=New`: `SteerOuter = LockToLock×180/SteerRatio` (2.6×180/15 =
31.2°), `SteerInner = min(Outer−(1−Ackerman)×Outer, 1.2×Outer)`, Ackerman .9.
Aplikace přímo na `Arm.Steer.CFrame` vůči `Base` (kinematicky, ne silou) +
decay `SteerDecay=330` SPS, `MinSteer=10 %`, rychlosti `SteerSpeed=.05/
ReturnSpeed=.1`°/tick, myš `MSteerExp=1`. Camber/caster/toe (vše 0°) se
**aplikují jen natočením kola** (`CFrame.Angles`), ne fyzikou závěsu –
přiznané v Tune („Don't physically apply"). 4WS off (`FWSteer=None`); zadní
osa zamčena weldem (`MakeWeld(base,axle)` pro R kola).

**Co lze měnit:** převod, Ackerman, decay, rychlosti parametrem (bezpečné;
`SteerDecay` nízký = přetáčivé ve vysoké rychlosti). Skutečný odklon/záklon
jen geometrií (kinematika ramen není simulována – camber je vizuální).
**[N]:** `Tune.StAxisOffset` v Tune **chybí**, ale `Initialize:171` ho čte
(`CFrame.new(0, nil, 0)` → za běhu error). Buď je Tune starší než skripty,
nebo vypadl řádek – **nutno ověřit prvním spuštěním ve Studiu** (kap. 17).

---

## 10. Pneumatiky a trakce (SS6)

**[F]** (`Simulated` 196 řádků; `Initialize` 96–125.) Grip = `CustomPhysicalProperties`
kol, přepisované každých `wait()` podle skluzu: poměr
`wheel/(0.774×speed)` → režimy lock (<8 % → ×`WheelLockRatio=1/2`), TCS-off
(>80 % → ×1), prokluz (>130 % → ×`WheelspinRatio=1/1.1`), jinak plná.
Základ `F/RTargetFriction=.7 + Heat`, minimum `.1`, opotřebení `WearSpeed=.4`,
regenerace `RegenSpeed=3.6`, elasticita `.5`, váhy 1. Hustota kol z Tune
(`FWheelDensity/RWheelDensity=.1`) – **hmotnost kola = jediný „parametr
pneumatiky" v Tune**; zbytek v `_WHEELTUNE` tabulce v `Simulated` (mimo Tune!).
Kola = koule (`shape=0/Ball` **[F]** z `Part.shape`), tření se bere z materiálu
dílu × výše uvedené.

**Co lze měnit:** cílovou adhezi/opotřebení **skriptem** (`Simulated`
`_WHEELTUNE`), hustotu kol parametrem. Rozměr pneu = rozměr dílu kola
(geometrie; `wDia` se odvozuje automaticky z `Size.x` největšího hnacího kola).
Test: brzdná dráha z 200 SPS, smykový kruh, teplota/opotřebení v GUI `Tires`.

---

## 11. Hmotnost a těžiště

**[F]** (`Initialize` 473–541; Tune 32–48.) Vše massless kromě kol/náprav;
pak váhový kvádr `#Weight` v `Body`: velikost `WeightBSize =
{7.03, 5.35, 18.11}` (≈ rozměry auta v palcích/10), poloha =
Lerp(střed zadku, střed předku, `WeightDist=55 %`) + `CGHeight=.8` nad mediánem
kol; hustota dopočtena na cílových `Weight=3439 lb` (s cap-varováním ≥2).
`AxleSize=1.5/AxleDensity=.1`, kola `.1`, custom-zavěšení `.01`. Sedící hráč =
massless (váha postavy odebrána, `getPProperties`).

**Co lze měnit:** hmotnost/distribuce/CG parametrem (bezpečné; `CGHeight` > ~2
= převracení, `WeightDist` mimo 0–100 = extrémy schválně povoleny). Skutečné
rozložení (těžký motor vpředu apod.) jen konstrukcí. Test: vážení (součet
`GetMass`), klopení v zatáčce, brzdný ponor.

---

## 12. Brzdy, ABS, TCS

**[F]** (`Drive` 999–1077; Tune 329–338.) Každé kolo má **dva** runtime motory
(`#AV` trakce, `#BV` brzda – `HingeConstraint`, ActuatorType Motor, tvoří
`Initialize` 440–462): `tqOUT = tq/1.5 × (60/GetRealPhysicsFPS) × plyn × TCS ×
on × spojka`; brzda `#BV = (FBrake/RBrakeForce × 60/FPS × brzda × tqABS) +
EBrake×(1−plyn)×(RPM/Redline) + PBrake`. `BrakeForce=2500, Bias=.6`,
`PBrakeForce=5000/Bias=0` (jen zadek), `EBrakeForce=500` (motorová brzda v
redline). ABS: pokud `|RotVel×(Size.x/2) − Velocity| − ABSThreshold(20) > 0`
→ `tqABS=0` (plné přerušení, ne pulzování!). TCS: lineární škrcení
`1 − min(max(0, skluz−TCSThreshold 20)/TCSGradient 20,1) × (1−TCSLimit 10 %)`.
Prahy v **SPS** (studs/s), stavové flagy v `Values` (`ABSActive/TCSActive/
TCSAmt`), přepínače T/Y za jízdy.

**Co lze měnit:** síly/bias/prahy parametrem (bezpečné; `ABSThreshold`→0 =
brzdy téměř nebrzdí). Skriptem: pulzní ABS, brzdný asistent. Test: brzdná
dráha s/bez ABS na suchu, stabilita při brzdění v oblouku.

---

## 13. Aerodynamika a pomocné síly

**[F]** (`Aerodynamics` 22 řádků; `Body` 200/202/204.) Tři `BodyThrust „T"`:
`DownforceF/R.Force = (0, −speed/300 × {125,150}, 0)`, `Drag =
(0,0,speed²×Drag/30)`, `Drag=.34`, `Vol=1` (zvuk větru). Hodnoty **natvrdo ve
skriptu, mimo Tune**.

**[F – chyba v kódu]:** `car.Body.Drag.T.Force = …(car.DriveSeat.Velocity.magnitude^2…)`
– `magnitude` malé-m neexistuje (správně `Magnitude`) → každé vyhodnocení
skončí chybou, **odpor vzduchu se nikdy neaplikuje** (přítlak ano – ten používá
správné `Velocity.Magnitude`). Oprava: jeden znak. Důsledek pro AutoEngineerAI:
maximálka v tomto kitu je bez odporu – po opravě klesne; měření V-max provádět
až po opravě.

**Co lze měnit:** skriptem (konstanty) nebo převodem do Tune. Test: V-max
před/po opravě, vztlak ve 300 SPS.

---

## 14. Constraints a konstrukce (kostra simulace)

**[F]** Sériově: 108× `WeldConstraint` (tuhá karoserie/kola-díly), 72×
`Attachment`, 32× `HingeConstraint` (wishbone-čepy v custom zavěšení,
`LimitsEnabled=1` u 24, `ActuatorType=None`, momenty 0 – pasivní čepy),
4× `SpringConstraint` (template, přepisuje runtime), 3× `BodyThrust` (aero).
Za běhu přibude na kolo: `Arm/Base/Axle/AxleP` (1.5³, `AxleDensity`),
`#SA/#SB` + `SpringConstraint` (jen bez custom geometrie), `BodyGyro Steer`
(P 100000/D 1000/50 kNm), `BodyGyro Stabilizer` na kole i tlumiči, Hinge `#AV/
#BV` (pohon/brzda). Karoserie: `ModelWeld(Body, DriveSeat)`, pak `UnAnchor`
všeho; `DriveSeat` ukotven jen do usednutí. PGS vyžadováno (`PGSIsEnabled`,
jinak error); legacy větev v `Simulated` odkazuje neexistující
`FWLgcyDensity` – mrtvý kód **[F]**.

---

## 15. GUI, hodnoty, telemetrie

**[F]** `Values` (NumberValue 31×: FL/FR/RL/RR, STime, Version, …, RPM, SteerC/T,
TCSAmt, Throttle, Boost*, Horsepower, Hp*, Torque, Tq*; BoolValue 14×: IsOn,
ControlsOpen, ABS(+Active), AutoClutch, MouseSteerOn, PBrake, TCS(+Active),
4× on; StringValue TransmissionMode; Vector3Value 4× OriginalSize + Velocity;
`Car` ObjectValue) – vše čte `Drive`/`Gauges`/`HP reader`. GUI: `AC6_Controls`
(přemapování), `Gauges` (otáčkoměr, rychlost, max-rychlosti z převodů),
`Tires` (stress/wear polygony), myš-spojka, zapalování.
`Gauges:62` čte `_Tune.ElecRedline/ElecTransition2`, Tune má
`E_Redline/E_Trans2` – nekonzistence, projeví se jen v čistě-elektrickém
režimu (zde `Electric=false`, mrtvé) **[F]**.

---

## 16. Matice „co lze měnit čím" + limity

| Oblast | Parametrem (Tune) | Skriptem | Geometrií/konstrukcí |
|---|---|---|---|
| Výkon/křivka | HP, Peak, Redline, Sharpness, CurveMult, turbo/sání, setrvačník, odezvy | tvar křivky, paliva, hybridní logika | — |
| Převodovka | poměry, FD, typy spojky, časy řazení | řadicí logika, LC | — |
| Pohon/dif | Config, Vector, Power/Coast/Preload | středový dif, aktivní vektor | — |
| Odpružení | tuhost/tlumení/zdvihy, gyro-D | dvoubodové tlumení, aktivita | kinematika ramen (custom model) |
| Řízení | převod, Ackerman, decay, rychlosti | mapování, 4WS | reálná geometrie nápravy |
| Pneu/trakce | hustota kol | **`Simulated._WHEELTUNE`** (grip/wear!) | rozměr kol, materiál |
| Hmotnost/CG | Weight, Dist, CGHeight, WBSize | — | rozložení dílů, kolize |
| Brzdy/ABS/TCS | síly, bias, prahy | pulzní ABS, chytré TCS | — |
| Aero | — (mimo Tune!) | konstanty + bugfix | plochy, difuzor (vizuál) |
| Karoserie | barva pružin | MiscWeld | díly, kolize, sedadla |

**Bezpečné [F+P]:** vše v Tune v pásmu reálných aut; `FDMult=1`; prahy
ABS/TCS ≥ ~5 SPS; tuhosti 0.25–4×; CGHeight ≤ ~1.2; WeightDist 30–70.
**Rizikové [P]:** nulové/záporné délky pružin, `Min>MaxLength`, extrémní bias
(0/1), `SteerDecay`→0 ve 300 SPS, `Preload` 100 + uzamčené dify v rejdu
(přetáčení simu), `Flywheel`→0 (kmitání RPM), `ClutchEngage`→0 (rázy).
**Tvrdé limity [F]:** 60Hz Heartbeat + `60/RealPhysicsFPS` škálování (závislost
na FPS!); kola musí být koule/jmenovitě FL-FR-RL-RR (jinak `Drive`/`Simulated`
je ignorují); `DriveSeat` povinný; PGS povinné; fyzika běží na klientu řidiče.

---

## 17. Nalezené chyby a nekonzistence (vše [F], ověřeno ve zdrojích)

1. `Initialize:171` čte neexistující `Tune.StAxisOffset` → podezření na
   runtime error při stavbě nápravy (Tune v souboru klíč nemá; grep celé sady
   negativní). **Blokuje/neblokuje? – ověřit prvním spuštěním ve Studiu.**
2. `Aerodynamics:21` – `Velocity.magnitude` (má být `Magnitude`) → odpor se
   nikdy neaplikuje (kap. 13).
3. `Gauges_AC6:62` – `ElecRedline/ElecTransition2` vs. Tune
   `E_Redline/E_Trans2` (projeví se jen při `Electric=true`).
4. `Simulated` non-PGS větev odkazuje `FWLgcyDensity/RWLgcyDensity` (v Tune
   nejsou) – mrtvé, protože `Initialize` bez PGS skončí chybou.
5. `Drive:62` `_PGear` inicializováno, dále zřejmě nevyužito (kosmetika).

---

## 18. Jak objektivně testovat (návrh pro Test Environment)

**[P]** (postupy, ne výsledky): rovinka 0–400 m (telemetrie `Values.Velocity/
RPM/Gear` → křivka, časy, V-max po bugfixu aero); brzdění ze 150/250 SPS
(dráha, stabilita, ABS on/off); smykový kruh Ø ~100 (nedo/přetáčivost,
vliv `TorqueVector`/difů); nerovnosti (kontakt kol, rozkmit – ANOVA 3 jízd);
slalom (odezva řízení, `SteerDecay` sweep); rozjezd 1 kola ve vzduchu
(funkce difu); spotřeba FPS (`RealPhysicsFPS` vs. `tqOUT` škálování).
Vše opakovat 3×, tolerance ±3 %, stejný povrch/material.

---

## 19. Otevřené body a doporučené další kroky

1. **[N]** Přesné rozměry/CFrame kol a dílů (float-gap, kap. 1) → Studio +
   kalibrace; pak doplnit `vehicle-data/analyzed/`.
2. Spustit kopii ve Studiu (Play, PGS) a potvrdit/vyvrátit body 17.1–17.4.
3. Opravit `magnitude` bug před jakýmkoli měřením V-max.
4. Rozhodnout: `StAxisOffset` doplnit do Tune (např. 0) vs. pin verze skriptů.
5. Zvážit přesun `_WHEELTUNE` a aero-konstant do Tune (jednotná konfigurace
   pro Optimizer).
6. Předat FÁZI 3: pohon je **HingeConstraint-motorový** (ne `VehicleSeat`,
   ne `Motor6D`); veškerá logika klientská; jediný zdroj pravdy = Tune +
   `Simulated`; geometrie ramen mimo parametry.

---

## 20. Shrnutí pro koordinátora

**Hotovo:** binární audit celého `chasis.rbxm` bez zápisu do originálu;
hierarchie 815 instancí, všech 17 Luau zdrojů, kompletní Tune, constrainty,
chyby v kódu, matice změn, limity, testovací návrh – vše výše s rozlišením
F/P/N a přesnými cestami ke zdrojům (ID instancí, `soubor:řádek`).
**Ověřená fakta:** AC6C 1.5 U2.1 (LuaInt fork); pohon Hinge-motory #AV/#BV;
brzdy #BV + on/off ABS a gradientní TCS; SS6 pneumatiky mimo Tune; váha
kvádr+dopočet hustoty; PGS-only; klientská fyzika.
**Nevyřešeno:** přesné float-rozměry (postup v kap. 1/19); runtime chyby
(17.1–17.4) čekají na Studio.
**Soubor:** tento dokument. Mimo něj vytvořena pouze pracovní kopie rbxm
(identická, SHA výše) – žádné jiné zápisy.
