# F4.3 Calibration Backlog – Agent B (Calibration Preparation)

**Vlastník:** Agent B, FÁZE 4.2.1. Vlastněný soubor: `reports/F4-3-CALIBRATION-BACKLOG.md`.
**Datum:** 2026-11-17. Jazyk: česky; identifikátory anglicky.
**Vstupy (READ-ONLY, čteno):** `src/Chassis/catalog/parameters.json` (125 záznamů),
`docs/A-CHASSIS-AUDIT.md` (celý, citace §), `src/Chassis/adapters/achassis_v1.py`,
`docs/MAPPING.md`, `docs/AGENT-RULES.md`. Žádné kódové změny, žádné git operace.
**Zásada:** žádné vymyšlené rozsahy — kde `min`/`max` v katalogu chybí (`null`),
zůstává prázdné; eviduje se pouze zdroj, odkud rozsah získat, a postup ověření.

## 1. Metoda a ověřená fakta

**[F]** Katalog obsahuje 125 záznamů; `MUTABLE_TUNE` je **79**.
Z nich má číselný `min` + `max` pouze **7** (Bias 0–1; CurveMult 0–1; Preload,
FDiffPower, FDiffCoast 0–100; TorqueVector −1–1; WeightDist 0–100).
Zbývajících **72** má `min: null, max: null` — rozsah je nutno teprve stanovit.
**[F]** Dva MUTABLE_TUNE záznamy (`damper`, `spring_stiffness`) mají
`verification_status: PENDING`, `confidence: 0.4` — kandidátní dekód float-lane
(audit §1, §8: symetrie kol nevychází, Studio-verifikace nutná).
**[F]** Výčtové/bool parametry (`Config`, `Clutch`, `TransModes`, přepínače)
nemají číselný rozsah z podstaty — přípustné hodnoty dává výčet v auditu
(Tune:144-328, Drive větve); v tabulce je u nich zdroj = audit § + výčet.
**[P]** Bezpečnostní meze v auditu §16 („bezpečné cca 0.25–4×", „prahy ≥ ~5 SPS",
„CGHeight ≤ ~1.2") jsou předpoklady, ne ověřené `min`/`max` — do katalogu
se bez Studio-měření nezapisují.
**[N]** Skutečné meze všech 72 parametrů bez rozsahu (postup: Studio sweepy S1–S9 níže).

Předpoklady měření (audit §17): (1) před jakýmkoli spuštěním ověřit
`StAxisOffset` runtime error (Initialize:171, chyba č. 1); (2) V-max měřit
až po opravě `magnitude` bugu (Aerodynamics:21, chyba č. 2); (3) `FDMult = 1`
při všech rychlostních měřeních (jinak Gauges lžou, §6).

## 2. Souhrnné počty

| Kategorie (mapování `config_path` prefixu) | Počet | S rozsahem | Bez rozsahu |
|---|---|---|---|
| motor (`engine.*`) | 24 | 1 (CurveMult) | 23 |
| převodovka+spojka (`transmission.*`) | 16 | 0 | 16 |
| pohon+diferenciály (`powertrain.*`) | 6 | 4 (Preload, FDiffPower, FDiffCoast, TorqueVector) | 2 |
| odpružení (`suspension.*`) | 7 | 0 | 7 |
| řízení (`steering.*`) | 10 | 0 | 10 |
| pneumatiky (`tires.*`) | 2 | 0 | 2 |
| hmotnost (`mass.*`) | 6 | 1 (WeightDist) | 5 |
| brzdy (`brakes.*`) | 8 | 1 (Bias) | 7 |
| ostatní | 0 | 0 | 0 |
| **Celkem MUTABLE_TUNE** | **79** | **7** | **72** |

Priorita: **P0** = blokuje F4.3 kalibraci / search_space (7 jmenovaných parametrů
ze zadání); **P1** = přímý jízdní účinek, měřitelné telemetrií; **P2** = kontextový/
přepínačový účinek; **P3** = mrtvá větev / konstanta / kosmetika (neměří se jízdou).

| Priorita | Počet | Parametry |
|---|---|---|
| P0 | 7 | Horsepower, FinalDrive, Ratios, IdleRPM, Redline, BrakeForce, Bias |
| P1 | 41 | viz tabulka |
| P2 | 25 | viz tabulka |
| P3 | 6 | Electric, Engine, EqPoint, Superchargers, SusRadius, FWSteer |

Legenda ověřovacích postupů (vše Studio Play, PGS on, lokální „řidič", 3 opakování, tolerance ±3 %, stejný povrch):
**S1** rovinka 0–400 m (telemetrie `Values.Velocity/RPM/Gear/Horsepower/Torque`);
**S2** brzdění ze 150/250 SPS (dráha, stabilita, ABS/TCS on-off klávesy T/Y,
flagy `ABSActive/TCSActive/TCSAmt`); **S3** smykový kruh Ø~100 (nedo/přetáčivost);
**S4** nerovnosti (rozkmit, kontakt kol, náklon); **S5** slalom (odezva řízení);
**S6** 1 kolo ve vzduchu (funkce difu, `RotVelocity` kol); **S7** volnoběh +
rozjezd do kopce (Stall vyžaduje ignition plugin); **S8** odečet ve Studiu bez
jízdy (Tune tabulka, `SpringConstraint`, `Size` kol, rozvor/rozchod); **S9** sweep
protokol (1 parametr, ostatní fix, krok + 3 opakování).

## 3. Backlog tabulka (všech 79 MUTABLE_TUNE)

| parametr | kategorie | zdroj rozsahu | způsob ověření | priorita |
|---|---|---|---|---|
| Horsepower | motor | audit §5; Drive:435-650,784-930; Tune:144-208 — číselný rozsah chybí, pouze Studio sweep | S1+S9: sweep výkonu, křivka 0–100 + V-max; kříž `Values.Horsepower/Torque` vs. Sim křivka (§6) | P0 |
| IdleRPM | motor | audit §5; Drive:435-650 — rozsah chybí, pouze Studio | S7+S9: sweep volnoběhu, držení otáček, rozjezd, Stall-chování; závislost IdleThrottle | P0 |
| Redline | motor | audit §5; Drive:435-650 (`_spLimit` → `#AV.AngularVelocity`) — rozsah chybí, pouze Studio | S1+S9: omezovač, sražení RevBounce (plné/½ na posledním stupni), V-max na stupeň | P0 |
| FinalDrive | motor | audit §6; Drive:653-732; Tune:240-328 — rozsah chybí, pouze Studio | S1+S9: sweep převodu, `_WheelRPM = maxSpin×Ratio×fFDr`, časy 0–400 m; FDMult=1, Gauges cross-check | P0 |
| Ratios | převodovka+spojka | audit §6; Drive:653-732,809-842; Gauges_AC6 — rozsah chybí (dict R/N/1–6), pouze Studio | S1: V-max na stupeň z Gauges vs. telemetrie, klepání omezovače; strukturální nesoulad list≠dict řeší Agent D (MAPPING.md §6 ř.10) | P0 |
| BrakeForce | brzdy | audit §12; Drive:999-1077 (`#BV` vzorec, škálování 60/FPS) — rozsah chybí, pouze Studio | S2+S9: brzdná dráha 150/250 SPS, závislost na FPS (`RealPhysicsFPS`); ABSThreshold→0 = brzdy téměř nebrzdí | P0 |
| Bias | brzdy | audit §12 (0–1 v katalogu; extrémy 0/1 rizikové [P], §16) | S2+S3: sweep 0.3–0.8 stabilita v oblouku; 0/1 jen bezpečnostní test | P0 |
| PeakRPM | motor | audit §5 (maximum paraboly CurveN) — rozsah chybí, pouze Studio | S1: vrchol křivky vs. řazení (AutoUpThresh rel. peak); sweep kolem 6800 | P1 |
| CurveMult | motor | audit §5 (~0–1 v katalogu; >~1 nerealistická křivka) | S1: tvar křivky, spotřeba nestability při >1 | P1 |
| PeakSharpness | motor | audit §5 (extrémy → špička/díra) — rozsah chybí, pouze Studio | S1+S9: sweep strmosti, jízdní stabilita | P1 |
| RevAccel | motor | audit §5 (interakce Flywheel) — rozsah chybí, pouze Studio | S1+S7: točivost motoru, odezva na plyn | P1 |
| RevDecay | motor | audit §5 — rozsah chybí, pouze Studio | S7: doběh otáček bez plynu | P1 |
| RevBounce | motor | audit §5 (omezovač, ½ na posledním stupni) — rozsah chybí, pouze Studio | S1: chování na redline, závislost Redline | P1 |
| Flywheel | motor | audit §5 (vyšší = rychlejší; →0 kmitání RPM [P]) — rozsah chybí, pouze Studio | S1+S7: mísení `_GoalRPM/_WheelRPM` přes `_Clutch`; sweep shora dolů | P1 |
| ThrotAccel | motor | audit §5 — rozsah chybí, pouze Studio | S1: agresivita odezvy na plyn | P1 |
| ThrotDecel | motor | audit §5 — rozsah chybí, pouze Studio | S7: doběh po ubrání | P1 |
| BrakeAccel | motor | audit §5 (vstup #BV logiky) — rozsah chybí, pouze Studio | S2: náběh brzdného signálu | P1 |
| BrakeDecel | motor | audit §5 — rozsah chybí, pouze Studio | S2: uvolnění brzd | P1 |
| Turbochargers | motor | audit §5 (vzorec HP_T) — rozsah chybí, pouze Studio; MAPPING.md §7: kandidát 0–4 | S1+S9: 0/1/2, špičkový výkon; závislost T_Boost | P1 |
| T_Boost | motor | audit §5 (HP_T = T_Boost×počet×CompressionRatio/10/7.5) — rozsah chybí, pouze Studio; CompressionRatio je UNKNOWN (odečet S8) | S1: plnicí tlak vs. špička; vyžaduje turbo.count ≥ 1 | P1 |
| T_BoostLag | motor | audit §5 (dynamika `_TBoost` 0.05–2) — rozsah chybí, pouze Studio | S1: prodleva náběhu 1. stupně | P1 |
| T2_BoostLag | motor | audit §5 (platí jen při Turbochargers=2) — rozsah chybí, pouze Studio | S1: náběh 2. stupně, jen při počtu 2 | P1 |
| IdleThrottle | motor | audit §5 (drží IdleRPM) — rozsah chybí, pouze Studio | S7: závislost IdleRPM | P1 |
| InclineComp | motor | audit §5 (násobič `1+lookVector.y×g`, zpátečka invertována) — rozsah chybí, pouze Studio | S7: rozjezd do kopce, couvání z kopce | P1 |
| AutoUpThresh | převodovka+spojka | audit §6 (rel. peak) — rozsah chybí, pouze Studio | S1: bod řazení nahoru vs. PeakRPM; závislost AutoShiftMode | P1 |
| AutoDownThresh | převodovka+spojka | audit §6 — rozsah chybí, pouze Studio | S1: bod podřazení 1400 ± sweep | P1 |
| ShiftUpTime | převodovka+spojka | audit §6 (DCT 0.25) — rozsah chybí, pouze Studio | S1: prodleva výkonu při řazení | P1 |
| ShiftDnTime | převodovka+spojka | audit §6 (DCT 0.125) — rozsah chybí, pouze Studio | S1: prodleva při podřazení | P1 |
| ClutchEngage | převodovka+spojka | audit §6 (→0 rázy [P]) — rozsah chybí, pouze Studio | S7: záběr, závislost Flywheel | P1 |
| FDMult | převodovka+spojka | audit §6 (≠1 rozhodí Gauges jen vizuálně) — rozsah chybí, pouze Studio | S1: měnit jen samostatně (konflikt FD×FDMult, MAPPING.md §4); provozně = 1 | P1 |
| Preload | pohon+diferenciály | audit §7 (0–100 v katalogu; vysoký + zamčené dify = přetáčení [P]) | S3+S6: sweep, odpor v rejdu | P1 |
| FDiffPower | pohon+diferenciály | audit §7 (0–100 v katalogu) | S3+S6: váha násobiče pod plynem | P1 |
| FDiffCoast | pohon+diferenciály | audit §7 (0–100 v katalogu) | S3+S6: váha násobiče bez plynu | P1 |
| EBrakeForce | brzdy | audit §12 (`EBrake×(1−plyn)×(RPM/Redline)`) — rozsah chybí, pouze Studio | S2+S7: motorová brzda v redline; závislost Redline | P1 |
| PBrakeForce | brzdy | audit §12 (jen zadek, bias 0) — rozsah chybí, pouze Studio | S2: ruční brzda, smyk zadku | P1 |
| ABSThreshold | brzdy | audit §12 (SPS; →0 = brzdy téměř nebrzdí) — rozsah chybí, pouze Studio | S2+S9: práh `\|RotVel×(Size.x/2)−Velocity\|`; bezpečně ≥ ~5 SPS (§16 [P]) | P1 |
| TCSThreshold | brzdy | audit §12 (SPS, gradientní vzorec) — rozsah chybí, pouze Studio | S2+S6: práh prokluzu; bezpečně ≥ ~5 SPS (§16 [P]) | P1 |
| TCSGradient | brzdy | audit §12 (strmost škrcení) — rozsah chybí, pouze Studio | S2+S6: strmost `1−min(max(0,skluz−práh)/gradient,1)×(1−limit)` | P1 |
| TCSLimit | brzdy | audit §12 (zbytkový moment 10 %) — rozsah chybí, pouze Studio | S2+S6: limit + flagy TCSActive/TCSAmt | P1 |
| Stiffness | odpružení | audit §8 (PENDING kandidátní dekód; F/R 20000; <~5000 dosedání [P]) — rozsah chybí, nejdřív S8 | S8: odečet `SpringConstraint.Stiffness` ve Studiu (symetrie F/R!); pak S4 sweep 0.25–4× | P1 |
| Damping | odpružení | audit §8 (PENDING kandidátní dekód; F/R 500; =0 houpání) — rozsah chybí, nejdřív S8 | S8: odečet `SpringConstraint.Damping`; pak S4 sweep, závislost Stiffness | P1 |
| SteerDecay | řízení | audit §9 (330 SPS; nízký = přetáčivé ve vysoké rychlosti) — rozsah chybí, pouze Studio | S5+S1: sweep útlumu, vysoká rychlost | P1 |
| LockToLock | řízení | audit §9 (`SteerOuter` = 2.6×180/15 = 31.2°) — rozsah chybí, pouze Studio | S5: rejd vs. SteerRatio; závislost SteerRatio | P1 |
| SteerRatio | řízení | audit §9 (15) — rozsah chybí, pouze Studio | S5: převod, vstup SteerOuter vzorce | P1 |
| Ackerman | řízení | audit §9 (0.9; `SteerInner` vzorec, cap 1.2×Outer) — rozsah chybí, pouze Studio | S5+S3: geometrie rejdu vnitřní/vnější kolo | P1 |
| Weight | hmotnost | audit §11 (3439 lb; hustota kvádru dopočtena, cap-varování ≥2) — rozsah chybí, pouze Studio | S8: vážení `GetMass` součet; S1+S2: vliv na časy/dráhu; převod lb→kg až runtime (MAPPING.md §6 ř.12) | P1 |
| WeightDist | hmotnost | audit §11 (55 % v katalogu 0–100; mimo 0–100 extrémy schválně povoleny) | S3+S2: poloha kvádru Lerp + CGHeight; provozně 30–70 (§16 [P]) | P1 |
| CGHeight | hmotnost | audit §11 (0.8; >~2 převracení, bezpečně ≤~1.2 [P]) — rozsah chybí, pouze Studio | S3: klopení v zatáčce, brzdný ponor; sweep 0.5–1.2 | P1 |
| Clutch | převodovka+spojka | audit §6 — výčet Clutch/TorqueConverter/CVT (není číselný rozsah) | S7: větev spojkové logiky; TQLock/RPMEngage jen pro měnič/CVT | P2 |
| RPMEngage | převodovka+spojka | audit §6 (3500 rpm, větev měniče/CVT) — rozsah chybí, pouze Studio | S7: jen při měničové větvi; při Clutch ignorováno | P2 |
| SpeedEngage | převodovka+spojka | audit §6 (20 SPS, spojení `_GoalRPM/_WheelRPM`) — rozsah chybí, pouze Studio | S7: záběr za jízdy | P2 |
| Stall | převodovka+spojka | audit §6 (bool; vyžaduje ignition plugin) — výčet true/false | S7: chcípnutí motoru, restart klávesou F | P2 |
| ClutchKick | převodovka+spojka | audit §6 (bool launch control, standardně off) — výčet true/false | S1: startovací procedura | P2 |
| AutoShiftMode | převodovka+spojka | audit §6 — výčet (Speed/…; Tune:240-328, Drive:653-732) | S1: režim Auto() logiky; S8: odečet výčtu z Tune | P2 |
| AutoShiftType | převodovka+spojka | audit §6 — výčet DCT/…; časy ShiftUp/DnTime | S1: typ automatu; S8: odečet výčtu | P2 |
| TransModes | převodovka+spojka | audit §6 — výčet [Semi,Manual,Auto], první = výchozí | S1: výchozí chování převodovky; S8: odečet pořadí | P2 |
| Config | pohon+diferenciály | audit §7 — výčet FWD/RWD/AWD (není středový dif — zjednodušení!) | S6+S3: hnaná kola dle jmen FL/FR/RL/RR; AWD bez mezinápravového prokluzu | P2 |
| DifferentialType | pohon+diferenciály | audit §7 — výčet New/Old (starý dif ignorován) | S6: párové násobiče kolem 1 (součet páru = 2); S8: odečet | P2 |
| TorqueVector | pohon+diferenciály | audit §7 (−1–1 v katalogu; 0 = 50:50; −1 = 100 % předek) | S3+S6: předozadní bias; není středový dif | P2 |
| FGyroDamp | odpružení | audit §8 (D=100, MaxTorque 1,0,1; BodyGyro kol) — rozsah chybí, pouze Studio | S4: stabilizace klopení kol F; symetrie k R | P2 |
| RGyroDamp | odpružení | audit §8 (100, symetricky k F) — rozsah chybí, pouze Studio | S4: symetrie k F | P2 |
| FGyroDampening | odpružení | audit §8 (D=50, MaxTorque 0,0,1; Stabilizer tlumiče) — rozsah chybí, pouze Studio | S4: tlumení klopení jednotky tlumiče F | P2 |
| RGyroDampening | odpružení | audit §8 (50) — rozsah chybí, pouze Studio | S4: symetrie k F | P2 |
| MinSteer | řízení | audit §9 (10 %; ovladatelnost ve vysoké rychlosti) — rozsah chybí, pouze Studio | S5+S1: minimální rejd; závislost SteerDecay | P2 |
| SteerSpeed | řízení | audit §9 (0.05 °/tick; kinematicky na `Arm.Steer.CFrame`) — rozsah chybí, pouze Studio | S5: rychlost rejdu | P2 |
| ReturnSpeed | řízení | audit §9 (0.1 °/tick; centrování) — rozsah chybí, pouze Studio | S5: rychlost vracení | P2 |
| MSteerExp | řízení | audit §9 (exponent 1; kamera AC6_MSteer_Camera) — rozsah chybí, pouze Studio | S5: křivka myši; S8: kontrola GUI větve | P2 |
| SteeringType | řízení | audit §9 — výčet New/Old (nová větev SteerOuter/Inner) | S5: větev výpočtu; S8: odečet | P2 |
| FWheelDensity | pneumatiky | audit §10 (0.1; jediný „parametr pneumatiky" v Tune) — rozsah chybí, pouze Studio | S8: hmotnost kola; grip je `_WHEELTUNE` v Simulated (mimo Tune!) | P2 |
| RWheelDensity | pneumatiky | audit §10 (0.1) — rozsah chybí, pouze Studio | S8: symetrie k F | P2 |
| AxleSize | hmotnost | audit §11 (1.5; runtime díly 1.5³) — rozsah chybí, pouze Studio | S8: geometrie Arm/Base/Axle/AxleP; vliv na hmotnost | P2 |
| AxleDensity | hmotnost | audit §11 (0.1; custom-zavěšení .01) — rozsah chybí, pouze Studio | S8: hustota náprav; vážení | P2 |
| WeightBSize | hmotnost | audit §11 ([7.03,5.35,18.11] ≈ rozměry auta) — rozsah chybí, pouze Studio | S8: rozměr kvádru #Weight; závislost Weight | P2 |
| Engine | motor | audit §5 — výčet true/false (spalovací větev; elektro mrtvá) | S8: přepínač; při false celá větev neaktivní | P3 |
| Electric | motor | audit §5 — výčet true/false (mrtvá větev; Gauges mismatch chyba č.3) | P3: neměřit jízdou, dokud Electric=false; E_Trans/E_Redline/E_Torque jsou UNKNOWN (S8 odečet) | P3 |
| EqPoint | motor | audit §5 — fyzikální konstanta 5252 (HP↔lb-ft), ne ladicí knob | P3: neměnit; S8: kontrola hodnoty v Tune | P3 |
| Superchargers | motor | audit §5 (0 = větev neaktivní; `S_Sensitivity` UNKNOWN) — rozsah chybí, pouze Studio | P3: při 0 neměřit; S_Sensitivity nejdřív S8 odečet | P3 |
| SusRadius | odpružení | audit §8 (0.2; vzhled pružiny, Template) — vizuální | P3: vzhled; jízdně neměřit | P3 |
| FWSteer | řízení | audit §9 (None = 4WS off; zadní osa weld `MakeWeld`) — výčet | P3: 4WS off; změna = konstrukční zásah | P3 |

Rozdělení priorit: P0 = 7, P1 = 41, P2 = 25, P3 = 6 (součet 79).

## 4. Prioritní backlog F4.3 (pořadí prací)

1. **P0 – týden 1 (blokuje search_space):** S8 odečty (Tune klíče RDiff/PBrake-bias/
   CompressionRatio/S_Sensitivity, `Size` kol, rozvor/rozchod) + ověření chyby
   č. 1 (StAxisOffset) + oprava chyby č. 2 (magnitude) → pak S1 sweepy
   Horsepower/FinalDrive/Ratios/Redline/IdleRPM + S2 sweepy BrakeForce/Bias.
2. **P1 – týden 2:** křivka motoru (PeakRPM/CurveMult/Sharpness/Flywheel/Rev*),
   turbo (po S8 odečtu CompressionRatio), řazení (Auto*/Shift*), dify (Preload/
   FDiff*/TorqueVector), podvozek (Stiffness/Damping po S8!), řízení, TCS/ABS,
   hmotnost. Každý parametr: S9 protokol, 3 opakování, telemetrie do
   `vehicle-data/analyzed/`.
3. **P2 – týden 3:** přepínače/větve (Clutch, Config, DiffType, TransModes,
   AutoShift*, Stall, Kick, RPM/SpeedEngage), odezvy signálů, gyro-D, hustoty,
   WeightBSize/Axle*.
4. **P3 – odložit:** Engine/Electric/Superchargers/EqPoint/SusRadius/FWSteer (mrtvé /
   konstantní / vizuální). Do search_space nepatří (MAPPING.md §5: filtry
   `MUTABLE_TUNE + verified + min<max + used_in + backend_caps` — bez rozsahu
   nic neprojde; dnes prochází max. 7 parametrů).
5. **Pravidlo zápisu:** každý stanovený rozsah = `min`/`max` + `source`
   (audit § / Studio protokol S1–S9 s datem) + `verification_status`; PENDING
   (Stiffness/Damping) drží `confidence ≤ 0.4` do S8.

## 5. Motor: bezpečné propojení A-Chassis Horsepower s modelem motoru v Simu

**Zásada (MAPPING.md §6 ř. 1–2):** `engine.peak_torque_nm ≠ Horsepower`,
`engine.peak_power_kw ≠ Horsepower` — bez definovaného převodu se nepřepisuje;
`map_config` obojí odmítá. `Horsepower` (hp, Tune 200) je **jediný výkonový
skalár Tune** a škáluje celou momentovou křivku `CurveN` (audit §5), nikoli
bodový moment. Ztotožnění „výkon = moment" je zakázáno (P = M·ω; bez otáček
převod neexistuje).

Navržené propojení (křivka, ne skalár):

1. **Sim vlastní tvar, Tune vlastní škálování.** Sim model motoru definuje
   normalizovaný průběh momentu `M_norm(RPM)` kotvený na
   IdleRPM → PeakRPM → Redline + `CurveMult`/`PeakSharpness` (tvarové parametry
   zůstávají v Tune, audit §5). A-Chassis `Horsepower` pak nastavuje pouze
   absolutní měřítko: `M(RPM) = M_norm(RPM) × k`, kde `k` se kalibruje tak, aby
   `P(PeakRPM) = M·ω` odpovídal Sim cíli `P_peak` (kW→hp převod explicitně
   v adaptéru/runtime vrstvě, nikdy v úložišti — CONTRACTS §8, MAPPING.md §6 ř.12).
2. **Turbo/kompresor mimo rovnítko.** `HP_T` z `T_Boost×počet×CompressionRatio/
   10/7.5` (audit §5) se přičítá v Drive kódu — Sim nesmí turbo „přičíst"
   podruhé. `CompressionRatio` je UNKNOWN → před kalibrací S8 odečet z Tune;
   do té doby turbo drží default (2 / T_Boost 7 / lagy 125/250).
3. **`EqPoint = 5252` je konstanta**, ne ladicí knob (P3) — HP↔lb-ft škálování
   křivky se jí nemění.
4. **Ověření (S1+S7):** ustálené RPM vs. rychlost na stupeň + čas 0–100 +
   `Values.Horsepower/Torque` vs. predikce Simu; 3 jízdy, tolerance ±3 %;
   V-max až po opravě magnitude bugu. `Flywheel/RevAccel/ClutchEngage` drží
   default, dokud není ukotvena základní křivka (interakce _GoalRPM/_WheelRPM).
5. **Co do search_space:** z motoru smí ladit Optimizer až po F4.3 rozsazích —
   první kandidáti `Horsepower`, `PeakRPM`, `Redline`, `CurveMult`
   (vše P0/P1 s telemetrií S1); `IdleRPM` až po S7 (Stall/rozjezd).

## 6. Otevřené body pro F4.3

**[N]** 72 číselných rozsahů (postup S1–S9 výše); **[N]** názvy klíčů zadních
difů (`RDiffPower?/RDiffCoast?` — audit uvádí jen „zadek 40/30", §7) a PBrake
biasu (hodnota 0 ověřena, název odhad — QA vlna 2); **[N]** hodnoty
`S_Sensitivity`, `CompressionRatio`, `TQLock`, `SusLength/PreCompress/
ExtensionLim/CompressLim`, `StAxisOffset` (chyba č. 1) — vše S8 odečet z Tune
ve Studiu; **[N]** float-rozměry kol/karoserie (audit §1 — kalibrační díl).
Grep negativní na `StAxisOffset` v Tune potvrzen auditem §9/§17 — první spuštění
ve Studiu rozhodne (doplnit vs. pin verze skriptů).
