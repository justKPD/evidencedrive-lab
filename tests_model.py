"""Analytical/limiting-case and failure-path checks, not Bosch validation."""
import copy
import json
import math
from pathlib import Path
import time
import unittest

import model


def constant(value=0.6, **extra):
    return {"demand": [{"time_s": 0, "value": value}], **extra}


def fault(kind="power_loss", target="A", start=2, end=3, fid="fault-1", **extra):
    return {"id": fid, "kind": kind, "target": target, "start_s": start, "end_s": end, **extra}


def at(result, t):
    return next(r for r in result["trace"] if abs(r["t_s"] - t) < 1e-9)


class NumericalModelTests(unittest.TestCase):
    def test_zero_demand_is_constant_velocity(self):
        r = model.simulate(constant(0))
        self.assertAlmostEqual(r["summary"]["distance_m"], 120, places=9)
        self.assertEqual(r["summary"]["final_speed_mps"], 20)
        self.assertEqual(r["summary"]["peak_decel_mps2"], 0)

    def test_healthy_pressure_matches_analytical_step_response(self):
        r = model.simulate(constant())
        for t in (0, 0.02, 0.2, 1, 3):
            row = at(r, t)
            self.assertAlmostEqual(row["pressure_a"], 0.6 * (1 - math.exp(-t / 0.12)), places=12)
            self.assertAlmostEqual(row["pressure_b"], 0.6 * (1 - math.exp(-t / 0.18)), places=12)
            self.assertAlmostEqual(row["brake_decel_mps2"], row["pressure_a"] * 8, places=12)

    def test_initial_healthy_channels_do_not_wait_for_recovery(self):
        row = model.simulate(constant())["trace"][0]
        self.assertTrue(row["ready_a"] and row["ready_b"])
        self.assertEqual(row["recover_a_s"], 0)
        self.assertEqual(row["pressure_a"], 0)

    def test_velocity_matches_closed_form_discrete_integral(self):
        c = constant(duration_s=2, dt_s=0.02, initial_speed_mps=30)
        r = model.simulate(c)
        n, dt, ratio = 100, 0.02, math.exp(-0.02 / 0.12)
        expected = 30 - dt * 4.8 * (n - (1 - ratio ** n) / (1 - ratio))
        self.assertAlmostEqual(r["summary"]["final_speed_mps"], expected, places=10)

    def test_default_demand_is_zero_order_held_without_future_leakage(self):
        r = model.simulate()
        self.assertEqual(at(r, 0.48)["demand"], 0)
        self.assertEqual(at(r, 0.5)["demand"], 0.6)
        self.assertEqual(at(r, 0.5)["pressure_a"], 0)
        self.assertGreater(at(r, 0.52)["pressure_a"], 0)

    def test_independent_supply_failure_preserves_other_channel(self):
        healthy = model.simulate(constant())
        failed = model.simulate(constant(faults=[fault()]))
        for t in (2, 2.2, 2.98):
            row = at(failed, t)
            self.assertFalse(row["power_a"])
            self.assertTrue(row["power_b"])
            self.assertEqual(row["pressure_a"], 0)
            self.assertAlmostEqual(row["pressure_b"], at(healthy, t)["pressure_b"], places=12)
            self.assertAlmostEqual(row["brake_decel_mps2"], at(healthy, t)["pressure_b"] * 8, places=12)

    def test_shared_supply_failure_exposes_both_channels(self):
        r = model.simulate(constant(topology="shared", faults=[fault()]))
        row = at(r, 2.2)
        self.assertFalse(row["power_a"] or row["power_b"])
        self.assertEqual(row["brake_decel_mps2"], 0)

    def test_common_cause_failure_is_not_removed_by_independent_topology(self):
        r = model.simulate(constant(faults=[fault("common_power_loss", "both")]))
        self.assertEqual(at(r, 2.2)["pressure_a"], 0)
        self.assertEqual(at(r, 2.2)["pressure_b"], 0)

    def test_recovery_is_measured_from_sampled_restoration(self):
        r = model.simulate(constant(faults=[fault(end=3)]))
        self.assertAlmostEqual(at(r, 3)["recover_a_s"], 0.25)
        self.assertFalse(at(r, 3.24)["ready_a"])
        self.assertTrue(at(r, 3.26)["ready_a"])
        self.assertEqual(at(r, 3.26)["pressure_a"], 0)
        self.assertGreater(at(r, 3.28)["pressure_a"], 0)
        events = [e for e in r["events"] if e["type"] == "recovery_complete" and e["target"] == "A"]
        self.assertEqual(events[0]["t_s"], 3.26)

    def test_new_supply_failure_restarts_recovery_hold(self):
        r = model.simulate(constant(faults=[fault(end=2.2), fault(start=2.3, end=2.4, fid="again")]))
        self.assertFalse(at(r, 2.64)["ready_a"])
        self.assertTrue(at(r, 2.66)["ready_a"])

    def test_signal_delay_reads_only_past_demand(self):
        r = model.simulate({"faults": [fault("signal_delay", start=0, end=6, value=0.3)]})
        self.assertEqual(at(r, 0.78)["command_a"], 0)
        self.assertEqual(at(r, 0.8)["command_a"], 0.6)
        self.assertEqual(at(r, 0.5)["command_b"], 0.6)
        self.assertTrue(at(r, 0.6)["signal_disagreement"])

    def test_decimal_history_clock_does_not_add_an_extra_sample_delay(self):
        r = model.simulate({"faults": [fault("signal_delay", start=0, end=6, value=0.2)]})
        self.assertEqual(at(r, 0.68)["command_a"], 0)
        self.assertEqual(at(r, 0.7)["command_a"], 0.6)

    def test_signal_stuck_overrides_delayed_demand_and_can_block_release(self):
        f = [fault("signal_delay", start=0, end=6, value=0.3), fault("signal_stuck", start=1, end=6, value=0.8, fid="stuck")]
        r = model.simulate({"faults": f})
        self.assertEqual(at(r, 1.2)["command_a"], 0.8)
        self.assertGreater(at(r, 5.8)["pressure_a"], 0.79)
        self.assertEqual(at(r, 5.8)["demand"], 0)

    def test_actuator_stuck_retains_actual_pressure_at_activation(self):
        r = model.simulate(constant(faults=[fault("actuator_stuck", start=0.2, end=1)]))
        held = at(r, 0.2)["pressure_a"]
        for t in (0.4, 0.8, 0.98):
            self.assertEqual(at(r, t)["pressure_a"], held)
        self.assertGreater(at(r, 1.02)["pressure_a"], held)

    def test_power_clamp_overrides_stuck_actuator_without_reinstating_pressure(self):
        faults = [fault("actuator_stuck", start=0.2, end=6), fault(start=1, end=2, fid="power")]
        r = model.simulate(constant(faults=faults))
        self.assertGreater(at(r, 0.8)["pressure_a"], 0)
        self.assertEqual(at(r, 1)["pressure_a"], 0)
        self.assertEqual(at(r, 3)["pressure_a"], 0)
        self.assertEqual(at(r, 3)["mode_a"], "actuator_stuck")

    def test_stuck_activation_while_unpowered_captures_zero(self):
        faults = [fault(start=0, end=2), fault("actuator_stuck", start=1, end=6, fid="jam")]
        r = model.simulate(constant(faults=faults))
        self.assertEqual(at(r, 3)["pressure_a"], 0)

    def test_friction_and_redundant_arbitration_do_not_double_capacity(self):
        r = model.simulate(constant(1, friction_mu=0.2))
        self.assertAlmostEqual(at(r, 2)["brake_decel_mps2"], 0.2 * 9.81, places=12)
        both = model.simulate(constant())
        self.assertLessEqual(both["summary"]["peak_decel_mps2"], 4.8)

    def test_force_scales_with_mass_without_inventing_changed_deceleration(self):
        light = model.simulate(constant(mass_kg=1000))
        heavy = model.simulate(constant(mass_kg=2000))
        self.assertEqual(at(light, 1)["brake_decel_mps2"], at(heavy, 1)["brake_decel_mps2"])
        self.assertEqual(at(light, 1)["force_n"] * 2, at(heavy, 1)["force_n"])

    def test_velocity_never_negative_and_distance_monotonic(self):
        r = model.simulate(constant(1, initial_speed_mps=0.1))
        self.assertEqual(r["summary"]["final_speed_mps"], 0)
        self.assertTrue(all(row["speed_mps"] >= 0 for row in r["trace"]))
        self.assertTrue(all(a["distance_m"] <= b["distance_m"] for a, b in zip(r["trace"], r["trace"][1:])))

    def test_non_grid_fault_boundaries_have_explicit_sampled_events(self):
        r = model.simulate(constant(faults=[fault(start=0.513, end=0.731)]))
        starts = [e["t_s"] for e in r["events"] if e["type"] == "fault_start"]
        ends = [e["t_s"] for e in r["events"] if e["type"] == "fault_end"]
        self.assertEqual(starts, [0.52]); self.assertEqual(ends, [0.74])
        self.assertEqual(at(r, 0.52)["active_faults"], ["fault-1"])
        self.assertEqual(at(r, 0.74)["active_faults"], [])

    def test_sampling_does_not_read_even_slightly_future_knots_or_faults(self):
        r = model.simulate({"demand": [{"time_s": 0, "value": 0}, {"time_s": 0.50000000001, "value": 0.6}], "faults": [fault(start=0.50000000001, end=1)]})
        self.assertEqual(at(r, 0.5)["demand"], 0)
        self.assertEqual(at(r, 0.5)["active_faults"], [])
        self.assertEqual(at(r, 0.52)["demand"], 0.6)
        self.assertEqual(at(r, 0.52)["active_faults"], ["fault-1"])

    def test_finer_time_grid_converges_toward_continuous_step_integral(self):
        # Pressure integration is exact; the motion uses left-sample effort.
        duration, u, tau, max_decel, speed = 2, 0.6, 0.12, 8, 30
        exact_v = speed - u * max_decel * (duration - tau * (1 - math.exp(-duration / tau)))
        errors = []
        for dt in (0.1, 0.05, 0.025, 0.005):
            r = model.simulate(constant(u, duration_s=duration, dt_s=dt, initial_speed_mps=speed))
            errors.append(abs(r["summary"]["final_speed_mps"] - exact_v))
        self.assertTrue(all(a > b for a, b in zip(errors, errors[1:])), errors)
        self.assertLess(errors[-1], 0.013)

    def test_payload_is_unchanged_and_json_is_finite(self):
        c = constant(faults=[fault()]); original = copy.deepcopy(c)
        r = model.simulate(c)
        self.assertEqual(c, original)
        json.dumps(r, allow_nan=False)
        self.assertEqual(len(r["trace"]), 301)

    def test_strict_invalid_inputs_are_not_silently_repaired(self):
        cases = [
            {"unknown": 3}, {"friction_mu": float("nan")}, {"mass_kg": True}, {"mass_kg": 10**1000},
            {"dt_s": "0.02"}, {"duration_s": 6.01}, {"controller_revision": "arbitration-2"},
            {"topology": "magic"}, {"variant": "<script>"},
            {"demand": [{"time_s": 1, "value": 0.2}]},
            {"demand": [{"time_s": 0, "value": 0.2}, {"time_s": 0, "value": 0.4}]},
            {"demand": [{"time_s": 0, "value": 1.1}]},
            {"faults": [fault("power_loss", end=2, start=2)]},
            {"faults": [fault("unknown")]}, {"faults": [fault([])]}, {"faults": [fault("common_power_loss", "A")]},
            {"faults": [fault("signal_delay")]}, {"faults": [fault("signal_stuck", value=2)]},
            {"faults": [fault("actuator_stuck", value=0.5)]},
            {"faults": [fault(), fault(start=2.5, end=4, fid="overlap")]},
            {"faults": [fault(), fault(start=4, end=5)]},
            {"faults": [dict(fault(), hidden_label="PASS")]},
        ]
        for config in cases:
            with self.subTest(config=config), self.assertRaises(ValueError):
                model.simulate(config)

    def test_adjacent_fault_intervals_are_allowed_and_order_independent(self):
        faults = [fault(start=1, end=2), fault(start=2, end=3, fid="second")]
        first = model.simulate(constant(faults=faults))
        second = model.simulate(constant(faults=list(reversed(faults))))
        self.assertEqual(first["trace"], second["trace"])
        self.assertEqual(first["events"], second["events"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(NumericalModelTests)
    start = time.time()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    out = {"passed": result.wasSuccessful(), "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "elapsed_s": time.time() - start, "scope": "Declared independent numerical abstraction; not Bosch or functional-safety certification."}
    folder = Path(__file__).parent / "verification"
    folder.mkdir(exist_ok=True)
    (folder / "python_model_tests.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    raise SystemExit(0 if result.wasSuccessful() else 1)
