# F7.1 Rojo incident (2026-11-18) — connection interruption

## Zjisteni (evidence, ne dohady)
- Studio instance `17ce64ee…` (Place1) bezi kontinualne cely den — stejne ID pred i po
  incidentu => Studio NEBYLO restartovano, zadny prepinac mista/projektu.
- Rojo server (v7.7.1, projekt AutoEngineerTestGame, :34872): proces start 15:49:44
  (PID zmena zaznamenana koordin. pozorováním v 15:49). Kdo ho restartoval, neni
  z dostupnych logu zjistitelne — koordinátor ani jeho subagenti zadny restart
  neprovedli (prikazy toho dne: cteni, curl/ps/netstat, sleep; zadny rojo serve/stop).
- Po 15:49 sync netekl (prazdne grepy, probe-komentar za 45 s ve Studiu neviditelny),
  ackoli server bezel — typicke pro rozpojeny plugin (znama nekompatibilita
  server 7.7.1 vs plugin 7.2.1).
- Uzivatel manualne reconnectnul (~16:20) => sync obnoven, overeno ctenim radku
  497-498 (F7.1-8 kod) a naslednym T01 behu (3/3 RUN v outboxu).
- Nové soubory (ServerDrive.lua) behem vypadku nedotekly vubec; edity existujicich
  souboru po reconnectu ano — proto inline ServerDrive do ScenarioRunner (commit F7.1-6).

## Marker test (po reconnectu)
- `F7-ROJO-MARKER-1625` (komentar na konci ScenarioRunner): ve Studiu viditelny do
  ~35 s (script_read radek 1711; script_grep vratil falesny no-match — znamy lag indexu).
- Po revertu: Studio tail konci 1709, pracovni strom `git status` cisty.
- Zadna nesouvisejici zmena ve Studiu nezaznamenana. Verdikt: PASS.

## Zaver
| Polozka | Vysledek |
|---|---|
| Studio restart | NOT CONFIRMED (stejne instance ID) |
| Rojo server restart (15:49) | CONFIRMED (proces start 15:49:44), iniciator UNKNOWN |
| Rojo disconnection | CONFIRMED (sync netekl pri bezicim serveru) |
| Iniciacni akce | UNKNOWN (koordinator: zadny restart/disconnect neprovedl) |
| Root cause | UNKNOWN (kandidati: pad/restart serve-procesu v 15:49; plugin 7.2.1 vs server 7.7.1; externi zasah — bez dukazu nerozlisitelne) |
| Aktualni spojeni | CONNECTED (ESTABLISHED obe strany, marker PASS) |
| Marker sync test | PASS |
| Preventivni opatreni | (1) pred kazdym Play overit sync ctenim ve Studiu; (2) nove soubory overit ve Studiu do 60 s, jinak inline; (3) zaden restart Studia/Rojo bez evidovaneho duvodu; (4) sjednotit verze plugin/server na 7.7.x (mimo muj zapis — vyzaduje akci uzivatele ve Studiu) |

## Operacni protokol (koordinator + Studio operator: jedna osoba)
- Zivou Studio session ovlada pouze koordinator; subagenti read-only analyza.
- Zadny restart/reconnect/prepnuti projektu bez: co je rozbite + dukaz + navrh + dopad.
- Po kazde reconnectu: marker test + zaznam.
