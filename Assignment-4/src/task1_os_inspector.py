import shutil
import subprocess
from pathlib import Path
from src.common import ensure_output_dir, write_text, utc_now

ADB_COMMANDS = {
    "devices": ["adb", "devices", "-l"],
    "processes": ["adb", "shell", "ps", "-A"],
    "memory": ["adb", "shell", "cat", "/proc/meminfo"],
    "activity_processes": ["adb", "shell", "dumpsys", "activity", "processes"],
    "activities": ["adb", "shell", "dumpsys", "activity", "activities"],
    "services": ["adb", "shell", "service", "list"],
    "cpu": ["adb", "shell", "dumpsys", "cpuinfo"],
    "binder": ["adb", "shell", "service", "list"],
}

def _run(command, timeout=25):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        output = result.stdout + (("\nSTDERR:\n" + result.stderr) if result.stderr else "")
        return result.returncode, output.strip() or "(command returned no text)"
    except subprocess.TimeoutExpired:
        return 124, "COMMAND TIMEOUT"
    except Exception as exc:
        return 1, f"COMMAND ERROR: {exc}"

def collect_android_evidence():
    print("TASK 1 – Android OS evidence collector")
    out = ensure_output_dir("task1")
    if not shutil.which("adb"):
        msg = "ADB NOT FOUND. Install Android Platform Tools and add adb to PATH.\n"
        msg += "No device measurements were collected. See README.md for setup.\n"
        (out / "adb_status.txt").write_text(msg, encoding="utf-8")
        print(msg)
        return

    code, device_output = _run(ADB_COMMANDS["devices"])
    (out / "00_devices.txt").write_text(device_output, encoding="utf-8")
    print("Connected device check:\n" + device_output[:1500])
    if code != 0 or "device" not in device_output.splitlines()[-1].lower():
        print("Check adb devices. Unlock the phone and accept the USB debugging prompt.")
    for name, command in ADB_COMMANDS.items():
        if name == "devices":
            continue
        rc, output = _run(command)
        (out / f"{name}.txt").write_text(
            f"Captured: {utc_now()}\nCommand: {' '.join(command)}\nExit code: {rc}\n\n{output}\n",
            encoding="utf-8"
        )
        print(f"[{name}] exit={rc}; saved outputs/task1/{name}.txt")

    # Binder service listing is live evidence of Android system services.
    binder_text = (out / "binder.txt").read_text(encoding="utf-8", errors="replace")
    (out / "binder_ipc_observation.txt").write_text(
        "Binder-related observation\n"
        "Command: adb shell service list\n"
        "This lists Android services registered with the service manager. "
        "It is supporting evidence that framework services are exposed through Android's "
        "service/ Binder infrastructure; it is not a packet-level Binder trace.\n\n"
        + binder_text[:12000], encoding="utf-8"
    )
    print("Saved live Android command output. iOS evidence must be documented or collected on macOS.")
