-- ConfigSchema: validace VehicleConfig v runtime (lehka zrcadlova kontrola
-- contracts/vehicle_config.schema.json). Chybejici pole = null v telemetrii, nikdy vymyslene.

local ConfigSchema = {}

ConfigSchema.SCHEMA_VERSION = "1.0.0"
ConfigSchema.ID_PATTERN = "^cfg_[A-Za-z0-9_]+$"

local REQUIRED_TOP =
	{ "schema_version", "config_id", "vehicle_profile_id", "chassis_adapter", "parameters", "rationale" }
local REQUIRED_PARAMS = { "engine", "transmission", "tires", "suspension", "steering", "brakes", "geometry_overrides" }

function ConfigSchema.Validate(config: any): (boolean, { string })
	local errors: { string } = {}
	if typeof(config) ~= "table" then
		return false, { "config_neni_tabulka" }
	end
	for _, key in REQUIRED_TOP do
		if config[key] == nil then
			table.insert(errors, "chybi_pole:" .. key)
		end
	end
	if config.schema_version ~= nil and config.schema_version ~= ConfigSchema.SCHEMA_VERSION then
		table.insert(errors, "spatna_schema_version:" .. tostring(config.schema_version))
	end
	if config.config_id ~= nil and not string.match(tostring(config.config_id), ConfigSchema.ID_PATTERN) then
		table.insert(errors, "spatne_config_id:" .. tostring(config.config_id))
	end
	if typeof(config.parameters) == "table" then
		for _, key in REQUIRED_PARAMS do
			if config.parameters[key] == nil then
				table.insert(errors, "chybi_parameters:" .. key)
			end
		end
	else
		table.insert(errors, "parameters_neni_tabulka")
	end
	return #errors == 0, errors
end

return ConfigSchema
