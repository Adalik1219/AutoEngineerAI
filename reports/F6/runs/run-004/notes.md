# run-004 — kampaň b09 (BrakeBias 0.9, ve F5 nikdy neběžela)

Stejný slot přeladěn `WriteTune(BrakeBias, 0.9)` za běhu (server-brzda čte
Tune live, takže účinné okamžitě; klientský Drive by potřeboval rebuild).

Průběh: 3/3 `completed`, 0 errors, stopped=true, vzdálenosti
152.0 / 144.6 / 153.6. SUMMARY `failed` POUZE branou
`rozptyl_drahy_nad_5_pct` (delta 5.99 %): r2 outlier (peak_decel 52
proti 23/30, jinak zdravý průběh — yaw 0.15, lat 0.86, v0 99.98).
Kandidáti: fps-hitch (moment 60/fps) nebo settle-rozptyl; k rozhodnutí
je potřeba větší n (mimo mandát F6: žádná další kampaň T03).

Verdikt běhu: jízdy platné, statistická brána nesplněna jedním outlierem.
Neoznačeno za PASS; důvod přesně uveden (protokol F6).
