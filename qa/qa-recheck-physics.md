# QA re-check fyzika (vlna oprav R1–R5) — nezávislé ověření

Vlastník: qa/qa-recheck-physics.md. READ-ONLY mimo tento report. Metoda: vlastní čtení + vlastní běhy ze `C:/.DATA/AutoEngineerAI`, Python 3 stdlib, žádné git operace. Výchozí dokument: `qa/qa-physics.md` §4.

## R1 — package-level `run_scenario(config, scenario, mode)` — POTVRZENO (opraveno)

- `hasattr(src.Sim,'run_scenario') = True`
- RAW: `signatura: (config, scenario, mode='local-sim', dt=0.004166666666666667, seed=0, out_dir=None)`
- RAW: `src: C:\.DATA\AutoEngineerAI\src\Sim\__init__.py`
- Smoke RAW: `run_scenario(dict(SAMPLE_MX5_CONFIG),'straight_accel','local-sim')` → csv+manifest vytvořeny, `csv_exists: True`, `manifest.backend = src.Physics.api`
- Negativní RAW: `mode='BAD'` → `ValueError: Nepodporovany mode 'BAD' (ocekavano 'local-sim')`

## R2 — `src/Physics/api.py`, 5 funkcí, backend — POTVRZENO (opraveno)

- `api.py exists: True`; všech 5 `callable: True` — RAW: `tire_slip True / tire_force True / engine_torque True / gear_output True / quasi_static_loads True`
- RAW: `backend_name: src.Physics.api` (dříve `builtin-v1`)
- Behaviorální RAW shoda backend→api:
  - `slip: (0.2, 0.030002666026849468)`, `PB_vs_API_slip` identické
  - `force: (3163.6252389574274, 2447.749036856426)`
  - `etq: 198.64796429664293`
  - `go: (2249.6000000000004, 11.840000000000002)`
  - `qsl: (3433.5, 3433.5, 3433.5, 3433.5)`

## R3 — AWD větev volá diff — POTVRZENO (opraveno)

- Grep RAW (`src/Sim/vehicle.py`): ř. 265–274 `else: # AWD: split pres src/Physics/diff … t_drive = phys.distribute_drive_torque(tau_shaft, "AWD", front_bias=…, lock_front=…, lock_rear=…, lock_center=…, omega=_om)`; žádné `tau_shaft/4` v AWD větvi (pouze `/2.0` pro RWD/FWD ř. 262/264).
- Behaviorální RAW (`distribute_drive_torque(1000,'AWD',…)`):
  - `bias04: [200.0, 200.0, 300.0, 300.0] sum: 1000.0`
  - `bias05: [250.0, 250.0, 250.0, 250.0] sum: 1000.0`
  - `open (lock=0): [250.0, 250.0, 250.0, 250.0]` vs `locked (lock=1): [450.0, 450.0, 50.0, 50.0]`, `lock_meni: True`

## R4 — eps = 0.5 — POTVRZENO (opraveno)

- RAW: `tires.TIRE_EPS_MPS = 0.5`, `api.TIRE_EPS_MPS = 0.5`, `backend.TIRE_EPS_MPS = 0.5`
- Behaviorální RAW: `PB.tire_slip(0,0,10,0.3,0)[kappa] = 6.0`, očekáváno `(10*0.3)/0.5 = 6.0` — sedí.

## R5 — limit v hlavičce vehicle.py — POTVRZENO (opraveno)

- RAW `head -c 1200 src/Sim/vehicle.py` obsahuje blok `LIMIT (QA vlna 2, R5 — zamerne nemodelovano, nemeni se bez koordinace):` s `_engine_rpm … z rychlosti vozu`, wheelspinem `|slip| > 0.5`, oknem `m*a*v vs P_motor (az +20 kW …)` a větou `Hnaci moment se navic neomezuje trakcnim stropem mu*Fz*R.`

## Verdikt

**PASS** — všech 5 oprav R1–R5 potvrzeno vlastním během. Zbytkové vady: žádné (soubor:řádka — nic).
