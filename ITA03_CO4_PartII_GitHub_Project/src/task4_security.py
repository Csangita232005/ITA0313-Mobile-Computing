import json
from pathlib import Path
from src.common import write_text

DEFAULT_CONFIG = {
    "app_name": "RuralCareTest",
    "permissions": ["CAMERA", "ACCESS_FINE_LOCATION"],
    "data_stores": [
        {"name":"auth_token","type":"EncryptedSharedPreferences","encrypted":True,"private":True},
        {"name":"patient_db","type":"SQLite","encrypted":True,"private":True},
        {"name":"cache","type":"File","encrypted":False,"private":True}
    ],
    "network_endpoints": [
        {"url":"https://api.ruralcare.example/v1/sync","protocol":"HTTPS","tls_validation":True,"certificate_pinning":False},
        {"url":"http://legacy.example/upload","protocol":"HTTP","tls_validation":False,"certificate_pinning":False}
    ],
    "exported_components": [
        {"name":"InternalDebugActivity","exported":False,"permission_protected":True},
        {"name":"ShareReceiver","exported":True,"permission_protected":False}
    ],
    "app_signed": True,
    "verified_boot_assumed": True,
    "keystore_backed_key": True
}

THREATS = [
    ("Spoofing","Stolen/replayed authentication token","Token store and login session","Keystore-backed key, short-lived token, server revocation","Token theft from a compromised/unlocked device remains possible."),
    ("Tampering","Modification of local patient records","Encrypted local database","Authenticated encryption, database integrity checks, server validation","A compromised running app can still write validly authenticated data."),
    ("Repudiation","Worker denies creating a record","Audit trail","Server-side append-only audit events with user/device/time IDs","Clock drift or compromised credentials can weaken attribution."),
    ("Information disclosure","Local database or cache extraction","Patient database and files","Private app sandbox + encryption at rest + hardware-backed key","Rooted OS or unlocked device may expose plaintext during use."),
    ("Denial of service","Repeated requests or storage exhaustion","REST API and local storage","Rate limiting, quotas, bounded cache and retry backoff","Distributed abuse and network outages remain possible."),
    ("Elevation of privilege","Unprotected exported component invoked externally","Exported activity/receiver","Set exported=false or require signature-level permission; validate caller","Other attack surfaces in dependencies may remain."),
    ("Information disclosure","Network interception of API traffic","API traffic","TLS certificate validation; pinning where justified","Compromised trust store/device or malicious trusted endpoint remains a risk.")
]

def load_config():
    path = Path("config/security_config.json")
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
    return DEFAULT_CONFIG

def audit(config):
    rows = []
    permissions = set(config.get("permissions", []))
    if "CAMERA" in permissions:
        rows.append(("Camera permission","Permission misuse","Request only at point of use; runtime permission","PARTIALLY BLOCKED","User denial and camera misuse by compromised app remain possible."))
    if "ACCESS_FINE_LOCATION" in permissions:
        rows.append(("Location permission","Location tracking","Runtime permission, foreground disclosure and purpose limitation","PARTIALLY BLOCKED","Granted location can still be misused by the app."))
    for store in config.get("data_stores", []):
        safe = store.get("private", False) and store.get("encrypted", False)
        rows.append((store["name"],"Local data theft","App sandbox + encryption + Keystore-backed key",
                     "BLOCKED" if safe else "EXPOSED",
                     "Rooted/unlocked-device runtime exposure remains." if safe else "Store is private/encrypted flag is missing; data-at-rest protection is insufficient."))
    for endpoint in config.get("network_endpoints", []):
        safe = endpoint.get("protocol","").upper() == "HTTPS" and endpoint.get("tls_validation",False)
        rows.append((endpoint["url"],"Network interception","HTTPS/TLS with certificate validation",
                     "BLOCKED" if safe else "EXPOSED",
                     "Pinning is optional and threat-model dependent." if safe else "Cleartext or unvalidated traffic can expose/alter data."))
    for component in config.get("exported_components", []):
        safe = not component.get("exported",False) or component.get("permission_protected",False)
        rows.append((component["name"],"External component invocation","Non-exported component or signature permission",
                     "BLOCKED" if safe else "EXPOSED",
                     "Input validation is still required." if safe else "Untrusted apps may invoke the exported component."))
    return rows

def render_report(config, rows, title="SECURITY AUDIT"):
    exposed = sum(1 for row in rows if row[3] == "EXPOSED")
    partial = sum(1 for row in rows if row[3] == "PARTIALLY BLOCKED")
    verdict = "FAIL – exposed assets require remediation" if exposed else (
        "CONDITIONAL – residual risks require acceptance" if partial else "PASS – no exposed assets in this configuration")
    lines = [title, f"Application: {config.get('app_name')}", "-"*90,
             "STRIDE THREAT MODEL"]
    for category, threat, asset, mitigation, residual in THREATS:
        lines += [f"\nCategory: {category}", f"Threat: {threat}", f"Asset: {asset}",
                  f"Mitigation: {mitigation}", f"Residual risk: {residual}"]
    lines += ["\nASSET DECISION TRACE",
              f"{'ASSET':30} | {'ATTACK VECTOR':25} | {'RESULT':18} | REASON"]
    for asset, attack, mechanism, result, reason in rows:
        lines.append(f"{asset[:30]:30} | {attack[:25]:25} | {result:18} | {reason}")
    lines += ["\nFINAL VERDICT", verdict,
              f"Exposed assets: {exposed}; partially blocked assets: {partial}.",
              "This is a configuration audit, not proof that the running app is secure."]
    return "\n".join(lines), verdict

def run_security_audit():
    print("TASK 4 – Defensive security audit")
    config = load_config()
    rows = audit(config)
    report, verdict = render_report(config, rows)
    write_text("task4_security_audit.txt", report)
    print(report)

    # Predict first, then weaken one control and re-run the audit.
    weakened = json.loads(json.dumps(config))
    for endpoint in weakened["network_endpoints"]:
        if endpoint["protocol"].upper() == "HTTPS":
            endpoint["protocol"] = "HTTP"
            endpoint["tls_validation"] = False
            break
    weak_rows = audit(weakened)
    weak_report, weak_verdict = render_report(weakened, weak_rows, "WEAKENED-CONTROL EXPERIMENT")
    write_text("task4_weakened_control.txt",
               "PREDICTION BEFORE EXECUTION:\n"
               "The API traffic asset should change from BLOCKED to EXPOSED because TLS is removed.\n"
               "The audit verdict should become FAIL if this is the only changed network endpoint.\n\n"
               + weak_report)
    print("\nPrediction: cleartext endpoint should be EXPOSED; weakened verdict: " + weak_verdict)
