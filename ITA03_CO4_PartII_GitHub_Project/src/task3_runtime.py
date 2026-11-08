import gc
import time
import tracemalloc
from src.common import write_csv, write_text

def cpu_work(n=180000):
    total = 0
    for i in range(1, n):
        total = (total + (i * 31) % 9973) & 0xFFFFFFFF
    return total

def allocation_work(count=45000):
    values = [{"id": i, "label": f"record-{i}", "values": [i, i+1, i+2]} for i in range(count)]
    checksum = sum(item["values"][1] for item in values)
    return checksum, len(values)

def list_render_work(count=12000):
    rows = [f"<row id='{i}' title='Delivery {i}' status='pending'/>" for i in range(count)]
    return len("".join(rows)), len(rows)

def measure(label, function):
    gc.collect()
    tracemalloc.start()
    start = time.perf_counter()
    result = function()
    elapsed = time.perf_counter() - start
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"workload":label,"elapsed_seconds":round(elapsed,6),
            "current_heap_bytes":current,"peak_heap_bytes":peak,"result":str(result)}

def run_runtime_lab():
    print("TASK 3 – Runtime workload and failure instrumentation")
    rows = []
    # Cold/warm here means first and repeated invocation within this Python process,
    # not Android ART cold/warm startup.
    for name, fn in [
        ("cpu_loop", cpu_work),
        ("object_allocation", allocation_work),
        ("ui_list_model", list_render_work),
    ]:
        rows.append(measure(name + "_first_run", fn))
        rows.append(measure(name + "_repeat_run", fn))

    # Deliberate bounded leak: a global-like list retains references.
    retained_objects = []
    leak_samples = []
    tracemalloc.start()
    for batch in range(1, 6):
        retained_objects.extend([{"batch":batch,"payload":"X"*4096} for _ in range(300)])
        current, peak = tracemalloc.get_traced_memory()
        leak_samples.append({"batch":batch,"retained_objects":len(retained_objects),
                             "current_heap_bytes":current,"peak_heap_bytes":peak})
    tracemalloc.stop()
    leak_detected = all(leak_samples[i]["current_heap_bytes"] < leak_samples[i+1]["current_heap_bytes"]
                        for i in range(len(leak_samples)-1))

    # Main-thread blocking detector: a watchdog threshold, not a real Android ANR.
    threshold_seconds = 0.25
    block_start = time.perf_counter()
    time.sleep(0.40)
    block_duration = time.perf_counter() - block_start
    blocking_detected = block_duration > threshold_seconds

    write_csv("task3_runtime_results.csv", rows)
    write_csv("task3_heap_growth.csv", leak_samples)
    report = (
        "TASK 3 RUNTIME REPORT\n"
        "Python benchmark note: these values instrument Python workloads on the host. "
        "They are not ART compilation/GC measurements.\n\n"
        + "\n".join(
            f"{r['workload']}: elapsed={r['elapsed_seconds']}s, "
            f"current_heap={r['current_heap_bytes']} bytes, peak_heap={r['peak_heap_bytes']} bytes"
            for r in rows
        )
        + "\n\nProduction-failure demonstrations:\n"
        f"Bounded retained-object growth detected: {leak_detected}\n"
        f"Retained object count: {len(retained_objects)}\n"
        f"Heap samples: {leak_samples}\n"
        f"Main-thread blocking duration: {block_duration:.3f}s; threshold={threshold_seconds:.2f}s; "
        f"blocking detected={blocking_detected}\n"
        "Interpretation: tracemalloc observes Python allocations; gc.collect() invokes Python GC. "
        "The blocking watchdog is a simulation. On Android use StrictMode, Android Studio Profiler, "
        "logcat, LeakCanary and ANR traces to identify ART/Android behaviour.\n"
    )
    write_text("task3_runtime_report.txt", report)
    print(report)
