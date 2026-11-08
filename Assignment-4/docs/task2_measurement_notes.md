# Task 2 measurement notes

The benchmark reports wall-clock duration, process CPU duration for compute cases, worker count and result count. It compares:

1. Serial compute-heavy hashing.
2. Background `ThreadPoolExecutor` hashing.
3. A tiny task where executor setup/scheduling overhead can dominate.
4. Sequential I/O waiting versus overlapping waits.

The same result checksums are asserted to ensure both paths performed equivalent work. On CPython, the Global Interpreter Lock can limit CPU-bound Python bytecode parallelism. The hashing workload calls a native implementation that can release the GIL for sufficiently large inputs, but actual speed-up is hardware- and runtime-dependent.

For the assignment's Android-specific thread-to-core placement requirement, run an Android Kotlin/Java version and collect Perfetto or Android Studio CPU Profiler evidence. Python host thread timings alone do not prove big.LITTLE core placement.
