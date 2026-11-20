# Agent E-PROVENANCE — analýza důkazní integrity (Fáze 1/7)
Vlastník: subagent E-PROVENANCE · Datum: 2026-11-20 · Větev: fix/normalization-evidence-integrity · read-only, stavy 94 ID neměněny

## Existující struktura
Všech 94 záznamů má `evidence={mustang_cil, zdroj_cile, puvod}` (validátor vyžaduje přítomnost klíčů; audit §2/R7 totéž). Příklady: VERIFIED `drive_config` (RWD + `drivetrain [1b]` + oficiální zdroj); ESTIMATED `wheel_radius` (výpočet + vstupy + metoda). **Verdikt: trojice je vhodnější než návrh ze zadání** — je v datech, kódu i auditu; nemigruje se, jen zpřísňuje.

## Mezera `je_dukaze` (před opravou)
`not in PRAZDNE and not startswith("UNKNOWN")` → projde `"xxx"`, `"viz audit"`, `"odhad"` jako důkaz; nekontroluje hodnotu, jednotku, zdroj, lokaci, původ.

## Strojová pravidla (předáno Agentu E, implementováno)
- `je_hodnota`: číslice NEBO velkopísmenný enum kód (`RWD` projde; `xxx`/`odhad`/`n/a (RWD)` ne).
- `ma_lokator`: `§`/`#`/`` ` ``/`[..]` v `zdroj_cile` (`audit §6`, `` `drivetrain` ([1b]) `` projdou; `viz audit` ne).
- VERIFIED vyžaduje konkrétní `mustang_cil` + zdroj s lokátorem + specifický `puvod` (len≥6); jinak `VERIFIED-bez-evidence` (testy 38–41).
- ESTIMATED: placeholder `puvod` → `ESTIMATED-bez-původu` (42); placeholder `zdroj_cile` → `ESTIMATED-bez-zdroje` (43, nové); holé `odhad` bez metody → `ESTIMATED-k-revizi` PENDING, ne tichý PASS (44).
- UNKNOWN/PENDING s konkrétním cílem → `ruční-review` PENDING (45, existující).
- Vědomá odchylka od návrhu testu PROVENANCE-5: holé `odhad` u ESTIMATED s nekonkrétním cílem je PENDING-k-revizi, ne FAIL — 4 reálné záznamy (`diff_preload_f`, `front_diff_coast`, `front_diff_power`, `torque_vector`) mají právě `puvod="odhad"`; FAIL by zlomil pristine strom. Není to tichý PASS: každý takový záznam je nově jmenovitě flagován.
