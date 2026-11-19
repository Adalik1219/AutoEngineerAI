# AUDIT2 geometrie — rbxm_parser.py + wheel_detect.py (FÁZE A, audit only)

Větev `feat/m1-m2-foundation`, HEAD `6cedbe1` (PR #2 OPEN, NEMERGOVAT).
Rozsah: `src/Inspection/rbxm_parser.py` + `src/Inspection/wheel_detect.py` +
testy `tests/test_m2_rbxm_parser.py`, `tests/test_m2_wheel_detect.py`.
Navazuje na `reports/AUDIT-geometry.md` (HEAD `0f5b923`); změny mezi revizemi
jsou hardening-commit `ff6f266`. Žádný kód se neměnil; vše níže je ověřeno
během proti pracovní kopii (`assets/chassis-original/chasis-work-copy.rbxm`,
sha256 `dc8747e0…2c1fefdf`, 815 instancí / 37 typů) a syntetickými testy.

## Verdikt

- Reálný soubor: 4 kola Ball 2.7³, středy 2×2 obdélník, Y-spread 0.0 —
  `detect_wheels` 4× WHEEL + BLOCKED, `assess` 4× GEOMETRY_OK + BLOCKED.
  Obojí správně (44 legitimních dílů podvozku + neověřená kalibrace).
- Všechny 3 nálezy P0 z AUDIT-geometry.md jsou OPRAVENY a kryty testy
  (B1: `nonfinite_size`, `nonfinite_position`, `nonfinite_rotation`).
  P1 validace rotace je OPRAVENA (`invalid_rotation` + `unread_rotation`).
- Žádný otevřený P0. Zůstávají P2 (magické tolerance, neověřená preset-tabulka,
  neznámý shape-enum 16777216, bez horního stropu konečných hodnot).
- Kalibrace `studs_per_meter` stále NOT_IMPLEMENTED — správně, drží BLOCKED
  do M3 Studio ground-truth.

## Ověřené uzávěry (požadované body)

- **isfinite brány: ANO.** Per-kolo `size` (`nonfinite_size`), `position`
  (`nonfinite_position`), `rotation` (`nonfinite_rotation`) + obranná brána
  před křížovými výpočty (`nonfinite wheel geometry in cross-check`).
  Testy: `test_assess_inf_size_blocked`, `test_assess_nan_size_label`,
  `test_assess_inf_nan_position_blocked`, `test_assess_nonfinite_rotation_blocked`
  — vše PASS (74/74 v obou souborech, plná suita 256 PASS / 0 FAIL / 4 PENDING).
- **Matice ortonormalita: ANO.** `_is_rotation_matrix` (řádky jednotkové/kolmé,
  det +1, tol 1e-3). Škálující (2·I) i převrácená (det −1) → `invalid_rotation`
  + BLOCKED (`test_assess_invalid_rotation_blocked`). Živě: rotace FL je
  ortonormální (True).
- **Presety: ANO, s evidovaným limitem.** id 0 = vlastní matice,
  id 2 = identita (řetězec `"identity"`), jiné id → `rotation=None` +
  `unread-preset-N` → `unread_rotation` + BLOCKED (`test_assess_unread_rotation_blocked`,
  D2). Tabulka preset-id mimo 0/2 není ověřena — převzato tvrzení souboru,
  ne fakt (P2 níže).
- **Tolerance: přítomny, ale bez zdroje (P2).** `_clusters` 0.06, výškový práh
  0.05, sféricita/konzistence 0.01, ortonormalita 1e-3. Na reálné kopii sedí
  s rezervou (size rozptyl 0.0, Y-spread 0.0), ale žádná není ukotvena ke
  Studio ground-truth — při M3 kalibraci znovu odvodit, ne opsat.
- **FL/FR/RL/RR klasifikace: ANO.** Konjunkce (a) v Model:Wheels + (b) jméno +
  (c) Ball; 8 kombinací kryto `test_classify_conjunction_all_three_required`.
  Živě: FL(−45.19,·,−203.25) FR(−51.18,·,−203.25) RL(−45.19,·,−213.77)
  RR(−51.18,·,−213.77) = 2×2 mřížka, symetrická.
- **44 dílů podvozku: inventář stále platí.** Živě přepočítáno: 44 Part
  ve stromě Wheels mimo kola, všechna shape None (unread), `unidentified` = 44.
  Struktura 11 dílů × 4 rohy (SuspensionGeometry 8/57/106/155, Weld 13/62/111/160)
  se nezměnila; `detect` ani `assess` je správně neignorují ani neomlouvají.
- **BLOCKED držení: ANO.** Reálná kopie: `detect` 1 důvod
  (`UNKNOWN …: 44`); `assess` 2 důvody (44 + `float_decode_unverified`).
  Chybějící/duplicitní Wheels, cyklus, missing parent, duplicitní id, les,
  chybějící geometrie — vše BLOCKED s testem.
- **Kalibrace NOT IMPLEMENTED: ANO.** `calibrate_studs_per_meter` vždy
  NOT_IMPLEMENTED vč. ignorování vstupů; `geometry.calibration.status` i
  `assess.calibration.status` NOT_IMPLEMENTED; `trusted=False` na všech
  floatech. Hash souboru čtením neměněn (test 12).

## Nálezy

### P2 — magické tolerance bez zdroje (přetrvává z AUDIT §P2)

`_clusters` 0.06, Y-práh 0.05, sféricita/konzistence 0.01, `_is_rotation_matrix`
tol 1e-3. Funkční, ale žádná hodnota není odvozena z měření. Při M3 znovu
odvodit ze Studio ground-truth.

### P2 — preset-tabulka CFrame mimo id 0/2 neověřena (známý LIMIT)

`rotation="identity"` u id 2 je převzaté tvrzení souboru. Kód to značí
správně (`identity-preset (tabulka neoverena)`), jen připomínám pro M3:
před jakýmkoli použitím orientace ověřit proti Studiu.

### P2 — shape-enum 16777216 (0x01000000) u 44 dílů podvozku neznámý

Kód řeší správně (`unread`, `shape=None` → `bad_shape`, žádný odhad).
Význam hodnoty není ověřen (očekávaně non-Ball PartType, ale mapování zná
jen 0/1/2). Pro M3 zdokumentovat, až bude Studio ground-truth.

### P2 — bez horního stropu konečných hodnot + parse/assess asymetrie

Konečné, ale absurdní hodnoty (např. size 1e30) projdou jako `read` /
GEOMETRY_OK — řeší stejná budoucí rozsahová brána jako P2 výše.
Související: neortonormální matice je v parse-vrstvě stále `read`
(`trusted=False`), blokuje až `assess` (`invalid_rotation`) — pro M2
dostačující, protože parse-vrstva nikdy nic neprohlašuje za ověřené.
Globální cyklus mimo řetěz kol: `parse_bytes` ho odmítne (`_check_hierarchy`),
`assess`/`detect` ho nevidí (chodí jen předky Partů) — bez dopadu na M2
(les/cyklus na cestě kol je BLOCKED všude), jen konstatuji pro M3.

## Co je správně (neměnit)

Trusted flags (shape `True`, floaty `False` s důvodem), žádná geometrie
z jména (`missing_size`/`missing_position`/`bad_shape`), neznámý enum →
`unread`, prohozené lane → jiná hodnota + stále BLOCKED (E4), hierarchie
→ výjimka/BLOCKED, `forest` politika ve všech třech cestách
(parse/detect/assess), determinismus, `inputs_ignored` u kalibrace.
