from src.common import write_csv, write_text

def evaluate_power_state(screen_on, moving, battery_pct, held_wakelock):
    if battery_pct <= 15:
        state = "LOW_POWER"
    elif screen_on or moving:
        state = "ACTIVE"
    elif held_wakelock:
        state = "IDLE_WAKELOCK_HELD"
    else:
        state = "DOZE_OR_IDLE"
    return state

def run_power_lab():
    print("TASK 5 – DVFS, Doze/App Standby, wakelock and batching")
    scenarios = [
        {"case":"foreground_moving","screen_on":True,"moving":True,"battery_pct":75,"wakelock":False,"batching":False},
        {"case":"screen_off_stationary","screen_on":False,"moving":False,"battery_pct":70,"wakelock":False,"batching":True},
        {"case":"screen_off_wakelock","screen_on":False,"moving":False,"battery_pct":68,"wakelock":True,"batching":True},
        {"case":"low_battery","screen_on":False,"moving":False,"battery_pct":12,"wakelock":False,"batching":True},
        {"case":"moving_screen_off","screen_on":False,"moving":True,"battery_pct":55,"wakelock":False,"batching":True},
    ]
    rows = []
    for s in scenarios:
        state = evaluate_power_state(s["screen_on"],s["moving"],s["battery_pct"],s["wakelock"])
        # Transparent relative model units; not measured mAh.
        cpu_units = 4.0 if state == "ACTIVE" else 1.0
        if state == "LOW_POWER": cpu_units = 0.6
        radio_wakeups = 12 if not s["batching"] else 3
        if s["wakelock"]: cpu_units += 2.5
        estimated_units = cpu_units + radio_wakeups * 0.35 + (1.5 if s["moving"] else 0.2)
        rows.append({"case":s["case"],"policy_state":state,"dvfs_policy":"performance" if state=="ACTIVE" else "balanced/efficiency",
                     "doze_policy":"restricted/idle" if state in ("DOZE_OR_IDLE","LOW_POWER") else "active",
                     "wakelock_held":s["wakelock"],"batching":s["batching"],"estimated_radio_wakeups":radio_wakeups,
                     "relative_energy_units":round(estimated_units,2),
                     "responsiveness":"high" if state=="ACTIVE" else "deferred/non-urgent work"})
    write_csv("task5_power_trace.csv", rows)

    # Conflict: partial wakelock prevents deep idle benefit even though app batches.
    conflict = rows[2]
    report = ["TASK 5 POWER TRACE", "Relative energy units are an illustrative model, not measured mAh.",
              "case | state | DVFS | Doze | wakelock | radio wakeups | relative energy"]
    for r in rows:
        report.append(f"{r['case']} | {r['policy_state']} | {r['dvfs_policy']} | {r['doze_policy']} | "
                      f"{r['wakelock_held']} | {r['estimated_radio_wakeups']} | {r['relative_energy_units']}")
    report += ["\nSTRESS / CONFLICT TEST",
               "A partial wakelock is held while the screen is off. Batching reduces radio wake-ups, "
               "but the held wakelock prevents the device from reaching its deepest idle behaviour.",
               f"Observed model case: {conflict['case']}; wake-lock={conflict['wakelock_held']}; "
               f"relative energy={conflict['relative_energy_units']}.",
               "Interpretation: application-level batching cannot fully compensate for a lower-layer "
               "wakelock that keeps the CPU active. Use bounded wake locks and release them in finally blocks.",
               "\nDeployment: continuous tracking needs adaptive sampling and a justified foreground service; "
               "gaming/media needs sustained CPU/GPU thermal-aware policy; managed fleets need policy profiles "
               "that respect OS-version differences and enterprise controls."]
    write_text("task5_power_report.txt", "\n".join(report))
    print("\n".join(report))
