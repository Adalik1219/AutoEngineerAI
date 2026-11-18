-- ScenarioRunner: stavovy automat scenare IDLE -> SPAWN -> RUNNING -> COMPLETED / FAILED.
-- Ridic je deterministicky replay (plyn/brzda/volant jako funkce casu + def. rampy).
--
-- REPORT BRZDA/ABS (Agent H1, overeno live ctenim Drive zdroje v Play session,
-- Server datamodel, pouze cteni; zadny spawn, zadny zapis):
--   Zdroj: ...VehicleTemplates.JeepTemplate."A-Chassis Tune"."A-Chassis Interface".Drive
--   (LocalScript, 1178 radku).
--   OVERENA FAKTA:
--   (a) Brzda je SAMOSTATNY vstup 0..1 (NENI zaporny Throttle). Retezec:
--       _IBrake (klavesa Brake/Brake2 nebo gamepad osa, 0/1) -> vyhlazeni
--       _InBrake rampami _Tune.BrakeAccel (nabeh) / _Tune.BrakeDecel (dobeh)
--       -> podle smeru jizdy _GBrake -> `local brake = _GBrake`.
--   (b) Brzdny moment na kolo: MotorMaxTorque =
--       (F/RBrakeForce * (60/fps) * brake * tqABS) + EBrakeForce-slozka +
--       PBrakeForce-slozka; FBrakeForce/RBrakeForce = BrakeForce*BrakeBias
--       resp. BrakeForce*(1-BrakeBias). Live Tune: BrakeForce=2500,
--       BrakeBias=0.6, BrakeAccel=0.2, BrakeDecel=0.5.
--   (c) ABS: `_ABS = _Tune.ABSEnabled` (live default true) + toggle klavesou
--       ToggleABS za jizdy. Aktivace: `_ABS and brake>0 and
--       |RotVelocity*(size.x/2) - Velocity| - ABSThreshold > 0` => tqABS=0
--       (brzdny moment se vypne); `_ABSActive = (tqABS<1)`. Live ABSThreshold=20.
--       Signaly: Values.ABS (BoolValue, stav) a Values.ABSActive (BoolValue,
--       aktivita) -- cte TelemetryCollector jako abs_enabled/abs_active.
--       ABSEnabled NENI v MUTABLE_TUNE (VehicleManager) => harness ho nezapisuje;
--       spoleha na default true ze sablony.
--   (d) VYVRACENY PREDPOKLAD [P] z TestClient.client.lua: Drive v tomto buildu
--       NIKDE necte seat.Throttle/seat.Steer (0 vyskytu) -- cte pouze
--       UserInputService/gamepad. Mapovani `seat.Throttle = -brake` tedy brzdu
--       fyzicky nepusti; serverovy replay v TestHarness pouze loguje vstupy do
--       telemetrie, skutecnou aplikaci resi klientsky ridic (Agent D).
--   (e) Trat (TestTrack.rbxmx, overeno): StartLine x=2, BrakeLine x=3000.
--       Replay T03 brzi od t=0 (deterministicky, dle ScenarioDefinitions);
--       propojeni brzdy s prekrocenim BrakeLine je PENDING (vyzaduje
--       rozhodnuti vlastnika scenaru, ScenarioDefinitions nevlastnim).

local ScenarioRunner = {}
ScenarioRunner.__index = ScenarioRunner

-- F5 Agent D: deterministicke startovni podminky T03 (vlastnik: startovni blok).
--   (1) Rychlost presne 100 +/- 1 studs/s: nastaveni + OVERENI pred startem
--       mereni (zpetne cteni DriveSeat AssemblyLinearVelocity; mimo toleranci
--       = opakuj nastaveni max 3x, pak fail s duvodem). Zdroj rychlosti je
--       def.initial_conditions.speed_studs_s (default 100), tolerance
--       def.initial_conditions.entry_tol (default 1).
--   (2) Pozice/orientace: spawnCFrame od volajiciho (TestHarness: dil StartLine
--       + 3 y clearance, H1); Spawn overi facing +X (RightVector.X >= 0.9) a
--       roll ~= 0 (PrimaryPart/DriveSeat CFrame, tol 5 deg) pred startem.
--   (3) ABS: stav ABSThreshold/ABSEnabled se cte z Tune POUZE read-only
--       (pcall require, zadny zapis; ABSEnabled neni mutable a harness ho
--       nezapisuje). Aktivita zustava dle fyziky (Drive _ABS/_ABSActive ->
--       Values.ABS/ABSActive -> TelemetryCollector abs_enabled/abs_active ->
--       ComputeT03Metrics abs). Nelze-li ABS overit, zaznamena se
--       abs_pending:<duvod> (volajici prida do errors behu, mereni dal bezi).
--   NEMENI rizeni: WriteDriveAttributes vlastni Agent A (nedotykat).

--- Tolerancni konstanty startu T03 (stud/s, stupne, pocet pokusu).
ScenarioRunner.T03_DEFAULT_ENTRY_SPEED = 100
ScenarioRunner.T03_DEFAULT_ENTRY_TOL = 1.0
ScenarioRunner.T03_START_RETRIES = 3
ScenarioRunner.T03_ROLL_TOL_DEG = 5
ScenarioRunner.T03_FACING_MIN_X = 0.9
-- F5-FX2 spawn-settle-go: po Deploy + nulovani rychlosti cekej, dokud
-- |vertikalni rychlost| < 2 studs/s AND |roll| < 5 deg (max 3 s), pak teprve
-- armuj mereni (vstupni rychlost + gate).
ScenarioRunner.SETTLE_VSPEED_TOL = 2.0
ScenarioRunner.SETTLE_MAX_S = 3.0

ScenarioRunner.State = {
	IDLE = "idle",
	SPAWN = "spawn",
	RUNNING = "running",
	COMPLETED = "completed",
	FAILED = "failed",
}

function ScenarioRunner.new(opts: any): any
	local self = setmetatable({}, ScenarioRunner)
	opts = opts or {}
	self.state = ScenarioRunner.State.IDLE
	self.def = nil
	self.runId = nil
	self.t = 0
	self.failReason = nil
	self.inputHashParts = {}
	self.stopT = nil -- T03: cas prvniho poklesu XZ-rychlosti pod stopSpeed
	self.startInfo = nil -- F5 Agent D: vysledek overeni startu T03 (info z VerifyT03Start)
	self.absPending = nil -- F5 Agent D: "pending:<duvod>" ABS, nelze-li overit z Tune
	return self
end

function ScenarioRunner:GetState(): string
	return self.state
end

-- F5 Agent D: read-only pomocne cteni startovnich podminek (zadny zapis).
function ScenarioRunner.FindDriveSeat(vehicle: Instance?): VehicleSeat?
	if vehicle == nil then
		return nil
	end
	local ok, seat = pcall(function()
		return (vehicle :: Instance):FindFirstChildWhichIsA("VehicleSeat", true)
	end)
	if not ok or seat == nil or not (seat :: Instance):IsA("BasePart") then
		return nil
	end
	return seat :: VehicleSeat
end

-- XZ rychlost DriveSeat (Drive cte DriveSeat.Velocity; H1) pro overeni vstupu.
function ScenarioRunner.ReadDriveSeatXzSpeed(vehicle: Instance?): number?
	local seat = ScenarioRunner.FindDriveSeat(vehicle)
	if seat == nil then
		return nil
	end
	local v = (seat :: BasePart).AssemblyLinearVelocity
	return math.sqrt(v.X * v.X + v.Z * v.Z)
end

-- Roll (kloneni kolem podelne osy) z CFrame PrimaryPart / DriveSeat, ve stupnich.
function ScenarioRunner.ReadStartRollDeg(vehicle: Instance?): number?
	if vehicle == nil then
		return nil
	end
	local part: BasePart? = nil
	if (vehicle :: Instance):IsA("Model") then
		part = ((vehicle :: Model).PrimaryPart :: any) :: BasePart?
	end
	if part == nil then
		local seat = ScenarioRunner.FindDriveSeat(vehicle)
		if seat ~= nil then
			part = seat :: BasePart
		end
	end
	if part == nil then
		return nil
	end
	local ok, rx, _, rz = pcall(function()
		return (part :: BasePart).CFrame:ToOrientation()
	end)
	if not ok or typeof(rx) ~= "number" or typeof(rz) ~= "number" then
		return nil
	end
	-- Roll kolem podelne osy X pri facing +X odpovida rotaci Z orientace.
	return math.deg(rz)
end

-- Facing +X ze spawnCFrame: X slozka RightVector (trat vede podel +X, H1).
function ScenarioRunner.ReadSpawnFacingX(spawnCFrame: CFrame?): number?
	if spawnCFrame == nil then
		return nil
	end
	local ok, rv = pcall(function()
		return (spawnCFrame :: CFrame).RightVector
	end)
	if not ok or typeof(rv) ~= "Vector3" then
		return nil
	end
	return (rv :: Vector3).X
end

-- F5-FX2: vertikalni rychlost (drop po spawnu) pro settle-go. |Y| slozka
-- AssemblyLinearVelocity DriveSeat (fallback PrimaryPart); nil pri chybe.
function ScenarioRunner.ReadVerticalSpeed(vehicle: Instance?): number?
	if vehicle == nil then
		return nil
	end
	local part: BasePart? = nil
	local seat = ScenarioRunner.FindDriveSeat(vehicle)
	if seat ~= nil then
		part = seat :: BasePart
	elseif (vehicle :: Instance):IsA("Model") then
		part = ((vehicle :: Model).PrimaryPart :: any) :: BasePart?
	end
	if part == nil then
		return nil
	end
	local ok, v = pcall(function()
		return (part :: BasePart).AssemblyLinearVelocity
	end)
	if not ok or typeof(v) ~= "Vector3" then
		return nil
	end
	return math.abs((v :: Vector3).Y)
end

-- ABS konfigurace z Tune POUZE pro cteni (zadny zapis, zadny WriteTune).
-- Vraci (config, status): config = { abs_threshold, abs_enabled } (nil hodnoty
-- pri chybejicim klici); status = "ok" | "pending:<duvod>".
function ScenarioRunner.ReadABSConfig(vehicle: Instance?): (any?, string)
	if vehicle == nil then
		return nil, "pending:chybi_vozidlo"
	end
	local okFind, tune = pcall(function()
		return (vehicle :: Instance):FindFirstChild("A-Chassis Tune", true)
	end)
	if not okFind or tune == nil or not (tune :: Instance):IsA("ModuleScript") then
		return nil, "pending:chybi_A-Chassis_Tune"
	end
	local okReq, tuneTable = pcall(require, tune)
	if not okReq or typeof(tuneTable) ~= "table" then
		return nil, "pending:require_Tune_selhalo"
	end
	local cfg = {
		abs_threshold = (tuneTable :: any).ABSThreshold,
		abs_enabled = (tuneTable :: any).ABSEnabled,
	}
	if typeof(cfg.abs_threshold) ~= "number" or typeof(cfg.abs_enabled) ~= "boolean" then
		return cfg, "pending:chybi_ABSThreshold_nebo_ABSEnabled_v_Tune"
	end
	return cfg, "ok"
end

-- Nastaveni startovni rychlosti T03: RightVector spawnCFrame * speed na vsechny
-- BaseParty (DriveSeat explicitne; stejna semantika jako TestHarness, H1).
function ScenarioRunner.ApplyT03StartSpeed(vehicle: Instance?, spawnCFrame: CFrame, speed: number): boolean
	if vehicle == nil or spawnCFrame == nil or typeof(speed) ~= "number" then
		return false
	end
	local ok = pcall(function()
		local v = (spawnCFrame :: CFrame).RightVector * speed
		for _, d in (vehicle :: Instance):GetDescendants() do
			if d:IsA("BasePart") then
				local part = d :: BasePart
				part.AssemblyLinearVelocity = v
				part.AssemblyAngularVelocity = Vector3.zero
			end
		end
	end)
	return ok
end

-- Overeni startovnich podminek T03 pred startem mereni.
-- Vraci (ok, reasons, info): reasons = seznam duvodu (prazdny pri ok);
-- info = { entry_speed, entry_tol, measured_speed, roll_deg, facing_x,
--   abs_threshold, abs_enabled, abs_status }.
function ScenarioRunner.VerifyT03Start(vehicle: Instance?, def: any, spawnCFrame: CFrame?): (boolean, { string }, any)
	local reasons: { string } = {}
	local entrySpeed = ScenarioRunner.T03_DEFAULT_ENTRY_SPEED
	local entryTol = ScenarioRunner.T03_DEFAULT_ENTRY_TOL
	if def ~= nil and def.initial_conditions ~= nil then
		local s = (def.initial_conditions :: any).speed_studs_s
		if typeof(s) == "number" then
			entrySpeed = s
		end
		local e = (def.initial_conditions :: any).entry_tol
		if typeof(e) == "number" then
			entryTol = e
		end
	end
	local measured = ScenarioRunner.ReadDriveSeatXzSpeed(vehicle)
	if measured == nil then
		table.insert(reasons, "entry_speed_neoverena:chybi_DriveSeat")
	elseif math.abs((measured :: number) - entrySpeed) > entryTol then
		table.insert(
			reasons,
			string.format(
				"entry_speed_mimo_toleranci:cil=%.1f_tol=%.1f_mereno=%.2f",
				entrySpeed,
				entryTol,
				measured :: number
			)
		)
	end
	local facingX = ScenarioRunner.ReadSpawnFacingX(spawnCFrame)
	if facingX == nil then
		table.insert(reasons, "facing_neoveren:chybi_spawnCFrame")
	elseif (facingX :: number) < ScenarioRunner.T03_FACING_MIN_X then
		table.insert(reasons, string.format("facing_neni_+X:RightVector.X=%.3f", facingX :: number))
	end
	local rollDeg = ScenarioRunner.ReadStartRollDeg(vehicle)
	if rollDeg == nil then
		table.insert(reasons, "roll_neoveren:chybi_PrimaryPart_nebo_DriveSeat")
	elseif math.abs(rollDeg :: number) > ScenarioRunner.T03_ROLL_TOL_DEG then
		table.insert(reasons, string.format("roll_pred_startem_nenulovy:%.1f_deg", rollDeg :: number))
	end
	local absCfg, absStatus = ScenarioRunner.ReadABSConfig(vehicle)
	local info = {
		entry_speed = entrySpeed,
		entry_tol = entryTol,
		measured_speed = measured,
		facing_x = facingX,
		roll_deg = rollDeg,
		abs_threshold = if absCfg ~= nil then absCfg.abs_threshold else nil,
		abs_enabled = if absCfg ~= nil then absCfg.abs_enabled else nil,
		abs_status = absStatus,
	}
	return #reasons == 0, reasons, info
end

function ScenarioRunner:Reset(): ()
	self.state = ScenarioRunner.State.IDLE
	self.def = nil
	self.runId = nil
	self.t = 0
	self.failReason = nil
	self.inputHashParts = {}
	self.stopT = nil
	self.startInfo = nil
	self.absPending = nil
end

-- Spawn faze: synchronni reset vozidla na startovni CFrame, nulove rychlosti, ustaleni.
-- PivotTo pivotuje kolem PrimaryPart (VehicleManager.CloneVehicle nastavi
-- PrimaryPart = DriveSeat na klonech; F4.4 M2 -- bez nej je placement kloubove
-- sestavy nedefinovany). Rychlosti se nuluji (zadna zmena fyziky); vyskove
-- odsazeni (+3 y pro T03) dodava volajici ve spawnCFrame (TestHarness).
-- F5 Agent D: pro kind "straight_brake_100_0" (T03) nasleduje po ustaleni
-- nastaveni presne vstupni rychlosti + overeni pred startem mereni
-- (zpetne cteni DriveSeat; mimo toleranci = retry max 3x, pak FAILED).
function ScenarioRunner:Spawn(def: any, runId: string, vehicle: Instance?, spawnCFrame: CFrame?): (boolean, string?)
	self.def = def
	self.runId = runId
	self.state = ScenarioRunner.State.SPAWN
	self.t = 0
	self.stopT = nil
	self.startInfo = nil
	self.absPending = nil
	-- F5-FX2 stuck-brake: pred startem mereni EXPLICITNE nuluj vstupy
	-- (0,0,0 + overeni; best-effort, duvod se propise do failReason pri voidu).
	if vehicle ~= nil then
		local okZero, zeroErr = ScenarioRunner.ClearDriveInputs(vehicle)
		if not okZero then
			self.state = ScenarioRunner.State.FAILED
			self.failReason = "startovni_podminky:" .. tostring(zeroErr)
			return false, self.failReason
		end
	end
	if vehicle ~= nil and spawnCFrame ~= nil and vehicle:IsA("Model") then
		pcall(function()
			vehicle:PivotTo(spawnCFrame)
			for _, d in vehicle:GetDescendants() do
				if d:IsA("BasePart") then
					d.AssemblyLinearVelocity = Vector3.zero
					d.AssemblyAngularVelocity = Vector3.zero
				end
			end
		end)
	end
	local settle = 1.0
	if def ~= nil and def.initial_conditions ~= nil and def.initial_conditions.settle_s ~= nil then
		settle = def.initial_conditions.settle_s
	end
	task.wait(settle)
	if def ~= nil and (def :: any).kind == "straight_brake_100_0" then
		return self:SpawnT03Verified(vehicle, spawnCFrame)
	end
	self.state = ScenarioRunner.State.RUNNING
	return true, nil
end

-- F5 Agent D: T03 vetev Spawnu (pouze startovni podminky; rizeni netkne).
-- Po ustaleni nastavi vstupni rychlost, overi (rychlost/facing/roll/ABS),
-- pri nesplnene rychlosti opakuje nastaveni max T03_START_RETRIES x.
-- Vraci (true, absPending|nil) pri uspechu, (false, duvod) pri neuspechu.
function ScenarioRunner:SpawnT03Verified(vehicle: Instance?, spawnCFrame: CFrame?): (boolean, string?)
	if vehicle == nil or spawnCFrame == nil then
		self.state = ScenarioRunner.State.FAILED
		self.failReason = "startovni_podminky:chybi_vozidlo_nebo_spawnCFrame"
		return false, self.failReason
	end
	local def = self.def
	local entrySpeed = ScenarioRunner.T03_DEFAULT_ENTRY_SPEED
	if def ~= nil and (def :: any).initial_conditions ~= nil then
		local s = ((def :: any).initial_conditions :: any).speed_studs_s
		if typeof(s) == "number" then
			entrySpeed = s
		end
	end
	-- F5-FX2 spawn-settle-go: po Deploy + nulovani rychlosti cekej na usednuti
	-- (|vy| < 2 AND |roll| < 5 deg, max 3 s), pak teprve armuj mereni.
	-- Timeout = void s duvodem (rock/spin loterie z rozhoupane sestavy, F4).
	local okSettle, settleErr = ScenarioRunner.WaitForSettle(vehicle)
	if not okSettle then
		self.state = ScenarioRunner.State.FAILED
		self.failReason = "startovni_podminky:" .. tostring(settleErr)
		return false, self.failReason
	end
	-- F5-FX2 (4): roll ~= 0 over PRED nastavenim rychlosti (jinak void).
	-- Rychlost se na rozhoupanou sestavu vubec nenastavuje.
	local preRoll = ScenarioRunner.ReadStartRollDeg(vehicle)
	if preRoll == nil then
		self.state = ScenarioRunner.State.FAILED
		self.failReason = "startovni_podminky:roll_neoveren_pred_rychlosti:chybi_PrimaryPart_nebo_DriveSeat"
		return false, self.failReason
	elseif math.abs(preRoll) > ScenarioRunner.T03_ROLL_TOL_DEG then
		self.state = ScenarioRunner.State.FAILED
		self.failReason = string.format("startovni_podminky:roll_pred_startem_nenulovy:%.1f_deg", preRoll)
		return false, self.failReason
	end
	local ok = false
	local reasons: { string } = {}
	local info: any = nil
	for _ = 1, ScenarioRunner.T03_START_RETRIES do
		ScenarioRunner.ApplyT03StartSpeed(vehicle, spawnCFrame, entrySpeed)
		ok, reasons, info = ScenarioRunner.VerifyT03Start(vehicle, def, spawnCFrame)
		if ok then
			break
		end
		-- Retry ma smysl jen pro rychlost; facing/roll/spawn se nastavenim
		-- rychlosti nezmeni -- pri jejich poruse konci smycka hned.
		local onlySpeed = true
		for _, r in reasons do
			if string.find(r, "entry_speed_mimo_toleranci", 1, true) == nil then
				onlySpeed = false
				break
			end
		end
		if not onlySpeed then
			break
		end
	end
	self.startInfo = info
	if info ~= nil and typeof(info.abs_status) == "string" and string.sub(info.abs_status, 1, 8) == "pending:" then
		self.absPending = "abs_" .. info.abs_status
	end
	if not ok then
		self.state = ScenarioRunner.State.FAILED
		self.failReason = "startovni_podminky:" .. table.concat(reasons, ";")
		return false, self.failReason
	end
	self.state = ScenarioRunner.State.RUNNING
	return true, self.absPending
end

-- Deterministicky ridic: vraci (throttle, brake, steer) pro dany cas.
function ScenarioRunner:DriverInputs(t: number): (number, number, number)
	local kind = if self.def ~= nil then self.def.kind else "straight_accel"
	if kind == "straight_brake_100_0" then
		return 0, math.clamp(t / 0.15, 0, 1), 0
	elseif kind == "lane_change" then
		-- Replay: jedna perioda sinu od t=5 s (identicke vstupy pro kazdou variantu).
		local steer = 0
		if t >= 5 and t <= 8 then
			steer = 0.4 * math.sin(2 * math.pi * (t - 5) / 3)
		end
		return 0.5, 0, steer
	else
		return math.clamp(t / 0.2, 0, 1), 0, 0
	end
end

-- F4.4 F3 / F5-A arbitrace: zapis ridiciho vystupu do atributu vozu (server->klient replikace).
-- Drive mustek (VehicleManager.ApplyDriveInputBridge) v Heartbeat smycce PREBIRA pritomne
-- atributy do _IBrake/_IThrot/_GSteerT: server je JEDINY urcujici zapisovac (autonomni rezim).
-- nil = atribut se SMAZE a prislusna osa se vrati do manualniho rezimu (klavesy/gamepad).
-- Zadny jiny vstup se tu nemeni; sedadlo se nepouziva (Drive ho v tomto buildu necte).
-- Diagnostika pozadovane-vs-skutecne brzdy BEZ noveho kanalu (novy kanal vlastni Agent C):
-- pozadovana hodnota je v telemetrii v existujicim kanalu `inputs.brake` (toteze hodnoty,
-- jake dostava TelemetryCollector:SetInputs); skutecnou brzdu publikuje Drive kazdy frame
-- v existujicim Values.Brake (_GBrake). Trvalou neshodu hlasi CheckBrakeDiag jednim warn (zadny
-- zapis fyziky, zadny novy kanal, zadny novy atribut).
-- F5-A: tolerance a perzistence read-back diagnostiky brzdy (vzorky volani WriteDriveAttributes).
ScenarioRunner.BRAKE_DIAG_TOL = 0.08
ScenarioRunner.BRAKE_DIAG_SAMPLES = 45
ScenarioRunner._brakeDiagState = {}
function ScenarioRunner.WriteDriveAttributes(vehicle: Instance?, throttle: number?, brake: number?, steer: number?): ()
	if vehicle == nil then
		return
	end
	pcall(function()
		if throttle == nil then
			vehicle:SetAttribute("AE_Throttle", nil)
		else
			vehicle:SetAttribute("AE_Throttle", throttle)
		end
		if brake == nil then
			vehicle:SetAttribute("AE_Brake", nil)
		else
			vehicle:SetAttribute("AE_Brake", brake)
		end
		if steer == nil then
			vehicle:SetAttribute("AE_Steer", nil)
		else
			vehicle:SetAttribute("AE_Steer", steer)
		end
	end)
	ScenarioRunner.CheckBrakeDiag(vehicle, brake)
end

-- F5-A: read-only read-back pozadovane (AE_Brake) vs skutecne (Values.Brake) brzdy.
-- Volano z WriteDriveAttributes (vzorkovaci frekvence harnessu); zadny zapis, zadny spawn.
-- Neshoda trvajici BRAKE_DIAG_SAMPLES po sobe jdoucich volani = jeden warn na beh (latch).
-- Values/Drive jeste nebezi => zadny zaver (cekam). Vycisteni pri brake == nil (konec behu).
function ScenarioRunner.CheckBrakeDiag(vehicle: Instance?, brakeCmd: number?): ()
	if vehicle == nil then
		return
	end
	if brakeCmd == nil then
		ScenarioRunner._brakeDiagState[vehicle] = nil
		return
	end
	local st: any = ScenarioRunner._brakeDiagState[vehicle]
	if st == nil then
		st = { mism = 0, warned = false }
		ScenarioRunner._brakeDiagState[vehicle] = st
	end
	if st.warned then
		return
	end
	local ok, actual = pcall(function()
		local values = (vehicle :: Instance):FindFirstChild("Values", true)
		if values == nil then
			return nil
		end
		local b = (values :: Instance):FindFirstChild("Brake")
		if b ~= nil and b:IsA("NumberValue") then
			return (b :: NumberValue).Value
		end
		return nil
	end)
	if not ok or actual == nil then
		return
	end
	if math.abs((actual :: number) - (brakeCmd :: number)) > ScenarioRunner.BRAKE_DIAG_TOL then
		st.mism = st.mism + 1
	else
		st.mism = 0
	end
	if st.mism >= ScenarioRunner.BRAKE_DIAG_SAMPLES then
		st.warned = true
		warn(
			string.format(
				"[AE_BRAKE_DIAG] pozadovano AE_Brake=%.3f vs skutecne Values.Brake=%.3f (trva >=%d vzorku)",
				brakeCmd :: number,
				actual :: number,
				ScenarioRunner.BRAKE_DIAG_SAMPLES
			)
		)
	end
end

-- F5-FX2 stuck-brake: EXPLICITNI nulovani AE_Brake/AE_Throttle/AE_Steer
-- (WriteDriveAttributes 0,0,0) + overeni zpetnym prectenim. nil atribut
-- posledni prikaz nemaze (klientsky _IBrake drzi 1.0 i po briefu, F4-F1.0),
-- proto se pise 0, ne nil. Vraci (true) nebo (false, duvod).
function ScenarioRunner.ClearDriveInputs(vehicle: Instance?): (boolean, string?)
	if vehicle == nil then
		return false, "chybi_vozidlo"
	end
	ScenarioRunner.WriteDriveAttributes(vehicle, 0, 0, 0)
	local ok, b, t, s = pcall(function()
		return (vehicle :: Instance):GetAttribute("AE_Brake"),
			(vehicle :: Instance):GetAttribute("AE_Throttle"),
			(vehicle :: Instance):GetAttribute("AE_Steer")
	end)
	if not ok then
		return false, "vstupni_nuly_neovereny:GetAttribute_selhalo"
	end
	if b ~= 0 or t ~= 0 or s ~= 0 then
		return false,
			string.format(
				"vstupni_nuly_neovereny:AE_Brake=%s_AE_Throttle=%s_AE_Steer=%s",
				tostring(b),
				tostring(t),
				tostring(s)
			)
	end
	return true, nil
end

-- F5-FX2 spawn-settle-go: po Deploy + nulovani rychlosti cekej, dokud
-- |vertikalni rychlost| < SETTLE_VSPEED_TOL AND |roll| < T03_ROLL_TOL_DEG
-- (max SETTLE_MAX_S, krok 0.1 s), pak teprve armuj mereni.
-- Vraci (true) pri usednuti, (false, duvod) pri timeoutu (volajici voiduje).
function ScenarioRunner.WaitForSettle(vehicle: Instance?): (boolean, string?)
	local deadline = os.clock() + ScenarioRunner.SETTLE_MAX_S
	while true do
		local vy = ScenarioRunner.ReadVerticalSpeed(vehicle)
		local roll = ScenarioRunner.ReadStartRollDeg(vehicle)
		if
			vy ~= nil
			and roll ~= nil
			and vy < ScenarioRunner.SETTLE_VSPEED_TOL
			and math.abs(roll) < ScenarioRunner.T03_ROLL_TOL_DEG
		then
			return true, nil
		end
		if os.clock() >= deadline then
			return false, string.format("settle_timeout:vy=%s_roll=%s", tostring(vy), tostring(roll))
		end
		task.wait(0.1)
	end
end
-- Vyhodnoceni ukonceni; vraci "running" | "completed" | "failed".
function ScenarioRunner:Evaluate(sample: any, def: any, t: number): string
	if sample == nil then
		return "running"
	end
	-- Fail pred completion (bezpecnost). Roll je nepovinny kanal; chybi-li, preskocit.
	if sample.roll_deg ~= nil and math.abs(sample.roll_deg) > 45 then
		self.failReason = "roll_gt_45"
		return "failed"
	end
	if sample.nan_detected == true then
		self.failReason = "nan_telemetry"
		return "failed"
	end
	-- T03 (straight_brake_100_0): completion dle ScenarioDefinitions --
	-- "rychlost < 0.1 studs/s + 1 s ustaleni". Rychlost = XZ slozka (vodorovna
	-- rovina; Y ignorujeme). Po prvnim poklesu pod 0.1 se ceka 1.0 s, pak completed.
	-- Timeout (duration_s) zustava zaloznim koncem (neuplny beh s vlajkou).
	if (if def ~= nil then def.kind else nil) == "straight_brake_100_0" then
		local v = ScenarioRunner.XzSpeed(if sample.vel ~= nil then sample.vel else nil)
		if v ~= nil then
			if v < 0.1 then
				if self.stopT == nil then
					self.stopT = t
				end
				if t - (self.stopT :: number) >= 1.0 then
					return "completed"
				end
			else
				self.stopT = nil
			end
		end
	end
	if t >= (def.duration_s or 30) then
		return "completed"
	end
	return "running"
end

function ScenarioRunner:Finish(status: string, reason: string?, vehicle: Instance?): ()
	if status == "completed" then
		self.state = ScenarioRunner.State.COMPLETED
	else
		self.state = ScenarioRunner.State.FAILED
	end
	self.failReason = reason
	-- F5-FX2 stuck-brake: na konci behu EXPLICITNE nuluj vstupy
	-- (0,0,0 + overeni; best-effort — volajici muze overit sam).
	if vehicle ~= nil then
		pcall(function()
			ScenarioRunner.ClearDriveInputs(vehicle)
		end)
	end
end

-- XZ slozka vektoru {x,y,z} (vodorovna rychlost / vzdalenost); nil pri chybejicich datech.
function ScenarioRunner.XzSpeed(v: any): number?
	if typeof(v) ~= "table" or typeof(v.x) ~= "number" or typeof(v.z) ~= "number" then
		return nil
	end
	return math.sqrt(v.x * v.x + v.z * v.z)
end

function ScenarioRunner.XzSegment(a: any, b: any): number?
	if typeof(a) ~= "table" or typeof(b) ~= "table" then
		return nil
	end
	if typeof(a.x) ~= "number" or typeof(a.z) ~= "number" then
		return nil
	end
	if typeof(b.x) ~= "number" or typeof(b.z) ~= "number" then
		return nil
	end
	local dx = b.x - a.x
	local dz = b.z - a.z
	return math.sqrt(dx * dx + dz * dz)
end

-- T03 metriky z XZ telemetrie (vzorky TelemetryCollector: pos{x,y,z}, vel{x,y,z},
-- accel?, yaw_rate?, abs_active?). Vraci (metrics, nil) nebo (nil, reason).
--   brake_distance_studs: kumulativni XZ draha od prvniho vzorku do prvniho
--     vzorku s XZ-rychlosti < 0.1 (prah zastaveni dle ScenarioDefinitions T03).
--   stopping_time_s: cas t tohoto vzorku (od zacatku brzdneho replaye t=0).
--   mean_decel_studs_s2: v0/stopping_time (v0 = XZ rychlost prvniho vzorku).
--   peak_decel_studs_s2: maximum XZ slozky accel pres vzorky do zastaveni
--     (nil, chybi-li accel kanal).
--   lat_deviation_studs: max |z - z0| (primy usek podel osy X; priblizne).
--   yaw_rate_max: max |yaw_rate| do zastaveni (nil, chybi-li kanal).
--   abs: { active = bool, active_samples = n } z existujiciho signalu
--     Values.ABSActive; chybi-li kanal ve vsech vzorcich,
--     { active = nil, reason = "chybi Values.ABSActive ve vozidle" }.
-- Nezastavi-li vuz do konce zaznamu: stopped=false + draha/cas do konce zaznamu
-- (neuplny beh; agregace takovy beh oznacuje).
function ScenarioRunner.ComputeT03Metrics(samples: any): (any?, string?)
	if typeof(samples) ~= "table" or #samples == 0 then
		return nil, "prazdne_vzorky"
	end
	local first = samples[1]
	local v0 = ScenarioRunner.XzSpeed(if first ~= nil then first.vel else nil)
	if v0 == nil then
		return nil, "chybi_vel_v_prvnim_vzorku"
	end
	local dist = 0
	local distAtStop: number? = nil
	local stopT: number? = nil
	local peakDecel = 0
	local peakKnown = false
	local yawMax = 0
	local yawKnown = false
	local latDev = 0
	local x0Known = typeof(first.pos) == "table" and typeof(first.pos.z) == "number"
	local absKnown = false
	local absSeen = false
	local absSamples = 0
	local prevPos = if typeof(first.pos) == "table" then first.pos else nil
	for i = 2, #samples do
		local s = samples[i]
		if typeof(s) ~= "table" then
			continue
		end
		local seg = ScenarioRunner.XzSegment(prevPos, s.pos)
		if seg ~= nil then
			dist += seg
		end
		if typeof(s.pos) == "table" then
			prevPos = s.pos
		end
		if typeof(s.accel) == "table" then
			local a = ScenarioRunner.XzSpeed(s.accel)
			if a ~= nil then
				peakKnown = true
				peakDecel = math.max(peakDecel, a)
			end
		end
		if typeof(s.yaw_rate) == "number" then
			yawKnown = true
			yawMax = math.max(yawMax, math.abs(s.yaw_rate))
		end
		if x0Known and typeof(s.pos) == "table" and typeof(s.pos.z) == "number" then
			latDev = math.max(latDev, math.abs(s.pos.z - (first.pos :: any).z))
		end
		if s.abs_active ~= nil then
			absKnown = true
			if s.abs_active == true then
				absSeen = true
				absSamples += 1
			end
		end
		if stopT == nil and typeof(s.t) == "number" then
			local v = ScenarioRunner.XzSpeed(s.vel)
			if v ~= nil and v < 0.1 then
				stopT = s.t
				distAtStop = dist
			end
		end
	end
	local stopped = stopT ~= nil
	local brakeDist = if distAtStop ~= nil then distAtStop else dist
	local stopTime = if stopT ~= nil then stopT else (samples[#samples] :: any).t
	local abs: any
	if absKnown then
		abs = { active = absSeen, active_samples = absSamples }
	else
		abs = { active = nil, reason = "chybi Values.ABSActive ve vozidle (Drive signal nezapsal)" }
	end
	return {
		stopped = stopped,
		brake_distance_studs = brakeDist,
		stopping_time_s = stopTime,
		mean_decel_studs_s2 = if stopT ~= nil and (stopT :: number) > 0 then v0 / (stopT :: number) else nil,
		peak_decel_studs_s2 = if peakKnown then peakDecel else nil,
		lat_deviation_studs = latDev,
		yaw_rate_max = if yawKnown then yawMax else nil,
		initial_speed_studs_s = v0,
		abs = abs,
	},
		nil
end

return ScenarioRunner
