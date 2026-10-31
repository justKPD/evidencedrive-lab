"""Declared two-channel brake-effort abstraction, independent of Bosch software.

The model exposes explicit assumptions and computed observations; it does not
assign safety verdicts. A separate reviewed contract/oracle interprets a trace.
Only the Python standard library is required.
"""
from __future__ import annotations

from copy import deepcopy
import math
import re
from typing import Any

MODEL_VERSION = "edrive-model-1"
EPS = 1e-10
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,79}\Z")
FAULT_KINDS = {"power_loss", "common_power_loss", "signal_delay", "signal_stuck", "actuator_stuck"}


def defaults() -> dict[str, Any]:
    """Return an independent, mutable copy of the documented configuration."""
    return {
        "duration_s": 6,
        "dt_s": 0.02,
        "initial_speed_mps": 20,
        "mass_kg": 1600,
        "friction_mu": 0.9,
        "max_decel_mps2": 8,
        "tau_a_s": 0.12,
        "tau_b_s": 0.18,
        "recovery_hold_s": 0.25,
        "topology": "independent",
        "variant": "demo-v1",
        "controller_revision": "arbitration-1",
        "demand": [
            {"time_s": 0, "value": 0},
            {"time_s": 0.5, "value": 0.6},
            {"time_s": 5, "value": 0},
        ],
        "faults": [],
    }


def _number(value: Any, name: str, low: float, high: float) -> float:
    try:
        finite = math.isfinite(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else False
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError(f"{name} must be a finite number, not a boolean or numeric string.")
    if not low <= value <= high:
        raise ValueError(f"{name} must be between {low} and {high}.")
    return float(value)


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError(f"{name} must be a 1–80 character identifier using letters, digits, . _ : or -.")
    return value


def validate_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate and normalize a partial configuration without mutating it.

    A supplied demand/fault array replaces that entire default array. Unknown
    fields and unsupported controller revisions are refused rather than ignored.
    """
    if config is None:
        config = {}
    if not isinstance(config, dict):
        raise ValueError("Simulation configuration must be an object.")
    c = defaults()
    unknown = set(config) - set(c)
    if unknown:
        raise ValueError("Unknown configuration fields: " + ", ".join(sorted(unknown)))
    c.update(deepcopy(config))
    limits = {
        "duration_s": (0.5, 20), "dt_s": (0.005, 0.1),
        "initial_speed_mps": (0, 60), "mass_kg": (100, 5000),
        "friction_mu": (0.05, 1.5), "max_decel_mps2": (1, 15),
        "tau_a_s": (0.01, 2), "tau_b_s": (0.01, 2),
        "recovery_hold_s": (0, 2),
    }
    for key, (low, high) in limits.items():
        c[key] = _number(c[key], key, low, high)
    quotient = c["duration_s"] / c["dt_s"]
    if abs(quotient - round(quotient)) > 1e-8:
        raise ValueError("duration_s / dt_s must be an integer.")
    if round(quotient) + 1 > 4001:
        raise ValueError("The simulation may contain at most 4001 sampled states.")
    if c["topology"] not in ("independent", "shared"):
        raise ValueError("topology must be independent or shared.")
    c["variant"] = _identifier(c["variant"], "variant")
    if c["controller_revision"] != "arbitration-1":
        raise ValueError("Only controller_revision arbitration-1 is implemented.")

    knots = c["demand"]
    if not isinstance(knots, list) or not 1 <= len(knots) <= 128:
        raise ValueError("demand must contain 1–128 zero-order-held knots.")
    previous = -math.inf
    normalized = []
    for index, knot in enumerate(knots):
        if not isinstance(knot, dict) or set(knot) != {"time_s", "value"}:
            raise ValueError("Each demand knot must contain exactly time_s and value.")
        t = _number(knot["time_s"], f"demand[{index}].time_s", 0, c["duration_s"])
        value = _number(knot["value"], f"demand[{index}].value", 0, 1)
        if t <= previous:
            raise ValueError("Demand knot times must be strictly increasing.")
        if index == 0 and t != 0:
            raise ValueError("The first demand knot must start at time 0.")
        normalized.append({"time_s": t, "value": value})
        previous = t
    c["demand"] = normalized

    faults = c["faults"]
    if not isinstance(faults, list) or len(faults) > 64:
        raise ValueError("faults must be an array of at most 64 intervals.")
    ids = set()
    normalized_faults = []
    for index, fault in enumerate(faults):
        if not isinstance(fault, dict):
            raise ValueError(f"faults[{index}] must be an object.")
        required = {"id", "kind", "target", "start_s", "end_s"}
        if not required <= set(fault) or set(fault) - required - {"value"}:
            raise ValueError("Each fault requires id, kind, target, start_s, end_s and only an optional value.")
        fid = _identifier(fault["id"], f"faults[{index}].id")
        if fid in ids:
            raise ValueError("Fault identities must be unique.")
        ids.add(fid)
        kind, target = fault["kind"], fault["target"]
        if not isinstance(kind, str) or kind not in FAULT_KINDS:
            raise ValueError("Unknown fault kind: " + str(kind))
        if (kind == "common_power_loss" and target != "both") or (kind != "common_power_loss" and target not in ("A", "B")):
            raise ValueError("common_power_loss targets both; other faults target A or B.")
        start = _number(fault["start_s"], f"faults[{index}].start_s", 0, c["duration_s"])
        end = _number(fault["end_s"], f"faults[{index}].end_s", 0, c["duration_s"])
        if start >= end:
            raise ValueError("A fault end_s must be greater than start_s.")
        item = {"id": fid, "kind": kind, "target": target, "start_s": start, "end_s": end}
        if kind in ("signal_delay", "signal_stuck"):
            if "value" not in fault:
                raise ValueError(kind + " requires a numeric value.")
            item["value"] = _number(fault["value"], f"faults[{index}].value", 0, 2 if kind == "signal_delay" else 1)
        elif "value" in fault:
            raise ValueError("Only signal_delay and signal_stuck accept value; actuator_stuck captures its current pressure.")
        for old in normalized_faults:
            if old["kind"] == kind and old["target"] == target and max(start, old["start_s"]) < min(end, old["end_s"]):
                raise ValueError("Overlapping faults of the same kind and target are ambiguous.")
        normalized_faults.append(item)
    c["faults"] = normalized_faults
    return c


def _demand(c: dict[str, Any], time_s: float) -> float:
    if time_s < 0:
        return 0.0
    value = 0.0
    for knot in c["demand"]:
        if knot["time_s"] > time_s:
            break
        value = knot["value"]
    return value


def simulate(config_dict: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute the same declared equations for arbitrary validated inputs.

    A row at t records the state before advancing the next interval. Commands
    sampled at t drive that interval. Fault intervals are start-inclusive and
    end-exclusive, evaluated on the sample grid. No verdict is hardcoded here.
    """
    c = validate_config(config_dict)
    steps = round(c["duration_s"] / c["dt_s"])
    pressure = {"A": 0.0, "B": 0.0}
    was_power = {"A": True, "B": True}
    recover_at: dict[str, float | None] = {"A": None, "B": None}
    old_active: set[str] = set()
    fault_by_id = {fault["id"]: fault for fault in c["faults"]}
    speed, distance = c["initial_speed_mps"], 0.0
    trace, events = [], []

    def event(t: float, type_: str, target: str, message: str) -> None:
        events.append({"t_s": t, "type": type_, "target": target, "message": message})

    for index in range(steps + 1):
        t = round(index * c["dt_s"], 12)
        active = [f for f in c["faults"] if f["start_s"] <= t < f["end_s"]]
        active_ids = {f["id"] for f in active}
        for fid in sorted(active_ids - old_active):
            f = fault_by_id[fid]
            event(t, "fault_start", f["target"], f"{fid}: {f['kind']} became active on this sample.")
        for fid in sorted(old_active - active_ids):
            f = fault_by_id[fid]
            event(t, "fault_end", f["target"], f"{fid}: {f['kind']} ended on this sample.")
        old_active = active_ids

        demand = _demand(c, t)
        power = {"A": True, "B": True}
        for f in active:
            if f["kind"] == "common_power_loss" or (f["kind"] == "power_loss" and c["topology"] == "shared"):
                power = {"A": False, "B": False}
            elif f["kind"] == "power_loss":
                power[f["target"]] = False
        ready, modes, commands, stuck = {}, {}, {}, {}
        for channel in ("A", "B"):
            if not power[channel]:
                pressure[channel] = 0.0
                recover_at[channel] = None
                if was_power[channel]:
                    event(t, "power_lost", channel, "Pressure is clamped to zero while this supply is unavailable.")
            elif not was_power[channel]:
                recover_at[channel] = round(t + c["recovery_hold_s"], 12)
                event(t, "power_restored", channel, "Supply restored; the declared recovery hold begins.")
            ready[channel] = power[channel] and (recover_at[channel] is None or t >= recover_at[channel])
            if ready[channel] and recover_at[channel] is not None:
                event(t, "recovery_complete", channel, "Recovery hold completed; subsequent intervals may track demand.")
                recover_at[channel] = None
            if not ready[channel]:
                pressure[channel] = 0.0
            selected = {f["kind"]: f for f in active if f["target"] == channel}
            delay = selected.get("signal_delay", {}).get("value", 0.0)
            command = _demand(c, round(t - delay, 12))
            if "signal_stuck" in selected:
                command = selected["signal_stuck"]["value"]
            commands[channel] = command
            stuck[channel] = "actuator_stuck" in selected
            modes[channel] = (
                "power_lost" if not power[channel] else
                "recovering" if not ready[channel] else
                "actuator_stuck" if stuck[channel] else
                "signal_stuck" if "signal_stuck" in selected else
                "signal_delay" if "signal_delay" in selected else "tracking"
            )
            was_power[channel] = power[channel]

        effort = min(max(pressure.values()) * c["max_decel_mps2"], c["friction_mu"] * 9.81)
        trace.append({
            "t_s": t, "demand": demand,
            "requested_decel_mps2": demand * c["max_decel_mps2"],
            "pressure_a": pressure["A"], "pressure_b": pressure["B"],
            "command_a": commands["A"], "command_b": commands["B"],
            "power_a": power["A"], "power_b": power["B"],
            "ready_a": ready["A"], "ready_b": ready["B"],
            "recover_a_s": max(0.0, recover_at["A"] - t) if recover_at["A"] is not None else 0.0,
            "recover_b_s": max(0.0, recover_at["B"] - t) if recover_at["B"] is not None else 0.0,
            "mode_a": modes["A"], "mode_b": modes["B"],
            "brake_decel_mps2": effort, "speed_mps": speed,
            "distance_m": distance, "force_n": c["mass_kg"] * effort,
            "active_faults": sorted(active_ids),
            "signal_disagreement": abs(commands["A"] - commands["B"]) > 0.15 + EPS,
        })
        if index == steps:
            break
        # The state at t drives motion during [t,t+dt). Trapezoid distance is a
        # declared grid approximation, including when velocity reaches zero.
        following_speed = max(0.0, speed - effort * c["dt_s"])
        distance += 0.5 * (speed + following_speed) * c["dt_s"]
        speed = following_speed
        for channel, tau_key in (("A", "tau_a_s"), ("B", "tau_b_s")):
            if not ready[channel]:
                pressure[channel] = 0.0
            elif not stuck[channel]:
                command = commands[channel]
                pressure[channel] = min(1.0, max(0.0, command + (pressure[channel] - command) * math.exp(-c["dt_s"] / c[tau_key])))
            # A stuck actuator retains its current value. If power/recovery
            # clamped it to zero, no stored-pressure value is reinstated.
    return {
        "model_version": MODEL_VERSION, "config": c, "trace": trace,
        "events": events,
        "summary": {
            "duration_s": c["duration_s"], "final_speed_mps": trace[-1]["speed_mps"],
            "distance_m": trace[-1]["distance_m"],
            "peak_decel_mps2": max(row["brake_decel_mps2"] for row in trace),
            "min_speed_mps": min(row["speed_mps"] for row in trace),
            "model_steps": len(trace),
        },
    }


if __name__ == "__main__":
    import json
    import sys
    incoming = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    print(json.dumps(simulate(incoming), allow_nan=False))
