-- ScenarioRunner: stavovy automat scenare IDLE -> SPAWN -> RUNNING -> COMPLETED / FAILED.
-- Ridic je deterministicky replay (plyn/brzda/volant jako funkce casu + def. rampy).
--
-- REPORT BRZDA/ABS (Agent H1, overeno live ctenim Drive zdroje v Play session,
-- Server datamodel, pouze cteni; zadny spawn, zadny zapis):
--   Zdroj: ...VehicleTemplates.JeepTemplate."A-Chassis Tune"."A-Chassis Interface".Drive
--   (LocalScript, 1178 radku).
--   OVERENA FAKTA:
--   (a) Brzda je SAMOSTATNY vstup 0..1 (NENI zaporny Throttle). Retezec:
--       _IBrake (klavesa Brake/Brake2 nebo gamepad osa, 0/1) -> vyhlazeni
--       _InBrake rampami _Tune.BrakeAccel (nabeh) / _Tune.BrakeDecel (dobeh)
--       -> podle smeru jizdy _GBrake -> `local brake = _GBrake`.
--   (b) Brzdny moment na kolo: MotorMaxTorque =
--       (F/RBrakeForce * (60/fps) * brake * tqABS) + EBrakeForce-slozka +
--       PBrakeForce-slozka; FBrakeForce/RBrakeForce = BrakeForce*BrakeBias
--       resp. BrakeForce*(1-BrakeBias). Live Tune: BrakeForce=2500,
--       BrakeBias=0.6, BrakeAccel=0.2, BrakeDecel=0.5.
--   (c) ABS: `_ABS = _Tune.ABSEnabled` (live default true) + toggle klavesou
--       ToggleABS za jizdy. Aktivace: `_ABS and brake>0 and
--       |RotVelocity*(size.x/2) - Velocity| - ABSThreshold > 0` => tqABS=0
--       (brzdny moment se vypne); `_ABSActive = (tqABS<1)`. Live ABSThreshold=20.
--       Signaly: Values.ABS (BoolValue, stav) a Values.ABSActive (BoolValue,
--       aktivita) -- cte TelemetryCollector jako abs_enabled/abs_active.
--       ABSEnabled NENI v MUTABLE_TUNE (VehicleManager) => harness ho nezapisuje;
--       spoleha na default true ze sablony.
--   (d) VYVRACENY PREDPOKLAD [P] z TestClient.client.lua: Drive v tomto buildu
--       NIKDE necte seat.Throttle/seat.Steer (0 vyskytu) -- cte pouze
--       UserInputService/gamepad. Mapovani `seat.Throttle = -brake` tedy brzdu
--       fyzicky nepusti; serverovy replay v TestHarness pouze loguje vstupy do
--       telemetrie, skutecnou aplikaci resi klientsky ridic (Agent D).
--   (e) Trat (TestTrack.rbxmx, overeno): StartLine x=2, BrakeLine x=3000.
--       Replay T03 brzi od t=0 (deterministicky, dle ScenarioDefinitions);
--       propojeni brzdy s prekrocenim BrakeLine je PENDING (vyzaduje
--       rozhodnuti vlastnika scenaru, ScenarioDefinitions nevlastnim).

local ScenarioRunner = {}
-- F7.1-inline: ServerDrive (server-autoritativni pohon, verny port A-Chassis
-- Drive Build 6C) je primo zde, protoze Rojo sync NOVYCH souboru do Studia je
-- nespolehlivy (ServerDrive.lua jako samostatny ModuleScript nedotekl).
-- Duvod: klientsky Drive bezi, ale jeho zapisy #AV/#BV se na serverem
-- vlastnenych dilech NEAPLIKUI (F6-D). Server proto pocita stejny retezec:
-- rampa _IThrot->_GThrot, _GoalRPM/_RPM/_WheelRPM, spojka, Auto-shift (Speed),
-- krivka CurveN + twin-turbo, tqOUT na #AV, brzda+EBrake+tqABS na #BV.
-- Odchylky od Drive (dokumentovane, zadna teleport/velocity nahrada):
--  D1 _TMode je vzdy "Auto" (server nema manualni vstupy).
--  D2 Launch: _CGear==0 + plyn + stani -> 1 (Drive New-vers to neresi;
--     Old-vers to delal; bez toho by vuz nikdy nevyjel).
--  D3 DCT cekani pres casova razitka (zadne wait() v server ticku).
--  D4 _ClPressing = (neutral nebo shifting); manualni spojka neni.
--  D5 Stall/chcipnuti mimo rozsah (_IsOn=true, AutoStart); revMin=IdleRPM.
--  D6 PBrakeV=0 v autonomnim rezimu (parita V2 _PBrake=false).
--  D7 Delnyk nulou u _CGear==0 v ClutchModulate je hlidan (Drive by dal NaN).
--  D8 Zadny wait(), zadny spawn, zadny zapis CFrame/Velocity -- jen #AV/#BV.
-- Stav je per-vozidlo (Reset pri ClearDriveInputs / konci behu).
-- Aktualni hodnoty Tune se ctou live pres require (stejne jako Drive).
local ServerDrive = {}
ServerDrive.__index = ServerDrive

ServerDrive._states = {}
ServerDrive._guardWarned = {}
-- F7.1-T01B diagnostika: pocet ticku bez jedineho #AV (rozliseni
-- "pohon nedodaval" vs "pohon dodaval, vuz stal" pri analyze outlieru).
ServerDrive._noavTicks = {}

local function sdReadTune(vehicle: Instance?): any?
	if vehicle == nil then
		return nil
	end
	local ok, tune = pcall(function()
		local t = (vehicle :: Instance):FindFirstChild("A-Chassis Tune", true)
		if t == nil or not (t :: Instance):IsA("ModuleScript") then
			return nil
		end
		return require(t :: ModuleScript)
	end)
	if not ok or typeof(tune) ~= "table" then
		return nil
	end
	return tune
end

local function sdReadWheels(vehicle: Instance?): { BasePart }
	local out: { BasePart } = {}
	pcall(function()
		local wheels = (vehicle :: Instance):FindFirstChild("Wheels", true)
		if wheels == nil then
			return
		end
		for _, w in wheels:GetChildren() do
			if w:IsA("BasePart") then
				table.insert(out, w)
			end
		end
	end)
	return out
end

local function sdReadSeat(vehicle: Instance?): VehicleSeat?
	local seat: VehicleSeat? = nil
	pcall(function()
		seat = (vehicle :: Instance):FindFirstChild("DriveSeat", true) :: any
		if seat ~= nil and not (seat :: any):IsA("VehicleSeat") then
			seat = nil
		end
	end)
	return seat
end

local function sdCurveN(rpmThousands: number, p: any): number
	local hp = p.hp
	local peak = p.peak
	local sharp = p.sharp
	local cmult = p.cmult
	return ((-(rpmThousands - peak) ^ 2) * math.min(hp / (peak ^ 2), cmult ^ (peak / hp)) + hp)
		* (rpmThousands - ((rpmThousands ^ sharp) / (sharp * peak ^ (sharp - 1))))
end

-- Lokalni front-matcher (parita ScenarioRunner.IsFrontWheel nize v souboru).
local function sdIsFrontWheel(name: string): boolean
	return name == "FL" or name == "FR" or name == "F"
end

-- Stav na vozidlo; Reset() pri zacatku/konci behu (ClearDriveInputs).
function ServerDrive.Reset(vehicle: Instance?)
	if vehicle == nil then
		return
	end
	ServerDrive._states[vehicle] = nil
	ServerDrive._guardWarned[vehicle] = nil
	ServerDrive._noavTicks[vehicle] = nil
	pcall(function()
		local veh = vehicle :: Instance
		veh:SetAttribute("AE_RPM", nil)
		veh:SetAttribute("AE_Gear", nil)
		veh:SetAttribute("AE_ThrotAct", nil)
		veh:SetAttribute("AE_BrakeAct", nil)
		veh:SetAttribute("AE_ABSActive", nil)
	end)
end

local function sdGetState(vehicle: Instance, tune: any, now: number): any
	local st = ServerDrive._states[vehicle]
	if st ~= nil and st.tune == tune then
		return st
	end
	-- Precompute konstanty motoru z Tune (parita Drive Engine setup).
	local fFD = tune.FinalDrive * tune.FDMult
	local fFDr = fFD * 30 / math.pi
	local peak = tune.PeakRPM / 1000
	local p = {
		hp = tune.Horsepower / 100,
		peak = peak,
		sharp = tune.PeakSharpness,
		cmult = tune.CurveMult,
		eq = tune.EqPoint / 1000,
	}
	local peakCurveN = sdCurveN(peak, p)
	local hpT = ((tune.Horsepower * ((tune.T_Boost * tune.Turbochargers) * (tune.CompressionRatio / 10)) / 7.5) / 2) / 100
	st = {
		tune = tune,
		fFD = fFD,
		fFDr = fFDr,
		curveP = p,
		peakCurveN = peakCurveN,
		hpT = hpT,
		tPsi = tune.T_Boost * tune.Turbochargers,
		inThrot = 0,
		inBrake = 0,
		gThrot = 0,
		gBrake = 0,
		rpm = 0,
		goalRPM = 0,
		gear = 0,
		clutch = 0,
		clutchKick = 0,
		clutchModulate = 0,
		clPressing = false,
		shifting = false,
		shiftUp = false,
		shiftDn = false,
		shiftUntil = 0,
		tBoost = 0,
		hpPrev = 0,
		spLimit = 0,
		outTorque = 0,
		tcsActive = false,
		absActive = false,
		lastTick = now,
		wDia = 0,
	}
	ServerDrive._states[vehicle] = st
	return st
end

-- Jeden server tick pohonu. Volano (steer) se ignoruje (F7.2).
-- inThrottle/inBrake 0..1; vraci (true, souhrn) nebo (false, duvod).
function ServerDrive.Step(vehicle: Instance?, inThrottle: number, inBrake: number): (boolean, any)
	if vehicle == nil then
		return false, "chybi_vozidlo"
	end
	local tune = sdReadTune(vehicle)
	if tune == nil then
		return false, "chybi_Tune_v_kopii"
	end
	local wheels = sdReadWheels(vehicle)
	if #wheels == 0 then
		return false, "zadna_kola_Wheels"
	end
	local seat = sdReadSeat(vehicle)
	if seat == nil then
		return false, "chybi_DriveSeat"
	end

	local now = os.clock()
	local st = sdGetState(vehicle, tune, now)
	local dt = now - (st.lastTick or now)
	if dt <= 0 then
		dt = 1 / 60
	end
	st.lastTick = now
	local deltaTime = dt * 60
	if deltaTime < 0.25 then
		deltaTime = 0.25
	elseif deltaTime > 2 then
		deltaTime = 2
	end

	local fps = 60
	pcall(function()
		fps = game:GetService("Workspace"):GetRealPhysicsFPS()
	end)
	if typeof(fps) ~= "number" or (fps :: number) <= 0 then
		fps = 60
	end
	local factor = 60 / (fps :: number)

	local cmdT = math.max(0, math.min(1, inThrottle))
	local cmdB = math.max(0, math.min(1, inBrake))
	-- Striktni exkluze plyn vs brzda (vzor AutonomousDriver).
	if cmdT > 0 and cmdB > 0 then
		cmdB = 0
	end

	-- wDia: maximalni sirka kol (Drive:301), kesovano na stav.
	if st.wDia <= 0 then
		for _, w in wheels do
			if w.Size.X > st.wDia then
				st.wDia = w.Size.X
			end
		end
		if st.wDia <= 0 then
			st.wDia = 2.7
		end
	end
	local wDRatio = st.wDia * math.pi / 60

	-- Rampa vstupu (Drive Inputs:310-319).
	if st.inThrot <= cmdT then
		st.inThrot = math.min(cmdT, st.inThrot + (tune.ThrotAccel * deltaTime))
	else
		st.inThrot = math.max(cmdT, st.inThrot - (tune.ThrotDecel * deltaTime))
	end
	if st.inBrake <= cmdB then
		st.inBrake = math.min(cmdB, st.inBrake + (tune.BrakeAccel * deltaTime))
	else
		st.inBrake = math.max(cmdB, st.inBrake - (tune.BrakeDecel * deltaTime))
	end

	local speed = (seat :: VehicleSeat).AssemblyLinearVelocity.Magnitude
	local seatVel = (seat :: VehicleSeat).AssemblyLinearVelocity
	local lookY = (seat :: VehicleSeat).CFrame.LookVector.Y

	-- Shifting okno (DCT casovac misto wait()).
	st.clPressing = (st.gear == 0) or st.shifting
	if st.shifting then
		if now >= st.shiftUntil then
			if st.shiftUp then
				st.gear = math.min(st.gear + 1, #tune.Ratios - 2)
			elseif st.shiftDn then
				st.gear = math.max(st.gear - 1, -1)
			end
			st.shiftUp = false
			st.shiftDn = false
			st.shifting = false
			st.clPressing = (st.gear == 0)
		end
	end
	if st.shiftUp and not st.shifting then
		st.gThrot = 0
	elseif st.shiftDn and not st.shifting then
		st.gThrot = (tune.ShiftThrot / 100)
	else
		st.gThrot = st.inThrot
	end
	st.gBrake = st.inBrake

	-- Automatic Transmission, Speed-mode (Drive Auto:669-676), _TMode=Auto (D1).
	-- Launch (D2): stojici vuz + plyn -> 1.
	if st.gear == 0 and (st.inThrot - (tune.IdleThrottle / 100) > 0) and speed < 5 then
		st.gear = 1
		st.clPressing = false
	end
	if st.gear >= 1 and speed > 5 and not st.shifting then
		local upAt = math.ceil(wDRatio * (tune.PeakRPM + tune.AutoUpThresh) / tune.Ratios[st.gear + 2] / st.fFD)
		local dnAt = 0
		if st.gear > 1 then
			dnAt = math.ceil(wDRatio * (tune.PeakRPM - tune.AutoDownThresh) / tune.Ratios[st.gear + 1] / st.fFD)
		end
		if speed > upAt then
			st.shiftUp = true
		elseif st.gear > 1 and speed < dnAt then
			st.shiftDn = true
		end
	end
	if (st.shiftUp or st.shiftDn) and not st.shifting then
		if st.gear >= 1 then
			st.shifting = true
			-- DCT: casovac (Drive Gear:694-714 misto wait()).
			local dur = if st.shiftUp then tune.ShiftUpTime else tune.ShiftDnTime
			st.shiftUntil = now + math.max(0.01, dur)
			st.clPressing = true
		else
			st.shiftUp = false
			st.shiftDn = false
		end
	end

	-- Otacky motoru (Drive Engine:784-852).
	local revMin = tune.IdleRPM
	local goalMin = tune.IdleRPM
	local goalMax = tune.Redline
	local maxSpin = 0
	local nSpin = 0
	for _, w in wheels do
		maxSpin += w.RotVelocity.Magnitude
		nSpin += 1
	end
	if nSpin > 0 then
		maxSpin /= nSpin
	end
	local revThrot = st.gThrot
	if st.goalRPM > goalMax + 100 then
		revThrot = tune.IdleThrottle / 100
	end
	st.goalRPM = math.clamp(
		(st.rpm - tune.RevDecay * deltaTime) + ((tune.RevDecay + tune.RevAccel) * revThrot * deltaTime),
		goalMin,
		tune.Redline + 100
	)
	if st.goalRPM > tune.Redline then
		if st.gear < #tune.Ratios - 2 then
			st.goalRPM -= tune.RevBounce
		else
			st.goalRPM -= tune.RevBounce * 0.5
		end
	end
	local gearIdx = math.max(1, math.min(st.gear + 2, #tune.Ratios))
	local wheelRPM = maxSpin * tune.Ratios[gearIdx] * st.fFDr
	-- Spojka, typ Clutch + AutoClutch (Drive:809-835). D7: hlidany delenec.
	st.clutchKick = st.clutchKick * (tune.ClutchEngage / 100)
	local denom = math.abs(st.gear)
	if denom < 1 then
		denom = 1
	end
	st.clutchModulate = math.min((((speed / tune.SpeedEngage) / denom) - st.clutchKick), 1)
	if st.clPressing then
		st.clutch = 1
	else
		st.clutch = math.min(1 - st.clutchModulate, 1)
	end
	local aRPM = math.max(math.min((st.goalRPM * st.clutch) + (wheelRPM * (1 - st.clutch)), tune.Redline + 100), revMin)
	local clutchP = math.min(math.abs(aRPM - st.rpm) / (tune.Flywheel * deltaTime), 0.9)
	if st.clPressing then
		clutchP = 0
	end
	st.rpm = st.rpm * clutchP + aRPM * (1 - clutchP)
	st.spLimit = (tune.Redline + 100) / (st.fFDr * math.max(0.001, tune.Ratios[gearIdx]))
	if st.rpm > tune.Redline then
		if st.gear < #tune.Ratios - 2 then
			st.rpm -= tune.RevBounce
		else
			st.rpm -= tune.RevBounce * 0.5
		end
	end

	-- Twin-turbo dynamika (Drive:859-872; SCount=0, Electric=false).
	local bThrot = st.gThrot
	local hpPrev = st.hpPrev
	if st.tPsi > 0 then
		local tpsi1 = st.tPsi / tune.Turbochargers
		if st.tBoost < 1 then
			st.tBoost = st.tBoost + ((((((hpPrev*(bThrot*1.2)/tune.Horsepower)/8)-(((st.tBoost/tpsi1*(tpsi1/15)))))*((8/(tune.T_BoostLag/(deltaTime)))*2))/tpsi1)*15)
		else
			st.tBoost = st.tBoost + ((((((hpPrev*(bThrot*1.2)/tune.Horsepower)/8)-(((st.tBoost/tpsi1*(tpsi1/15)))))*((8/(tune.T2_BoostLag/(deltaTime)))*2))/tpsi1)*15)
		end
		if st.tBoost < 0.05 then
			st.tBoost = 0.05
		elseif st.tBoost > 2 then
			st.tBoost = 2
		end
	else
		st.tBoost = 0
	end

	-- Kroutici moment (Drive:888-929; prirozeny + turbo; bez elektriky).
	local nt, tt = 0, 0
	local x = math.max(0, st.rpm)
	if x > 0 then
		local cp = st.curveP
		local cN = sdCurveN(x / 1000, cp)
		local hpN = (math.max(cN / (st.peakCurveN / cp.hp), 0)) * 100
		nt = ((hpN * (cp.eq / x)) * tune.Ratios[gearIdx] * st.fFD) * 1000
		local cT = sdCurveN(x / 1000, {
			hp = st.hpT,
			peak = cp.peak,
			sharp = cp.sharp,
			cmult = cp.cmult,
			eq = cp.eq,
		})
		local peakT = sdCurveN(cp.peak, {
			hp = st.hpT,
			peak = cp.peak,
			sharp = cp.sharp,
			cmult = cp.cmult,
			eq = cp.eq,
		})
		local hpT2 = (math.max(cT / (peakT / math.max(0.001, st.hpT)), 0)) * 100
		tt = (((hpT2 * (cp.eq / x)) * tune.Ratios[gearIdx] * st.fFD) * 1000) * (st.tBoost / 2)
	end
	local cGrav = game:GetService("Workspace").Gravity * tune.InclineComp / 32.2
	local iComp = lookY * cGrav
	local tq = (nt + tt) * math.max(1, 1 + iComp)
	st.outTorque = tq
	-- _HP aproximace pro turbo-dynamiku pristiho ticku (meritko Drive _HP).
	st.hpPrev = math.max(0, (nt + tt) / 1000)

	-- Prumery kol + AWD bias (Drive:931-948, 1021-1029).
	local fws, fwn, rws, rwn = 0, 0, 0, 0
	for _, w in wheels do
		if w.Name == "FL" or w.Name == "FR" then
			fws += w.RotVelocity.Magnitude
			fwn += 1
		elseif w.Name == "RL" or w.Name == "RR" then
			rws += w.RotVelocity.Magnitude
			rwn += 1
		end
	end
	if fwn == 0 then
		fws, fwn = maxSpin, 1
	end
	if rwn == 0 then
		rws, rwn = maxSpin, 1
	end
	fws /= fwn
	rws /= rwn
	local bias = (tune.TorqueVector + 1) / 2

	local fbF = tune.BrakeForce * tune.BrakeBias
	local fbR = tune.BrakeForce * (1 - tune.BrakeBias)
	local throt = st.gThrot
	local brake = st.gBrake
	local clutchOut = 0
	if not st.clPressing then
		clutchOut = 1
	end

	local anyAV = false
	local countBV = 0
	local countAV = 0
	st.tcsActive = false
	st.absActive = false
	for _, w in wheels do
		local slipV = seatVel.Magnitude
		local rotV = w.RotVelocity.Magnitude * (w.Size.X / 2)
		-- TCS (Drive:1031-1039).
		local tqTCS = 1
		if tune.TCSEnabled and throt > 0 then
			tqTCS = 1 - (math.min(math.max(0, math.abs(rotV - slipV) - tune.TCSThreshold) / tune.TCSGradient, 1) * (1 - (tune.TCSLimit / 100)))
		end
		if tqTCS < 1 then
			st.tcsActive = true
		end
		-- ABS (Drive:1008-1013).
		local tqABS = 1
		if tune.ABSEnabled and brake > 0 and math.abs(rotV - slipV) - tune.ABSThreshold > 0 then
			tqABS = 0
		end
		if tqABS < 1 then
			st.absActive = true
		end
		-- Diferencial New (Drive:976-993).
		local diffF, diffR = 1, 1
		if w.Name == "FR" then
			local cl = wheels[1]
			for _, o in wheels do
				if o.Name == "FL" then
					cl = o
					break
				end
			end
			local avg = ((w.RotVelocity.Magnitude / math.max(0.001, cl.RotVelocity.Magnitude)) - 1) * (tune.FDiffPreload / 10)
			diffF = math.ceil(math.max(0,math.min(2,1-( ((tune.FDiffPower/100)*avg*throt) + ((tune.FDiffCoast/100)*avg*(1-throt)))))*100)/100
			diffR = 2 - diffF
		elseif w.Name == "FL" then
			local cr = wheels[1]
			for _, o in wheels do
				if o.Name == "FR" then
					cr = o
					break
				end
			end
			local avg = ((w.RotVelocity.Magnitude / math.max(0.001, cr.RotVelocity.Magnitude)) - 1) * (tune.FDiffPreload / 10)
			diffF = math.ceil(math.max(0,math.min(2,1-( ((tune.FDiffPower/100)*avg*throt) + ((tune.FDiffCoast/100)*avg*(1-throt)))))*100)/100
			diffR = 2 - diffF
		elseif w.Name == "RR" then
			local cl = wheels[1]
			for _, o in wheels do
				if o.Name == "RL" then
					cl = o
					break
				end
			end
			local avg = ((w.RotVelocity.Magnitude / math.max(0.001, cl.RotVelocity.Magnitude)) - 1) * (tune.RDiffPreload / 10)
			diffR = math.ceil(math.max(0,math.min(2,1-( ((tune.RDiffPower/100)*avg*throt) + ((tune.RDiffCoast/100)*avg*(1-throt)))))*100)/100
			diffF = 2 - diffR
		elseif w.Name == "RL" then
			local cr = wheels[1]
			for _, o in wheels do
				if o.Name == "RR" then
					cr = o
					break
				end
			end
			local avg = ((w.RotVelocity.Magnitude / math.max(0.001, cr.RotVelocity.Magnitude)) - 1) * (tune.RDiffPreload / 10)
			diffR = math.ceil(math.max(0,math.min(2,1-( ((tune.RDiffPower/100)*avg*throt) + ((tune.RDiffCoast/100)*avg*(1-throt)))))*100)/100
			diffF = 2 - diffR
		end
		local isF = sdIsFrontWheel(w.Name)
		local tqW = tq
		if tune.Config == "AWD" then
			if isF then
				tqW = tq * (1 - bias)
			else
				tqW = tq * bias
			end
		end
		local tqOUT = (tqW / 1.5) * factor * throt * tqTCS * clutchOut
		local av = w:FindFirstChild("#AV")
		local bv = w:FindFirstChild("#BV")
		if av ~= nil and av:IsA("HingeConstraint") then
			av.MotorMaxTorque = tqOUT * (if w.Name == "RR" then diffR elseif w.Name == "RL" then diffR elseif w.Name == "FR" then diffF elseif w.Name == "FL" then diffF else 1)
			av.AngularVelocity = st.spLimit
			anyAV = true
			countAV += 1
		end
		if bv ~= nil and bv:IsA("HingeConstraint") then
			local base = if isF then fbF else fbR
			local eb = tune.EBrakeForce * ((1 - throt) * (st.rpm / math.max(1, tune.Redline)))
			bv.MotorMaxTorque = (base * factor * brake * tqABS) + eb
			countBV += 1
		end
	end
	if not anyAV then
		ServerDrive._noavTicks[vehicle] = (ServerDrive._noavTicks[vehicle] or 0) + 1
		return false, "moment_nezapsan:zadne_#AV_nenalezeno"
	end

	-- Publikace stavu pro telemetrii (atributy; nil=manual mimo beh).
	pcall(function()
		local veh = vehicle :: Instance
		veh:SetAttribute("AE_RPM", math.floor(st.rpm + 0.5))
		veh:SetAttribute("AE_Gear", st.gear)
		veh:SetAttribute("AE_ThrotAct", throt)
		veh:SetAttribute("AE_BrakeAct", brake)
		veh:SetAttribute("AE_ABSActive", st.absActive)
	end)
	return true, {
		rpm = st.rpm,
		gear = st.gear,
		spLimit = st.spLimit,
		outTorque = tq,
		tcs = st.tcsActive,
		abs = st.absActive,
		bvCount = countBV,
		avCount = countAV,
	}
end

-- F7.1-T01B: pocet ticku bez dodaneho momentu v aktualnim behu (nil = zadny).
function ServerDrive.NoAvTicks(vehicle: Instance?): number?
	if vehicle == nil then
		return nil
	end
	return ServerDrive._noavTicks[vehicle]
end
-- F7.1-T01B: pristup k diagnostice pohonu pro harness (souhrn behu).
ScenarioRunner.ServerDrive = ServerDrive
-- Konec F7.1-inline ServerDrive.
ScenarioRunner.__index = ScenarioRunner

-- F5 Agent D: deterministicke startovni podminky T03 (vlastnik: startovni blok).
--   (1) Rychlost presne 100 +/- 1 studs/s: nastaveni + OVERENI pred startem
--       mereni (zpetne cteni DriveSeat AssemblyLinearVelocity; mimo toleranci
--       = opakuj nastaveni max 3x, pak fail s duvodem). Zdroj rychlosti je
--       def.initial_conditions.speed_studs_s (default 100), tolerance
--       def.initial_conditions.entry_tol (default 1).
--   (2) Pozice/orientace: spawnCFrame od volajiciho (TestHarness: dil StartLine
--       + 3 y clearance, H1); Spawn overi facing +X (RightVector.X >= 0.9) a
--       roll ~= 0 (PrimaryPart/DriveSeat CFrame, tol 5 deg) pred startem.
--   (3) ABS: stav ABSThreshold/ABSEnabled se cte z Tune POUZE read-only
--       (pcall require, zadny zapis; ABSEnabled neni mutable a harness ho
--       nezapisuje). Aktivita zustava dle fyziky (Drive _ABS/_ABSActive ->
--       Values.ABS/ABSActive -> TelemetryCollector abs_enabled/abs_active ->
--       ComputeT03Metrics abs). Nelze-li ABS overit, zaznamena se
--       abs_pending:<duvod> (volajici prida do errors behu, mereni dal bezi).
--   NEMENI rizeni: WriteDriveAttributes vlastni Agent A (nedotykat).

--- Tolerancni konstanty startu T03 (stud/s, stupne, pocet pokusu).
ScenarioRunner.T03_DEFAULT_ENTRY_SPEED = 100
ScenarioRunner.T03_DEFAULT_ENTRY_TOL = 1.0
ScenarioRunner.T03_START_RETRIES = 3
ScenarioRunner.T03_ROLL_TOL_DEG = 5
ScenarioRunner.T03_FACING_MIN_X = 0.9
-- F6: smer trate je dan geometrii (+X: StartLine x=2 -> EndWall x=3804).
-- Po yaw180-fixu nese spawnCFrame RightVector -X, proto rychlost i facing
-- vychazeji z TRACK_DIR / cumaku vozu, nikdy z RightVector spawnCFrame.
ScenarioRunner.T03_TRACK_DIR = Vector3.xAxis
-- F5-FX2 spawn-settle-go: po Deploy + nulovani rychlosti cekej, dokud
-- |vertikalni rychlost| < 2 studs/s AND |roll| < 5 deg (max 3 s), pak teprve
-- armuj mereni (vstupni rychlost + gate).
ScenarioRunner.SETTLE_VSPEED_TOL = 2.0
ScenarioRunner.SETTLE_MAX_S = 3.0
-- FX3 (G4.3, jeden slot): kanonicke jmeno pracovniho slotu. Handoff H1:
-- VehicleManager.DeployVehicle prejmenuje klon na SLOT_NAME; pojistka je
-- ScenarioRunner.EnsureSlotName volana ze Spawnu.
ScenarioRunner.SLOT_NAME = "AE_VehicleSlot"
-- FX3 (G4.2, _InBrake-dozneni): zbytkovy brzdny moment < 2 % je hluboko pod
-- rozlisenim entry gate (+-1 studs/s pri v = 100); timeout 3 s kryje i pomaly
-- BrakeDecel. Blizsi fyzika u WaitForBrakeDecay.
ScenarioRunner.BRAKE_DECAY_TOL = 0.02
ScenarioRunner.BRAKE_DECAY_MAX_S = 3.0

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
	self.stopT = nil -- T03: cas prvniho poklesu XZ-rychlosti pod stopSpeed
	self.gateT = nil -- T01B: cas prekonani gate
	self.gateV = nil -- T01B: rychlost pri prekonani gate
	self.completionReason = nil -- T01B: 'finish_gate_crossed' pri cistem dokonceni
	self.startInfo = nil -- F5 Agent D: vysledek overeni startu T03 (info z VerifyT03Start)
	self.absPending = nil -- F5 Agent D: "pending:<duvod>" ABS, nelze-li overit z Tune
	return self
end

function ScenarioRunner:GetState(): string
	return self.state
end

-- F5 Agent D: read-only pomocne cteni startovnich podminek (zadny zapis).
function ScenarioRunner.FindDriveSeat(vehicle: Instance?): VehicleSeat?
	if vehicle == nil then
		return nil
	end
	local ok, seat = pcall(function()
		return (vehicle :: Instance):FindFirstChildWhichIsA("VehicleSeat", true)
	end)
	if not ok or seat == nil or not (seat :: Instance):IsA("BasePart") then
		return nil
	end
	return seat :: VehicleSeat
end

-- XZ rychlost DriveSeat (Drive cte DriveSeat.Velocity; H1) pro overeni vstupu.
function ScenarioRunner.ReadDriveSeatXzSpeed(vehicle: Instance?): number?
	local seat = ScenarioRunner.FindDriveSeat(vehicle)
	if seat == nil then
		return nil
	end
	local v = (seat :: BasePart).AssemblyLinearVelocity
	return math.sqrt(v.X * v.X + v.Z * v.Z)
end

-- Roll (kloneni kolem podelne osy) z CFrame PrimaryPart / DriveSeat, ve stupnich.
function ScenarioRunner.ReadStartRollDeg(vehicle: Instance?): number?
	if vehicle == nil then
		return nil
	end
	local part: BasePart? = nil
	if (vehicle :: Instance):IsA("Model") then
		part = ((vehicle :: Model).PrimaryPart :: any) :: BasePart?
	end
	if part == nil then
		local seat = ScenarioRunner.FindDriveSeat(vehicle)
		if seat ~= nil then
			part = seat :: BasePart
		end
	end
	if part == nil then
		return nil
	end
	local ok, rx, _, rz = pcall(function()
		return (part :: BasePart).CFrame:ToOrientation()
	end)
	if not ok or typeof(rx) ~= "number" or typeof(rz) ~= "number" then
		return nil
	end
	-- Roll kolem podelne osy X pri facing +X odpovida rotaci Z orientace.
	return math.deg(rz)
end

-- Facing +X ze spawnCFrame: X slozka RightVector (trat vede podel +X, H1).
-- F6: POZOR -- po yaw-fixu (-90°) sleduje cumak LookVector spawnCFrame.
-- Tato funkce zustava pro kompatibilitu; gate pouziva primarne
-- ReadVehicleFacingX (cumak skutecneho vozu).
function ScenarioRunner.ReadSpawnFacingX(spawnCFrame: CFrame?): number?
	if spawnCFrame == nil then
		return nil
	end
	local ok, rv = pcall(function()
		return (spawnCFrame :: CFrame).RightVector
	end)
	if not ok or typeof(rv) ~= "Vector3" then
		return nil
	end
	return (rv :: Vector3).X
end

-- F5-FX2: vertikalni rychlost (drop po spawnu) pro settle-go. |Y| slozka
-- AssemblyLinearVelocity DriveSeat (fallback PrimaryPart); nil pri chybe.
function ScenarioRunner.ReadVerticalSpeed(vehicle: Instance?): number?
	if vehicle == nil then
		return nil
	end
	local part: BasePart? = nil
	local seat = ScenarioRunner.FindDriveSeat(vehicle)
	if seat ~= nil then
		part = seat :: BasePart
	elseif (vehicle :: Instance):IsA("Model") then
		part = ((vehicle :: Model).PrimaryPart :: any) :: BasePart?
	end
	if part == nil then
		return nil
	end
	local ok, v = pcall(function()
		return (part :: BasePart).AssemblyLinearVelocity
	end)
	if not ok or typeof(v) ~= "Vector3" then
		return nil
	end
	return math.abs((v :: Vector3).Y)
end

-- FX3 (G4.1, Sit-event transfer vlastnictvi): usednuti priradi celou 167-dilnou
-- sestavu sedicimu klientovi (engine automatic); server pak cte stale/jumpy
-- repliky a meri garbage (S1: zamrzla telemetrie x==2.00/v==100.00). Pred
-- briefem nastaveny nil-ownership po usednuti NEPLATI. Overeno zive (E-final-II
-- G1 mezikut): nil APLIKOVANY PO usednuti DRZI (0/167 klient, 8 s+ pri trvalem
-- sezeni; transfer se deje POUZE na Sit-event, ne kontinualne) + diagnosticky
-- puls 30 prokazal fresh telemetrii. Proto: reclaim PO usednuti, pred kazdym
-- repem (Spawn/SpawnT03Verified tuto funkci volaji), a harness (H1, mimo
-- mandat) ji ma volat i na Sit-event. Bez overeni GetNetworkOwner()==nil se
-- rychlost/gate nesmi armit -- jinak void s duvodem.
function ScenarioRunner.ReclaimServerOwnership(vehicle: Instance?): (boolean, string?)
	if vehicle == nil then
		return false, "chybi_vozidlo"
	end
	local parts: { BasePart } = {}
	local okCollect = pcall(function()
		if (vehicle :: Instance):IsA("BasePart") then
			table.insert(parts, vehicle :: BasePart)
		end
		for _, d in (vehicle :: Instance):GetDescendants() do
			if d:IsA("BasePart") then
				table.insert(parts, d :: BasePart)
			end
		end
	end)
	if not okCollect then
		return false, "ownership_neovereno:vyber_dilu_selhal"
	end
	if #parts == 0 then
		return false, "ownership_neovereno:zadne_BasePart_k_reclaimu"
	end
	for _, part in parts do
		pcall(function()
			(part :: BasePart):SetNetworkOwner(nil)
		end)
	end
	local foreign = 0
	local okCheck = true
	for _, part in parts do
		local ok, owner = pcall(function()
			return (part :: BasePart):GetNetworkOwner()
		end)
		if not ok then
			okCheck = false
			break
		end
		if owner ~= nil then
			foreign += 1
		end
	end
	if not okCheck then
		return false, "ownership_neovereno:cteni_GetNetworkOwner_selhalo"
	end
	if foreign > 0 then
		return false, string.format("ownership_neovereno:%d/%d_dilu_drzi_klient", foreign, #parts)
	end
	return true, nil
end

-- FX3 (G4.3, jeden slot): pojistka ze strany ScenarioRunner. Handoff H1:
-- VehicleManager.DeployVehicle ma klon prejmenovat na SLOT_NAME; Spawn tuto
-- funkci vola vzdy, takze kazdy rep konci v jednom slotu (idempotentni,
-- reference pres Instance se prejmenovanim nerozbiji).
function ScenarioRunner.EnsureSlotName(vehicle: Instance?): boolean
	if vehicle == nil then
		return false
	end
	local ok = pcall(function()
		if (vehicle :: Instance).Name ~= ScenarioRunner.SLOT_NAME then
			(vehicle :: Instance).Name = ScenarioRunner.SLOT_NAME
		end
	end)
	return ok
end

-- FX3 (G4.2, _InBrake-dozneni): cteni skutecne brzdy Values.Brake (NumberValue;
-- _GBrake, zapisuje Drive kazdy frame). nil = Drive nebezi / Values chybi.
function ScenarioRunner.ReadBrakeValue(vehicle: Instance?): number?
	if vehicle == nil then
		return nil
	end
	local ok, val = pcall(function()
		local values = (vehicle :: Instance):FindFirstChild("Values", true)
		if values == nil then
			return nil
		end
		local b = (values :: Instance):FindFirstChild("Brake")
		if b ~= nil and (b:IsA("NumberValue") or b:IsA("IntValue")) then
			return (b :: NumberValue).Value
		end
		return nil
	end)
	if not ok then
		return nil
	end
	return val
end

-- FX3 (G4.2, _InBrake-dozneni): po ClearDriveInputs(0,0,0) CEKAT, dokud
-- Values.Brake -> ~0, a TEPRVE pak speed-set. Fyzika: klientsky _IBrake drzi
-- 1.0 i po briefu (nil atribut posledni prikaz nemaze); nula zapsana serverem
-- dojde pres replikaci az dalsi Heartbeat a _InBrake dobiha rampou BrakeDecel.
-- Nastavi-li se rychlost driv, prvni vzorky brzdi zbytkovym momentem pri
-- roztocenych kolech a scrubuji -- druha slozka post-gate bleedu. Chybi-li
-- Values/Brake (Drive nebezi), neni co cekat -- true (stejna filozofie jako
-- CheckBrakeDiag "cekam"). Timeout = void s duvodem.
function ScenarioRunner.WaitForBrakeDecay(vehicle: Instance?): (boolean, string?)
	if vehicle == nil then
		return false, "chybi_vozidlo"
	end
	local deadline = os.clock() + ScenarioRunner.BRAKE_DECAY_MAX_S
	while true do
		local b = ScenarioRunner.ReadBrakeValue(vehicle)
		if b == nil then
			return true, nil
		end
		if math.abs(b) <= ScenarioRunner.BRAKE_DECAY_TOL then
			return true, nil
		end
		if os.clock() >= deadline then
			return false, string.format("brzda_nedoznela:Values.Brake=%.3f_tol=%.2f", b, ScenarioRunner.BRAKE_DECAY_TOL)
		end
		task.wait(0.1)
	end
end

-- ABS konfigurace z Tune POUZE pro cteni (zadny zapis, zadny WriteTune).
-- Vraci (config, status): config = { abs_threshold, abs_enabled } (nil hodnoty
-- pri chybejicim klici); status = "ok" | "pending:<duvod>".
function ScenarioRunner.ReadABSConfig(vehicle: Instance?): (any?, string)
	if vehicle == nil then
		return nil, "pending:chybi_vozidlo"
	end
	local okFind, tune = pcall(function()
		return (vehicle :: Instance):FindFirstChild("A-Chassis Tune", true)
	end)
	if not okFind or tune == nil or not (tune :: Instance):IsA("ModuleScript") then
		return nil, "pending:chybi_A-Chassis_Tune"
	end
	local okReq, tuneTable = pcall(require, tune)
	if not okReq or typeof(tuneTable) ~= "table" then
		return nil, "pending:require_Tune_selhalo"
	end
	local cfg = {
		abs_threshold = (tuneTable :: any).ABSThreshold,
		abs_enabled = (tuneTable :: any).ABSEnabled,
	}
	if typeof(cfg.abs_threshold) ~= "number" or typeof(cfg.abs_enabled) ~= "boolean" then
		return cfg, "pending:chybi_ABSThreshold_nebo_ABSEnabled_v_Tune"
	end
	return cfg, "ok"
end

-- F6: facing +X z CUMAKU skutecneho vozu (Collision_Front vs. pivot).
-- Duvod: spawnCFrame-facing gate (ReadSpawnFacingX) vzdy prosel, prestoze vuz
-- stal celem k -X (F6-run-001). Meri skutecne vozidlo, ne pozadavek.
function ScenarioRunner.ReadVehicleFacingX(vehicle: Instance?): number?
	if vehicle == nil or not (vehicle :: Instance):IsA("Model") then
		return nil
	end
	local ok, fx = pcall(function()
		local m = vehicle :: Model
		local front = m:FindFirstChild("Collision_Front", true)
		if front == nil or not (front :: Instance):IsA("BasePart") then
			return nil
		end
		local pivot = m:GetPivot()
		local d = ((front :: BasePart).Position - pivot.Position)
		if d.Magnitude < 0.01 then
			return nil
		end
		return d.Unit:Dot(ScenarioRunner.T03_TRACK_DIR)
	end)
	if not ok then
		return nil
	end
	return fx
end

-- Nastaveni startovni rychlosti T03: TRACK_DIR (+X) * speed na vsechny
-- BaseParty (DriveSeat explicitne; stejna semantika jako TestHarness, H1).
-- FX3 (G4.2, post-gate bleed 2-4 studs/s): krome linearni rychlosti se kolum
-- nastavuje i UHLOVA rychlost omega = v / R kolem lateralni osy. Fyzika:
-- valeni bez prokluzu vyzaduje nulovou rychlost kontaktniho bodu kola,
-- V_cm + omega x (-R*up) = 0, coz pri dir kolmem na up dava
-- omega = (up x dir) * (v/R), kde dir je smer jizdy (TRACK_DIR +X, F6).
-- Drive pocita povrchovou rychlost kola jako |RotVelocity * (size.x/2)|
-- (ABS prokluzovy prah, hlavicka) -- proto se R bere stejne: R = Size.X / 2
-- konkretniho dilu kola. Kolo s nulovym uhlovym momentem pri v = 100
-- a nulovem plynu je prudky prechodovy odpor v prvnich krocich
-- (drivetrain-scrub) -- presne ten bleed, ktery voidoval S3 3/3.
-- Nekola (karoserie) dostanou nulovou uhlovou rychlost. Kola = dily,
-- jejichz nazev nebo rodic/prarodic obsahuje "wheel" (kontejner "Wheels"
-- v A-Chassis sablone); neni-li zadne kolo rozpoznano, plati linear-only
-- fallback (beh se nerusi -- rychlostni gate dale hlida v0).
function ScenarioRunner.IsWheelPart(part: Instance?): boolean
	if part == nil then
		return false
	end
	local node: Instance? = part
	for _ = 1, 3 do
		if node == nil then
			return false
		end
		local ok, nm = pcall(function()
			return (node :: Instance).Name
		end)
		if ok and typeof(nm) == "string" and string.find(string.lower(nm), "wheel", 1, true) ~= nil then
			return true
		end
		node = (node :: Instance).Parent
	end
	return false
end

function ScenarioRunner.ApplyT03StartSpeed(vehicle: Instance?, spawnCFrame: CFrame, speed: number): boolean
	if vehicle == nil or spawnCFrame == nil or typeof(speed) ~= "number" then
		return false
	end
	local ok = pcall(function()
		local cf: CFrame = spawnCFrame :: CFrame
		-- F6: smer trate +X (TRACK_DIR); cf se pouziva jen pro UpVector (omega).
		local dir = ScenarioRunner.T03_TRACK_DIR
		local up = cf.UpVector
		local axle = up:Cross(dir)
		local axleLen = axle.Magnitude
		if axleLen < 1e-6 then
			axle = Vector3.zAxis * -1
		else
			axle /= axleLen
		end
		local v = dir * speed
		for _, d in (vehicle :: Instance):GetDescendants() do
			if d:IsA("BasePart") then
				local part = d :: BasePart
				part.AssemblyLinearVelocity = v
				if ScenarioRunner.IsWheelPart(part) then
					local r = part.Size.X / 2
					if typeof(r) == "number" and r > 0.05 then
						part.AssemblyAngularVelocity = axle * (speed / r)
					else
						part.AssemblyAngularVelocity = Vector3.zero
					end
				else
					part.AssemblyAngularVelocity = Vector3.zero
				end
			end
		end
	end)
	return ok
end

-- Overeni startovnich podminek T03 pred startem mereni.
-- Vraci (ok, reasons, info): reasons = seznam duvodu (prazdny pri ok);
-- info = { entry_speed, entry_tol, measured_speed, roll_deg, facing_x,
--   abs_threshold, abs_enabled, abs_status }.
function ScenarioRunner.VerifyT03Start(vehicle: Instance?, def: any, spawnCFrame: CFrame?): (boolean, { string }, any)
	local reasons: { string } = {}
	local entrySpeed = ScenarioRunner.T03_DEFAULT_ENTRY_SPEED
	local entryTol = ScenarioRunner.T03_DEFAULT_ENTRY_TOL
	if def ~= nil and def.initial_conditions ~= nil then
		local s = (def.initial_conditions :: any).speed_studs_s
		if typeof(s) == "number" then
			entrySpeed = s
		end
		local e = (def.initial_conditions :: any).entry_tol
		if typeof(e) == "number" then
			entryTol = e
		end
	end
	local measured = ScenarioRunner.ReadDriveSeatXzSpeed(vehicle)
	if measured == nil then
		table.insert(reasons, "entry_speed_neoverena:chybi_DriveSeat")
	elseif math.abs((measured :: number) - entrySpeed) > entryTol then
		table.insert(
			reasons,
			string.format(
				"entry_speed_mimo_toleranci:cil=%.1f_tol=%.1f_mereno=%.2f",
				entrySpeed,
				entryTol,
				measured :: number
			)
		)
	end
	-- F6: facing z CUMAKU vozu (primarne), fallback LookVector spawnCFrame
	-- (cumak = LookVector po yaw-fixu -90°; stary prime test pres RightVector
	-- byl vzdy PASS a maskoval spatnou orientaci).
	local facingX = ScenarioRunner.ReadVehicleFacingX(vehicle)
	if facingX == nil then
		local okL, lv = pcall(function()
			return (spawnCFrame :: CFrame).LookVector
		end)
		if okL and typeof(lv) == "Vector3" then
			facingX = (lv :: Vector3).X
		end
	end
	if facingX == nil then
		table.insert(reasons, "facing_neoveren:chybi_vuz_i_spawnCFrame")
	elseif (facingX :: number) < ScenarioRunner.T03_FACING_MIN_X then
		table.insert(reasons, string.format("facing_neni_+X:cumak.X=%.3f", facingX :: number))
	end
	local rollDeg = ScenarioRunner.ReadStartRollDeg(vehicle)
	if rollDeg == nil then
		table.insert(reasons, "roll_neoveren:chybi_PrimaryPart_nebo_DriveSeat")
	elseif math.abs(rollDeg :: number) > ScenarioRunner.T03_ROLL_TOL_DEG then
		table.insert(reasons, string.format("roll_pred_startem_nenulovy:%.1f_deg", rollDeg :: number))
	end
	local absCfg, absStatus = ScenarioRunner.ReadABSConfig(vehicle)
	local info = {
		entry_speed = entrySpeed,
		entry_tol = entryTol,
		measured_speed = measured,
		facing_x = facingX,
		roll_deg = rollDeg,
		abs_threshold = if absCfg ~= nil then absCfg.abs_threshold else nil,
		abs_enabled = if absCfg ~= nil then absCfg.abs_enabled else nil,
		abs_status = absStatus,
	}
	return #reasons == 0, reasons, info
end

function ScenarioRunner:Reset(): ()
	self.state = ScenarioRunner.State.IDLE
	self.def = nil
	self.runId = nil
	self.t = 0
	self.failReason = nil
	self.inputHashParts = {}
	self.stopT = nil
	self.gateT = nil
	self.gateV = nil
	self.completionReason = nil
	self.startInfo = nil
	self.absPending = nil
end

-- Spawn faze: synchronni reset vozidla na startovni CFrame, nulove rychlosti, ustaleni.
-- PivotTo pivotuje kolem PrimaryPart (VehicleManager.CloneVehicle nastavi
-- PrimaryPart = DriveSeat na klonech; F4.4 M2 -- bez nej je placement kloubove
-- sestavy nedefinovany). Rychlosti se nuluji (zadna zmena fyziky); vyskove
-- odsazeni (+3 y pro T03) dodava volajici ve spawnCFrame (TestHarness).
-- F5 Agent D: pro kind "straight_brake_100_0" (T03) nasleduje po ustaleni
-- nastaveni presne vstupni rychlosti + overeni pred startem mereni
-- (zpetne cteni DriveSeat; mimo toleranci = retry max 3x, pak FAILED).
function ScenarioRunner:Spawn(def: any, runId: string, vehicle: Instance?, spawnCFrame: CFrame?): (boolean, string?)
	self.def = def
	self.runId = runId
	self.state = ScenarioRunner.State.SPAWN
	self.t = 0
	self.stopT = nil
	self.gateT = nil
	self.gateV = nil
	self.completionReason = nil
	self.startInfo = nil
	self.absPending = nil
	-- FX3 (G4.3/G4.1): jeden slot + server-ownership pred nulovanim (best-effort;
	-- striktni gate s voidem je v SpawnT03Verified; ostatni scenare gate nemaji).
	if vehicle ~= nil then
		ScenarioRunner.EnsureSlotName(vehicle)
		ScenarioRunner.ReclaimServerOwnership(vehicle)
	end
	-- F5-FX2 stuck-brake: pred startem mereni EXPLICITNE nuluj vstupy
	-- (0,0,0 + overeni; best-effort, duvod se propise do failReason pri voidu).
	if vehicle ~= nil then
		local okZero, zeroErr = ScenarioRunner.ClearDriveInputs(vehicle)
		if not okZero then
			self.state = ScenarioRunner.State.FAILED
			self.failReason = "startovni_podminky:" .. tostring(zeroErr)
			return false, self.failReason
		end
	end
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
	if def ~= nil and def.initial_conditions ~= nil and def.initial_conditions.settle_s ~= nil then
		settle = def.initial_conditions.settle_s
	end
	task.wait(settle)
	if def ~= nil and (def :: any).kind == "straight_brake_100_0" then
		return self:SpawnT03Verified(vehicle, spawnCFrame)
	end
	self.state = ScenarioRunner.State.RUNNING
	return true, nil
end

-- F5 Agent D: T03 vetev Spawnu (pouze startovni podminky; rizeni netkne).
-- Po ustaleni nastavi vstupni rychlost, overi (rychlost/facing/roll/ABS),
-- pri nesplnene rychlosti opakuje nastaveni max T03_START_RETRIES x.
-- Vraci (true, absPending|nil) pri uspechu, (false, duvod) pri neuspechu.
function ScenarioRunner:SpawnT03Verified(vehicle: Instance?, spawnCFrame: CFrame?): (boolean, string?)
	if vehicle == nil or spawnCFrame == nil then
		self.state = ScenarioRunner.State.FAILED
		self.failReason = "startovni_podminky:chybi_vozidlo_nebo_spawnCFrame"
		return false, self.failReason
	end
	local def = self.def
	local entrySpeed = ScenarioRunner.T03_DEFAULT_ENTRY_SPEED
	if def ~= nil and (def :: any).initial_conditions ~= nil then
		local s = ((def :: any).initial_conditions :: any).speed_studs_s
		if typeof(s) == "number" then
			entrySpeed = s
		end
	end
	-- F5-FX2 spawn-settle-go: po Deploy + nulovani rychlosti cekej na usednuti
	-- (|vy| < 2 AND |roll| < 5 deg, max 3 s), pak teprve armuj mereni.
	-- Timeout = void s duvodem (rock/spin loterie z rozhoupane sestavy, F4).
	local okSettle, settleErr = ScenarioRunner.WaitForSettle(vehicle)
	if not okSettle then
		self.state = ScenarioRunner.State.FAILED
		self.failReason = "startovni_podminky:" .. tostring(settleErr)
		return false, self.failReason
	end
	-- FX3 (G4.1): PO usednuti reclaim + OVERENI nil-ownershipu; jinak void.
	-- Musi predchazet VSEM zpetnym ctenim (decay, pre-roll, gate) -- na
	-- klientem vlastnenych dilech server cte stale repliky (S1).
	local okOwn, ownErr = ScenarioRunner.ReclaimServerOwnership(vehicle)
	if not okOwn then
		self.state = ScenarioRunner.State.FAILED
		self.failReason = "startovni_podminky:" .. tostring(ownErr)
		return false, self.failReason
	end
	-- FX3 (G4.2): zero uz zapsano (Spawn/ClearDriveInputs) -- pockat na decay
	-- Values.Brake -> 0 PRED speed-setem, jinak prvni vzorky scrubuji.
	local okDecay, decayErr = ScenarioRunner.WaitForBrakeDecay(vehicle)
	if not okDecay then
		self.state = ScenarioRunner.State.FAILED
		self.failReason = "startovni_podminky:" .. tostring(decayErr)
		return false, self.failReason
	end
	-- F5-FX2 (4): roll ~= 0 over PRED nastavenim rychlosti (jinak void).
	-- Rychlost se na rozhoupanou sestavu vubec nenastavuje.
	local preRoll = ScenarioRunner.ReadStartRollDeg(vehicle)
	if preRoll == nil then
		self.state = ScenarioRunner.State.FAILED
		self.failReason = "startovni_podminky:roll_neoveren_pred_rychlosti:chybi_PrimaryPart_nebo_DriveSeat"
		return false, self.failReason
	elseif math.abs(preRoll) > ScenarioRunner.T03_ROLL_TOL_DEG then
		self.state = ScenarioRunner.State.FAILED
		self.failReason = string.format("startovni_podminky:roll_pred_startem_nenulovy:%.1f_deg", preRoll)
		return false, self.failReason
	end
	local ok = false
	local reasons: { string } = {}
	local info: any = nil
	-- FX3 (G4.2, first-tol): entry_tol ZUSTAVA +-1 (default; def muze zpresnit,
	-- ne rozsirit nad fyzikalni smysl). Proc NE 2-3: bleed 2-4 studs/s je
	-- aparaturovy artefakt (drivetrain-scrub + _InBrake-dozneni), ne fyzika
	-- brzdeni; sirsi tol by poustela predbrzdene/rozhoupane behy a zkreslila
	-- brake_distance. Spravny fix je odstranit pricinu (decay-wait vyse +
	-- omega v ApplyT03StartSpeed + minimalni okno gate->prvni vzorek), ne
	-- roztahnout branu. GATE->SAMPLE (H1, mimo mandat): od uspesneho gate
	-- zadny wait -- harness musi collector startovat a prvni vzorek brat bez
	-- prodlevy, jinak se bleed vrati oknem.
	for _ = 1, ScenarioRunner.T03_START_RETRIES do
		ScenarioRunner.ApplyT03StartSpeed(vehicle, spawnCFrame, entrySpeed)
		ok, reasons, info = ScenarioRunner.VerifyT03Start(vehicle, def, spawnCFrame)
		if ok then
			break
		end
		-- Retry ma smysl jen pro rychlost; facing/roll/spawn se nastavenim
		-- rychlosti nezmeni -- pri jejich poruse konci smycka hned.
		local onlySpeed = true
		for _, r in reasons do
			if string.find(r, "entry_speed_mimo_toleranci", 1, true) == nil then
				onlySpeed = false
				break
			end
		end
		if not onlySpeed then
			break
		end
	end
	self.startInfo = info
	if info ~= nil and typeof(info.abs_status) == "string" and string.sub(info.abs_status, 1, 8) == "pending:" then
		self.absPending = "abs_" .. info.abs_status
	end
	if not ok then
		self.state = ScenarioRunner.State.FAILED
		self.failReason = "startovni_podminky:" .. table.concat(reasons, ";")
		return false, self.failReason
	end
	self.state = ScenarioRunner.State.RUNNING
	return true, self.absPending
end

-- Deterministicky ridic: vraci (throttle, brake, steer) pro dany cas.
function ScenarioRunner:DriverInputs(t: number, x: number?): (number, number, number)
	local kind = if self.def ~= nil then self.def.kind else "straight_accel"
	if kind == "straight_brake_100_0" then
		return 0, math.clamp(t / 0.15, 0, 1), 0
	elseif kind == "straight_accel_brake" then
		-- F7.1-T01B: faze rizena pozici (x = posledni znama PrimaryPart.x).
		-- Plyn do brake_start_x, pak plna server-brzda do vyhodnoceni.
		local cut = 2500
		if self.def ~= nil and typeof((self.def :: any).brake_start_x) == "number" then
			cut = (self.def :: any).brake_start_x
		end
		if typeof(x) == "number" and (x :: number) >= cut then
			return 0, 1, 0
		end
		return math.clamp(t / 0.2, 0, 1), 0, 0
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

-- =====================================================================
-- F7.2 ServerSteer: server-side kinematicky steering (port A-Chassis 'New').
-- Zdroj: Drive LocalScript blok [[Steering]] r. 322-380 + Tune [[Steering]].
-- Princip: absolutni CFrame zapis cepu Arm.Steer relativne k Base, kazdy tick,
-- doslovny vzorec Drive (F-set {F,FL,FR}; R-set vynechan, FWSteer='None').
-- Zivotni cyklus (AC6): vstupni entry (manual loop) je NEZAVISLA na internim
-- stavu steerC — zruseni entry nuluje prikaz (steerT=0), Step se vola dal pres
-- ServerSteer.Settle(vehicle), dokud se kola nenarovnaji (ReturnSpeed).
-- Fail-closed: chybi-li Arm/Steer/Base u pritomne sady -> ZADNY zapis.
-- =====================================================================
local ServerSteer = {}
ServerSteer._states = {} -- [vehicle] = { steerC:number, tune:any }
ServerSteer._settling = {} -- [vehicle] = true (dopad navratu po zruseni entry)
ServerSteer._warnedValues = {} -- [vehicle] = true (Values.SteerC chybi, warn 1x)
ServerSteer.MAXTICKS = 3 -- dt-strop (D1): ticks=min(dt*60,0,3)
ServerSteer.CENTER_STEERC = 0.005 -- |steerC| pod prahem = narovnano
ScenarioRunner.ServerSteer = ServerSteer

local STEER_SETS = { "F", "FL", "FR" }

-- Unikatni identita dilu v ramci slotu (S0/B): plna cesta + trida + velikost.
-- Zachyti i vymenu dilu za jiny stejho jmena/tridy/rodice (velikost se lisi).
-- Zbytkove riziko (identicky dvojnik) je mimo scope a je zapsano v planu.
local function ssPartIdentity(slot: Instance, d: Instance): string
	local rel = d:GetFullName()
	local prefix = slot:GetFullName() .. "."
	if string.sub(rel, 1, #prefix) == prefix then
		rel = string.sub(rel, #prefix + 1)
	end
	local extra = "-"
	if d:IsA("BasePart") then
		local s = (d :: BasePart).Size
		extra = string.format("%.3f,%.3f,%.3f", s.X, s.Y, s.Z)
	end
	return rel .. "|" .. d.ClassName .. "|" .. extra
end

-- S0: vychozi snapshot struktury vozidla (pred kazdou jizdou).
-- { count, parts={[id]=true}, roots={[rootId]={path,anchored,owner}},
--   av, bv, heights={[kolo]={baseY,centerY}} }
function ScenarioRunner.SnapshotVehicle(vehicle: Instance?): (any?, string?)
	if vehicle == nil then
		return nil, "chybi_vozidlo"
	end
	local snap: any = { parts = {}, roots = {}, heights = {}, count = 0, av = 0, bv = 0 }
	local ok, err = pcall(function()
		local veh = vehicle :: Instance
		for _, d in veh:GetDescendants() do
			snap.count += 1
			snap.parts[ssPartIdentity(veh, d)] = true
			if d:IsA("HingeConstraint") then
				if d.Name == "#AV" then
					snap.av += 1
				elseif d.Name == "#BV" then
					snap.bv += 1
				end
			end
		end
		-- unikatni assembly roots pres BaseParty
		local seen: { [Instance]: boolean } = {}
		for _, d in veh:GetDescendants() do
			if d:IsA("BasePart") then
				local rok, root = pcall(function()
					return (d :: BasePart):GetAssemblyRootPart()
				end)
				if rok and root ~= nil and seen[root] ~= true then
					seen[root] = true
					local own: string? = nil
					pcall(function()
						local o = (root :: BasePart):GetNetworkOwner()
						if o ~= nil then
							own = o.Name
						end
					end)
					snap.roots[ssPartIdentity(veh, root)] = {
						path = (root :: Instance):GetFullName(),
						anchored = (root :: BasePart).Anchored,
						owner = own,
					}
				end
			end
		end
		-- staticke vysky: kola (prima BasePart deti Wheels) + Base prednich sad
		local wheels: Instance? = nil
		pcall(function()
			wheels = veh:FindFirstChild("Wheels", true)
		end)
		if wheels ~= nil then
			for _, w in (wheels :: Instance):GetChildren() do
				if w:IsA("BasePart") then
					snap.heights[w.Name .. ".tire"] = (w :: BasePart).Position.Y
				else
					local base: Instance? = nil
					pcall(function()
						base = (w :: Instance):FindFirstChild("Base")
					end)
					if base ~= nil and (base :: Instance):IsA("BasePart") then
						snap.heights[w.Name .. ".base"] = (base :: BasePart).Position.Y
					end
				end
			end
		end
	end)
	if not ok then
		return nil, "snapshot_selhal:" .. tostring(err)
	end
	return snap, nil
end

-- S0: porovnani aktualniho stavu se snapshotem. (true,{}) nebo (false, diffs).
function ScenarioRunner.DiffSnapshot(vehicle: Instance?, snap: any): (boolean, { string })
	local diffs: { string } = {}
	if vehicle == nil then
		return false, { "chybi_vozidlo" }
	end
	if snap == nil then
		return false, { "chybi_snapshot" }
	end
	pcall(function()
		local veh = vehicle :: Instance
		local count = 0
		local cur: { [string]: boolean } = {}
		for _, d in veh:GetDescendants() do
			count += 1
			cur[ssPartIdentity(veh, d)] = true
		end
		if count ~= (snap.count :: number) then
			table.insert(diffs, string.format("pocet_dilu:%s->%s", tostring(snap.count), tostring(count)))
		end
		for id, _ in snap.parts do
			if cur[id] ~= true then
				table.insert(diffs, "chybi_dil:" .. tostring(id))
			end
		end
		for id, _ in cur do
			if (snap.parts :: any)[id] ~= true then
				table.insert(diffs, "novy_dil:" .. tostring(id))
			end
		end
		-- roots: znovu sestavit a porovnat (AC7 re-enumerace)
		local seen: { [Instance]: boolean } = {}
		local curRoots: { [string]: any } = {}
		for _, d in veh:GetDescendants() do
			if d:IsA("BasePart") then
				local rok, root = pcall(function()
					return (d :: BasePart):GetAssemblyRootPart()
				end)
				if rok and root ~= nil and seen[root] ~= true then
					seen[root] = true
					local own: string? = nil
					pcall(function()
						local o = (root :: BasePart):GetNetworkOwner()
						if o ~= nil then
							own = o.Name
						end
					end)
					curRoots[ssPartIdentity(veh, root)] = {
						anchored = (root :: BasePart).Anchored,
						owner = own,
					}
				end
			end
		end
		for id, r in snap.roots do
			local c = curRoots[id]
			if c == nil then
				table.insert(diffs, "chybi_root:" .. tostring(id))
			else
				if (c :: any).anchored ~= (r :: any).anchored then
					table.insert(diffs, "zmena_anchored:" .. tostring(id))
				end
				if (c :: any).owner ~= (r :: any).owner then
					table.insert(
						diffs,
						string.format("zmena_owneru:%s:%s->%s", tostring(id), tostring((r :: any).owner), tostring((c :: any).owner))
					)
				end
			end
		end
		for id, _ in curRoots do
			if (snap.roots :: any)[id] == nil then
				table.insert(diffs, "novy_root:" .. tostring(id))
			end
		end
		-- #AV/#BV pocty
		local av, bv = 0, 0
		for _, d in veh:GetDescendants() do
			if d:IsA("HingeConstraint") then
				if d.Name == "#AV" then
					av += 1
				elseif d.Name == "#BV" then
					bv += 1
				end
			end
		end
		if av ~= (snap.av :: number) then
			table.insert(diffs, string.format("pocet_AV:%s->%s", tostring(snap.av), tostring(av)))
		end
		if bv ~= (snap.bv :: number) then
			table.insert(diffs, string.format("pocet_BV:%s->%s", tostring(snap.bv), tostring(bv)))
		end
	end)
	return #diffs == 0, diffs
end

-- Relativni natoceni ridiciho cepu vuci zakladne (D3/AC4): {sada=stupne}.
function ServerSteer.MeasureAngles(vehicle: Instance?): ({ [string]: number }?, string?)
	if vehicle == nil then
		return nil, "chybi_vozidlo"
	end
	local out: { [string]: number } = {}
	local fail: string? = nil
	pcall(function()
		local veh = vehicle :: Instance
		local wheels = veh:FindFirstChild("Wheels", true)
		if wheels == nil then
			fail = "chybi_Wheels"
			return
		end
		for _, setName in STEER_SETS do
			local folder = (wheels :: Instance):FindFirstChild(setName)
			if folder == nil then
				continue
			end
			local arm = folder:FindFirstChild("Arm")
			local steerP = arm and arm:FindFirstChild("Steer")
			local base = folder:FindFirstChild("Base")
			if arm == nil or steerP == nil or base == nil then
				fail = "nekompletni_sada:" .. setName
				return
			end
			local rel: CFrame = ((base :: BasePart).CFrame:ToObjectSpace((steerP :: BasePart).CFrame))
			local _rx, ry, _rz = rel:ToOrientation()
			out[setName] = math.deg(ry)
		end
	end)
	if fail ~= nil then
		return nil, fail
	end
	return out, nil
end

-- Hlavni krok rizeni: steerT (-1..1, uz validovane/clampnute), dt ze Heartbeat.
-- Vraci (true) nebo (false, duvod). Fail-closed: zadny castecny zapis na kola.
function ServerSteer.Step(vehicle: Instance?, steerT: number?, dtRaw: number?): (boolean, string?)
	if vehicle == nil then
		return false, "chybi_vozidlo"
	end
	local veh = vehicle :: Instance
	local tune = sdReadTune(veh)
	if tune == nil then
		return false, "chybi_Tune"
	end
	if tune.SteeringType ~= "New" then
		return false, "steering_type_ne_new:" .. tostring(tune.SteeringType)
	end
	for _, k in { "SteerSpeed", "ReturnSpeed", "SteerDecay", "MinSteer", "SteerRatio", "LockToLock", "Ackerman", "SteerInner" } do
		if typeof(tune[k]) ~= "number" then
			return false, "chybi_Tune_klic:" .. k
		end
	end
	local seat = sdReadSeat(veh)
	if seat == nil then
		return false, "chybi_DriveSeat"
	end
	local st = ServerSteer._states[veh]
	if st == nil or st.tune ~= tune then
		st = { steerC = 0, tune = tune }
		ServerSteer._states[veh] = st
	end
	local cmd = 0
	if typeof(steerT) == "number" then
		cmd = math.max(-1, math.min(1, steerT :: number))
	end
	-- D1: dt-strop (ticks=min(dt*60,0,3)); bezny provoz = matematicka ekvivalence.
	local ticks = 1
	if typeof(dtRaw) == "number" and (dtRaw :: number) > 0 then
		ticks = math.min((dtRaw :: number) * 60, ServerSteer.MAXTICKS)
	end
	-- Rampa (doslovny Drive 344-356).
	local sc: number = st.steerC
	if sc < cmd then
		sc = if sc < 0 then math.min(cmd, sc + (tune.ReturnSpeed :: number) * ticks) else math.min(cmd, sc + (tune.SteerSpeed :: number) * ticks)
	else
		sc = if sc > 0 then math.max(cmd, sc - (tune.ReturnSpeed :: number) * ticks) else math.max(cmd, sc - (tune.SteerSpeed :: number) * ticks)
	end
	st.steerC = sc
	-- Konstanty (Drive 325-326) + sDecay (Drive 359).
	local outer: number = (tune.LockToLock * 180) / tune.SteerRatio
	local inner: number = math.min(outer - (outer * (1 - tune.Ackerman)), outer * 1.2)
	local vmag = 0
	pcall(function()
		vmag = (seat :: VehicleSeat).AssemblyLinearVelocity.Magnitude
	end)
	local sDecay: number = 1 - math.min(vmag / (tune.SteerDecay :: number), 1 - ((tune.MinSteer :: number) / 100))
	-- Dvoufasove: validuj vsechny pritomne sady, pak zapis (zadny castecny).
	local wheels: Instance? = nil
	pcall(function()
		wheels = veh:FindFirstChild("Wheels", true)
	end)
	if wheels == nil then
		return false, "chybi_Wheels"
	end
	type SteerJob = { steer: BasePart, base: BasePart, deg: number }
	local jobs: { SteerJob } = {}
	local found = 0
	for _, setName in STEER_SETS do
		local folder: Instance? = nil
		pcall(function()
			folder = (wheels :: Instance):FindFirstChild(setName)
		end)
		if folder == nil then
			continue
		end
		found += 1
		local arm: Instance? = nil
		local steerP: Instance? = nil
		local base: Instance? = nil
		pcall(function()
			arm = (folder :: Instance):FindFirstChild("Arm")
			if arm ~= nil then
				steerP = (arm :: Instance):FindFirstChild("Steer")
			end
			base = (folder :: Instance):FindFirstChild("Base")
		end)
		if arm == nil or steerP == nil or base == nil then
			return false, "nekompletni_sada:" .. setName
		end
		if not (steerP :: Instance):IsA("BasePart") or not (base :: Instance):IsA("BasePart") then
			return false, "steer_base_nejenom_part:" .. setName
		end
		local deg: number
		if setName == "F" then
			deg = -math.deg(sc * (tune.SteerInner :: number) * sDecay) -- doslovne Drive 365
		elseif setName == "FL" then
			deg = if sc >= 0 then -math.deg(sc * outer * sDecay) else -math.deg(sc * inner * sDecay)
		else -- FR
			deg = if sc >= 0 then -math.deg(sc * inner * sDecay) else -math.deg(sc * outer * sDecay)
		end
		table.insert(jobs, { steer = steerP :: BasePart, base = base :: BasePart, deg = deg })
	end
	if found == 0 then
		return false, "zadna_predni_sada"
	end
	for _, j in jobs do
		local okW = pcall(function()
			(j.steer :: BasePart).CFrame = (j.base :: BasePart).CFrame * CFrame.Angles(0, math.rad(j.deg :: number), 0)
		end)
		if not okW then
			return false, "zapis_CFrame_selhal"
		end
	end
	-- Publikace: AE_SteerC (telemetrie/D3/AC4) + Values.SteerC (SS6 kanal).
	pcall(function()
		veh:SetAttribute("AE_SteerC", sc)
	end)
	local vals: Instance? = nil
	pcall(function()
		vals = veh:FindFirstChild("Values", true)
	end)
	local sv: Instance? = nil
	if vals ~= nil then
		pcall(function()
			sv = (vals :: Instance):FindFirstChild("SteerC")
		end)
	end
	if sv ~= nil and (sv :: Instance):IsA("NumberValue") then
		pcall(function()
			(sv :: NumberValue).Value = sc
		end)
	elseif ServerSteer._warnedValues[veh] ~= true then
		ServerSteer._warnedValues[veh] = true
		warn("[AE_SERVER_STEER] chybi Values.SteerC (SS6 friction neuvidi rejd)")
	end
	return true, nil
end

-- Settle: po zruseni entry pokracovat Step(steerT=0) az do narovnani.
function ServerSteer.Settle(vehicle: Instance?): ()
	if vehicle == nil then
		return
	end
	ServerSteer._settling[vehicle :: Instance] = true
end

-- Forget: vozidlo pryc / plny uklid po narovnani.
function ServerSteer.Forget(vehicle: Instance?): ()
	if vehicle == nil then
		return
	end
	ServerSteer._settling[vehicle :: Instance] = nil
	ServerSteer._states[vehicle :: Instance] = nil
	ServerSteer._warnedValues[vehicle :: Instance] = nil
end

-- Seznam vozidel cekajicich na dorovnani (snapshot pro smycku).
function ServerSteer.SettlingList(): { Instance }
	local out: { Instance } = {}
	for vehicle, _ in ServerSteer._settling do
		table.insert(out, vehicle)
	end
	return out
end

-- Narovnano: stav chybi nebo |steerC| pod prahem (kolo nasleduje automaticky,
-- protoze Step pise absolutni CFrame kazdy tick).
function ServerSteer.IsCentered(vehicle: Instance?): boolean
	if vehicle == nil then
		return true
	end
	local st = ServerSteer._states[vehicle :: Instance]
	if st == nil then
		return true
	end
	return math.abs(st.steerC) <= ServerSteer.CENTER_STEERC
end

function ServerSteer.GetSteerC(vehicle: Instance?): number?
	if vehicle == nil then
		return nil
	end
	local st = ServerSteer._states[vehicle :: Instance]
	if st == nil then
		return nil
	end
	return st.steerC
end

-- F4.4 F3 / F5-A arbitrace: zapis ridiciho vystupu do atributu vozu (server->klient replikace).
-- Drive mustek (VehicleManager.ApplyDriveInputBridge) v Heartbeat smycce PREBIRA pritomne
-- atributy do _IBrake/_IThrot/_GSteerT: server je JEDINY urcujici zapisovac (autonomni rezim).
-- nil = atribut se SMAZE a prislusna osa se vrati do manualniho rezimu (klavesy/gamepad).
-- Zadny jiny vstup se tu nemeni; sedadlo se nepouziva (Drive ho v tomto buildu necte).
-- Diagnostika pozadovane-vs-skutecne brzdy BEZ noveho kanalu (novy kanal vlastni Agent C):
-- pozadovana hodnota je v telemetrii v existujicim kanalu `inputs.brake` (toteze hodnoty,
-- jake dostava TelemetryCollector:SetInputs); skutecnou brzdu publikuje Drive kazdy frame
-- v existujicim Values.Brake (_GBrake). Trvalou neshodu hlasi CheckBrakeDiag jednim warn (zadny
-- zapis fyziky, zadny novy kanal, zadny novy atribut).
-- F5-A: tolerance a perzistence read-back diagnostiky brzdy (vzorky volani WriteDriveAttributes).
ScenarioRunner.BRAKE_DIAG_TOL = 0.08
ScenarioRunner.BRAKE_DIAG_SAMPLES = 45
ScenarioRunner._brakeDiagState = {}
function ScenarioRunner.WriteDriveAttributes(vehicle: Instance?, throttle: number?, brake: number?, steer: number?, scenarioKind: string?): ()
	if vehicle == nil then
		return
	end
	local kind = if typeof(scenarioKind) == "string" then scenarioKind else "unknown"
	-- F7.1-T03-guard: v T03 je plyn vzdy 0 (baseline nesmi uhnout; assert).
	-- Plyn je povolen jen straight_accel (replay T01/T02), straight_accel_brake
	-- (T01B collision-free) a manual (zive rizeni pres AEDriveCmd); jinde se ignoruje. Steer server do F7.2 nepouziva.
	if typeof(throttle) == "number" and (throttle :: number) > 0 then
		if kind == "straight_brake_100_0" then
			if ServerDrive._guardWarned[vehicle] ~= true then
				ServerDrive._guardWarned[vehicle] = true
				warn("[AE_THROTTLE_GUARD] plyn v T03 ignorovan (baseline ochrana)")
			end
			throttle = 0
		elseif kind ~= "straight_accel" and kind ~= "straight_accel_brake" and kind ~= "manual" then
			if ServerDrive._guardWarned[vehicle] ~= true then
				ServerDrive._guardWarned[vehicle] = true
				warn(string.format("[AE_THROTTLE_GUARD] plyn ignorovan:kind=%s (povolen jen straight_accel/straight_accel_brake/manual)", kind))
			end
			throttle = 0
		end
	end
	pcall(function()
		if throttle == nil then
			vehicle:SetAttribute("AE_Throttle", nil)
		else
			vehicle:SetAttribute("AE_Throttle", throttle)
		end
		if brake == nil then
			vehicle:SetAttribute("AE_Brake", nil)
		else
			vehicle:SetAttribute("AE_Brake", brake)
		end
		if steer == nil then
			vehicle:SetAttribute("AE_Steer", nil)
		else
			vehicle:SetAttribute("AE_Steer", steer)
		end
	end)
	-- F7.1-T01B: diagnostika Values.Brake se preskakuje — server-brzda
	-- (ApplyServerBrake) obchazi klientsky bridge zamerne; overuje ji v-decay.
	if kind ~= "straight_accel_brake" then
		ScenarioRunner.CheckBrakeDiag(vehicle, brake)
	end
	-- Konec behu (nil,nil,nil = navrat do manualu): reset server-pohonu.
	-- F7.2: steering stav preziva (Settle dorovna pres ReturnSpeed), viz AC6.
	if throttle == nil and brake == nil and steer == nil then
		ServerDrive.Reset(vehicle)
		ServerSteer.Settle(vehicle)
	end
	-- F7.1: plyn>0 v straight_accel -> server-autoritativni pohon (ServerDrive,
	-- verny port Drive: #AV moment + #BV plna formule vcetne EBrake/tqABS).
	-- Jinak legacy brzdna cesta (F6-D, cisla beze zmeny; T03 vzdy tudy).
	if typeof(throttle) == "number" and (throttle :: number) > 0 then
		local ok, err = ServerDrive.Step(vehicle, throttle :: number, if typeof(brake) == "number" then brake :: number else 0)
		if not ok then
			warn(string.format("[AE_SERVER_DRIVE] %s", tostring(err)))
		end
		return
	end
	-- F6-D: server aplikuje brzdny moment primo (brake==nil = manual, nesaha).
	if brake ~= nil then
		ScenarioRunner.ApplyServerBrake(vehicle, brake)
	end
end

-- F5-A: read-only read-back pozadovane (AE_Brake) vs skutecne (Values.Brake) brzdy.
-- Volano z WriteDriveAttributes (vzorkovaci frekvence harnessu); zadny zapis, zadny spawn.
-- Neshoda trvajici BRAKE_DIAG_SAMPLES po sobe jdoucich volani = jeden warn na beh (latch).
-- Values/Drive jeste nebezi => zadny zaver (cekam). Vycisteni pri brake == nil (konec behu).
function ScenarioRunner.CheckBrakeDiag(vehicle: Instance?, brakeCmd: number?): ()
	if vehicle == nil then
		return
	end
	if brakeCmd == nil then
		ScenarioRunner._brakeDiagState[vehicle] = nil
		return
	end
	local st: any = ScenarioRunner._brakeDiagState[vehicle]
	if st == nil then
		st = { mism = 0, warned = false }
		ScenarioRunner._brakeDiagState[vehicle] = st
	end
	if st.warned then
		return
	end
	local ok, actual = pcall(function()
		local values = (vehicle :: Instance):FindFirstChild("Values", true)
		if values == nil then
			return nil
		end
		local b = (values :: Instance):FindFirstChild("Brake")
		if b ~= nil and b:IsA("NumberValue") then
			return (b :: NumberValue).Value
		end
		return nil
	end)
	if not ok or actual == nil then
		return
	end
	if math.abs((actual :: number) - (brakeCmd :: number)) > ScenarioRunner.BRAKE_DIAG_TOL then
		st.mism = st.mism + 1
	else
		st.mism = 0
	end
	if st.mism >= ScenarioRunner.BRAKE_DIAG_SAMPLES then
		st.warned = true
		warn(
			string.format(
				"[AE_BRAKE_DIAG] pozadovano AE_Brake=%.3f vs skutecne Values.Brake=%.3f (trva >=%d vzorku)",
				brakeCmd :: number,
				actual :: number,
				ScenarioRunner.BRAKE_DIAG_SAMPLES
			)
		)
	end
end

-- F6-D: server-autoritativni brzda (vlastnik fyziky).
-- F7.1: brzdna cesta je LEGACY (cisla beze zmeny; T03 a vse s throttle==0
-- tudy vzdy). Plyn resi ServerDrive.Step (verny port Drive) volany
-- z WriteDriveAttributes pri throttle>0 v straight_accel.
-- Pricina (run-003): pri server-nil ownership klientsky Drive sice bezi
-- (V1/V2 mosty, Values zrcadla), ale jeho zapisy motoru (#AV/#BV) se na
-- serverem vlastnenych dilech NEAPLIKUJI (overeno obema smery: server 200 vs
-- klient 0). Brzdeni videne ve F5 byla zablokovana-kola scrub (BV zamrzle na
-- Initialize defaultu 5000), ne ucinek rampy. Proto brzdi PRIMO server:
-- kazdy tick behu + kazde nulovani zapise #BV moment dle Tune
-- (brzdna slozka vzorce Drive; bez ABS-emulace a bez EBrake/PBrake slozek)
-- a #AV moment 0 (T03 nema plyn; ostatni scenare serverem nejezdi).
-- Klientsky Drive tim nekonfliktuje (jeho zapisy se zahazuji).
-- Manualni rezim (brake==nil) server nesaha.
-- F7.1-K1: presny front/rear matcher. Kola jsou FL/FR/F (predni) a RL/RR/R
-- (zadni) -- viz Drive Initialize:405/:434 a steering :364-:429 (presna
-- rovnost, ne substring). Neznamy nazev = fail-closed (false + duvod),
-- nikdy tiche rear. Duvod: substring "F" trefi cokoli s pismenem F.
function ScenarioRunner.IsFrontWheel(name: string): (boolean, string?)
	if name == "FL" or name == "FR" or name == "F" then
		return true, nil
	elseif name == "RL" or name == "RR" or name == "R" then
		return false, nil
	end
	return false, string.format("kolo_nerozpoznano:%s", tostring(name))
end
function ScenarioRunner.ReadBrakeForceConfig(vehicle: Instance?): (number?, number?)
	if vehicle == nil then
		return nil, nil
	end
	local ok, fb, rb = pcall(function()
		local tune = (vehicle :: Instance):FindFirstChild("A-Chassis Tune", true)
		if tune == nil or not (tune :: Instance):IsA("ModuleScript") then
			return nil, nil
		end
		local tt = require(tune :: ModuleScript)
		if typeof(tt) ~= "table" then
			return nil, nil
		end
		local force = (tt :: any).BrakeForce
		local bias = (tt :: any).BrakeBias
		if typeof(force) ~= "number" or typeof(bias) ~= "number" then
			return nil, nil
		end
		return (force :: number) * (bias :: number), (force :: number) * (1 - (bias :: number))
	end)
	if not ok then
		return nil, nil
	end
	return fb, rb
end

function ScenarioRunner.ApplyServerBrake(vehicle: Instance?, brake01: number?): (boolean, string?)
	if vehicle == nil then
		return false, "chybi_vozidlo"
	end
	local b = if typeof(brake01) == "number" then math.max(0, math.min(1, brake01 :: number)) else 0
	local fb, rb = ScenarioRunner.ReadBrakeForceConfig(vehicle)
	if fb == nil or rb == nil then
		return false, "brzdny_moment_neoveren:chybi_BrakeForce/BrakeBias_v_Tune"
	end
	local fps = 60
	pcall(function()
		fps = game:GetService("Workspace"):GetRealPhysicsFPS()
	end)
	if typeof(fps) ~= "number" or (fps :: number) <= 0 then
		fps = 60
	end
	local factor = 60 / (fps :: number)
	local count = 0
	pcall(function()
		local wheels = (vehicle :: Instance):FindFirstChild("Wheels", true)
		local parts: { Instance } = if wheels ~= nil then wheels:GetChildren() else (vehicle :: Instance):GetDescendants()
		for _, w in parts do
			if w:IsA("BasePart") then
				-- F7.1-K1: presny matcher (FL/FR/F = predni); neznamy nazev
				-- = fail-closed rear + duvod (misto ticheho prehozeni biasu).
				local isF, fErr = ScenarioRunner.IsFrontWheel(w.Name)
				if fErr ~= nil then
					warn(string.format("[AE_K1] %s (kolo %s povazovano za zadni)", tostring(fErr), tostring(w:GetFullName())))
				end
				for _, h in w:GetChildren() do
					if h:IsA("HingeConstraint") and h.Name == "#BV" then
						h.MotorMaxTorque = (if isF then (fb :: number) else (rb :: number)) * factor * b
						count += 1
					elseif h:IsA("HingeConstraint") and h.Name == "#AV" then
						h.MotorMaxTorque = 0
					end
				end
			end
		end
	end)
	if count == 0 then
		return false, "brzdny_moment_nezapsan:zadne_#BV_nenalezeno"
	end
	return true, nil
end

-- F5-FX2 stuck-brake: EXPLICITNI nulovani AE_Brake/AE_Throttle/AE_Steer
-- (WriteDriveAttributes 0,0,0) + overeni zpetnym prectenim. nil atribut
-- posledni prikaz nemaze (klientsky _IBrake drzi 1.0 i po briefu, F4-F1.0),
-- proto se pise 0, ne nil. Vraci (true) nebo (false, duvod).
function ScenarioRunner.ClearDriveInputs(vehicle: Instance?): (boolean, string?)
	if vehicle == nil then
		return false, "chybi_vozidlo"
	end
	ScenarioRunner.WriteDriveAttributes(vehicle, 0, 0, 0)
	-- F7.1: s nulovanim vstupu reset server-pohonu (gear/RPM/rampa/stav + AE_* atributy).
	ServerDrive.Reset(vehicle)
	-- F7.2: steering entry zruseno, stav preziva a dorovna pres Settle (AC6).
	ServerSteer.Settle(vehicle)
	local ok, b, t, s = pcall(function()
		return (vehicle :: Instance):GetAttribute("AE_Brake"),
			(vehicle :: Instance):GetAttribute("AE_Throttle"),
			(vehicle :: Instance):GetAttribute("AE_Steer")
	end)
	if not ok then
		return false, "vstupni_nuly_neovereny:GetAttribute_selhalo"
	end
	if b ~= 0 or t ~= 0 or s ~= 0 then
		return false,
			string.format(
				"vstupni_nuly_neovereny:AE_Brake=%s_AE_Throttle=%s_AE_Steer=%s",
				tostring(b),
				tostring(t),
				tostring(s)
			)
	end
	return true, nil
end

-- F5-FX2 spawn-settle-go: po Deploy + nulovani rychlosti cekej, dokud
-- |vertikalni rychlost| < SETTLE_VSPEED_TOL AND |roll| < T03_ROLL_TOL_DEG
-- (max SETTLE_MAX_S, krok 0.1 s), pak teprve armuj mereni.
-- Vraci (true) pri usednuti, (false, duvod) pri timeoutu (volajici voiduje).
function ScenarioRunner.WaitForSettle(vehicle: Instance?): (boolean, string?)
	local deadline = os.clock() + ScenarioRunner.SETTLE_MAX_S
	while true do
		local vy = ScenarioRunner.ReadVerticalSpeed(vehicle)
		local roll = ScenarioRunner.ReadStartRollDeg(vehicle)
		if
			vy ~= nil
			and roll ~= nil
			and vy < ScenarioRunner.SETTLE_VSPEED_TOL
			and math.abs(roll) < ScenarioRunner.T03_ROLL_TOL_DEG
		then
			return true, nil
		end
		if os.clock() >= deadline then
			return false, string.format("settle_timeout:vy=%s_roll=%s", tostring(vy), tostring(roll))
		end
		task.wait(0.1)
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
	-- T03 (straight_brake_100_0): completion dle ScenarioDefinitions --
	-- "rychlost < 0.1 studs/s + 1 s ustaleni". Rychlost = XZ slozka (vodorovna
	-- rovina; Y ignorujeme). Po prvnim poklesu pod 0.1 se ceka 1.0 s, pak completed.
	-- Timeout (duration_s) zustava zaloznim koncem (neuplny beh s vlajkou).
	if (if def ~= nil then def.kind else nil) == "straight_brake_100_0" then
		local v = ScenarioRunner.XzSpeed(if sample.vel ~= nil then sample.vel else nil)
		if v ~= nil then
			if v < 0.1 then
				if self.stopT == nil then
					self.stopT = t
				end
				if t - (self.stopT :: number) >= 1.0 then
					return "completed"
				end
			else
				self.stopT = nil
			end
		end
	end
	-- F7.1-T01B (straight_accel_brake): gate + dobrzdeni pred zdi.
	-- Prekonani gate (pos.x >= gate_x) + rychlost < 0.1 + 1 s ustaleni
	-- => completed s completionReason 'finish_gate_crossed'.
	-- x >= wall_fail_x => failed (pojistka pred kontaktem se zdi).
	if (if def ~= nil then def.kind else nil) == "straight_accel_brake" then
		local gateX = 2510
		local wallX = 3600
		if def ~= nil then
			if typeof((def :: any).gate_x) == "number" then
				gateX = (def :: any).gate_x
			end
			if typeof((def :: any).wall_fail_x) == "number" then
				wallX = (def :: any).wall_fail_x
			end
		end
		local px: number? = nil
		if sample.pos ~= nil and typeof((sample.pos :: any).x) == "number" then
			px = (sample.pos :: any).x
		end
		local v = ScenarioRunner.XzSpeed(if sample.vel ~= nil then sample.vel else nil)
		if px ~= nil and (px :: number) >= wallX then
			self.failReason = "wall_fail:blizkost_zdi"
			return "failed"
		end
		if self.gateT == nil and px ~= nil and (px :: number) >= gateX then
			self.gateT = t
			self.gateV = v
		end
		if self.gateT ~= nil and v ~= nil and (v :: number) < 0.1 then
			if self.stopT == nil then
				self.stopT = t
			end
			if t - (self.stopT :: number) >= 1.0 then
				self.completionReason = "finish_gate_crossed"
				return "completed"
			end
		else
			self.stopT = nil
		end
	end
	if t >= (def.duration_s or 30) then
		if (if def ~= nil then def.kind else nil) == "straight_accel_brake" then
			-- F7.1-T01B: timeout bez gate NENI dokonceni (zadny falesny PASS).
			self.failReason = "timeout_bez_gate"
			return "failed"
		end
		return "completed"
	end
	return "running"
end

function ScenarioRunner:Finish(status: string, reason: string?, vehicle: Instance?): ()
	if status == "completed" then
		self.state = ScenarioRunner.State.COMPLETED
	else
		self.state = ScenarioRunner.State.FAILED
	end
	self.failReason = reason
	-- F5-FX2 stuck-brake: na konci behu EXPLICITNE nuluj vstupy
	-- (0,0,0 + overeni; best-effort — volajici muze overit sam).
	if vehicle ~= nil then
		pcall(function()
			ScenarioRunner.ClearDriveInputs(vehicle)
		end)
	end
end

-- XZ slozka vektoru {x,y,z} (vodorovna rychlost / vzdalenost); nil pri chybejicich datech.
function ScenarioRunner.XzSpeed(v: any): number?
	if typeof(v) ~= "table" or typeof(v.x) ~= "number" or typeof(v.z) ~= "number" then
		return nil
	end
	return math.sqrt(v.x * v.x + v.z * v.z)
end

function ScenarioRunner.XzSegment(a: any, b: any): number?
	if typeof(a) ~= "table" or typeof(b) ~= "table" then
		return nil
	end
	if typeof(a.x) ~= "number" or typeof(a.z) ~= "number" then
		return nil
	end
	if typeof(b.x) ~= "number" or typeof(b.z) ~= "number" then
		return nil
	end
	local dx = b.x - a.x
	local dz = b.z - a.z
	return math.sqrt(dx * dx + dz * dz)
end

-- T03 metriky z XZ telemetrie (vzorky TelemetryCollector: pos{x,y,z}, vel{x,y,z},
-- accel?, yaw_rate?, abs_active?). Vraci (metrics, nil) nebo (nil, reason).
--   brake_distance_studs: kumulativni XZ draha od prvniho vzorku do prvniho
--     vzorku s XZ-rychlosti < 0.1 (prah zastaveni dle ScenarioDefinitions T03).
--   stopping_time_s: cas t tohoto vzorku (od zacatku brzdneho replaye t=0).
--   mean_decel_studs_s2: v0/stopping_time (v0 = XZ rychlost prvniho vzorku).
--   peak_decel_studs_s2: maximum XZ slozky accel pres vzorky do zastaveni
--     (nil, chybi-li accel kanal).
--   lat_deviation_studs: max |z - z0| (primy usek podel osy X; priblizne).
--   yaw_rate_max: max |yaw_rate| do zastaveni (nil, chybi-li kanal).
--   abs: { active = bool, active_samples = n } z existujiciho signalu
--     Values.ABSActive; chybi-li kanal ve vsech vzorcich,
--     { active = nil, reason = "chybi Values.ABSActive ve vozidle" }.
-- Nezastavi-li vuz do konce zaznamu: stopped=false + draha/cas do konce zaznamu
-- (neuplny beh; agregace takovy beh oznacuje).
function ScenarioRunner.ComputeT03Metrics(samples: any): (any?, string?)
	if typeof(samples) ~= "table" or #samples == 0 then
		return nil, "prazdne_vzorky"
	end
	local first = samples[1]
	local v0 = ScenarioRunner.XzSpeed(if first ~= nil then first.vel else nil)
	if v0 == nil then
		return nil, "chybi_vel_v_prvnim_vzorku"
	end
	local dist = 0
	local distAtStop: number? = nil
	local stopT: number? = nil
	local peakDecel = 0
	local peakKnown = false
	local yawMax = 0
	local yawKnown = false
	local latDev = 0
	local x0Known = typeof(first.pos) == "table" and typeof(first.pos.z) == "number"
	local absKnown = false
	local absSeen = false
	local absSamples = 0
	local prevPos = if typeof(first.pos) == "table" then first.pos else nil
	for i = 2, #samples do
		local s = samples[i]
		if typeof(s) ~= "table" then
			continue
		end
		local seg = ScenarioRunner.XzSegment(prevPos, s.pos)
		if seg ~= nil then
			dist += seg
		end
		if typeof(s.pos) == "table" then
			prevPos = s.pos
		end
		if typeof(s.accel) == "table" then
			local a = ScenarioRunner.XzSpeed(s.accel)
			if a ~= nil then
				peakKnown = true
				peakDecel = math.max(peakDecel, a)
			end
		end
		if typeof(s.yaw_rate) == "number" then
			yawKnown = true
			yawMax = math.max(yawMax, math.abs(s.yaw_rate))
		end
		if x0Known and typeof(s.pos) == "table" and typeof(s.pos.z) == "number" then
			latDev = math.max(latDev, math.abs(s.pos.z - (first.pos :: any).z))
		end
		if s.abs_active ~= nil then
			absKnown = true
			if s.abs_active == true then
				absSeen = true
				absSamples += 1
			end
		end
		if stopT == nil and typeof(s.t) == "number" then
			local v = ScenarioRunner.XzSpeed(s.vel)
			if v ~= nil and v < 0.1 then
				stopT = s.t
				distAtStop = dist
			end
		end
	end
	local stopped = stopT ~= nil
	local brakeDist = if distAtStop ~= nil then distAtStop else dist
	local stopTime = if stopT ~= nil then stopT else (samples[#samples] :: any).t
	local abs: any
	if absKnown then
		abs = { active = absSeen, active_samples = absSamples }
	else
		abs = { active = nil, reason = "chybi Values.ABSActive ve vozidle (Drive signal nezapsal)" }
	end
	return {
		stopped = stopped,
		brake_distance_studs = brakeDist,
		stopping_time_s = stopTime,
		mean_decel_studs_s2 = if stopT ~= nil and (stopT :: number) > 0 then v0 / (stopT :: number) else nil,
		peak_decel_studs_s2 = if peakKnown then peakDecel else nil,
		lat_deviation_studs = latDev,
		yaw_rate_max = if yawKnown then yawMax else nil,
		initial_speed_studs_s = v0,
		abs = abs,
	},
		nil
end

-- F7.1-T01B: metriky gate + dobrzdeni (pocitano z plnych vzorku, ne decimace).
-- Vraci { gate_crossed, t_gate_s, v_cut_studs_s, x_stop_studs,
-- brake_start_x_studs, brake_distance_studs, lat_deviation_studs, vmax_studs_s }.
function ScenarioRunner.ComputeT01BMetrics(samples: any, def: any): (any?, string?)
	if typeof(samples) ~= "table" or #samples == 0 then
		return nil, "prazdne_vzorky"
	end
	local gateX = 2510
	if def ~= nil and typeof((def :: any).gate_x) == "number" then
		gateX = (def :: any).gate_x
	end
	local gateT: number? = nil
	local gateV: number? = nil
	local vmax = 0
	local xStop = 0
	local xStopKnown = false
	local brakeStartX: number? = nil
	local latDev = 0
	local z0: number? = nil
	local first = samples[1]
	if typeof(first) == "table" and typeof(first.pos) == "table" and typeof((first.pos :: any).z) == "number" then
		z0 = (first.pos :: any).z
	end
	for _, s in samples do
		if typeof(s) ~= "table" then
			continue
		end
		local v = ScenarioRunner.XzSpeed((s :: any).vel)
		if v ~= nil then
			vmax = math.max(vmax, v)
		end
		if typeof((s :: any).pos) == "table" and typeof((((s :: any).pos) :: any).x) == "number" then
			local px = ((((s :: any).pos) :: any).x :: number)
			xStop = math.max(xStop, px)
			xStopKnown = true
			if gateT == nil and px >= gateX then
				gateT = if typeof((s :: any).t) == "number" then ((s :: any).t :: number) else nil
				gateV = v
			end
		end
		if brakeStartX == nil and typeof((s :: any).inputs) == "table" then
			local b = (((s :: any).inputs) :: any).brake
			if typeof(b) == "number" and (b :: number) > 0 then
				if typeof((s :: any).pos) == "table" and typeof((((s :: any).pos) :: any).x) == "number" then
					brakeStartX = ((((s :: any).pos) :: any).x :: number)
				end
			end
		end
		if z0 ~= nil and typeof((s :: any).pos) == "table" and typeof((((s :: any).pos) :: any).z) == "number" then
			latDev = math.max(latDev, math.abs(((((s :: any).pos) :: any).z :: number) - (z0 :: number)))
		end
	end
	local brakeDist: number? = nil
	if brakeStartX ~= nil and xStopKnown then
		brakeDist = xStop - (brakeStartX :: number)
	end
	return {
		gate_crossed = gateT ~= nil,
		t_gate_s = gateT,
		v_cut_studs_s = gateV,
		x_stop_studs = if xStopKnown then xStop else nil,
		brake_start_x_studs = brakeStartX,
		brake_distance_studs = brakeDist,
		lat_deviation_studs = latDev,
		vmax_studs_s = vmax,
	},
		nil
end

return ScenarioRunner
