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
	return self
end

function ScenarioRunner:GetState(): string
	return self.state
end

function ScenarioRunner:Reset(): ()
	self.state = ScenarioRunner.State.IDLE
	self.def = nil
	self.runId = nil
	self.t = 0
	self.failReason = nil
	self.inputHashParts = {}
	self.stopT = nil
end

-- Spawn faze: synchronni reset vozidla na startovni CFrame, nulove rychlosti, ustaleni.
-- PivotTo pivotuje kolem PrimaryPart (VehicleManager.CloneVehicle nastavi
-- PrimaryPart = DriveSeat na klonech; F4.4 M2 -- bez nej je placement kloubove
-- sestavy nedefinovany). Rychlosti se nuluji (zadna zmena fyziky); vyskove
-- odsazeni (+3 y pro T03) dodava volajici ve spawnCFrame (TestHarness).
function ScenarioRunner:Spawn(def: any, runId: string, vehicle: Instance?, spawnCFrame: CFrame?): (boolean, string?)
	self.def = def
	self.runId = runId
	self.state = ScenarioRunner.State.SPAWN
	self.t = 0
	self.stopT = nil
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
	if def.initial_conditions ~= nil and def.initial_conditions.settle_s ~= nil then
		settle = def.initial_conditions.settle_s
	end
	task.wait(settle)
	self.state = ScenarioRunner.State.RUNNING
	return true, nil
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

-- F4.4 F3: zapis ridiciho vystupu do atributu vozu (server->klient replikace).
-- Drive mustek (VehicleManager.ApplyDriveInputBridge) je v Heartbeat smycce ORuje
-- do _IBrake/_IThrot/_GSteerT. Zadny jiny vstup se tu nemeni; sedadlo se nepouziva
-- (Drive ho v tomto buildu necte, viz hlavicka).
function ScenarioRunner.WriteDriveAttributes(vehicle: Instance?, throttle: number, brake: number, steer: number): ()
	if vehicle == nil then
		return
	end
	pcall(function()
		vehicle:SetAttribute("AE_Throttle", throttle)
		vehicle:SetAttribute("AE_Brake", brake)
		vehicle:SetAttribute("AE_Steer", steer)
	end)
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

function ScenarioRunner:Finish(status: string, reason: string?): ()
	if status == "completed" then
		self.state = ScenarioRunner.State.COMPLETED
	else
		self.state = ScenarioRunner.State.FAILED
	end
	self.failReason = reason
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
