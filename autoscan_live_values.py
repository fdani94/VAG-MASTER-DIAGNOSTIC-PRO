"""Conservative live-data reference guidance for Auto-Scan diagnostic plans.

Exact controller/engine data always wins. This helper only adds numeric guidance where a
reasonably stable Ross-Tech reference exists; otherwise it tells the user to compare the
controller's Requested/Specified value with Actual and consult the label/repair data.
"""


def _blob(fault, plan):
    return " ".join([
        str(getattr(fault, "code", "") or ""),
        str(getattr(fault, "vag_code", "") or ""),
        str(getattr(fault, "title", "") or ""),
        str(plan.get("title", "") or ""),
        str(plan.get("description", "") or ""),
        str(plan.get("causes", "") or ""),
    ]).lower()


def build_live_reference(fault, plan):
    """Return human-readable VCDS live-data targets for a fault/plan.

    Values are diagnostic references, not universal factory specifications.
    """
    text = _blob(fault, plan)
    rows = []

    # Always preserve any controller/DTC-specific values already stored in the local DB.
    params = str(plan.get("parameters", "") or "").strip()
    expected = str(plan.get("expected", "") or "").strip()
    if params or expected:
        rows.append(
            "FIȘA LOCALĂ / CONTROLLER\n"
            f"Parametri: {params or '—'}\n"
            f"Țintă / interval: {expected or '—'}"
        )

    if any(k in text for k in ("fuel trim", "system too lean", "system too rich", "mixture", "amestec", "p0171", "p0172", "p2187", "p2188")):
        rows.append(
            "FUEL TRIM / LAMBDA (benzină)\n"
            "VCDS: 01-Engine → Measuring Blocks 032/033 pe ECU-urile vechi sau Advanced Measuring Values pe UDS.\n"
            "Referință: trimurile învățate sunt în mod normal aproximativ în zona ±10%. Valori pozitive mari = ECU adaugă combustibil; valori negative mari = ECU scade combustibil.\n"
            "Lambda: la ralanti/cruise în closed-loop ținta este în jur de 1.00. La accelerație/sarcină mare strategia poate cere amestec mai bogat, deci nu folosi 1.00 ca limită universală."
        )

    if any(k in text for k in ("lambda", "oxygen sensor", "o2 sensor", "sonda lambda", "p2196", "p2195", "p013", "p014")):
        rows.append(
            "SONDĂ LAMBDA / CONTROL AMESTEC\n"
            "VCDS: caută Lambda actual / Lambda specified, oxygen sensor control, short-term correction și fuel trim.\n"
            "Referință: în closed-loop stabil la ralanti/cruise, Lambda actual trebuie să urmărească ținta ECU și este de regulă foarte aproape de 1.00. Dacă ținta este 1.00 iar actualul rămâne persistent mult sub 1.00 = bogat; mult peste 1.00 = sărac.\n"
            "Important: la sarcină mare sau în anumite strategii de încălzire/catalizator, ținta poate fi diferită."
        )

    if any(k in text for k in ("boost", "charge pressure", "turbo", "p0299", "p0234", "p0235", "p1556", "p1557")):
        rows.append(
            "PRESIUNE TURBO / BOOST\n"
            "VCDS: 01-Engine → Group 011 pe multe TDI vechi sau Advanced Measuring Values → charge pressure specified/requested + actual pe CAN/UDS.\n"
            "Țintă: folosește valoarea Requested/Specified a ECU ca referință numerică pentru mașina respectivă; Actual trebuie să o urmărească fără abatere persistentă mare.\n"
            "Exemplu Ross-Tech NUMAI pentru ALH 90 CP stock: spike ~2.1 bar absolut, apoi ~1.9 bar absolut în sarcină. Nu aplica aceste valori altui motor."
        )

    if any(k in text for k in ("maf", "mass air", "air mass", "debit aer", "p010", "egr")):
        rows.append(
            "MAF / DEBIT AER\n"
            "VCDS: 01-Engine → Group 003 pe multe TDI vechi sau Advanced Measuring Values → air mass specified + actual.\n"
            "Țintă: Actual trebuie comparat cu Specified pentru ECU-ul concret.\n"
            "Exemplu Ross-Tech NUMAI pentru ALH 90 CP stock: la ~3000 rpm în sarcină maximă, MAF actual cel puțin ~850–900 mg/str. Nu folosi această valoare pe PD/CR/TSI sau alte motoare."
        )

    if any(k in text for k in ("coolant", "engine temperature", "temperatura lichid", "g62", "p011")):
        rows.append(
            "TEMPERATURĂ LICHID RĂCIRE\n"
            "VCDS: coolant temperature / engine coolant temperature.\n"
            "Referință de diagnostic: după încălzire completă trebuie să ajungă și să rămână într-o zonă plauzibilă pentru termostatul/motorul respectiv. Pentru procedura istorică TDI Timing Ross-Tech cere peste ~85°C.\n"
            "Nu considera 90°C o valoare fixă universală; unele motoare moderne folosesc temperaturi comandate diferit."
        )

    if any(k in text for k in ("voltage", "terminal 30", "battery", "bater", "low voltage", "undervoltage", "03041")):
        rows.append(
            "TENSIUNE ALIMENTARE / TERMINAL 30\n"
            "VCDS: battery voltage / Terminal 30 / supply voltage în modulul care raportează eroarea.\n"
            "Verificare practică: compară tensiunea VCDS cu multimetrul la baterie și urmărește căderea în timpul pornirii. Pe sisteme cu management inteligent al încărcării tensiunea de încărcare variază, deci nu folosi o singură valoare de alternator ca specificație universală."
        )

    if any(k in text for k in ("dpf", "particle filter", "soot", "particulate")):
        rows.append(
            "DPF\n"
            "VCDS: soot mass calculated/measured, differential pressure, exhaust temperatures, distance/time since regeneration.\n"
            "Țintă numerică: folosește limitele afișate/documentate pentru ECU-ul concret; pragurile diferă între PD/PPD, CR CAN și CR UDS. Nu porni regenerarea doar pe baza unei valori generice."
        )

    if any(k in text for k in ("rail pressure", "fuel pressure", "presiune combustibil", "p0087", "p0088", "p0191")):
        rows.append(
            "PRESIUNE COMBUSTIBIL / RAIL\n"
            "VCDS: fuel rail pressure specified/requested + actual.\n"
            "Țintă: Actual trebuie să urmărească Requested; valorile absolute diferă foarte mult între MPI/FSI/TSI și CR TDI, deci aplicația nu impune un prag universal fără cod motor/ECU."
        )

    if not rows:
        rows.append(
            "LIVE DATA\n"
            "În VCDS caută parametrul Actual împreună cu Requested/Specified/Target în modulul care a raportat DTC-ul. "
            "Pe UDS folosește Advanced Measuring Values; pe controlerele vechi folosește Measuring Blocks/label file. "
            "Dacă fișa controllerului nu oferă o limită numerică, nu aplica o valoare generică de la alt motor sau alt modul."
        )

    return "\n\n".join(rows)


def enrich_plan(fault, plan):
    plan = dict(plan)
    plan["live_reference"] = build_live_reference(fault, plan)
    return plan
