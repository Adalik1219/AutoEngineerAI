# M2.1 — technický spike formátu RBXM: rozhodnutí o strategii parseru

**Datum:** 2026-11-19 · **Větev:** M2 spike (read-only, bez zápisu do RBXM)
**Vstup (pouze čtení):** `C:/.DATA/AutoEngineerAI/assets/chassis-original/chasis-work-copy.rbxm`
**Originál (nedotčen):** `C:/Users/adamr/Downloads/chasis.rbxm`
**Pravidla:** Python 3 stdlib only · česky · identifikátory anglicky · žádný zápis do RBXM.

## 1. Rozhodnutí (TL;DR)

**Strategie: čistě-stdlib pure-Python parser psaný na míru (žádná externí závislost).**
Důkaz proveditelnosti je v §3–§5 níže: hlavička, census chunků a LZ4-dekomprese
prvního chunku byly provedeny **pouze stdlib kódem napsaným v rámci tohoto spike**
a výsledky souhlasí s nezávislým auditem (`docs/A-CHASSIS-AUDIT.md`).

**Co spike NEtvrdí (ne předstíraná podpora):**
`PROP` hodnoty, `PRNT` vazby a float/CFrame/Vector3 lane se v tomto spike
**nedekódují** — produkční parser (C05/C06) vzniká až po tomto rozhodnutí a
přebírá rozhodovací pravidlo kol doslovně. Float-přesnost vyžaduje ground-truth
ze Studia (otevřený bod auditu, kap. 1/19) — do té doby M2.4–M2.6 = UNKNOWN/BLOCKED.

## 2. Metoda a integrita vstupu (ověřená fakta)

- SHA-256 před prací (pracovní kopie i originál):
  `dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf`
  (230 421 B) — shodné, viz audit §1.
- Po práci hash znovu ověřen (§6); čtení proběhlo `open(rb).read()` — soubor
  nebyl nikdy otevřen k zápisu.
- V repu **žádná RBXM čtečka neexistuje** (grep `lz4|rbxm|SSTR|INST` v `*.py`
  nachází jen zmínky v dokumentech/testech, žádný dekodér) — potvrzen předpoklad ROADMAP M2.1.
- Prostředí: CPython 3.14, `import lz4` **není dostupný** (ModuleNotFoundError) —
  externí cesta (pip `lz4`) by porušila stdlib-only pravidlo, proto se nevolí.

## 3. Hlavička souboru (vlastní sonda, stdlib `struct`)

| Pole | Offset | Hodnota |
|---|---|---|
| magic | 0–7 | `<roblox!` |
| signatura | 8–13 | `89 FF 0D 0A 1A 0A` |
| verze | 14–15 | `0` (u16 LE) |
| numTypes | 16–19 | `37` (u32 LE) |
| numInstances | 20–23 | `815` (u32 LE) |
| reserved | 24–31 | 8× `00` |
| první chunk | 32 | `META` |

Poznámka: bez 8B `reserved` vycházejí nesmyslné délky chunků (ověřeno pokusem —
slepá cesta zdokumentována, aby ji produkce neopakovala).

## 4. Census chunků (vlastní walk, shoda s auditem)

`META: 1 · SSTR: 1 · INST: 37 · PROP: 928 · PRNT: 1 · END: 1`, konec na
bajtů přesně (`END\0`, `complen=0`, tělo `</roblox>`, 9 B).

- `INST: 37` = `numTypes` ✓; `PRNT` 1 s 815 vazbami dle auditu (vazby samotné
  se v tomto spike nedekódují — viz §1).
- `PROP: 928` vs. audit §1 „927× PROP": rozdíl 1 (audit nepočítá nejspíš
  prázdný/typový chunk); pro spike nepodstatné, produkce přepočítá.
- Komprese: typicky `complen < uncomplen` (LZ4 bloky); `complen=0` = raw
  (jen `END`).

## 5. Důkaz stdlib-cesty: LZ4 dekomprese pure-Python (~30 řádků, bez závislostí)

V rámci spike napsán minimální LZ4-block dekompresor (token/nibbles,
literály, offset u16 LE, překrývající se match-copy). Ověřeno na datech kopie:

- `META` (`complen=36 → uncomplen=34`): dekódováno přesně na 34 B:
  `01 00 00 00 | 12 00 00 00 "ExplicitAutoJoints" | 04 00 00 00 "true"`
  → **1 položka `ExplicitAutoJoints=true`** ✓ (shoda s auditem §1).
- `SSTR` (`complen=112548 → uncomplen=113064`): dekódováno, `nshared = 0`
  (prázdná tabulka sdílených řetězců) ✓ (shoda s auditem).
- `INST` (37×): všechny dekódovány; `typeID u32 + className` dává třídy
  `0 Attachment, 1 BillboardGui, 2 BlockMesh, 3 BodyThrust, 4 BoolValue,
  5 CylinderMesh, 6 Decal, 7 EqualizerSoundEffect, 8 Folder, 9 Frame,
  10 HingeConstraint, 11 ImageLabel, 12 LocalScript, 13 Model,
  14 ModuleScript, 15 NumberValue, 16 ObjectValue, 17 Part, 18 PointLight,
  19 RemoteEvent, 20 ScreenGui, 21 Script, 22 ScrollingFrame, 23 Sound,
  24 SpotLight, 25 SpringConstraint, 26 StringValue, 27 SurfaceGui,
  28 TextBox, 29 TextButton, 30 TextLabel, 31 UIAspectRatioConstraint,
  32 UISizeConstraint, 33 UnionOperation, 34 Vector3Value, 35 VehicleSeat,
  36 WeldConstraint` — plná množina dle auditu (Part, Model, VehicleSeat,
  SpringConstraint, HingeConstraint přítomny) ✓.

## 6. Rozhodnutí o strategii parseru (doporučení pro C05/C06)

1. **Žádný externí nástroj/nativní knihovna** — parser bude pure-Python stdlib
   (`struct` + vendored LZ4-block dekompresor ze spike).
2. **Pořadí implementace:** `INST` (hotovo-koncept) → `PRNT` (interleaved
   varinty, schéma známo z auditu) → `PROP` ne-float typy (string/bool/enum/
   int/ref/Color3) → **float/CFrame/Vector3 lane až po Studio ground-truth**
   (kalibrační díl známé velikosti, postup auditu kap. 1).
3. **Read-only kontrakt:** parser nikdy neotevírá RBXM k zápisu; `run_all.py`
   / G-01 brána kontroluje SHA před/po (hash výše).
4. **Rozhodovací pravidlo kol** žije v `src/Inspection/wheel_detect.py` a
   produkční parser ho přebírá doslovně (konjunkce a→b→c, UNKNOWN se záznamem,
   BLOCKED podmínky).

## 7. Hash po práci (nezměněnost)

`sha256sum` pracovní kopie i originálu po všech sondách: oba
`dc8747e0…fedf` — **shodné se stavem před prací, G-01 drží.**

## 8. Otevřené body (neznámé, postup)

- [N] Float/CFrame dekódování (rotované prokládané lane) — postup: Studio
  odečet `Size`/`CFrame` kol FL/FR/RL/RR + kalibrační díl (audit kap. 1/19).
- [N] `PROP 928 vs 927` — přepočet v produkčním parseru.
- [N] `Tune.StAxisOffset` a bug `Velocity.magnitude` (audit §17) — ověřit
  prvním spuštěním ve Studiu; mimo rozsah M2.

---

# C05-C — hardening parseru: referenty, limity, validace (M2, hotovo)

**Datum:** 2026-11-19 · **Vstup (pouze čtení):** pracovní kopie
`assets/chassis-original/chasis-work-copy.rbxm` + druhý soubor
`testgame/src/ServerStorage/VehicleTemplates/JeepTemplate.rbxm`.
**LIMIT (výslovně):** oba soubory mají stejný SHA-256
`dc8747e0…fedf` (230 421 B) — v repu je **jeden distinctní model**,
třetí různý RBXM neexistuje. Testuje se na těchto dvou + syntetických
fixturech (vlastní builder v `tests/test_m2_rbxm_parser.py`).

## A. Referenty: mapování skutečný referent→instance

- Instance se indexují **skutečným referentem** (`id` = referent, výstup
  řazený), žádný předpoklad souvislosti `0..n`: PRNT kids se validují
  jako **množina** proti množině referentů INST (pořadí i rozsah libovolné).
- Duplicitní kid v PRNT = `RbxmCorruptError`; parent mimo referenty
  (i kdyby byl číselně „v rozsahu") = `RbxmHierarchyError` (BLOCKED).
- Duplicitní referent napříč INST = corrupt (beze změny); nově i
  duplicitní INST `type_id` = corrupt.
- Test `test_noncontiguous_referents`: syntetické referenty `[5, 7, 9]`,
  PRNT `[(5,None),(7,5),(9,7)]` projde se správnou mapou parentů.

## B. Limity (kontrola před alokací, bezpečné odmítnutí)

| Limit | Hodnota | Kde se hlídá |
|---|---|---|
| `MAX_FILE_BYTES` | 8 MiB | `parse_rbxm` (getsize) + `parse_bytes` před parsováním |
| `MAX_TOTAL_UNCOMPRESSED` | 256 MiB | `_read_chunks` průběžně před každou dekompresí/alokací |
| `MAX_UNCOMPRESSED_BYTES` (1 chunk) | 256 MiB | hlavička chunku (beze změny) |
| `MAX_CHUNKS` | 100 000 | před appendem (beze změny, zpřísněno) |
| `MAX_INSTANCES` | 10 000 000 | hlavička + INST county (beze změny) |
| `MAX_META_ENTRIES` | 100 000 | `_parse_meta` |

Reálná kopie (230 kB, ~1 MB dekomprimovaně) je hluboko pod stropy.
Test `test_limits_refused_before_alloc`: 8 MiB+ blob a chunk
s `uncomp_len` 300 MiB se odmítnou bez alokace.

## C. Validace Name↔INST, META/SSTR/INST/PRNT/END, corrupt vs unsupported

- **Name↔INST:** PROP pro neznámý `type_id` = corrupt; počet jmen musí
  sedět s počtem instancí typu; **chybějící celé Name PROP → `name: None`,
  `name_status: "missing"`** (evidováno `missing_name_count`/`unnamed_ids`);
  chybějící jméno **nikdy** neznamená rozpoznaný objekt (assess → BLOCKED).
- **META:** duplicitní klíč = corrupt (místo tichého přepsání).
- **INST:** `is_service` musí být 0/1 (reálná kopie: všude 0), jinak corrupt.
- **PRNT:** právě jeden chunk; `version != 0` = **unsupported** (dřív corrupt);
  `prnt_count != num_instances`, špatná délka dat = corrupt.
- **END:** špatné tělo / data za END = corrupt (beze změny).
- **Nepodporované PROP** (všechny typy mimo Name/shape/size/CFrame/CFrame0/
  PivotOffset): přeskočeny, ale **evidovány se `status: "unread"`**
  ve `skipped_props` — není to tichý průchod (reálná kopie: stovky takových,
  např. `BoolValue`, `Color3`, `UDim2`; `Name` s jiným typem = corrupt,
  protože by zamlčel identitu).
- **Rozlišení poškozený vs nepodporovaný:** nová `RbxmUnsupportedError`
  (podtřída `RbxmError`) pro dobře formovaný, ale nepodporovaný obsah:
  jiná verze souboru, neprázdná SSTR tabulka, PRNT verze ≠ 0.
  Vše strukturální = `RbxmCorruptError`; hierarchie = `RbxmHierarchyError`.
- **Fuzz** (`test_fuzz_never_unsafe`, seed `20261119`): **200 mutací**
  (1–3 náhodné byty) + **5 trunkací** (1, 32, 1000, polovina, len−10).
  Výsledek: jen `RbxmError`, nebo strukturálně platný model (stejné počty,
  parenty v množině id, tvary ze známé množiny). Mutace v řetězcích
  zůstává detekovatelná jen hashem (formát nemá checksum) — viz test 12.

# C05-D — geometrie: dekódování shape/size/CFrame + provenience (M2, hotovo)

## Lane-kódování (vlastní reverzní inženýrství, ověřeno křížově níže)

- **Enum/int PROP** (`shape` 0x12): 4 lane, **LSB lane první**, bez zigzagu
  a delt. Důkaz: Part `shape` → `{0: 4, 1: 104, 2: 1}` = 4× Ball (kola),
  104× Block, 1× Cylinder — kola = Ball dle auditu §10.
- **Floaty** (`size` 0x0E, pozice CFrame): **component-major** (X/Y/Z pole
  za sebou, každé 4 lane), **MSB lane první**, u32 transformováno
  **ror1** (`bits = (w >> 1) | ((w & 1) << 31)`). Důkaz: 327/327 kladných,
  kola `(2.7, 2.7, 2.7)`, 4 středy symetrické (níže); `VehicleSeat.size`
  (N=1) = `(2, 1, 2)` = defaultní seat.
- **CFrame** (0x10): nejprve **orientační bloky** instancí
  (`u8 id` + pro `id 0` matice 9× f32 **plain LE**, bez lane/rotace),
  pak **pozice jako float lane** výše. Důkaz: Part 5341 = 109×(1+36) +
  12×109; matice 109/109 ortonormální, det +1.
- Orientační id: `0` = vlastní matice; `2` = identita bez dat (všechny
  PivotOffset = samé `2`, pozice přesně `(0,0,0)`); **jiné id = neověřená
  preseta → orientace `unread`** (Attachment: 56× id `32`, poctivě
  neinterpretováno — tabulka preset bez ground-truth).

## Provenience u každé vlastnosti (D)

Každá instance nese `props[vlastnost] = {status, trusted, how, …}`:
`status` = `read`/`missing`/`unread`; `trusted=True` jen u tvaru (enum,
křížově ověřen); floaty vždy `trusted=False` (bez Studio ground-truth).
Geometrie se **nikdy neodvozuje z názvů** — jen z PROP (test E3: samotné
jméno FL bez PROP → `bad_shape`/`missing_*` + BLOCKED).
`model["geometry"] = PARTIAL` + `calibration: NOT_IMPLEMENTED`.

## Výsledky kol na reálné kopii (E)

| Kolo | id | tvar | size (studs) | střed (studs) |
|---|---|---|---|---|
| FL | 3 | Ball | (2.7, 2.7, 2.7) | (−45.19, 23.62, −203.25) |
| FR | 52 | Ball | (2.7, 2.7, 2.7) | (−51.18, 23.62, −203.25) |
| RL | 101 | Ball | (2.7, 2.7, 2.7) | (−45.19, 23.62, −213.77) |
| RR | 150 | Ball | (2.7, 2.7, 2.7) | (−51.18, 23.62, −213.77) |

Rozchod ≈ 5.99, rozvor ≈ 10.52, stejné Y; matice všech Partů ortonormální
(109/109, det +1); Union/WeldC/Seat CFrame též 100 % (40/40, 108/108, 1/1).

## (E) Geometrické posouzení: `assess_wheel_geometry` (nové, v parseru)

`wheel_detect.py` se **neměnil**. Nová vrstva zrcadlí pravidlo (a)+(b)+(c)
a přidává: sféricitu (≤ 1 %), shodu rozměrů (≤ 1 %), obdélník středů
(2 shluky X × 2 shluky Z, tolerance 0.06; stejné Y ± 0.05) a evidenci
floatů. Na reálné kopii: 4× `GEOMETRY_OK` se středy/rozměry, ale
**BLOCKED** — (1) 44 dílů podvozku (ramena, huby, pružiny) parentovaných
ve stromě `Wheels` = identitně UNKNOWN (pravidlo M2.2, geometrií vyloučeny
jako Block, ale BLOCKED trvá — žádné tiché překlasifikování); (2) níže (F).
Syntetika: konzistentní 4 kola → jediný důvod BLOCKED je kalibrace;
ne-obdélník → `rectangular` důvod; chybějící PROP → `bad_shape`/
`missing_size`/`missing_position`.

## (F) Kalibrace studs/m: PŘIPRAVENA, ale NOT IMPLEMENTED

`calibrate_studs_per_meter()` existuje jako rozhraní + provenience, ale
**vždy vrací `NOT_IMPLEMENTED`** (i s argumenty — ty eviduje jako
`inputs_ignored`). Důvod: bez Studio ground-truth (kalibrační díl známé
velikosti odečtený ve Studiu) nelze ověřit dekódování floatů ani měřítko;
strukturální důkazy (ortonormalita, symetrie, defaultní seat) nejsou
prohlášení za ověřené. Ověření = úkol M3. Hodnota `studs_per_meter`
nikde v M2 nevystupuje jako číslo.

## Hash po práci (G-01)

`sha256sum` obou pracovních kopií po všech sondách a testech:
`dc8747e0…fedf` — shodné se stavem před prací; čtení proběhlo vždy
`open(rb).read()`, žádný soubor nebyl otevřen k zápisu.
