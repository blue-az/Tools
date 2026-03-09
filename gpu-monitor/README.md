# gpu-monitor

Monitor, record, and graph GPU usage from the command line.

Uses installed tools first:
- `nvidia-smi` for NVIDIA
- `rocm-smi` for AMD/ROCm
- `/sys/class/drm/card*/device/gpu_busy_percent` (`sysfs`) for AMD setups like Waybar modules
- `demo` backend for testing without a visible GPU

No Python packages are required beyond the standard library.

## Web Dashboard (Live + Record Control)

Start the local dashboard:

```bash
python3 gpu-monitor/gpu_dashboard.py
```

Then open:

`http://127.0.0.1:8765`

Dark theme URL:

`http://127.0.0.1:8765/?theme=dark`

What you get:
- Live CPU utilization card
- Live GPU usage cards (utilization, memory, temperature, power)
- Live utilization chart (GPU + CPU, rolling history)
- `Start Recording` / `Stop Recording` buttons
- Active CSV recording path shown in the UI

Useful options:

```bash
python3 gpu-monitor/gpu_dashboard.py --host 0.0.0.0 --port 8765 --interval 1 --history 300
```

Backend options:
- Auto-detect by default (`nvidia`, then `rocm`, then `sysfs`)
- Force backend: `--backend nvidia`, `--backend rocm`, or `--backend sysfs`
- Test without GPU access: `--backend demo --demo-gpus 2`

## Quick Start

```bash
python3 gpu-monitor/gpu_monitor.py run --duration 120 --interval 1
```

This creates:
- `gpu-monitor/logs/gpu_usage_*.csv`
- `gpu-monitor/graphs/gpu_usage_*.svg`
- `gpu-monitor/graphs/gpu_usage_*.html`

## Commands

### Run monitor + recorder + graph

```bash
python3 gpu-monitor/gpu_monitor.py run [options]
```

Options:
- `--backend {nvidia,rocm,sysfs,demo}`: backend override; default auto-detect
- `--interval 1.0`: sample interval in seconds
- `--duration 60`: run length in seconds (`0` means until Ctrl+C)
- `--output-dir gpu-monitor`: output root for logs/graphs
- `--csv /path/file.csv`: write to specific CSV path
- `--label domain_variation_2`: include a stable label in filenames and metadata
- `--note "attempt 1 build log entry"`: store a short experiment note in metadata JSON
- `--demo-gpus 2`: number of synthetic GPUs in demo mode

Example for experiment attribution:

```bash
python3 gpu-monitor/gpu_monitor.py run \
  --backend sysfs \
  --duration 0 \
  --label domain_a_variation_2 \
  --note "tools.py attempt 1"
```

This produces a matched set of artifacts:
- `gpu-monitor/logs/domain_a_variation_2_gpu_usage_*.csv`
- `gpu-monitor/logs/domain_a_variation_2_gpu_usage_*.json`
- `gpu-monitor/graphs/domain_a_variation_2_gpu_usage_*.svg`
- `gpu-monitor/graphs/domain_a_variation_2_gpu_usage_*.html`

The JSON sidecar contains:
- label and note
- start/end timestamps
- duration in seconds
- backend and interval
- artifact paths
- a build-log snippet you can paste into experiment notes

### Detached recorder for agent use

If the dashboard is already running and an agent needs its own separate data-gathering process, use the detached recorder commands:

```bash
python3 gpu-monitor/gpu_monitor.py start \
  --backend sysfs \
  --interval 1 \
  --label domain_a_variation_2 \
  --note "tools.py attempt 1"
```

This prints JSON with:
- `pid`
- `pid_file`
- `log_file`

Check status:

```bash
python3 gpu-monitor/gpu_monitor.py status gpu-monitor/runtime/domain_a_variation_2_gpu_monitor_YYYYMMDD_HHMMSS.pid
```

Stop it:

```bash
python3 gpu-monitor/gpu_monitor.py stop gpu-monitor/runtime/domain_a_variation_2_gpu_monitor_YYYYMMDD_HHMMSS.pid
```

Separate instances are fine as long as they write to different output files. The dashboard sampler and agent-driven recorders are independent processes and only read telemetry; they do not share mutable state.

### Generate graph from existing CSV

```bash
python3 gpu-monitor/gpu_monitor.py graph gpu-monitor/logs/gpu_usage_YYYYMMDD_HHMMSS.csv
```

Optional:
- `--svg /path/report.svg`
- `--html /path/report.html`

## Demo Mode

If GPU telemetry is unavailable in the current session:

```bash
python3 gpu-monitor/gpu_monitor.py run --backend demo --duration 20 --interval 1 --demo-gpus 2
```
