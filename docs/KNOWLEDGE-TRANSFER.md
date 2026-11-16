# Knowledge Transfer — RobloxSimulator → AutoEngineerAI

Zdroj: `C:/.DATA/RobloxSimulator`, HEAD `238a934` (ověřeno `git rev-parse`). Audit je **read-only**: zdroj se nikdy neupravuje, neslouží jako runtime závislost.
Vlastník tohoto souboru: technický analytik fyzikálních simulací vozidel.
Jazyk: česky. Identifikátory a kód anglicky.

Společný kontext: `C:/.DATA/AutoEngineerAI/docs/PROJECT-PLAN.md`, pravidla: `C:/.DATA/AutoEngineerAI/docs/AGENT-RULES.md`.

---

## 1. Co zdroj skutečně je (ověřený fakt)

Pure-Luau fyzikální knihovna vozidel (`game/shared/vehicle/`, ~25 modulů) + tenký Roblox-most (`game/server/RobloxAdapter/`, 8 modulů) + lokální testy pod Lune (`tests/`, `tools/Physical_Lab/`).
Testy běží lokálně s planárním hostem, **ne v Roblox enginu**. README/STATUS/CONTROL-RESET shodně: nativní jízdní runtime a bridge nejsou hotové; zelené lokální testy nejsou důkaz funkčního auta v Robloxu.

Rámec (ověřeno): body frame `+x` vpravo, `+y` nahoru, `−z` vpřed (`Tires.luau`, `VehicleTypes.luau` vyžaduje jednotkovou `+y` normálu). Jednotky SI, autorita `Types/SIContract.luau` (`FIXED_DT = 1/240 s`), `Types/EnvironmentSI.luau` (`g = 9.81`). Převod SI↔Roblox jedině `RobloxAdapter/UnitMap.luau`: `1 stud = 0.28 m`, `KG_PER_RMU = 21.952`, síla `/6.14656`, moment `/1.7210368`, rad/s beze změny.

---

## 2. Modul po modulu: problém / matematika / cesta / předpoklady / omezení / vhodnost / co převzít

### 2.1 Pneumatiky

**TireSlip** (`game/shared/vehicle/Tires/TireSlip.luau`, 77 ř.) — `computeSlip(inp)`, `validateInput(inp)`.
Matematika (ř. 58–60): `denom = max(|vx|, eps)`, `kappa = (ω·R − vx)/denom`, `alpha = steer − atan(vy/denom)`.
Předpoklady: rovinný kontakt, osy `+x doprava, +z dopředu`, sdílený `eps`-guard.
Omezení: čistá kinematika bez Fz/μ; `vx < eps` záměrně zkresluje (crawl `0.2/0.5 → kappa −0.4`); couvání/stání je numerický guard, ne fyzika.
Vhodnost: vysoká. **Převzít princip** (vzorce kappa/alpha + eps-guard + fail-fast na NaN/inf).

**TireGrip** (`game/shared/vehicle/Tires/TireGrip.luau`, 92 ř.) — `computeGrip(cfg, kappa, alphaRad, fzN)`, `validateConfig` (`muBase ∈ (0,2]`, B/C > 0).
Matematika (ř. 65–72): Magic-Formula větev `F(s) = D·sin(C·atan(B·s))` zvlášť pro osy, `D = μ·Fz`; sdružení třecí kružnicí `rho = √((Fx0/μFz)² + (Fy0/μFz)²)`, `rho > 1 → škálování 1/rho`; `Fz ≤ 0 → (0,0)`.
Předpoklady: B/C/D patří datům povrchu; směr výslednice se zachovává.
Omezení: **kruh, ne elipsa** (samo přiznáno ř. 4–5); žádná load-senzitivita B/C, camber/toe, teplota, opotřebení, žádný vratný moment Mz; pád za peakem je vlastnost zvolených B/C, ne měřená guma.
Vhodnost: střední–vysoká jako start. **Převzít princip** (MF + friction circle + `Fz ≤ 0 → 0`); pro AutoEngineerAI později elipsa + Mz + load-senzitivita.

**Tires (orchestrátor)** (`game/shared/vehicle/Tires/Tires.luau`, 210 ř.) — `checkWheelForces`, `tangentToBody(fxT, fyT, steer)` (ř. 76), `compute(deps, args)` (ř. 101).
Matematika: rychlost středu kola `ux = vx + yaw·pz − surf.x`, `uz = vz − yaw·px − surf.z` (ř. 164–165); Slip→Grip ×4; `resistTorque = R·fxT` (ř. 198); moment `r×F`, `F = (fxB, 0, fzB)` (ř. 184–186); `forceSumBody.y = 0` (ř. 205).
Předpoklady: `fzN` je **vstup zvenčí** (suspension/contact solver); injektované `deps = {slip, grip}`, žádný `require`/Roblox API.
Omezení: **modul žádné Fz nepočítá**; planární model, normála jen `+y`.
Vhodnost: vysoká jako architektura. **Převzít princip** (DI závislostí, `r×F` momenty, tangenciální `resistTorque`, testovatelnost bez enginu).

### 2.2 Řízení

**Steering** (`game/shared/vehicle/Controls/Steering.luau`, 108 ř.) — `compute(cfg, state, input, vMps, dt, wheelbaseM, trackM) → (delta, deltaL, deltaR, newState)`, `validateConfig` (`maxAngle ∈ (0,1]` rad).
Matematika: `target = clamp(input,−1,1)·maxAngle / (1 + (|v|/vref)²)` (ř. 64–66); rate-limit `δnew = δold + clamp(target − δold, ±maxRate·dt)` (ř. 68); Ackermann `R = L/tan|δ|`, `inner = atan(L/(R−T/2))`, `outer = atan(L/(R+T/2))` (ř. 75–88).
Předpoklady: stav se nemutuje; geometrie čísly parametrem.
Omezení: čistá kinematika záměru — bez poddajnosti, bez momentu ve volantu; ořez `1/(1+r²)` je heuristika; `|v|` symetrie ignoruje nestabilitu zpátečky.
Vhodnost: vysoká. **Převzít princip** (rate-limit + rychlostní ořez + Ackermann L/R). Testy: Ackermann inner 0.3335 / outer 0.2725 při `δ = 0.3`, ořez `0.6/101` při 100 m/s — kryjí kinematiku, NE slalom vozu v čase ani zpoždění aktuátoru.

### 2.3 Přenos hmotnosti

**WeightTransfer** (`game/shared/vehicle/Chassis/WeightTransfer.luau`, 224 ř., deklarovaná kvazistatika) — `checkLoadSum(loads, mass, g)` (tolerance 0,5 %, ř. 71), `computeLoads(mass, aM, bM, h, L, T, aLong, aLat, aVert, g, aeroN, zCopM)` (ř. 101).
Matematika (ř. 167–191): `gEff = g + aVert`; `Ff = m·gEff·b/L`, `Rr = m·gEff·b…a/L`; `Δlong = m·aLong·h/L`; `Dlat = 2·m·aLat·h/T` jako diference L−R, strany `±Dlat/2`, split náprav statickým `b/L`; `raw ≤ 0 → clamp 0 + lifted`, `liftedEquivalentKg_1g = max(0, −Σneg/g)` (1-g ekvivalent).
Předpoklady: ustálené/pomalé manévry; caller ručí za konzistenci `mass/g`; striktní `aM + bM == L`; `gEff < 0 → REJECT`.
Omezení: žádná setrvačnost neodpružených hmot, tlumiče, zdvih; laterální split `b/L` je **provizorní alokační předpoklad** (test to říká výslovně); clamp porušuje `Σ = m·g` (řeší až `VehicleDynamics`).
Vhodnost: střední jako kvazistatický odhad. **Převzít princip** (rovnice + `gEff` + aero-split + lifted-ekvivalent); transienty musí dodat podvozek, ne tento modul. Testy: statika 4×3552.5 N, ±5 m/s², laterál, lift práh, freefall, determinismus — NE transient obrubníku.

### 2.4 Kolo / brzdy / podvozek

**Wheel** (`Chassis/Wheel.luau`, 106 ř.) — `computeNetTorque(driveNm, brakeTotalNm, fxN, radiusM, omega, omegaStatic) → (netNm, held)` (ř. 66). `tireT = Fx·R`; hold `|ω| ≤ ωstat ∧ |demand| ≤ brake → (0, true)`; jinak `net = drive − brake·sign(ω) − tireT`. **Neintegruje ω** (dělá Dynamics). Při `ω = 0` mimo hold je brzdný člen 0 (nespojitost signa). **Převzít princip.**

**Brakes** (`Controls/Brakes.luau`) — `service(pedal, cfg)`: `front = p·Tmax·bias`, `rear = p·Tmax·(1−bias)`; `handbrake`: nezávislý zadní okruh; `brakeSlip(ω, R, vx, eps) = clamp(1 − ωR/vx, 0, 1)`, `|vx| < eps → 0`. ABS záměrně odstraněno. **Převzít princip.**

**Suspension** (`Chassis/Suspension.luau`) — `compute(springForceN, damperForceN, suspCfg, corner) → forceN, travelUsedM, toppedOut, bottomedOut`. `F_kolo = r²·(F_pružina + F_tlumič)` (virtuální práce, motion-ratio); zdvih sevřen, flagy včetně rovnosti. Bez vlastní fyziky záměrně — hotové síly dodá volající. **Převzít princip.**
**Springs** — `F = k·x + preload [+ dorazy]`; validace odmítá `stiffness < 1000 N/m` (podezření na N/mm). **Převzít princip + guard.**
**Dampers** — `F = bump·v (v>0) | rebound·v (v<0) | 0`. Čistě rychlostní. **Převzít princip.**
**AntiRollBar** (`Chassis/AntiRollBar.luau`, 30 ř.) — **STUB, jen `validateConfig`**, žádná `compute`. Příčná vazba neexistuje. **Nepřevzít nic** (není co); pro AutoEngineerAI nová implementace `F_arb = k·(dispL − dispR)`.

### 2.5 Motor / převodovka / pohon

**Engine** (`Powertrain/Engine.luau`) — `compute(cfg, rpmRadS, throttle, fuelFlowKgps, derate) → {torqueNm, powerW}`. `τ = throttle·Tmax·derate·revGate·fuelGate`, `P = τ·ω`; `revGate = rpm < redline ? 1 : 0`. **Plochá křivka** (žádná závislost na ω), skok na redline, palivo jen hradlo, `inertiaKgm2` se validuje ale **nepoužije** (mrtvý parametr). **Převzít strukturu** (signatura + hradla + `P = τ·ω`); křivku nahradit skutečnou mapou `τ(ω, throttle)`.

**Gearbox** (`Powertrain/Gearbox.luau`) — `compute(cfg, τin, ωin, gear) → (τout, ωout)`. `τout = sign·τin·ratio·finalDrive·eff`, `ωout = sign·ωin/(ratio·finalDrive)`; `gear 0 → (0,0)`; R se `sign = −1`; invariant `τout·ωout = τin·ωin·eff`. finalDrive žije **právě zde**. Bezestavový ideální převod. **Převzít princip.**

**Transmission** (`Powertrain/Transmission.luau`) — `update(state, cfg, rpm, throttle, v, dt, direction) → (gear, shiftEvent, clutchEng, newState)`. **Okamžité řazení v témže ticku**, hystereze prahy up/down, z 1 se nepodřazuje, `clutchEng` vždy 1 (legacy), `shiftTimerS` vždy 0; R-interlock `|v| < vRevMax` (striktně); **automat bez horního stropu** — strop dělá až `VehicleDynamics`; `dt` se jen validuje (nemá efekt). **Převzít princip** (prahy + interlock + nemutovaný vstup); přidat časování řazení a strop dovnitř.

**Shafts** (`Powertrain/Shafts.luau`) — `compute(cfg, τin, ωin, lock01, ωL, ωR) → (τL, τR)`. `T = τin·eff`; `bias = lock·dω/(dω + 5.0)`; pomalejší `T·(0.5 + 0.5·bias)`, invariant `Σ = T`. `lock = 0 → 50/50`. **Převzít princip** (vzorec biasu + invariant).

**Clutch** (`Powertrain/Clutch.luau`) — odstraněna, stub; cesta momentu Engine → Gearbox → Shafts. **Nepřevzít nic.**

### 2.6 Integrace stavu a momenty

**VehicleDynamics** (`game/shared/vehicle/VehicleDynamics.luau`, ~18 tis. znaků) — jediný krok auta.
- Kola: **explicitní Euler v 48 substepech**, `h = dt/48`, `I·dω/dt = Tdrive − Tbrake − R·Fx` (pozorování karoserie zmrazená). Guardy `TIRE_EPS_MPS = 0.5`, `OMEGA_STATIC_RMPS = 0.5`.
- Karoserie: **neintegruje se v core vůbec** — integruje ji host/Roblox; testy používají lokálního planárního hosta. Krok gravitaci nevrací, host ji přidává právě jednou. `WeightTransfer` dostává kvazistatický odhad `(vel − prevVel)/dt` (tick 0 → 0), `aLong = −az`.
- Motor: kinematická vazba sondou `Gearbox.compute(cfg, 0, 1, gear) → totalRatio = |1/ωprobe|`; `rpm = min(mean|ω_hnaná|·totalRatio, redline)`; neutrál drží otáčky (žádný idle-regulátor).
- DT-refinement test: `DT` vs `DT/2` na LAUNCH, tolerance 15 %.
- **AWD = explicitní 50/50 bez mezinápravového difu** (ř. 264–267: `half = τshaft·0.5`); `lock` je ve `step` natvrdo `0, 0` — svornost je otestovaná unit-testy, ale v kroku auta se **nikdy neuplatní**.
**Převzít princip** (substepping kol + zmrazená observace + fail-fast + `CoreState`/`StepOutput` kontrakt); karoserii a gravitaci řešit v AutoEngineerAI vlastním integrátorem napojeným na Roblox.

**MassProperties** (`Chassis/MassProperties.luau`) — jediná autorita hmoty: `Σm`, vážený CoM, **plný tenzor o CoM** (`Ixx = Σm(ry²+rz²)` atd., produkty `−Σm·rx·ry`); CoG musí ležet mezi nápravami. **Převzít princip + vzorce.**
**ChassisBody** — jen typy + NaN/inf stráž, nic neintegruje. **Nepřevzít nic** (jen vzor guardů).
**Vec3 / DriveInput** — plain-table ops; `throttle −1..1` (znaménko = směr), `steer −1..1`, `brake 0..1`, `handbrake`, `tick`. **Převzít princip.**

### 2.7 Asistence a systémy (STUBY — nepřevzít nic)

`Assists/StabilityControl.luau`, `Assists/TractionControl.luau`, `Controls/Aerodynamics.luau`, `Systems/Cooling.luau`, `Systems/Damage.luau`, `Systems/Fuel.luau`, `Systems/Electronics.luau` — **jen `validateConfig` + typy, žádná `compute`/`step`**. Hlavičky popisují zamýšlenou matematiku (aero `½ρv²CdA/ClA + CoP`; cooling/damage/fuel derate až příští krok), ale kód neexistuje. Testy kryjí jen validace configu. Pro AutoEngineerAI nová implementace.

### 2.8 Roblox-most (mapuje jednotky, nesimuluje)

`RobloxAdapter/UnitMap.luau` — jediná SI↔Roblox autorita (viz §1). **Převzít čísla.**
`Adapter.luau` — legacy hinge bridge, explicitně NE cílový runtime: `computeCommands` (pure, Lune-testovatelná: `motorTargetRadS = omega`, momenty přes `nmToRobloxTorque`), `applyCommands` (Studio-only: `hinge.MotorMaxTorque = drive+brake` — s vlastní pneumatikou nekompatibilní, CR5 ruší). **Nepřevzít logiku, jen konvenci `compute`/`apply` oddělení.**
`ImpulseBridge.luau` — čistá matematika bez engine API: `J = F·dt → /6.14656`, `dL = T·dt → /1.7210368`, bodové impulzy 4 kol, `assertSingleApplication` XOR stráž (režim P XOR režim C, nikdy obojí). Žádné `ApplyImpulse` uvnitř — Studio strana **není hotová**. **Převzít princip** (konverze + XOR stráž).
`Scheduler / Validation / Ownership / Lifecycle / RaycastTrack` — pure lokální poloviny (plán substepů, fail-fast, matice vlastnictví, automat spawn/destroy/reset, `solveCorner` bez `workspace:Raycast`). **Převzít princip** (oddělení pure/Studio poloviny).

---

## 3. Ověření známých omezení (čtením kódu — potvrzeno / vyvráceno)

| Omezení | Verdikt | Citace |
|---|---|---|
| Zjednodušené zatížení kol | **POTVRZENO** | `Tires.luau` ř. 17: `fzN` je vstup zvenčí; modul žádné Fz nepočítá. `WeightTransfer` je kvazistatika, laterální split `b/L` provizorní |
| Chybějící vertikální dynamika | **POTVRZENO** | `Tires.luau` ř. 205: `forceSumBody.y = 0` — planární model; `WeightTransfer` ř. 2–5: transienty musí dodat Suspension |
| Neintegrovaná per-corner dynamika | **POTVRZENO** | `Tires.compute` bere `fzN` hotové; `Suspension.compute` je algebraická mapa bez integračního kroku; drop-test/statická rovnováha nikde |
| AWD 50/50 | **POTVRZENO** | `VehicleDynamics.luau` ř. 264–267: `half = τshaft·0.5`, komentář přiznává chybějící mezinápravový dif; `lock` ve step natvrdo `0, 0` |
| Neověřený runtime | **POTVRZENO** | README/STATUS/CONTROL-RESET: bridge není hotový; vše běží pod Lune s lokálním hostem; `ApplyImpulse` ve Studiu neexistuje |
| Rozdíl lokální test vs Roblox jízda | **POTVRZENO** | Chybí: engine contact solver, proměnlivé dt/substep jitter, latence/replikace, skutečná hmotnost dílů, uzavřená smyčka řízení→skluz→síla→zatížení→ω v čase v enginu |
| Plochý motor | **POTVRZENO (navíc)** | `Engine.luau`: `τ` nezávislé na ω; redline skok; `inertiaKgm2` mrtvý parametr |
| Chybějící asistence/systémy | **POTVRZENO (navíc)** | SC/TC/Aero/Cooling/Damage/Fuel/Electronics/ARB: jen `validateConfig`, žádná fyzika |

Nic z výše uvedeného nebylo vyvráceno.

---

## 4. Testy a validace: co kryjí a co NE

Kryjí (Lune, deterministické, analytické reference): kappa/alpha hrany, MF peak + pád 11,8 % + friction-circle mřížku, Ackermann čísla, rate-limit, WT statiku/kombinace/lift/freefall/determinismus, motor/gearbox/shafts golden hodnoty (`400·2.1·3.7·0.95 = 2952.6`), řazení prahy/interlock, `Tires.compute` přes integrační `wave2_f1_chain_spec`, `vehicle_step_spec` (STATIC/LAUNCH/BRAKE/STOP-REVERSE/STEER/AIRBORNE/DT-konvergence), `vehicle_multiconfig_spec` (torque-split layoutu, corrupt gear 99 musí chybovat, ground-air-ground `maxΔv ≤ 0.5`), `impulsebridge_spec` (bilance `r×J`, XOR stráž).

NEkryjí: `Tires.compute` nemá vlastní unit test; chování vozu v čase (slalom, transient obrubníku); povrchy/teploty/camber/Mz; ABS/TC/SC logiku; integraci moment→ω v enginu; cokoli v živém Robloxu (impulzy, hmotnost dílů, scheduling 240 Hz, replikace, lifecycle).

Filozofie k převzetí: analytické golden hodnoty, hraniční matice, determinismus-seedy, mutační sondy (`Physical_Lab/regression/`), nezávislé křížové reference (`Physical_Lab/reference/f7_*`, `pl10_*`), fail-fast na NaN/inf bez fallbacků.

---

## 5. Fakta / předpoklady / neznámé

**Ověřená fakta:** vše v §2–§4 s citací cesty a funkce. HEAD `238a934`. SI kontrakt, rámec, UnitMap čísla, rovnice slip/grip/steer/WT/shafts/gearbox, 48 substepů Euler kol, karoserie mimo core, AWD 50/50, lock 0, STUB seznam, testovací krytí výše.

**Předpoklady (převzaté, neověřené v Robloxu):** `1 stud = 0.28 m` platí pro cílový rig; `FIXED_DT = 1/240` je dosažitelné schedulerem; kvazistatické Fz stačí jako vstup pneumatik pro první iteraci; explicitní Euler s 48 substepy je stabilní i s reálnými daty A-Chassis; bias-vzorec `lock·dω/(dω+5.0)` je přijatelný model svornosti.

**Neznámé:** skutečné B/C/μ reálných gum (zdroj má 1 CFG); skutečné `τ(ω)` a převody cílového vozu; chování hinge/constraints pod 240 Hz zátěží; latence ownership/replikace; jak A-Chassis skutečně počítá trakci (nezkoumáno zde — patří Chassis Intelligence); výkon 48×4 substepů v enginu.

---

## 6. Rizika a další kroky

**Rizika:** (1) Záměna lokálního passa za důkaz jízdy v Robloxu — nikdy nevydávat simulaci za runtime důkaz (PROJECT-PLAN §2.10). (2) Tiché STUBY — importovat jejich `validateConfig` jako hotovou fyziku. (3) `lock = 0` natvrdo a AWD 50/50 tiše zděděné do terénního vozu. (4) Plochý motor + skok na redline → nerealistická akcelerace. (5) `forceSumBody.y = 0` → žádné skoky/obrubníky. (6) Transmission bez stropu závislý na externím clampu. (7) Nespojitost brzdy při `ω = 0`.

**Doporučené další kroky:** (1) V AutoEngineerAI postavit vlastní integrátor karoserie + gravitaci (core to nedělá). (2) Fz řešit kontaktním/podvozkovým solverem s per-corner stavem, ne jen kvazistatikou. (3) Motorová mapa `τ(ω, throttle)` z referenčních dat skutečného vozu. (4) Mezinápravový dif + konfigurovatelný lock pro AWD. (5) Elipsa + Mz + load-senzitivita pneumatik. (6) Časování řazení + strop stupně dovnitř Transmission. (7) Nativní smoke v Robloxu (lineární/úhlový impulz, static support, launch→brake→steer) před jakýmkoli tvrzením o jízdě. (8) Analýza A-Chassis (`chasis.rbxm`) modulem Chassis Intelligence — tento dokument ji nenahrazuje.

---

## 7. Shrnutí převzetí (princip / část / nic)

| Oblast | Převzít |
|---|---|
| Slip kinematika + eps-guard + fail-fast | **princip + vzorce** |
| MF grip + friction circle + `Fz≤0→0` | **princip**; elipsa/Mz/teploty nově |
| `Tires.compute` orchestrace (DI, `r×F`, `R·fxT`) | **princip** |
| Steering (rate-limit, ořez, Ackermann) | **princip + vzorce** |
| WeightTransfer kvazistatika | **princip + rovnice**; transienty nově |
| Wheel / Brakes / Suspension / Springs / Dampers | **princip + vzorce + guardy** |
| Engine / Gearbox / Shafts | **strukturu + vzorce**; křivku/strop/lock nově |
| VehicleDynamics (substepping, kontrakty stavů) | **princip**; karoserii/gravitaci nově |
| MassProperties (CoM + plný tenzor) | **princip + vzorce** |
| UnitMap čísla; ImpulseBridge XOR stráž; pure/Studio oddělení | **část (čísla + vzor)** |
| ARB / SC / TC / Aero / Cooling / Damage / Fuel / Electronics / Clutch / ChassisBody / Adapter logika | **nic** (stuby nebo legacy) |
| Testovací filozofie (golden hodnoty, hrany, determinismus, mutace, křížové reference) | **princip** |

*Konec dokumentu. Read-only audit dokončen; zdroj `C:/.DATA/RobloxSimulator` nezapsán (ověřeno `git status --short` prázdné — viz závěrečná zpráva).*
