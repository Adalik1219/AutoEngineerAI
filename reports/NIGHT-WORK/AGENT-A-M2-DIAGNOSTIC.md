# Agent A – M2 technický audit a diagnostika

- Větev: `feat/m2-m3-geometry`, HEAD `9803db3` (ověřeno `git rev-parse`).
- Rozsah čtení: `src/Inspection/rbxm_parser.py`, `src/Inspection/wheel_detect.py`,
  `src/Inspection/scale_calibration.py`,
  testy `test_m2_rbxm_parser`, `test_m2_wheel_detect`,
  `test_m2_scale_calibration`, `test_m2_rbxm_inspector`, `test_m2_integration`.
- Pravidla dodržena: RBXM pouze čteno (hash `dc8747e0…fefdf`, 230421 B, před/po shodný),
  `C:/.DATA/RobloxSimulator` nedotčen, žádné nové runtime tvrzení, žádný merge.
- Stav testů (ověřeno během auditu, `python -m unittest`): scale+wheel+inspector
  91 testů OK; integrace 20 testů OK; parser 57 testů OK.

## 1. Jak M2 počítá výsledek (ověřený řetězec)

1. `parse_rbxm` → 815 instancí / 37 typů, 1 kořen, `Model:Wheels` + 4× `Ball`
   (id 3/52/101/150). Tvar `trusted=True`, floaty `trusted=False`.
2. `detect_wheels` → 4× `VALID_WHEEL`, 44× `KNOWN_NON_WHEEL`, `status OK`,
   neblokuje (ověřeno integračním testem).
3. `assess_wheel_geometry` → 4× `GEOMETRY_OK` (středy/rozměry/obdélník sedí),
   **ale celek `BLOCKED`**, právě 1 důvod `float_decode_unverified`
   (ověřeno testem `test_assess_blocked_float_unverified`).
4. `report_from_assess` → propagace každého assess důvodu do
   `assess_blocked_reasons` ⇒ `overall_status BLOCKED`, per-kolo `GEOMETRY_OK`
   v těle reportu zůstává (záměr, test `test_assess_blocked_propagates_to_report`).
5. `calibrate` z reportovacích měření → `overall_status BLOCKED`, důvod
   `nekonzistentní měřítko: rozptyl odhadů 7.44 % > 5 %`.
6. `usable_for_m3` → `False`, `require_verified_for_m3` zvedá
   `CalibrationBlockedError`. M3 brána je zavřená správně.

## 2. Vstupy kalibrace (`scale_calibration.calibrate`)

- `references` (default `default_references()`, profil M1 / Mustang GT 2024 EU):
  `wheelbase` 2.719 m VERIFIED, `track_f` 1.585 m VERIFIED,
  `track_r` 1.642 m VERIFIED, `tire_d_f` 0.6866 m ESTIMATED (výpočet
  z designace 255/40 R19), `tire_d_r` 0.7026 m ESTIMATED (275/40 R19).
  `unit` povinně `'m'`, každý záznam má `source` + `status` + `uncertainty_si`.
- `measurements_studs`: `wheelbase / track_f / track_r / tire_d_f / tire_d_r`
  ve studs (z `inspection_report`), `None` = chybí; `0`/zápor/NaN/inf = výjimka.
- `u_studs` (default 0.05): nejistota měření v RBXM, symetrická 1σ.

## 3. VERIFIED vs ESTIMATED (`scale_calibration.py:292-296`)

```python
all_verified = all(st == "VERIFIED" for _, _, st in per_param.values())
max_dev = max(abs(v) for v in deviations.values())
status = "VERIFIED" if (all_verified and max_dev <= VERIFIED_MAX_DEV_PCT) else "ESTIMATED"
```

- `VERIFIED` = **všechny použité reference VERIFIED** A zároveň
  `max |odchylka| <= 2.0 %` (`VERIFIED_MAX_DEV_PCT`).
- Jinak (jakákoli ESTIMATED reference nebo větší odchylka) = `ESTIMATED`.
- Důsledek pro reálná data: i kdyby rozptyl prošel, plná sada s pneu
  ESTIMATED dává strop `ESTIMATED` (test `test_mixed_status_is_estimated`;
  `test_estimated_does_not_pass_gate`).

## 4. Rozptyl a nezávislé rodiny (`scale_calibration.py:244-273`)

- Odhad na parametr: `est = studs / SI_m`; rodiny `PARAM_FAMILY`:
  `wheelbase → wheelbase`, `track_f/track_r → track`,
  `tire_d_f/tire_d_r → tire_diameter`.
- Brána `< 2 nezávislé rodiny → BLOCKED` (závislé páry se nepočítají dvakrát).
- Rozptyl: `spread = (max-min)/mean*100 > 5 % → BLOCKED` (`M2.10`).
- Výpočet je deterministický (řazení + pevné pořadí součtů), ověřeno testy
  determinismu.

## 5. `overall_status` / `usable_for_m3` / `require_verified_for_m3`

| `overall_status` | Význam | `usable_for_m3` | `require_verified_for_m3` |
|---|---|---|---|
| `VERIFIED` | vše VERIFIED + odchylky ≤ 2 % | `True` | projde |
| `ESTIMATED` | konzistentní, ale ne vše VERIFIED | `False` | `CalibrationBlockedError` |
| `UNKNOWN` | žádná měření (není co kalibrovat) | `False` | `CalibrationBlockedError` |
| `BLOCKED` | < 2 rodiny, nebo rozptyl > 5 % | `False` | `CalibrationBlockedError` |

Implementace `usable_for_m3` (`scale_calibration.py:310-314`) vrací
`result.get("overall_status") == "VERIFIED"`, ne-mapy odmítá `False`;
`require_verified_for_m3` (`:317-327`) zvedá `CalibrationBlockedError`
s hláškou o vyžadovaném VERIFIED. Obojí kryto testy `TestM3Gate`.

## 6. Blok `float_decode_unverified` (`rbxm_parser.py:1372-1374`)

`assess_wheel_geometry` na konci **bezpodmínečně** přidává:

```python
block("float_decode_unverified: velikosti a stredy kol potvrzeny Studiem, "
      "ale tvary dilu, rotace a kalibrace studs/m nejsou overeny "
      "(kalibrace NOT IMPLEMENTED)")
```

Takže assess je v M2 vždy `BLOCKED`, i když je geometrie 4× `GEOMETRY_OK`.
Je to záměrná provenienční brzda (bez Studio ground-truth nelze floaty
prohlásit za ověřené), ne zapomenutá podmínka. Report ji propaguje
(`report_from_assess` → `assess_blocked_reasons`), viz test I-1.

## 7. Stub `calibrate_studs_per_meter` (`rbxm_parser.py:1378-1398`)

Vždy vrací `status NOT_IMPLEMENTED`, `studs_per_meter None`,
`inputs_ignored` flag; nikdy nevrací číslo. Stejný stav nese
`geometry.calibration` v `parse_bytes` a `calibration` v assess.
Žádná cesta z něj nevede číslo do M3.

## 8. Výsledek JeepTemplate 7.44 % (vlastní přepočet, ne citace)

Měření z reportu (studs): wheelbase 10.5227966, track_f 5.9906616,
track_r 5.9907227, pneu 2.7/2.7. Odhady `studs/m` proti referencím M1:

| param | odhad | status ref |
|---|---|---|
| wheelbase | 3.87010 | VERIFIED |
| track_f | 3.77960 | VERIFIED |
| track_r | 3.64843 | VERIFIED |
| tire_d_f | 3.93242 | ESTIMATED |
| tire_d_r | 3.84287 | ESTIMATED |

`spread = (3.93242-3.64843)/průměr*100 = 7.44 % > 5 %` ⇒ `BLOCKED`,
`estimates []`, nejistota `None` (žádná vymyšlená čísla, G-04).
Odpovídá testům `TestJeepTemplateGroundTruth` a `test_real_measurements_blocked`.

## 9. Přesná příčina, proč M2 nedává VERIFIED (tři nezávislé vrstvy)

Každá vrstva samostatně stačí k zablokování VERIFIED na reálných datech.
Pořadí je pořadím řetězce, ne důležitosti.

### P1 — Bezpodmínečný assess blok (záměrná brzda)

- Soubor+funkce: `src/Inspection/rbxm_parser.py :: assess_wheel_geometry`,
  ř. 1372–1374 (`block("float_decode_unverified …")`).
- Aktuální chování: assess vždy `BLOCKED` (1 důvod), i když 4 kola
  `GEOMETRY_OK`, 44 known, 0 unidentified.
- Očekávané chování pro VERIFIED: assess `OK` při konzistentní geometrii.
- Důkaz: `test_assess_blocked_float_unverified` (1 důvod, substring
  `float_decode_unverified`); integrace `815 instancí, 4× GEOMETRY_OK,
  celek BLOCKED`.
- Návrh opravy: podmínit blok výsledkem M3 ověření floatů
  (Studio ground-truth kalibračního dílu + ověřená kalibrace); do té doby
  ponechat. Vlastník pravidla: Agent A (parser).
- Opravitelné bez Studio dat: **NE** — odstranění bloku bez náhrady by byla
  obcházka provenience, ne oprava.
- Kategorie: **DESIGN LIMITATION** (vědomý požadavek M2, ne chyba kódu).

### P2 — Rozptyl 7.44 % proti mustangovským referencím (datový fakt)

- Soubor+funkce: `src/Inspection/scale_calibration.py :: calibrate`,
  ř. 267–273 (brána `CONSISTENCY_MAX_SPREAD_PCT = 5.0`).
- Aktuální chování: `BLOCKED`, `nekonzistentní měřítko: rozptyl 7.44 % > 5 %`.
- Očekávané chování pro VERIFIED: rozptyl ≤ 5 % (a pak viz P3).
- Důkaz: vlastní přepočet výše (3.648–3.932, spread 7.4447 %);
  `test_jeep_template_is_blocked` (substring `7.44`).
- Podstatný kontext: měřený model je **JeepTemplate**, reference jsou
  **Mustang GT 2024 EU** (jiné vozidlo) — rozchod/rozvor/pneu se nutně
  rozcházejí. Není to důkaz chyby dekódování floatů; geometrie kol samotná
  je vnitřně konzistentní (symetrický obdélník, sféricita 0.0).
- Návrh opravy: (a) doložit referenční rozměry **Jeepu** (MUSTANG-SOURCE-CHECK
  postupem) a kalibrovat Jeep→Jeep; nebo (b) kalibrovat Mustang až proti
  mustangovskému modelu. Bez jednoho z toho je BLOCKED správně.
- Opravitelné bez Studio dat: **ČÁSTEČNĚ** — referenční rozměry Jeepu lze
  dohledat z dokumentace (M1 postup), ale jejich **VERIFIED status**
  vyžaduje ověření zdroje člověkem; finální VERIFIED kalibrace stejně
  potřebuje P1/P3.
- Kategorie: **MISSING INPUT** (chybí referenční sada pro měřené vozidlo).

### P3 — ESTIMATED strop z pneu referencí (pravidlo statusu)

- Soubor+funkce: `src/Inspection/scale_calibration.py :: calibrate`,
  ř. 292–296 (`all_verified` + `VERIFIED_MAX_DEV_PCT = 2.0`).
- Aktuální chování: plná sada (VERIFIED rozvor/rozchody + ESTIMATED pneu)
  je i při konzistenci `ESTIMATED` a neprojde M3 bránou.
- Očekávané chování pro VERIFIED: všechny použité reference VERIFIED
  + `max |dev| ≤ 2 %`.
- Důkaz: `test_mixed_status_is_estimated`, `test_estimated_does_not_pass_gate`;
  `test_consistent_all_verified_is_verified` ukazuje, že cesta k VERIFIED
  existuje (pouze VERIFIED podmnožina, synteticky konzistentní).
- Návrh opravy: buď povýšit pneu reference na VERIFIED (tovární údaj pro
  dané vozidlo, ne nominální výpočet z designace ±5 mm), nebo kalibrovat
  jen na VERIFIED podmnožině (rozvor + 1× track = 2 rodiny, projde bránou
  rodin). I pak ale zůstává P1 (assess BLOCKED) a P2 (reálný rozptyl).
- Opravitelné bez Studio dat: **ČÁSTEČNĚ** — zúžení na VERIFIED podmnožinu
  je čistě kódová/datová změna volání, ale na reálných datech stejně
  narazí na P2; povýšení pneu na VERIFIED vyžaduje lidské ověření zdroje.
- Kategorie: **DESIGN LIMITATION** (pravidlo `pouze VERIFIED → VERIFIED`
  + M3 brána; zamýšlená přísnost).

## 10. Kategorizovaný seznam všech prověřených bodů

| # | Bod | Kategorie | Bez Studio dat opravitelné? |
|---|---|---|---|
| P1 | Bezpodmínečný `float_decode_unverified` blok v assess | DESIGN LIMITATION | NE |
| P2 | Rozptyl 7.44 %: Jeep měření vs Mustang reference | MISSING INPUT | ČÁSTEČNĚ (reference dohledatelné, VERIFIED status ne) |
| P3 | ESTIMATED strop (pneu reference) + brána `require_verified_for_m3` | DESIGN LIMITATION | ČÁSTEČNĚ (viz P3) |
| P4 | `calibrate_studs_per_meter` stub NOT_IMPLEMENTED | DESIGN LIMITATION | NE (je to M3 úkol definicí) |
| P5 | `build_inspection_report` umí `GEOMETRY_OK` na syntetických Studio číslech, na reálném řetězci dává `BLOCKED` propagací | NO ISSUE (konzistentní: report nesmí být zelený na BLOCKED datech) | — |
| P6 | Počítání rodin (track_f/track_r jedna rodina, pneu jedna rodina) | NO ISSUE (odpovídá příkazu, kryto testy `test_single_family_tracks_blocked`, `test_fewer_than_two…`) | — |
| P7 | Výpočet rozptylu / inverse-variance kombinace / determinismus | NO ISSUE (vlastní přepočet 7.4447 % souhlasí; testy determinismu procházejí) | — |
| P8 | Shape `Ball trusted=True` vs floaty `trusted=False` | NO ISSUE (křížově ověřeno: kola Ball, 104× Block + 1× Cylinder, 0 unread; `SHAPE-CROSS-CHECK.md`) | — |
| P9 | Skipped props (~800+ `unread`) | NO ISSUE (explicitní evidence, ne tichý průchod; test `test_skipped_props_are_explicit_not_silent`) | — |
| P10 | `coordinate_frame.verified_in_studio=true` + rozpor s návrhovou konvencí os | NO ISSUE s poznámkou: rámec je Studio-měřený (x=lateral, y=up, z=longitudinal); lidský úkol je potvrdit ho pro M3 kalibrační díl, viz P11 | — |
| P11 | Chybějící Studio ground-truth kalibračního dílu známé velikosti | HUMAN-STUDIO BLOCKER | NE (vyžaduje Studio + člověka) |
| P12 | Chybějící referenční sada Jeepu (M1 profil je mustangovský) | MISSING INPUT (+ lidské ověření zdroje) | ČÁSTEČNĚ |

## 11. CODE ISSUE — výsledek: **0**

Systematicky prověřeny: dekódování referentů/enum/float lane, CFrame,
PRNT/hierarchie, `_clusters`, `classify_candidate`/`detect_wheels`,
`build_inspection_report`/`report_from_assess`, `calibrate`/
`usable_for_m3`/`require_verified_for_m3`. Všechny M2 testy procházejí
(91 + 57 + 20 výše). Nenalezena žádná chyba kódu, která by bránila
VERIFIED — blokátory jsou datové a návrhově záměrné (P1–P4, P11–P12).
Seznam CODE ISSUE je proto prázdný; přesné lokace nejsou žádné k uvedení.

## 12. Co odblokuje VERIFIED (minimální cesta, pořadí závazné)

1. **Člověk/Studio (P11):** kalibrační díl známé velikosti odečtený ve Studiu
   → ověřené dekódování floatů → M3 ověřená kalibrace → podmíněný
   `float_decode_unverified` blok (P1) a realizace stubu (P4).
2. **Reference pro měřené vozidlo (P2):** referenční sada Jeepu (nebo
   mustangovský model) s lidsky ověřenými zdroji.
3. **Statusová čistota (P3):** všechny použité reference VERIFIED
   (nebo kalibrace jen na VERIFIED podmnožině) + `max |dev| ≤ 2 %`
   a rozptyl ≤ 5 %.
4. Pak `calibrate → VERIFIED` → `require_verified_for_m3` projde.

Bez bodu 1 nelze M2 VERIFIED dosáhnout žádnou úpravou kódu —
jakékoli „změkčení" bran by bylo obcházením M3 brány, ne opravou.
