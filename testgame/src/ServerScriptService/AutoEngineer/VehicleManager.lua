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

-- F4.3-HR: oprava struktury sablony za behu (Agent HR, 2026-11-17).
-- Pricina: vsechny A-Chassis skripty (Drive LocalScript, Initialize Script,
-- Plugins/*, Simulated) jsou v sablone potomky ModuleScriptu 'A-Chassis Tune'
-- a engine je proto nespousti ('lacking capability', overeno live vypisem
-- vsech LuaSourceContainer s cestami). Sablona zustava nedotcena (bitova
-- kopie originalu); oprava se deje POUZE na pracovni kopii vznikle Clone.
-- RepairStructure presune cele podstromy 'A-Chassis Interface', 'Initialize',
-- 'Plugins' a 'README' zpod Tune na koren kopie; jejich vzajemne relativni
-- vazby (sourozenci pod spolecnym rodicem) zustavaji zachovany, Tune tabulka
-- se nemeni, nic se nemaze. Dve kotvy Initialize, ktere ukazovaly na Tune
-- jako rodice (car=script.Parent.Parent; require(script.Parent)), se prekotvi
-- na koren kopie (car=script.Parent; require Tune jmenem) — bez toho by
-- Initialize po presunu vyzadoval Model misto ModuleScriptu a build by
-- neprobehl. Overene zavislosti (live, Server): Drive cte Tune pres
-- require(car["A-Chassis Tune"]) a sourozence Car/Values/IsOn pod Interface
-- (presunem celeho Interface nedotceno); Gauges pres
-- require(car["A-Chassis Tune"].README) (README presunuto vedle Tune).
VehicleManager.REPAIR_MOVE_NAMES = {
	"A-Chassis Interface",
	"Initialize",
	"Plugins",
	"README",
}

local function plainReplaceOnce(s, from, to)
	local i, j = string.find(s, from, 1, true)
	if not i then
		return s, false
	end
	return string.sub(s, 1, i - 1) .. to .. string.sub(s, j + 1), true
end

-- Presune cele podstromy zpod Tune-ModuleScriptu na koren pracovni kopie
-- (sablonu ani jeji potomky odmitne). Idempotentni: jiz presunute preskoci.
-- Vrati true, pocet presunu / false, duvod. Prubeh loguje pres print.
function VehicleManager.RepairStructure(vehicle)
	if typeof(vehicle) ~= "Instance" then
		return false, "ocekavan Instance vozidla"
	end
	local templatesFolder = VehicleManager.ResolveTemplatesFolder()
	if templatesFolder and (vehicle == templatesFolder or vehicle:IsDescendantOf(templatesFolder)) then
		return false, "odmitnuto: sablonu neopravovat (pouze pracovni kopie)"
	end
	local template = VehicleManager.ResolveTemplate()
	if template and vehicle == template then
		return false, "odmitnuto: cil je sablona JeepTemplate"
	end
	local tune = vehicle:FindFirstChild(VehicleManager.TUNE_MODULE_NAME)
	if not tune or not tune:IsA("ModuleScript") then
		return false, "Tune ModuleScript (A-Chassis Tune) v kopii nenalezen"
	end
	local moved = 0
	for _, name in ipairs(VehicleManager.REPAIR_MOVE_NAMES) do
		local child = tune:FindFirstChild(name)
		if child then
			child.Parent = vehicle
			moved += 1
			print(string.format("[RepairStructure] %s: '%s' (%s) presunuto na koren kopie",
				vehicle:GetFullName(), name, child.ClassName))
		else
			local already = vehicle:FindFirstChild(name)
			if already then
				print(string.format("[RepairStructure] %s: '%s' jiz na koreni (%s), preskoceno",
					vehicle:GetFullName(), name, already.ClassName))
			else
				print(string.format("[RepairStructure] %s: VAROVANI: '%s' nenalezeno ani pod Tune ani na koreni",
					vehicle:GetFullName(), name))
			end
		end
	end
	-- Prekotveni dvou kotev Initialize na koren kopie (pouze klon, sablona
	-- sahnuta neni). Zbytek Initialize (WaitForChild Interface/Plugins/README,
	-- script.Parent["A-Chassis Interface"], script.Parent.Plugins) po presunu
	-- cele ctverice na koren plati beze zmeny.
	local init = vehicle:FindFirstChild("Initialize")
	if init and init:IsA("Script") then
		local src = init.Source
		local patched = 0
		local out, hit = plainReplaceOnce(src,
			"local car=script.Parent.Parent",
			"local car=script.Parent")
		if hit then
			src = out
			patched += 1
		end
		out, hit = plainReplaceOnce(src,
			"local _Tune=require(script.Parent)",
			"local _Tune=require(script.Parent[\"A-Chassis Tune\"])")
		if hit then
			src = out
			patched += 1
		end
		if patched > 0 then
			init.Source = src
		end
		print(string.format("[RepairStructure] %s: Initialize kotvy prekotevny: %d/2",
			vehicle:GetFullName(), patched))
		-- MiscWeld (ModuleScript, potomek Initialize) kotvi vuz tremi hoppy
		-- (MiscWeld -> Initialize -> Tune -> vuz); po presunu staci dva
		-- (MiscWeld -> Initialize -> vuz). Bez toho by MiscWeld cetl
		-- car = Workspace a navzdy visel na Workspace:WaitForChild("Misc").
		local misc = init:FindFirstChild("MiscWeld")
		if misc then
			local msrc = misc.Source
			local mout, mhit = plainReplaceOnce(msrc,
				"car = script.Parent.Parent.Parent",
				"car = script.Parent.Parent")
			if mhit then
				misc.Source = mout
			end
			print(string.format("[RepairStructure] %s: MiscWeld kotva: %s",
				vehicle:GetFullName(), mhit and "prekotevena" or "nenalezena (beze zmeny)"))
		else
			print(string.format("[RepairStructure] %s: VAROVANI: MiscWeld pod Initialize nenalezen",
				vehicle:GetFullName()))
		end
	else
		print(string.format("[RepairStructure] %s: VAROVANI: Initialize (Script) na koreni nenalezen",
			vehicle:GetFullName()))
	end
	return true, moved
end

-- Klonuje sablonu jako pracovni kopii s opravenou strukturou (RepairStructure).
-- ZAMERNE NEPARENTUJE do Workspace: Initialize stavi podvozek pri vstupu do
-- Workspace a cte Tune pres require, takze spravne poradi je
-- CloneVehicle -> WriteTune -> DeployVehicle. Nasazeni: DeployVehicle.
-- Original (sablona) zustava nedotcen; original rbxm neni ve stromu hry.
function VehicleManager.CloneVehicle(configId)
	local template, err = VehicleManager.ResolveTemplate()
	if not template then
		return nil, err
	end
	local clean = sanitizeConfigId(configId)
	local clone = template:Clone()
	clone.Name = string.format("Jeep_%s", clean)
	local ok, rerr = VehicleManager.RepairStructure(clone)
	if not ok then
		clone:Destroy()
		return nil, rerr
	end
	return clone
end

-- Explicitni nasazeni opravene pracovni kopie do Workspace (spusti build
-- podvozku pres Initialize). Prijima pouze vystup CloneVehicle.
function VehicleManager.DeployVehicle(vehicle)
	if typeof(vehicle) ~= "Instance" then
		return nil, "ocekavan Instance vozidla"
	end
	vehicle.Parent = Workspace
	return vehicle
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
