import json
import time
from pathlib import Path
from src.common import write_csv, write_text

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    AESGCM = None

SCENARIOS = [
    {"name":"charging_wifi","battery":92,"charging":True,"network":"wifi","motion":"moving","temperature_c":29,"low_power":False,"queued":8},
    {"name":"high_battery_lte","battery":80,"charging":False,"network":"lte","motion":"moving","temperature_c":31,"low_power":False,"queued":12},
    {"name":"low_battery_stationary","battery":20,"charging":False,"network":"lte","motion":"stationary","temperature_c":30,"low_power":False,"queued":25},
    {"name":"battery_saver","battery":12,"charging":False,"network":"lte","motion":"stationary","temperature_c":29,"low_power":True,"queued":18},
    {"name":"no_connectivity","battery":55,"charging":False,"network":"none","motion":"moving","temperature_c":28,"low_power":False,"queued":40},
    {"name":"device_hot","battery":48,"charging":False,"network":"wifi","motion":"moving","temperature_c":43,"low_power":False,"queued":20},
]

def choose_policy(s):
    # Sampling interval seconds and upload decision are policy outputs.
    if s["temperature_c"] >= 42:
        interval, upload, reason = 60, "DEFER_UNTIL_COOLER", "Thermal protection"
    elif s["battery"] <= 15 or s["low_power"]:
        interval, upload, reason = 180, "WIFI_OR_CHARGING_ONLY", "Critical battery saver"
    elif s["battery"] <= 25 and s["motion"] == "stationary":
        interval, upload, reason = 120, "DEFER_TO_WIFI_OR_CHARGING", "Low battery and stationary"
    elif s["network"] == "none":
        interval, upload, reason = 30, "QUEUE_OFFLINE", "No network; retain locally"
    elif s["charging"] and s["network"] == "wifi":
        interval, upload, reason = 10, "UPLOAD_BATCH_NOW", "Charging on Wi-Fi"
    elif s["network"] in ("wifi","lte") and s["motion"] == "moving":
        interval, upload, reason = 20, "UPLOAD_BATCH_IF_QUEUE_THRESHOLD", "Moving with usable network"
    else:
        interval, upload, reason = 60, "DEFER_OR_BATCH", "Balanced default"
    return interval, upload, reason

def encrypt_record(record, aes):
    raw = json.dumps(record, sort_keys=True).encode("utf-8")
    nonce = __import__("os").urandom(12)
    ciphertext = aes.encrypt(nonce, raw, b"ITA03-CO4-Task6")
    return nonce.hex(), ciphertext.hex()

def estimate_energy(interval, upload, network, motion, temperature):
    # Transparent illustrative energy model in relative mAh per policy cycle.
    sample_cost = 0.012 * (60.0 / interval)
    radio_cost = 0.45 if upload in ("UPLOAD_BATCH_NOW","UPLOAD_BATCH_IF_QUEUE_THRESHOLD") else (
        0.08 if upload in ("DEFER_TO_WIFI_OR_CHARGING","DEFER_UNTIL_COOLER","WIFI_OR_CHARGING_ONLY") else 0.02)
    gps_cost = 0.22 if motion == "moving" else 0.04
    thermal_penalty = 0.08 if temperature >= 42 else 0.0
    return round(sample_cost + radio_cost + gps_cost + thermal_penalty, 4)

def run_tracking_lab():
    print("TASK 6 – Battery-aware secure field-tracking prototype")
    if AESGCM is None:
        raise RuntimeError("cryptography is missing. Run: pip install -r requirements.txt")
    # Demo-only ephemeral key. Production must use Android Keystore / iOS Keychain.
    key = AESGCM.generate_key(bit_length=256)
    aes = AESGCM(key)
    output_rows = []
    encrypted_samples = []
    for index, scenario in enumerate(SCENARIOS, start=1):
        interval, upload, reason = choose_policy(scenario)
        energy = estimate_energy(interval, upload, scenario["network"], scenario["motion"], scenario["temperature_c"])
        record = {"record_id":f"RC-{index:04d}","scenario":scenario["name"],
                  "sample_interval_seconds":interval,"upload_action":upload}
        nonce, ciphertext = encrypt_record(record, aes)
        encrypted_samples.append({"record_id":record["record_id"],"nonce":nonce,"ciphertext":ciphertext})
        output_rows.append({
            "condition":scenario["name"],"battery_percent":scenario["battery"],"charging":scenario["charging"],
            "network":scenario["network"],"motion":scenario["motion"],"temperature_c":scenario["temperature_c"],
            "queued_records":scenario["queued"],"policy_reason":reason,"sampling_interval_seconds":interval,
            "upload_action":upload,"encrypted_before_queueing":True,"encrypted_before_transmission":True,
            "encryption":"AES-256-GCM demo","estimated_energy_mAh_per_cycle":energy
        })
    write_csv("task6_policy_results.csv", output_rows)
    write_text("task6_encrypted_demo_records.json", json.dumps(encrypted_samples, indent=2))

    # Independent 3-case validation against hand-calculated expected policy.
    validation_cases = [SCENARIOS[0], SCENARIOS[2], SCENARIOS[4]]
    expected = [(10,"UPLOAD_BATCH_NOW"),(120,"DEFER_TO_WIFI_OR_CHARGING"),(30,"QUEUE_OFFLINE")]
    actual = [choose_policy(s)[:2] for s in validation_cases]
    validation_ok = actual == expected

    # Scale test: number of policy evaluations and wakeups for larger event/fleet loads.
    scale_rows = []
    for device_count in (1,5,10,20):
        records_per_device = 500
        evaluations = device_count * records_per_device
        # Batch uploads: one wake-up per batch of up to 25 records/device, plus one initial sync wake.
        wakeups = device_count * ((records_per_device + 24)//25 + 1)
        queued = device_count * records_per_device
        approx_memory_kb = queued * 0.65
        scale_rows.append({"devices":device_count,"records":queued,"policy_evaluations":evaluations,
                           "estimated_wakeups":wakeups,"estimated_memory_kb":round(approx_memory_kb,1),
                           "energy_note":"model estimate; validate on device with batterystats"})
    write_csv("task6_scale_results.csv", scale_rows)

    # Always-on baseline vs adaptive model for the 3-case validation set.
    baseline_cycles = len(validation_cases) * (0.012 * (60/5) + 0.45 + 0.22)
    adaptive_cycles = sum(estimate_energy(*choose_policy(s)[:2], s["network"], s["motion"], s["temperature_c"])
                          for s in validation_cases)
    report = ["TASK 6 INTEGRATED PROTOTYPE",
              "Six distinct conditions evaluated. Energy values are illustrative relative mAh/cycle estimates, not physical measurements.",
              "AES-256-GCM encryption completed before records are written to the demo queue. Demo key is ephemeral and is not OS-backed.",
              "\nPOLICY RESULTS"]
    for r in output_rows:
        report.append(f"{r['condition']}: battery={r['battery_percent']}%, network={r['network']}, "
                      f"motion={r['motion']}, temp={r['temperature_c']}C -> sample={r['sampling_interval_seconds']}s; "
                      f"upload={r['upload_action']}; encrypted={r['encrypted_before_queueing']}; "
                      f"estimated_energy={r['estimated_energy_mAh_per_cycle']} mAh/cycle; reason={r['policy_reason']}")
    report += ["\nVALIDATION (3 conditions)",
               f"Expected: {expected}",f"Actual:   {actual}",f"Validation passed: {validation_ok}",
               f"Three-case baseline estimate: {baseline_cycles:.4f} relative mAh",
               f"Three-case adaptive estimate: {adaptive_cycles:.4f} relative mAh",
               "\nSCALABILITY"]
    for r in scale_rows:
        report.append(f"devices={r['devices']}, records={r['records']}, evaluations={r['policy_evaluations']}, "
                      f"wakeups={r['estimated_wakeups']}, approx_memory={r['estimated_memory_kb']} KB")
    report += ["\nInterpretation: batching reduces repeated radio wake-ups, but frequent high-rate GPS sampling still consumes energy. "
               "Battery percentage alone is insufficient: charging state, network type, motion, temperature, queue size and last-upload time "
               "change the best decision. During emergencies, prioritise delivery using a temporary high-priority policy and accept higher energy, heat, privacy exposure and cost."]
    write_text("task6_tracking_report.txt", "\n".join(report))
    print("\n".join(report))
