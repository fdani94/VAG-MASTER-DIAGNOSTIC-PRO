"""Airbag / Instruments / SRI / Immobilizer / KESSY expansion.
Safety-first: no airbag bypass/emulator guidance and no immobilizer bypass.
"""

def _source(con, title, url):
    con.execute("INSERT OR IGNORE INTO sources(title,publisher,url,source_type,notes) VALUES(?,?,?,?,?)",
                (title, "Ross-Tech", url, "official/wiki", "Verified VCDS reference"))
    r=con.execute("SELECT id FROM sources WHERE url=?",(url,)).fetchone()
    return r[0] if r else None


def _add(con, category, title, applies, path, steps, expected, warnings, sid):
    # Reuse procedures schema already used by expansion packs.
    cols={r[1] for r in con.execute("PRAGMA table_info(procedures)").fetchall()}
    data={
        "category":category,"title":title,"applies_to":applies,"vcds_path":path,
        "steps":steps,"expected_result":expected,"warnings":warnings,"source_id":sid,
        "verified":1
    }
    keys=[k for k in data if k in cols]
    if not keys: return
    # Avoid duplicates where supported.
    if "title" in cols:
        row=con.execute("SELECT id FROM procedures WHERE title=? LIMIT 1",(title,)).fetchone()
        if row: return
    q=",".join(keys); p=",".join("?" for _ in keys)
    con.execute(f"INSERT INTO procedures({q}) VALUES({p})",tuple(data[k] for k in keys))


def install(con):
    s_airbag=_source(con,"Ross-Tech Airbag Coding","https://wiki.ross-tech.com/wiki/index.php/Airbag_Coding")
    s_vw20=_source(con,"Ross-Tech AirbagVW20","https://wiki.ross-tech.com/wiki/index.php/AirbagVW20")
    s_a38p=_source(con,"Ross-Tech Audi A3 8P Airbag 9.41","https://wiki.ross-tech.com/wiki/index.php/Audi_A3_%288P%29_Airbag_9.41")
    s_sri=_source(con,"Ross-Tech SRI Reset Procedure","https://wiki.ross-tech.com/wiki/index.php/SRI_Reset_Procedure")
    s_immo2=_source(con,"Ross-Tech Immobilizer II Cluster Swapping","https://wiki.ross-tech.com/wiki/index.php/Immobilizer_II_Immobilizer_Swapping_%28Instrument_Cluster%29")
    s_bcm2=_source(con,"Ross-Tech MLB BCM2 Acc Start Auth","https://wiki.ross-tech.com/wiki/index.php/MLB_based_Acc/Start_Auth_%28J393%29_BCM2")

    _add(con,"Airbag","Airbag controller replacement - safe workflow","New compatible SRS controller only; exact coding depends on controller/index/platform",
         "[Auto-Scan] -> [15-Airbags] -> [Coding-07] -> Coding Helper / Long Coding Helper",
         "1. Save complete Auto-Scan and original coding before removal.\n2. Repair igniter/sensor/wiring faults first.\n3. Install the correct NEW controller and bolt it correctly.\n4. Maintain stable battery voltage.\n5. Use VCDS Suggested Coding/Long Coding Helper only when offered for that controller.\n6. Cycle ignition, re-enter 15-Airbags and verify coding/DTCs.\n7. Never treat permanent crash data as a normal Clear DTC operation.",
         "Correct non-zero coding accepted where applicable; no SRS DTCs after repairs.",
         "SRS is safety-critical. Do not fit bypass resistors/emulators. Ross-Tech does not support used deployed/crash-data controller reset; follow factory repair information.",s_airbag)

    _add(con,"Airbag","MQB AirbagVW20 - J706 seat occupied recognition basic setting","MQB AirbagVW20: A3 8V, Leon 5F, Octavia 5E, Golf 5G and compatible controllers",
         "[15-Airbags] -> [Security Access-16] -> [Basic Settings-04]",
         "Prerequisites: vehicle 5-35 C; battery >=12.4 V; passenger seat empty/normal; belt unplugged; no CP, controller faulty, crash data, not-coded or igniter faults. Use the Security Access shown by VCDS for Seat Occupied Recognition. Run 'Seat occupied recognition serial number' until Finished Correctly, then run 'Resetting seat occupied recognition'. Finish by checking Fault Codes.",
         "Both basic settings finish correctly and 15-Airbags stores no relevant fault.",
         "Do not guess Security Access. Use the value presented by VCDS for the installed controller.",s_vw20)

    _add(con,"Airbag","Audi A3 8P Airbag 9.41 - J706 calibration/reset","Audi A3 8P with Airbag 9.41/J706 configuration",
         "[15-Airbags] -> Security Access 30475 -> Basic Settings Group 001; then Adaptation Channel 000",
         "Seat empty and normal, belt unplugged, no system faults, interior 0-37 C. Perform Basic Settings Group 001. After repair, Security Access 30475 -> Adaptation 000 -> Read -> Save for reset. Recheck DTCs.",
         "J706 calibration/reset completes and PODS/airbag status is normal.",
         "Only for the documented 8P Airbag 9.41 configuration; do not apply this access code to unrelated SRS modules.",s_a38p)

    _add(con,"Instruments / Service","Service Reminder Interval reset (SRI)","Most supported VW/Audi/SEAT/Skoda clusters with service interval function",
         "VCDS main screen -> [SRI Reset]",
         "1. Complete maintenance first.\n2. Open SRI Reset and allow VCDS to read service adaptation values.\n3. Choose the correct operation for vehicle/region (not blindly Simple/Basic on newer Audi).\n4. Perform SRI.\n5. Cycle ignition and verify reminder.\n6. Do not convert fixed/flexible service strategy unless vehicle equipment supports it.",
         "Service reminder clears and service adaptation values match intended schedule.",
         "Service strategy is market/equipment dependent. Some clusters do not use service intervals.",s_sri)

    _add(con,"Immobilizer / Cluster","Immobilizer II - instrument cluster replacement/matching","Older VAG vehicles positively identified as Immobilizer II (14-digit Immo-ID, not later VIN-based system)",
         "[17-Instruments] Coding; [19-CAN Gateway] if integrated; [17-Instruments] Adaptation Channel 00",
         "1. Save old cluster coding/adaptations and obtain legitimate PINs required by the documented Immo II procedure.\n2. Install replacement cluster.\n3. Transfer original coding and applicable Gateway/SRI values.\n4. In 17-Instruments use Adaptation Channel 00 -> Read -> Save to match cluster to ECU where applicable.\n5. Cycle ignition as documented, then perform legitimate key matching for the vehicle.\n6. Verify engine start, immobilizer lamp, cluster and DTCs.",
         "Cluster/ECU match succeeds and authorized keys operate normally.",
         "Not an immobilizer bypass. Procedure applies only to confirmed Immo II. VCDS cannot alter/correct odometer reading of a used cluster.",s_immo2)

    _add(con,"Immobilizer / KESSY","MLB BCM2/J393 replacement - VCDS limitation","Audi 8K/8T/8R/4G/4H and Touareg 7P with BCM2 1.1/2.0; not MLBevo",
         "[05-Acc/Start Auth.] / [46-Central Conv.] for identification and coding backup",
         "1. Identify BCM2 exactly from Auto-Scan.\n2. Save full Auto-Scan and Long Coding before replacement.\n3. VCDS can expose coding information/Long Coding Helper where applicable.\n4. Immobilizer component matching and Component Protection removal require the factory online process with authorized access; do not present Clear DTC or Long Coding as a substitute.\n5. After authorized matching, rescan and verify all related modules.",
         "Correctly matched BCM2 has no immobilizer/Component Protection faults and authorized keys/start functions work.",
         "VCDS alone cannot perform BCM2 immobilizer matching or remove Component Protection. No bypass instructions are provided.",s_bcm2)
    con.commit()
