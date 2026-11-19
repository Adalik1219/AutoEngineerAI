# M2 STUDIO GROUND-TRUTH — geometrie kol (Wheels)

> Role Agent D. Nezávislé měření ve Studiu + porovnání s parserem.
> Navazuje na `reports/STUDIO_GROUND_TRUTH.md` (kola Ball 2.7³, 5.9907/10.5228 POTVRZENO) — neopakuje ho, přidává tabulku Studio|Parser|Rozdíl|Stav a PENDING položky.

| Meta | Hodnota |
|---|---|
| Větev / HEAD | `feat/m2-m3-geometry` / `ab840a9` (PR #2 NEMERGOVAT, žádné git operace) |
| Studio instance | `ae_test.rbxlx`, mode **Edit** (`8bc1ee5c-…`, druhá instance `Unavailable`) |
| Cesta ve Studiu | `ServerStorage.VehicleTemplates.JeepTemplate.Wheels` (Model) |
| Pracovní kopie | `assets/chassis-original/chasis-work-copy.rbxm` — **pouze čtena** |
| SHA-256 před | `dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf` |
| SHA-256 po | `dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf` (shodný — read-only) |
| Parser reference | `src/Inspection/rbxm_parser.py` `parse_rbxm()` nad pracovní kopií, kola id 3/52/101/150 |
| Datum / měřil | 2026-11-19 / Agent D (MCP read-only: list/get_state/search/inspect, **bez Play**) |

## Metoda (nezávislá na parseru)

1. `list_roblox_studios` → instance `ae_test.rbxlx` / Edit; `get_studio_state` → Edit k dispozici.
2. `search_game_tree(path=ServerStorage, max_depth=6)` → hierarchie potvrzena ze živého stromu (keyword `Wheels` s defaultní hloubkou 3 nic nenašel — Wheels je v hloubce 4; poučení pro příště: hledat s `max_depth ≥ 6` nebo přes `ServerStorage`).
3. `inspect_instance` modelu `…JeepTemplate.Wheels` a každého kola FL/FR/RL/RR → `Size`, `CFrame.Position`, `Shape` čteny přímo z vlastností instancí.
4. Parser spuštěn zvlášť nad pracovní kopií (`parse_rbxm`) — porovnání až po měření, ne během něj.

## Jednotky

Vše ve **studech** (nativní jednotka Studia / `Size` a `CFrame.Position`). Kalibrace `studs_per_meter` je záměrně NOT_IMPLEMENTED (viz AUDIT2-geometry) — převod na metry proto **není součástí** této ground-truth; jakýkoli přepočet na metry je PENDING (níže).

## Hierarchie Wheels (potvrzeno ze živého stromu)

- `JeepTemplate` (Model) → `Wheels` (Model, 4 children, 196 descendants) → `FL`, `FR`, `RL`, `RR` (vše ClassName **Part**).
- Každé kolo: 6 children (`WheelFixed`, `SuspensionFixed`, `Mesh`[CylinderMesh], `Parts`, `SuspensionGeometry`, `OriginalSize`[Vector3Value]) + 48 descendants — všechna 4 identická struktura.
- Kola: `Anchored=true`, `CanCollide=true`, `Material=Rubber`, `BrickColor=Black`, `Transparency=0`; rotace FL/RL `90, 0, -90`, FR/RR `90, 0, 90`.

## Středy kol (Studio, `CFrame.Position`)

| Kolo | X | Y | Z |
|---|---|---|---|
| FL | -45.187889099121094 | 23.622142791748047 | -203.2503662109375 |
| FR | -51.178550720214844 | 23.622142791748047 | -203.25039672851562 |
| RL | -45.18785858154297 | 23.622142791748047 | -213.77316284179688 |
| RR | -51.17858123779297 | 23.622142791748047 | -213.77316284179688 |

Y identické na všech 4 (spread 0.0). Tvoří 2×2 obdélník symetrický kolem středu `(-48.18, ·, -208.61)` (= WorldPivot modelu).

## Porovnání Studio | Parser (vše ve studech)

| Veličina | Studio | Parser (id 3/52/101/150) | Rozdíl | Stav |
|---|---|---|---|---|
| Průměr FL (Size) | 2.700000047683716³ | (2.700000047683716)³ | 0.0 | ✅ POTVRZENO |
| Průměr FR (Size) | 2.700000047683716³ | (2.700000047683716)³ | 0.0 | ✅ POTVRZENO |
| Průměr RL (Size) | 2.700000047683716³ | (2.700000047683716)³ | 0.0 | ✅ POTVRZENO |
| Průměr RR (Size) | 2.700000047683716³ | (2.700000047683716)³ | 0.0 | ✅ POTVRZENO |
| Tvar všech 4 | `Enum.PartType.Ball` | `Ball` | — (mapování názvu) | ✅ POTVRZENO |
| Střed FL | (−45.187889099121094, 23.622142791748047, −203.2503662109375) | shodný bit-přesně | 0.0 | ✅ POTVRZENO |
| Střed FR | (−51.178550720214844, 23.622142791748047, −203.25039672851562) | shodný bit-přesně | 0.0 | ✅ POTVRZENO |
| Střed RL | (−45.18785858154297, 23.622142791748047, −213.77316284179688) | shodný bit-přesně | 0.0 | ✅ POTVRZENO |
| Střed RR | (−51.17858123779297, 23.622142791748047, −213.77316284179688) | shodný bit-přesně | 0.0 | ✅ POTVRZENO |
| Rozchod přední \|FL.x−FR.x\| | 5.99066162109375 | 5.99066162109375 | 0.0 | ✅ POTVRZENO |
| Rozchod zadní \|RL.x−RR.x\| | 5.99072265625 | 5.99072265625 | 0.0 | ✅ POTVRZENO |
| Rozvor levý \|FL.z−RL.z\| | 10.522796630859375 | 10.522796630859375 | 0.0 | ✅ POTVRZENO |
| Rozvor pravý \|FR.z−RR.z\| | 10.52276611328125 | 10.52276611328125 | 0.0 | ✅ POTVRZENO |

Pozn.: přední/zadní rozchod se liší o ~6.1e-5 stu, levý/pravý rozvor o ~3.0e-5 stu — pod rozlišením float32 šumu, oba páry konzistentní s `≈5.99` / `≈10.52` z předchozího kola.

## PENDING (nelze bez Play — s postupem)

| # | Položka | Proč PENDING | Postup (až pokyn koordinátora k Play) |
|---|---|---|---|
| P1 | Dynamická CFrame kol za jízdy (odpružení, travel) | Edit-mode `CFrame` je statický; `SpringConstraint`/pružení se projeví až v simulaci | Koordinátor povolí Play → `start_stop_play`, za jízdy číst `CFrame.Position` kol v `Server` datamodelu ve vzorcích, pak `stop`; zapsat min/max travel |
| P2 | Valivý poloměr / kontakt s vozovkou | Kontakt kola se zemí je výsledek fyziky, ne vlastnost Partu | Play-test na rovince: telemetrie Y-středu vs. poloměr 1.35 stu; ověřit, zda vizuální mesh (CylinderMesh) odpovídá koliznímu Ball tvaru |
| P3 | Převod studs→metry (`studs_per_meter`) | Vyžaduje referenci se známým reálným rozměrem, kterou nemáme | Dodat referenční míru (skutečný vůz) → `calibrate_studs_per_meter` až pak; do té doby všechny míry jen ve studech |

## Verdikt

Statická geometrie kol je **bit-přesně shodná** mezi Studiem a parserem (rozdíl 0.0 ve všech 13 řádcích). Parserová tvrzení Ball 2.7³ / rozchod ≈5.99 / rozvor ≈10.52 jsou **POTVRZENA přesnými čísly výše**. Zbývá pouze P1–P3, vše vázané na Play, nic neblokuje M2.
