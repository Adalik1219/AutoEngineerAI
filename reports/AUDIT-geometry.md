# AUDIT geometrie — rbxm_parser.py + wheel_detect.py (FÁZE A, audit only)

Větev `feat/m1-m2-foundation`, commit `0f5b923`. Rozsah: `src/Inspection/rbxm_parser.py`
(Shape/Size/CFrame dekódování, trusted flags, `assess_wheel_geometry`) +
`src/Inspection/wheel_detect.py` (identitní pravidlo, klasifikace FL/FR/RL/RR) + testy
`tests/test_m2_rbxm_parser.py`, `tests/test_m2_wheel_detect.py`.
Žádný kód se neměnil; všechny nálezy jsou ověřeny spuštěním proti pracovní kopii
(`assets/chassis-original/chasis-work-copy.rbxm`, sha256 `dc8747e0…2c1fefdf`, 815 instancí / 37 typů)
a syntetickými fixture stavěnými existujícím test-builderem.

## Verdikt

- Reálný soubor: geometrie 4 kol je strukturálně konzistentní (Ball, size 2.7³, symetrický
  obdélník středů, stejné Y), všechny floaty v souboru jsou konečné (ověřeno
  `math.isfinite` přes všechny size/position v modelu — 0 nekonečných).
- `detect_wheels`: 4× WHEEL, ale BLOCKED — 44 UNKNOWN dílů podvozku ve stromě Wheels.
  Správně, nejde o chybu (viz tabulka níže).
- `assess_wheel_geometry`: 4× GEOMETRY_OK, ale BLOCKED — kalibrace NOT IMPLEMENTED
  + 44 UNKNOWN. Správně drží BLOCKED do Studio ground-truth (M3).
- Latentní vada P0: `assess` umí přijmout neplatnou geometrii jako GEOMETRY_OK
  (`+Inf` size i pozice prochází per-kolo verdiktem; důkaz níže). Na reálném souboru
  se neprojevuje, ale je to díra ve validační vrstvě, ne jen chybějící kalibrace.

## Nálezy

### P0 — `assess` přijme `+Inf` size jako GEOMETRY_OK (dokázáno synteticky)

- `src/Inspection/rbxm_parser.py` ř. 1068–1075: kontrola size je
  `isinstance(v, float)` + `v > 0` + sféricita `max-min > 0.01*max`.
  Žádné `math.isfinite`. Pro `size=(inf,inf,inf)`: `inf > 0` je True,
  `max-min = inf-inf = nan`, `nan > …` je False → projde.
- Následná křížová kontrola (ř. 1116–1120) je stejným inf poražena:
  `ref=inf`, `abs(2.7-inf)=inf`, `inf > 0.01*inf (=inf)` je False → projde.
- Ověřeno: syntetický model se 4 koly, FL size `(inf,inf,inf)` →
  `wheels['FL']['status'] == 'GEOMETRY_OK'`, jediný blocked_reasons je kalibrační
  catch-all (ř. 1146–1148). Per-kolo verdikt je tedy nepravdivý; BLOCKED drží jen
  náhodou díky poslednímu `block(...)`, ne díky geometrii.

### P0 — `assess` přijme `+Inf`/`NaN` pozici jako GEOMETRY_OK (dokázáno synteticky)

- Ř. 1076–1080: u pozice se kontroluje jen `None` / `status != "read"`.
  Žádný `isinstance`, žádné `isfinite`, žádný rozsah.
- Ověřeno: pozice FL `(inf,1.0,0.0)` i `(nan,1.0,0.0)` →
  `wheels['FL']['status'] == 'GEOMETRY_OK'`. Agregátní layout-kontrola (ř. 1121–1142)
  to v těchto případech zachytila (`wheel layout not rectangular`), ale per-kolo
  verdikt zůstává GEOMETRY_OK, což je špatně — neplatné kolo se nesmí tvářit jako
  geometricky OK ani na dílčí úrovni.
- `NaN` size je naproti tomu zachycen jen náhodou (`nan > 0` je False →
  `nonpositive_size`); nulové a záporné size jsou zachyceny korektně (`v > 0`,
  ověřeno synteticky: `(0,0,0)` → `nonpositive_size`).

### P0 — v celé geometrické cestě chybí `math.isfinite`

- Grep `isfinite|isnan|isinf` přes `src/Inspection/`: jediný výskyt je mimo geometrii
  (`units.py`). Konkrétně bez kontroly: `_decode_float_lanes` (ř. 251–273, `struct.unpack`
  může vyrobit inf/nan/subnormály a projdou jako `read`), `_parse_cframe_array`
  matice (ř. 298–310), size-kontrola (ř. 1068–1075), position-kontrola (ř. 1076–1080),
  křížová konzistence (ř. 1116–1120), layout-shluky (ř. 1121–1142).
- Doporučení pro FÁZI B (neměnit teď): `isfinite` brána na každém floatu hned za
  `_decode_float_lanes` / `_parse_cframe_array` (status `unread` + reason, ne tichý
  průchod), plus `isfinite` v `assess` před každým výpočtem → `bad_size` /
  `missing_position`-ekvivalent a per-kolo UNKNOWN.

### P1 — rotační matice CFrame se nikdy nevaliduje

- Ř. 839–851 a 874–899: matice z bloku id 0 se přebírá doslovně (`tuple(matrix)`),
  bez kontroly konečnosti, ortonormality či determinantu. `rotation_status`
  rozlišuje jen `matrix` / `identity` / `unread-preset-N`. Převrácená nebo škálující
  matice by prošla jako `read`. Pro M2 (pouze středy + rozměry) je to přijatelné,
  před jakýmkoli použitím orientace (M3) je nutná validace.

### P1 — presety orientace mimo id 0/2 jsou neověřené (známý LIMIT, evidován správně)

- Ř. 305–308: `matrices.append(None)` + `rotation_status = "unread-preset-N"`.
  Na reálné kopii se nevyskytuje (vše id 0 s maticí), syntetický test D2 kryje.
  Není to nález proti kódu, jen připomenutí: tabulka preset-id není ověřena, takže
  `rotation="identity"` (ř. 846–848) je převzaté tvrzení souboru, ne fakt.

### P1 — shape všech 44 dílů podvozku je `unread`, enum 16777216

- Všech 44 Part ve stromě Wheels mimo kola má
  `props.shape = {status: unread, reason: "neznama hodnota enum 16777216; …"}`.
  Hodnota `16777216 = 0x01000000` je u všech identická — konzistentní, ale její význam
  není ověřen (mělo by jít o non-Ball PartType, ale mapování zná jen 0/1/2).
  Kód to řeší správně (žádný odhad, `shape=None` → `bad_shape`), jen konstatuji pro M3.

### P2 — magické tolerance bez zdroje

- `_clusters` tolerance `0.06` (ř. 549–557), výškový práh `0.05` (ř. 1130),
  sféricita a konzistence `0.01` (ř. 1074, 1118). Na reálné kopii sedí s rezervou
  (kola přesně 2.7, Y identická), ale žádná z hodnot není ukotvena ke Studio
  ground-truth. Při M3 kalibraci znovu odvodit, ne opsat.

### P2 — `position` bez typové kontroly, `size` bez rozměrového stropu

- Ř. 1076–1080 nepoužívá ani `isinstance(v, float)` (size ho má, ř. 1068).
  Absurdní, ale konečné hodnoty (1e30) projdou oběma kontrolami. Řeší stejná
  `isfinite`+rozsah brána jako P0.

## Co je správně (explicitně potvrzuji, neměnit)

- Trusted flags: shape `trusted=True` (křížově ověřeno: kola = Ball),
  size/CFrame/pozice/matice `trusted=False` s důvodem (ř. 775–776, 818–826, 852–859).
- Chybějící geometrie nikdy neodvozena z jména (E3, `missing_size`/`missing_position`/`bad_shape`).
- Neznámý shape enum → `unread`, kolo UNKNOWN (E5). Prohozené lane → trusted zůstává False (E4).
- Hierarchie: duplicitní id, cykly, neplatný parent → výjimka → BLOCKED, nikdy validní výsledek.
- `calibrate_studs_per_meter` vždy NOT_IMPLEMENTED (F). Hash souboru se čtením nemění (12/12b).
- Reálný soubor: 0 nekonečných size/position; 4 kola GEOMETRY_OK se správnými symetriemi.

## BLOCKED důvody na reálné kopii (doslovně)

- `detect_wheels`: status BLOCKED, jediný důvod
  `UNKNOWN candidate(s) inside Model:Wheels: 44`.
- `assess_wheel_geometry`: status BLOCKED, důvody
  `UNKNOWN candidate(s) inside Model:Wheels: 44` a
  `float_decode_unverified: rozmery a stredy jsou precteny, ale bez Studio
  ground-truth nedurveryhodne ke kalibraci (kalibrace studs/m NOT IMPLEMENTED)`.
- OK vyžaduje M3: Studio ground-truth (kalibrační díl známé velikosti) + ověřená
  kalibrace + `isfinite` brána (P0 výše). Do té doby zůstává BLOCKED správně.

## Tabulka: 44 dílů ve stromě Wheels, které nejsou kola

Všech 44 je `class_name=Part` uvnitř `Model:Wheels` (id 2, parent `0 A-Chassis 6C by Novena`).
Každý porušuje identitní pravidlo (b)+(c): jméno ∉ FL/FR/RL/RR a shape None
(`unread`, enum 16777216) → `failed_checks = [bad_designation, bad_shape]` → UNKNOWN.
Nejde o chybu modelu ani parseru: je to legitimní podvozek — 11 dílů zavěšení
(SpringBottom, CLower, CUpper, SpringTop, LowerArmB, LowerArmF, Hub, LowerArm,
UpperArmF, UpperArmB, UpperArm) × 4 rohy (FL/FR/RL/RR). Rodiče 8/57/106/155 =
`SuspensionGeometry` (pod příslušným kolem), 13/62/111/160 = `Weld` (pod
SuspensionGeometry). Zbytek stromu (148 instancí: Model/WeldConstraint/Attachment/
HingeConstraint/CylinderMesh/SpringConstraint/Vector3Value) nejsou Part, takže je
`detect_wheels` / `assess` správně ignorují a do tabulky nepatří.

| id | název | class | parent | proč není kolo |
|----|-------|-------|--------|----------------|
| 9 | SpringBottom | Part | 8 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 14 | CLower | Part | 13 Weld | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 17 | CUpper | Part | 13 Weld | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 20 | SpringTop | Part | 8 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 22 | LowerArmB | Part | 8 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 26 | LowerArmF | Part | 8 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 30 | Hub | Part | 8 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 31 | LowerArm | Part | 8 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 37 | UpperArmF | Part | 8 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 41 | UpperArmB | Part | 8 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 45 | UpperArm | Part | 8 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 58 | SpringBottom | Part | 57 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 63 | CLower | Part | 62 Weld | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 66 | CUpper | Part | 62 Weld | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 69 | SpringTop | Part | 57 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 71 | LowerArmB | Part | 57 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 75 | LowerArmF | Part | 57 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 79 | Hub | Part | 57 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 80 | LowerArm | Part | 57 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 86 | UpperArmF | Part | 57 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 90 | UpperArmB | Part | 57 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 94 | UpperArm | Part | 57 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 107 | SpringBottom | Part | 106 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 112 | CLower | Part | 111 Weld | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 115 | CUpper | Part | 111 Weld | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 118 | SpringTop | Part | 106 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 120 | LowerArmB | Part | 106 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 124 | LowerArmF | Part | 106 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 128 | Hub | Part | 106 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 129 | LowerArm | Part | 106 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 135 | UpperArmF | Part | 106 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 139 | UpperArmB | Part | 106 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 143 | UpperArm | Part | 106 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 156 | SpringBottom | Part | 155 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 161 | CLower | Part | 160 Weld | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 164 | CUpper | Part | 160 Weld | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 167 | SpringTop | Part | 155 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 169 | LowerArmB | Part | 155 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 173 | LowerArmF | Part | 155 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 177 | Hub | Part | 155 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 178 | LowerArm | Part | 155 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 184 | UpperArmF | Part | 155 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 188 | UpperArmB | Part | 155 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
| 192 | UpperArm | Part | 155 SuspensionGeometry | (b) jméno ∉ FL/FR/RL/RR + (c) shape None (unread enum 16777216) → UNKNOWN, legitimní díl podvozku |
