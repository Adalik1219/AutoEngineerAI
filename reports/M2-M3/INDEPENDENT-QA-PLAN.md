# Nezávislý QA plán vlny 2 — M2/M3 geometrie (Agent F)

**Vlastněný soubor:** `reports/M2-M3/INDEPENDENT-QA-PLAN.md` · **Datum:** 2026-11-19 · **Jazyk:** česky
**Rozsah:** pouze plán, READ-ONLY vše kromě tohoto souboru (žádné změny kódu ani testů, žádné git operace).
**Větev:** `feat/m2-m3-geometry` (HEAD `ab840a9`, PR #2 nemergován).
**Zdroje (čteno):** `reports/M2-M3-CONTRACTS-FREEZE-v1.md`, `qa/qa-contracts-data.md`,
`reports/STUDIO_GROUND_TRUTH.md`, `reports/F4-3-CALIBRATION-BACKLOG.md`,
`reports/MUSTANG-SOURCE-CHECK.md`, `tests/test_m2_rbxm_parser.py`, `tests/test_m2_wheel_detect.py`.
**Cíl dat:** EUROPEAN FACTORY STANDARD SPECIFICATION (Mustang GT 2024 EU; hlavička „bez Performance Packu" je zastaralá US logika).

## Gate vlny 2 (brána M2→M3)

M3 (`geometry_target.json`, `geometry_diff.json`, producent Agent E) se **nesmí** začít plnit, dokud:
1. `inspection_report.json` má `overall_status: GEOMETRY_OK` (ne UNKNOWN/BLOCKED),
2. `scale_calibration.json` má `overall_status: VERIFIED` nebo `ESTIMATED` (ne UNKNOWN/BLOCKED),
3. `coordinate_frame.verified_in_studio = true`.
Při BLOCKED vstupu M2 → celý M3 report BLOCKED (freeze § geometry_diff).

## Blok 1 — Parser a hierarchie (M2, Agent B)

| # | Kontrola | Metoda | PASS kritérium |
|---|---|---|---|
| P1 | Hierarchie úplná | Integrace na verzované fixture `JeepTemplate.rbxm` (815 instancí, 37 typů, kořen) | Žádná ztracená instance, `Model:Wheels` + FL/FR/RL/RR přítomny |
| P2 | Tvary/size/CFrame | Ball/Block/Cylinder z parseru vs Studio ground truth (Ball 2.7³, float32 `2.700000047683716`) | Shoda tvaru + size ±float32 tolerance; **žádná geometrie odvozená z názvu** |
| P3 | Chybové kontrakty | Syntetické poškozené varianty v paměti (header, chunky, LZ4, INST, PRNT) | `RbxmCorruptError` / `RbxmHierarchyError` / `RbxmUnsupportedError` dle typu vady; nikdy tichý PASS |
| P4 | Hash-před-po | SHA-256 fixture před/po (`dc8747e0…`, 230421 B) | Hash identický — testy jen čtou |
| P5 | Chybějící fixture | Oba soubory chybí | SKIP (PENDING), nikdy ERROR |
| P6 | LIMIT-výhrada | Oba soubory mají stejný hash → jediný distinctní model | Zaznamenáno jako LIMIT, druhý soubor testován zvlášť |

## Blok 2 — Kola: strany, nápravy, falešní kandidáti (M2.2, wheel_detect)

Pravidlo: kolo = (a) v `Model:Wheels` + (b) jméno FL/FR/RL/RR + (c) tvar Ball; jinak UNKNOWN se záznamem.

| # | Kontrola | Metoda | PASS kritérium |
|---|---|---|---|
| W1 | 4× WHEEL na zdravé hierarchii | Syntetická fixture (kořen 0 ← Wheels 2 ← 4 kola) | `status OK`, `failed_checks == []`, determinismus (2× stejný výsledek) |
| W2 | Ball mimo Wheels | Duplicita FR s `parent_id` mimo Wheels | `UNKNOWN` + `not_in_wheels`; výsledek neotráví (FR = id 52) |
| W3 | Špatné jméno (`FrontLeft`) | Porušení podmínky (b) | Daná pozice `UNKNOWN`, celek BLOCKED, záznam v `unidentified` |
| W4 | Příslušenství ve Wheels | `SpringConstraint` / `SuspensionGeometry`-Model uvnitř Wheels | Není kolo ani UNKNOWN, neblokuje |
| W5 | Strany/nápravy | `axles.front = {FL,FR}`, `rear = {RL,RR}`; track = \|L.x−R.x\|, wheelbase = \|F.z−R.z\| | Track ≈ 5.99, wheelbase ≈ 10.52 (Studio: 5.99066 / 10.52280) |
| W6 | Známý BLOCKED-stav | Reálný strom: 44 dílů podvozku ve stromu Wheels | `wheel_detect` hlásí 4× WHEEL, ale BLOCKED — ověřit, že brána M3 zůstává zavřená |

## Blok 3 — Kalibrace: nezávislý přepočet, nejistoty, BLOCKED (M2, Agent C)

| # | Kontrola | Metoda | PASS kritérium |
|---|---|---|---|
| K1 | Nezávislý přepočet | Vlastní skript (stdlib): `studs_per_meter` z každého páru (reference_SI ↔ měření_studs) pro wheelbase / track_f / track_r / tire_d | Shoda s `estimates[]` producenta na všech 5 mírách |
| K2 | Nejistota | `uncertainty` + `deviations_pct` z rozptylu odhadů; Y-identické (23.622142791748047) nesmí skrýt rozptyl X/Z | Nejistota uvedena, metoda popsána; podezřele nulová → FAIL |
| K3 | Pravidlo 2 referencí | < 2 nezávislé reference → BLOCKED + `blocked_reason` | Vynuceno strojně, ne jen dokumentačně |
| K4 | Jednotky | Každá reference `value_si + unit`; SI i studs vedle sebe | Žádné bezjednotkové číslo v kalibračním vstupu/výstupu |
| K5 | Mustang-rozpory jako reference | Převody 1–6 POTVRZENY, ale **stálý převod 3.15 vs 3.55 nejasný**; bias brzd NENALEZEN; křivka momentu NENALEZENA | Nejasné hodnoty nesmí být `VERIFIED` referencí; bias/křivka → BLOCKED nebo `ESTIMATED` s nízkou confidence, nikdy tichý default |
| K6 | Nález H (přenesený) | `value:null` smí mít jen `confidence: 0` (ARCH §3.2; qa-contracts-data nález H: 4×/10×/9× `0.2`) | Kalibrační reference s `null` + nenulovou confidencí → FAIL |

## Blok 4 — Studio: zdroj pravdy, jednotky, PENDING≠PASS

Ground truth (`STUDIO_GROUND_TRUTH.md`, 2026-11-19, Edit mode, read-only): kola Ball 2.7³, track ≈ 5.99, wheelbase ≈ 10.52.

| # | Kontrola | Metoda | PASS kritérium |
|---|---|---|---|
| S1 | Zdroj vs parser | Porovnat Size/CFrame/Shape ze `inspect_instance` s parserem | Shoda (float32 tolerance); verdikt „POTVRZENO s přesnými čísly, žádný PENDING zbytek" |
| S2 | Jednotky | `METERS_PER_STUD = 0.28`, `KG_PER_RMU = 21.952`, `g = 9.81`, `dt = 1/240` vs `UnitMap.luau` / `SIContract` / `EnvironmentSI` (qa-contracts-data §2: 4/4 POTVRZENO) | Jakákoli odchylka konstanty → STOP celé vlně |
| S3 | PENDING≠PASS | Chybějící fixture → SKIP; `damper`/`spring_stiffness` PENDING (confidence 0.4, float-lane kandidát) | SKIP/PENDING se nesmí započítat do PASS počtů ani otevřít bránu M3 |
| S4 | Read-only session | SHA-256 work-copy před/po identický; jen `search_game_tree` / `inspect_instance` / `script_read` / `version()` | Hash shodný; žádný apply/play |

## Blok 5 — M3: převody, cíle, BLOCKED propagace (Agent E, až po bráně)

| # | Kontrola | Metoda | PASS kritérium |
|---|---|---|---|
| M1 | Brána | `geometry_target.json` existuje jen při GEOMETRY_OK + VERIFIED/ESTIMATED + `verified_in_studio=true` | Jinak M3 BLOCKED, žádné cíle |
| M2 | Převody | `tire_d_f/r_studs` z designací `25.4·rim+2·w·a/100` (kontrola: 616/655/629); převodové poměry EU 6MT 3.237/2.104/1.422/1.000/0.814/0.622 | Přepočet ±0.3 mm; stálý převod jen s uvedením která varianta (3.15 vs 3.55) |
| M3 | Cíle | `wheelbase/track_f/track_r/tire_d` + `wheel_centers {FL,FR,RL,RR}`, `units: "studs"`, `sources[]`, `status_per_value` | Každá hodnota má status; vše studs |
| M4 | Diff | `geometry_diff.json`: `{param, source_value+unit, target_value+unit, delta, method, status, source_ref}` | Při BLOCKED vstupu M2 → celý report BLOCKED (propagace ověřena testem) |
| M5 | P=M·n konzistence | `P = M·n/9549` na referencích (MX-5/Civic/GR86 ✓ vzor; Mustang 540 Nm@5100 → 288 kW < 328 ✓) | Nesoulad → FAIL cíle |

## Blok 6 — Adversarial sada (minimálně 8 případů)

| # | Případ | Očekáváno |
|---|---|---|
| A1 | Prohozené strany (FL↔FR instance) | UNKNOWN nebo špatná strana detekována; track se nesmí „vyjít náhodou" |
| A2 | Kolo tvaru Block/Cylinder ve Wheels se jménem FL | UNKNOWN (porušena podmínka c) |
| A3 | Duplicitní jméno FL (2× ve Wheels) | BLOCKED, obě zaznamenána |
| A4 | Chybějící kolo (jen 3 ve Wheels) | BLOCKED |
| A5 | Wheels model chybí / přejmenován | `RbxmHierarchyError` nebo BLOCKED, nikdy 4× WHEEL |
| A6 | CFrame s NaN/inf | Corrupt/UNKNOWN, nikdy číslo v reportu |
| A7 | Kalibrace s 1 referencí | BLOCKED + `blocked_reason` |
| A8 | Kalibrace s rozpornými referencemi (3.15 vs 3.55 jako „obě VERIFIED") | ESTIMATED/BLOCKED s vysokou nejistotou, nikdy tichý výběr jedné |

## Verdikty a reportování

- Každý blok: **PASS / PASS s výhradou / FAIL / BLOCKED** + důkaz (soubor:řádka, hash, přesné číslo).
- Do PASS počtů se nesmí započítat SKIP/PENDING.
- Výstup vlny: tento plán + `INDEPENDENT-QA-VERDICT.md` (verdikty po blocích) + seznam oprav s držitelem souboru (QA neopravuje cizí soubory).
