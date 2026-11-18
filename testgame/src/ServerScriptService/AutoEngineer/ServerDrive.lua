-- ServerDrive: server-autoritativni pohon, verny port A-Chassis Drive
-- (Build 6C, Template verze v JeepTemplate.rbxm) pro server-nil ownership.
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

local function readTune(vehicle: Instance?): any?
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

local function readWheels(vehicle: Instance?): { BasePart }
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

local function readSeat(vehicle: Instance?): VehicleSeat?
	local seat: VehicleSeat? = nil
	pcall(function()
		seat = (vehicle :: Instance):FindFirstChild("DriveSeat", true) :: any
		if seat ~= nil and not (seat :: any):IsA("VehicleSeat") then
			seat = nil
		end
	end)
	return seat
end

local function curveN(rpmThousands: number, p: any): number
	local hp = p.hp
	local peak = p.peak
	local sharp = p.sharp
	local cmult = p.cmult
	return ((-(rpmThousands - peak) ^ 2) * math.min(hp / (peak ^ 2), cmult ^ (peak / hp)) + hp)
		* (rpmThousands - ((rpmThousands ^ sharp) / (sharp * peak ^ (sharp - 1))))
end

-- Lokalni front-matcher (parita ScenarioRunner.IsFrontWheel; zadna zpetna
-- zavislost: ScenarioRunner require-uje tento modul).
local function isFrontWheel(name: string): boolean
	return name == "FL" or name == "FR" or name == "F"
end

-- Stav na vozidlo; Reset() pri zacatku/konci behu (ClearDriveInputs).
function ServerDrive.Reset(vehicle: Instance?)
	if vehicle == nil then
		return
	end
	ServerDrive._states[vehicle] = nil
	ServerDrive._guardWarned[vehicle] = nil
	pcall(function()
		(vehicle :: Instance):SetAttribute("AE_RPM", nil)
		(vehicle :: Instance):SetAttribute("AE_Gear", nil)
		(vehicle :: Instance):SetAttribute("AE_ThrotAct", nil)
		(vehicle :: Instance):SetAttribute("AE_BrakeAct", nil)
		(vehicle :: Instance):SetAttribute("AE_ABSActive", nil)
	end)
end

local function getState(vehicle: Instance, tune: any, now: number): any
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
	local peakCurveN = curveN(peak, p)
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
	local tune = readTune(vehicle)
	if tune == nil then
		return false, "chybi_Tune_v_kopii"
	end
	local wheels = readWheels(vehicle)
	if #wheels == 0 then
		return false, "zadna_kola_Wheels"
	end
	local seat = readSeat(vehicle)
	if seat == nil then
		return false, "chybi_DriveSeat"
	end

	local now = os.clock()
	local st = getState(vehicle, tune, now)
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
			st.tBoost += ((((((hpPrev * (bThrot * 1.2)) / tune.Horsepower) / 8) - ((st.tBoost / tpsi1 * (tpsi1 / 15)))) * ((8 / (tune.T_BoostLag / deltaTime)) * 2)) / tpsi1) * 15)
		else
			st.tBoost += ((((((hpPrev * (bThrot * 1.2)) / tune.Horsepower) / 8) - ((st.tBoost / tpsi1 * (tpsi1 / 15)))) * ((8 / (tune.T2_BoostLag / deltaTime)) * 2)) / tpsi1) * 15)
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
		local cN = curveN(x / 1000, cp)
		local hpN = (math.max(cN / (st.peakCurveN / cp.hp), 0)) * 100
		nt = ((hpN * (cp.eq / x)) * tune.Ratios[gearIdx] * st.fFD) * 1000
		local cT = curveN(x / 1000, {
			hp = st.hpT,
			peak = cp.peak,
			sharp = cp.sharp,
			cmult = cp.cmult,
			eq = cp.eq,
		})
		local peakT = curveN(cp.peak, {
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
	local cwspeed = (fws + rws) / 2
	local bias = (tune.TorqueVector + 1) / 2

	local fbF = tune.BrakeForce * tune.BrakeBias
	local fbR = tune.BrakeForce * (1 - tune.BrakeBias)
	local pbF = tune.PBrakeForce * tune.PBrakeBias
	local pbR = tune.PBrakeForce * (1 - tune.PBrakeBias)
	local throt = st.gThrot
	local brake = st.gBrake
	local clutchOut = 0
	if not st.clPressing then
		clutchOut = 1
	end

	local anyAV = false
	local countBV = 0
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
			diffF = math.ceil(math.max(0, math.min(2, 1 - (((tune.FDiffPower / 100) * avg * throt) + ((tune.FDiffCoast / 100) * avg * (1 - throt)))))) * 100) / 100
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
			diffF = math.ceil(math.max(0, math.min(2, 1 - (((tune.FDiffPower / 100) * avg * throt) + ((tune.FDiffCoast / 100) * avg * (1 - throt)))))) * 100) / 100
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
			diffR = math.ceil(math.max(0, math.min(2, 1 - (((tune.RDiffPower / 100) * avg * throt) + ((tune.RDiffCoast / 100) * avg * (1 - throt)))))) * 100) / 100
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
			diffR = math.ceil(math.max(0, math.min(2, 1 - (((tune.RDiffPower / 100) * avg * throt) + ((tune.RDiffCoast / 100) * avg * (1 - throt)))))) * 100) / 100
			diffF = 2 - diffR
		end
		local isF = isFrontWheel(w.Name)
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
			av.MotorMaxTorque = tqOUT * (if w.Name == "RR" then diffR elseif w.Name == "RL" then diffF elseif w.Name == "FR" then diffF elseif w.Name == "FL" then diffF else 1)
			av.AngularVelocity = st.spLimit
			anyAV = true
		end
		if bv ~= nil and bv:IsA("HingeConstraint") then
			local base = if isF then fbF else fbR
			local eb = tune.EBrakeForce * ((1 - throt) * (st.rpm / math.max(1, tune.Redline)))
			local pb = if isF then pbF else pbR
			bv.MotorMaxTorque = (base * factor * brake * tqABS) + eb + (pb * 0)
			countBV += 1
		end
	end
	if not anyAV then
		return false, "moment_nezapsan:zadne_#AV_nenalezeno"
	end

	-- Publikace stavu pro telemetrii (atributy; nil=manual mimo beh).
	pcall(function()
		(vehicle :: Instance):SetAttribute("AE_RPM", math.floor(st.rpm + 0.5))
		(vehicle :: Instance):SetAttribute("AE_Gear", st.gear)
		(vehicle :: Instance):SetAttribute("AE_ThrotAct", throt)
		(vehicle :: Instance):SetAttribute("AE_BrakeAct", brake)
		(vehicle :: Instance):SetAttribute("AE_ABSActive", st.absActive)
	end)
	return true, {
		rpm = st.rpm,
		gear = st.gear,
		spLimit = st.spLimit,
		outTorque = tq,
		tcs = st.tcsActive,
		abs = st.absActive,
		bvCount = countBV,
	}
end

return ServerDrive
