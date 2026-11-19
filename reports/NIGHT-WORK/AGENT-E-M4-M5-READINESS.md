# Agent E — M4/M5 readiness: inventura + plán (bez implementace)

- Větev: `feat/m2-m3-geometry`, HEAD `9803db3` (ověřeno `git rev-parse --short HEAD`).
- Datum: 2026-11-19. Jazyk: čeština; kód anglicky.
- Pravidla dodržena: RBXM pouze čteno (neotevřeno ani k zápisu), `C:/.DATA/RobloxSimulator` pouze jako citovaný zdroj v hlavičkách modulů (žádný zápis), žádné UNKNOWN se nevymýšlelo, M4/M5 **nejsou** označeny za dokončené, žádný merge PR #2 / `main` / nový PR. Jediný zápis je tento report.
- Ověřené běhy (tato inventura, živě): `src/Chassis/catalog/loader.py --selftest` → `SELFTEST OK` (138 záznamů); `mapping_engine.run_selftest()` → OK (prostor vzorku 6 klíčů); reálný katalog × `backend_caps()` → viz §M5 (nález R1).

---

## M4 — stav fyzikálního modelu (`src/Physics/`)

### M4.1 Existující modely (12 modulů, vše čisté funkce, SI, g=9.81, x vpřed / y vlevo / z vzhůru)

| Soubor | Co umí (funkce) | Stav |
|---|---|---|
| `engine.py` | `torque_at_rpm` (lineární interpolace, clamp), `engine_output` (plyn lineárně, derate, fuel/rev gate — nad redline moment 0), `curve_from_config` (náhradní 3-bodová křivka), `rpm_to_rad_s`/`rad_s_to_rpm`, `validate_curve` | Funkční; křivka buď měřená, nebo `estimated` náhražka |
| `gearbox.py` | `gear_output` (M_out·w_out = M_in·w_in·eff; N=0→(0,0); R znaménko), `update_gear` (hystereze up/down + R-interlock), `total_ratio_for_gear`, `validate_ratios` | Funkční |
| `diff.py` | `shaft_split` (bias = lock·dw/(dw+5.0) k pomalejšímu kolu, invariant Σ=T·eff), `distribute` (FWD/RWD/AWD, konfigurovatelný `front_bias` + `lock_center`) | Funkční; vědomě NEpřebírá chybu zdroje (AWD 50/50 + lock=0 natvrdo) |
| `tires.py` | `compute_slip` (kappa; alpha; guard `TIRE_EPS_MPS=0.5`), `magic_formula`, `compute_grip` (D=mu·Fz, třecí **kruh**, Fz≤0→(0,0)), `tire_forces` | Funkční |
| `brakes.py` | `service_brake` (p·Tmax·bias /2 na kolo), `handbrake` (zadek), `brake_slip`, `abs_modulate` (zjednodušené škrcení, min 30 %) | Funkční |
| `load_transfer.py` | `static_loads` (m·g·b/L), `compute_loads` (Δlong=m·a·h/L; Dlat=2·m·a·h/T; aero; clamp ≤0 + `lifted`), `check_load_sum` (tolerance 0,5 %) | Funkční |
| `mass.py` | `total_mass`, `center_of_mass`, `inertia_cuboid`, `inertia_tensor_point_masses` (plný tenzor k CoM) | Funkční |
| `aero.py` | `drag_force`/`downforce` (½ρv²CdA/ClA), `aero_loads` (+ `front_bias`, `power_loss_W`) | Funkční; NOVÁ implementace dle zamýšlené matematiky (zdroj byl STUB) |
| `steering.py` | `target_angle` (1/(1+r²) ořez), `rate_limit`, `ackermann`, `compute` | Funkční |
| `suspension.py` | `spring_force` (+ doraz, guard <1000 N/m proti záměně N/mm), `damper_force`, `wheel_force` (r²), `travel_check`, `quarter_force`, `anti_roll_bar` (NOVÁ; ve zdroji stub) | Funkční |
| `api.py` | Tenké adaptéry pro `src/Sim/physics_backend.py`: `tire_slip`, `tire_force`, `engine_torque`, `gear_output`, `quasi_static_loads` | Funkční; delegace beze změny fyziky |
| `selftest.py` | Akceptační invarianty (ΣFz, P=M·ω, Σ=T·eff, friction circle, redline řez, řazení, lock) + RAW výstup; exit 0 | Existuje; běží |

### M4.2 Funkční výpočty — co je hotové a co záměrně chybí

- Hotové: statika/kvazistatika L/R symetrie, podélný i příčný přenos, P=M·ω, invarianty převodu/difu, neutrál, hystereze řazení, třecí kruh, ABS-škrcení, Ackermann, čtvrtinový model + ARB.
- Záměrně zjednodušeno (flag `simplified`, ne chyba): třecí **kruh** místo elipsy; bez camberu/teploty/opotřebení/Mz; bez dynamiky plnění motoru; ostrý rev-gate; okamžité řazení (výpadek řeší volající přes `shift_time_s`); algebraická svornost bez teploty/lamel; kvazistatika bez transientů podvozku; ořez řízení heuristikou; CoP jedním číslem.

### M4.3 Pmax/Mmax oddělení

- Odděleno na úrovni modelu: `engine_output` bere celou křivku (tvar ≈ Mmax informace) a `api.engine_torque` přidává výkonový strop `P = tau·omega ≤ Pmax` (cap `peak_power_kw·1000/omega`). Stejný princip používá `fallback_sim._engine_torque` (`min(t_peak, P·1000/omega)`).
- Riziko pro M4: `curve_from_config` odvozuje **oba** body z `peak_torque_nm + peak_power_kw` (vrchol M v 0.55·redline, vrchol P v 0.93·redline) — tj. bez měřené křivky jsou Pmax/Mmax svázané odhadem. Skutečné oddělení vyžaduje měřenou `torque_curve` (brzda/OEM kotva), která dnes neexistuje → viz úkol T-M4-02 (UNKNOWN, neměřit od stolu).

### M4.4 Momentová křivka

- `validate_curve` (≥2 body, rostoucí rpm, Nm≥0) + `torque_at_rpm` (lineární interpolace, clamp na krajích). `engine_output` škáluje plynem lineárně.
- Chybí (plán, ne implementace): měřená křivka vozu, nelinearita plynu, teplotní derate mapa, omezovač místo řezu.

### M4.5 Diferenciál

- `distribute` + `shaft_split` pokrývají FWD/RWD/AWD, `front_bias`, tři svornosti, invariant Σ. Chování locku ověřuje selftest (pomalejší kolo dostane víc).
- Chybí: mapa svornosti vs. teplota/prokluz, mezinápravový dif s vlastní charakteristikou (dnes algebraický bias), kalibrace `lock_*` na datech (dnes `estimated`).

### M4.6 UNKNOWN použití v M4

- Pravidlo je dodrženo technicky: každý modul má `SOURCES` s flagy `measured/estimated/simplified`; odhady jsou přiznané (`mu`, `mf_B_C`, CdA/ClA, `lock`, `bias_front`, tuhosti/tlumiče, `vref`/`max_rate`, CoP).
- Seznam nejistot s dopadem (z `SOURCES`):
  - `engine.throttle_linearity`, `rev_gate_cut` — tvar křivky ve středních otáčkách / chování na omezovači.
  - `gearbox.efficiency`, `shift_rpm/time` — účinnost a body řazení (kalibrační).
  - `diff.front_bias`, `lock*` — split a svornost bez měření.
  - `tires.mu`, `mf_B_C`, kruh místo elipsy — největší nejistota boční dynamiky.
  - `mass.positions_m`, `cuboid_dims` — CoM/setrvačnost z geometrie, ne z vážení.
  - `aero.CdA/ClA/cop_split` — odpor/přítlak odhadem (0.85·š·v heuristika v katalogu).
  - `brakes.max_torque_nm/bias_front` — Tmax z kotoučů, bias ~0.6 kalibrační.
  - `suspension.*` kromě `travel_m` — tuhosti/tlumiče/preload/motion-ratio odhadem.
- Nic z výše uvedeného se v kódu netváří jako měřené; M4 proto **není hotová** — chybí kalibrace na datech (M1/M3 vstupy) a rozhodnutí, které odhady se smí použít pro ladění.

### M4.7 Co z M1 lze použít bez M2

- M1 = referenční profil Mustang GT 2024 EU (`vehicle-data/references/ford-mustang-gt-2024-eu-manual-standard.json`, testy `test_m1_mustang_profile.py`, M1-T01…T07). Bez M2 (geometrie z RBXM) lze z M1 použít: identitu/variantu profilu, tovární skaláry motoru (Pmax/Mmax/redline/idle — jako *cíle*, ne jako měřená křivka), převodové poměry + final drive (OEM tabulky), hmotnostní rámec (curb + řidič), referenční cíle pro acceptance (t_0_100, V-max, brzda). Nelze bez M2: CoM polohu, rozvor/rozchod pro daný asset, poloměr kola, zdvihy, max úhel řízení — to vše váže M2/M3 měření na konkrétním RBXM (`dc8747e0…`, PR #2 OPEN, NEMERGOVAT).

---

## M5 — stav katalogu a mapování

### M5.1 Katalog 138 parametrů (ověřeno)

- `src/Chassis/catalog/parameters.json`: list 138 záznamů, 19 polí (`loader.FIELDS`), validace `loader.validate` + selftest `EXPECTED_COUNT=138` → PASS.
- Kategorie: MUTABLE_TUNE **82** | SCRIPT_CONTROLLED **14** | UNKNOWN **37** | READ_ONLY **3** | STRUCTURE_CONTROLLED **2**.
- `verification_status`: PASS **95** | PENDING **43**. PENDING ⊆ převážně suspension/elektro/geometrie/diferenciálové prahy (úplný seznam 43 id v reportu-příloze kódu; překryv PENDING∩MUTABLE = jen 5: `damper_f`, `damper_r`, `diff_preload_r`, `sus_stiffness_f`, `sus_stiffness_r`).
- `value_type`: integer 49, number 43, null 30, string/boolean/object/array zbytek. Jednotky: 100× prázdné, zbytek SPS/rpm/%/bool/°/tick/s/ks.
- Prefixy `config_path`: engine 36, suspension 23, transmission 17, powertrain 15, steering 11, brakes 9, mass 6, tires 5, ostatní 14+2.

### M5.2 Rozsahy — kritický nález R1

- Ze **82** MUTABLE má `min/max` vyplněno jen **7**: `brake_bias_front` [0,1], `curve_mult` [0,1], `diff_preload_f` [0,100], `front_diff_coast/power` [0,100], `torque_vector` [-1,1], `weight_dist_pct` [0,100]. Zbylých 75 má `min=max=None` (vč. `horsepower`, `final_drive`, `gear_ratios`, `idle_rpm`, `redline_rpm`, tuhosti).
- Důsledek (živě ověřeno): `build_search_space(katalog, backend_caps())` → **`['BrakeBias']`**; `backend_caps()` → 6 klíčů (`BrakeBias, BrakeForce, FinalDrive, IdleRPM, Ratios, Redline`). Optimizer tedy dnes dynamicky ladí **1 knob**. `PARAM_DEFS` v `search_space.py` zná legacy pouze 2 knoby (`transmission.final_drive` [2.5,4.2], `brakes.bias_front` [0.55,0.70]) a `_dynamic_specs()` se reálně nepoužije (FinalDrive má v katalogu null) — v kódu přiznáno jako zbytkové vady D1/D2.
- `engine.peak_torque_nm` / `engine.peak_power_kw` nemají Tune protějšek (MAPPING.md §6/1) a do prostoru nikdy nevstoupí — Sim je čte, Tune je nezná (D2).

### M5.3 Target→Tune mapování (`map_config`, `build_search_space`)

- Funkční a otestované: `tune_changes` vs `rejected` (žádná tichá ignorace), pravidla neznámý→reject / ne-MUTABLE→reject / mimo rozsah→reject / závislost→reject / konflikt (first-wins, abecedně první) / `verification_status`→warning, `None`→skip, `peak_power_kw ≠ horsepower` bez převodu→reject. Selftest A–J prochází (ověřeno).
- `build_search_space`: 5 filtrů (MUTABLE + ověřeno + číselný rozsah + neprázdné `used_in` + backend_caps). Na vzorku vrací 6 klíčů; na reálném katalogu 1 (viz R1) — engine je správně, data (rozsahy) chybí.

### M5.4 Závislosti a konflikty

- Katalog nese strojově `depends_on` (desítky hran: turbo.boost→turbo.count, final_drive↔gear_ratios, sus_stiffness→sus_length/pre_compress, pbrake, tcs_*, weight_*, elektro_*, dif prahy→differential_type…) a `conflicts` (20 záznamů: `differential_type` vs staré prahy, `final_drive_mult` vs `gauge_max_speed_display`, `arm_kinematics` vs wishbone/sus_angle, elektro gauge kolize…).
- `mapping/dependencies.py`: `CATEGORY_RULES` (map_action apply/reject + reason šablony), `KNOWN_DEPENDS` (1: turbo.boost), `KNOWN_CONFLICTS` (1: final_drive_mult vs final_drive). Pokrytí tabulek je **ukázkové**, nikoli úplné — katalogové hrany jsou zdrojem pravdy, tabulky je dokumentují pro A-Chassis.
- Mezera: cyklické závislosti v katalogu (`rev_accel`↔`flywheel`, `peak_rpm`↔`auto_up_thresh`, `steer_ratio`↔`lock_to_lock`, `sus_length`↔`pre_compress`…) — engine je vyhodnocuje vůči `requested+default`, cykly dnes nezpůsobí pád, ale ani nejsou detekovány/hlášeny jako cyklus.

### M5.5 Chybějící change planner

- `src/Optimizer/change_plan.py`: pravidlový `plan_from_diagnosis` v0 (RULES: accel→final_drive +0.15, vmax→final_drive −0.15, brake→bias k 0.60, slip/roll→diagnostické `review_*` mimo prostor). Deterministický, `plan_id` z `diagnosis_id`.
- Co chybí pro M5: **skutečný change planner** = krok mezi Diagnosis a `map_config`: převod `steps[].to` na validovaný `VehicleConfig.parameters` diff (kontrola schématu + katalog min/max + závislosti + konflikty + bezpečnostní obálka max_step), návrh pořadí kroků (nejlevnější/nejbezpečnější první), sloučení více diagnóz do jedné změny, a zpětná vazba `rejected → nový návrh`. Dnes `change_plan` generuje kroky i mimo prostor a optimizer je tiše ignoruje (v kódu přiznáno) — to je místo, kde vzniká díra mezi „doporučeno“ a „aplikováno“.

### M5.6 PENDING zachování

- Pravidlo platí a je vymaháno: UNKNOWN (37) a PENDING (43) se nikdy nemapují (`map_config` reject + `build_search_space` filtr PASS-only; loader vyžaduje `tune_key` jen u MUTABLE). PENDING seznam je vypsatelný (`loader.run_selftest()['pending_studio']`, 43 id).
- Riziko: 5 PENDING∩MUTABLE (`damper_f/r`, `diff_preload_r`, `sus_stiffness_f/r`) jsou přesně podvozkové knoby, které by M5 potřebovala — jejich ověření je závislé na M3/studiu, do té doby zůstávají mimo prostor.

### M5.7 Optimizer — relevantní stav pro M5

- `optimizer.py`: koordinátní sondy ±krok + grid 2 parametrů, `safety_filter` (meze + max_step 2·step), `propose` čte celou historii, rollback pointerem, konec na target_score/max_iterations/CONVERGED. Pracuje nad `PARAM_DEFS` (dnes 2 knoby) — rozšíření na katalogové knoby je plánovaná práce (wiring F4.3).
- `acceptance.py`: A1–A5 (vše musí platit; nižší=lepší; stráž V-max −2 %; SIM vždy `UNCONFIRMED_RUNTIME`).
- `backend.py`: priorita `src/Sim.run_scenario`, jinak `fallback-synth-v0` (manifest flag). Scénáře S1_accel + S3_brake; aliasy metrik.
- `fallback_sim.py`: bodová hmota, ideální převod, řazení při `shift_rpm` s výpadkem `shift_time_s`, trakční strop RWD, odpor+valení; kalibrace MASS 1150 kg / R 0.308 m / CdA 0.70 / MU 0.95 / OPT_BIAS 0.60. Citlivý na final_drive (vnitřní optimum ~3.5–4.0).
- `store.py`/`statistics.py`: append-only historie + best pointer; medián/IQR/Mann-Whitney.
- Testy: `test_f4_mapping.py` (katalog QA), `test_f4_optimizer_effect.py` (bias 0.70→0.62 mění metriku, 5/5 znamének; peak_torque mimo prostor; determinismus), `test_module_contracts.py` (fyzika vs orákula), `test_f4_integration.py`, M2 sada 168 testů zelená, plná sada 372 běhů / 368 PASS / 4 PENDING (dle M2-M3 closeoutu).

---

## Implementační plán M4/M5 (soubor — funkce — vstupy/výstupy — testy — závislosti — rizika)

> Plán je návrh pro koordinátora; **žádná implementace nebyla provedena**.

| ID | Soubor (nový/úprava) | Funkce | Vstupy → výstupy | Testy | Závislosti | Rizika |
|---|---|---|---|---|---|---|
| T-M4-01 | `src/Physics/engine.py` (+) | `load_measured_curve(path)`, `throttle_map` (nelinearita) | CSV/OEM tabulka [(rpm,Nm)] → validovaná křivka; (thr) → efektivní plyn | selftest: monotónnost, P=M·ω, clamp; contracting test vs `curve_from_config` | M1 tovární kotvy; měřená data (brzda) | Bez dat = stále `estimated`; nedomýšlet body |
| T-M4-02 | `src/Physics/engine.py`, `api.py` | Oddělení Pmax/Mmax: křivka nese M(n), Pmax jen strop | měřená křivka + Pmax → `engine_torque` s cap | test: Pmax cap aktivní jen nad zlomem; Mmax z křivky ≠ Pmax/ω záměna | T-M4-01 | Svázaný odhad do dodání křivky |
| T-M4-03 | `src/Physics/diff.py` (+) | Kalibrace `lock_*`, `front_bias` z dat; mapa lock vs dw | telemetrie prokluzů → (bias, lock) | selftest invariant Σ; nová data-driven zkouška symetrie | M1 (typ pohonu), M3/telemetrie | Bez dat zůstat `estimated` |
| T-M4-04 | `src/Physics/tires.py` (+) | Elipsa místo kruhu; load-senzitivita B/C (volitelně) | (kappa, alpha, Fz, mu) → (fx, fy) s elipsou | orákulum: \|F\| ≤ mu·Fz; zpětná kompatibilita kruhu přepínačem | Rozhodnutí koordinátora (změna fyziky!) | **Neměnit bez schválení** — dnes jen plán |
| T-M4-05 | `src/Physics/suspension.py`, `load_transfer.py` | Transientní člen (tlumičová rychlost → Fz dynamika) | zdvihové rychlosti → ΔFz | drop-test/statická rovnováha test | M2 geometrie (M3) | Bez M2/M3 jen algebraika |
| T-M5-01 | `src/Chassis/catalog/parameters.json` (+ `loader.py` beze změny rozhraní) | Doplnit `min/max` pro laděné MUTABLE (min. final_drive, gear_ratios, idle/redline, horsepower, tuhosti…) | audit/kód/studio → ověřené rozsahy; `verification_status` PASS jen s důkazem | loader selftest (138+), `build_search_space` ≠ prázdný | Agent A formát (19 polí); studio pro PENDING | **Nevymýšlet rozsahy**; bez zdroje → PENDING |
| T-M5-02 | `src/Optimizer/search_space.py` | Wiring F4.3: `_dynamic_specs` → `search_space()`, `PARAM_DEFS` rozšířit o krok/jednotku pro nové knoby | katalog min/max + PARAM_DEFS krok → prostor | `test_f4_optimizer_effect` rozšířit; safety_filter test | T-M5-01 (bez rozsahů se prostor nehne) | Legacy meze sladit/odstranit (D1) |
| T-M5-03 | `src/Optimizer/change_plan.py` (nový planner vedle RULES) | `propose_change(diagnosis, config, catalog)` → validovaný diff + pořadí + `rejected→renávrh` | diagnosis + config → ChangePlan dle `contracts/change_plan.schema.json` | contract test; map_config round-trip; determinismus | `mapping_engine`, `contracts/*`, T-M5-01 | Dnes kroky mimo prostor tiše padají — planner to musí uzavřít |
| T-M5-04 | `src/Chassis/mapping/dependencies.py` | Doplnit KNOWN_DEPENDS/CONFLICTS z katalogových hran + detekce cyklů | katalog hrany → tabulky + `docs/MAPPING.md` | selftest cyklu (A↔B hlásí, nepadá) | Katalog jako zdroj pravdy | Cykly dnes nedetekovány |
| T-M5-05 | `src/Chassis/adapters/achassis_v1.py` (+ `registry.py`) | `apply_config` pro nové knoby z T-M5-02 (jen PASS+MUTABLE) | tune_changes → patch report | `test_f4_mapping` + adapter testy | T-M5-01/T-M5-02, M2 RBXM (nezměněno) | RBXM read-only; nic netiše |
| T-M5-06 | `tests/test_m5_*.py` (nové) | M5 acceptance: prostor ≥ N knobů, planner round-trip, PENDING nikdy namapováno | — | exit 0 + RAW | Vše výše | M5 není DONE bez těchto testů |

Pořadí: T-M5-01 → T-M5-02 → T-M5-03 → T-M5-05 → T-M5-04/T-M4-01…05. T-M5-01 je hrdlo (bez ověřených rozsahů se nehne prostor ani planner).

---

## Práce dokončitelné nezávisle na M3 (bezpečné samostatné úkoly)

M3 = geometrie/RBXM; nic níže ji nepotřebuje (žádné čtení RBXM, žádná závislost na M2 výstupech):

1. **S-01 — Katalogové min/max z kódu (ne ze studia).** Z `achassis_v1.py`/auditu dohledat ověřitelné meze pro `final_drive`, `gear_ratios`, `idle_rpm`, `redline_rpm`, `horsepower`, `curve_mult` (ten má), `weight_dist_pct` (ten má); vše s citací `A-CHASSIS-AUDIT.md §` + kódová reference. Bez studia = jen to, co je v kódu/auditu; zbytek zůstává PENDING. (→T-M5-01, část)
2. **S-02 — Cyklus-detektor závislostí.** `dependencies.py` + test: najde cykly v katalogových `depends_on` (dnes min. 4 páry) a hlásí je; engine se nemění. Čistě analytické.
3. **S-03 — Change-planner návrh (papírový + contract test).** Spec `propose_change` (vstupy/výstupy/chybové větve) + test proti `contracts/change_plan.schema.json`; bez napojení na optimizer. (→T-M5-03, fáze spec)
4. **S-04 — Optimizer wiring na sucho.** `search_space._dynamic_specs` převést na volitelný `search_space(dynamic=True)` + testy nad syntetickým katalogem (ne reálným); reálný katalog se nehne, dokud nejsou rozsahy. (→T-M5-02, bez dat)
5. **S-05 — M4 orákula (testy, ne fyzika).** Nezávislé kontrolní výpočty pro `engine/gearbox/diff/tires/brakes/load_transfer` (ručně spočítané hodnoty) jako nový `tests/test_m4_oracles.py`; žádná změna `src/Physics/`.
6. **S-06 — Pmax/Mmax audit.** Tabulka: kde se v kódu Pmax a Mmax mísí/oddělují (`engine.py`, `api.py`, `fallback_sim.py`, `search_space.py`, katalog) + doporučení jediného kanonického toku. Papírové, bez kódu.
7. **S-07 — UNKNOWN/PENDING mapa pro studio.** Z 43 PENDING + 37 UNKNOWN sestavit požadavek na měření (co, jak, priorita pro M5: bias potvrzen; tuhosti/tlumiče/dif prahy/geometrie chybí). Papírové, PENDING zachováno.

Všechny S-úkoly: read-only mimo vlastní nové soubory/reporty, bez RBXM zápisu, bez merge, M4/M5 zůstávají OPEN.

---

## Přílohy (strojově ověřeno při inventuře)

- PENDING 43 id: `anchor_offset_f/r`, `compress_lim_f/r`, `compression_ratio`, `damper_f/r`, `diff_preload_r`, `electric_end_mult/percent`, `electric_front_mult`, `electric_redline/torque*` (7), `electric_trans1/2`, `extension_lim_f/r`, `front/rear_wishbone_len`, `lock_thresh_c/f/r`, `pre_compress_f/r`, `rear_diff_coast/power`, `slip_thresh_c/f/r`, `spring_color`, `steer_axis_offset`, `supercharger_sensitivity`, `sus_angle_f/r`, `sus_length_f/r`, `sus_stiffness_f/r`, `tq_lock`, `wheel_radius`, `wheelbase_etc`.
- MUTABLE s min/max (7): viz §M5.2. Zbylých 75 MUTABLE: `min=max=None`.
- Živý stav: loader SELFTEST OK (138); mapping selftest OK; reálný `build_search_space` = `['BrakeBias']` (R1); `PARAM_DEFS` = 2 knoby; plná sada dle M2-M3 closeoutu 372/368/4 PENDING (nepřebíráno, citováno).
- Neověřeno zde (mimo mandát): Play/runtime validace, studio ground-truth PENDING položek, měřená momentová křivka, hmotnosti vozu.
