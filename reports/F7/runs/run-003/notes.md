# run-003 — T01B 3/3 + Q4 manual (2026-11-18)

## Kampan (cfg_f71_t01j, no-sit, reuse slot)
- 3/3 `completed`, reason `finish_gate_crossed`, 0 chyb, noav=0.
- Gate (x>=2500): t=25.42/21.92/21.89, v=196.1/197.9/197.6 @ x=2512/2506/2511.
- Stop: x=3045.8/3048.9/3052.9 (odstup od zdi ~750), brzda 541.9/539.3/540.7 (profil: z ~197).
- draha/int_vdt = 1.000/1.000/1.000; 0 skoku (teleport-brana); max|z| 0.69/0.76/1.36.
- r1 = warm-up (t_0_60 8.1 vs 4.67/4.64); r2/r3 opakovatelnost <0.3 %.
- RAW: p1..p7 po 150000 B + tail (6108/73121/86716), sestaveno + JSON-validovano
  (1970/1755/1757 vzorku = manifest). catch-up burst (dt=0: 501/420/124) = artefakt
  Heartbeat, integralni metriky nedotceny.
- Rep-2 anomalie (kampane b/c) se NEOPAKOVALA: passenger/weld je PODEZRELA
  pricina (korelace: no-sit kampan cista), NENI prokazany root cause.

## Q4 manual (AEDriveCmd -> ServerDrive, unseated, server vlastni vse)
- Q4.1 plyn PASS: mid-stream (0.6) thA=0.6, #AVtq=143, v=8.2 (server-owned).
  Cestou objeveno: diskretni povel = 1 tick -> nasazen manual loop (ab03ce8)
  + dead-man pres ClearDriveInputs (c755522).
- Q4.2 release PASS: dead-man 1.0s -> motor off, v 8.2->0, zadny dobeh.
- Q4.3 brzda PASS: v 11.3->0.0 na 3 coulech (brzda drzi az do dead-man).
- Q4.4 steer BLOKOVAN: dyaw 0.004/3s; client-Drive v session nebezi
  (capability-denial) + server-ownership zahazuje gyro; chyba server-side
  steer-akutator (F7.2).
- Validace: clamp PASS (5->1, -2->0, 9->1); stale-seq CODE-VERIFIED,
  runtime dup/stale test PENDING. Occupant: PENDING (vse unseated, validace
  neimplementovana). Rozsah: overen ServerDrive harness, NE original A-Chassis
  runtime (v teto session nebezi; PENDING/BLOCKED).
- Ztrata vozu pri testu (pouze Q4 rig, ne T01B dukaz): poddimenzovane brzdne
  okno z v=190 + dead-man uvolnil brzdu -> sjezd do voidu. Lekce zapsana.

## Verdikt
T01B PASS. Q4 parcialni PASS (vse krome steer). F7.1 OPEN do steer-rozhodnuti (F7.2 scope).
