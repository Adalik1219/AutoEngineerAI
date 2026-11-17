# QA FÁZE 4 – Parameter Intelligence (Agent C)

**Vlastník:** Agent C – QA. **Vlastněné soubory:** `tests/test_f4_mapping.py`, tento report.
**Pravidla:** česky; `docs/AGENT-RULES.md`; stdlib; žádné git operace; READ-ONLY mimo vlastněné.
**Běh:** `python3 -m unittest tests.test_f4_mapping` → **OK (27 běhů, 1 legitimní PENDING)**;
`python3 tests/run_all.py` → **PASS (132 běhů, 128 PASS, 0 FAIL, 4 PENDING)**.
**Zdroje pravdy (čteno):** `docs/A-CHASSIS-AUDIT.md`, `src/Chassis/adapters/achassis_v1.py`.
Tvrzení Agentů A/B/D nepřevzata – vše níže je vlastní čtení kódu + vlastní testy.

Značení: **[F]** ověřený fakt (vlastní běh/čtení), **[P]** předpoklad, **[N]** neznámé.
Mapování F4-01–F4-12 na body ze zadání je moje rekonstrukce (zadání v repo není):
úplnost, původ+klasifikace, UNKNOWN, ověřené Tune klíče, mapovatelnost, jednotky,
odmítnutí, prostor z ověřených, backend-podpora, test-sady, rbxm, QA-artefakty.

---

## 1. Verdikty F4-01–F4-12

| ID | Bod | Verdikt | Důkaz |
|---|---|---|---|
| F4-01 | Katalog úplný (125/125, 19 polí, unikátní id/cesty) | **PASS** | `test_f4_01_*`: 125 záznamů, 19 polí, kategorie 79/14/2/3/27 **[F]** |
| F4-02 | Původ + klasifikace (provenance, auditní zdroj) | **PASS** | parita ≥100 klíčů katalog↔adaptér (mutable⇔MUTABLE_TUNE/measured); 125/125 zdrojů `A-CHASSIS-AUDIT.md §` **[F]** |
| F4-03 | UNKNOWN zůstává UNKNOWN (27), nic vymyšleného | **PASS** | všech 27 `value/default/min/max None`, `PENDING`; 23 firm-klíčů kryto adaptérem (unknown/immutable), 22/23 doslovně v auditu (viz N1) **[F]** |
| F4-04 | Ověřené Tune klíče (spot-check 12), read-only chráněna, závislosti | **PASS** | 12/12 shoda katalog+adaptér s auditem (§5/§6/§12); READ_ONLY `none`, SCRIPT `script`; závislost turba + všechny `depends_on` tokeny se překládají **[F]** |
| F4-05 | Mapovatelnost (3 vlastnosti vč. motoru) | **PASS** | `Horsepower+FinalDrive+Bias` → Tune; `peak_power_kw≠horsepower`; `peak_torque_nm` správně odmítnut (nemá Tune protějšek) **[F]** |
| F4-06 | Jednotky (hp/rpm/0–1; žádné tiché převody) | **PASS** | unit z katalogu v `tune_change`; `BrakeForce` se nerovná Nm, `Weight` lb→kg řeší runtime (MAPPING.md §6) – engine nic tiše nepřevádí **[F]** |
| F4-07 | Odmítnutí (unknown/read-only/mimo-rozsah/konflikt/závislost) + vstup neporušen | **PASS** | 6 druhů odmítnutí, determinismus (FD×FDMult vítězí abecedně první), deepcopy-test vstupu **[F]** |
| F4-08 | Prostor jen z ověřených (5 filtrů) | **PASS s výhradou** | reálný katalog + caps adaptéru → přesně 7 klíčů (`Bias, CurveMult, FDiffCoast, FDiffPower, Preload, TorqueVector, WeightDist`), vše PASS+s rozsahem+`used_in`; `FinalDrive/Horsepower` bez rozsahu → mimo prostor (viz V2) **[F]** |
| F4-09 | Backend-podpora (prostor jen z backendem podporovaných) | **PASS** | `backend_caps()` v `search_space.py` (zdroj Sim) vrací 6 Tune klíčů; `build_search_space` → `['Bias']`; `search_space()` → `[brakes.bias_front]`, bez `peak_torque_nm`; `test_f4_integration` 3/3 OK – vlastní běh po Agentu D (viz V1) **[F]** |
| F4-10 | Testovací sady zelené (selftesty + repo suite) | **PASS** | `loader --selftest` OK (125), `mapping_engine` SELFTEST OK, `run_all` 132 běhů / 0 FAIL **[F]** |
| F4-11 | rbxm integrita + žádná aplikace neověřených + záznam odmítnutí + provenance | **PASS** | sha256 `dc8747…fefdf` shoduje, 230 421 B, mtime beze změny; adaptér odmítá `S_Sensitivity`/`WarpDrive`; `touched_model_files` prázdné; PENDING 31 **[F]** |
| F4-12 | QA artefakty (testy + tento report + seznam vad) | **PASS** | tento soubor + `tests/test_f4_mapping.py` (vč. nového `test_f4_09_backend_caps_ze_simu_a_prostor_bez_peak_torque`), exit 0 **[F]** |

**[P]** F4-10 „H suite" čtu jako testovací sady (selftesty + `run_all`); jiný význam H
v zadání/repu není.
**[N]** Studio-měření (31 PENDING: `Stiffness/Damping` float-lane §1, `StAxisOffset`
runtime §17.1, V-max až po opravě `magnitude` §17.2) – bez Studia PENDING, nikdy PASS.

---

## 2. Seznam vad a nálezů (soubor:řádka)

1. **V1 – VYŘEŠENO (Agent D), re-verifikováno: backend caps + prostor bez `peak_torque_nm`.**
   Původní FAIL: `src/Optimizer/backend.py` nevystavoval žádné Tune caps a
   `search_space.py` ladil `engine.peak_torque_nm` bez Tune protějšku.
   Agent D přesunul kanonický zdroj caps na Sim backend:
   `src/Optimizer/search_space.py:51` `backend_caps()` mapuje
   `SIM_SUPPORTED_CONFIG_PATHS` (:40, 15 cest) přes katalog na Tune klíče –
   vlastní běh: `['Bias', 'BrakeForce', 'FinalDrive', 'IdleRPM', 'Ratios', 'Redline']`
   (vše neprázdné řetězce, `Horsepower` správně mimo – Sim čte moment/výkon,
   ne Tune `horsepower`) **[F]**.
   `build_search_space(katalog, caps)` → `['Bias']` (neprázdný) **[F]**;
   `search_space()` → `[brakes.bias_front [0, 1]]`, `engine.peak_torque_nm`
   neobsahuje **[F]**; `map_config` ho explicitně odmítá
   („bez záznamu se nemapuje (nikdy se nevymýšlí)") **[F]**;
   `tests/test_f4_integration.py` 3/3 OK **[F]**.
   Verdikt F4-09 změněn FAIL → **PASS**; starý test
   `test_f4_09_backend_bez_tune_caps` nahrazen testem nového stavu
   (`test_f4_09_backend_caps_ze_simu_a_prostor_bez_peak_torque`).

2. **V2 – výhrada (F4-08 / práce F4.3): ověřené klíče bez rozsahu mimo prostor.**
   `final_drive` i `horsepower` jsou PASS, ale `min/max None` (vlastní čtení
   katalogu) **[F]** → 5. filtr `build_search_space` je vyřadí; prostor Optimizeru
   je dnes jednoprvkový (`brakes.bias_front`). Mapování samo je správně (F4-05),
   jen není co ladit. Nic se nedomýšlí – doplnění rozsahů z auditu/Studia je
   práce F4.3. Stejně tak 6 Tune-knobů s rozsahem mimo Sim-podporu
   (`CurveMult, Preload, FDiffPower/Coast, TorqueVector, WeightDist`, viz F4-08)
   v prostoru není, protože je Sim nečte / Optimizer je nezná (wiring F4.3).

3. **V3 – drobnost (jen dokumentační dluh): docstring enginu stále uvádí starý tvar.**
   `src/Chassis/mapping_engine.py:28,35` píší `verification_status == "verified"`,
   kanonický tvar katalogu je `PASS` (`VERIFIED_STATUS`, ř. 55); chování je
   sjednoceno přes `VERIFIED_STATUSES = ("PASS", "verified")` (ř. 56) a selftest
   Agenta B prochází **[F]**. Dopad žádný, doporučeno sjednotit text při příštím
   dotyku souboru.

4. **V4 – drobnost: mrtvá statická mez `peak_torque_nm` v `search_space.py`.**
   `PARAM_DEFS` (:112–125) stále vede `engine.peak_torque_nm` 180–250 Nm a
   `CORE_ORDER`/`_plan_priority` (:129–175) ho řadí, ačkoli dynamický prostor
   (`_dynamic_specs` ← `build_search_space`) ho neobsahuje – nemá katalogový
   záznam ani Tune protějšek **[F]**. Dnes neškodné (filtr ho nepustí), ale mate;
   doporučeno odstranit ve F4.3 při wiringu nových knobů.

5. **V5 – pozorování: motorový knob není end-to-end uzavřen (rozhodnutí F4.3).**
   `SIM_SUPPORTED_CONFIG_PATHS` obsahuje `engine.peak_torque_nm/peak_power_kw`
   (Sim je čte), ale katalog pro ně správně nemá záznam – `map_config` je odmítá
   s důvodem, nikdy je nevymýšlí **[F]**. Tune-cesta `engine.horsepower` tedy
   funguje v mapování (✓), ale Sim na ni nereaguje (✗, čte moment/výkon).
   Rozhodnout ve F4.3 (křivka/kalibrace). Krytí Sim⊆katalog není 1:1 (ze 6 caps
   projde 5 filtry jen `Bias`) – definováno, otestováno, bez tichého chování.

**N1 – definice „22/23 firm-klíčů doslovně v auditu" (F4-03, vlastní běh).**
23 firm-klíčů = UNKNOWN záznamy s pevným pravopisem `tune_key` (bez „?"), tj.
27 UNKNOWN − `spring_color` (bez klíče) − 3 s otazníkem
(`Bias(PBrake)?`, `RDiffCoast?`, `RDiffPower?`) **[F]**.
Všech 23 je kryto adaptérem (`provenance unknown`, `mutable False`) **[F]**.
Doslovný výskyt v `docs/A-CHASSIS-AUDIT.md`: **22/23** (vlastní podřetězcové
hledání) **[F]**. Jediný chybějící je **`FWsBoneLen`** (`front_wishbone_len`,
0 výskytů): audit §8, ř. 222 má jen sdružený token ``F/RWsBoneLen=4``
z neaktivní procedurální větve (bez `SuspensionGeometry`), v němž se doslovně
najde `RWsBoneLen` (1 výskyt), zatímco F-varianta je odvozena symetrií.
Katalog i adaptér ji vedou `UNKNOWN`/immutable/`PENDING`
(`change_method pending-studio`), nic se z ní nemapuje – dopad žádný.