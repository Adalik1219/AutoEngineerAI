-- ScenarioRunner: stavovy automat scenare IDLE -> SPAWN -> RUNNING -> COMPLETED / FAILED.
-- Ridic je deterministicky replay (plyn/brzda/volant jako funkce casu + def. rampy).

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
end

-- Spawn faze: synchronni reset vozidla na startovni CFrame, nulove rychlosti, ustaleni.
function ScenarioRunner:Spawn(def: any, runId: string, vehicle: Instance?, spawnCFrame: CFrame?): (boolean, string?)
	self.def = def
	self.runId = runId
	self.state = ScenarioRunner.State.SPAWN
	self.t = 0
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

return ScenarioRunner
