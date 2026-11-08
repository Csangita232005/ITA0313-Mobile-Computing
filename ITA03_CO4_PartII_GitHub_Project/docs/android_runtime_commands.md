# Android runtime / ART evidence commands

Run these on your own Android emulator or USB-connected phone. Replace the package name.

```powershell
adb shell dumpsys package com.example.app
adb shell cmd package compile -m verify com.example.app
adb shell cmd package compile -m speed-profile com.example.app
adb shell cmd package compile -m speed com.example.app
adb shell dumpsys package dexopt
adb logcat -c
adb logcat -d | findstr /i "art gc concurrent freed"
adb shell dumpsys meminfo com.example.app
```

Compilation filters differ by Android version/device. Record command errors rather than inventing output. The `verify`, `speed-profile`, and `speed` filters are intended to expose different verification/optimisation choices. Restore the normal state or reinstall the test app if needed.

For app launch timing:

```powershell
adb shell am force-stop com.example.app
adb shell am start -W -n com.example.app/.MainActivity
```

Repeat the start without force-stop to compare a warm/reused process condition. Save the complete `ThisTime`, `TotalTime`, and `WaitTime` lines. These timings depend on device state and should be measured repeatedly.

For memory and process state:

```powershell
adb shell ps -A
adb shell dumpsys activity processes
adb shell dumpsys meminfo com.example.app
adb shell cat /proc/meminfo
```

For Doze testing on a test device only:

```powershell
adb shell dumpsys deviceidle force-idle
adb shell dumpsys deviceidle
adb shell dumpsys deviceidle unforce
```

Do not force idle on a phone used for emergency calls or important daily work. Behaviour varies by Android release and OEM.
