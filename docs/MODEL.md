# EvidenceDrive numerical model

`model.py` is an independently declared two-channel brake-effort abstraction.
Its implementation is not Bosch software, an identified internal defect, an
ECU implementation, real hydraulic validation or a functional-safety assessment.
The team's actual test artifact remains unconfirmed. The model supplies
computed observations to a separately reviewed contract and property checker.

## Public interface

- `defaults()` returns a fresh plain JSON-compatible configuration.
- `validate_config(partial)` merges a partial object into defaults, validates it
  strictly, normalizes numeric fields and returns a copy.
- `simulate(partial)` returns `{model_version, config, trace, events, summary}`.
- `MODEL_VERSION` is `edrive-model-1`.
- Running `python model.py` accepts a configuration JSON object on stdin and
  emits the complete result. No third-party numerical package is required.

A supplied `demand` or `faults` array replaces that default array entirely. For
example, changing the duration below the default last demand knot requires
supplying an appropriate demand array rather than silently truncating it.

## Declared equations

The demand is a zero-order-held sequence of strictly increasing knots, starting
at time zero, with values between zero and one. Each channel receives that
demand unless an explicit signal delay or stuck-command fault changes it.

For a healthy, ready channel with constant command `u` over one interval:

```
p(t + dt) = u + (p(t) - u) exp(-dt / tau)
```

Normalized pressure is clipped to `[0,1]`. The two channels are redundant, not
two additive sources of full braking capacity. The declared arbitration chooses
the larger channel pressure:

```
a_brake = min(max(pA,pB) * max_decel, friction_mu * 9.81)
force_capacity = mass * a_brake
v_next = max(0, v - a_brake * dt)
x_next = x + (v + v_next) * dt / 2
```

`brake_decel_mps2` is available braking effort expressed as deceleration, not the
finite-difference derivative after the vehicle has stopped. `force_n` is the
associated braking-force capacity; a nonzero value at rest does not imply
motion or mechanical work. `max_decel_mps2` is an explicit vehicle-level
parameter, so changing mass scales force but does not silently recalibrate it.

Pressure propagation is the exact first-order solution for the held command.
Motion uses effort sampled at the start of each interval. Trapezoid distance
uses clipped endpoint velocity; a stop occurring between grid points is
therefore a grid approximation. Step-size sensitivity is tested rather than
called independent physical validation.

## Clock and sample semantics

`duration_s / dt_s` must be integral. There are `duration/dt + 1` rows, including
both zero and the final time, at most 4,001. Times, history-query times and
recovery deadlines use a 12-decimal-place clock. This avoids a binary decimal
artifact such as `0.7 - 0.2` delaying a signal by a whole sample.

A row at `t` contains the current pressure, speed and distance **before** the
next interval is advanced. The command sampled at `t` drives the pressure update
for that next interval. There is no future-demand interpolation. A demand step
at `0.5s` has zero pressure at the `0.5s` row when starting from rest; response
first appears at the following sample.

Fault intervals are start-inclusive and end-exclusive. An event not exactly on
the grid takes effect at the first sampled point at or after it. For example,
on a `0.02s` grid, a fault starting at `0.513s` first appears at `0.52s`, and one
ending at `0.731s` first appears ended at `0.74s`. There is no tolerance that
activates a genuinely future knot or fault early.

## Faults and precedence

Every fault has a unique identifier, kind, target, start and end. Targets are
`A` or `B`, except `common_power_loss`, whose target is `both`.

| Fault | Declared effect |
|---|---|
| `power_loss` | Independent topology disables its target supply; shared topology disables both channels because they share that supply dependency. |
| `common_power_loss` | Disables both channels even with independently declared supplies. Independence is not immunity to an arbitrary common cause. |
| `signal_delay` | Reads the past held demand at `t-value`; negative history returns zero. `value` is seconds, 0–2. |
| `signal_stuck` | Forces its target command to `value`, 0–1. It takes precedence over signal delay. |
| `actuator_stuck` | Holds the actual current channel pressure when it becomes active; it accepts no invented pressure parameter. |

Power loss and the following recovery hold take precedence over actuator or
signal faults and clamp channel pressure to zero immediately. A stuck actuator
that was holding pressure does not reinstate that old pressure after a supply
loss; the zero clamp wins. If it first becomes stuck while unpowered, it holds
zero. After the stuck interval ends, an available channel resumes its ordinary
first-order response from the state actually present.

On the first sampled restoration of power, a channel starts its declared
`recovery_hold_s`. During the hold it remains unready with zero pressure. It
becomes ready at the first sample meeting the deadline, and pressure responds
over the subsequent interval. An initially healthy channel starts ready without
a recovery delay. A new power loss during recovery restarts this process.

Channel modes follow this priority: `power_lost`, `recovering`,
`actuator_stuck`, `signal_stuck`, `signal_delay`, `tracking`. Raw commands remain
visible even when their channel has no power. Signal disagreement indicates an
absolute command difference greater than 0.15 (with a small floating-point
comparison tolerance); it is an observation, not an automatic safety verdict.

Fault start/end and power/recovery transitions are recorded as events. Active
fault IDs are included in every sampled state. Fault lists are not secretly
converted into expected pass/fail outcomes.

## Strict supported envelope

- Duration 0.5–20s; dt 0.005–0.1s; at most 4,001 rows.
- Initial speed 0–60m/s; mass 100–5,000kg; friction coefficient 0.05–1.5.
- Maximum deceleration parameter 1–15m/s²; channel time constants 0.01–2s.
- Recovery hold 0–2s; at most 128 demand knots and 64 fault intervals.
- The variant is a bounded identifier. Only `controller_revision=arbitration-1`
  is implemented; another name cannot silently run the same algorithm.
- Unknown fields, malformed intervals, duplicate fault IDs, unsupported kinds,
  booleans/numeric strings in numeric fields and all nonfinite numbers are
  refused. Overlapping intervals with the same kind and target are ambiguous
  and refused; adjoining intervals and different fault mechanisms are allowed.

The accepted numerical bounds are demonstration limits, not manufacturer
ratings or claims about a particular vehicle.

## Verification

Run `python tests_model.py`. The result is saved to
`verification/python_model_tests.json`. The test set covers analytical
first-order pressure response, a closed-form discrete velocity integral,
zero-demand motion, no future access, independent/shared/common-cause faults,
recovery boundaries, delay and stuck precedence, force/friction bounds,
nonnegative velocity, monotone distance, grid convergence, immutable inputs and
strict error handling. The actual saved count takes precedence over a prose
count after edits.

These checks establish implementation behavior under the declared equations.
They do not independently validate the physical assumptions. A separate
Python/browser comparison is maintained by the integrating project owner;
matching implementations still do not prove a real braking system correct.
