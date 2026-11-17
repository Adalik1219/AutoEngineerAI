-- AutonomousDriver (ModuleScript) -- deterministicky autonomni ridic pro A-Chassis 6C.
-- Vlastnik: Agent D. Faze 9 (Test Environment + Autonomous Driver).
--
-- PURE LOGIKA, ZADNA HERNI API: tento modul nevola game/Workspace/Vector3 ani
-- zadne sluzby. Pracuje pouze s cisly a tabulkami (studs, sekundy), aby sel
-- jednotkove testovat mimo Studio (lune / plain Lua). Vezen varovani: pokud sem
-- nekdo prida game API, rozbije testovatelnost.
--
-- KLICOVY FAKT (docs/A-CHASSIS-AUDIT.md): fyziku A-Chassis 6C pocita KLIENT
-- (Drive LocalScript, Heartbeat ~60 Hz); DriveSeat ma Torque/MaxSpeed/Steer 0
-- a slouzi jen jako sedadlo + vstupni kanal (Throttle/Steer). Ridic proto neridi
-- fyziku ani neteleportuje vozidlo -- pouze vydava vstupy, ktere TestClient
-- predava do existujicich seat-vstupu. Vyjimka: zadna (ani spawn; ten dela server).
--
-- Scenare T01-T07 viz Shared/ScenarioDefinitions.lua (port S1-S7 z
-- docs/TESTING-OPTIMIZATION.md). Rychlosti ve studs/s dle tech definici.
-- Determinismus: stejny (scenarioId, params, dt-sekvence, feedback) => stejna
-- sekvence vystupu. Zadny math.random, zadny wall-clock uvnitr.
--
-- Souradna konvence pro waypoint follower (TestClient ji musi dodrzet):
--   px = Position.X, py = Position.Z, heading = atan2(look.X, look.Z),
--   dopredny vektor = (sin(heading), cos(heading)) v rovine (px, py).
--
-- Jazyk: komentare cesky, identifikatory anglicky.

local AutonomousDriver = {}

AutonomousDriver.DRIVER_VERSION = "1.0.0"

-- Podporovane scenare: druh rizeni + vychozi parametry.
-- kind: "accel" (plynova rampa, rovne), "brake" (cruise + brzdna zona),
--   "circle" (pure pursuit kruh), "lanechange" (replay volantu dle drahy),
--   "pursuit" (pure pursuit obecnych waypointu), "cruise" (regulator + rovne).
AutonomousDriver.SCENARIOS = {
	T01 = { kind = "accel", completeSpeed = 100, coastAfter_s = 3.0, throttleRamp_s = 0.2 },
	T02 = { kind = "accel", completeSpeed = nil, coastAfter_s = 0, throttleRamp_s = 0.2 },
	T03 = { kind = "brake", entrySpeed = 100, brakeRamp_s = 0.15, stopSpeed = 0.1, settleAfter_s = 1.0 },
	T04 = { kind = "circle", targetSpeed = 40, lookahead = 14, radius = 100, arriveRadius = 4 },
	T05 = { kind = "lanechange", entrySpeed = 60, maneuverLength = 120, steerAmp = 0.5 },
	T06 = { kind = "pursuit", targetSpeed = 40, lookahead = 10, arriveRadius = 4 },
	T07 = { kind = "cruise", targetSpeed = 60 },
}

-- Bezpecnostni limity vystupu (A-Chassis cte Throttle/Steer v -1..1).
AutonomousDriver.LIMITS = {
	throttleMin = 0,
	throttleMax = 1,
	brakeMin = 0,
	brakeMax = 1,
	steerMin = -1,
	steerMax = 1,
}

function AutonomousDriver.clamp(v: number, lo: number, hi: number): number
	if v < lo then
		return lo
	end
	if v > hi then
		return hi
	end
	return v
end

-- Linearni rampa 0 -> 1 za rampTime sekund (od t = 0).
function AutonomousDriver.ramp(t: number, rampTime: number): number
	if rampTime <= 0 then
		return 1
	end
	if t <= 0 then
		return 0
	end
	if t >= rampTime then
		return 1
	end
	return t / rampTime
end

-- Obaleni uhlu do (-pi, pi].
function AutonomousDriver.wrapAngle(a: number): number
	local twoPi = 2 * math.pi
	a = a % twoPi
	if a > math.pi then
		return a - twoPi
	end
	return a
end

-- Rychlostni regulator (P-regulator): drzi cilovou rychlost.
-- Vraci throttle 0..1, brake 0..1 (nikdy oboji soucasne).
function AutonomousDriver.SpeedControl(
	currentSpeed: number,
	targetSpeed: number,
	kpT: number?,
	kpB: number?
): (number, number)
	local pT = kpT or 0.08
	local pB = kpB or 0.15
	local err = targetSpeed - currentSpeed
	if err >= 0 then
		return AutonomousDriver.clamp(err * pT, 0, 1), 0
	end
	return 0, AutonomousDriver.clamp(-err * pB, 0, 1)
end

-- Pure pursuit waypoint follower (cista geometrie, zadna fyzika).
-- pose = { x, y, heading } (viz konvence v hlavicce),
-- waypoints = pole { x, y }, lookahead = rozhled v studs.
-- Vraci steer -1..1, index ciloveho bodu, pricnou odchylku (studs).
function AutonomousDriver.PurePursuit(
	pose: { x: number, y: number, heading: number },
	waypoints: { { x: number, y: number } },
	lookahead: number,
	steerGain: number?
): (number, number, number)
	local gain = steerGain or 0.06
	local n = #waypoints
	if n == 0 then
		return 0, 0, 0
	end
	-- Cilovy bod: prvni waypoint dale nez lookahead; jinak posledni.
	local targetIdx = n
	for i = 1, n do
		local dx = waypoints[i].x - pose.x
		local dy = waypoints[i].y - pose.y
		if math.sqrt(dx * dx + dy * dy) >= lookahead then
			targetIdx = i
			break
		end
	end
	local dx = waypoints[targetIdx].x - pose.x
	local dy = waypoints[targetIdx].y - pose.y
	local dist = math.sqrt(dx * dx + dy * dy)
	-- Pricna odchylka: souradnice cile v ramu vozidla (vpred = osa y).
	local alpha = AutonomousDriver.wrapAngle(math.atan2(dx, dy) - pose.heading)
	local crossTrack = 0
	if dist > 1e-6 then
		crossTrack = dist * math.sin(alpha)
	end
	-- Kivivost pure pursuit: k = 2 * sin(alpha) / Ld; rizeni umerne kivivosti.
	local curvature = 0
	if lookahead > 1e-6 then
		curvature = (2 * math.sin(alpha)) / lookahead
	end
	local steer = AutonomousDriver.clamp(curvature / gain, -1, 1)
	return steer, targetIdx, crossTrack
end

-- Generovani kruhovych waypointu (T04 skidpad): stred (cx, cy), polomer r.
function AutonomousDriver.CircleWaypoints(
	cx: number,
	cy: number,
	r: number,
	count: number?
): { { x: number, y: number } }
	local n = count or 32
	local pts = {}
	for i = 1, n do
		local a = (2 * math.pi * (i - 1)) / n
		table.insert(pts, { x = cx + r * math.cos(a), y = cy + r * math.sin(a) })
	end
	return pts
end

-- Replay profil natoceni volantu pro T05 (losi test) jako funkce ujete drahy s.
-- Dvojita zmena pruhu: jedna perioda sinusovky pres maneuverLength (vlevo+vrat).
function AutonomousDriver.LaneChangeSteer(s: number, maneuverLength: number, steerAmp: number): number
	if maneuverLength <= 0 then
		return 0
	end
	if s < 0 or s > maneuverLength then
		return 0
	end
	return steerAmp * math.sin((2 * math.pi * s) / maneuverLength)
end

-- Casove profily plyn/brzda/volant pro primkove scenare (replay, bez zpetne vazby).
-- T01/T02: plny plyn s rampou, volant 0. T03: rizeno stavove (viz step), zde jen brzda.
AutonomousDriver.Profiles = {}

function AutonomousDriver.Profiles.StraightAccel(
	t: number,
	rampTime: number
): { throttle: number, brake: number, steer: number }
	return { throttle = AutonomousDriver.ramp(t, rampTime or 0.2), brake = 0, steer = 0 }
end

function AutonomousDriver.Profiles.FullBrake(
	tBrake: number,
	rampTime: number
): { throttle: number, brake: number, steer: number }
	return { throttle = 0, brake = AutonomousDriver.ramp(tBrake, rampTime or 0.15), steer = 0 }
end

-- Vytvoreni stavoveho ridice pro scenar. params prepisuji vychozi hodnoty
-- (targetSpeed, waypoints, circleCenter, maneuverLength, ...).
-- Vraci ctrl, nebo nil + duvod.
function AutonomousDriver.new(scenarioId: string, params: { [string]: any }?): (any, string?)
	local spec = AutonomousDriver.SCENARIOS[scenarioId]
	if spec == nil then
		return nil, "unknown_scenario:" .. tostring(scenarioId)
	end
	local p = params or {}
	local ctrl = {
		scenarioId = scenarioId,
		kind = spec.kind,
		spec = spec,
		t = 0,
		distance = 0,
		phase = "run",
		phaseT = 0,
		coastT = 0,
		settleT = 0,
		emergency = false,
		done = false,
		doneReason = nil :: string?,
		targetSpeed = p.targetSpeed or spec.targetSpeed or spec.entrySpeed or spec.completeSpeed or 0,
		lookahead = p.lookahead or spec.lookahead or 10,
		steerGain = p.steerGain or 0.06,
		arriveRadius = p.arriveRadius or spec.arriveRadius or 4,
		maneuverLength = p.maneuverLength or spec.maneuverLength or 120,
		steerAmp = p.steerAmp or spec.steerAmp or 0.5,
		kpT = p.kpT,
		kpB = p.kpB,
		waypoints = p.waypoints,
	}
	if ctrl.kind == "circle" and ctrl.waypoints == nil then
		local c = p.circleCenter or { x = 0, y = 0 }
		local r = p.radius or spec.radius or 100
		ctrl.waypoints = AutonomousDriver.CircleWaypoints(c.x, c.y, r, p.circlePoints or 32)
	end
	return ctrl, nil
end

function AutonomousDriver.reset(ctrl): ()
	ctrl.t = 0
	ctrl.distance = 0
	ctrl.phase = "run"
	ctrl.phaseT = 0
	ctrl.coastT = 0
	ctrl.settleT = 0
	ctrl.emergency = false
	ctrl.done = false
	ctrl.doneReason = nil
end

-- Nouzove zastaveni: latch; dalsi step() vraci plnou brzdu + done.
function AutonomousDriver.EmergencyStop(ctrl): ()
	ctrl.emergency = true
end

-- Kontrola abort kriterii z telemetrie (cista funkce).
-- fb = { rollDeg?, nanFlag? }. Vraci duvod, nebo nil (pokracovat).
function AutonomousDriver.CheckAbort(fb: { [string]: any }): string?
	if fb.nanFlag == true then
		return "nan_telemetry"
	end
	local roll = fb.rollDeg
	if type(roll) == "number" and math.abs(roll) > 45 then
		return "rollover"
	end
	return nil
end

-- Jeden krok ridice. fb (feedback, vse cisla):
--   { speed, x, y, heading, rollDeg?, nanFlag?, brakeZone? }
-- Vraci { throttle, brake, steer, done, doneReason } (doneReason nil pokud bezi).
function AutonomousDriver.step(ctrl, dt: number, fb: { [string]: any }): { [string]: any }
	if ctrl.done then
		return { throttle = 0, brake = 1, steer = 0, done = true, doneReason = ctrl.doneReason }
	end
	if ctrl.emergency then
		ctrl.done = true
		ctrl.doneReason = "emergency_stop"
		return { throttle = 0, brake = 1, steer = 0, done = true, doneReason = "emergency_stop" }
	end

	local stepDt = dt
	if type(stepDt) ~= "number" or stepDt <= 0 then
		stepDt = 1 / 60
	end
	ctrl.t += stepDt
	ctrl.phaseT += stepDt

	local speed = tonumber(fb.speed) or 0
	ctrl.distance += math.max(0, speed) * stepDt

	local abort = AutonomousDriver.CheckAbort(fb)
	if abort ~= nil then
		ctrl.done = true
		ctrl.doneReason = abort
		return { throttle = 0, brake = 1, steer = 0, done = true, doneReason = abort }
	end

	local kind = ctrl.kind
	local L = AutonomousDriver.LIMITS

	if kind == "accel" then
		local prof = AutonomousDriver.Profiles.StraightAccel(ctrl.t, ctrl.spec.throttleRamp_s or 0.2)
		local out = { throttle = prof.throttle, brake = 0, steer = 0, done = false, doneReason = nil :: string? }
		local cs = ctrl.spec.completeSpeed
		if cs ~= nil and speed >= cs then
			ctrl.coastT += stepDt
			if ctrl.coastT >= (ctrl.spec.coastAfter_s or 3.0) then
				ctrl.done = true
				ctrl.doneReason = "completed"
				out.done = true
				out.doneReason = "completed"
			end
		else
			ctrl.coastT = 0
		end
		return out
	elseif kind == "brake" then
		if ctrl.phase == "run" then
			-- Prijezd: regulator drzi entrySpeed, volant 0, dokud harness
			-- neoznami brzdnou zonu (fb.brakeZone == true).
			local th, br = AutonomousDriver.SpeedControl(speed, ctrl.spec.entrySpeed or 100, ctrl.kpT, ctrl.kpB)
			if fb.brakeZone == true then
				ctrl.phase = "braking"
				ctrl.phaseT = 0
			end
			return { throttle = th, brake = br, steer = 0, done = false, doneReason = nil :: string? }
		else
			local prof = AutonomousDriver.Profiles.FullBrake(ctrl.phaseT, ctrl.spec.brakeRamp_s or 0.15)
			local out = { throttle = 0, brake = prof.brake, steer = 0, done = false, doneReason = nil :: string? }
			if speed <= (ctrl.spec.stopSpeed or 0.1) then
				ctrl.settleT += stepDt
				if ctrl.settleT >= (ctrl.spec.settleAfter_s or 1.0) then
					ctrl.done = true
					ctrl.doneReason = "completed"
					out.done = true
					out.doneReason = "completed"
				end
			else
				ctrl.settleT = 0
			end
			return out
		end
	elseif kind == "circle" or kind == "pursuit" then
		local pose = {
			x = tonumber(fb.x) or 0,
			y = tonumber(fb.y) or 0,
			heading = tonumber(fb.heading) or 0,
		}
		local wps = ctrl.waypoints or {}
		local steer, _, _ = AutonomousDriver.PurePursuit(pose, wps, ctrl.lookahead, ctrl.steerGain)
		local th, br = AutonomousDriver.SpeedControl(speed, ctrl.targetSpeed, ctrl.kpT, ctrl.kpB)
		local out = {
			throttle = AutonomousDriver.clamp(th, L.throttleMin, L.throttleMax),
			brake = AutonomousDriver.clamp(br, L.brakeMin, L.brakeMax),
			steer = AutonomousDriver.clamp(steer, L.steerMin, L.steerMax),
			done = false,
			doneReason = nil :: string?,
		}
		-- Hotovo pri dojezdu k poslednimu waypointu (slalom T06 / cil).
		if #wps > 0 then
			local last = wps[#wps]
			local dx = last.x - pose.x
			local dy = last.y - pose.y
			if math.sqrt(dx * dx + dy * dy) <= ctrl.arriveRadius and ctrl.distance > 10 then
				ctrl.done = true
				ctrl.doneReason = "completed"
				out.done = true
				out.doneReason = "completed"
			end
		end
		return out
	elseif kind == "lanechange" then
		-- Replay: volant = funkce ujete drahy (identicke vstupy pro kazdou
		-- variantu, viz T05); rychlost drzi regulator.
		local steer = AutonomousDriver.LaneChangeSteer(ctrl.distance, ctrl.maneuverLength, ctrl.steerAmp)
		local th, _ = AutonomousDriver.SpeedControl(speed, ctrl.targetSpeed, ctrl.kpT, ctrl.kpB)
		local out = {
			throttle = AutonomousDriver.clamp(th, L.throttleMin, L.throttleMax),
			brake = 0,
			steer = AutonomousDriver.clamp(steer, L.steerMin, L.steerMax),
			done = false,
			doneReason = nil :: string?,
		}
		if ctrl.distance >= ctrl.maneuverLength then
			ctrl.done = true
			ctrl.doneReason = "completed"
			out.done = true
			out.doneReason = "completed"
		end
		return out
	else -- kind == "cruise" (T07): regulator + rovne.
		local th, br = AutonomousDriver.SpeedControl(speed, ctrl.targetSpeed, ctrl.kpT, ctrl.kpB)
		return {
			throttle = AutonomousDriver.clamp(th, L.throttleMin, L.throttleMax),
			brake = AutonomousDriver.clamp(br, L.brakeMin, L.brakeMax),
			steer = 0,
			done = false,
			doneReason = nil :: string?,
		}
	end
end

return AutonomousDriver
