# Implementation Roadmap – backlog M1–M9 (hybridní režim)

**Stav:** návrh v1 (ke schválení). Hlavní technická specifikace pro implementační agenty.
**Cílové vozidlo:** `docs/VEHICLE-SPECIFICATIONS.md`. **Proces:** `docs/HYBRID_WORKFLOW.md`.
**Kritéria:** `docs/ACCEPTANCE_CRITERIA.md`. **Aktuální stav kódu:** `docs/PROJECT_STATUS.md`.
**Pravidla:** `AGENTS.md`, `docs/AGENT-RULES.md`. Česky; identifikátory a kód anglicky.

Závislosti: `M1 ─┐ → M3 ─→ M4 ─┐ → M5 → M6 → M7 → M8 → (M9 propojuje vše)`. `M2 ─┘ ↗`
M1+M2 paralelně; M3 potřebuje M1+M2; M4 potřebuje M1+M2 (může částečně běžet s M3);
M5–M9 sekvenčně. Formát dat mezi moduly: JSON dle `contracts/*.schema.json`; každá
hodnota má jednotku, každý cíl má zdroj nebo označený odhad.

Názvy nových cest níže jsou **navržené** — před implementací ověřit proti skutečnému
repozitáři a použít existující implementaci, kde vyhovuje (`PROJECT_STATUS.md` §2).
Žádné duplicitní moduly. Rozlišovat implementace / test / ověření (stupnice v `PRODUCT_VISION.md` §5).

Výstupní rozložení konfiguračního balíčku (M6, kořen v existujícím `vehicle-data/runs/`):
`vehicle-data/runs/<vehicle_id>/iteration_NNN/{vehicle_profile,geometry_target,physics_target,achassis_changes,test_protocol.md,expected_results,rollback}.json + manifest.json`.

---

## M1 – Vehicle Specification Foundation · priorita P0 · stav: PARTIAL

1. **Cíl:** spolehlivá databáze reálných vozidel; první profil Mustang GT 2024 EU manuál standard.
2. **Odpovědnosti:** datový model specifikace; evidence zdrojů a důvěryhodnosti; validace variant a neznámých údajů; export/import profilu.
3. **Vstupy:** `docs/VEHICLE-SPECIFICATIONS.md`, zdroje [1–3], `vehicle-data/references/_schema.json`.
4. **Výstupy:** `vehicle-data/references/ford-mustang-gt-2024-eu-manual-standard.json`
   (`vehicle_id` kebab-case dle `_schema.json` patternu `^[a-z0-9]+(-[a-z0-9]+)*$`);
   propojení na `contracts/reference_profile.schema.json` polem `source_vehicle_id`.
5. **Datové struktury:** obálka `{value, unit, source, source_type: factory|measurement|aggregator|estimate, confidence 0–1, notes}`; stavy `VERIFIED | ESTIMATED | UNKNOWN` (UNKNOWN = `value: null`).
6. **Navržené soubory:** přednostně rozšířit existující `src/Reference/{loader,validate,compare}.py`
   a `vehicle-data/references/` (žádný paralelní `src/autoengineer/vehicle_specs/` ani `data/vehicles/`).
   Povinná konvence poznámek z `src/Reference/validate.py`: odhad `notes: "ODHAD: …"`,
   chybějící údaj `notes: "CHYBÍ: … + postup doplnění"`; `value: null` + `confidence > 0.5` je chyba;
   `source_type: factory` vyžaduje `confidence ≥ 0.8`.
7. **Závislosti:** žádné (paralelně s M2).
8. **Úkoly:** M1.1 model `VehicleSpecification` · M1.2 oddělené modely motor/převodovka/pneu/geometrie · M1.3 metadata zdrojů (URL, datum, jednotky, autorita) · M1.4 stavy VERIFIED/ESTIMATED/UNKNOWN · M1.5 profil Mustangu · M1.6 oddělení standard GT vs. Performance Pack · M1.7 kontrola kompatibility variant (EU≠US, GT≠Pack) · M1.8 export/import specifikace · **M1.9 výjimka torque_curve: `VEHICLE-DATA.md` §2.3 žádá ≥2 tovární kotvy, pro Mustang existuje 0 — profil proto nese prázdnou křivku se statusem UNKNOWN a zdůvodněním v `notes` (`CHYBÍ: …`); `validate.py` je null-safe (`or {}`), výjimku explicitně zdokumentovat a nesmí se stát precedentem pro domýšlení bodů**.
9. **Unit testy:** načtení Mustangu; chybějící povinné pole → odmítnuto; neplatná převodovka → odmítnuto; záměna EU/US → odmítnuto; neznámá křivka zůstává UNKNOWN; VERIFIED bez zdroje → odmítnuto; smíchání GT/Pack → odmítnuto.
10. **Integration testy:** profil projde `tools/validate_contracts.py`; `source_vehicle_id` linkuje DB záznam s pipeline profilem.
11. **Akceptační kritéria:** M1-T01…M1-T07 dle zadání (vše PASS); každá známá hodnota má zdroj, každá neznámá zůstává neznámá.
12. **Definition of Done:** Mustang se načte jako validní verzovaný profil; zdroje dohledatelné.
13. **Omezení/rizika:** převody, křivka, rozložení hmotnosti, brzdy, aero jsou UNKNOWN — M4 s nimi musí počítat; riziko záměny EU/US a GT/Pack dat.
14. **Stav:** PARTIAL — schémata a 2 referenční vozy existují (civic, gr86), mustang profil chybí.

## M2 – RBXM Inspector & Scale Calibration · priorita P0 · stav: NOT IMPLEMENTED

1. **Cíl:** read-only změřit existující RBXM (kola, nápravy, rozměry) a určit měřítko studs/m.
2. **Odpovědnosti:** parsování RBXM bez zápisu; identifikace 4 kol + náprav; výpočet rozvoru/rozchodů/průměrů; inventář dílů a hmotností; čtení Tune/Script/Structure parametrů; kalibrace `studs_per_meter`.
3. **Vstupy:** pracovní kopie RBXM (nikdy originál).
4. **Výstupy:** `inspection_report.json` + `studs_per_meter` s nejistotou, nebo `BLOCKED` s důvodem.
5. **Vztah:** `k = W_studs / 2.719`, kde `W_studs` je naměřený rozvor; konzistence ověřena přes ≥2 nezávislé rozměry (rozvor + rozchod + průměr kola).
6. **Navržené soubory:** `src/autoengineer/inspection/{rbxm_inspector,geometry_reader,part_inventory,achassis_reader,inspection_report}.py`; `src/autoengineer/units/{conversions,scale_calibration}.py` — ověřit proti `src/common/units.py` (existuje, rozšířit místo duplikace).
7. **Závislosti:** žádné (paralelně s M1).
8. **Úkoly:** M2.1 spike formátu RBXM: v repu **žádná čtečka neexistuje** — nejdřív ověřit,
   čím binární RBXM číst (stdlib vs. existující nástroj), read-only na kopii s hash-kontrolou ·
   M2.2 identifikace 4 kol a středů **heuristikou z `docs/A-CHASSIS-AUDIT.md` (§Model:Wheels → díly
   FL/FR/RL/RR; kola tvar Ball; `wDia` se odvozuje ze `Size.x` největšího hnacího kola)** ·
   M2.3 identifikace náprav · M2.4 rozvor · M2.5 rozchody · M2.6 průměry pneu **s křížovou kontrolou
   proti `wDia`** · M2.7 inventář dílů/hmotností · M2.8 čtení Tune/Script/Structure parametrů ·
   M2.9 kalibrace `studs_per_meter` · M2.10 kontrola konzistence měřítka z více rozměrů.
   Nejednoznačné označení kola nebo chybějící `Model:Wheels` → `UNKNOWN` + `BLOCKED`, nikdy odhad.
9. **Unit testy:** determinismus (2× stejný RBXM = identický výstup); všechna 4 kola rozpoznána; nápravy určeny; rozvor/rozchod shodné s referencí.
10. **Integration testy:** report proti ručnímu měření ve Studiu; nekonzistentní měřítko → WARNING/BLOCKED; nejednoznačné označení kola → UNKNOWN.
11. **Akceptační kritéria:** M2-T01…M2-T08 (včetně **zápis do originálu RBXM se nesmí stát** — hash vstupu se po běhu nemění).
12. **Definition of Done:** modul změří model a určí měřítko, nebo prokazatelně oznámí, že to nelze.
13. **Omezení/rizika:** žádný RBXM parser v repu zatím neexistuje (největší riziko plánu); float/CFrame rozměry A-Chassis dosud neověřeny ve Studiu (otevřený bod ze STATUS).
14. **Stav:** NOT IMPLEMENTED.

## M3 – Geometry Engine · priorita P0 · stav: NOT IMPLEMENTED

1. **Cíl:** cílová geometrie Mustangu v studs + rozdílový report proti vstupnímu modelu. Bez zásahu do originálu.
2. **Odpovědnosti:** převod mm→studs; cílové rozvor/rozchody/průměry/pozice kol; symetrie a kolize; report.
3. **Vstupy:** profil M1 + inspekce a měřítko M2.
4. **Výstupy:** `geometry_target.json`, `geometry_diff.json` (rozdíl + posunutí L/R kol).
   Minimální tvar záznamu: `{param, source_value, source_unit, target_value, target_unit,
   delta, method: "measured"|"computed", status}`; `method: computed` jen z ověřených vstupů,
   jinak `BLOCKED` (propagace z M2, žádná čísla při nekonzistentním měřítku).
5. **Vztah:** `D = 19·25,4 + 2·W·A/100` → přední 686,6 mm / zadní 702,6 mm (nominální, nezatížené).
6. **Navržené soubory:** `src/autoengineer/geometry/{dimensions,wheel_geometry,axle_geometry,geometry_diff,geometry_validator}.py`.
7. **Závislosti:** M1 + M2 (BLOCKED při nekonzistentním měřítku).
8. **Úkoly:** M3.1 převod rozměrů na studs · M3.2–M3.4 cílové rozvor/rozchody · M3.5 průměry pneu · M3.6 pozice středů kol · M3.7 geometrický rozdíl vs. originál · M3.8 posunutí L/R kol · M3.9 symetrie a kolize · M3.10 report.
9. **Unit testy:** přepočty rozvor/rozchod = správné studs; průměry 686,6 / 702,6 mm; symetrie L/R; záměna P/Z nápravy → odmítnuto.
10. **Integration testy:** diff report proti M2 inspekci reálného RBXM; kolize kola s karoserií → WARNING/BLOCKED.
11. **Akceptační kritéria:** M3-T01…M3-T09; při BLOCKED měřítku žádný výstup s čísly.
12. **Definition of Done:** přesný geometrický rozdíl vstup → Mustang, bez automatického zásahu do originálu.
13. **Omezení/rizika:** závisí na M2 (bez parseru nelze); nominální průměry ≠ zatížené; strukturální posuny kol jsou `STRUCTURE_CONTROLLED` (viz M5).
14. **Stav:** NOT IMPLEMENTED.

## M4 – Physics Engine v2 · priorita P0 · stav: PARTIAL

1. **Cíl:** fyzikální cíle Mustangu z ověřených dat; matematika drží, neznámé se nevymýšlejí.
2. **Odpovědnosti:** jednotkový systém; modely hmotnosti, motoru (+oddělené Pmax/Mmax), křivky momentu s neúplnými daty, převodovky, stálého převodu, pneu, brzd, akcelerace, odporů; nejistota každého výsledku.
3. **Vstupy:** profil M1 (+ M2 hmotnosti, je-li k dispozici).
4. **Výstupy:** `physics_target.json` (každý cíl: hodnota + jednotka + zdroj + stav + nejistota).
5. **Vztahy:** `P = T·2π·RPM/60`; `a = (F_drive − F_resistance)/m`; `v = RPM/60·2πr/(i_g·i_f)`. Výkonová bilance, trakce/prokluz a brzdění = samostatné části (poučení: žádná nereálná bilance vydávaná za predikci).
6. **Navržené soubory:** `src/autoengineer/physics/{mass_model,engine_model,torque_curve,transmission_model,differential_model,tire_model,braking_model,suspension_model,steering_model,performance_model}.py` — ověřit proti existujícím `src/Physics/{engine,gearbox,tires,brakes,suspension,steering,mass,aero,diff,load_transfer}.py` a rozšířit je, ne duplikovat.
7. **Závislosti:** M1 + M2; částečně souběžně s M3.
8. **Úkoly:** M4.1 jednotkový systém · M4.2 hmotnost · M4.3 motor (Pmax/Mmax odděleně) · M4.4 křivka momentu s UNKNOWN body · M4.5 6st. převodovka · M4.6 stálý převod · M4.7 pneu/obvodové rychlosti · M4.8 referenční brzdný model · M4.9 akcelerace · M4.10 jízdní odpory · M4.11 nejistota a stav výsledků.
9. **Unit testy:** převody Nm/kW/PS; `P` z `T·RPM`; rychlost kola; přesně 6 stupňů; záporná hmotnost/převod → odmítnuto.
10. **Integration testy:** Python výpočet vs. archivovaná Studio telemetrie (F6/F7 data) — shoda v toleranci, jinak FAIL; simulace se nikdy neprohlašuje za runtime důkaz.
11. **Akceptační kritéria:** M4-T01…M4-T10 (neznámá křivka = žádné vymyšlené body; monotónnost brzdné dráhy; energetická kontrola bilance).
12. **Definition of Done:** výpočty matematicky ověřené, s limity; neznámé explicitní.
13. **Omezení/rizika:** 6 známých omezení přenesených z RobloxSimulatoru (`KNOWLEDGE-TRANSFER.md`); sim-to-real gap řeší povinný `mode` flag (ARCHITECTURE §8).
14. **Stav:** PARTIAL — `src/Physics/*` + selftesty existují, chybí torque_curve s UNKNOWN podporou, differential/performance jako cíle Mustangu, nejistoty.

## M5 – A-Chassis Mapping v2 · priorita P0 · stav: PARTIAL

1. **Cíl:** převod geometrických a fyzikálních cílů na konkrétní podporované A-Chassis parametry s důvodem.
2. **Odpovědnosti:** katalog parametrů; vazba cíl → Tune klíč; rozsahy jen z ověřených pravidel; validace závislostí a konfliktů; pořadí změn; odmítnutí nejednoznačného mapování.
3. **Vstupy:** cíle M3/M4 + `src/Chassis/catalog/parameters.json` (138 záznamů).
4. **Výstupy:** `achassis_changes.json` — každá změna `{target, target_value, unit, mapping_type, status PENDING, reason, old_value}`.
5. **Vztahy:** `achassis_changes.json` je lidsky čitelný rozpad; závazným artefaktem je
   `change_plan.json` dle `contracts/change_plan.schema.json` (`plan_` ID, kroky `area/action/from/to`,
   `chassis_decision: keep|adapt|replace`). Chování enginu (`src/Chassis/mapping_engine.py`):
   `verification_status != verified` → mapuje se **s varováním**, status změny proto zůstává `PENDING`;
   `VERIFIED` až po Studio testu (brána G-06). Kategorie (neměnit):
   `MUTABLE_TUNE | SCRIPT_CONTROLLED | STRUCTURE_CONTROLLED | READ_ONLY | UNKNOWN`
   (aktuálně 82/14/2/3/37); strukturální změna vždy samostatně označena.
6. **Navržené soubory:** `src/autoengineer/achassis/{parameter_registry,mapping_rules,dependency_validator,conflict_validator,change_planner}.py` — ověřit proti `src/Chassis/{registry,mapping_engine,mapping/dependencies}.py` a rozšířit.
7. **Závislosti:** geometrické + fyzikální cíle (M3/M4) a existující katalog.
8. **Úkoly:** M5.1 zachovat katalog · M5.2 zachovat kategorie · M5.3 vazba cíl → Tune klíč · M5.4 rozsahy jen z ověřených pravidel · M5.5 validace závislostí · M5.6 validace konfliktů · M5.7 zdůvodnění změny · M5.8 pořadí změn · M5.9 odmítnutí nejednoznačného mapování.
9. **Unit testy:** neznámý parametr → odmítnuto; READ_ONLY → odmítnuto; mimo rozsah → odmítnuto; konfliktní změna → odmítnuto.
10. **Integration testy:** change set proti katalogu 138 parametrů; každá změna má důvod + původní hodnotu; neověřená změna nikdy nedostane VERIFIED.
11. **Akceptační kritéria:** 7 pravidel ze zadání (vše PASS); strukturální změny oddělené.
12. **Definition of Done:** engine navrhuje jen změny, které umí bezpečně a jednoznačně vysvětlit.
13. **Omezení/rizika:** 37 UNKNOWN parametrů se nesmí automaticky měnit; neověřené Tune rozsahy se nesmí vymýšlet.
14. **Stav:** PARTIAL — katalog 138 + `mapping_engine.py` + `dependencies.py` existují; chybí vazba fyzikální cíl → Tune klíč a change planner s pořadím.

## M6 – Configuration Generator & Rollback · priorita P1 · stav: PARTIAL

1. **Cíl:** bezpečné pracovní konfigurace pro iterace + návrat.
2. **Odpovědnosti:** `VehicleConfiguration`; generátor balíčků; verzování iterací; diff; rollback; kontrola integrity vstupu; manifest; ochrana originálu; oddělení návrhu od aplikace.
3. **Vstupy:** change set M5 + profil M1.
4. **Výstupy:** `output/<vehicle_id>/iteration_NNN/` (9 souborů vč. `rollback.json`, `manifest.json`).
5. **Datové struktury:** `contracts/{vehicle_config,change_plan,manifest}.schema.json` (existují); každá iterace unikátní ID (`cfg_` prefix, `src/common/ids.py`).
6. **Navržené soubory:** `src/autoengineer/config/{generator,manifest,change_set,rollback,diff_report,config_validator}.py` — ověřit proti `src/Optimizer/{change_plan,store}.py` + `src/Sim/config.py`.
7. **Závislosti:** M5.
8. **Úkoly + částečné selhání:** M6.1 `VehicleConfiguration` · M6.2 generátor · M6.3 verzování ·
   M6.4 diff · M6.5 rollback · M6.6 integrita vstupu (hash) · M6.7 manifest (zdroje+výpočty;
   povinná pole dle `contracts/manifest.schema.json`: `run_id, code_version, seed,
   scenario_versions, artifacts`) · M6.8 originál beze změny · M6.9 oddělení návrhu od aplikace ·
   **M6.10 atomicita: zápis probíhá do nové kopie + atomický swap, nikdy in-place do aktivní
   konfigurace; pád uprostřed aplikace (kill-test) musí nechat předchozí iteraci funkční a
   `rollback.json` musí obnovit last-known-good s nulovým diffem**.
9. **Unit testy:** stejné vstupy = stejný výstup (determinismus); nevalidní konfigurace → odmítnuto; rollback obnoví původní.
10. **Integration testy:** hash originálního RBXM se po generování nemění; každá iterace unikátní ID; změny dohledatelné v historii.
11. **Akceptační kritéria:** 7 pravidel ze zadání + atomicita M6.10 (vše PASS); žádná změna se neaplikuje automaticky na originál.
12. **Definition of Done:** konfiguraci lze vytvořit, porovnat a vrátit bez rizika ztráty auta.
13. **Omezení/rizika:** binární artefakty v gitu (zvážit LFS — otevřený bod ARCHITECTURE §11).
14. **Stav:** PARTIAL — `Optimizer/store.py` + `change_plan.py` + manifest kontrakt existují; chybí generátor balíčků, diff report, rollback s nulovým diffem.

## M7 – Human Test Protocol Generator · priorita P1 · stav: PARTIAL

1. **Cíl:** přesné pokyny, podle kterých člověk testuje ve Studiu.
2. **Odpovědnosti:** katalog testů; protokoly geometrie/akcelerace/brzdění/zatáčení/stability; podmínky; opakování; tolerance; formulář/JSON pro výsledky.
3. **Vstupy:** konfigurační balíček M6.
4. **Výstupy:** `test_protocol.md` + `expected_results.json` + `result_schema` formulář.
5. **Testy Mustangu:** T-GEO-01/02 (1×), T-ACC-01 (5×), T-BRK-01 (5×), T-STEER-01/02 (3+3×), T-REL-01 (3×), T-STAB-01 (3×) — viz `HYBRID_WORKFLOW.md` §3.
6. **Navržené soubory:** `src/autoengineer/testing/{test_definitions,protocol_generator,expected_results,result_schema,test_conditions}.py` — ověřit proti `src/Sim/scenarios.py`, `testgame/src/.../ScenarioDefinitions.lua`, `docs/TESTING-OPTIMIZATION.md` (11 scénářů), `contracts/scenario.schema.json`.
7. **Závislosti:** M6.
8. **Úkoly:** M7.1 katalog testů · M7.2–M7.6 protokoly (geo/accel/brake/steer/stabilita) ·
   M7.7 podmínky (trať, povrch, seed, počáteční stav — viz `testgame/.../ScenarioDefinitions.lua`) ·
   M7.8 opakování · M7.9 tolerance · M7.10 formulář/JSON ·
   **M7.11 `expected_results.json` musí ke každému testu obsahovat
   `{target, unit, tolerance, min_repetitions, verdict_rule}`; verdict_rule je explicitní nerovnost
   (např. `|Error_%| ≤ tolerance → PASS`), protokol bez čísel se zamítá.
   Trasabilita na existující scénáře: T-ACC-01 → S1 (akcelerace), T-BRK-01 → S3 (brzdy 100→0).
9. **Unit testy:** každý test má postup + jednotky + toleranci; schéma výsledku validuje prázdný i plný formulář.
10. **Integration testy:** protokol pro iteration_NNN proti `expected_results.json`; podmínky odpovídají prostředí Studia (`ROBLOX-RUNTIME.md`).
11. **Akceptační kritéria:** každý test má jednoznačný postup, očekávané hodnoty **s číselnou
    tolerancí a verdict_rule**, jednotky, vyhodnocení; počty opakování = minimum výše;
    `environment.mode` výsledku musí být `roblox-runtime` (dle `contracts/test_result.schema.json`),
    jinak výsledek není runtime důkaz.
12. **Definition of Done:** člověk bez expertních znalostí provede test a odevzdá validní měření.
13. **Omezení/rizika:** lidský faktor (opakovatelnost); F7.2 AC1–AC7 ukazují, jak přísné musí být prahy a symetrie.
14. **Stav:** PARTIAL — scénáře a telemetrická schémata existují (Sim + testgame + Lua), chybí generátor lidsky čitelných protokolů a formulář.

## M8 – Measurement Evaluator & Iteration Advisor · priorita P1 · stav: PARTIAL

1. **Cíl:** z měření technické rozhodnutí (pomohlo / ne / rollback).
2. **Odpovědnosti:** načítání měření; validace jednotek/podmínek; průměr/medián/směrodatná odchylka/rozsah; % odchylka; opakovatelnost vs. přesnost; outliery s evidencí; návrh další změny; historie + rollback doporučení.
3. **Vstupy:** vyplněný formulář M7 + telemetrie ze Studia.
4. **Výstupy:** `evaluation.json` + doporučení (`NEXT-ITERATION | ACCEPTED | ROLLED-BACK` s důvodem).
5. **Vztahy:** `x̄ = Σx/n`; `s = √(Σ(x−x̄)²/(n−1))`; `Error_% = (measured − target)/target·100`;
   medián = prostřední hodnota seřazeného vzorku; rozsah = max−min.
   **Opakovatelnost** `R = (max−min)/|x̄|·100 %` (precedent F7.2 AC3: R ≤ 10 %, jen je-li |x̄| bezpečně
   od nuly); **přesnost** `|x̄ − target|/|target|·100 %`. Pravidla: `n < 3` → `INSUFFICIENT`,
   nikdy PASS; outlier se flaguje (|odchylka| > 3s nebo Grubbs) a **nikdy tiše nemazává** —
   vyřazení jen se záznamem důvodu v `evaluation.json`.
6. **Navržené soubory:** `src/autoengineer/evaluation/{measurement_loader,statistics,deviation,repeatability,evaluator,iteration_advisor}.py` — ověřit proti `src/Telemetry/{evaluate,metrics}.py` + `src/Optimizer/{statistics,acceptance}.py` (duplicitě se vyhnout).
7. **Závislosti:** M7.
8. **Úkoly:** M8.1 načítání měření · M8.2 validace jednotek/podmínek · M8.3 statistiky · M8.4 % odchylka · M8.5 opakovatelnost vs. přesnost · M8.6 nevalidní/chybějící měření · M8.7 návrh další změny · M8.8 historie · M8.9 rollback.
9. **Unit testy:** správný průměr/odchylka/% odchylka (ručně spočtené fixture).
10. **Integration testy:** nekompletní sada nikdy nedostane PASS; outlier se nezkracuje bez evidence; doporučení vždy uvádí důvod; neúspěšná iterace umí vyvolat rollback.
11. **Akceptační kritéria:** 8 pravidel ze zadání (vše PASS).
12. **Definition of Done:** systém z výsledků Studia určí, zda změna pomohla, a vysvětlí proč.
13. **Omezení/rizika:** malá n (3–5 opakování) → široké intervaly; lidská variabilita se nesmí plést s efektem změny (opakovatelnost ≠ přesnost).
14. **Stav:** PARTIAL — statistika a evaluace existují (`Telemetry/`, `Optimizer/`), chybí loader ručních měření, opakovatelnost a iteration advisor.

## M9 – End-to-End Hybrid Workflow · priorita P1 · stav: PARTIAL

1. **Cíl:** jeden použitelný proces od RBXM po vyhodnocenou iteraci bez ručních zásahů do výpočtů.
2. **Odpovědnosti:** `BuildVehicle` orchestrace; stav; historie iterací; finální report.
3. **Vstupy:** RBXM + `vehicle_id` (Mustang).
4. **Výstupy:** iterace + `manifest.json` + finální report (musí projít bez ručního zásahu do internals).
5. **Kroky:** M9.1 `BuildVehicle` · M9.2 profil · M9.3 RBXM analýza · M9.4 geometrické rozdíly · M9.5 fyzikální cíle · M9.6 change set · M9.7 balíček · M9.8 protokol · M9.9 import výsledků · M9.10 vyhodnocení · M9.11 návrh změn · M9.12 historie.
6. **Navržené soubory:** `src/autoengineer/workflow/{vehicle_build,iteration_manager,workflow_state,report_generator}.py` — ověřit proti `autoengineer.py` + `src/Optimizer/optimizer.py` + `src/Sim/run.py`.
7. **Závislosti:** M1–M8 (M9 je propojuje, neobchází).
8. **Úkoly:** viz kroky M9.1–M9.12 výše.
9. **Unit testy:** stavový stroj `PLANNED → … → (ACCEPTED|ROLLED-BACK|NEXT-ITERATION)`; rollback na libovolnou iteraci.
10. **Integration testy:** kompletní workflow s testovacím RBXM i Mustang profilem; dvě po sobě jdoucí iterace; zachování originálu (hash); žádné runtime PASS bez Studio testu.
11. **Akceptační kritéria:** 9 pravidel ze zadání (vše PASS).
12. **Definition of Done + dokončovací brána M9:** od vstupního RBXM po vyhodnocený ruční test
    bez ručního zásahu do výpočtů **a** současně: všechny brány G-01–G-10 PASS, každá iterace má
    archivovaný protokol + telemetrii + `manifest.json` (pole dle `contracts/manifest.schema.json`),
    žádný výsledek s `environment.mode: local-sim` se nevydává za runtime důkaz.
13. **Omezení/rizika:** stojí a padá s M2 (RBXM parser); do M2 BLOCKED je M9 jen kostra nad simulovanými daty s `mode` flagem.
14. **Stav:** PARTIAL — `autoengineer.py` CLI + optimizer cyklus existují; chybí orchestrace M1→M8, stav iterací, report generátor.
