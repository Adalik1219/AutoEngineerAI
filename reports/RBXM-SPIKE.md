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
