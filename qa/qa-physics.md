# QA-fyzika (vlna 2) — audit src/Physics/*.py a src/Sim/*.py

Vlastník: QA-fyzika. Rozsah: `src/Physics/*.py`, `src/Sim/*.py`. Metoda: vlastní čtení
kódu + vlastní nové testy + analytické výpočty. READ-ONLY mimo tento report.
Kořeny: SI, x vpřed / y vlevo / z vzhůru, g = 9.81. Python 3 stdlib, žádné git operace.

## 1. Rozsah auditu

Čteno celé: `tires.py`, `engine.py`, `gearbox.py`, `diff.py`, `load_transfer.py`,
`suspension.py`, `steering.py`, `aero.py`, `brakes.py`, `mass.py`, `selftest.py`
(Physics); `vehicle.py`, `physics_backend.py`, `config.py`, `run.py`, `scenarios.py`,
`selftest.py` (Sim). Referenční principy KNOWLEDGE-TRANSFER.md §2.1–2.6 použity
jako vzor, ne jako důkaz — každý bod níže je vlastní měření.

## 2. Vlastní testy + RAW výstupy (nové případy, ne rerun cizích selftestů)

Spuštěno `C:/.DATA/AutoEngineerAI`, python3 stdlib.

### T1 linearita MF v nule: d/ds = D·C·B
Numerická derivace `magic_formula` v 0 (krok 1e-6) vs analytika:
`num=76000.0000 ana=76000.0000 relerr=9.35e-11` (D=4000, B=10, C=1.9). PASS.

### T2 friction circle: mřížka kappa×alpha 31×31, Fz=4000, mu=1
`worst |F|/muFz = 1.000000` (<=1). `Fz<=0 → (0,0)` pro 0.0 i −10.0. PASS.

### T3 motor: P = M·n/9550 na 3 bodech křivky [(800,120),(4000,205),(7000,184)]
- 1000 rpm: T=125.312 Nm, P_W=13122.7, P_kW=13.123, P_9550=13121.728
- 4000 rpm: T=205.000 Nm, P_W=85870.2, P_kW=85.870
- 6500 rpm: T=187.500 Nm, P_W=127627.2, P_kW=127.627
`P = M·omega` exaktně (diff 0 až 1.5e-11); `/9550` sedí na 7e-5 relativně
(rozdíl 9550 vs 9549.297 = 2π/60, očekávané). PASS.

### T4 gearbox+diff: zachování výkonu / součty splitů
`gear_output(200,300,st.2,[3.2,2.1,1.5],3.7)`: M_out·w_out = 57000.0000 =
200·300·0.95 exaktne. RWD split Σ=950.0000 = 1000·0.95 exaktne.
Lock: RL=902.5 > RR=47.5 (pomalejší kolo bere víc). AWD front_bias=0.4:
předek 380.0 / zadek 570.0, Σ=950.0. PASS.

### T5 load_transfer: statika ΣFz=m·g, rozdělení b/L
m=1400, a=b=1.35, L=2.7: Σ=13734.0000 = m·g exaktne; přední náprava 6867.0 =
m·g·b/L exaktne. PASS.

### T6 suspension: statická výchylka F/k, znaménko tlumení
x=F/k: 4000/30000=0.13333 → `spring_force`=4000.0 exaktne. Tlumič: +0.5 m/s
(bump) → +1500.0; −0.5 (rebound) → −2000.0; 0 → 0.0. Znaménko správně
(odpor proti směru pohybu). PASS.

### T7 steering: inner>outer, R=L/tan
δ=0.3, L=2.7, T=1.55: left(inner)=0.32727 > right(outer)=0.27682; R=8.728366 =
L/tan(δ) exaktne. PASS.

### T8 aero: škálování v²
drag(10)=42.875 N, drag(20)=171.5 N, poměr 4.0 exaktne. PASS.

### S1 determinismus (vlastní rerun, 2 běhy straight_accel, seed 1, dt=1/240)
`dbd8cb2e8e9c1bfb == dbd8cb2e8e9c1bfb` → bitově shodné. PASS.

### S2 konvergence dt vs dt/2 (straight_accel)
t_0_100: dt=8.9708 s, dt/2=8.9667 s, rel. rozdíl 5e-4; koncové x 219.95 vs
219.81 m. PASS (hluboko pod 15% tolerancí dle KT §2.6).

### S3 energie/sanita (straight_accel, MX-5 config)
nonfinite=0, záporná Fz=0, záporná v=0. Globální bilance: E_motor=986 kJ vs
ΔKE+E_drag=834 kJ (+E_crr≈30 kJ) → poměr 0.85 (zbytek: slip-heating +
shift-cuty — fyzikálně přípustné). Peak decel při brzdě 0.87·g < μ·g. PASS
s výhradou: 354 vzorků v okně t∈[7.38,11.97] má m·a·v > P_motor+20 kW —
artefakt zdokumentované aproximace `_engine_rpm` z rychlosti vozu
(vehicle.py:155-165) + trvalý wheelspin zadku (|slip|>0.5 u 2863/2875 vzorků);
není to globální porušení, ale slabé místo modelu. Viz oprava R5.

### S4 hodnověrnost t_0_100 a brzdy vs analytika
t_0_100 = 8.971 s (fyz. minimum E/Pmax = 3.29 s; reálná MX-5 ND2 ≈ 6.5 s).
Brzda 100–0: 51.42 m, čas 4.68 s (ideál v²/2μg = 39.33 m; reál ≈ 36 m).
Obě čísla řádově správně, pomalejší než reference — vysvětlitelné modelem:
rozjezdová spojka 0.55+0.45·v/4 (vehicle.py:246), výpadek tahu 0.35 s při
řazení, trvalý prokluz zadku, náběh brzdy 0.15 s. Není to FAIL fyziky. PASS.

### S5 počet CSV sloupců
Naměřeno `len(TELEMETRY_COLUMNS) = 30`. Tvrzení agenta C o 33 sloupcích
VYVRÁCENO (i `Sim/selftest.py` EXPECTED_COLUMNS má 30 a prochází). PASS.

### S6 chybějící package-level run_scenario (ARCH §5.3)
ARCH 5.3 předepisuje `run_scenario(config: VehicleConfig, scenario: Scenario,
mode: str) -> RawTelemetry`. Realita: `src/Sim/__init__.py` nic takového
neexportuje (`hasattr(Sim,'run_scenario') = False`); `run.py:43` má
`run_scenario(config_path, scenario_id, dt, seed, out_dir)` — jiná signatura,
jiná úroveň. FAIL → oprava R1.

### S7 mezera builtin-v1 vs src/Physics
`physics_backend.backend_name() = 'builtin-v1'`. Důvod: `src/Physics/api.py`
NEEXISTUJE, takže oba importní pokusy padnou do fallbacku a Sim běží na 100 %
vlastního inline kódu — žádný řádek `src/Physics/*` se při simulaci neprovede
(`vehicle.py` importuje pouze `physics_backend`, grep potvrzeno). Navíc by
signatury stejně neseděly: backend čeká `tire_force(mu_long, mu_lat)` vs
`compute_grip(single mu)`; `engine_torque(rpm, peak…)` vs
`engine_output(curve, …)`; `gear_output(torque, ratio, …)` vs
`gear_output(torque, omega, gear, …)`; `quasi_static_loads(bez aero/gEff)` vs
`compute_loads(aero, gEff, REJECT)`. Rozdílný je i eps-guard:
backend `eps=1.0` (physics_backend.py:56) vs `TIRE_EPS_MPS=0.5` (tires.py:29).
FAIL → oprava R2. Související: `vehicle.py:251-256` řeší AWD natvrdo
`tau/4` a ignoruje `diff.py` (front_bias/lock_center) → oprava R3.

## 3. Verdikt po blocích

| Blok | Verdikt | Důkaz |
|---|---|---|
| tires | PASS | T1, T2 |
| engine | PASS | T3 |
| gearbox+diff (moduly) | PASS | T4 |
| load_transfer | PASS | T5 |
| suspension (modul) | PASS | T6 |
| steering | PASS | T7 |
| aero | PASS | T8 |
| mass/brakes | PASS (převzato ze čtení + cizí selftest zelený; vlastní spot-check bias/součet OK) | selftest ř. 118-121 |
| Sim determinismus | PASS | S1 |
| Sim konvergence dt | PASS | S2 |
| Sim energie/sanita | PASS s výhradou | S3, R5 |
| Sim t_0_100/brzda hodnověrnost | PASS (řádově; pomalejší než reál, vysvětleno) | S4 |
| CSV sloupce (30, ne 33) | PASS + vyvráceno tvrzení 33 | S5 |
| ARCH §5.3 package-level run_scenario | FAIL | S6 → R1 |
| Přepnutí Sim na src/Physics | FAIL | S7 → R2 (+R3, R4) |

Zelená u modulů = důkaz výše, ne převzatá. Cizí selftesty (`Physics/selftest.py`,
`Sim/selftest.py`) jsem spustil jen jako orientaci, verdikty stojí na T1–T8/S1–S7.

## 4. Přesný seznam nutných oprav

- **R1 (FAIL):** `src/Sim/__init__.py` — chybí package-level
  `run_scenario(config, scenario, mode)` dle ARCH §5.3 (existující
  `src/Sim/run.py:43` má signaturu `(config_path, scenario_id, dt, seed,
  out_dir)`). Očekávané: export funkce se signaturou kontraktu, nebo
  oprava ARCH, ne ticho.
- **R2 (FAIL):** `src/Physics/api.py` — soubor CHYBÍ. `src/Sim/
  physics_backend.py:31-48` očekává `tire_slip, tire_force, engine_torque,
  gear_output, quasi_static_loads`; aktivní backend je `builtin-v1`, Sim
  nikdy nevolá `src/Physics`. Očekávané: tenké adaptéry nad `tires`,
  `engine`, `gearbox`, `load_transfer` s přesně těmito signaturami.
- **R3 (FAIL):** `src/Sim/vehicle.py:251-256` — AWD větev `tau_shaft/4`
  natvrdo; ignoruje `parameters.transmission` split i `src/Physics/diff.py`
  (`front_bias`, `lock_center`). Očekávané: volat `diff.distribute`
  (stejná chyba, jakou KT §2.6 vytýká zdroji: AWD 50/50 + lock=0).
- **R4:** `src/Sim/physics_backend.py:56` — `eps=1.0` vs
  `src/Physics/tires.py:29` `TIRE_EPS_MPS=0.5`. Očekávané: jedna sdílená
  konstanta (po R2 přebírá backend hodnotu z `src/Physics`).
- **R5 (výhrada, ne blokující):** `src/Sim/vehicle.py:155-165` (`_engine_rpm`
  z rychlosti vozu) + trvalý wheelspin zadku v `straight_accel` — zkresluje
  lokální výkonovou bilanci (S3). Očekávané: zdokumentovat jako limit v
  hlavičce `vehicle.py`, nebo omezit hnací moment trakčním stropem
  μ·Fz·R. Žádná změna bez rozhodnutí koordinátora (READ-ONLY role QA).
