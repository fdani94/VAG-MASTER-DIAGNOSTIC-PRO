"""KID Diagnostic - verified Auto-Scan DTC expansion 3.

Adds detailed workshop guidance for additional Ross-Tech documented DTCs.
The UI must still treat a DTC as a diagnostic lead, not proof that a part is bad.
"""

SOURCE = "Ross-Tech Wiki / VCDS"

ROWS = [
    {
        "code": "P00AF", "title": "Turbocharger actuator module: stuck / performance",
        "description": "Control of the turbocharger actuator does not follow the requested operating range.",
        "symptoms": "MIL or glow-plug warning, reduced engine performance / limp mode.",
        "causes": "N75 fault or wrong connector, vacuum leak/low vacuum, sticking VNT mechanism, G581 actuator/position feedback fault, wiring/connectors.",
        "diagnosis": "1. Save Auto-Scan and freeze frame. 2. Inspect vacuum hoses and actuator linkage. 3. In 01-Engine run Output Tests for charge-pressure control/N75 when supported. 4. Compare requested vs actual boost and actuator position in Advanced Measuring Values. 5. Verify N75 connector against wiring diagram before replacing parts.",
        "repair": "Repair vacuum leaks/wiring first; correct crossed connectors; free/repair the VNT mechanism only after mechanical confirmation; replace N75 or actuator/turbo assembly only when testing identifies the failed component.",
        "severity": "high", "component": "N75 / G581 / VNT turbo control", "component_location": "Engine bay; exact N75/actuator position depends on engine code.",
        "vcds_parameters": "Charge pressure specified/actual; turbo actuator position specified/actual; N75 duty cycle where exposed.",
        "expected_values": "Actual boost/actuator position should track requested values under the specified test conditions; use engine-specific data where available.",
        "test_path": "01-Engine > Output Tests and/or Advanced Measuring Values", "replacement_steps": "After repair clear DTC, perform any engine-specific actuator/basic setting if documented, road-test while logging boost, then repeat Auto-Scan.",
        "confidence": "verified"
    },
    {
        "code": "P0088", "title": "Fuel Rail/System Pressure: Too High",
        "description": "Measured rail pressure is above the control target/range.",
        "symptoms": "MIL; possible high-pitched noise at idle; drivability symptoms depend on engine.",
        "causes": "G247 rail-pressure sensor/circuit, N276 pressure regulator supply/control, N290 metering valve where fitted, wiring/connectors; on specific engines additional timing/voltage causes may apply.",
        "diagnosis": "1. Read freeze frame. 2. 01-Engine > Advanced Measuring Values: compare fuel rail pressure specified vs actual. 3. Check G247 plausibility and wiring. 4. Check power/ground/control at N276 and N290 where fitted. 5. Follow engine-specific service information before condemning high-pressure components.",
        "repair": "Repair wiring/supply faults; replace the sensor/regulator/metering component only after electrical and pressure testing identifies it.",
        "severity": "high", "component": "G247 / N276 / N290 fuel-pressure control", "component_location": "Fuel rail/high-pressure fuel system; exact position depends on engine.",
        "vcds_parameters": "Fuel rail pressure specified; fuel rail pressure actual; regulator/metering-valve data where exposed.",
        "expected_values": "Actual rail pressure should follow specified pressure without persistent excessive deviation; exact pressure is engine/load dependent.",
        "test_path": "01-Engine > Advanced Measuring Values", "replacement_steps": "Depressurize fuel system per workshop procedure; after repair clear DTC, verify rail pressure through operating range and rescan.",
        "confidence": "verified"
    },
    {
        "code": "P0336", "title": "Engine Speed Sensor G28: Range/Performance",
        "description": "Implausible crankshaft/engine-speed signal.",
        "symptoms": "Hard/no start, stalling, MIL, intermittent running faults.",
        "causes": "G28 sensor, wiring/connectors, sensor gap/trigger wheel, mechanical timing or signal plausibility issue depending on engine.",
        "diagnosis": "Check freeze frame and related cam/crank DTCs; inspect G28 connector/harness; monitor engine speed during cranking in 01-Engine; compare cam/crank synchronization values where the ECU exposes them.",
        "repair": "Repair wiring/connector or mechanical trigger/timing fault; replace G28 only after signal/supply testing supports it.",
        "severity": "high", "component": "G28 engine speed/crankshaft sensor", "component_location": "Near crankshaft/flywheel/bellhousing area depending on engine family.",
        "vcds_parameters": "Engine speed during cranking; synchronization/cam-crank status where available.",
        "expected_values": "A stable non-zero RPM signal must be present while cranking; exact synchronization fields vary by ECU.",
        "test_path": "01-Engine > Advanced Measuring Values", "replacement_steps": "After repair clear DTC, verify reliable hot/cold starting and stable RPM signal, then rescan.",
        "confidence": "verified"
    },
    {
        "code": "P068A", "title": "ECM/PCM Power Relay De-Energized Performance",
        "description": "ECU power relay/power-down sequence is implausible.",
        "symptoms": "MIL, starting or shutdown issues, intermittent electrical faults.",
        "causes": "ECU power supply/relay, battery voltage, grounds, wiring/connectors, relay control or ECU power-down issue.",
        "diagnosis": "Start with battery voltage and grounds; inspect ECU power relay/fuses and terminal supplies; use Auto-Scan to identify undervoltage or communication faults in other modules; verify relay output during key-on/key-off.",
        "repair": "Correct battery/ground/fuse/relay/wiring faults before considering ECU failure.",
        "severity": "high", "component": "ECM power supply / power relay", "component_location": "Fuse/relay carrier or ECU supply path; location is platform-specific.",
        "vcds_parameters": "Terminal voltage / ECU supply voltage where available; freeze-frame voltage.",
        "expected_values": "Supply should remain within vehicle electrical specifications without abnormal dropouts.",
        "test_path": "Auto-Scan + 01-Engine > Advanced Measuring Values where supported", "replacement_steps": "After electrical repair clear faults, cycle ignition several times, verify restart/shutdown and repeat Auto-Scan.",
        "confidence": "verified"
    },
    {
        "code": "P242F", "title": "Diesel Particulate Filter: Restriction / Ash Accumulation",
        "description": "DPF restriction/ash loading has reached a diagnostic threshold.",
        "symptoms": "DPF/MIL warning, reduced power, regeneration issues.",
        "causes": "High ash loading, excessive soot due to another engine fault, pressure-sensor/hoses issue, failed regeneration history.",
        "diagnosis": "Read DPF soot/ash values, differential pressure and regeneration history in 01-Engine. Check pressure-sensor hoses and related DTCs. Diagnose root causes of excessive soot before regeneration or DPF replacement.",
        "repair": "Repair sensor/engine faults first. Regeneration is appropriate only when the ECU/workshop conditions permit it; ash is not removed by normal regeneration and may require approved cleaning or DPF replacement.",
        "severity": "high", "component": "DPF and differential-pressure monitoring", "component_location": "Exhaust aftertreatment; sensor and hoses normally connect across DPF.",
        "vcds_parameters": "DPF soot mass calculated/measured; ash load; differential pressure; distance/time since regeneration; exhaust temperatures.",
        "expected_values": "Use ECU/engine-specific limits; pressure should be plausible for exhaust flow and loading.",
        "test_path": "01-Engine > Advanced Measuring Values; Basic Settings/Service Regeneration only if supported", "replacement_steps": "After DPF replacement/approved cleaning perform the engine-specific DPF replacement/reset adaptation if documented, verify pressure values and rescan.",
        "confidence": "verified"
    },
    {
        "code": "P2BA6", "title": "NOx Exceedance - SCR NOx Catalyst Performance",
        "description": "SCR system performance is insufficient to keep NOx within expected range.",
        "symptoms": "MIL/AdBlue warning, possible start countdown on some vehicles.",
        "causes": "AdBlue quality/dosing issue, NOx sensor plausibility, SCR catalyst efficiency, exhaust leak, temperature/engine fault affecting SCR operation.",
        "diagnosis": "Check all SCR/NOx/AdBlue related DTCs first. Review upstream/downstream NOx values, reductant level/quality and dosing data, exhaust temperatures and SCR enable status where exposed. Inspect exhaust for leaks.",
        "repair": "Correct upstream engine/exhaust faults, wiring/sensors and dosing faults before replacing SCR catalyst. Follow model-specific guided test information for dosing and catalyst evaluation.",
        "severity": "high", "component": "SCR/AdBlue/NOx aftertreatment", "component_location": "Exhaust aftertreatment and AdBlue dosing system; positions vary by platform.",
        "vcds_parameters": "NOx sensor values; reductant pressure/dosing; SCR temperatures; catalyst efficiency/status where exposed.",
        "expected_values": "No universal NOx number applies; upstream/downstream relationship and dosing response must be evaluated under ECU-specific operating conditions.",
        "test_path": "01-Engine > Advanced Measuring Values / Basic Settings where supported", "replacement_steps": "After component replacement perform any documented SCR/NOx sensor adaptation/basic setting, clear faults only after repair, complete required drive cycle and rescan.",
        "confidence": "verified"
    },
    {
        "code": "P189A", "title": "Clutch 1: Clearance too Small",
        "description": "DSG clutch adaptation detects insufficient clutch 1 clearance.",
        "symptoms": "Shift quality problems, transmission warning, adaptation failure.",
        "causes": "Clutch wear/mechanical condition, incorrect adaptation/basic setting, mechatronic/hydraulic issue depending on gearbox.",
        "diagnosis": "Identify gearbox family before any procedure. Read 02-Transmission DTCs and clutch adaptation values. Do not apply DQ200/DQ250/DQ500/0B5 procedures interchangeably. Check prerequisites and gearbox temperature before Basic Settings.",
        "repair": "Perform only the gearbox-specific Basic Settings/adaptation procedure; if adaptation remains outside limits, inspect clutch/mechatronic mechanical condition.",
        "severity": "high", "component": "DSG clutch 1 / mechatronic adaptation", "component_location": "Inside DSG transmission.",
        "vcds_parameters": "Clutch adaptation/clearance values, gearbox temperature, hydraulic/adaptation status depending on transmission.",
        "expected_values": "Use transmission-specific limits; no universal clutch clearance value is safe across DSG families.",
        "test_path": "02-Transmission > Advanced Measuring Values / Basic Settings", "replacement_steps": "After clutch/mechatronic work perform the exact gearbox-specific Basic Settings and defined adaptation road test, then rescan.",
        "confidence": "verified"
    },
    {
        "code": "P189C", "title": "DSG hydraulic pressure / function fault",
        "description": "Transmission hydraulic/mechatronic operation is outside the expected range; exact wording depends on controller dataset.",
        "symptoms": "Transmission warning, poor/no gear engagement, limp mode.",
        "causes": "Hydraulic pressure supply, pump/accumulator/mechatronic fault, wiring/supply issue or internal transmission condition depending on gearbox.",
        "diagnosis": "Identify exact gearbox and full VCDS fault text. Check battery/supply first, then transmission temperature, hydraulic pressure and pump activation data where exposed. Follow gearbox-specific repair information.",
        "repair": "Repair supply/wiring faults first; diagnose hydraulic/mechatronic assembly before replacement. Do not use a generic DSG reset as a repair.",
        "severity": "critical", "component": "DSG mechatronic / hydraulic pressure system", "component_location": "Transmission mechatronic assembly.",
        "vcds_parameters": "Hydraulic pressure, pump status/runtime, gearbox temperature, clutch/adaptation status where available.",
        "expected_values": "Controller and gearbox specific; compare against documented transmission procedure.",
        "test_path": "02-Transmission > Fault Codes + Advanced Measuring Values", "replacement_steps": "After mechatronic/transmission repair perform gearbox-specific coding/basic settings/adaptation and road test.",
        "confidence": "verified"
    },
]


def _ensure_columns(con):
    cols = {r[1] for r in con.execute("PRAGMA table_info(dtcs)")}
    wanted = {
        "component": "TEXT", "component_location": "TEXT", "vcds_parameters": "TEXT",
        "expected_values": "TEXT", "test_path": "TEXT", "replacement_steps": "TEXT",
        "confidence": "TEXT"
    }
    for name, typ in wanted.items():
        if name not in cols:
            con.execute(f"ALTER TABLE dtcs ADD COLUMN {name} {typ}")


def install(con):
    _ensure_columns(con)
    cols = {r[1] for r in con.execute("PRAGMA table_info(dtcs)")}
    for r in ROWS:
        existing = con.execute("SELECT id FROM dtcs WHERE UPPER(code)=? LIMIT 1", (r["code"].upper(),)).fetchone()
        payload = {k: v for k, v in r.items() if k in cols}
        if existing:
            sets = ", ".join(f"{k}=?" for k in payload if k != "code")
            vals = [payload[k] for k in payload if k != "code"] + [existing[0]]
            con.execute(f"UPDATE dtcs SET {sets} WHERE id=?", vals)
        else:
            payload.setdefault("verified", 1)
            names = list(payload)
            con.execute(
                f"INSERT INTO dtcs ({','.join(names)}) VALUES ({','.join('?' for _ in names)})",
                [payload[n] for n in names]
            )
    con.commit()
