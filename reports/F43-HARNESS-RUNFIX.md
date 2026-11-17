# F4.3 – Harness RUNFIX pokus T03 (Agent HS, 2026-11-17)

**Vlastník:** Agent HS. Větev `f43-live-tune-reconciliation` (pracovní; `f43` v repu neexistuje).
Studio Play Solo (`17ce64ee-a452-4e5c-b95d-45e66be3b314`, user-controlled).
**Verdikt: FAIL** — STOP dle pravidel (klient neřídí), žádná dráha neměřena, vše smazáno.

## Ověřené předpoklady (prošly)

- Freshness gate: `IsMutable('BrakeBias') == true`, `GetMutableKeys() == 82`, `DenyReason('Bias')` = PREJMENOVANO → BrakeBias.
- Bridge `ServerStorage.AutoEngineerBridge` existuje; inbox 0, outbox 0 (mechanismus volný).
- `SpawnLocation` existuje; hráč `Adalik1219` má postavu + Humanoid, nesezen.
- `AE_DriverCommands` RemoteEvent existuje na klientovi (vytváří TestClient); ze serveru **není viditelný**
  (client-created, nereplikuje se nahoru) — server na něj nemá handle.
- Trať: `StraightLane` x 0→1500, `StartLine` x=2, `BrakeLine` x=3000, směr jízdy +X; čelo vozu = +LookVector.

## Provedené kroky (běh 1, bias 0.6)

1. `CloneVehicle('f43_run')` → `Jeep_f43_run` → přejmenováno `AE_VehicleSlot` (findVehicleSlot OK).
   `WriteTune(BrakeBias, 0.6)` + `ReadTune` = 0.6. Serverový `Initialize` postavil podvozek
   (4× `#BV`, `Values`, GUI do PlayerGui po usednutí).
2. Klidové usazení na StartLine (CFrame.lookAt +X, bez pádu): up +Y≈0.996, LV≈+X.
   `DriveSeat.AssemblyLinearVelocity = (100,0,0)` jako startovní podmínka (decay vlivem odporu).
3. Usednutí: `seat:Sit(humanoid)` OK (occupant potvrzen), `IsOn=true` (klíček) OK.

## STOP — přesná diagnóza (krok: jízda klienta; důkaz: měřeno)

Klient vůz **neřídí** — tři nezávislé důkazy z živé session:

- (a) `seat.Throttle=1` po 4 s → rychlost **0**, `Values/RPM=0` (vstupní kanál TestClientu [P] nefunguje).
- (b) GUI `Values/Throttle=1` (+odbrzděno `PBrake=false`) po 3–5 s → rychlost **0**, RPM zamrzlé na **950** (idle),
  `Gear=0`, `PBrake` se vrací na **true**, `#BV` motory zamrzlé (`MotorMaxTorque=5000`, `AngularVelocity=0`).
  Správný kanál je `Controls`/`Values` (RUNTIME-API §2), ne seat — ani ten nefunguje.
- (c) Konzole: `Drive`, `Initialize`, `Simulated`, `Controls_AC6`, `Ignition`, zvukové skripty —
  opakovaně `Cannot start ... (lacking capability RunClientScript/RunServerScript)`.
  Vlastní kontrolní `Script` (HS_Probe) běží (`hs-probe-ok` v konzoli) → sandbox MCP je v pořádku,
  capability chybí **skriptům šablony** (importovaný .rbxm), ne mým příkazům.

Bonus-nález (měřeno, blokuje smysl bias-porovnání i po opravě řízení):
server `ReadTune(BrakeBias)` = **0.9** vs klient `require(Tune).BrakeBias` = **0.6**.
`WriteTune` mutuje jen serverovou VM tabulku; klientský `Drive` čte klientskou kopii zdroje.
Bez změny kódu/šablony se bias fyzikálně **nemůže projevit**.

Harness-gap (potvrzeno): serverový `TestHarness` pálí `AERunBrief`, `TestClient` poslouchá jen
`AE_DriverCommands` — inbox-běh klienta nikdy nespustí, ani kdyby skripty běžely.

## Cleanup (ověřeno)

`AE_VehicleSlot` destrukce = true, `HS_Probe` smazán, žádné `VehicleSeat` ve Workspace,
inbox 0 / outbox 0, šablona `JeepTemplate` nedotčena. Žádný běh do outboxu nezapsán (žádná data).

## Doporučení

1. Šablonu/place opravit mimo runtime (skriptům chybí capabilities — znovu uložit/importovat
   `JeepTemplate` důvěryhodnou cestou), restart Play Solo (ovládá uživatel).
2. Sjednotit `AERunBrief` → `AE_DriverCommands` (kódová změna, vlastník harnessu).
3. Rozhodnout kanál vstupů (`Controls`/`Values` vs seat) + obsluhu `PBrake`/`Gear`/`IsOn` v TestClientu.
4. Vyřešit propagaci Tune na klienta (jinak bias zůstane SIM-only).
Do té doby: T03 RUN-měření nelze provést; opakování pokusu bez těchto oprav nemá smysl.
