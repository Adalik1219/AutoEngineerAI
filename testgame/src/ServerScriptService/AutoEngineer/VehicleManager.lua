-- VehicleManager (ModuleScript)
-- Server-side sprava pracovnich kopii vozidla Jeep (A-Chassis 6C).
-- Vlastnik: Agent C. Zdroj pravdy pro Tune klice: src/Chassis/catalog/parameters.json.
--
-- Pravidla:
--   1. Nikdy nemodifikuje sablonu (JeepTemplate ve VehicleTemplates).
--   2. Pracuje pouze s klony ve Workspace (pracovni kopie s config_id v nazvu).
--   3. Tune cteni/zapis POUZE pro klice kategorie MUTABLE_TUNE.
--   4. Read-only / script-controlled / structure / unknown klice odmita s duvodem.
--   5. Kazdy uspesny zapis si pamatuje puvodni hodnotu pro rollback.

local ServerStorage = game:GetService("ServerStorage")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Workspace = game:GetService("Workspace")

local VehicleManager = {}

VehicleManager.TEMPLATE_NAME = "JeepTemplate"
VehicleManager.TEMPLATES_FOLDER_NAME = "VehicleTemplates"
VehicleManager.TUNE_MODULE_NAME = "A-Chassis Tune"

-- Mnozina MUTABLE_TUNE klicu (82 polozek, generovano z parameters.json, F4.3 live-rekonciliace).
local MUTABLE_TUNE_SET = {
	ABSThreshold = true,
	Ackerman = true,
	AutoDownThresh = true,
	AutoShiftMode = true,
	AutoShiftType = true,
	AutoUpThresh = true,
	AxleDensity = true,
	AxleSize = true,
	BrakeAccel = true,
	BrakeBias = true,
	BrakeDecel = true,
	BrakeForce = true,
	CGHeight = true,
	Clutch = true,
	ClutchEngage = true,
	ClutchKick = true,
	Config = true,
	CurveMult = true,
	DifferentialType = true,
	EBrakeForce = true,
	Electric = true,
	Engine = true,
	EqPoint = true,
	FDMult = true,
	FDiffCoast = true,
	FDiffPower = true,
	FDiffPreload = true,
	FGyroDamp = true,
	FGyroDampening = true,
	FSusDamping = true,
	FSusStiffness = true,
	FWSteer = true,
	FWheelDensity = true,
	FinalDrive = true,
	Flywheel = true,
	Horsepower = true,
	IdleRPM = true,
	IdleThrottle = true,
	InclineComp = true,
	LockToLock = true,
	MSteerExp = true,
	MinSteer = true,
	PBrakeForce = true,
	PeakRPM = true,
	PeakSharpness = true,
	RDiffPreload = true,
	RGyroDamp = true,
	RGyroDampening = true,
	RPMEngage = true,
	RSusDamping = true,
	RSusStiffness = true,
	RWheelDensity = true,
	Ratios = true,
	Redline = true,
	ReturnSpeed = true,
	RevAccel = true,
	RevBounce = true,
	RevDecay = true,
	ShiftDnTime = true,
	ShiftUpTime = true,
	SpeedEngage = true,
	Stall = true,
	SteerDecay = true,
	SteerRatio = true,
	SteerSpeed = true,
	SteeringType = true,
	Superchargers = true,
	SusRadius = true,
	T2_BoostLag = true,
	TCSGradient = true,
	TCSLimit = true,
	TCSThreshold = true,
	T_Boost = true,
	T_BoostLag = true,
	ThrotAccel = true,
	ThrotDecel = true,
	TorqueVector = true,
	TransModes = true,
	Turbochargers = true,
	Weight = true,
	WeightBSize = true,
	WeightDist = true,
}

-- Zname odmitane klice mimo MUTABLE_TUNE s duvodem (dle katalogu F4.3):
-- READ_ONLY (3), SCRIPT_CONTROLLED (7), STRUCTURE_CONTROLLED (2), UNKNOWN (3),
-- PREJMENOVANO (15).
local DENY_REASONS = {
	["ElecRedline/ElecTransition2"] = "READ_ONLY: Gauges cte jine nazvy nez Tune (audit §15); nezapisovat",
	FWLgcyDensity = "READ_ONLY: mrtva non-PGS vetev, klic v live Tune neexistuje (audit §10, §17.4, F4.3)",
	RWLgcyDensity = "READ_ONLY: mrtva non-PGS vetev, klic v live Tune neexistuje (audit §10, §17.4, F4.3)",
	DownforceF = "SCRIPT_CONTROLLED: pritlak F je konstanta ve skriptu Aerodynamics, mimo Tune (audit §13)",
	DownforceR = "SCRIPT_CONTROLLED: pritlak R je konstanta ve skriptu Aerodynamics, mimo Tune (audit §13)",
	Drag = "SCRIPT_CONTROLLED: odpor je konstanta v Aerodynamics, mimo Tune (audit §13)",
	TargetFriction = "SCRIPT_CONTROLLED: adheze je v Simulated._WHEELTUNE, mimo Tune (audit §10, §16)",
	WearSpeed = "SCRIPT_CONTROLLED: opotrebeni je v Simulated._WHEELTUNE, mimo Tune (audit §10)",
	WheelLockRatio = "SCRIPT_CONTROLLED: pomer lock-rezimu je v Simulated, mimo Tune (audit §10)",
	WheelspinRatio = "SCRIPT_CONTROLLED: pomer prokluzu je v Simulated, mimo Tune (audit §10)",
	WheelRadius = "STRUCTURE_CONTROLLED: polomer kol je geometrie dilu, ne parametr Tune (audit §10, katalog)",
	Wheelbase = "STRUCTURE_CONTROLLED: rozvor/rozchod je geometrie, mimo Tune (audit §1, katalog)",
	StAxisOffset = "UNKNOWN: klic v live Tune CHYBI, Initialize:171 ho cte -> runtime error (audit §9, §17.1, F4.3)",
	CompressionRatio = "UNKNOWN: klic auditem potvrzen jen ve vzorci HP_T, hodnota v katalogu null (audit §5, katalog)",
	Bias = "PREJMENOVANO: genericky klic neexistuje -> zapis BrakeBias (F4.3 live Tune)",
	Damping = "PREJMENOVANO: genericky klic neexistuje -> zapis FSusDamping / RSusDamping (F4.3 live Tune)",
	Stiffness = "PREJMENOVANO: genericky klic neexistuje -> zapis FSusStiffness / RSusStiffness (F4.3 live Tune)",
	Preload = "PREJMENOVANO: genericky klic neexistuje -> zapis FDiffPreload / RDiffPreload (F4.3 live Tune)",
	SlipThres = "PREJMENOVANO: klic stareho difu -> zapis FDiffSlipThres / RDiffSlipThres / CDiffSlipThres (F4.3 live Tune)",
	LockThres = "PREJMENOVANO: klic stareho difu -> zapis FDiffLockThres / RDiffLockThres / CDiffLockThres (F4.3 live Tune)",
	SusLength = "PREJMENOVANO: genericky klic neexistuje -> zapis FSusLength / RSusLength (F4.3 live Tune)",
	PreCompress = "PREJMENOVANO: genericky klic neexistuje -> zapis FPreCompress / RPreCompress (F4.3 live Tune)",
	ExtensionLim = "PREJMENOVANO: genericky klic neexistuje -> zapis FExtensionLim / RExtensionLim (F4.3 live Tune)",
	CompressLim = "PREJMENOVANO: genericky klic neexistuje -> zapis FCompressLim / RCompressLim (F4.3 live Tune)",
	SusAngle = "PREJMENOVANO: genericky klic neexistuje -> zapis FSusAngle / RSusAngle (F4.3 live Tune)",
	AnchorOffset = "PREJMENOVANO: genericky klic neexistuje -> zapis FAnchorOffset / RAnchorOffset (F4.3 live Tune)",
	["Bias(PBrake)?"] = "PREJMENOVANO: odhad nazvu -> zapis PBrakeBias, hodnota 0 overena behem (F4.3 live Tune)",
	["RDiffPower?"] = "PREJMENOVANO: odhad nazvu -> zapis RDiffPower (F4.3 live Tune)",
	["RDiffCoast?"] = "PREJMENOVANO: odhad nazvu -> zapis RDiffCoast (F4.3 live Tune)",
	SusCoilPending = "UNKNOWN: viz FSus*/RSus* zaznamy - dekod float-lane nepotvrzen (audit §1, katalog PENDING)",
}

-- Originalni hodnoty pro rollback: [vehicle] -> { [key] = deepCopy(hodnoty) }.
local Originals = {}

local function deepCopy(value, seen)
	if typeof(value) ~= "table" then
		return value
	end
	seen = seen or {}
	if seen[value] then
		return seen[value]
	end
	local copy = {}
	seen[value] = copy
	for k, v in pairs(value) do
		copy[deepCopy(k, seen)] = deepCopy(v, seen)
	end
	return copy
end

local function sanitizeConfigId(configId)
	if typeof(configId) ~= "string" then
		configId = tostring(configId)
	end
	local clean = string.gsub(configId, "[^%w%-_]", "_")
	if clean == "" then
		clean = "default"
	end
	return clean
end

-- Najde slozku VehicleTemplates (ServerStorage primarne, ReplicatedStorage zalozne).
function VehicleManager.ResolveTemplatesFolder()
	local folder = ServerStorage:FindFirstChild(VehicleManager.TEMPLATES_FOLDER_NAME)
	if folder then
		return folder
	end
	folder = ReplicatedStorage:FindFirstChild(VehicleManager.TEMPLATES_FOLDER_NAME)
	if folder then
		return folder
	end
	return nil
end

-- Vrati nedotcenou sablonu (nikdy ji nemodifikovat, pouze klonovat).
function VehicleManager.ResolveTemplate()
	local folder = VehicleManager.ResolveTemplatesFolder()
	if not folder then
		return nil, "chybi slozka VehicleTemplates (ServerStorage ani ReplicatedStorage)"
	end
	local template = folder:FindFirstChild(VehicleManager.TEMPLATE_NAME)
	if not template then
		return nil, "chybi sablona JeepTemplate ve VehicleTemplates"
	end
	return template
end

-- Klonuje sablonu do Workspace jako pracovni kopii s config_id v nazvu.
-- Original (sablona) zustava nedotcena; original rbxm neni ve stromu hry.
function VehicleManager.CloneVehicle(configId)
	local template, err = VehicleManager.ResolveTemplate()
	if not template then
		return nil, err
	end
	local clean = sanitizeConfigId(configId)
	local clone = template:Clone()
	clone.Name = string.format("Jeep_%s", clean)
	clone.Parent = Workspace
	return clone
end

-- Bezpecne odstrani POUZE pracovni kopii z Workspace.
-- Odmitne smazani sablony nebo cehokoliv uvnitr VehicleTemplates.
function VehicleManager.DestroyVehicle(vehicle)
	if typeof(vehicle) ~= "Instance" then
		return false, "ocekavan Instance vozidla"
	end
	local templatesFolder = VehicleManager.ResolveTemplatesFolder()
	if templatesFolder and (vehicle == templatesFolder or vehicle:IsDescendantOf(templatesFolder)) then
		return false, "odmitnuto: cil je sablona nebo jeji potomek (chrani se original)"
	end
	local template = VehicleManager.ResolveTemplate()
	if template and vehicle == template then
		return false, "odmitnuto: cil je sablona JeepTemplate"
	end
	if vehicle.Parent ~= Workspace and not vehicle:IsDescendantOf(Workspace) then
		return false, "odmitnuto: mazu pouze pracovni kopie ve Workspace"
	end
	Originals[vehicle] = nil
	vehicle:Destroy()
	return true
end

-- Najde Tune ModuleScript ("A-Chassis Tune") uvnitr kopie vozidla.
function VehicleManager.ResolveTune(vehicle)
	if typeof(vehicle) ~= "Instance" then
		return nil, "ocekavan Instance vozidla"
	end
	local tune = vehicle:FindFirstChild(VehicleManager.TUNE_MODULE_NAME, true)
	if tune and tune:IsA("ModuleScript") then
		return tune
	end
	return nil, "Tune ModuleScript (A-Chassis Tune) v kopii nenalezen"
end

function VehicleManager.IsMutable(key)
	return MUTABLE_TUNE_SET[key] == true
end

function VehicleManager.DenyReason(key)
	if MUTABLE_TUNE_SET[key] then
		return nil
	end
	local known = DENY_REASONS[key]
	if known then
		return known
	end
	return "UNKNOWN: klic neni v MUTABLE_TUNE katalogu (odmitnuto, zapis povolen pouze dle parameters.json)"
end

-- Precte hodnotu Tune klice z kopie. Povoleno pouze pro MUTABLE_TUNE.
function VehicleManager.ReadTune(vehicle, key)
	if typeof(key) ~= "string" or key == "" then
		return false, "prazdny klic"
	end
	if not VehicleManager.IsMutable(key) then
		return false, VehicleManager.DenyReason(key)
	end
	local tuneModule, err = VehicleManager.ResolveTune(vehicle)
	if not tuneModule then
		return false, err
	end
	local ok, tuneTable = pcall(require, tuneModule)
	if not ok then
		return false, "require Tune selhalo: " .. tostring(tuneTable)
	end
	if typeof(tuneTable) ~= "table" then
		return false, "Tune nevraci tabulku"
	end
	return true, deepCopy(tuneTable[key])
end

-- Zapise hodnotu Tune klice do kopie. Povoleno pouze pro MUTABLE_TUNE.
-- Puvodni hodnota se uklada pro rollback (pouze prvni zapis klice).
-- POZOR: zmena se projevi pri stavbe podvozku (Initialize cte Tune pres require);
-- zapis do jiz postavenych runtime instanci (kola, motory) se nepropaguje automaticky.
function VehicleManager.WriteTune(vehicle, key, value)
	if typeof(key) ~= "string" or key == "" then
		return false, "prazdny klic"
	end
	if not VehicleManager.IsMutable(key) then
		return false, VehicleManager.DenyReason(key)
	end
	local tuneModule, err = VehicleManager.ResolveTune(vehicle)
	if not tuneModule then
		return false, err
	end
	local ok, tuneTable = pcall(require, tuneModule)
	if not ok then
		return false, "require Tune selhalo: " .. tostring(tuneTable)
	end
	if typeof(tuneTable) ~= "table" then
		return false, "Tune nevraci tabulku"
	end
	local perVehicle = Originals[vehicle]
	if not perVehicle then
		perVehicle = {}
		Originals[vehicle] = perVehicle
	end
	if perVehicle[key] == nil then
		perVehicle[key] = deepCopy(tuneTable[key])
	end
	tuneTable[key] = value
	return true
end

-- Vrati vsechny zmenene klice kopie do puvodnich hodnot. Vrati pocet obnovenych klicu.
function VehicleManager.Rollback(vehicle)
	local perVehicle = Originals[vehicle]
	if not perVehicle then
		return 0
	end
	local tuneModule, err = VehicleManager.ResolveTune(vehicle)
	if not tuneModule then
		return 0, err
	end
	local ok, tuneTable = pcall(require, tuneModule)
	if not ok or typeof(tuneTable) ~= "table" then
		return 0, "require Tune selhalo"
	end
	local count = 0
	for key, original in pairs(perVehicle) do
		tuneTable[key] = deepCopy(original)
		count += 1
	end
	Originals[vehicle] = nil
	return count
end

-- Vrati serazeny seznam vsech MUTABLE_TUNE klicu (82 polozek dle katalogu F4.3).
function VehicleManager.GetMutableKeys()
	local keys = {}
	for key, _ in pairs(MUTABLE_TUNE_SET) do
		table.insert(keys, key)
	end
	table.sort(keys)
	return keys
end

return VehicleManager
