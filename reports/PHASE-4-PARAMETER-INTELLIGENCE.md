# FÁZE 4 – Parameter Intelligence: integrace katalog ↔ mapping ↔ Optimizer (FINAL, koordinátor)

**Verdikt koordinátora: FÁZE 4.1 + 4.2 SPLNĚNY.** F4-01–F4-07 PASS, F4-08 PASS s výhradou
(jednoprvkový prostor — chybí ověřené rozsahy 70/77 MUTABLE+PASS, viz BLOCKED),
F4-09 PASS (po Agentu D; QA re-verifikovala), F4-10 PASS (132 běhů, 128 PASS, 0 FAIL,
4 oprávněné PENDING), F4-11 PASS (rbxm SHA shoda, Simulator read-only), F4-12 PASS.
QA report kompletní (V1–V5, N1 definováno). Níže původní draft Agenta D beze změny.

Tři známé nesoulady (zadání): (1) `verification_status` PASS/PENDING vs `verified` –
VYŘEŠENO; (2) `backend_caps` bez kanonického zdroje – VYŘEŠENO (zdroj = Sim backend);
(3) `engine.peak_torque_nm`/`peak_power_kw` bez Tune protějšku v prostoru –
VYŘEŠENO (z prostoru ven, test explicitního odmítnutí).

---

## 1. IMPLEMENTED (Agent D, tato vlna)

1. **`src/Chassis/mapping_engine.py` – sjednocení `verification_status`.**
   `VERIFIED_STATUS = "PASS"` (kanonický tvar katalogu Agenta A:
   `loader.py: VERIFICATION = ("PASS", "PENDING")`, PASS = ověřeno auditem/kódem [F])
   + `VERIFIED_STATUSES = ("PASS", "verified")` (`map_config` varování i
   `build_search_space` filtr akceptují oba tvary; `"verified"` = starší název ze
   zadání FÁZE 4.2, jen zpětná kompatibilita selftestu Agenta B).
   Důsledek: `build_search_space` na reálném katalogu už nevrací `[]`.
2. **`src/Optimizer/search_space.py` – dynamický prostor z katalogu.**
   `search_space(config, plan)` už neobsahuje pevný trojlístek, ale volá
   `build_search_space(katalog, backend_caps())` a převádí `tune_key → config_path`
   přes katalog. Meze `min/max` vždy z katalogu (ověřený zdroj); krok/jednotka/popisek
   z `PARAM_DEFS`, je-li knob Optimizeru znám. `PARAM_DEFS`, `CORE_ORDER`, `get_param`,
   `set_param`, `_plan_priority` beze změny (čte je `optimizer.py`).
   `engine.peak_torque_nm` v prostoru není (nemá katalogový záznam ani Tune protějšek).
3. **`backend_caps`: kanonický zdroj = Sim backend.**
   `SIM_SUPPORTED_CONFIG_PATHS` v `search_space.py` = množina `config_path`, které
   vyhodnocovací větev prokazatelně čte: `fallback_sim._params`
   (`engine.peak_torque_nm/peak_power_kw`, `transmission.gears/final_drive/shift_rpm/
   shift_time_s`, `tires.grip_long`, `brakes.bias_front`) + `src/Sim/vehicle.py`
   (navíc `engine.idle_rpm/redline_rpm`, `transmission.efficiency/drive`,
   `brakes.torque_Nm`, `tires.grip_lat/mu_road`). `backend_caps()` mapuje tuto
   množinu přes katalog na `tune_key` (jen `MUTABLE_TUNE` se svým klíčem, bez ohledu
   na status – ten filtruje `build_search_space`). Dnešní výsledek na reálném
   katalogu: `['Bias', 'BrakeForce', 'FinalDrive', 'IdleRPM', 'Ratios', 'Redline']`.
4. **`tests/test_f4_integration.py` (nový, 3 testy).**
   Řetěz VehicleConfig → `map_config` → `parameters.tune` → `apply_config` →
   Sim `run_scenario(straight_accel)` → `evaluate` → TestResult + explicitní test
   odmítnutí `engine.peak_torque_nm` s důvodem + test kanonického zdroje caps
   (`Horsepower` v caps není – Sim čte moment/výkon, ne `horsepower`).
5. **Rozhraní katalog ↔ mapping (sémantika, závazně):**
   - `verification_status`: `PASS` = ověřeno auditem/kódem, smí do optimalizace;
     `PENDING` = čeká na Studio/odečet, nikdy do Tune (`map_config` mapuje
     s varováním, `build_search_space` vylučuje). `"verified"` = historický alias.
   - `backend_caps`: seznam Tune klíčů podporovaných Sim backendem (zdroj výše).
     Prázdné caps → prázdný prostor (definováno, `build_search_space` takto funguje).
   - `config_path → tune_key`: převod dává katalog (`config_path` unikátní);
     `tune_key = null` = mimo Tune → vždy `rejected`, nikdy se nevymýšlí.

## 2. VERIFIED (naměřeno, raw výstupy v testech)

- Prostor na reálném katalogu NEPRÁZDNÝ: `build_search_space` = `['Bias']`
  (jediný průnik ověřeno + rozsah + Sim-podpora); před sjednocením `[]` (ověřeno).
- `test_f4_integration`: 3/3 OK, exit 0, RAW blok tištěn (`backend_caps`,
  `tune_space`, `optimizer_space`, `tune_changes`, `rejected`, `adapter_applied`,
  `sim_manifest`, `test_result`); `peak_torque_nm` rejected:
  „neznámý parametr … bez záznamu se nemapuje (nikdy se nevymýšlí)“.
- H suite `tests/run_all.py`: 0 FAIL (viz §5).
- `mapping_engine` selftest: `SELFTEST OK` (zpětná kompatibilita `verified`).
- Optimizer selftest s novým prostorem: viz §5 (rekalibrace NENÍ potřeba –
  degradovaný knob `brakes.bias_front` je v dynamickém prostoru).

## 3. PENDING (čeká, mimo tuto vlnu)

- Studio-verifikace 31 PENDING záznamů katalogu (kap. 4 katalogu Agenta A),
  vč. `StAxisOffset` runtime-výseku a `magnitude` bugu (blokují V-max kampaň).
- Rozšíření `PARAM_DEFS`/wiring pro 6 Tune-knobů s rozsahem mimo Sim
  (`CurveMult`, `Preload`, `FDiffPower/Coast`, `TorqueVector`, `WeightDist`) –
  dnes v prostoru nejsou (Sim je nečte / Optimizer je nezná).

## 4. BLOCKED (co blokuje F4.3)

1. **Chybějící ověřené rozsahy v katalogu** (`min/max = null` u 70/77 MUTABLE+PASS,
   vč. `FinalDrive`, `Horsepower`): prostor je dnes jednoprvkový (`brakes.bias_front`).
   F4.3 (plná optimalizace) vyžaduje doplnění rozsahů z auditu/Studio – bez nich
   není co ladit. Nic se nedomýšlí (pravidlo Agenta A).
2. **`engine.horsepower` vs Sim**: jediná legitimní motorová Tune-cesta, ale Sim
   čte `peak_torque_nm/peak_power_kw` – motorový knob dnes není uzavřený end-to-end
   (mapování Tune-cestou ✓, Sim-odezva ✗). Rozhodnout ve F4.3 (křivka/kalibrace).
3. **Chyby kódu z auditu §17** (dokumentováno, neopravováno): `StAxisOffset`
   (podezření na runtime error), `Velocity.magnitude` (V-max bez odporu).

## 5. NOT IMPLEMENTED (vědomě mimo rozsah této vlny)

- Zápis do Tune/binárky (adaptér READ-ONLY režim; `patched_config` pro Engineering).
- Změny `optimizer.py`, `backend.py`, `autoengineer.py`, schématu VehicleConfig.
- Rekalibrace Optimizer selftestu (nebyla potřeba – viz VERIFIED).
- Geometrie, Studio automatizace, git operace (zakázáno).

## Akceptační evidence

| Požadavek | Výsledek |
|---|---|
| Prostor na reálném katalogu NEPRÁZDNÝ | `['Bias']` → `brakes.bias_front [0, 1]` (bylo `[]`) |
| Integrační test exit 0 + raw | `python3 -m unittest tests.test_f4_integration` → OK (3 testy) + RAW bloky |
| H suite 0 FAIL | `python3 tests/run_all.py` → 132 běhů, 128 PASS, 0 FAIL, 4 PENDING (3 výchozí + 1 Studio-skip Agenta C) |
| Optimizer selftest zelený | `python3 src/Optimizer/selftest.py` → exit 0, 8/8 OK, bias 0.70→0.61, S 8.27→6.71, backend external-src.Sim |
| peak_torque_nm explicitně odmítnut | `rejected` s důvodem, `tune_changes == []` |
