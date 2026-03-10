#!/usr/bin/env python3
"""Local web dashboard for live GPU monitoring and recording."""

from __future__ import annotations

import argparse
import json
import threading
import time
from collections import deque
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import gpu_monitor


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GPU Dashboard</title>
  <style>
    :root {
      --bg: #f4f6f8;
      --panel: #ffffff;
      --ink: #111827;
      --muted: #4b5563;
      --accent: #d97706;
      --ok: #047857;
      --warn: #b91c1c;
      --line: #d1d5db;
      --chart-bg: #ffffff;
      --card-bg-top: #ffffff;
      --card-bg-bottom: #f9fafb;
      --shadow: rgba(17, 24, 39, 0.05);
      --bg-accent1: #dbeafe;
      --bg-accent2: #e2e8f0;
    }
    body[data-theme="dark"] {
      --bg: #0b1220;
      --panel: #111827;
      --ink: #e5e7eb;
      --muted: #94a3b8;
      --accent: #22d3ee;
      --ok: #34d399;
      --warn: #f87171;
      --line: #334155;
      --chart-bg: #0f172a;
      --card-bg-top: #111827;
      --card-bg-bottom: #0f172a;
      --shadow: rgba(2, 6, 23, 0.5);
      --bg-accent1: #1f2937;
      --bg-accent2: #0f172a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 8% 10%, var(--bg-accent1) 0, var(--bg) 35%),
        radial-gradient(circle at 96% 2%, var(--bg-accent2) 0, var(--bg) 40%);
    }
    .wrap { max-width: 1180px; margin: 0 auto; padding: 20px 14px 30px; }
    .top {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-end;
      margin-bottom: 14px;
    }
    h1 {
      margin: 0;
      font-size: 28px;
      letter-spacing: -0.02em;
      font-weight: 700;
    }
    .sub { color: var(--muted); font-size: 14px; margin-top: 4px; }
    .bar {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    button {
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--ink);
      padding: 10px 14px;
      border-radius: 10px;
      cursor: pointer;
      font-weight: 600;
    }
    button:hover { border-color: #9ca3af; }
    .start { border-color: #34d399; }
    .stop { border-color: #fca5a5; }
    .chip {
      border: 1px solid var(--line);
      background: var(--panel);
      padding: 8px 10px;
      border-radius: 999px;
      font-size: 13px;
      color: var(--muted);
    }
    .status-on { color: var(--ok); font-weight: 700; }
    .status-off { color: var(--warn); font-weight: 700; }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
      box-shadow: 0 8px 20px var(--shadow);
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
      margin-bottom: 12px;
    }
    .card {
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px;
      background: linear-gradient(180deg, var(--card-bg-top) 0%, var(--card-bg-bottom) 100%);
    }
    .k { font-size: 12px; color: var(--muted); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.06em; }
    .v { font-size: 26px; font-weight: 700; letter-spacing: -0.01em; }
    .small { font-size: 12px; color: var(--muted); margin-top: 4px; }
    canvas {
      width: 100%;
      height: 360px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--chart-bg);
      display: block;
    }
    .foot { margin-top: 8px; font-size: 12px; color: var(--muted); }
  </style>
</head>
<body data-theme="dark">
  <div class="wrap">
    <div class="top">
      <div>
        <h1>GPU Dashboard</h1>
        <div class="sub" id="meta">Loading...</div>
      </div>
      <div class="bar">
        <span class="chip">Recording: <span id="recState" class="status-off">OFF</span></span>
        <button class="start" id="startBtn">Start Recording</button>
        <button class="stop" id="stopBtn">Stop Recording</button>
      </div>
    </div>
    <div class="panel">
      <div class="cards" id="cards"></div>
      <canvas id="chart" width="1120" height="360"></canvas>
      <div class="foot" id="recordPath">No active recording file.</div>
    </div>
  </div>

  <script>
    const colors = ["#d97706","#2563eb","#059669","#7c3aed","#dc2626","#0891b2"];
    const cardsEl = document.getElementById("cards");
    const recState = document.getElementById("recState");
    const recordPath = document.getElementById("recordPath");
    const meta = document.getElementById("meta");
    const chart = document.getElementById("chart");
    const ctx = chart.getContext("2d");
    const params = new URLSearchParams(window.location.search);
    const theme = (params.get("theme") || "dark").toLowerCase();
    if (theme !== "light") {
      document.body.setAttribute("data-theme", "dark");
    } else {
      document.body.removeAttribute("data-theme");
    }

    document.getElementById("startBtn").addEventListener("click", async () => {
      const r = await fetch("/api/record/start", { method: "POST" });
      if (!r.ok) alert("Could not start recording");
      refresh(true);
    });
    document.getElementById("stopBtn").addEventListener("click", async () => {
      const r = await fetch("/api/record/stop", { method: "POST" });
      if (!r.ok) alert("Could not stop recording");
      refresh(true);
    });

    function n(v, unit = "", digits = 1) {
      if (v === null || v === undefined || Number.isNaN(v)) return "-";
      return Number(v).toFixed(digits) + unit;
    }

    function renderCards(cpu, gpus) {
      cardsEl.innerHTML = "";
      const cpuCard = document.createElement("div");
      cpuCard.className = "card";
      cpuCard.innerHTML = `
        <div class="k">CPU</div>
        <div class="v" style="color:#f59e0b">${n(cpu, "%")}</div>
        <div class="small">Host Total Utilization</div>
      `;
      cardsEl.appendChild(cpuCard);
      const keys = Object.keys(gpus).sort((a,b) => Number(a) - Number(b));
      keys.forEach((gpu, i) => {
        const d = gpus[gpu];
        const el = document.createElement("div");
        el.className = "card";
        el.innerHTML = `
          <div class="k">GPU ${gpu}</div>
          <div class="v" style="color:${colors[i % colors.length]}">${n(d.util_gpu_pct, "%")}</div>
          <div class="small">${d.gpu_name || ""}</div>
          <div class="small">Mem: ${n(d.util_mem_pct, "%")} | Temp: ${n(d.temp_c, " C")} | Power: ${n(d.power_w, " W")}</div>
        `;
        cardsEl.appendChild(el);
      });
    }

    function drawChart(seriesByGpu, cpuSeries) {
      const w = chart.width;
      const h = chart.height;
      const pad = { l: 44, r: 14, t: 12, b: 24 };
      ctx.clearRect(0, 0, w, h);
      const dark = document.body.getAttribute("data-theme") === "dark";
      ctx.fillStyle = dark ? "#0f172a" : "#ffffff";
      ctx.fillRect(0, 0, w, h);

      const x0 = pad.l, y0 = pad.t, x1 = w - pad.r, y1 = h - pad.b;
      ctx.strokeStyle = dark ? "#334155" : "#e5e7eb";
      ctx.lineWidth = 1;
      for (let i = 0; i <= 5; i++) {
        const y = y0 + (y1 - y0) * (i / 5);
        ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke();
        const val = (100 - (i * 20));
        ctx.fillStyle = dark ? "#94a3b8" : "#6b7280";
        ctx.font = "11px monospace";
        ctx.fillText(`${val}%`, 6, y + 4);
      }

      const all = [];
      Object.values(seriesByGpu).forEach(arr => arr.forEach(p => all.push(p)));
      (cpuSeries || []).forEach(p => all.push(p));
      if (!all.length) return;
      const tMin = Math.min(...all.map(p => p.t));
      const tMax = Math.max(...all.map(p => p.t));
      const span = Math.max(1, tMax - tMin);

      const keys = Object.keys(seriesByGpu).sort((a,b) => Number(a) - Number(b));
      keys.forEach((gpu, i) => {
        const arr = seriesByGpu[gpu];
        if (arr.length < 2) return;
        ctx.strokeStyle = colors[i % colors.length];
        ctx.lineWidth = 2;
        ctx.beginPath();
        arr.forEach((p, idx) => {
          const x = x0 + ((p.t - tMin) / span) * (x1 - x0);
          const y = y1 - (Math.max(0, Math.min(100, p.v)) / 100) * (y1 - y0);
          if (idx === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        });
        ctx.stroke();
      });

      if ((cpuSeries || []).length >= 2) {
        ctx.strokeStyle = "#f59e0b";
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 4]);
        ctx.beginPath();
        cpuSeries.forEach((p, idx) => {
          const x = x0 + ((p.t - tMin) / span) * (x1 - x0);
          const y = y1 - (Math.max(0, Math.min(100, p.v)) / 100) * (y1 - y0);
          if (idx === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        });
        ctx.stroke();
        ctx.setLineDash([]);
      }
    }

    async function refresh(withStatus = false) {
      const dataRes = await fetch("/api/data");
      if (!dataRes.ok) return;
      const data = await dataRes.json();
      renderCards(data.cpu_latest, data.latest || {});
      drawChart(data.series || {}, data.cpu_series || []);
      meta.textContent = `Backend: ${data.backend} | Interval: ${data.interval_s}s | History: ${data.history_seconds}s`;
      if (!withStatus) {
        const sRes = await fetch("/api/status");
        if (!sRes.ok) return;
        const status = await sRes.json();
        setStatus(status);
      }
    }

    function setStatus(status) {
      const on = !!status.recording;
      recState.textContent = on ? "ON" : "OFF";
      recState.className = on ? "status-on" : "status-off";
      recordPath.textContent = status.csv_path ? `Recording file: ${status.csv_path}` : "No active recording file.";
    }

    async function init() {
      const sRes = await fetch("/api/status");
      if (sRes.ok) setStatus(await sRes.json());
      await refresh(false);
      setInterval(refresh, 1000);
    }
    init();
  </script>
</body>
</html>
"""


class AppState:
    def __init__(
        self,
        backend: str,
        interval_s: float,
        history_seconds: int,
        output_dir: Path,
        demo_gpus: int,
    ) -> None:
        self.backend = backend
        self.interval_s = max(0.1, interval_s)
        self.history_seconds = max(30, history_seconds)
        self.output_dir = output_dir
        self.demo_gpus = demo_gpus
        self.max_points = int(self.history_seconds / self.interval_s) + 3

        self.latest: dict[str, dict[str, Any]] = {}
        self.series: dict[str, deque[dict[str, float]]] = {}
        self.cpu_latest: float | None = None
        self.cpu_series: deque[dict[str, float]] = deque(maxlen=self.max_points)
        self.recording = False
        self.csv_path: Path | None = None
        self.samples_written = 0
        self.last_error: str | None = None
        self.lock = threading.Lock()
        self.stop_event = threading.Event()

    def start_recording(self) -> None:
        with self.lock:
            if self.recording:
                return
            stamp = time.strftime("%Y%m%d_%H%M%S")
            csv_path = self.output_dir / "logs" / f"gpu_usage_{stamp}.csv"
            self.output_dir.mkdir(parents=True, exist_ok=True)
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            self.csv_path = csv_path
            self.samples_written = 0
            self.recording = True

    def stop_recording(self) -> None:
        with self.lock:
            self.recording = False

    def snapshot_status(self) -> dict[str, Any]:
        with self.lock:
            return {
                "backend": self.backend,
                "interval_s": self.interval_s,
                "history_seconds": self.history_seconds,
                "cpu_latest": self.cpu_latest,
                "recording": self.recording,
                "csv_path": str(self.csv_path) if self.csv_path else None,
                "samples_written": self.samples_written,
                "last_error": self.last_error,
            }

    def snapshot_data(self) -> dict[str, Any]:
        with self.lock:
            series_out: dict[str, list[dict[str, float]]] = {}
            for gpu, q in self.series.items():
                series_out[gpu] = list(q)
            return {
                "backend": self.backend,
                "interval_s": self.interval_s,
                "history_seconds": self.history_seconds,
                "cpu_latest": self.cpu_latest,
                "cpu_series": list(self.cpu_series),
                "latest": self.latest,
                "series": series_out,
                "recording": self.recording,
                "csv_path": str(self.csv_path) if self.csv_path else None,
            }

    def sampler_loop(self) -> None:
        while not self.stop_event.is_set():
            now = time.time()
            try:
                rows = gpu_monitor.collect_once(self.backend, now, self.demo_gpus)
                cpu_util = gpu_monitor.collect_cpu_util_pct()
                with self.lock:
                    self.last_error = None
                    self.cpu_latest = cpu_util
                    if cpu_util is not None:
                        self.cpu_series.append({"t": float(now), "v": float(cpu_util)})
                    for row in rows:
                        gpu = str(row.get("gpu_index", "0"))
                        row["cpu_util_pct"] = cpu_util
                        self.latest[gpu] = row
                        if gpu not in self.series:
                            self.series[gpu] = deque(maxlen=self.max_points)
                        self.series[gpu].append(
                            {"t": float(now), "v": float(row.get("util_gpu_pct") or 0.0)}
                        )
                    if self.recording and self.csv_path is not None:
                        gpu_monitor.write_csv(self.csv_path, rows)
                        self.samples_written += 1
            except Exception as exc:
                with self.lock:
                    self.last_error = str(exc)
            self.stop_event.wait(self.interval_s)


def make_handler(state: AppState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, payload: dict[str, Any], code: int = 200) -> None:
            blob = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(blob)))
            self.end_headers()
            self.wfile.write(blob)

        def _send_html(self, html: str, code: int = 200) -> None:
            blob = html.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(blob)))
            self.end_headers()
            self.wfile.write(blob)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send_html(INDEX_HTML)
                return
            if parsed.path == "/api/status":
                self._send_json(state.snapshot_status())
                return
            if parsed.path == "/api/data":
                self._send_json(state.snapshot_data())
                return
            if parsed.path == "/health":
                self._send_json({"ok": True})
                return
            self._send_json({"error": "Not found"}, code=HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            _ = parse_qs(parsed.query)
            if parsed.path == "/api/record/start":
                state.start_recording()
                self._send_json(state.snapshot_status())
                return
            if parsed.path == "/api/record/stop":
                state.stop_recording()
                self._send_json(state.snapshot_status())
                return
            self._send_json({"error": "Not found"}, code=HTTPStatus.NOT_FOUND)

        def log_message(self, fmt: str, *args: Any) -> None:
            return

    return Handler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GPU usage web dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8765, help="Bind port")
    parser.add_argument("--backend", choices=["nvidia", "rocm", "sysfs", "demo"], default=None, help="Backend override")
    parser.add_argument("--interval", type=float, default=1.0, help="Sampling interval in seconds")
    parser.add_argument("--history", type=int, default=300, help="Live chart history window in seconds")
    parser.add_argument("--output-dir", default="gpu-monitor", help="Output root (logs/)")
    parser.add_argument("--demo-gpus", type=int, default=1, help="Synthetic GPU count for demo backend")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        backend = gpu_monitor.detect_backend(args.backend)
    except RuntimeError as exc:
        print(f"Error: {exc}")
        return 1

    state = AppState(
        backend=backend,
        interval_s=args.interval,
        history_seconds=args.history,
        output_dir=Path(args.output_dir).resolve(),
        demo_gpus=args.demo_gpus,
    )
    thread = threading.Thread(target=state.sampler_loop, daemon=True)
    thread.start()

    server = ThreadingHTTPServer((args.host, args.port), make_handler(state))
    print(f"GPU dashboard running: http://{args.host}:{args.port}")
    print(f"Backend: {backend}")
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        state.stop_event.set()
        server.server_close()
        thread.join(timeout=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
