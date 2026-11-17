-- TestHarness (ServerScriptService/AutoEngineer): orchestrace celeho toku z briefu.
-- Tok: bridge/inbox VehicleConfig -> spawn varianty -> T01-T07 (ScenarioRunner +
-- TelemetryCollector 60 Hz) -> per-run vystup -> bridge/outbox + AEStatus Remote.
-- Studio-beh je PENDING (dosud nemereno v Roblox runtime); vystup je mapovatelny
-- na TestResult (mode roblox-runtime) pres Shared.TelemetrySchema.

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

local CODE_VERSION = "ae-harness-0.1.0"
local VEHICLE_ID = "ae-test-vehicle"

local function findVehicleSlot(): Instance?
	local slot = ServerStorage:FindFirstChild("AE_VehicleSlot")
	if slot == nil then
		slot = workspace:FindFirstChild("AE_VehicleSlot")
	end
	return slot
end

local function runOneScenario(def: any, config: any, bridge: Folder, remotes: Folder, index: number): any
	local runId = string.format("RUN-%s-%s-%02d", tostring(config.config_id or "nocfg"), def.scenario_id, index)
	local runner = ScenarioRunner.new({})
	local collector = TelemetryCollector.new({ rateHz = ScenarioDefinitions.SAMPLE_RATE_HZ })
	local vehicle = findVehicleSlot()
	collector:SetVehicle(vehicle :: Instance?)

	local seed = def.seed or 0
	local spawnCFrame = workspace:GetAttribute("AE_Spawn") -- nil => bez presunu
	if typeof(spawnCFrame) == "CFrame" then
		runner:Spawn(def, runId, vehicle, spawnCFrame)
	else
		runner:Spawn(def, runId, vehicle, nil)
	end
	(remotes:FindFirstChild("AERunBrief") :: RemoteEvent):FireAllClients({
		run_id = runId,
		scenario_id = def.scenario_id,
	})
	collector:Start()

	local t = 0
	local step = 1 / ScenarioDefinitions.SAMPLE_RATE_HZ
	local status = "running"
	local errors: { string } = {}
	while status == "running" do
		task.wait(step)
		t += step
		local throttle, brake, steer = runner:DriverInputs(t)
		collector:SetInputs(throttle, brake, steer)
		local sample = collector:SampleOnce(t)
		if sample == nil then
			table.insert(errors, "chybi_merici_part")
		end
		status = runner:Evaluate(sample or {}, def, t)
	end
	runner:Finish(status, runner.failReason)
	collector:Stop()

	local completion = if status == "completed" then "completed" else "failed"
	if runner.failReason ~= nil then
		table.insert(errors, tostring(runner.failReason))
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
		summary = { duration_s = t, state = runner:GetState() },
	})
	local ok, _ = TelemetrySchema.ValidateRun(output)
	if not ok then
		table.insert(errors, "neplatny_run_vystup")
		output.errors = errors
	end
	RuntimeController.WriteOutboxResult(bridge, output);
	(remotes:FindFirstChild("AEStatus") :: RemoteEvent):FireAllClients({ run_id = runId, status = completion })
	return output
end

local function runBrief(config: any, scenarioIds: { string }?): { any }
	local bridge = RuntimeController.EnsureBridge()
	local remotes = RuntimeController.EnsureRemotes()
	local ids = scenarioIds or ScenarioDefinitions.ListIds()
	local results = {}
	for i, sid in ids do
		local def = ScenarioDefinitions.Get(sid)
		if def == nil then
			continue
		end
		table.insert(results, runOneScenario(def, config, bridge, remotes, i))
	end
	return results
end

-- Start: bridge + remotes za behu; brief z inboxu (prvni StringValue), jinak cekani na AESubmitConfig.
local function main(): ()
	local bridge = RuntimeController.EnsureBridge()
	local remotes = RuntimeController.EnsureRemotes()
	RuntimeController.BindSubmitConfig(remotes, function(config: any)
		task.spawn(function()
			runBrief(config)
		end)
	end)
	local pending = RuntimeController.ReadInboxConfig(bridge, nil)
	if pending ~= nil then
		task.spawn(function()
			runBrief(pending)
		end)
	end
end

main()
