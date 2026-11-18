-- ScenarioDefinitions: scenare T01-T07 (FÁZE 9, runtime).
-- Kazdy scenar: id, pocatecni podminky, postup, completion/fail,
-- merene veliciny, opakovatelnost. Zdroj: docs/TESTING-OPTIMIZATION.md S1-S7.
-- Jazyk: komentarove cesky, identifikatory anglicky.

local ScenarioDefinitions = {}

ScenarioDefinitions.SCENARIO_VERSION = "1.0.0"
ScenarioDefinitions.SAMPLE_RATE_HZ = 60

-- Spolecna tolerance opakovatelnosti (prehluší per-scenar, pokud neuvedeno jinak).
ScenarioDefinitions.DEFAULT_REPEAT_TOL = {
	times_pct = 5, -- casy (0-100) +/-5 %
	distances_pct = 5, -- drahy (brzdeni) +/-5 %
	rms_pct = 10, -- RMS (vertikalni zrychleni, yaw) +/-10 %
}

ScenarioDefinitions.DEFINITIONS = {
	{
		scenario_id = "T01",
		name_cz = "Akcelerace 0-100",
		kind = "straight_accel",
		seed = 101,
		duration_s = 40,
		repetitions = 3,
		track = { shape = "straight", length_studs = 800, lane_half_width_studs = 4 },
		surface = "DRY_ASPHALT",
		initial_conditions = {
			speed_studs_s = 0,
			throttle = 0,
			brake = 0,
			steer = 0,
			gear = "auto",
			settle_s = 1.0,
		},
		procedure = "Z klidu plny plyn (rampa 0->1 za 0.2 s), volant 0, automaticke razeni. Merit do 100 studs/s + 3 s dojezd.",
		completion = "Dosazeno 100 studs/s a uplynuly 3 s dojezdu, nebo timeout 40 s (neuplne s vlajkou).",
		failure_abort = { "roll_deg_gt = 45", "opusteni pruhu > 2 m", "NaN v telemetrii", "timeout 40 s" },
		measurements = { "t_0_100_s", "t_0_60_s", "slip_ratio_max_launch", "gear_shift_count", "v_t_curve" },
		repeatability = "3 opakovanii, median; rozptyl casu do +/-5 %, jinak test neplatny.",
	},
	{
		scenario_id = "T01B",
		name_cz = "Akcelerace s gate a dobrzdenim pred zdi (collision-free)",
		kind = "straight_accel_brake",
		seed = 111,
		duration_s = 40,
		repetitions = 3,
		brake_start_x = 2500,
		gate_x = 2510,
		wall_fail_x = 3600,
		track = { shape = "straight", length_studs = 3800, lane_half_width_studs = 4 },
		surface = "DRY_ASPHALT",
		initial_conditions = {
			speed_studs_s = 0,
			throttle = 0,
			brake = 0,
			steer = 0,
			gear = "auto",
			settle_s = 1.0,
		},
		procedure = "Z klidu plny plyn (rampa 0->1 za 0.2 s) do x>=brake_start_x, pak plna server-brzda do zastaveni. Gate x>=gate_x musi byt prekonana.",
		completion = "Prekonani gate + rychlost < 0.1 studs/s + 1 s ustaleni => finish_gate_crossed. Timeout nebo x>=wall_fail_x => failed.",
		failure_abort = { "roll_deg_gt = 45", "opusteni pruhu > 2 m", "NaN v telemetrii", "x_ge_wall_fail_x", "timeout 40 s" },
		measurements = { "t_gate_s", "v_cut_studs_s", "x_stop_studs", "brake_distance_studs", "t_0_60_s", "t_0_100_s" },
		repeatability = "3 opakovani; rozptyl t_gate a x_stop do +/-5 % po warm-up.",
	},
	{
		scenario_id = "T02",
		name_cz = "Maximalni rychlost V-max",
		kind = "straight_accel",
		seed = 102,
		duration_s = 90,
		repetitions = 3,
		track = { shape = "straight", length_studs = 3000, lane_half_width_studs = 4 },
		surface = "DRY_ASPHALT",
		initial_conditions = {
			speed_studs_s = 0,
			throttle = 0,
			brake = 0,
			steer = 0,
			gear = "auto",
			settle_s = 1.0,
		},
		procedure = "Plny plyn od t=0, drzet primer; automaticke razeni az do ustaleni rychlosti.",
		completion = "Ustalena rychlost (std poslednich 5 s < 0.5 m/s ekv.) nebo timeout 90 s.",
		failure_abort = { "roll_deg_gt = 45", "yaw_rate_gt_30_degs_pri_prime_jizde", "opusteni pruhu > 2 m", "NaN" },
		measurements = { "v_max_studs_s", "t_to_vmax_s", "yaw_rate_rms_high_speed", "lat_deviation_rms" },
		repeatability = "3 opakovanii, median; dlouhy beh, kratsi ustaleni tolerovano vlajkou not_settled.",
	},
	{
		scenario_id = "T03",
		name_cz = "Brzdeni 100-0",
		kind = "straight_brake_100_0",
		seed = 103,
		duration_s = 20,
		repetitions = 3,
		track = { shape = "straight", length_studs = 800, lane_half_width_studs = 4 },
		surface = "DRY_ASPHALT",
		initial_conditions = {
			speed_studs_s = 100,
			throttle = 0,
			brake = 0,
			steer = 0,
			gear = "auto",
			settle_s = 1.0,
			entry_tol = 1.0,
		},
		procedure = "Ustalena rychlost 100 studs/s (+/-1), pak plna brzda (rampa 0->1 za 0.15 s), volant 0.",
		completion = "Rychlost < 0.1 studs/s + 1 s ustaleni, nebo timeout 20 s.",
		failure_abort = { "yaw_gt_90_deg_protoceni", "opusteni pruhu > 2 m", "prevraceni", "NaN" },
		measurements = {
			"brake_distance_studs",
			"stopping_time_s",
			"mean_decel",
			"peak_decel",
			"lat_deviation_braking",
			"yaw_rate_max_braking",
		},
		repeatability = "3 opakovanii na povrchu; rozptyl drahy do +/-5 %, jinak neplatny.",
	},
	{
		scenario_id = "T04",
		name_cz = "Konstantni polomer / skidpad",
		kind = "constant_radius_turn",
		seed = 104,
		duration_s = 25,
		repetitions = 3,
		track = { shape = "circle", radius_studs = 100, corridor_half_width_studs = 2 },
		surface = "DRY_ASPHALT",
		initial_conditions = {
			speed_studs_s = 40,
			throttle = 0,
			brake = 0,
			steer = 0,
			gear = "auto",
			settle_s = 1.0,
		},
		procedure = "Stopar drzi kruh R=100 studs; rychlost stupnovana po krocich, dokud neni dosazen limit (nedodrzeni polomeru nebo plateau lat_accel).",
		completion = "Odjeto 25 s nebo dosazen lateralni limit s vlajkou; koridor dodrzen.",
		failure_abort = { "vyjeti_z_koridoru_pm_2m", "smyk_beta_gt_20_deg", "prevraceni", "NaN" },
		measurements = {
			"a_lat_max_steady",
			"understeer_gradient",
			"steer_vs_lat_accel_curve",
			"yaw_vs_steer_coherence",
		},
		repeatability = "3 opakovani na rychlostni krok; vyzaduje min. 3 platne kroky pro gradient.",
	},
	{
		scenario_id = "T05",
		name_cz = "Dvojita zmena pruhu (losi test)",
		kind = "lane_change",
		seed = 105,
		duration_s = 20,
		repetitions = 3,
		track = { shape = "straight_cones", length_studs = 400, lane_half_width_studs = 4 },
		surface = "DRY_ASPHALT",
		initial_conditions = {
			speed_studs_s = 60,
			throttle = 0,
			brake = 0,
			steer = 0,
			gear = "auto",
			settle_s = 1.0,
		},
		procedure = "Vstupni rychlost 60 studs/s; replay profil natoceni volantu jako funkce drahy (identicke vstupy pro kazdou variantu).",
		completion = "Prujezd koridorem bez kontaktu s kuzely; zaznamenat max vstupni rychlost pri pruchodu.",
		failure_abort = { "kontakt_s_kuzelem", "roll_deg_gt = 45", "hodiny_yaw_gt_180_deg", "NaN" },
		measurements = { "passed_bool", "yaw_rate_overshoot", "sideslip_max", "roll_max", "settling_time_s" },
		repeatability = "3 opakovani na rychlost; vstupy bitove identicke (kontrola hashe vstupni sekvence).",
	},
	{
		scenario_id = "T06",
		name_cz = "Slalom",
		kind = "slalom",
		seed = 106,
		duration_s = 30,
		repetitions = 3,
		track = { shape = "slalom", cone_count = 10, spacing_studs = 60, corridor_half_width_studs = 2 },
		surface = "DRY_ASPHALT",
		initial_conditions = {
			speed_studs_s = 40,
			throttle = 0,
			brake = 0,
			steer = 0,
			gear = "auto",
			settle_s = 1.0,
		},
		procedure = "Stopar s preview (pure-pursuit, pevne parametry driver_version); prujezd 10 kuzely.",
		completion = "Prujezd cilem; cas a pocet naruseni koridoru zaznamenany.",
		failure_abort = { "prevraceni", "hodiny_yaw_gt_180_deg", "NaN", "timeout 30 s" },
		measurements = { "slalom_time_s", "yaw_gain", "steer_effort_rms", "corridor_violations" },
		repeatability = "3 opakovani; parametry ridice verzovane v driver_version.",
	},
	{
		scenario_id = "T07",
		name_cz = "Nerovnosti / rozbity povrch",
		kind = "bump_section",
		seed = 107,
		duration_s = 25,
		repetitions = 3,
		track = { shape = "straight_bumps", length_studs = 400, lane_half_width_studs = 4 },
		surface = "BUMP",
		initial_conditions = {
			speed_studs_s = 60,
			throttle = 0,
			brake = 0,
			steer = 0,
			gear = "auto",
			settle_s = 1.0,
		},
		procedure = "Rychlostni regulator 60 studs/s pres definovane pole nerovnosti (pevny seed 107, stejne hrboly pro vsechny varianty).",
		completion = "Dojezd 400 studs nebo 25 s; zaznamenat ztratu kontaktu.",
		failure_abort = { "ztrata_kontaktu_vsech_4_kol_gt_0.5_s", "prevraceni", "NaN" },
		measurements = {
			"vert_accel_rms",
			"susp_travel_min_max_per_wheel",
			"tire_contact_loss_time_s",
			"pitch_rms",
			"roll_rms",
		},
		repeatability = "3 opakovani s pevnym seedem nerovnosti; rozptyl RMS do +/-10 %.",
	},
}

function ScenarioDefinitions.Get(scenario_id: string)
	for _, def in ScenarioDefinitions.DEFINITIONS do
		if def.scenario_id == scenario_id then
			return def
		end
	end
	return nil
end

function ScenarioDefinitions.ListIds(): { string }
	local ids = {}
	for _, def in ScenarioDefinitions.DEFINITIONS do
		table.insert(ids, def.scenario_id)
	end
	return ids
end

return ScenarioDefinitions
