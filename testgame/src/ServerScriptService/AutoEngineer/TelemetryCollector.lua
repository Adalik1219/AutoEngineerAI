-- TelemetryCollector: vzorkovani 60 Hz do bufferu (Heartbeat akumulator).
-- Per-run vystup: run_id, scenario_id, vehicle_id, config_id, timestamp,
-- environment, measurements, completion_status, errors.
-- RPM/prevod cte z A-Chassis Values, pokud existuji; jinak nil (null), nikdy vymysl.

local RunService = game:GetService("RunService")

local TelemetryCollector = {}
TelemetryCollector.__index = TelemetryCollector

local RATE_HZ = 60
local WINDOW = 5 -- klouzavy prumer zrychleni pres >=5 vzorku

local function readValues(vehicle: Instance): any
	if vehicle == nil then
		return nil
	end
	-- A-Chassis Values ziji v A-Chassis Interface (ScreenGui) nebo primo ve vozidle.
	local found = vehicle:FindFirstChild("Values", true)
	return found
end

local function readNumber(parent: Instance?, name: string): number?
	if parent == nil then
		return nil
	end
	local child = parent:FindFirstChild(name)
	if child == nil then
		return nil
	end
	if child:IsA("NumberValue") or child:IsA("IntValue") then
		return child.Value
	end
	return nil
end

local function readBool(parent: Instance?, name: string): boolean?
	if parent == nil then
		return nil
	end
	local child = parent:FindFirstChild(name)
	if child == nil then
		return nil
	end
	if child:IsA("BoolValue") then
		return child.Value
	end
	return nil
end

local function readString(parent: Instance?, name: string): string?
	if parent == nil then
		return nil
	end
	local child = parent:FindFirstChild(name)
	if child ~= nil and child:IsA("StringValue") then
		return child.Value
	end
	return nil
end

function TelemetryCollector.new(opts: any): any
	local self = setmetatable({}, TelemetryCollector)
	opts = opts or {}
	self.rateHz = opts.rateHz or RATE_HZ
	self.maxSamples = opts.maxSamples or (self.rateHz * 120)
	self.samples = {}
	self.collecting = false
	self.accum = 0
	self.conn = nil
	self.vehicle = nil
	self.inputs = { throttle = 0, brake = 0, steer = 0 }
	self.prevVel = nil
	self.accelWindow = {}
	return self
end

function TelemetryCollector:SetVehicle(vehicle: Instance?)
	self.vehicle = vehicle
end

function TelemetryCollector:SetInputs(throttle: number, brake: number, steer: number)
	self.inputs.throttle = throttle
	self.inputs.brake = brake
	self.inputs.steer = steer
end

function TelemetryCollector:PrimaryPart(): BasePart?
	if self.vehicle == nil then
		return nil
	end
	if self.vehicle:IsA("Model") then
		local m = self.vehicle :: Model
		if m.PrimaryPart ~= nil then
			return m.PrimaryPart
		end
		return m:FindFirstChildWhichIsA("BasePart")
	end
	if self.vehicle:IsA("BasePart") then
		return self.vehicle
	end
	return nil
end

function TelemetryCollector:SampleOnce(t: number): any?
	local part = self:PrimaryPart()
	if part == nil then
		return nil
	end
	local pos = part.Position
	local vel = part.AssemblyLinearVelocity
	local angVel = part.AssemblyAngularVelocity
	local yawRate = angVel.Y

	-- Zrychleni: derivace rychlosti + klouzavy prumer (surove i filtrovane).
	local dt = 1 / self.rateHz
	local rawAccel = nil
	if self.prevVel ~= nil then
		rawAccel = (vel - self.prevVel) / dt
	end
	self.prevVel = vel
	local filtAccel = nil
	if rawAccel ~= nil then
		table.insert(self.accelWindow, rawAccel)
		if #self.accelWindow > WINDOW then
			table.remove(self.accelWindow, 1)
		end
		local sum = Vector3.zero
		for _, a in self.accelWindow do
			sum += a
		end
		filtAccel = sum / #self.accelWindow
	end

	local _, yaw, roll = part.CFrame:ToOrientation()
	-- Roll: kloneni kolem podelne osy X pri facing +X = Z-slozka ToOrientation
	-- (stejna konvence jako ScenarioRunner.ReadStartRollDeg; zivi Evaluate roll_gt_45).
	local values = readValues(self.vehicle)
	local rpm = readNumber(values, "RPM")
	local gear = readNumber(values, "Gear") or readNumber(values, "GearNum")
	if gear == nil then
		local gs = readString(values, "Gear")
		gear = if gs ~= nil then tonumber(gs) else nil
	end
	-- ABS signaly (A-Chassis Drive, overeno live Agent H1): Drive kazdy frame
	-- zapisuje Values.ABS (BoolValue, stav _ABS: default z _Tune.ABSEnabled,
	-- prepinatelny klavesou ToggleABS) a Values.ABSActive (BoolValue, true prave
	-- kdyz _ABS a brzda a prokluz kol nad _Tune.ABSThreshold). Chybi-li Values
	-- ve vozidle (Drive nebezi / sablona bez Values), je vysledkem nil => null,
	-- nikdy se nevymysli; duvod hlasi ScenarioRunner.ComputeT03Metrics.
	local absEnabled = readBool(values, "ABS")
	local absActive = readBool(values, "ABSActive")

	local sample = {
		t = t,
		pos = { x = pos.X, y = pos.Y, z = pos.Z },
		vel = { x = vel.X, y = vel.Y, z = vel.Z },
		accel_raw = if rawAccel ~= nil then { x = rawAccel.X, y = rawAccel.Y, z = rawAccel.Z } else nil,
		accel = if filtAccel ~= nil then { x = filtAccel.X, y = filtAccel.Y, z = filtAccel.Z } else nil,
		yaw_rate = yawRate,
		yaw = yaw,
		roll_deg = math.deg(roll), -- vzdy cislo (CFrame); chybi jen v legacy exportech f44
		rpm = rpm, -- nil => null, neni-li ve Values
		gear = gear, -- nil => null
		abs_enabled = absEnabled, -- nil => null, neni-li Values.ABS
		abs_active = absActive, -- nil => null, neni-li Values.ABSActive
		inputs = { throttle = self.inputs.throttle, brake = self.inputs.brake, steer = self.inputs.steer },
	}
	return sample
end

function TelemetryCollector:Start(): ()
	if self.collecting then
		return
	end
	self.samples = {}
	self.accelWindow = {}
	self.prevVel = nil
	self.accum = 0
	self.collecting = true
	local clock = 0
	self.conn = RunService.Heartbeat:Connect(function(dt: number)
		if not self.collecting then
			return
		end
		self.accum += dt
		clock += dt
		local step = 1 / self.rateHz
		while self.accum >= step do
			self.accum -= step
			if #self.samples < self.maxSamples then
				local s = self:SampleOnce(clock)
				if s ~= nil then
					table.insert(self.samples, s)
				end
			end
		end
	end)
end

function TelemetryCollector:Stop(): ()
	self.collecting = false
	if self.conn ~= nil then
		self.conn:Disconnect()
		self.conn = nil
	end
end

function TelemetryCollector:Clear(): ()
	self.samples = {}
	self.accelWindow = {}
	self.prevVel = nil
end

function TelemetryCollector:GetRunOutput(ctx: any): any
	return {
		run_id = ctx.run_id,
		scenario_id = ctx.scenario_id,
		vehicle_id = ctx.vehicle_id,
		config_id = ctx.config_id,
		timestamp = DateTime.now():ToIsoDate(),
		environment = {
			mode = "roblox-runtime",
			seed = ctx.seed,
			code_version = ctx.code_version or "dev",
			place_version = ctx.place_version,
			physics = ctx.physics,
		},
		measurements = {
			rate_hz = self.rateHz,
			sample_count = #self.samples,
			samples = self.samples,
			summary = ctx.summary,
		},
		completion_status = ctx.completion_status or "unknown",
		errors = ctx.errors or {},
	}
end

-- Decimace vzorku pro outbox (StringValue limit 200 kB, F44-T03-RUNS H1).
-- Plna telemetrie zustava v behu (self.samples / navrat runOneScenario);
-- do outboxu se uklada kazdy step-ty vzorek (vzdy prvni + posledni).
-- maxKept=200 => ~140 kB pri ~700 B/vzorek (T01 40 s: step 12; T03: step 2).
-- Summary + metriky se NEskrtaji; T03 metriky volajici prepocita z ulozenych
-- (decimovanych) vzorku, aby nezavisly prepocet v test_f44_regression.py sedel.
-- Vraci (decimovane_vzorky, step).
--
-- F5-C (Agent C): konzistence SUMMARY vs run-docs (defekt 5, F44-T03-FINAL §4.5).
-- Zvolena varianta "agregace vzdy z kept" (mensi zasah nez podminena decimace:
-- plne T03-behy maji ~1000-2000 vzorku >> 200 kB, takze podminena decimace by
-- je stejne decimovala a full-vs-kept nesoulad by zustal). Pravidlo: run-doc
-- metriky i SUMMARY agregat se pocitaji ZE STEJNYCH kept-vzorku, kanonickou
-- implementaci ScenarioRunner.ComputeT03Metrics. Handoff (vlastnik TestHarness):
-- runBrief agreguje distances z kept/outbox t03 (navrat buildOutboxDoc), ne
-- z plneho navratu runOneScenario. Kohortova politika testu:
-- test_f44_regression.py (f44 = legacy tolerance, f55+ = exaktne).
function TelemetryCollector.DecimateForOutbox(samples: any, maxKept: number): ({ any }, number)
	if typeof(samples) ~= "table" or #samples == 0 then
		return {}, 1
	end
	maxKept = math.max(2, math.floor(maxKept or 200))
	if #samples <= maxKept then
		return samples, 1
	end
	local step = math.ceil(#samples / maxKept)
	local kept: { any } = { samples[1] }
	for i = 1 + step, #samples, step do
		table.insert(kept, samples[i])
	end
	if kept[#kept] ~= samples[#samples] then
		table.insert(kept, samples[#samples])
	end
	return kept, step
end

return TelemetryCollector
