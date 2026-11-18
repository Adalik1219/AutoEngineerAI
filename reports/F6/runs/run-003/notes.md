# run-003 — kampaň b06 (první platná T03 kampaň projektu)

Brief `cfg_f6_b06` (BrakeBias 0.6 = default Tune), T03-only, inbox přes
`AESubmitConfig` (JSON string — POZOR: předání tabulky místo JSON stringu
končí warningem `expects a string, but table was passed` a brief se nespustí;
přitom vůz se může hýbat z předchozích manuálních testů — ověřit outbox!).

Průběh: 3/3 `completed`, 0 errors, stopped=true, vzdálenosti
153.0 / 151.9 / 153.0 (delta 0.73 %, repeatability_ok=true).
První vzorky v0≈100, brzdná rampa t/0.15→1, zastavení ~3.2 s.
Šampion: server-autoritativní brzda (ApplyServerBrake) — klientský Drive
sice běží (mosty V1/V2, zrcadla), ale jeho motorové zápisy se na
serverem vlastněných dílech neaplikují (důkaz: server 200 vs klient 0).

Soubory: 3× RUN (plná 60Hz telemetrie) + SUMMARY. Surová data = RUN JSONy.
