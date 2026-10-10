# Benchmarks

Machine-readable results belong in dated subdirectories with a human-readable report. Record
hardware, drivers, dependency/model versions, quantization, context, codecs, resolution, network,
and test configuration. Collect p50/p95/worst-case where relevant.

`scripts/benchmark.ps1 -Profile inventory` records only detected environment facts and marks
`hardware_performance_executed=false`. It is not a simulated benchmark. Media/model benchmark
profiles must fail until they contain real implementations and must never invent measurements.
