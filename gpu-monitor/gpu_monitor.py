#!/usr/bin/env python3
"""Monitor, record, and graph GPU usage with nvidia-smi/rocm-smi backends."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import os
import random
import re
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


CSV_HEADERS = [
    "timestamp_iso",
    "timestamp_epoch",
    "backend",
    "cpu_util_pct",
    "gpu_index",
    "gpu_name",
    "util_gpu_pct",
    "util_mem_pct",
    "mem_used_mib",
    "mem_total_mib",
    "temp_c",
    "power_w",
]

PALETTE = [
    "#0b7285",
    "#d9480f",
    "#2b8a3e",
    "#6741d9",
    "#c2255c",
    "#5f3dc4",
    "#087f5b",
    "#e67700",
]

_CPU_PREV_IDLE: float | None = None
_CPU_PREV_TOTAL: float | None = None


def run_command(cmd: list[str], timeout: int = 5) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0:
        raise RuntimeError(err or out or f"Command failed: {' '.join(cmd)}")
    return out


def slugify_label(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", label.strip().lower())
    slug = slug.strip("_")
    return slug or "session"


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def runtime_paths(output_dir: Path, label: str | None = None) -> tuple[Path, Path]:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = f"{slugify_label(label)}_" if label else ""
    stem = f"{prefix}gpu_monitor_{stamp}"
    runtime_dir = output_dir / "runtime"
    return runtime_dir / f"{stem}.pid", runtime_dir / f"{stem}.log"


def collect_cpu_util_pct() -> float | None:
    """Return total CPU utilization percentage from /proc/stat deltas."""
    global _CPU_PREV_IDLE, _CPU_PREV_TOTAL
    try:
        first = Path("/proc/stat").read_text(encoding="utf-8").splitlines()[0]
    except (OSError, IndexError):
        return None
    parts = first.split()
    if not parts or parts[0] != "cpu" or len(parts) < 5:
        return None
    try:
        nums = [float(x) for x in parts[1:]]
    except ValueError:
        return None
    idle = nums[3] + (nums[4] if len(nums) > 4 else 0.0)
    total = sum(nums)

    if _CPU_PREV_IDLE is None or _CPU_PREV_TOTAL is None:
        _CPU_PREV_IDLE = idle
        _CPU_PREV_TOTAL = total
        return None

    d_idle = idle - _CPU_PREV_IDLE
    d_total = total - _CPU_PREV_TOTAL
    _CPU_PREV_IDLE = idle
    _CPU_PREV_TOTAL = total
    if d_total <= 0:
        return None
    busy = 100.0 * (1.0 - (d_idle / d_total))
    return max(0.0, min(100.0, busy))


def now_iso(epoch: float) -> str:
    return dt.datetime.fromtimestamp(epoch).isoformat(timespec="seconds")


def parse_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s or s.upper() in {"N/A", "NAN", "NONE"}:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", s)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def extract_json_blob(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0 or end <= start:
        raise ValueError("No JSON object found in command output")
    return text[start : end + 1]


def collect_nvidia(epoch: float) -> list[dict[str, Any]]:
    cmd = [
        "nvidia-smi",
        "--query-gpu=index,name,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu,power.draw",
        "--format=csv,noheader,nounits",
    ]
    raw = run_command(cmd)
    rows: list[dict[str, Any]] = []
    for line in raw.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 8:
            continue
        rows.append(
            {
                "timestamp_iso": now_iso(epoch),
                "timestamp_epoch": f"{epoch:.3f}",
                "backend": "nvidia",
                "gpu_index": parts[0],
                "gpu_name": parts[1],
                "util_gpu_pct": parse_float(parts[2]),
                "util_mem_pct": parse_float(parts[3]),
                "mem_used_mib": parse_float(parts[4]),
                "mem_total_mib": parse_float(parts[5]),
                "temp_c": parse_float(parts[6]),
                "power_w": parse_float(parts[7]),
            }
        )
    if not rows:
        raise RuntimeError("nvidia-smi returned no GPU rows")
    return rows


def find_value_by_hints(card: dict[str, Any], hints: list[str]) -> float | None:
    lower_hints = [h.lower() for h in hints]
    for key, value in card.items():
        key_l = str(key).lower()
        if any(h in key_l for h in lower_hints):
            parsed = parse_float(value)
            if parsed is not None:
                return parsed
    return None


def collect_rocm(epoch: float) -> list[dict[str, Any]]:
    cmd = [
        "rocm-smi",
        "--showproductname",
        "--showuse",
        "--showmemuse",
        "--showtemp",
        "--showpower",
        "--json",
    ]
    raw = run_command(cmd)
    data = json.loads(extract_json_blob(raw))
    rows: list[dict[str, Any]] = []

    for key, value in data.items():
        if not str(key).lower().startswith("card"):
            continue
        if not isinstance(value, dict):
            continue
        idx_match = re.search(r"\d+", str(key))
        gpu_index = idx_match.group(0) if idx_match else str(key)
        name = (
            value.get("Card series")
            or value.get("Card model")
            or value.get("Device Name")
            or f"AMD GPU {gpu_index}"
        )
        rows.append(
            {
                "timestamp_iso": now_iso(epoch),
                "timestamp_epoch": f"{epoch:.3f}",
                "backend": "rocm",
                "gpu_index": str(gpu_index),
                "gpu_name": str(name),
                "util_gpu_pct": find_value_by_hints(value, ["gpu use", "gfx use"]),
                "util_mem_pct": find_value_by_hints(value, ["memory use", "mem use"]),
                "mem_used_mib": None,
                "mem_total_mib": None,
                "temp_c": find_value_by_hints(value, ["temperature", "temp"]),
                "power_w": find_value_by_hints(value, ["power", "package power"]),
            }
        )

    if not rows:
        raise RuntimeError("rocm-smi returned no GPU rows")
    return rows


def read_float_from_file(path: Path, scale_divisor: float = 1.0) -> float | None:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    val = parse_float(raw)
    if val is None:
        return None
    if scale_divisor != 1.0:
        val = val / scale_divisor
    return val


def collect_sysfs(epoch: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for busy_file in sorted(Path("/sys/class/drm").glob("card*/device/gpu_busy_percent")):
        card_dir = busy_file.parent.parent
        card_name = card_dir.name
        idx_match = re.search(r"\d+", card_name)
        gpu_index = idx_match.group(0) if idx_match else card_name

        util = read_float_from_file(busy_file)
        if util is None:
            continue

        gpu_name = f"{card_name}"

        mem_used = read_float_from_file(card_dir / "device/mem_info_vram_used", scale_divisor=1024 * 1024)
        mem_total = read_float_from_file(card_dir / "device/mem_info_vram_total", scale_divisor=1024 * 1024)
        mem_util = None
        if mem_used is not None and mem_total and mem_total > 0:
            mem_util = (mem_used / mem_total) * 100.0

        temp = None
        power = None
        hwmons = sorted((card_dir / "device/hwmon").glob("hwmon*"))
        for hw in hwmons:
            if temp is None:
                temp = read_float_from_file(hw / "temp1_input", scale_divisor=1000.0)
            if power is None:
                # Most drivers report microwatts in power1_average.
                power = read_float_from_file(hw / "power1_average", scale_divisor=1_000_000.0)

        rows.append(
            {
                "timestamp_iso": now_iso(epoch),
                "timestamp_epoch": f"{epoch:.3f}",
                "backend": "sysfs",
                "gpu_index": str(gpu_index),
                "gpu_name": gpu_name,
                "util_gpu_pct": util,
                "util_mem_pct": mem_util,
                "mem_used_mib": mem_used,
                "mem_total_mib": mem_total,
                "temp_c": temp,
                "power_w": power,
            }
        )

    if not rows:
        raise RuntimeError("sysfs GPU metrics not found")
    return rows


def collect_demo(epoch: float, gpu_count: int = 1) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    t = epoch / 8.0
    for i in range(gpu_count):
        phase = i * 0.8
        util = 40 + 35 * math.sin(t + phase) + random.uniform(-6, 6)
        util = max(0, min(100, util))
        mem_util = max(0, min(100, util * 0.7 + random.uniform(-5, 5)))
        mem_total = 24564.0
        mem_used = max(0, min(mem_total, mem_total * (mem_util / 100.0)))
        temp = max(25, min(95, 48 + util * 0.35 + random.uniform(-2, 2)))
        power = max(10, min(450, 70 + util * 2.1 + random.uniform(-10, 10)))
        rows.append(
            {
                "timestamp_iso": now_iso(epoch),
                "timestamp_epoch": f"{epoch:.3f}",
                "backend": "demo",
                "gpu_index": str(i),
                "gpu_name": f"Demo GPU {i}",
                "util_gpu_pct": util,
                "util_mem_pct": mem_util,
                "mem_used_mib": mem_used,
                "mem_total_mib": mem_total,
                "temp_c": temp,
                "power_w": power,
            }
        )
    return rows


def detect_backend(explicit: str | None) -> str:
    if explicit:
        return explicit
    checks: list[tuple[str, Any]] = [
        ("nvidia", collect_nvidia),
        ("rocm", collect_rocm),
        ("sysfs", collect_sysfs),
    ]
    epoch = time.time()
    for name, fn in checks:
        try:
            _ = fn(epoch)
            return name
        except Exception:
            continue
    raise RuntimeError(
        "No working GPU backend found. Try --backend demo to validate the tool, "
        "or run on a system where nvidia-smi/rocm-smi/sysfs can access a GPU."
    )


def collect_once(backend: str, epoch: float, demo_gpus: int) -> list[dict[str, Any]]:
    if backend == "nvidia":
        return collect_nvidia(epoch)
    if backend == "rocm":
        return collect_rocm(epoch)
    if backend == "sysfs":
        return collect_sysfs(epoch)
    if backend == "demo":
        return collect_demo(epoch, gpu_count=demo_gpus)
    raise ValueError(f"Unsupported backend: {backend}")


def format_cell(value: Any, precision: int = 1) -> str:
    if value is None:
        return "-"
    if isinstance(value, str):
        return value
    return f"{float(value):.{precision}f}"


def print_live(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        cpu_txt = ""
        if row.get("cpu_util_pct") is not None:
            cpu_txt = f" cpu={format_cell(row['cpu_util_pct'])}%"
        print(
            f"[{row['timestamp_iso']}] gpu={row['gpu_index']} "
            f"{cpu_txt} "
            f"util={format_cell(row['util_gpu_pct'])}% "
            f"mem={format_cell(row['util_mem_pct'])}% "
            f"temp={format_cell(row['temp_c'])}C "
            f"power={format_cell(row['power_w'])}W"
        )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if not exists:
            writer.writeheader()
        for row in rows:
            out = {k: row.get(k, "") for k in CSV_HEADERS}
            writer.writerow(out)


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        out: list[dict[str, Any]] = []
        for row in reader:
            for k in (
                "timestamp_epoch",
                "cpu_util_pct",
                "util_gpu_pct",
                "util_mem_pct",
                "mem_used_mib",
                "mem_total_mib",
                "temp_c",
                "power_w",
            ):
                row[k] = parse_float(row.get(k))
            out.append(row)
        return out


def scale(value: float, v_min: float, v_max: float, px_min: float, px_max: float) -> float:
    if v_max == v_min:
        return (px_min + px_max) / 2.0
    return px_min + (value - v_min) * (px_max - px_min) / (v_max - v_min)


def points_to_path(points: list[tuple[float, float]]) -> str:
    if not points:
        return ""
    start = points[0]
    chunks = [f"M {start[0]:.2f} {start[1]:.2f}"]
    for x, y in points[1:]:
        chunks.append(f"L {x:.2f} {y:.2f}")
    return " ".join(chunks)


def generate_svg(rows: list[dict[str, Any]]) -> str:
    if not rows:
        raise ValueError("No rows available for graph")

    by_gpu: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        gpu = str(r.get("gpu_index", "0"))
        by_gpu.setdefault(gpu, []).append(r)
    for gpu_rows in by_gpu.values():
        gpu_rows.sort(key=lambda x: x.get("timestamp_epoch") or 0.0)

    all_t = [r["timestamp_epoch"] for r in rows if isinstance(r.get("timestamp_epoch"), float)]
    if not all_t:
        raise ValueError("No timestamp data available for graph")

    t_min, t_max = min(all_t), max(all_t)

    width = 1280
    height = 900
    left = 70
    right = width - 30
    panel_h = 220
    panel_gap = 40
    top0 = 70
    metrics = [
        ("util_gpu_pct", "GPU Util (%)", 0.0, 100.0),
        ("temp_c", "Temp (C)", None, None),
        ("power_w", "Power (W)", None, None),
    ]

    lines: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<text x="30" y="36" font-size="24" font-family="monospace" fill="#0f172a">GPU Usage Report</text>',
        f'<text x="30" y="58" font-size="14" font-family="monospace" fill="#334155">Generated {dt.datetime.now().isoformat(timespec="seconds")}</text>',
    ]

    legend_x = 30
    legend_y = height - 22
    for idx, gpu in enumerate(sorted(by_gpu.keys(), key=lambda x: int(x) if x.isdigit() else x)):
        color = PALETTE[idx % len(PALETTE)]
        x = legend_x + idx * 140
        lines.append(f'<circle cx="{x}" cy="{legend_y}" r="5" fill="{color}"/>')
        lines.append(
            f'<text x="{x + 10}" y="{legend_y + 5}" font-size="13" font-family="monospace" fill="#0f172a">GPU {gpu}</text>'
        )

    for panel_i, (key, label, fixed_min, fixed_max) in enumerate(metrics):
        p_top = top0 + panel_i * (panel_h + panel_gap)
        p_bot = p_top + panel_h
        lines.append(f'<rect x="{left}" y="{p_top}" width="{right - left}" height="{panel_h}" fill="#ffffff" stroke="#cbd5e1"/>')
        lines.append(
            f'<text x="{left}" y="{p_top - 10}" font-size="16" font-family="monospace" fill="#0f172a">{label}</text>'
        )

        vals = [r[key] for r in rows if isinstance(r.get(key), float)]
        if fixed_min is not None and fixed_max is not None:
            v_min, v_max = fixed_min, fixed_max
        elif vals:
            v_min = min(vals)
            v_max = max(vals)
            pad = max(1.0, (v_max - v_min) * 0.1)
            v_min -= pad
            v_max += pad
        else:
            v_min, v_max = 0.0, 1.0

        for tick in range(6):
            y_val = v_min + (v_max - v_min) * (tick / 5.0)
            y = scale(y_val, v_min, v_max, p_bot, p_top)
            lines.append(f'<line x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}" stroke="#e2e8f0"/>')
            lines.append(
                f'<text x="{left - 8}" y="{y + 4:.2f}" text-anchor="end" font-size="11" font-family="monospace" fill="#475569">{y_val:.1f}</text>'
            )

        for idx, gpu in enumerate(sorted(by_gpu.keys(), key=lambda x: int(x) if x.isdigit() else x)):
            color = PALETTE[idx % len(PALETTE)]
            gpu_rows = by_gpu[gpu]
            points: list[tuple[float, float]] = []
            for row in gpu_rows:
                t = row.get("timestamp_epoch")
                v = row.get(key)
                if not isinstance(t, float) or not isinstance(v, float):
                    continue
                x = scale(t, t_min, t_max, left, right)
                y = scale(v, v_min, v_max, p_bot, p_top)
                points.append((x, y))
            if len(points) >= 2:
                path = points_to_path(points)
                lines.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.2"/>')

        t0 = dt.datetime.fromtimestamp(t_min).strftime("%H:%M:%S")
        t1 = dt.datetime.fromtimestamp(t_max).strftime("%H:%M:%S")
        lines.append(
            f'<text x="{left}" y="{p_bot + 18}" font-size="11" font-family="monospace" fill="#475569">{t0}</text>'
        )
        lines.append(
            f'<text x="{right}" y="{p_bot + 18}" text-anchor="end" font-size="11" font-family="monospace" fill="#475569">{t1}</text>'
        )

    lines.append("</svg>")
    return "\n".join(lines)


def generate_graph(csv_path: Path, svg_path: Path, html_path: Path) -> None:
    rows = read_csv(csv_path)
    svg = generate_svg(rows)
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg, encoding="utf-8")
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GPU Usage Report</title>
  <style>
    body {{ margin: 0; background: #f1f5f9; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
    .wrap {{ max-width: 1300px; margin: 16px auto; padding: 8px; }}
    object {{ width: 100%; border: 1px solid #cbd5e1; background: #fff; }}
    .meta {{ color: #334155; font-size: 13px; margin-bottom: 8px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="meta">Source CSV: {csv_path.name}</div>
    <div class="meta">Metadata JSON: {csv_path.with_suffix(".json").name}</div>
    <object data="{svg_path.name}" type="image/svg+xml"></object>
  </div>
</body>
</html>
"""
    html_path.write_text(html, encoding="utf-8")


def default_paths(output_dir: Path, label: str | None = None) -> tuple[Path, Path, Path, Path]:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = f"{slugify_label(label)}_" if label else ""
    stem = f"{prefix}gpu_usage_{stamp}"
    csv_path = output_dir / "logs" / f"{stem}.csv"
    svg_path = output_dir / "graphs" / f"{stem}.svg"
    html_path = output_dir / "graphs" / f"{stem}.html"
    json_path = output_dir / "logs" / f"{stem}.json"
    return csv_path, svg_path, html_path, json_path


def write_session_metadata(
    metadata_path: Path,
    *,
    label: str | None,
    note: str | None,
    backend: str,
    interval_s: float,
    start_epoch: float,
    end_epoch: float,
    samples: int,
    csv_path: Path,
    svg_path: Path,
    html_path: Path,
) -> None:
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "label": label,
        "label_slug": slugify_label(label) if label else None,
        "note": note,
        "backend": backend,
        "interval_s": interval_s,
        "start_epoch": round(start_epoch, 3),
        "end_epoch": round(end_epoch, 3),
        "start_iso": now_iso(start_epoch),
        "end_iso": now_iso(end_epoch),
        "duration_seconds": round(max(0.0, end_epoch - start_epoch), 3),
        "samples": samples,
        "artifacts": {
            "csv": str(csv_path),
            "svg": str(svg_path),
            "html": str(html_path),
        },
        "build_log_snippet": f"gpu_csv={csv_path} gpu_meta={metadata_path}",
        "replay_command": " ".join(
            shlex.quote(part)
            for part in [
                "python3",
                "gpu-monitor/gpu_monitor.py",
                "graph",
                str(csv_path),
            ]
        ),
    }
    metadata_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def add_shared_run_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--backend", choices=["nvidia", "rocm", "sysfs", "demo"], default=None, help="Backend override")
    parser.add_argument("--interval", type=float, default=1.0, help="Sampling interval in seconds")
    parser.add_argument("--duration", type=float, default=60.0, help="Duration in seconds; 0 or less runs until Ctrl+C")
    parser.add_argument("--output-dir", default="gpu-monitor", help="Output base directory")
    parser.add_argument("--csv", default=None, help="Exact CSV output path")
    parser.add_argument("--label", default=None, help="Session label used in filenames and metadata")
    parser.add_argument("--note", default=None, help="Short experiment/build note stored in metadata JSON")
    parser.add_argument("--demo-gpus", type=int, default=1, help="Number of synthetic GPUs for demo backend")


def run_monitor(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir).resolve()
    csv_path, svg_path, html_path, metadata_path = default_paths(output_dir, args.label)
    if args.csv:
        csv_path = Path(args.csv).resolve()
        stem = csv_path.stem
        svg_path = csv_path.with_name(f"{stem}.svg")
        html_path = csv_path.with_name(f"{stem}.html")
        metadata_path = csv_path.with_name(f"{stem}.json")

    backend = detect_backend(args.backend)
    print(f"Using backend: {backend}")
    if args.label:
        print(f"Session label: {args.label}")
    if args.note:
        print(f"Session note: {args.note}")
    print(f"Logging to: {csv_path}")
    print("Press Ctrl+C to stop.\n")

    start = time.time()
    samples = 0
    end = start
    previous_sigterm = signal.getsignal(signal.SIGTERM)

    def handle_sigterm(signum: int, frame: Any) -> None:
        raise KeyboardInterrupt()

    signal.signal(signal.SIGTERM, handle_sigterm)
    try:
        while True:
            now = time.time()
            if args.duration > 0 and (now - start) >= args.duration:
                break
            rows = collect_once(backend, now, demo_gpus=args.demo_gpus)
            cpu_util = collect_cpu_util_pct()
            for row in rows:
                row["cpu_util_pct"] = cpu_util
            write_csv(csv_path, rows)
            print_live(rows)
            samples += 1
            end = now
            time.sleep(max(0.1, args.interval))
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)
        try:
            generate_graph(csv_path, svg_path, html_path)
            write_session_metadata(
                metadata_path,
                label=args.label,
                note=args.note,
                backend=backend,
                interval_s=args.interval,
                start_epoch=start,
                end_epoch=end,
                samples=samples,
                csv_path=csv_path,
                svg_path=svg_path,
                html_path=html_path,
            )
            print(f"\nSamples collected: {samples}")
            print(f"Metadata JSON: {metadata_path}")
            print(f"Graph SVG: {svg_path}")
            print(f"Graph HTML: {html_path}")
        except Exception as exc:
            print(f"\nCould not generate graph: {exc}", file=sys.stderr)
            return 1
    return 0


def start_monitor(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir).resolve()
    pid_path, log_path = runtime_paths(output_dir, args.label)
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        "run",
        "--duration",
        "0",
        "--interval",
        str(args.interval),
        "--output-dir",
        str(output_dir),
    ]
    if args.backend:
        cmd.extend(["--backend", args.backend])
    if args.csv:
        cmd.extend(["--csv", args.csv])
    if args.label:
        cmd.extend(["--label", args.label])
    if args.note:
        cmd.extend(["--note", args.note])
    if args.demo_gpus != 1:
        cmd.extend(["--demo-gpus", str(args.demo_gpus)])

    with log_path.open("a", encoding="utf-8") as log_f:
        proc = subprocess.Popen(
            cmd,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    pid_path.write_text(f"{proc.pid}\n", encoding="utf-8")
    payload = {
        "pid": proc.pid,
        "pid_file": str(pid_path),
        "log_file": str(log_path),
        "label": args.label,
        "backend": args.backend,
        "interval_s": args.interval,
        "output_dir": str(output_dir),
        "command": cmd,
    }
    print(json.dumps(payload, indent=2))
    return 0


def stop_monitor(args: argparse.Namespace) -> int:
    pid_path = Path(args.pid_file).resolve()
    if not pid_path.exists():
        print(f"PID file not found: {pid_path}", file=sys.stderr)
        return 1
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
    except ValueError:
        print(f"Invalid PID file: {pid_path}", file=sys.stderr)
        return 1

    if not process_exists(pid):
        print(f"Process already stopped: {pid}")
        return 0

    os.kill(pid, signal.SIGTERM)
    print(f"Stopped PID {pid}")
    return 0


def status_monitor(args: argparse.Namespace) -> int:
    pid_path = Path(args.pid_file).resolve()
    if not pid_path.exists():
        print(json.dumps({"pid_file": str(pid_path), "running": False, "reason": "missing_pid_file"}, indent=2))
        return 1
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
    except ValueError:
        print(json.dumps({"pid_file": str(pid_path), "running": False, "reason": "invalid_pid_file"}, indent=2))
        return 1

    print(
        json.dumps(
            {
                "pid": pid,
                "pid_file": str(pid_path),
                "running": process_exists(pid),
            },
            indent=2,
        )
    )
    return 0


def run_graph(args: argparse.Namespace) -> int:
    csv_path = Path(args.csv).resolve()
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        return 1
    svg_path = Path(args.svg).resolve() if args.svg else csv_path.with_suffix(".svg")
    html_path = Path(args.html).resolve() if args.html else csv_path.with_suffix(".html")
    generate_graph(csv_path, svg_path, html_path)
    print(f"Graph SVG: {svg_path}")
    print(f"Graph HTML: {html_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GPU monitor + recorder + grapher")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Monitor GPUs, record CSV, generate graph")
    add_shared_run_args(run_p)
    run_p.set_defaults(func=run_monitor)

    start_p = sub.add_parser("start", help="Start a detached recorder process for agent-driven data gathering")
    add_shared_run_args(start_p)
    start_p.set_defaults(func=start_monitor)

    stop_p = sub.add_parser("stop", help="Stop a detached recorder process")
    stop_p.add_argument("pid_file", help="PID file written by the start command")
    stop_p.set_defaults(func=stop_monitor)

    status_p = sub.add_parser("status", help="Check whether a detached recorder process is still running")
    status_p.add_argument("pid_file", help="PID file written by the start command")
    status_p.set_defaults(func=status_monitor)

    graph_p = sub.add_parser("graph", help="Generate graph from an existing CSV")
    graph_p.add_argument("csv", help="Input CSV path")
    graph_p.add_argument("--svg", default=None, help="Output SVG path")
    graph_p.add_argument("--html", default=None, help="Output HTML path")
    graph_p.set_defaults(func=run_graph)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
