-- TestHarness (ServerScriptService/AutoEngineer): orchestrace celeho toku z briefu.
-- Tok: bridge/inbox VehicleConfig -> spawn varianty -> T01-T07 (ScenarioRunner +
-- TelemetryCollector 60 Hz) -> per-run vystup -> bridge/outbox + AEStatus Remote.
-- Studio-beh je PENDING (dosud nemereno v Roblox runtime); vystup je mapovatelny
-- na TestResult (mode roblox-runtime) pres Shared.TelemetrySchema.
--
-- WIRING F4.4 (Agent H1):
--   * Slot auto-fill: neni-li AE_VehicleSlot (ServerStorage/workspace), harness
--     sam zalozí variantu CloneVehicle(config_id) -> WriteTune (brzdy z inbox
--     configu, pouze MUTABLE klice) -> DeployVehicle. Bez zmen sablony.
--   * T03 start: CFrame dilu StartLine (TestTrack, x=2) + rychlost 100 studs/s
--     pres AssemblyLinearVelocity vsech BasePartu (DriveSeat explicitne -- Drive
--     cte DriveSeat.Velocity). Viz ScenarioRunner REPORT BRZDA/ABS.
--   * Smycka repetitions = def.repetitions (T03: 3) na config; brake_distance
--     z XZ telemetrie + ABS aktivita do summary kazdeho behu; agregat
--     SUMMARY-<config>-T03 (mean/std/delta, repeatability +/-5 %) do outboxu.

local ServerStorage = game:GetService("ServerStorage")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local NS = ReplicatedStorage:WaitForChild("AutoEngineer")
local Shared = NS:WaitForChild("Shared")

local ScenarioDefinitions = require(Shared:WaitForChild("ScenarioDefinitions"))
local TelemetrySchema = require(Shared:WaitForChild("TelemetrySchema"))

local Self = script.Parent
local ScenarioRunner = require(Self:WaitForChild("ScenarioRunner"))
local TelemetryCollector = require(Self:WaitForChild("TelemetryCollector"))
local RuntimeController = require(Self:WaitForChild("RuntimeController"))
local VehicleManager = require(Self:WaitForChild("VehicleManager"))

local CODE_VERSION = "ae-harness-0.2.1"
local VEHICLE_ID = "ae-test-vehicle"

-- F7.1: mnozina vozidel s aktivnim replay-behem. Prikazy AEDriveCmd pro tato
-- vozidla se ignoruji (autorita je deterministicky replay, ne klient).
-- Klice: vozidlo -> true; cisti se pri konci behu (i pri fail).
local activeVehicles: { [Instance]: boolean } = {}

-- parameters.brakes (VehicleConfig, volny object) -> Tune klice. Pouze MUTABLE_TUNE
-- (VehicleManager); ABSEnabled/TCSEnabled tu ZAMERNE chybi -- nejsou mutable,
-- harness je nezapisuje (default true ze sablony, overeno live Agent H1).
local BRAKE_TUNE_KEYS = {
	"BrakeForce",
	"BrakeBias",
	"BrakeAccel",
	"BrakeDecel",
	"ABSThreshold",
	"EBrakeForce",
	"PBrakeForce",
}

local function findVehicleSlot(): Instance?
	local slot = ServerStorage:FindFirstChild("AE_VehicleSlot")
	if slot == nil then
		slot = workspace:FindFirstChild("AE_VehicleSlot")
	end
	return slot
end

-- Slot auto-fill (F4.4): chybi-li AE_VehicleSlot, zaloz variantu z inbox configu:
-- CloneVehicle(config_id) -> WriteTune (brzdy, pouze MUTABLE klice) -> DeployVehicle.
-- Vraci vozidlo k pouziti, nebo nil + chyby se jiz zapsanymi duvody.
local function ensureVehicle(config: any, errors: { string }): Instance?
	local slot = findVehicleSlot()
	if slot ~= nil then
		return slot
	end
	local configId = if config ~= nil and config.config_id ~= nil then tostring(config.config_id) else "nocfg"
	local clone, cerr = VehicleManager.CloneVehicle(configId)
	if clone == nil then
		table.insert(errors, "auto_fill_clone_selhal:" .. tostring(cerr))
		return nil
	end
	local brakes = if config ~= nil and config.parameters ~= nil then config.parameters.brakes else nil
	if typeof(brakes) ~= "table" then
		table.insert(errors, "config_bez_brakes:zadny_brake_tune_zapsan")
	else
		for _, key in BRAKE_TUNE_KEYS do
			local val = (brakes :: any)[key]
			if val ~= nil then
				if typeof(val) ~= "number" then
					table.insert(errors, "tune_preskocen_typ:" .. key)
				else
					local ok, err = VehicleManager.WriteTune(clone, key, val)
					if not ok then
						table.insert(errors, "tune_zamitnut:" .. key .. ":" .. tostring(err))
					end
				end
			end
		end
	end
	local deployed, derr = VehicleManager.DeployVehicle(clone)
	if deployed == nil then
		table.insert(errors, "auto_fill_deploy_selhal:" .. tostring(derr))
		pcall(function()
			VehicleManager.DestroyVehicle(clone)
		end)
		return nil
	end
	return deployed
end

-- Startovni CFrame T03: dil StartLine v TestTracku (x=2, identita, overeno
-- z TestTrack.rbxmx) + clearance +3 y nad desku (slab y=-0.45, sila 1.1 --
-- bez odsazeni konci kola pod povrchem a solver rychlost sezere, F44-T03-RUNS
-- H1). Orientace: yaw -90° kolem Y, aby CELO vozu mirilo +X po trati.
-- F6-run-002 zive overeno: cumak sleduje LookVector spawnCFrame (s identitou
-- stal celem +Z napric trati, rychlost +X ho tlacila bokem). StartLine ma
-- look -Z; yaw -90° ho stoci na +X. Rychlost dava TRACK_DIR (+X).
-- Fallback: atribut workspace AE_Spawn; pak nil (bez presunu).
local function findT03StartCFrame(): CFrame?
	local found = workspace:FindFirstChild("StartLine", true)
	if found ~= nil and found:IsA("BasePart") then
		return ((found :: BasePart).CFrame * CFrame.Angles(0, -math.pi / 2, 0)) + Vector3.new(0, 3, 0)
	end
	local attr = workspace:GetAttribute("AE_Spawn")
	if typeof(attr) == "CFrame" then
		return attr
	end
	return nil
end

-- Startovni rychlost T03: vsechny BaseParty (DriveSeat explicitne -- Drive cte
-- DriveSeat.Velocity) dostanou AssemblyLinearVelocity = TRACK_DIR * speed.
-- Trat vede podel +X (BrakeLine x=3000); F6: smer je dan geometrii trate,
-- ne orientaci spawnCFrame (ta po yaw-fixu nese RightVector +Z, LookVector +X).
-- LookVector StartLine (0,0,-1) miril napric trati do svodidla (F44-T03-RUNS H1).
-- Rychlost dava TRACK_DIR (ScenarioRunner.T03_TRACK_DIR, +X); F7.1-N3: jediny
-- zdroj smeru trate, zadna duplicitni definice.
local function applyStartSpeed(vehicle: Instance?, _cf: CFrame, speed: number): ()
	if vehicle == nil then
		return
	end
	local v = ScenarioRunner.T03_TRACK_DIR * speed
	for _, d in vehicle:GetDescendants() do
		if d:IsA("BasePart") then
			(d :: BasePart).AssemblyLinearVelocity = v
		end
	end
end

local function isT03(def: any): boolean
	return def ~= nil and def.kind == "straight_brake_100_0"
end

local function entrySpeed(def: any): number
	if def ~= nil and def.initial_conditions ~= nil then
		local s = (def.initial_conditions :: any).speed_studs_s
		if typeof(s) == "number" then
			return s
		end
	end
	return 100
end

-- Outbox StringValue limit je 200 kB; T01-rep (40 s, 60 Hz) mel 1.68 MB
-- (F44-T03-RUNS H1). Cap 200 ulozenych vzorku (~700 B/vzorek => ~140 kB,
-- rezerva na summary + JSON rezii); faktor je adaptivni step = ceil(n/200).
local OUTBOX_SAMPLE_CAP = 200

-- Decimovana kopie behu pro outbox: vzorky se prolozi (plne zustavaji
-- v `output`), summary + brake_distance vzdy (neskrtaji se). Je-li t03 beh,
-- metriky se prepocitaji z ulozenych vzorku (konzistence s prepocetm testu).
local function buildOutboxDoc(output: any, fullSamples: any, recomputeT03: boolean): any
	local kept, step = TelemetryCollector.DecimateForOutbox(fullSamples, OUTBOX_SAMPLE_CAP)
	local summary = (output.measurements :: any).summary
	if recomputeT03 and typeof(summary) == "table" then
		local m, _ = ScenarioRunner.ComputeT03Metrics(kept)
		summary = { duration_s = summary.duration_s, state = summary.state, t03 = m }
	end
	local meas = {
		rate_hz = (output.measurements :: any).rate_hz,
		sample_count = #kept,
		samples = kept,
		summary = summary,
		outbox_decimation = {
			step = step,
			kept_samples = #kept,
			full_samples = if typeof(fullSamples) == "table" then #fullSamples else 0,
		},
	}
	return {
		run_id = output.run_id,
		scenario_id = output.scenario_id,
		vehicle_id = output.vehicle_id,
		config_id = output.config_id,
		timestamp = output.timestamp,
		environment = output.environment,
		measurements = meas,
		completion_status = output.completion_status,
		errors = output.errors,
	}
end

local function runOneScenario(def: any, config: any, bridge: Folder, remotes: Folder, rep: number): (any, any)
	local runId = string.format("RUN-%s-%s-r%d", tostring(config.config_id or "nocfg"), def.scenario_id, rep)
	local runner = ScenarioRunner.new({})
	local collector = TelemetryCollector.new({ rateHz = ScenarioDefinitions.SAMPLE_RATE_HZ })
	local errors: { string } = {}
	local vehicle = ensureVehicle(config, errors)
	collector:SetVehicle(vehicle :: Instance?)
	if vehicle ~= nil then
		activeVehicles[vehicle] = true
	end

	local seed = def.seed or 0
	local spawnCFrame: CFrame? = nil
	if isT03(def) then
		spawnCFrame = findT03StartCFrame()
	else
		local attr = workspace:GetAttribute("AE_Spawn") -- nil => bez presunu
		if typeof(attr) == "CFrame" then
			spawnCFrame = attr
		end
	end
	runner:Spawn(def, runId, vehicle, spawnCFrame)
	-- F5-FX2: Spawn voiduje s duvodem (nulovani vstupu, settle-timeout,
	-- roll pred rychlosti) — takovy beh se nemeri, jen se zapise failed.
	local startFailed: string? = nil
	if runner:GetState() == ScenarioRunner.State.FAILED and runner.failReason ~= nil then
		startFailed = tostring(runner.failReason)
		table.insert(errors, startFailed)
	end
	-- F5 FX D-1: po applyStartSpeed znovu OVERIT rychlost z DriveSeat
	-- (read-back helper ScenarioRunner.ReadDriveSeatXzSpeed); pri neshode
	-- mimo toleranci fail behu s duvodem, ne slepe pokracovani.
	if startFailed == nil and isT03(def) and vehicle ~= nil and spawnCFrame ~= nil then
		local want = entrySpeed(def)
		applyStartSpeed(vehicle, spawnCFrame, want)
		local tol = ScenarioRunner.T03_DEFAULT_ENTRY_TOL
		if def.initial_conditions ~= nil and typeof((def.initial_conditions :: any).entry_tol) == "number" then
			tol = (def.initial_conditions :: any).entry_tol
		end
		local measured = ScenarioRunner.ReadDriveSeatXzSpeed(vehicle)
		if measured == nil then
			startFailed = "entry_speed_neoverena_po_apply:chybi_DriveSeat"
		elseif math.abs(measured - want) > (tol :: number) then
			startFailed = string.format(
				"entry_speed_mimo_toleranci_po_apply:cil=%.1f_tol=%.1f_mereno=%.2f",
				want,
				tol :: number,
				measured
			)
		end
		if startFailed ~= nil then
			table.insert(errors, startFailed)
		end
	end
	(remotes:FindFirstChild("AERunBrief") :: RemoteEvent):FireAllClients({
		run_id = runId,
		scenario_id = def.scenario_id,
	})
	-- F5-FX2 stuck-brake: pred startem mereni EXPLICITNE 0,0,0 + overeni.
	if startFailed == nil and vehicle ~= nil then
		local okZero, zeroErr = ScenarioRunner.ClearDriveInputs(vehicle)
		if not okZero then
			startFailed = tostring(zeroErr)
			table.insert(errors, startFailed)
		end
	end
	collector:Start()
	local t = 0
	local step = 1 / ScenarioDefinitions.SAMPLE_RATE_HZ
	local status = "running"
	-- F5-FX2 first-sample entry check (post-gate bleed, D-2, pouze T03):
	-- prvni platny vzorek musi byt 100±1 (entry_tol defu), jinak void s duvodem.
	local firstChecked = false
	if startFailed ~= nil then
		status = "failed"
		runner.failReason = startFailed
	end
	while status == "running" do
		task.wait(step)
		t += step
		local throttle, brake, steer = runner:DriverInputs(t)
		ScenarioRunner.WriteDriveAttributes(vehicle, throttle, brake, steer, def.kind)
		collector:SetInputs(throttle, brake, steer)
		local sample = collector:SampleOnce(t)
		if sample == nil then
			table.insert(errors, "chybi_merici_part")
		end
		if not firstChecked and isT03(def) and sample ~= nil and typeof(sample.vel) == "table" then
			firstChecked = true
			local v0 = ScenarioRunner.XzSpeed(sample.vel)
			if v0 ~= nil then
				local want = entrySpeed(def)
				local ftol = ScenarioRunner.T03_DEFAULT_ENTRY_TOL
				if def.initial_conditions ~= nil and typeof((def.initial_conditions :: any).entry_tol) == "number" then
					ftol = (def.initial_conditions :: any).entry_tol
				end
				if math.abs(v0 - want) > (ftol :: number) then
					local fsReason = string.format(
						"first_sample_mimo_toleranci:cil=%.1f_tol=%.1f_mereno=%.2f",
						want,
						ftol :: number,
						v0
					)
					table.insert(errors, fsReason)
					status = "failed"
					runner.failReason = fsReason
					break
				end
			end
		end
		status = runner:Evaluate(sample or {}, def, t)
	end

	runner:Finish(status, runner.failReason, vehicle)
	collector:Stop()
	-- F5-FX2 stuck-brake: na konci behu EXPLICITNE 0,0,0 + overeni, pak teprve
	-- nil (navrat do manualniho rezimu; _IBrake zustane na 0, ne zaseknuta 1.0).
	if vehicle ~= nil then
		local okEnd, endErr = ScenarioRunner.ClearDriveInputs(vehicle)
		if not okEnd then
			table.insert(errors, tostring(endErr))
		end
	end
	ScenarioRunner.WriteDriveAttributes(vehicle, nil, nil, nil)

	local completion = if status == "completed" and startFailed == nil then "completed" else "failed"
	if runner.failReason ~= nil then
		table.insert(errors, tostring(runner.failReason))
	end
	-- T03: metriky z XZ telemetrie + ABS aktivita do summary behu.
	local t03metrics: any? = nil
	if isT03(def) then
		local m, merr = ScenarioRunner.ComputeT03Metrics(collector.samples)
		if m ~= nil then
			t03metrics = m
			if m.stopped ~= true then
				table.insert(errors, "nezastaveno_do_timeout")
			end
		else
			table.insert(errors, "t03_metriky_selhaly:" .. tostring(merr))
		end
	end
	local output = collector:GetRunOutput({
		run_id = runId,
		scenario_id = def.scenario_id,
		vehicle_id = VEHICLE_ID,
		config_id = config.config_id,
		seed = seed,
		code_version = CODE_VERSION,
		completion_status = completion,
		errors = errors,
		summary = { duration_s = t, state = runner:GetState(), t03 = t03metrics },
	})
	local ok, _ = TelemetrySchema.ValidateRun(output)
	if not ok then
		table.insert(errors, "neplatny_run_vystup")
		output.errors = errors
	end
	-- Outbox (StringValue limit 200 kB, F44-T03-RUNS H1): uloz decimovanou
	-- kopii; plne vzorky + plne metriky zustavaji v navratu behu.
	-- T03 metriky se pro outbox PREPOCITAJI z ulozenych (decimovanych) vzorku,
	-- aby nezavisly prepocet v test_f44_regression.py sedel na 3 des. mista.
	-- Summary (duration_s, state, t03) se NESKRTA, jen vzorky.
	-- F5 FX C-1: outbox-doc (kept) se vraci jako druha hodnota; runBrief z nej
	-- agreguje SUMMARY, aby sedel exaktne s test_summary_aggregate (f55+).
	local outboxDoc = buildOutboxDoc(output, collector.samples, isT03(def))
	RuntimeController.WriteOutboxResult(bridge, outboxDoc);
	(remotes:FindFirstChild("AEStatus") :: RemoteEvent):FireAllClients({ run_id = runId, status = completion })
	if vehicle ~= nil then
		activeVehicles[vehicle] = nil
	end
	return output, outboxDoc
end

-- Agregace T03 serie (repetitions na config): mean/std/min/max brake_distance,
-- delta_pct = (max-min)/mean*100, repeatability_ok (delta <= 5 % a vse zastaveno).
-- Zapis SUMMARY-<config_id>-T03 do outboxu (tvar kompatibilni s ValidateRun).
local function writeT03Summary(
	bridge: Folder,
	config: any,
	def: any,
	distances: { number },
	runIds: { string },
	allStopped: boolean
): ()
	local n = #distances
	if n == 0 then
		return
	end
	local sum = 0
	local mn = distances[1]
	local mx = distances[1]
	for _, d in distances do
		sum += d
		mn = math.min(mn, d)
		mx = math.max(mx, d)
	end
	local mean = sum / n
	local var = 0
	for _, d in distances do
		var += (d - mean) * (d - mean)
	end
	local std = math.sqrt(var / n)
	local deltaPct = if mean > 0 then (mx - mn) / mean * 100 else nil
	local repeatOk = allStopped and deltaPct ~= nil and (deltaPct :: number) <= 5
	local errors: { string } = {}
	if not allStopped then
		table.insert(errors, "nektere_behy_nezastavily")
	end
	if deltaPct ~= nil and (deltaPct :: number) > 5 then
		table.insert(errors, "rozptyl_drahy_nad_5_pct")
	end
	local summaryObj = {
		run_id = string.format("SUMMARY-%s-T03", tostring(config.config_id or "nocfg")),
		type = "t03_summary",
		scenario_id = def.scenario_id,
		vehicle_id = VEHICLE_ID,
		config_id = config.config_id,
		timestamp = DateTime.now():ToIsoDate(),
		environment = {
			mode = "roblox-runtime",
			seed = def.seed or 0,
			code_version = CODE_VERSION,
		},
		measurements = {
			rate_hz = ScenarioDefinitions.SAMPLE_RATE_HZ,
			sample_count = 0,
			samples = {},
			summary = {
				n = n,
				run_ids = runIds,
				brake_distance_mean_studs = mean,
				brake_distance_std_studs = std,
				brake_distance_min_studs = mn,
				brake_distance_max_studs = mx,
				brake_distance_delta_pct = deltaPct,
				repeatability_ok = repeatOk,
			},
		},
		completion_status = if repeatOk then "completed" else "failed",
		errors = errors,
	}
	RuntimeController.WriteOutboxResult(bridge, summaryObj)
end

-- F4.4 F3: vyber scenaru z inbox configu (volitelny; default vsechny T01-T07).
-- Podporuje `scenario_ids` (pole) nebo `scenario_id` (jedno ID). Neplatna ci
-- neznama ID se preskakuji; je-li vysledek prazdny, plati default (plny brief).
local function resolveScenarioIds(config: any): { string }?
	if config == nil then
		return nil
	end
	local wanted: { string } = {}
	local seen: { [string]: boolean } = {}
	local function take(sid: any)
		if typeof(sid) == "string" and not seen[sid] and ScenarioDefinitions.Get(sid) ~= nil then
			seen[sid] = true
			table.insert(wanted, sid)
		end
	end
	local ids = (config :: any).scenario_ids
	if typeof(ids) == "table" then
		for _, sid in ids do
			take(sid)
		end
	else
		take((config :: any).scenario_id)
	end
	if #wanted == 0 then
		return nil
	end
	return wanted
end

local function runBrief(config: any, scenarioIds: { string }?): { any }
	local bridge = RuntimeController.EnsureBridge()
	local remotes = RuntimeController.EnsureRemotes()
	local ids = scenarioIds or ScenarioDefinitions.ListIds()
	local results = {}
	for _, sid in ids do
		local def = ScenarioDefinitions.Get(sid)
		if def == nil then
			continue
		end
		local reps = 3
		if typeof(def.repetitions) == "number" and (def.repetitions :: number) >= 1 then
			reps = math.floor(def.repetitions :: number)
		end
		local distances: { number } = {}
		local runIds: { string } = {}
		local allStopped = true
		for r = 1, reps do
			local out, outboxDoc = runOneScenario(def, config, bridge, remotes, r)
			table.insert(results, out)
			if isT03(def) then
				table.insert(runIds, tostring(out.run_id))
				-- F5 FX C-1: SUMMARY se agreguje z kept-vzorku outboxu (stejnych,
				-- ktere validuje test_summary_aggregate), ne z plneho navratu
				-- runOneScenario -- viz DecimateForOutbox ("agregace vzdy z kept").
				local t03 = if typeof(outboxDoc) == "table"
						and typeof(outboxDoc.measurements) == "table"
						and typeof(outboxDoc.measurements.summary) == "table"
					then (outboxDoc.measurements.summary :: any).t03
					else nil
				if typeof(t03) == "table" and typeof(t03.brake_distance_studs) == "number" then
					table.insert(distances, t03.brake_distance_studs)
					if t03.stopped ~= true then
						allStopped = false
					end
				else
					allStopped = false
				end
			end
		end
		if isT03(def) then
			writeT03Summary(bridge, config, def, distances, runIds, allStopped)
		end
	end
	return results
end

-- Start: bridge + remotes za behu; brief z inboxu (prvni StringValue), jinak cekani na AESubmitConfig.
local function main(): ()
	local bridge = RuntimeController.EnsureBridge()
	local remotes = RuntimeController.EnsureRemotes()
	RuntimeController.BindSubmitConfig(remotes, function(config: any)
		task.spawn(function()
			runBrief(config, resolveScenarioIds(config))
		end)
	end)
	-- F7.1: zive rizeni mimo replay-beh (Solo rig; vice hracu = BLOCKED, viz E).
	-- Replay smycka je autorita: pri aktivnim behu se klientsky navrh ignoruje.
	RuntimeController.BindDriveCmd(remotes, function(_player: any, cmd: any)
		local vehicle = findVehicleSlot()
		if vehicle == nil then
			return
		end
		if activeVehicles[vehicle] == true then
			return
		end
		ScenarioRunner.WriteDriveAttributes(vehicle, cmd.throttle, cmd.brake, cmd.steer, "manual")
	end)
	local pending = RuntimeController.ReadInboxConfig(bridge, nil)
	if pending ~= nil then
		task.spawn(function()
			runBrief(pending, resolveScenarioIds(pending))
		end)
	end
end

main()
