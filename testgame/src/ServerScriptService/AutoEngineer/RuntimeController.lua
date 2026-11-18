-- RuntimeController: tvorba Remotes za behu + prijem VehicleConfig z bridge/inbox
-- + zapis vysledku do bridge/outbox. Zadny staticky Remote v place; vse vznika za behu.

local ServerStorage = game:GetService("ServerStorage")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local HttpService = game:GetService("HttpService")

local Shared = ReplicatedStorage:WaitForChild("AutoEngineer"):WaitForChild("Shared")
local ConfigSchema = require(Shared:WaitForChild("ConfigSchema"))

local RuntimeController = {}

RuntimeController.BRIDGE_NAME = "AutoEngineerBridge"
RuntimeController.REMOTES_NAME = "AutoEngineerRemotes"

function RuntimeController.EnsureBridge(): Folder
	local bridge = ServerStorage:FindFirstChild(RuntimeController.BRIDGE_NAME)
	if bridge == nil then
		bridge = Instance.new("Folder")
		bridge.Name = RuntimeController.BRIDGE_NAME
		bridge.Parent = ServerStorage
	end
	for _, name in { "inbox", "outbox" } do
		if bridge:FindFirstChild(name) == nil then
			local f = Instance.new("Folder")
			f.Name = name
			f.Parent = bridge
		end
	end
	return bridge
end

-- Remotes vznikaji vzdy za behu (idempotentne): zadny vyzadovany predpripraveny objekt.
function RuntimeController.EnsureRemotes(): Folder
	local remotes = ReplicatedStorage:FindFirstChild(RuntimeController.REMOTES_NAME)
	if remotes == nil then
		remotes = Instance.new("Folder")
		remotes.Name = RuntimeController.REMOTES_NAME
		remotes.Parent = ReplicatedStorage
	end
	local defs = {
		{ name = "AERunBrief", class = "RemoteEvent" }, -- server -> klient/driver: start scenare
		{ name = "AETelemetry", class = "RemoteEvent" }, -- server -> sber: stav prubehu
		{ name = "AEStatus", class = "RemoteEvent" }, -- server -> kdokoli: completed/failed
		{ name = "AESubmitConfig", class = "RemoteFunction" }, -- klient/bridge -> server: VehicleConfig JSON
		{ name = "AEDriveCmd", class = "RemoteEvent" }, -- klient -> server: navrh pohonu (server je autorita, F7.1)
	}
	for _, d in defs do
		if remotes:FindFirstChild(d.name) == nil then
			local r = Instance.new(d.class)
			r.Name = d.name
			r.Parent = remotes
		end
	end
	return remotes
end

function RuntimeController.ReadInboxConfig(bridge: Folder, configId: string?): any?
	local inbox = bridge:FindFirstChild("inbox")
	if inbox == nil then
		return nil
	end
	local target: Instance? = nil
	if configId ~= nil then
		target = inbox:FindFirstChild(configId)
	else
		for _, c in inbox:GetChildren() do
			if c:IsA("StringValue") then
				target = c
				break
			end
		end
	end
	if target == nil or not target:IsA("StringValue") then
		return nil
	end
	local ok, decoded = pcall(function()
		return HttpService:JSONDecode(target.Value)
	end)
	if not ok then
		return nil
	end
	local valid, _ = ConfigSchema.Validate(decoded)
	if not valid then
		return nil
	end
	return decoded
end

function RuntimeController.WriteOutboxResult(bridge: Folder, runOutput: any): string
	local outbox = bridge:FindFirstChild("outbox")
	assert(outbox ~= nil, "chybi bridge/outbox")
	local id = tostring(runOutput.run_id or ("run_" .. os.clock()))
	local sv = Instance.new("StringValue")
	sv.Name = id
	local ok, encoded = pcall(function()
		return HttpService:JSONEncode(runOutput)
	end)
	sv.Value = if ok then encoded else "{}"
	sv.Parent = outbox
	return id
end

-- Prijem VehicleConfig pres RemoteFunction (JSON string -> tabulka + validace).
function RuntimeController.BindSubmitConfig(remotes: Folder, onConfig: (any) -> ()): ()
	local rf = remotes:WaitForChild("AESubmitConfig");
	(rf :: RemoteFunction).OnServerInvoke = function(_player: Player?, json: string): any
		local ok, decoded = pcall(function()
			return HttpService:JSONDecode(json)
		end)
		if not ok then
			return { accepted = false, errors = { "neplatny_json" } }
		end
		local valid, errors = ConfigSchema.Validate(decoded)
		if not valid then
			return { accepted = false, errors = errors }
		end
		onConfig(decoded)
		return { accepted = true, config_id = decoded.config_id }
	end
end

-- F7.1: prijem navrhu pohonu od klienta (RemoteEvent, server je autorita).
-- Klient jen NAVRHUJE {throttle 0..1, brake 0..1, steer -1..1, seq, run_id};
-- server validuje (clamp + rostouci seq + rate-limit ~60/s) a teprve pak vola
-- onCmd(player, cmd). Nevalidni vstup = warn + drop (zadny kick, zadny zapis).
function RuntimeController.BindDriveCmd(remotes: Folder, onCmd: (any, any) -> ()): ()
	local ev = remotes:WaitForChild("AEDriveCmd")
	local lastSeq: { [Player]: number } = {}
	local lastTick: { [Player]: number } = {}
	local evTyped = ev :: RemoteEvent
	evTyped.OnServerEvent:Connect(function(player: Player, payload: any)
		if typeof(payload) ~= "table" then
			return
		end
		local p = payload :: any
		if typeof(p.throttle) ~= "number" or typeof(p.brake) ~= "number" or typeof(p.steer) ~= "number" then
			return
		end
		if typeof(p.seq) ~= "number" then
			return
		end
		local now = os.clock()
		local ls = lastSeq[player]
		if ls ~= nil and (p.seq :: number) <= ls then
			return -- stale/duplicitni prikaz
		end
		local lt = lastTick[player]
		if lt ~= nil and (now - lt) < (1 / 60) - 0.001 then
			return -- rate-limit ~60/s
		end
		lastSeq[player] = p.seq :: number
		lastTick[player] = now
		onCmd(player, {
			throttle = math.max(0, math.min(1, p.throttle :: number)),
			brake = math.max(0, math.min(1, p.brake :: number)),
			steer = math.max(-1, math.min(1, p.steer :: number)),
			seq = p.seq,
			run_id = if typeof(p.run_id) == "string" then p.run_id else "",
		})
	end)
end

return RuntimeController
