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

-- F5-B: overeni struktury BEZ Script.Source (Agent B, 2026-11-17).
-- Fakt 1 (live dukaz primo v hernim server-vlakne, sondy AE_CapProbe3/4):
-- cteni i zapis .Source pada chybou "lacking capability PluginOrOpenCloud".
-- V produkci proto NELZE prekotevovat kotvy Initialize/MiscWeld -- zamerne
-- se na Source vubec nesaha (cteni ani zapis).
-- Fakt 2 (live dukaz AE_probe_build, NEOPRAVENY klon do Workspace): puvodni
-- struktura (Initialize/Interface/Plugins/README pod Tune) se POSTAVI --
-- Hinge 40, #AV/#BV 4/4, Plugins:Destroy probehlo, Interface 15 deti.
-- Engine tedy Script pod Tune-ModuleScriptem SPUSTI; presun na koren nebyl
-- nikdy potreba (zameneno s nebehem skriptu ve ServerStorage) a prave presun
-- kotvy rozbil a vynutil si Source-patche. Proto se NIC NEPRESOUVA.
-- Kotvy overeny proti auditu (live zdroje sablony): Initialize L18/L89/L91/
-- L93/L97/L99/L1104/L1106/L1124/L1128/L1247 vyzaduje script.Parent = Tune
-- (ModuleScript s detmi Interface/Plugins/README); Drive L43/L2221 a
-- Controls_AC6 L39 cte car["A-Chassis Tune"].README (README zustava pod
-- Tune); MiscWeld zustava pod Initialize (puvodni 3-hop plati, beze zmeny).
-- Tune je cista data (jediny vyskyt 'script' v celem zdroji je slovo
-- 'description' v komentari L19) -- require(Tune) vraci stejnou tabulku
-- pro Initialize/Drive/Gauges i ReadTune/WriteTune, zadny TuneLink-klon
-- ani synchronizace neni potreba. Sablona zustava nedotcena; overeni je
-- idempotentni (ciste cteni stromu pres FindFirstChild).

-- Overi kotvy puvodni struktury na pracovni kopii (sablonu ani jeji potomky
-- odmitne). NIC NEPRESOUVA, NESAHÁ na Source (F5-B: presun byl zbytecny,
-- kotvy plati v puvodni strukture -- viz komentar vyse). Idempotentni.
-- Vrati true, 0 / false, duvod. Prubeh loguje pres print.
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
	-- Ocekavane deti Tune (kotvy Initialize/Drive/Gauges): vse musi zustat
	-- pod Tune, jinak kotvy script.Parent neplati a build se nepostavi.
	local missing = {}
	for _, name in ipairs({ "A-Chassis Interface", "Initialize", "Plugins", "README" }) do
		local child = tune:FindFirstChild(name)
		if child then
			print(
				string.format(
					"[RepairStructure] %s: '%s' (%s) pod Tune OK",
					vehicle:GetFullName(),
					name,
					child.ClassName
				)
			)
		else
			table.insert(missing, name)
			print(
				string.format(
					"[RepairStructure] %s: VAROVANI: '%s' pod Tune chybi (kotva neplati, bez Source nelze opravit)",
					vehicle:GetFullName(),
					name
				)
			)
		end
	end
	-- MiscWeld zustava pod Initialize: puvodni 3-hop
	-- (MiscWeld -> Initialize -> Tune -> vuz) plati beze zmeny.
	local init = tune:FindFirstChild("Initialize")
	if init and init:IsA("Script") then
		local misc = init:FindFirstChild("MiscWeld")
		if misc then
			print(
				string.format(
					"[RepairStructure] %s: MiscWeld pod Initialize OK (%s, 3-hop beze zmeny)",
					vehicle:GetFullName(),
					misc.ClassName
				)
			)
		else
			table.insert(missing, "MiscWeld")
			print(string.format("[RepairStructure] %s: VAROVANI: MiscWeld pod Initialize chybi", vehicle:GetFullName()))
		end
	else
		table.insert(missing, "Initialize")
		print(
			string.format(
				"[RepairStructure] %s: VAROVANI: Initialize (Script) pod Tune nenalezen",
				vehicle:GetFullName()
			)
		)
	end
	if #missing > 0 then
		return false, "neuplna struktura pod Tune, chybi: " .. table.concat(missing, ", ")
	end
	return true, 0
end

-- Klonuje sablonu jako pracovni kopii s overenou strukturou (RepairStructure).
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
	-- F4.4 M2: atributovy mustek AE_Brake/AE_Throttle/AE_Steer do vstupu Drive
	-- (idempotentni; sablona jiz patchnuta v session => no-op).
	local okB, berr = VehicleManager.ApplyDriveInputBridge(clone)
	if not okB then
		clone:Destroy()
		return nil, berr
	end
	-- F4.4 M2: PrimaryPart = DriveSeat (pouze pracovni kopie). Bez nej je
	-- PivotTo na kloubove sestave (167 dilu, hinge/constraint spoje) osklive
	-- nedefinovane: dily se rozhazuji, vuz konci na boku nebo pada svetem
	-- (overeno live: roll -85.6, pad y=-419). S PrimaryPart je PivotTo
	-- deterministicky (rotace kolem sedadla) a klon dedenim drzi pohromade.
	-- M to delal stejne ("PrimaryPart = DriveSeat, pouze na klonech", F4.3).
	-- Sablona (.rbxm na disku) sahnuta neni; ziva sablona v session ho ma tez
	-- (operator, aby ho dedily i klony stavene starou zivou tabulkou).
	local seat = clone:FindFirstChildWhichIsA("VehicleSeat", true)
	if seat ~= nil then
		pcall(function()
			clone.PrimaryPart = seat
		end)
	end
	return clone
end

-- Explicitni nasazeni opravene pracovni kopie do Workspace (spusti build
-- podvozku pres Initialize). Prijima pouze vystup CloneVehicle.
-- F6-A: po parentu prebinduje serverovy Car.Value na novy klon (Initialize ho
-- nastavi take pri buildu, toto je idempotentni pojistka) a maze stale
-- PlayerGui Interface (mrtvy Drive by jinak psal na zniceny model).
function VehicleManager.DeployVehicle(vehicle)
	if typeof(vehicle) ~= "Instance" then
		return nil, "ocekavan Instance vozidla"
	end
	vehicle.Parent = Workspace
	pcall(function()
		local tune = vehicle:FindFirstChild("A-Chassis Tune", true)
		local iface = tune and tune:FindFirstChild("A-Chassis Interface")
		local carVal = iface and iface:FindFirstChild("Car")
		if carVal and carVal:IsA("ObjectValue") then
			carVal.Value = vehicle
		end
	end)
	VehicleManager.CleanupStaleClientInterfaces(vehicle)
	return vehicle
end

-- F6-A operator-step (pouze MCP, ma capability PluginOrOpenCloud): doplni V2
-- (_PBrake release) do ZIVE sablony v session. Idempotentni (marker V2):
-- obsahuje-li Drive V2, jen doplni atribut; obsahuje-li V1, pripoji V2 za
-- blok V1; jinak vlozi V1+V2 ke kotve. Nikdy nesaha na .rbxm na disku.
-- Klony po tomto kroku dedi V2 a nepotrebuji eject/resit tanec (F6-run-002).
function VehicleManager.EnsureTemplateBridgeV2()
	local template, terr = VehicleManager.ResolveTemplate()
	if not template then
		return false, terr
	end
	local drive = template:FindFirstChild("Drive", true)
	if drive == nil or not drive:IsA("LocalScript") then
		return false, "Drive LocalScript v sablone nenalezen"
	end
	local okRead, src = pcall(function()
		return drive.Source
	end)
	if not okRead or typeof(src) ~= "string" then
		return false, "Drive.Source sablony nelze cist ani s operator capability: " .. tostring(src)
	end
	if string.find(src, VehicleManager.DRIVE_INPUT_BRIDGE_V2_MARKER, 1, true) then
		template:SetAttribute(VehicleManager.TEMPLATE_BRIDGE_ATTR, true)
		return true, "sablona jiz obsahuje V2, atribut AE_BridgeApplied doplnen"
	end
	local v1 = VehicleManager.DRIVE_INPUT_BRIDGE_BLOCK
	local v2 = VehicleManager.DRIVE_INPUT_BRIDGE_V2_BLOCK
	local patched = nil
	local i = string.find(src, v1, 1, true)
	if i ~= nil then
		patched = string.sub(src, 1, i + #v1 - 1) .. "\n" .. v2 .. string.sub(src, i + #v1)
	else
		local anchor = VehicleManager.DRIVE_INPUT_BRIDGE_ANCHOR
		local a = string.find(src, anchor, 1, true)
		if a == nil then
			return false, "kotva Heartbeat/Inputs v Drive sablony nenalezena"
		end
		patched = string.sub(src, 1, a - 1) .. v1 .. "\n" .. v2 .. "\n" .. string.sub(src, a)
	end
	local okWrite, werr = pcall(function()
		drive.Source = patched
	end)
	if not okWrite then
		return false, "Drive.Source sablony nelze zapsat: " .. tostring(werr)
	end
	template:SetAttribute(VehicleManager.TEMPLATE_BRIDGE_ATTR, true)
	return true, "sablona doplnena o V2 (_PBrake release), AE_BridgeApplied=true"
end

-- F6-A: smaze stale klientske A-Chassis Interface v PlayerGui.
-- `keepVehicle` (je-li dan) se nikdy nemaze: jeho Car.Value je aktualni.
-- Stale = Car.Value chybi, ma Parent=nil (zniceny model), nebo neni ve Workspace
-- (dukaz: po DestroyVehicle zustava kopie v PlayerGui a jeji Drive pak kazdy
-- frame hlasi `DriveSeat is not a valid member` a prepisuje motory, F6-run-001).
-- Idempotentni, best-effort (pcall na hrace i instanci); sablona nedotcena.
function VehicleManager.CleanupStaleClientInterfaces(keepVehicle: Instance?): number
	local removed = 0
	pcall(function()
		local players = game:GetService("Players"):GetPlayers()
		for _, p in players do
			pcall(function()
				local gui = p:FindFirstChildOfClass("PlayerGui")
				if gui == nil then
					return
				end
				for _, iface in gui:GetChildren() do
					pcall(function()
						if iface.Name ~= "A-Chassis Interface" then
							return
						end
						local carVal = iface:FindFirstChild("Car")
						local target: Instance? = nil
						if carVal and carVal:IsA("ObjectValue") then
							target = carVal.Value
						end
						if keepVehicle ~= nil and target == keepVehicle then
							return
						end
						local stale = target == nil
						if not stale then
							local okAnc, inWs = pcall(function()
								return (target :: Instance):IsDescendantOf(Workspace)
							end)
							stale = (not okAnc) or (inWs ~= true)
						end
						if stale then
							iface:Destroy()
							removed += 1
						end
					end)
				end
			end)
		end
	end)
	return removed
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
	-- F6-A: az PO zniceni (Car.Value pak ukazuje na Parent=nil -> stale).
	VehicleManager.CleanupStaleClientInterfaces(nil)
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

-- F4.4 M2 / F5-A arbitrace: atributovy mustek AE_Brake / AE_Throttle / AE_Steer do vstupu Drive.
-- Duvod: Drive cte JEN UserInputService (klavesy/gamepad); sedadlo (seat.Throttle)
-- v tomto buildu nefunguje (0 cteni seatu, overeno H1). Serverovy harness/operator
-- nastavi car:SetAttribute("AE_Brake"|"AE_Throttle"|"AE_Steer") a klientsky Drive
-- je v Heartbeat smycce PREBIRA do vstupu, je-li atribut pritomen (cislo): server
-- je pak JEDINY urcujici zapisovac _IBrake/_IThrot/_GSteerT (brzda/plyn/volant).
-- Chybi-li atribut (nil = manualni rezim), klavesy/gamepad zustavaji nedotceny.
-- Rampy _IBrake->_InBrake (BrakeAccel/BrakeDecel) ani ABS logika Drive timto nedotceny
-- (mustek saha jen na surove vstupy _IBrake/_IThrot/_GSteerT pred Inputs(dt)).
-- Vyjimka z pravidla 1 (sablona nedotcena): koordinator M2 autorizoval aplikaci
-- TOTOZNEHO bloku na ZIVOU sablonu v session (nikdy .rbxm na disku); CloneVehicle
-- ho aplikuje na kazdou pracovni kopii (idempotentni).
VehicleManager.DRIVE_INPUT_BRIDGE_MARKER = "AE_DRIVE_INPUT_BRIDGE"
VehicleManager.DRIVE_INPUT_BRIDGE_ANCHOR = "\t\t--Inputs\n\t\tInputs(dt)"
VehicleManager.DRIVE_INPUT_BRIDGE_BLOCK = "\t\t-- AE_DRIVE_INPUT_BRIDGE (F4.4 M2, arbitrace F5-A): atributovy mustek pro bezridicske mereni.\n"
	.. "\t\t-- Server je JEDINY urcujici zapisovac vstupu, je-li atribut pritomen (cislo); nil = manual.\n"
	.. "\t\t-- Rampy _IBrake->_InBrake (BrakeAccel/BrakeDecel) ani ABS logika Drive nedotceny.\n"
	.. "\t\tdo\n"
	.. '\t\t\tlocal _aeBrake = car:GetAttribute("AE_Brake")\n'
	.. '\t\t\tif typeof(_aeBrake) == "number" then\n'
	.. "\t\t\t\t_IBrake = math.max(0, math.min(1, _aeBrake))\n"
	.. "\t\t\tend\n"
	.. '\t\t\tlocal _aeThrot = car:GetAttribute("AE_Throttle")\n'
	.. '\t\t\tif typeof(_aeThrot) == "number" then\n'
	.. "\t\t\t\t_IThrot = math.max(0, math.min(1, _aeThrot))\n"
	.. "\t\t\tend\n"
	.. '\t\t\tlocal _aeSteer = car:GetAttribute("AE_Steer")\n'
	.. '\t\t\tif typeof(_aeSteer) == "number" then\n'
	.. "\t\t\t\t_GSteerT = math.max(-1, math.min(1, _aeSteer))\n"
	.. "\t\t\tend\n"
	.. "\t\tend"

VehicleManager.TEMPLATE_BRIDGE_ATTR = "AE_BridgeApplied"

-- F6-A bridge V2: V1 + release rucni brzdy pri autonomnim rizeni.
-- Drive pri startu latchuje _PBrake=true, najde-li #BV=PBrakeForce (default,
-- ktery stavi Initialize; se zadnim biasem staci zadni kola, PBrakeBias=0).
-- Bez fyzicke klavesy P (End + rychlost>5) by kola zustala zamcena navzdy;
-- atributovy mustek saha jen na _IBrake/_IThrot/_GSteerT.
-- V2 se vklada ZA blok V1 (cti _aeBrake/_aeThrot/_aeSteer, ktere deklaruje V1).
VehicleManager.DRIVE_INPUT_BRIDGE_V2_MARKER = "AE_DRIVE_INPUT_BRIDGE_V2"
VehicleManager.DRIVE_INPUT_BRIDGE_V2_BLOCK = "\t\t-- AE_DRIVE_INPUT_BRIDGE_V2 (F6-A): pri autonomnim rizeni drzet rucni brzdu vyrazenou.\n"
	.. "\t\t-- Drive ji pri startu latchuje z #BV=PBrakeForce defaultu (Initialize); bez klavesy P\n"
	.. "\t\t-- by zustala zaseknuta a kola zamcena (F6-run-002). Manualni rezim (bez atributu) nedotcen.\n"
	.. "\t\tif typeof(_aeBrake) == \"number\" or typeof(_aeThrot) == \"number\" or typeof(_aeSteer) == \"number\" then\n"
	.. "\t\t\t_PBrake = false\n"
	.. "\t\tend"

-- Aplikuje mustek do Drive LocalScriptu vozidla (sablona i pracovni kopie).
-- Idempotentni: obsahuje-li Drive marker, vrati true + "jiz aplikovano".
-- F5-FX2 capability-safe: nejdrive atribut sablony AE_BridgeApplied (bez cteni
-- Source -- klon dedi patchovany Drive z operator-stepu EnsureTemplateBridge);
-- jinak pcall Source read/write s jasnym failem (server-thread bez
-- PluginOrOpenCloud na Source nesmi sahnout, F1.0 auto-fill crash l.531).
function VehicleManager.ApplyDriveInputBridge(vehicle)
	if typeof(vehicle) ~= "Instance" then
		return false, "ocekavan Instance vozidla"
	end
	-- 1) Sablona jiz patchnuta operator-stepem => klon dedi Drive bez Source.
	local tplOk, tplBridged = pcall(function()
		local tpl = VehicleManager.ResolveTemplate()
		if tpl == nil then
			return nil
		end
		return tpl:GetAttribute(VehicleManager.TEMPLATE_BRIDGE_ATTR)
	end)
	if tplOk and tplBridged == true then
		return true, "sablona patchnuta (AE_BridgeApplied), klon dedi Drive bez cteni Source"
	end
	local drive = vehicle:FindFirstChild("Drive", true)
	if drive == nil or not drive:IsA("LocalScript") then
		return false, "Drive LocalScript ve vozidle nenalezen"
	end
	-- 2) Capability-safe cteni Source (server-thread dale jen pres pcall).
	local okRead, src = pcall(function()
		return drive.Source
	end)
	if not okRead or typeof(src) ~= "string" then
		return false,
			"Drive.Source nelze cist v tomto vlakne (chybi capability PluginOrOpenCloud); priprav sablonu operator-stepem EnsureTemplateBridge"
	end
	if string.find(src, VehicleManager.DRIVE_INPUT_BRIDGE_MARKER, 1, true) then
		return true, "jiz aplikovano"
	end
	local anchor = VehicleManager.DRIVE_INPUT_BRIDGE_ANCHOR
	local i = string.find(src, anchor, 1, true)
	if i == nil then
		return false, "kotva Heartbeat/Inputs v Drive nenalezena"
	end
	local patched = string.sub(src, 1, i - 1) .. VehicleManager.DRIVE_INPUT_BRIDGE_BLOCK .. "\n" .. string.sub(src, i)
	local okWrite, werr = pcall(function()
		drive.Source = patched
	end)
	if not okWrite then
		return false,
			"Drive.Source nelze zapsat v tomto vlakne (chybi capability PluginOrOpenCloud); priprav sablonu operator-stepem EnsureTemplateBridge: "
				.. tostring(werr)
	end
	return true, "aplikovano"
end

-- F5-FX2 operator-step (pouze MCP, ma capability PluginOrOpenCloud): aplikuje
-- mustek na ZIVOu sablonu v session a nastavi atribut AE_BridgeApplied.
-- Klony pak prochazeji ApplyDriveInputBridge bez cteni Source (server-thread
-- safe). Idempotentni. Nikdy nesaha na .rbxm na disku.
function VehicleManager.EnsureTemplateBridge()
	local template, terr = VehicleManager.ResolveTemplate()
	if not template then
		return false, terr
	end
	local already = template:GetAttribute(VehicleManager.TEMPLATE_BRIDGE_ATTR)
	if already == true then
		return true, "sablona jiz patchnuta (AE_BridgeApplied)"
	end
	local drive = template:FindFirstChild("Drive", true)
	if drive == nil or not drive:IsA("LocalScript") then
		return false, "Drive LocalScript v sablone nenalezen"
	end
	local okRead, src = pcall(function()
		return drive.Source
	end)
	if not okRead or typeof(src) ~= "string" then
		return false, "Drive.Source sablony nelze cist ani s operator capability: " .. tostring(src)
	end
	if string.find(src, VehicleManager.DRIVE_INPUT_BRIDGE_MARKER, 1, true) then
		template:SetAttribute(VehicleManager.TEMPLATE_BRIDGE_ATTR, true)
		return true, "blok v sablone detekovan, atribut AE_BridgeApplied doplnen"
	end
	local i = string.find(src, VehicleManager.DRIVE_INPUT_BRIDGE_ANCHOR, 1, true)
	if i == nil then
		return false, "kotva Heartbeat/Inputs v Drive sablony nenalezena"
	end
	local patched = string.sub(src, 1, i - 1) .. VehicleManager.DRIVE_INPUT_BRIDGE_BLOCK .. "\n" .. string.sub(src, i)
	local okWrite, werr = pcall(function()
		drive.Source = patched
	end)
	if not okWrite then
		return false, "Drive.Source sablony nelze zapsat: " .. tostring(werr)
	end
	template:SetAttribute(VehicleManager.TEMPLATE_BRIDGE_ATTR, true)
	return true, "sablona patchnuta, AE_BridgeApplied=true"
end

return VehicleManager
