-- TelemetrySchema: validace vzorku/behu + mapovani na TestResult (mode roblox-runtime).
-- Chybejici volitelne hodnoty (RPM, prevod) = nil; nikdy se nevymysleji.

local TelemetrySchema = {}

TelemetrySchema.SCHEMA_VERSION = "1.0.0"
TelemetrySchema.MODE = "roblox-runtime"

local REQUIRED_SAMPLE = { "t", "pos", "vel", "accel", "yaw_rate", "inputs" }
local REQUIRED_RUN = {
	"run_id",
	"scenario_id",
	"vehicle_id",
	"config_id",
	"timestamp",
	"environment",
	"measurements",
	"completion_status",
	"errors",
}

function TelemetrySchema.ValidateSample(sample: any): (boolean, { string })
	local errors: { string } = {}
	if typeof(sample) ~= "table" then
		return false, { "vzorek_neni_tabulka" }
	end
	for _, key in REQUIRED_SAMPLE do
		if sample[key] == nil then
			table.insert(errors, "chybi_vzorek:" .. key)
		end
	end
	return #errors == 0, errors
end

function TelemetrySchema.ValidateRun(run: any): (boolean, { string })
	local errors: { string } = {}
	if typeof(run) ~= "table" then
		return false, { "beh_neni_tabulka" }
	end
	for _, key in REQUIRED_RUN do
		if run[key] == nil then
			table.insert(errors, "chybi_beh:" .. key)
		end
	end
	if typeof(run.environment) == "table" then
		if run.environment.mode ~= TelemetrySchema.MODE then
			table.insert(errors, "spatny_mode:" .. tostring(run.environment.mode))
		end
		if run.environment.seed == nil then
			table.insert(errors, "chybi_environment.seed")
		end
		if run.environment.code_version == nil then
			table.insert(errors, "chybi_environment.code_version")
		end
	end
	return #errors == 0, errors
end

-- Mapovani behu na TestResult (contracts/test_result.schema.json).
function TelemetrySchema.ToTestResult(run: any, extra: any): any
	extra = extra or {}
	local metrics = {}
	if typeof(run.measurements) == "table" then
		if typeof(run.measurements.summary) == "table" then
			metrics = run.measurements.summary
		elseif typeof(run.measurements) == "table" and run.measurements.samples ~= nil then
			metrics = { sample_count = #run.measurements.samples }
		else
			metrics = { sample_count = 0 }
		end
	end
	return {
		schema_version = "1.0.0",
		result_id = extra.result_id or ("tr_" .. tostring(run.run_id)),
		config_id = run.config_id,
		scenario_id = run.scenario_id,
		environment = {
			mode = TelemetrySchema.MODE,
			seed = run.environment.seed,
			code_version = run.environment.code_version,
		},
		metrics = metrics,
		deviations_vs_target = extra.deviations_vs_target or {},
		score = extra.score or 0,
		reproduced_runs = extra.reproduced_runs or 1,
		raw_telemetry_ref = extra.raw_telemetry_ref or ("telemetry/" .. tostring(run.run_id) .. ".json"),
	}
end

return TelemetrySchema
