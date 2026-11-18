-- TestClient (LocalScript, StarterPlayerScripts) -- klientsky ridic-testovac.
-- Vlastnik: Agent D. Faze 9 (Autonomous Driver runtime).
--
-- Uloha:
--   1. Najde DriveSeat pracovni kopie vozidla (klon, nikdy sablona/original).
--   2. Usadi lokalniho hrace (A-Chassis Drive bezi jen u ridice-klienta,
--      docs/A-CHASSIS-AUDIT.md: sitovy model; DriveSeat network-owner = hrac).
--   3. Na pokyn serveru pres RemoteEvent spusti/zastavi jizdu: vytvori
--      RuntimeController (Heartbeat smycka), ktery kazdy snimek vola
--      AutonomousDriver.step() a vystupy (throttle/brake/steer) predava do
--      EXISTUJICICH seat-vstupu DriveSeat (Throttle/Steer).
--   4. Po ukonceni scenare (completed/abort/timeout/nouzove zastaveni) vynuluje
--      vstupy a posle serveru vysledek pres tytez RemoteEvent.
--
-- ZAKAZY (Agent D): zadny teleport vozidla, zadne prime nastavovani
-- pozice/rychlosti (CFrame/Velocity/AssemblyLinearVelocity se tu nikdy
-- nezapisuji -- jen ctu pro feedback). Pocatecni spawn resi server (harness),
-- ne tento skript.
--
-- Mapovani vystupu ridice na VehicleSeat (PREDPOKLAD [P] -- overit ve Studiu,
-- viz PENDING): A-Chassis Drive cte seat.Throttle (-1..1) a seat.Steer (-1..1);
-- "S" (= zaporny Throttle) pri jizde vpred brzdi, pak couva. Proto:
--   seat.Throttle = (throttle > 0) and throttle or -brake; seat.Steer = steer.
-- Behem scenare nesmi hrac sahat na klavesy (ridic by se pral se vstupem).
--
-- Protokol RemoteEvent (ReplicatedStorage/AutoEngineer/AE_DriverCommands):
--   server -> klient OnClientEvent { cmd = "Start", scenarioId = "T01", params = {...} }
--   server -> klient OnClientEvent { cmd = "Stop", reason = "..." }
--   server -> klient OnClientEvent { cmd = "EmergencyStop", reason = "..." }
--   klient -> server FireServer { type = "Started", scenarioId }
--   klient -> server FireServer { type = "Result", scenarioId, outcome, reason, runTime_s, distance_studs }
--   klient -> server FireServer { type = "Error", message }
-- Harness-brief (ReplicatedStorage/AutoEngineerRemotes/AERunBrief, F4.4 Agent F3):
--   server -> klient OnClientEvent { run_id, scenario_id, params? } -- stejny Start
--   (usednuti hrace, je-li postava; zadny teleport). Obe sbernice aktivni soucasne.
-- outcome: "completed" | "aborted" | "timeout" | "emergency_stop" | "stopped".
--
-- Jazyk: komentare cesky, identifikatory anglicky.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Workspace = game:GetService("Workspace")

local AE_FOLDER_NAME = "AutoEngineer"
local SHARED_NAME = "Shared"
local DRIVER_MODULE_NAME = "AutonomousDriver"
local SCENARIOS_MODULE_NAME = "ScenarioDefinitions"
local REMOTE_NAME = "AE_DriverCommands"
local RUN_REMOTES_FOLDER = "AutoEngineerRemotes"
local RUN_BRIEF_NAME = "AERunBrief"
local DRIVE_SEAT_NAME = "DriveSeat"
local TUNE_MODULE_NAME = "A-Chassis Tune"

local LocalPlayer = Players.LocalPlayer

-- Nacteni sdilenych modulu (Rojo je synchronizuje jako ModuleScripty).
local aeFolder = ReplicatedStorage:WaitForChild(AE_FOLDER_NAME, 15)
local shared = aeFolder:WaitForChild(SHARED_NAME, 15)
local Driver = require(shared:WaitForChild(DRIVER_MODULE_NAME, 15))
local ScenarioDefs = require(shared:WaitForChild(SCENARIOS_MODULE_NAME, 15))

-- RemoteEvent pro rizeni ze serveru; zalozne vytvoreni kdyby harness (Agent E)
-- ve Studiu jeste nebezel -- klientem vytvoreny RemoteEvent se replikuje.
local remote = aeFolder:FindFirstChild(REMOTE_NAME)
if remote == nil then
	remote = Instance.new("RemoteEvent")
	remote.Name = REMOTE_NAME
	remote.Parent = aeFolder
end

-- F7.1: server-autoritativni pohon (AEDriveCmd). Klient posila navrh pohonu,
-- server je jediny zapisovac #AV/#BV (server-nil ownership). ApplyToSeat
-- zustava jako nouzovy manual-fallback (Drive ho za nil-ownership ignoruje).
local driveCmd: RemoteEvent? = nil
local driveSeq = 0
task.spawn(function()
	local folder = ReplicatedStorage:WaitForChild(RUN_REMOTES_FOLDER, 60)
	if folder == nil then
		return
	end
	local ev = folder:WaitForChild("AEDriveCmd", 60)
	if ev ~= nil and ev:IsA("RemoteEvent") then
		driveCmd = ev
	end
end)

local function clamp(v: number, lo: number, hi: number): number
	if v < lo then
		return lo
	end
	if v > hi then
		return hi
	end
	return v
end

-- Najde DriveSeat pracovni kopie: prednostne model s "A-Chassis Tune".
local function FindDriveSeat(): VehicleSeat?
	local fallback: VehicleSeat? = nil
	for _, desc in Workspace:GetDescendants() do
		if desc:IsA("VehicleSeat") and desc.Name == DRIVE_SEAT_NAME then
			local model = desc:FindFirstAncestorOfClass("Model")
			if model ~= nil and model:FindFirstChild(TUNE_MODULE_NAME, true) ~= nil then
				return desc
			end
			if fallback == nil then
				fallback = desc
			end
		end
	end
	return fallback
end

-- Zapis vystupu ridice do existujicich seat-vstupu. ZADNY zapis fyziky.
local function ApplyToSeat(seat: VehicleSeat, throttle: number, brake: number, steer: number)
	local t = clamp(throttle or 0, 0, 1)
	local b = clamp(brake or 0, 0, 1)
	local s = clamp(steer or 0, -1, 1)
	if t > 0 then
		seat.Throttle = t
	else
		seat.Throttle = -b
	end
	seat.Steer = s
	pcall(function()
		local tf = (seat :: any).ThrottleFloat
		local sf = (seat :: any).SteerFloat
		if tf ~= nil then
			(seat :: any).ThrottleFloat = seat.Throttle
		end
		if sf ~= nil then
			(seat :: any).SteerFloat = s
		end
	end)
end

local function ZeroSeat(seat: VehicleSeat?)
	if seat == nil then
		return
	end
	seat.Throttle = 0
	seat.Steer = 0
	pcall(function()
		(seat :: any).ThrottleFloat = 0
		(seat :: any).SteerFloat = 0
	end)
end

-- RuntimeController: jeden aktivni beh scenare (vytvari se na Start, nici na Stop/vysledek).
local RuntimeController = {
	active = false,
	connection = nil :: RBXScriptConnection?,
	ctrl = nil :: any,
	seat = nil :: VehicleSeat?,
	scenarioId = "",
	def = nil :: any,
	tStart = 0,
	timeout_s = 30,
	brakeZone = false,
	maxSpeedSeen = 0,
}

local function FeedbackFromSeat(seat: VehicleSeat): { [string]: any }
	local pos = seat.Position
	local lv = seat.CFrame.LookVector
	local rv = seat.CFrame.RightVector
	local vel = seat.AssemblyLinearVelocity
	local speed = vel.Magnitude
	local rollDeg = math.deg(math.asin(clamp(rv.Y, -1, 1)))
	return {
		speed = speed,
		x = pos.X,
		y = pos.Z,
		heading = math.atan2(lv.X, lv.Z),
		rollDeg = rollDeg,
		nanFlag = (speed ~= speed),
		brakeZone = RuntimeController.brakeZone,
	}
end

local function Finish(outcome: string, reason: string)
	if not RuntimeController.active then
		return
	end
	RuntimeController.active = false
	if RuntimeController.connection ~= nil then
		RuntimeController.connection:Disconnect()
		RuntimeController.connection = nil
	end
	ZeroSeat(RuntimeController.seat)
	local runTime = os.clock() - RuntimeController.tStart
	local dist = 0
	if RuntimeController.ctrl ~= nil then
		dist = RuntimeController.ctrl.distance or 0
	end
	RuntimeController.ctrl = nil
	RuntimeController.brakeZone = false
	remote:FireServer({
		type = "Result",
		scenarioId = RuntimeController.scenarioId,
		outcome = outcome,
		reason = reason,
		runTime_s = runTime,
		distance_studs = dist,
		maxSpeed_studs_s = RuntimeController.maxSpeedSeen,
		driverVersion = Driver.DRIVER_VERSION,
	})
end

local function StartScenario(scenarioId: string, params: { [string]: any }?)
	-- Uklid predchoziho behu (vstupy na nulu, zadny teleport).
	if RuntimeController.active then
		Finish("stopped", "superseded_by_new_start")
	end
	local def = ScenarioDefs.Get(scenarioId)
	if def == nil then
		remote:FireServer({ type = "Error", message = "unknown_scenario:" .. tostring(scenarioId) })
		return
	end
	local seat = RuntimeController.seat
	if seat == nil or seat.Parent == nil then
		seat = FindDriveSeat()
		RuntimeController.seat = seat
	end
	if seat == nil then
		remote:FireServer({ type = "Error", message = "drive_seat_not_found" })
		return
	end
	-- Ridic musi sedet: A-Chassis Drive bezi jen u klienta-ridice.
	-- F7.1-NOSIT: scenar muze sednuti zakazat (def.no_testclient_sit) --
	-- server-authorita ridice nepotrebuje; testuje se sit/weld vektor.
	local nosit = def ~= nil and (def :: any).no_testclient_sit == true
	local character = LocalPlayer.Character
	local humanoid = nil
	if character ~= nil then
		humanoid = character:FindFirstChildOfClass("Humanoid")
	end
	if nosit then
		RuntimeController.seat = seat
		RuntimeController.scenarioId = scenarioId
		RuntimeController.def = def
	else
	if humanoid == nil or seat.Occupant ~= humanoid then
		if humanoid ~= nil then
			seat:Sit(humanoid)
		end
		local t0 = os.clock()
		while (seat.Occupant ~= humanoid) and (os.clock() - t0 < 10) do
			task.wait(0.1)
			if humanoid == nil then
				break
			end
		end
		if seat.Occupant ~= humanoid then
			remote:FireServer({ type = "Error", message = "seat_failed" })
			return
		end
	end
	end

	local p = params or {}
	local ctrl, err = Driver.new(scenarioId, p)
	if ctrl == nil then
		remote:FireServer({ type = "Error", message = tostring(err) })
		return
	end
	RuntimeController.ctrl = ctrl
	RuntimeController.scenarioId = scenarioId
	RuntimeController.def = def
	RuntimeController.timeout_s = tonumber(p.timeout_s) or (tonumber(def.duration_s) or 30)
	RuntimeController.brakeZone = p.brakeZone == true
	RuntimeController.maxSpeedSeen = 0
	RuntimeController.tStart = os.clock()
	RuntimeController.active = true

	remote:FireServer({ type = "Started", scenarioId = scenarioId, driverVersion = Driver.DRIVER_VERSION })

	RuntimeController.connection = RunService.Heartbeat:Connect(function(dt: number)
		if not RuntimeController.active then
			return
		end
		-- Timeout hlida klient (server ma vlastni nezavisly limit).
		if os.clock() - RuntimeController.tStart >= RuntimeController.timeout_s then
			Finish("timeout", "client_timeout")
			return
		end
		local c = RuntimeController.ctrl
		local s = RuntimeController.seat
		if c == nil or s == nil or s.Parent == nil then
			Finish("aborted", "seat_lost")
			return
		end
		-- Aktualizace brzdne zony z parametru serveru (server ji muze poslat
		-- prikazem Start s brakeZone = true, nebo pozdeji pres params).
		local fb = FeedbackFromSeat(s)
		if fb.speed > RuntimeController.maxSpeedSeen then
			RuntimeController.maxSpeedSeen = fb.speed
		end
		local out = Driver.step(c, dt, fb)
		ApplyToSeat(s, out.throttle, out.brake, out.steer)
		-- F7.1: navrh pohonu serveru (server validuje + zapisuje, klient nenahrazuje).
		if driveCmd ~= nil then
			driveSeq += 1
			pcall(function()
				local dc = driveCmd :: RemoteEvent
				dc:FireServer({
					throttle = out.throttle,
					brake = out.brake,
					steer = out.steer,
					seq = driveSeq,
					run_id = RuntimeController.scenarioId,
				})
			end)
		end
		if out.done == true then
			if out.doneReason == "completed" then
				Finish("completed", "completed")
			elseif out.doneReason == "emergency_stop" then
				Finish("emergency_stop", "emergency_stop")
			else
				Finish("aborted", tostring(out.doneReason or "abort"))
			end
		end
	end)
end

-- Prijem prikazu ze serveru.
remote.OnClientEvent:Connect(function(msg: any)
	if type(msg) ~= "table" then
		return
	end
	if msg.cmd == "Start" then
		StartScenario(tostring(msg.scenarioId or ""), msg.params)
	elseif msg.cmd == "Stop" then
		Finish("stopped", tostring(msg.reason or "server_stop"))
	elseif msg.cmd == "EmergencyStop" then
		if RuntimeController.ctrl ~= nil then
			Driver.EmergencyStop(RuntimeController.ctrl)
		else
			ZeroSeat(RuntimeController.seat)
			remote:FireServer({
				type = "Result",
				scenarioId = RuntimeController.scenarioId,
				outcome = "emergency_stop",
				reason = tostring(msg.reason or "emergency_no_controller"),
				runTime_s = 0,
				distance_studs = 0,
				maxSpeed_studs_s = 0,
				driverVersion = Driver.DRIVER_VERSION,
			})
		end
	elseif msg.cmd == "SetBrakeZone" then
		-- Server oznamuje vjezd do brzdne zony (T03).
		RuntimeController.brakeZone = msg.value == true
	end
end)

-- Prijem briefu od serveroveho harnessu (F4.4 Agent F3): stejny Start jako pres
-- AE_DriverCommands -- usednuti hrace (je-li postava), zadny teleport.
-- Sbernice AE_DriverCommands zustava beze zmen; obe aktivni soucasne.
task.spawn(function()
	local folder = ReplicatedStorage:FindFirstChild(RUN_REMOTES_FOLDER)
	if folder == nil then
		folder = ReplicatedStorage:WaitForChild(RUN_REMOTES_FOLDER, 60)
	end
	if folder == nil then
		return
	end
	local brief = folder:FindFirstChild(RUN_BRIEF_NAME)
	if brief == nil then
		brief = folder:WaitForChild(RUN_BRIEF_NAME, 60)
	end
	if brief == nil or not brief:IsA("RemoteEvent") then
		return
	end
	brief.OnClientEvent:Connect(function(msg: any)
		if type(msg) ~= "table" then
			return
		end
		local sid = msg.scenario_id
		if typeof(sid) ~= "string" or sid == "" then
			return
		end
		local params: { [string]: any }? = nil
		if typeof(msg.params) == "table" then
			params = msg.params
		end
		StartScenario(sid, params)
	end)
end)

-- Pojistka: pri smrti postavy vstupy na nulu (zadny duchovni plyn).
LocalPlayer.CharacterAdded:Connect(function(character: Model)
	character:WaitForChild("Humanoid", 10)
	local hum = character:FindFirstChildOfClass("Humanoid")
	if hum ~= nil then
		hum.Died:Connect(function()
			Finish("aborted", "driver_died")
		end)
	end
end)

-- Pocatecni vyhledani sedadla (bez usednuti; usednuti az na Start).
-- Retry smycka: pracovni kopii vytvari serverovy harness az za behu.
task.spawn(function()
	local t0 = os.clock()
	while RuntimeController.seat == nil and (os.clock() - t0 < 60) do
		RuntimeController.seat = FindDriveSeat()
		if RuntimeController.seat == nil then
			task.wait(1)
		end
	end
end)
