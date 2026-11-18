# F5-CLOSURE — Runtime Stabilization: verdikt

**Verdikt: F5 NEPROCHÁZÍ (BLOCKED aparátorem). Kampan 3+3 (0/6 platných).**
H suite 155/0/4, lint + build zelené. Všechna kritéria 1–8, 10 viz níže; 9 FAIL.

## Mapování F5 1–10

| # | Požadavek | Verdikt | Důkaz |
|---|-----------|---------|-------|
| 1 | Arbitrace brzdy | PASS | server-autoritativní můstek, H zelená |
| 2 | Init vozidla bez Source | PASS (slot) / FAIL (Drive-bind, viz níže) | RepairStructure verify-only; Drive Car.Value stale |
| 3 | SUMMARY ze stejných vzorků | PASS | C-1 fix, test_summary_aggregate zelený na f44 |
| 4 | Start 100±1 | PASS (gate) / PENDING (entry hold — fyzika) | gate funguje; rychlost se neudrží (E3: kola zamčená) |
| 5 | ABS read-only | PASS | kanál + config čtení |
| 6 | roll_deg kanál | PASS | vzorky + schéma + regrese |
| 7 | Cleanup | PASS | slot/Jeep/bridge 0 po bězích |
| 8 | H suite + regrese | PASS | 159=155/0/4; test_f44_regression 11 OK |
| 9 | Kampaň 3+3, Δ>3σ, repeat ≤5 % | FAIL (0/6, vše void) | 5 pokusů (E, E-retry, E-final, E-final-II, E2), 0 platných |
| 10 | Uzávěr | TENTO DOKUMENT | — |

## Proč kampaň neprošla (E3, měřením potvrzeno)

1. **Zablokovaný rotační DOF kol (primární):** coast 100→0 za ~0.7 s (dx=37.4, reálný pohyb) při nulové brzdě; kola W74→2 do 0.1 s; přímý `#AV=2000/30` vozem nepohne (dx=0.03). Ve vzduchu drží 100.0 (není to srážka ani weld). Podezřelý dual-hinge pár `#AV`+`#BV` se zrcadlenými attachment-framy (overconstraint-bind vs. solver nerozlišeno). Q2/Q3/Q4 v `reports/F5-QA.md` sekce H+I.
2. **Mrtvý klientský Drive (sekundární):** `Car.Value` ukazuje na zničený model (`Parent=nil`), `car.DriveSeat` padá každý frame (Drive:359, Aerodynamics:16). Atributový můstek nemá živého konzumenta. Příčina staleness: Interface GUI v PlayerGui se klonuje jednou (ne za běh).
3. M3-čísla (56/40) jsou zpětně NEDŮVĚRYHODNÁ: pravděpodobně stale-repliky (poučení S1); E3 coast 37.4 je jediná věrohodná baseline.

## Co F5 přineslo (sloučeno v main, H zelená)

A (arbitrace) + B (no-Source verify-only; pokusem prokázáno: neměněný klon staví, cap-errors byly zastaralé) + C (SUMMARY z kept, roll_deg, dynamické f*/) + D (start-verify, ABS read-only) + FX (SUMMARY kept, re-verify) + FX2 (capability-safe bridge, nulování vstupů, settle-go, roll pre-check) + FX3 (reclaim ownership, omega, slot AE_VehicleSlot).

## Předání pro F6 (pořadí dle E3)

1. Rebind `Car.Value` na čerstvý slot za každý běh (čistá Instance-operace, funguje in-game) + nil-guard (vyžaduje Source → MCP operator-step nebo repo-kopie Drive).
2. H1: dual-hinge audit (`#AV`+`#BV` attachment-framy), `#BV` default; cíl: volně se točící kola.
3. Spin-hold gate do `SpawnT03Verified` (kola se točí před brzdou, jinak void).
4. Smoke (1 coast-beh, držení 100) → teprve pak 3+3.

Vstupní data: `reports/F5-QA.md` (sekce E-final-II, H0–H9, I), `reports/F44-T03-FINAL.md`, `reports/F44-T03-RUNS.md`.
Leží na main: f2a3eaf. Žádná f55 data (precedent: bez platných běhů se adresář nevytváří).
