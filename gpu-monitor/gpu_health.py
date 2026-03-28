#!/usr/bin/env python3
"""Lightweight GPU health policy checks for gpu-monitor."""

from __future__ import annotations

import json
import re
import subprocess
import warnings
from pathlib import Path
from typing import Any


DEFAULT_HEALTH_CONFIG: dict[str, Any] = {
    "temp_warning_c": 80.0,
    "temp_critical_c": 90.0,
    "vram_min_free_pct": 10.0,
    "power_warn_fraction_of_limit": 0.5,
    "ecc_sbe_warn_count": 10,
    "min_peak_util_pct": 0.0,
}

CRITICAL_XIDS = {31, 43, 48, 61, 62, 63, 64, 74, 79}
WARNING_XIDS = {13, 32, 45, 68, 92, 94, 95}
PROBLEM_THROTTLE_BITS = {
    0x0000000000000008: "HW_SLOWDOWN",
    0x0000000000000020: "SW_THERMAL_SLOWDOWN",
    0x0000000000000040: "HW_THERMAL_SLOWDOWN",
    0x0000000000000080: "HW_POWER_BRAKE_SLOWDOWN",
}
NORMAL_THROTTLE_BITS = {
    0x0000000000000001: "GPU_IDLE",
    0x0000000000000002: "APPLICATIONS_CLOCKS_SETTING",
    0x0000000000000004: "SW_POWER_CAP",
    0x0000000000000100: "DISPLAY_CLOCK_SETTING",
}
THROTTLE_REASONS = {
    **PROBLEM_THROTTLE_BITS,
    **NORMAL_THROTTLE_BITS,
    0x0000000000000010: "SYNC_BOOST",
}
_XID_RE = re.compile(r"Xid\s*\([^)]*\):\s*(\d+)")
_MODEL_CONFIG_DIR = Path(__file__).resolve().parent / "configs" / "models"


def slugify_model_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower())
    return slug.strip("_")


def _find_model_config_path(gpu_names: list[str]) -> Path | None:
    if not _MODEL_CONFIG_DIR.exists():
        return None
    for name in gpu_names:
        slug = slugify_model_name(name)
        candidate = _MODEL_CONFIG_DIR / f"{slug}.json"
        if candidate.exists():
            return candidate
    return None


def load_health_config(path: str | None, gpu_names: list[str] | None = None) -> dict[str, Any]:
    config = dict(DEFAULT_HEALTH_CONFIG)
    source = "defaults"
    if path:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Health config must be a JSON object")
        config.update(raw)
        source = str(Path(path).resolve())
    elif gpu_names:
        model_path = _find_model_config_path(gpu_names)
        if model_path is not None:
            raw = json.loads(model_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("Health config must be a JSON object")
            config.update(raw)
            source = str(model_path)

    config["_config_source"] = source
    if not path and source == "defaults":
        return config
    return config


def _nvml_module():
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import pynvml  # type: ignore
    except Exception:
        return None
    return pynvml


def query_xid_events() -> list[dict[str, Any]]:
    try:
        result = subprocess.run(
            ["dmesg", "--time-format=iso"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []

    events = []
    for line in result.stdout.splitlines():
        if "NVRM: Xid" not in line:
            continue
        match = _XID_RE.search(line)
        if not match:
            continue
        xid = int(match.group(1))
        if xid in CRITICAL_XIDS:
            severity = "FAIL"
        elif xid in WARNING_XIDS:
            severity = "WARN"
        else:
            severity = "INFO"
        events.append(
            {
                "xid": xid,
                "severity": severity,
                "raw": line.strip(),
            }
        )
    return events


def query_nvidia_gpu_health(gpu_index: int) -> dict[str, Any]:
    pynvml = _nvml_module()
    if pynvml is None:
        return {"available": False, "reason": "pynvml_unavailable"}

    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)

        power_limit_w = None
        try:
            power_limit_w = (
                pynvml.nvmlDeviceGetPowerManagementLimit(handle) / 1000.0
            )
        except Exception:
            power_limit_w = None

        graphics_max = None
        memory_max = None
        try:
            graphics_max = pynvml.nvmlDeviceGetMaxClockInfo(
                handle, pynvml.NVML_CLOCK_GRAPHICS
            )
        except Exception:
            graphics_max = None
        try:
            memory_max = pynvml.nvmlDeviceGetMaxClockInfo(
                handle, pynvml.NVML_CLOCK_MEM
            )
        except Exception:
            memory_max = None

        throttle_reasons = []
        problem_reasons = []
        unexpected_reasons = []
        try:
            bitmask = pynvml.nvmlDeviceGetCurrentClocksThrottleReasons(handle)
            for bit, name in THROTTLE_REASONS.items():
                if not bitmask & bit:
                    continue
                throttle_reasons.append(name)
                if bit in PROBLEM_THROTTLE_BITS:
                    problem_reasons.append(name)
                elif bit not in NORMAL_THROTTLE_BITS:
                    unexpected_reasons.append(name)
        except Exception:
            bitmask = None

        ecc = {
            "supported": False,
            "volatile_sbe": None,
            "volatile_dbe": None,
            "aggregate_sbe": None,
            "aggregate_dbe": None,
            "pending_retirement": False,
            "remap_failure": False,
        }
        try:
            vol_sbe = pynvml.nvmlDeviceGetTotalEccErrors(
                handle,
                pynvml.NVML_SINGLE_BIT_ECC,
                pynvml.NVML_VOLATILE_ECC,
            )
            vol_dbe = pynvml.nvmlDeviceGetTotalEccErrors(
                handle,
                pynvml.NVML_DOUBLE_BIT_ECC,
                pynvml.NVML_VOLATILE_ECC,
            )
            agg_sbe = pynvml.nvmlDeviceGetTotalEccErrors(
                handle,
                pynvml.NVML_SINGLE_BIT_ECC,
                pynvml.NVML_AGGREGATE_ECC,
            )
            agg_dbe = pynvml.nvmlDeviceGetTotalEccErrors(
                handle,
                pynvml.NVML_DOUBLE_BIT_ECC,
                pynvml.NVML_AGGREGATE_ECC,
            )
            ecc.update(
                {
                    "supported": True,
                    "volatile_sbe": vol_sbe,
                    "volatile_dbe": vol_dbe,
                    "aggregate_sbe": agg_sbe,
                    "aggregate_dbe": agg_dbe,
                }
            )
        except Exception:
            pass

        try:
            pending = pynvml.nvmlDeviceGetRetiredPages_v2(handle)
            ecc["pending_retirement"] = bool(pending)
        except Exception:
            pass

        try:
            remapped = pynvml.nvmlDeviceGetRemappedRows(handle)
            if isinstance(remapped, (list, tuple)) and len(remapped) == 4:
                ecc["remap_failure"] = bool(remapped[3])
        except Exception:
            pass

        return {
            "available": True,
            "power_limit_w": power_limit_w,
            "clock_graphics_max_mhz": graphics_max,
            "clock_memory_max_mhz": memory_max,
            "throttle_bitmask": hex(bitmask) if isinstance(bitmask, int) else None,
            "throttle_reasons": throttle_reasons,
            "problem_throttle_reasons": problem_reasons,
            "unexpected_throttle_reasons": unexpected_reasons,
            "ecc": ecc,
        }
    except Exception as exc:
        return {"available": False, "reason": str(exc)}
    finally:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass


def collect_nvidia_health(gpu_indices: list[int]) -> dict[str, Any]:
    return {
        str(gpu_index): query_nvidia_gpu_health(gpu_index)
        for gpu_index in sorted(set(gpu_indices))
    }


def _status_rank(status: str) -> int:
    return {"PASS": 0, "SKIP": 1, "WARN": 2, "FAIL": 3}.get(status, 0)


def _upgrade_status(current: str, new: str) -> str:
    return new if _status_rank(new) > _status_rank(current) else current


def _free_vram_pct(mem_used_mib: float | None, mem_total_mib: float | None) -> float | None:
    if mem_used_mib is None or mem_total_mib is None or mem_total_mib <= 0:
        return None
    return max(0.0, min(100.0, 100.0 * (1.0 - (mem_used_mib / mem_total_mib))))


def summarize_rows(
    rows: list[dict[str, Any]],
    *,
    backend: str,
    config: dict[str, Any],
    nvidia_health: dict[str, Any] | None = None,
    xid_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    gpu_rows: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        gpu = str(row.get("gpu_index", "0"))
        gpu_rows.setdefault(gpu, []).append(row)

    overall_status = "PASS"
    gpu_summaries = []
    session_gpus = []
    for gpu, group in sorted(gpu_rows.items(), key=lambda item: int(item[0]) if item[0].isdigit() else item[0]):
        latest = group[-1]
        util_values = [float(v) for v in (r.get("util_gpu_pct") for r in group) if isinstance(v, (int, float))]
        mem_util_values = [float(v) for v in (r.get("util_mem_pct") for r in group) if isinstance(v, (int, float))]
        temp_values = [float(v) for v in (r.get("temp_c") for r in group) if isinstance(v, (int, float))]
        power_values = [float(v) for v in (r.get("power_w") for r in group) if isinstance(v, (int, float))]
        free_values = [
            pct
            for pct in (
                _free_vram_pct(r.get("mem_used_mib"), r.get("mem_total_mib")) for r in group
            )
            if pct is not None
        ]
        metrics = {
            "gpu_name": latest.get("gpu_name"),
            "samples": len(group),
            "avg_util_gpu_pct": (sum(util_values) / len(util_values)) if util_values else None,
            "peak_util_gpu_pct": max(util_values) if util_values else None,
            "avg_util_mem_pct": (sum(mem_util_values) / len(mem_util_values)) if mem_util_values else None,
            "peak_util_mem_pct": max(mem_util_values) if mem_util_values else None,
            "max_temp_c": max(temp_values) if temp_values else None,
            "max_power_w": max(power_values) if power_values else None,
            "min_free_vram_pct": min(free_values) if free_values else None,
            "latest_util_gpu_pct": latest.get("util_gpu_pct"),
        }
        issues = []
        status = "PASS"

        max_temp = metrics["max_temp_c"]
        if isinstance(max_temp, (int, float)):
            if max_temp >= float(config["temp_critical_c"]):
                status = _upgrade_status(status, "FAIL")
                issues.append(
                    {
                        "status": "FAIL",
                        "check": "temperature",
                        "message": f"Peak temperature {max_temp:.1f}C exceeded critical threshold",
                    }
                )
            elif max_temp >= float(config["temp_warning_c"]):
                status = _upgrade_status(status, "WARN")
                issues.append(
                    {
                        "status": "WARN",
                        "check": "temperature",
                        "message": f"Peak temperature {max_temp:.1f}C exceeded warning threshold",
                    }
                )

        min_free = metrics["min_free_vram_pct"]
        if isinstance(min_free, (int, float)) and min_free < float(config["vram_min_free_pct"]):
            status = _upgrade_status(status, "WARN")
            issues.append(
                {
                    "status": "WARN",
                    "check": "vram_free",
                    "message": f"Free VRAM dropped to {min_free:.1f}%",
                }
            )

        peak_util = metrics["peak_util_gpu_pct"]
        min_peak_util = float(config.get("min_peak_util_pct", 0.0))
        if min_peak_util > 0 and isinstance(peak_util, (int, float)) and peak_util < min_peak_util:
            status = _upgrade_status(status, "WARN")
            issues.append(
                {
                    "status": "WARN",
                    "check": "utilization_floor",
                    "message": f"Peak GPU utilization only reached {peak_util:.1f}% (target: {min_peak_util:.1f}%)",
                }
            )

        extra = (nvidia_health or {}).get(gpu, {})
        power_limit_w = extra.get("power_limit_w")
        max_power = metrics["max_power_w"]
        if isinstance(power_limit_w, (int, float)) and isinstance(max_power, (int, float)):
            warn_limit = power_limit_w * float(config["power_warn_fraction_of_limit"])
            if max_power > warn_limit:
                status = _upgrade_status(status, "WARN")
                issues.append(
                    {
                        "status": "WARN",
                        "check": "power_baseline",
                        "message": (
                            f"Power reached {max_power:.1f}W against {power_limit_w:.1f}W limit"
                        ),
                    }
                )

        if extra.get("problem_throttle_reasons"):
            reasons = ", ".join(extra["problem_throttle_reasons"])
            status = _upgrade_status(status, "FAIL")
            issues.append(
                {
                    "status": "FAIL",
                    "check": "clock_throttle",
                    "message": f"Problematic clock throttle active: {reasons}",
                }
            )
        elif extra.get("unexpected_throttle_reasons"):
            reasons = ", ".join(extra["unexpected_throttle_reasons"])
            status = _upgrade_status(status, "WARN")
            issues.append(
                {
                    "status": "WARN",
                    "check": "clock_throttle",
                    "message": f"Unexpected clock limiting active: {reasons}",
                }
            )

        graphics_max = extra.get("clock_graphics_max_mhz")
        memory_max = extra.get("clock_memory_max_mhz")
        if graphics_max == 0 and memory_max == 0:
            status = _upgrade_status(status, "FAIL")
            issues.append(
                {
                    "status": "FAIL",
                    "check": "clocks_responsive",
                    "message": "Reported max graphics and memory clocks are both 0",
                }
            )

        ecc = extra.get("ecc", {})
        if ecc.get("supported"):
            vol_dbe = ecc.get("volatile_dbe") or 0
            agg_dbe = ecc.get("aggregate_dbe") or 0
            vol_sbe = ecc.get("volatile_sbe") or 0
            agg_sbe = ecc.get("aggregate_sbe") or 0
            sbe_warn_count = int(config["ecc_sbe_warn_count"])
            if vol_dbe > 0 or agg_dbe > 0:
                status = _upgrade_status(status, "FAIL")
                issues.append(
                    {
                        "status": "FAIL",
                        "check": "ecc_health",
                        "message": f"Double-bit ECC errors detected: volatile={vol_dbe}, aggregate={agg_dbe}",
                    }
                )
            elif ecc.get("remap_failure"):
                status = _upgrade_status(status, "FAIL")
                issues.append(
                    {
                        "status": "FAIL",
                        "check": "ecc_health",
                        "message": "Row remapping failure detected",
                    }
                )
            elif vol_sbe > sbe_warn_count or agg_sbe > sbe_warn_count:
                status = _upgrade_status(status, "WARN")
                issues.append(
                    {
                        "status": "WARN",
                        "check": "ecc_health",
                        "message": f"Elevated ECC single-bit errors: volatile={vol_sbe}, aggregate={agg_sbe}",
                    }
                )
            elif ecc.get("pending_retirement"):
                status = _upgrade_status(status, "WARN")
                issues.append(
                    {
                        "status": "WARN",
                        "check": "ecc_health",
                        "message": "Pages pending retirement; reboot recommended",
                    }
                )

        overall_status = _upgrade_status(overall_status, status)
        gpu_summaries.append(
            {
                "gpu_index": gpu,
                "status": status,
                "metrics": metrics,
                "issues": issues,
                "nvidia_health": extra or None,
            }
        )
        session_gpus.append(
            {
                "gpu_index": gpu,
                "gpu_name": latest.get("gpu_name"),
                "avg_util_gpu_pct": metrics["avg_util_gpu_pct"],
                "peak_util_gpu_pct": metrics["peak_util_gpu_pct"],
                "peak_util_mem_pct": metrics["peak_util_mem_pct"],
                "max_temp_c": metrics["max_temp_c"],
                "max_power_w": metrics["max_power_w"],
            }
        )

    node_issues = []
    for evt in xid_events or []:
        if evt["severity"] not in {"FAIL", "WARN"}:
            continue
        overall_status = _upgrade_status(overall_status, evt["severity"])
        node_issues.append(
            {
                "status": evt["severity"],
                "check": "xid_errors",
                "message": f"XID {evt['xid']} detected",
                "raw": evt.get("raw"),
            }
        )

    return {
        "overall_status": overall_status,
        "backend": backend,
        "thresholds": config,
        "config_source": config.get("_config_source", "defaults"),
        "session_summary": {
            "gpu_count": len(gpu_summaries),
            "gpus": session_gpus,
        },
        "gpu_summaries": gpu_summaries,
        "node_issues": node_issues,
    }


def summarize_latest_rows(
    latest_rows: list[dict[str, Any]],
    *,
    backend: str,
    config: dict[str, Any],
    nvidia_health: dict[str, Any] | None = None,
    xid_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return summarize_rows(
        latest_rows,
        backend=backend,
        config=config,
        nvidia_health=nvidia_health,
        xid_events=xid_events,
    )
