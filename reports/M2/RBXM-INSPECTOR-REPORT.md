# M2 — RBXM Inspector Report (Agent A)

**Datum:** 2026-11-19 · **Větev:** `feat/m2-m3-geometry` (HEAD `ab840a9`, PR #2 nemergován)
**Vstup (pouze čtení):** `assets/chassis-original/chasis-work-copy.rbxm` (+ `testgame/.../JeepTemplate.rbxm`,
`C:/Users/adamr/Downloads/chasis.rbxm` — všechny tři stejný soubor, viz níže)
**Parser:** `src/Inspection/rbxm_parser.py` (stdlib only, read-only) · **Testy:** `tests/test_m2_rbxm_parser.py`
(54 testů, všechny procházejí) + nový `tests/test_m2_rbxm_inspector.py` (důkazní, aditivní)
**Kontrakt:** `reports/M2-M3-CONTRACTS-FREEZE-v1.md` (zmrazený, neměněn)

## 1. Podporované vs nepodporované části formátu (s důkazy)

| Oblast | Stav | Důkaz |
|---|---|---|
| Hlavička (magic, signatura, verze 0, počty, reserved) | READ | `parse_rbxm` → `num_types=37, num_instances=815`; špatné magic/reserved/version → `RbxmCorruptError` / `RbxmUnsupportedError` (testy 2–3, §5) |
| Rámečky chunků + LZ4 pure-Python | READ | census `META:1 SSTR:1 INST:37 PROP:928 PRNT:1 END:1`, konec přesně na `END` (shoda se spike §4; `PROP 928` vs audit `927` potvrzen — audit nepočítá prázdný/typový chunk, nepodstatné) |
| META (slovník, explicitní `ExplicitAutoJoints=true`) | READ | `meta={'ExplicitAutoJoints':'true'}`; duplicitní klíč = corrupt (test) |
| SSTR prázdná (`nshared=0`) | READ | `sstr={'shared_strings':0}`; **neprázdná = `RbxmUnsupportedError`** (ne corrupt) — ověřeno §5 |
| INST (37 typů, 815 referentů `0..814` jako množina) | READ | třídy 0–36 shodné se spike §5; duplicitní referent/typ, `is_service ∉ {0,1}` = corrupt |
| PRNT v0 (815 vazeb, 1 kořen) | READ | parenty validovány jako množina; duplicitní kid, subset, cyklus, self-loop, les (2 kořeny), parent mimo referenty = odmítnuto (testy F2/F7) |
| PROP `Name` (string, identita) | READ | všech 815 jmen přítomno (`missing_name_count=0`); chybějící celé Name PROP → `name:None, missing` (nikdy rozpoznáno) |
| PROP `shape` = Ball (0) | READ, trusted | 4× `Ball` = kola FL/FR/RL/RR (id 3/52/101/150), invariantní vůči pořadí lane |
| PROP `shape` = Block/Cylinder na reálné kopii | **UNREAD (nepodporováno)** | 105× Part `shape=None`, důvod `neznama hodnota enum 16777216 (=0x01000000)` — viz nález N1 |
| PROP `size`, `CFrame/CFrame0/PivotOffset` (pozice+matice) | READ strukturálně, **trusted=False** | kola `(2.7,2.7,2.7)`, středy symetrické (§3); kalibrace `NOT_IMPLEMENTED` bez Studio ground-truth |
| CFrame orientační presety mimo id 0/2 | UNREAD (nepodporováno) | Attachment 56× id `32` → matice `None`, `unread` (test preset-sweep F6) |
| Všechny ostatní PROP typy (bool/int/float-solo/Color3/UDim/ref/…) | UNREAD, evidováno | **879× `skipped_props`** se `status:unread` (top: `0x02`=176, `0x12`=143, `0x04`=130, `0x01`=118); žádný tichý průchod |
| Neznámé chunky | přeskočeny, evidovány | `skipped_chunks` (ověřeno syntetickým `XXXX`, §5); integrita LZ4 kontrolována |
| Jiná verze souboru / PRNT verze ≠ 0 | `RbxmUnsupportedError` (ne corrupt) | ověřeno §5 — rozlišení poškozený vs nepodporovaný drží |

## 2. Read-only + hash dc8747e0… před/po

`open(rb).read()`, žádný zápis; SHA-256 všech tří kopií před i po práci:
`dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf` (230 421 B) — shodné, G-01 drží.
**LIMIT:** v repu je jeden distinctní model (work-copy = JeepTemplate = originál); třetí různý RBXM neexistuje.

## 3. Determinismus

Dvojí `parse_rbxm` → kanonické JSON shodné (byte-přesně). Fuzz v testech s pevným seedem `20261119`
(200 mutací + trunkace; F8: 1000bytový fuzz). Parse reálné kopie ~0.04 s.

## 4. Poškozené / chybějící / neznámé vstupy (vše ověřeno živě)

- Prázdný soubor → `RbxmCorruptError` (kratší než hlavička); zkrácený soubor → `Corrupt` (chunk přesahuje konec);
  1B mutace → `Corrupt` (LZ4 offset) nebo strukturálně platný model (mutace v řetězcích detekovatelná jen hashem — formát nemá checksum).
- Chybějící soubor → `RbxmCorruptError` (nelze přečíst, errno 2). Chybí-li obě reálné kopie, testy čtení hlásí SKIP (PENDING), nikdy ERROR.
- Neznámý chunk `XXXX` → zaparsováno, `skipped_chunks=['XXXX']`. Verze souboru 1 → `Unsupported`. PRNT verze 1 → `Unsupported`.
- Fuzz: nikdy nic jiného než `RbxmError`, nebo platný model se stejnými počty a parenty v množině id.

## 5. Limity (kontrola před alokací)

`MAX_FILE_BYTES` 8 MiB (getsize + `parse_bytes`), `MAX_TOTAL_UNCOMPRESSED` 256 MiB průběžně,
`MAX_UNCOMPRESSED_BYTES` 256 MiB, `MAX_CHUNKS` 100 000, `MAX_INSTANCES` 10 000 000,
`MAX_META_ENTRIES` 100 000, `MAX_FIELD_VALUES` 100 000 na jedno pole. Reálná kopie (230 kB) hluboko pod stropy.
Test `test_limits_refused_before_alloc` odmítá 8 MiB+ blob a 300 MiB chunk bez alokace.

## 6. Nová zjištění (Agent A)

- **N1 — lane-pořadí enum PROP (upřesnění spike C05-D):** kód `_decode_enum_lanes` a `how`-řetězec tvrdí
  „LSB lane první", ale surová data reálné kopie leží v **poslední** lane (MSB první): hodnota 1/Block se dekóduje
  jako `0x01000000 = 16777216` → `unread`. Živě potvrzeno (105× Part `shape=None` s tímto důvodem).
  Chování je **bezpečné** (nepodporováno místo špatného tvaru, kola=Ball invariantní), ale `how`-text a docstring
  jsou fakticky nepřesné a 104× Block + 1× Cylinder zůstávají `unread`. **Neopravuji** (cizí kód) — předávám
  koordinátorovi k rozhodnutí: buď přepnout dekodér na MSB-first s re-verifikací, nebo ponechat a opravit dokumentaci.
- **N2 — `PROP 928 vs audit 927`:** potvrzeno živě (`chunk_census` 928); rozdíl = prázdný/typový chunk, pro M2 nepodstatné.
- **N3 — `shape` v `skipped_props`:** `shape` s neznámou hodnotou není ve `skipped_props` (je v `props.shape`
  jako `unread`) — `skipped_props` obsahuje jen ostatní typy (`0x12` = 143× jiné enumy). Konzistentní, jen evidence.
- Chyba v parseru k záznamu s reprodukcí: **N1 výše** (reprodukce: `parse_rbxm` work-copy → instance id 9
  `props.shape = {status:unread, reason:'neznama hodnota enum 16777216…'}`).

## 7. Shrnutí dle §16

- **Úkol:** RBXM Inspector — podporované/nepodporované části, read-only, determinismus, vstupy, limity.
- **Práce:** živé sondy parseru na reálné kopii (hash, census, determinismus, assess, poškozené/neznámé vstupy),
  běh 54 existujících testů (OK), nový důkazní test, tento report.
- **Poznatky:** formátová podpora viz tabulka §1; 4 kola `GEOMETRY_OK` (Ball, 2.7, symetrické středy), ale celek
  `BLOCKED` (44 UNKNOWN kandidátů ve stromě `Wheels` + `float_decode_unverified`); `assess` rozchod ≈ 5.99, rozvor ≈ 10.52.
- **Fakta:** hash `dc8747e0…fedf` před/po shodný; census 37/815/928; 879 `skipped_props`; 0 chybějících jmen;
  parse ~0.04 s; 54/54 testů OK.
- **Testy:** `tests/test_m2_rbxm_parser.py` 54/54 OK (25.9 s); nový `tests/test_m2_rbxm_inspector.py` 7/7 OK.
- **Commit:** neznámý (pracuji na větvi `feat/m2-m3-geometry` HEAD `ab840a9`, žádné git operace).
- **Problémy:** N1 (lane-pořadí enum, zaznamenáno s reprodukcí, neopraveno); jinak žádný nový problém.
- **Rizika:** jediný distinctní model v repu (LIMIT); mutace v řetězcích bez checksumy; floaty bez Studio ground-truth.
- **Další krok:** koordinátor rozhodne N1 (MSB-first vs dokumentace); poté M3 kalibrace ve Studiu.
