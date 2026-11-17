# F4.3 – Závěrečné QA (Agent Q, 2026-11-17)

**Vlastník:** Agent Q. Větev `f43-live-tune-reconciliation`. Studio Play Solo
(`17ce64ee-a452-4e5c-b95d-45e66be3b314`, user-controlled) — pouze čtení
(`search_game_tree` + `execute_luau` po malých dávkách). Žádný spawn, žádný zápis,
žádný `start_stop_play`. **Vlastněný soubor: pouze tento report.**

## Verdikt: PODMÍNĚNÉ ANO k mergi

**Merge ANO** pro body 1–9 + 12 (katalog, mapování, testy, originál).
**Body 10–11 (RUN důkaz brzdné dráhy) = PENDING** — zůstávají otevřené do opakování
po opravě harnessu. RUN tvrzení Agenta M (`56.53 vs 40.44`) do merge-neblokuje,
ale nesmí se vydávat za uzavřený T03 RUN-důkaz.

## 1. Spot-check 10 klíčů: katalog vs live šablona (PASS)

Read-only `execute_luau` (Server) proti
`ServerStorage.VehicleTemplates.JeepTemplate["A-Chassis Tune"]`, 2 dávky po 5.
Šablona nedotčena (kořen 7 dětí: Misc, Wheels, Body, A-Chassis Tune, DriveSeat,
JeepBodyVisual, CollisionParts — ověřeno `search_game_tree`).

| live klíč | live hodnota (typ) | katalog `id` → `tune_key` | shoda |
|---|---|---|---|
| `BrakeBias` | 0.6 (number) | `brake_bias_front` → `BrakeBias` | OK |
| `PBrakeBias` | 0 (number) | `pbrake_bias` → `PBrakeBias` | OK |
| `FSusDamping` | 500 (number) | `damper_f` → `FSusDamping` | OK |
| `RSusDamping` | 500 (number) | `damper_r` → `RSusDamping` | OK |
| `FSusStiffness` | 20000 (number) | `sus_stiffness_f` → `FSusStiffness` | OK |
| `RSusStiffness` | 20000 (number) | `sus_stiffness_r` → `RSusStiffness` | OK |
| `FDiffPreload` | 20 (number) | `diff_preload_f` → `FDiffPreload` | OK |
| `RDiffPreload` | 20 (number) | `diff_preload_r` → `RDiffPreload` | OK |
| `FDiffSlipThres` | 50 (number) | `slip_thresh_f` → `FDiffSlipThres` (UNKNOWN, PENDING) | OK (klíč+typ; hodnota audit-nepopsána, poctivě PENDING) |
| `RDiffSlipThres` | 80 (number) | `slip_thresh_r` → `RDiffSlipThres` (UNKNOWN, PENDING) | OK (dtto) |

**10/10 PASS.** F/R varianty i oba UNKNOWN klíče existují v live Tune se shodným
typem; katalogová `tune_key` mapování sedí s `reports/F43-LIVE-DIFF.md` §2.

## 2. Spot-check min/max zdroj (PASS)

Z 138 záznamů má `min`+`max` právě 9 — **všech 9 má auditní zdroj**, žádný
vymyšlený limit. Namátka 5:

| `id` | min–max | zdroj |
|---|---|---|
| `brake_bias_front` | 0–1 | A-CHASSIS-AUDIT §12; Drive; Tune + live |
| `curve_mult` | 0–1 | A-CHASSIS-AUDIT §5; Drive; Tune |
| `diff_preload_f` | 0–100 | A-CHASSIS-AUDIT §7; Drive; Tune + live |
| `torque_vector` | −1–1 | A-CHASSIS-AUDIT §7; Drive; Tune |
| `weight_dist_pct` | 0–100 | A-CHASSIS-AUDIT §11; Initialize; Tune |

**5/5 PASS.** Zásada „žádné vymyšlené min/max" (LIVE-DIFF §3) dodržena.

## 3. H suite + validátory znovu spuštěny (PASS)

- `python tests/run_all.py`: **běhů 148, PASS 144, FAIL 0, ERROR 0, PENDING 4** →
  `VYSLEDEK: PASS (s 4 PENDING)`. PENDING totožné s baseline Agenta HR
  (Studio-měření, schema-conformance Fáze 5, 2× regresní baseline Fáze 9/10).
- `loader.py --selftest`: exit 0, `SELFTEST OK` (138 záznamů, 82/14/2/3/37, 43 pending-studio).
- `achassis_v1.py`: exit 0, `SELFTEST OK`.
- `git status --short`: **čistý** (QA nic neměnilo mimo tento report).

**PASS**, včetně bodu 9: `test_f43_reconciliation.py` (13 asercí proti tichému
no-op) je součástí suity a prochází; F4-C efekt-test
(`bias 0.70→0.62`, diff ~0.81 m, 5/5 shoda, determinismus 196 řádků) prochází.

## 4. Posouzení měření Agenta M (PENDING, ne PASS/FAIL)

Čísla v `reports/F43-RUNTIME-MEASURE.md`: baseline 56.53 vs bias-0.9 40.44,
rozdíl 16.09 studs, readback 0.6/0.9, cleanup doložen (klony zničeny,
inbox/outbox 0/0, šablona 7 dětí / Tune 4 děti). Dnes živě re-verifikováno:
**Workspace bez `Jeep_*`/`AE_*`, inbox 0 / outbox 0** — pořádek sedí.

Směr efektu (vyšší přední bias → kratší dráha) je fyzikálně věrohodný a čísla
jsou vnitřně konzistentní. ALE metoda není T03 souborového harnessu:

- měřeno přímou aktuací `#BV` HingeConstraints, nikoli klientským `Drive`
  (bez ABS, bez rampy, nikdo nesedí) — Agent M to poctivě uvádí v Limitech;
- 1 opakování na variantu (T03 chce 3), rozptyl netestován;
- konflikt s Agentem S (FAIL 0 vs 0: `WriteTune` se nepropaguje do postavených
  runtime instancí) a Agentem HS (klient vůz neřídí, capabilities) není rozporován —
  M obchází oba problémy jinou cestou (server-side build + přímá aktuace),
  takže jeho čísla S/HS nevyvracejí, ale ani T03 RUN neuzavírají.

**Verdikt bodu: PENDING.** Čísla přijata jako měřená, ne odhad; RUN-důkaz biasu
vyžaduje opakování opraveným harnessem (počáteční rychlost, vstupní kanál,
`brake_distance` v telemetrii, 3 opakování).

## 5. Originál nedotčen (PASS)

- `sha256sum C:/Users/adamr/Downloads/chasis.rbxm` =
  `dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf` —
  **shoduje se** se zadáním.
- Simulator status: žádné pracovní klony, inbox/outbox prázdné (viz §4),
  šablona netknuta (7 dětí kořene).

## 6. Verdikt 12 bodů

| Body | Předmět | Verdikt |
|---|---|---|
| 1–8 | katalog / mapování / testy (138 záznamů, 19 fantomů, diff 167 klíčů, H suite) | **PASS** (§1–§3) |
| 9 | testy proti no-op (`test_f43_reconciliation`, F4-C efekt) | **PASS** (§3) |
| 10–11 | runtime změna + porovnání dráhy (M: 56.53 vs 40.44) | **PENDING** (§4) |
| 12 | originál nedotčen (sha + Simulator prázdný) | **PASS** (§5) |

## 7. Doporučení mergi

- **ANO** pro: `parameters.json` (138), `loader.py`, `achassis_v1.py`,
  `VehicleManager.lua` (RepairStructure + MUTABLE 82), testy vč.
  `test_f43_reconciliation.py`, reporty R/S/HS/HR/M a tento QA report.
- **NEuzavírat** RUN-důkaz T03: body 10–11 zůstávají PENDING; další krok =
  oprava harnessu dle S §Doporučení + HS §Doporučení (rychlost 100, vstupní
  kanál `Controls`/`Values`, propagace Tune na klienta, `brake_distance`
  v telemetrii), pak 3× opakování.
- `CloneVehicle` nově neparentuje (kontraktová změna HR §2) — před mergem
  potvrdit s vlastníkem `docs/RUNTIME-API.md`.
- 50 live klíčů `CHYBÍ_V_KATALOGU` je mimo rozsah F4.3 vlny 1 (patří A/B),
  neblokuje merge, evidovat do kalibračního backlogu.
