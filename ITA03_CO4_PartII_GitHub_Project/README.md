# ITA03-MP Assignment 4B (CO4) – Part II
## Mobile Systems Engineering: Analyse, Instrument, Test, Debug & Optimise

This repository contains a reproducible Python-based engineering lab for the six practical tasks in Part II. It is designed to be opened in **VS Code on Windows** and can also run on Linux/macOS.

> **Important evidence note:** Python simulation measurements are measurements of the computer running the script, not measurements of an Android phone. Task 1 includes an ADB collector for real Android/emulator observations. For Android-only values (ART compilation, Doze, Battery Historian, process importance), run the documented ADB commands on your own device/emulator and save the real output. Do not label simulated values as phone measurements.

## Project coverage

| Assignment task | Project implementation | Evidence generated |
|---|---|---|
| Task 1 – OS analysis and lifecycle validation | `src/task1_os_inspector.py` | Android process, memory, activity, services and logcat evidence |
| Task 2 – architecture assumptions vs measured reality | `src/task2_threading.py` | Single-thread/background-executor timings, CPU time, peak Python allocation, small-workload counterexample |
| Task 3 – runtime behaviour | `src/task3_runtime.py` | CPU/allocation/list workloads, heap observations, cold/warm run comparison, deliberate leak and blocking detection |
| Task 4 – secure mobile application audit | `src/task4_security.py` | STRIDE threats, asset decision trace, verdict, weakened-control comparison |
| Task 5 – power management | `src/task5_power.py` | DVFS/Doze/wakelock/batching policy traces and conflict demonstration |
| Task 6 – integrated field-tracking prototype | `src/task6_tracking.py` | Six operating conditions, encrypted queue records, energy estimates, validation and scale test |

## Requirements

- Python 3.10 or newer (Python 3.13 is supported).
- Android Platform Tools (`adb`) for live Android evidence in Task 1. A physical Android phone with USB debugging or an Android emulator is required.
- `cryptography` package for AES-GCM demonstration in Task 6.

## Setup in VS Code (Windows)

1. Extract this ZIP file.
2. Open the extracted folder `ITA03_CO4_PartII_GitHub_Project` in VS Code.
3. Open **Terminal → New Terminal**.
4. Create a virtual environment:

```powershell
python -m venv .venv
```

5. Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run this for the current terminal only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

6. Install dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

7. Run all Python labs:

```powershell
python main.py all
```

8. Run an individual task:

```powershell
python main.py task2
python main.py task3
python main.py task4
python main.py task5
python main.py task6
```

9. Run the Android evidence collector (connect an Android device/emulator first):

```powershell
python main.py task1
```

If ADB is not installed or no device is connected, the collector records the limitation and prints the commands to run. It does not invent device output.

## Task 1 – Android live evidence

Install Android Platform Tools and enable USB debugging. Verify:

```powershell
adb devices
```

Accept the RSA debugging prompt on the phone. Then run:

```powershell
python main.py task1
```

The collector saves command outputs under `outputs/task1/`. Useful manual commands:

```powershell
adb shell ps -A
adb shell dumpsys meminfo
adb shell dumpsys activity processes
adb shell dumpsys activity activities
adb shell service list
adb shell cat /proc/meminfo
adb shell dumpsys cpuinfo
```

For a package-specific report, replace `com.example.app` with the package name:

```powershell
adb shell dumpsys meminfo com.example.app
adb shell dumpsys package com.example.app
adb shell am force-stop com.example.app
adb shell monkey -p com.example.app 1
```

For lifecycle evidence, add lifecycle logging to a small Android test app or use the app supplied by your course. Example Kotlin log statements:

```kotlin
override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    android.util.Log.d("LifecycleDemo", "onCreate")
}
override fun onStart() {
    super.onStart()
    android.util.Log.d("LifecycleDemo", "onStart")
}
override fun onResume() {
    super.onResume()
    android.util.Log.d("LifecycleDemo", "onResume")
}
override fun onPause() {
    android.util.Log.d("LifecycleDemo", "onPause")
    super.onPause()
}
override fun onStop() {
    android.util.Log.d("LifecycleDemo", "onStop")
    super.onStop()
}
override fun onDestroy() {
    android.util.Log.d("LifecycleDemo", "onDestroy")
    super.onDestroy()
}
```

Capture lifecycle logs:

```powershell
adb logcat -c
# Perform app actions on the phone: open app, press Home, return to app.
adb logcat -d -s LifecycleDemo:D
```

Memory-condition experiment (run only against your own test application):

```powershell
adb shell am send-trim-memory com.example.app RUNNING_LOW
adb shell dumpsys activity processes
adb shell dumpsys meminfo com.example.app
```

`am send-trim-memory` availability and accepted process-state values vary by Android version. If unsupported, record the exact error and use a reduced-RAM AVD or Android Studio memory profiler. Do not claim a process was killed unless the process list/log proves it.

### iOS comparison evidence

This project cannot collect iOS process internals from a Windows computer. For iOS, use documented architecture: Darwin/XNU, `launchd`, Mach ports/XPC, Core OS, Core Services, Media and Cocoa Touch. If you have access to a Mac and an iPhone, add Xcode Instruments/sysdiagnose evidence separately. Do not fabricate iOS logs.

## Outputs

Every run creates text/CSV evidence under `outputs/`:
- `task2_threading_results.csv`
- `task3_runtime_results.csv`
- `task4_security_audit.txt`
- `task5_power_trace.csv`
- `task6_policy_results.csv`
- `task6_scale_results.csv`
- task-specific `.txt` logs

The values depend on your computer, Python version, workload settings and Android device. Keep the generated outputs as your actual evidence.

## Tests

Run:

```powershell
python -m unittest discover -s tests -v
```

## Screenshot checklist

Take screenshots only after running the project on your computer/device. Suggested screenshots:

1. VS Code project folder and successful `python main.py all`.
2. Task 1 `adb devices` and one real `dumpsys`/`ps` output.
3. Task 2 comparison table printed in terminal and generated CSV.
4. Task 3 runtime results and failure-detection messages.
5. Task 4 STRIDE audit report including the weakened-control result.
6. Task 5 power-state trace and wake-lock conflict.
7. Task 6 six operating conditions, AES-GCM confirmation, validation and scale output.
8. Unit-test results.

Do not use example output in this README as proof that your own device produced it.

## GitHub upload

Create a new empty GitHub repository, for example `ITA03-CO4-Mobile-Systems-Engineering`.

In VS Code terminal:

```powershell
git init
git add .
git commit -m "Add CO4 mobile systems engineering implementation"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/ITA03-CO4-Mobile-Systems-Engineering.git
git push -u origin main
```

Replace `YOUR-USERNAME` with your GitHub username. Do not upload `.venv/`, private keys, personal device identifiers, patient information or private logs. The `.gitignore` file excludes common local artifacts.

## Limitations and academic integrity

- Task 2 uses Python's `ThreadPoolExecutor`. CPython's GIL can prevent CPU-bound Python threads from scaling across cores. This is a meaningful measured result, not a guarantee of speed-up. The program also includes an I/O-wait workload to demonstrate responsiveness and a tiny-task counterexample.
- Task 3's Python benchmark is a reproducible workload/heap instrumentation exercise. It is not ART. Use the ADB commands in `docs/android_runtime_commands.md` for ART compile filters and Android GC logs.
- Task 4 is a defensive static configuration audit for a test application. It does not attack third-party devices or networks.
- Task 5 and Task 6 use transparent, configurable energy estimates. They are not laboratory power measurements. Replace model assumptions with Battery Historian/Profiler data if available.
- Task 6 uses AES-GCM via `cryptography` for the local demonstration. Its generated development key is not Android Keystore or iOS Keychain protection. Production mobile applications must use platform-backed key storage and a reviewed server protocol.

## Report interpretation

For every task, include: source code → test input → expected behaviour → actual output → intermediate logs/trace → boundary/failure test → interpretation. Discuss differences between predicted and measured behaviour.
