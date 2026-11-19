# REMEDIATION-WAVE-FINAL-REPORT — opravná vlna M2

Větev `feat/m2-m3-geometry`. PR #2 nemergován (rozhoduje vlastník).
Pravidla: M3 NEOTEVŘENA · originál RBXM nedotčen · PENDING≠PASS · CODE≠RUNTIME.

## 1. Identifikace verze

- Výchozí SHA: `4cad304d80e897a2ab3c92a14442501614965789`
- Finální SHA: viz commit této vlny níže (koordinátor doplní po commitu)
- Větev: `feat/m2-m3-geometry` · Datum: 2026-11-19
- Vstupní RBXM: `assets/chassis-original/chasis-work-copy.rbxm`,
  SHA-256 `dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf`
  (před/po shodný, pouze čtení).

## 2. Agent A — klasifikace kol

- `src/Inspection/wheel_detect.py`: 4-tier + `CHASSIS_PART_ALLOWLIST` (11 názvů,
  jen uvnitř Wheels); `known_non_wheels` evidováno, neblokuje; UNKNOWN/INVALID → BLOCKED.
- `tests/test_m2_wheel_detect.py`: 18 povinných testů (důvody), celkem 53 OK.
- Reálná kopie: 4× VALID_WHEEL + 44× KNOWN_NON_WHEEL, 0 unidentified.
- Report: `reports/M2/WHEEL-GEOMETRY-REPORT.md`.

## 3. Agent B — kalibrace a M3 brána

- `src/Inspection/scale_calibration.py` beze změny (brána VERIFIED-only potvrzena);
  `tests/test_m2_scale_calibration.py`: 18 → 31 testů, PASS.
- Nález: M3 proposal pouštěl ESTIMATED → opraveno Agentem E na `== VERIFIED`.
- JeepTemplate: rozptyl 7,44 % → BLOCKED (správně, jiné vozidlo).
- Report: `reports/M2/SCALE-CALIBRATION-REPORT.md`.

## 4. Agent C — integrace

- `tests/test_m2_integration.py` (20 testů) + `reports/M2-M3/INTEGRATION-TEST-REPORT.md`.
- Nález I-1 (report zelený při BLOCKED assess) opraven propagací BLOCKED.
- Plná sada: 372 běhů / 368 PASS / 0 FAIL / 0 ERROR / 4 PENDING (pre-existing).
- `validate_contracts`: 24/0 (kryje contracts + vehicle-data; M2 freeze kryjí testy klíčů).
- G-01–G-07, G-10 ověřeny (tabulka v reportu).

## 5. Agent D — QA

- `reports/M2-M3/FINAL-INDEPENDENT-QA.md`: 15 sond + I-1, vše dle očekávání.
- Verdikt: M2 CONDITIONAL PASS; brána M3 NEOTEVŘENA (podmínky splněny:
  N1 opravena, reason-text aktualizován, re-běhy zelené, strom čistý).

## 6. CI

- URL + joby: doplní koordinátor po pushi finálního commitu (povinné dle §7).
- Lokálně: 372/368/0/4 sériově, reprodukovatelně.

## 7. Globální akceptace (G-01–G-07, G-10)

| Brána | Stav |
|---|---|
| G-01 originál nedotčen | PASS (hash shodný) |
| G-02 jednotky | PASS (studs + SI v kontraktech) |
| G-03 zdroje/cíle | PASS (profil VERIFIED + CHYBÍ) |
| G-04 UNKNOWN≠odhad | PASS |
| G-05 PENDING≠PASS | PASS (4 zdůvodněny) |
| G-06 CODE≠RUNTIME | PASS |
| G-07 simulace≠runtime | PASS (žádná simulace nevydávána) |
| G-10 reprodukovatelnost | PASS (determinismus testován) |

## 8. Konečné rozhodnutí

- **M2: CONDITIONAL PASS** (kalibrace konkrétního modelu BLOCKED — očekávané, ne defekt).
- **M3: BLOCKED (NEOTEVŘENA)** — chybí VERIFIED měřítko; otevření jen s validním měřítkem + splněnými branami §10.3.
- Další samostatná vlna možná: identifikace referenčního vozidla JeepTemplate + kalibrace vůči jeho továrním rozměrům (vyžaduje schválení).

## 6b. CI finálního commitu (doplněno koordinátorem)

- Commit: `a94e4a2` · run `44611902993` · 4/4 success (3.11–3.14).
- Předchozí runy: vlna 34a4994 zelená lokálně 372/368/0/4 (CI běží jen na push;
  mezilehlé commity bez push nebyly testovány v CI — lokální běhy doloženy v reportech).
