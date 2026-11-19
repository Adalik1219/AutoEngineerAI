# Hybrid Workflow – end-to-end proces člověk + stroj

**Stav:** návrh v1 (ke schválení).
**Vazba:** `docs/IMPLEMENTATION_ROADMAP.md` (M9), `docs/ACCEPTANCE_CRITERIA.md` (brány),
`docs/ROBLOX-RUNTIME.md` (prostředí Studia).

---

## 1. Role

| Krok | Provádí | Artefakt |
|---|---|---|
| 1. Načti cílový profil Mustangu | stroj (M1) | `vehicle_profile.json` |
| 2. Analyzuj vstupní RBXM (read-only) | stroj (M2) | `inspection_report.json` + měřítko |
| 3. Vypočti geometrické rozdíly | stroj (M3) | `geometry_diff.json` |
| 4. Vypočti fyzikální cíle | stroj (M4) | `physics_target.json` |
| 5. Namapuj cíle na A-Chassis Tune | stroj (M5) | `achassis_changes.json` (s důvody) |
| 6. Vygeneruj konfiguraci + rollback | stroj (M6) | `vehicle-data/runs/<vozidlo>/iteration_NNN/` |
| 7. Vygeneruj testovací protokol | stroj (M7) | `test_protocol.md` + formulář měření |
| 8. **Aplikuj konfiguraci ve Studiu** | **člověk** | upravená pracovní kopie |
| 9. **Proveď předepsané jízdy** | **člověk** | vyplněný formulář + telemetrie |
| 10. Vyhodnoť odchylky a navrhni dál | stroj (M8) | `evaluation.json` + doporučení |
| 11. Rozhodni: další iterace / rollback / hotovo | člověk + stroj (M9) | `manifest.json`, historie |

## 2. Pravidla iterace

1. Jedna iterace mění **pouze jednu logickou skupinu parametrů** (geometrie, nebo brzdy, nebo převodovka…).
2. Před během: záloha pracovní kopie. Po neúspěchu: revert s ověřeným nulovým diffem.
3. Originální `chasis.rbxm` / `JeepTemplate.rbxm` se nikdy nepřepisují; generátor zachovává hash vstupu.
4. Žádná automatická aplikace změn do originálu — návrh (M5/M6) a aplikace (člověk) jsou oddělené.
5. Bez runtime testu ve Studiu žádný `RUNTIME-VERIFIED` a žádná další iterace stavící na neověřeném předpokladu.

## 3. První testovací sada Mustangu (M7)

| ID | Test | Opakování |
|---|---|---|
| T-GEO-01 | Rozvor a rozchody (pásmo ve Studiu) | 1 |
| T-GEO-02 | Průměr a pozice kol | 1 |
| T-ACC-01 | Akcelerace 0–100 km/h | 5 |
| T-BRK-01 | Brzdění 100–0 km/h | 5 |
| T-STEER-01 / T-STEER-02 | Zatáčení vlevo / vpravo | 3 + 3 |
| T-REL-01 | Uvolnění plynu (dojezd / dead-man) | 3 |
| T-STAB-01 | Jízda rovně (stabilita) | 3 |

Počty opakování jsou navržené testovací minimum, nikoli hodnoty Fordu. Podmínky, tolerance
a očekávané hodnoty generuje M7 do `test_protocol.md`; výsledky se vracejí ve strukturovaném
JSON (`result_schema`), který validuje M8.

## 4. Stavový model iterace

`PLANNED → CONFIGURED → TESTED → EVALUATED → (ACCEPTED | ROLLED-BACK | NEXT-ITERATION)`.
Historii všech iterací drží M9 (`workflow_state.json`); rollback se umí vrátit na libovolnou
předchozí iteraci.
