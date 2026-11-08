import hashlib
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from statistics import median
from src.common import write_csv, write_text

def _hash_chunk(seed: int, rounds: int) -> str:
    payload = (f"RuralCare-route-chunk-{seed}".encode() * 4096)
    digest = payload
    for _ in range(rounds):
        digest = hashlib.sha256(digest).digest() + payload[:4096]
    return hashlib.sha256(digest).hexdigest()

def _small_task(n: int) -> int:
    total = 0
    for i in range(1, n + 1):
        total += (i * i) % 97
    return total

def _run_serial(items, fn):
    start_wall = time.perf_counter()
    start_cpu = time.process_time()
    results = [fn(item) for item in items]
    return results, time.perf_counter() - start_wall, time.process_time() - start_cpu

def _run_threaded(items, fn, workers):
    start_wall = time.perf_counter()
    start_cpu = time.process_time()
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="tracking-worker") as pool:
        results = list(pool.map(fn, items))
    return results, time.perf_counter() - start_wall, time.process_time() - start_cpu

def run_threading_lab():
    print("TASK 2 – Single-thread vs background executor")
    workers = min(4, max(2, os.cpu_count() or 2))
    # Large payloads cause hashlib's C implementation to release the GIL while hashing.
    workload = list(range(1, 13))
    serial, serial_wall, serial_cpu = _run_serial(workload, lambda x: _hash_chunk(x, 110))
    threaded, threaded_wall, threaded_cpu = _run_threaded(workload, lambda x: _hash_chunk(x, 110), workers)
    assert serial == threaded, "The two implementations produced different results."

    # Tiny task: executor setup and scheduling overhead should dominate.
    tiny_items = list(range(1, 25))
    tiny_serial, tiny_sw, tiny_sc = _run_serial(tiny_items, lambda x: _small_task(250))
    tiny_parallel, tiny_pw, tiny_pc = _run_threaded(tiny_items, lambda x: _small_task(250), workers)
    assert tiny_serial == tiny_parallel

    # I/O wait demo: workers overlap waiting and return sooner than sequential waits.
    waits = [0.08] * 8
    t0 = time.perf_counter()
    for delay in waits:
        time.sleep(delay)
    io_serial = time.perf_counter() - t0
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(time.sleep, waits))
    io_threaded = time.perf_counter() - t0

    rows = [
        {"case":"compute_hash_serial","wall_seconds":round(serial_wall,6),"process_cpu_seconds":round(serial_cpu,6),"workers":1,"result_count":len(serial),"interpretation":"Baseline"},
        {"case":"compute_hash_thread_pool","wall_seconds":round(threaded_wall,6),"process_cpu_seconds":round(threaded_cpu,6),"workers":workers,"result_count":len(threaded),"interpretation":"Compare measured result; depends on GIL release and host CPU"},
        {"case":"tiny_serial","wall_seconds":round(tiny_sw,6),"process_cpu_seconds":round(tiny_sc,6),"workers":1,"result_count":len(tiny_serial),"interpretation":"Small task baseline"},
        {"case":"tiny_thread_pool","wall_seconds":round(tiny_pw,6),"process_cpu_seconds":round(tiny_pc,6),"workers":workers,"result_count":len(tiny_parallel),"interpretation":"Counterexample: executor overhead may dominate"},
        {"case":"io_wait_serial","wall_seconds":round(io_serial,6),"process_cpu_seconds":"","workers":1,"result_count":len(waits),"interpretation":"Sequential waits"},
        {"case":"io_wait_thread_pool","wall_seconds":round(io_threaded,6),"process_cpu_seconds":"","workers":workers,"result_count":len(waits),"interpretation":"Concurrent waiting improves wall time"},
    ]
    write_csv("task2_threading_results.csv", rows)
    summary = (
        "TASK 2 MEASUREMENTS\n"
        f"Host logical CPUs reported by Python: {os.cpu_count()}\n"
        f"Thread-pool workers: {workers}\n\n"
        f"Hash workload: serial={serial_wall:.4f}s, thread-pool={threaded_wall:.4f}s; "
        f"process CPU serial={serial_cpu:.4f}s, thread-pool={threaded_cpu:.4f}s.\n"
        f"Tiny workload: serial={tiny_sw:.6f}s, thread-pool={tiny_pw:.6f}s.\n"
        f"I/O wait workload: serial={io_serial:.4f}s, thread-pool={io_threaded:.4f}s.\n\n"
        "Interpretation: do not assume more threads are always faster. Python's GIL, workload size, "
        "hashlib's native implementation, scheduling and synchronisation overhead affect results. "
        "These are host measurements, not Android core-placement measurements. Use Perfetto/top -H "
        "on Android for actual thread/core evidence.\n"
    )
    write_text("task2_threading_summary.txt", summary)
    print(summary)
