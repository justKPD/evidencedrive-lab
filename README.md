# EvidenceDrive Lab

**Does this source still support this engineering test, and does the evidence still support its conclusion after a change?**

An independent work sample connecting technical knowledge, reviewed test contracts, numerical fault experiments and inspectable evidence. Prepared around the public duties of Bosch REF299133V; no claim that this is Bosch's internal architecture or a discovered company defect.

## What works

1. **Configure and observe:** edit topology, demand history, friction, actuator dynamics, restoration hold and timed fault sequences. Run the actual numerical model. Inspect selected and no-fault reference vehicles on the same clock. Rotate, zoom, use the cutaway and jump to computed fault events or failed observations.
2. **Knowledge to test:** search exact source passages, ingest your own prose or structured source, inspect a proposed metric/limit/units/scope, explicitly review it and execute a check. Unknown tolerances remain incomplete. A simulation by itself has no test verdict.
3. **Change to evidence:** revise a source and assess each saved result's applicability. Preserve the old verdict and snapshots; separate citation review, required retest, incompatible scope and unknown assumptions.
4. **Experiments and proof:** execute a bounded fault campaign or twelve controlled source/context changes. Inspect the actual case, return to the working investigation, export the correct record and see withholding and full compute accounting.

The question panel inspects recorded state and suggests next steps. Only its documented explicit run command starts a model exploration. It cannot approve a test, invent a tolerance or rewrite a result. Optional free OpenRouter explanations are server-side, read-only proposals; deterministic guidance works without them.

## Run locally

Python 3.11+ and a modern WebGL browser are sufficient for the application. From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open **http://127.0.0.1:8786/**. `Start_EvidenceDrive.ps1` is the existing Windows launcher. Stop the service with Ctrl+C when launched in a terminal.

The local app calls the Python model. Serving only `web/` runs the independently implemented JavaScript model and displays **Browser solver**. A compatible Python service refusing a run is shown as an error, never bypassed by silent JavaScript fallback. `?fallback=1` exercises the computed SVG view when WebGL is unavailable.

## Model and evidence boundaries

- Declared lumped two-channel model, shared or independent supplies, first-order actuator response, friction bound and nonnegative vehicle speed. Capacity is `max(A,B)`, not an invented additive capacity. See [MODEL.md](docs/MODEL.md).
- Five mechanisms: local power loss, common power loss, delayed request, stuck request and stuck actuator. This is not a detailed hydraulic circuit, ABS/ESC implementation, actual Bosch brake controller or physical validation.
- Sources and acceptance limits shipped with the demo are **authored examples**, not Bosch requirements. Retrieval is lexical passage matching with scope checks, not general semantic understanding. Arbitrary prose is stored but never automatically promoted into an executable acceptance rule.
- Source, configuration, contract and result identities are preserved. Import recomputes numerical and property evidence. Content checksums detect changes but are not signatures, access control or proof of authorship. See [EVIDENCE.md](docs/EVIDENCE.md).
- Browser IndexedDB retains a working investigation locally. Export important work; clearing browser storage removes it. Campaign inspection has its own export and a return action. No multi-user database is implied.
- No functional-safety certification, HIL test, actual vehicle connection, confidential company data or measured factory saving is claimed.

## Reproduce verification

Start the local service, install Node.js, then run:

```powershell
.\.venv\Scripts\python.exe verify_all.py
```

Browser tests require Playwright and Microsoft Edge (`npm install --no-save playwright`, or set `PLAYWRIGHT_MODULE` to an installed module). The supplied environment also resolves the Codex bundled runtime. Unit/model-only checks:

```powershell
.\.venv\Scripts\python.exe -m unittest tests_model tests_service -q
node tests_evidence.mjs
.\.venv\Scripts\python.exe verify_cross_language.py
```

The full runner records source hashes, step outputs and machine-readable counts in `verification/release_verification.json`. Screenshots are actual Edge renders. Mock provider tests verify refusal, fallback and UI wiring; consult `verification/provider_live.json` separately for the bounded live free-provider attempt, if present.

## Controlled observations, not promises

Eight declared campaign cases compute **3 PASS, 4 FAIL and 1 NOT_APPLICABLE**, with **2,408 model states**. A fault can preserve the tracked property, and a low-friction run outside the source scope does not earn a passing verdict.

On twelve self-authored changes, dependency-aware handling produces 2 additional recorded executions versus 7 for exact revision/configuration and 8 for invalidate-all. All three have zero false reuse **in this fixture**; dependency-aware handling withholds 4 cases versus 3 for the baselines. Total evaluations, including initial checks and integrity recomputation, are respectively 28, 38 and 40. These are not general reliability or cost-saving estimates.

## Project map

| File | Purpose |
|---|---|
| `model.py`, `web/simulator.js` | Independent numerical implementations |
| `web/evidence.js` | Source, contract, property, change and import checks |
| `web/experiments.js` | Executed fault campaign |
| `web/main.js`, `web/scene.js` | Workflow, persistence and computed vehicle replay |
| `app.py` | Local execution and optional bounded explanation service |
| `verification/` | Tests, evaluated fixtures, source hashes and real screenshots |
| `docs/BUILD_SPEC.md` | Selected C+A+B scope |

## Hosting and secrets

Static hosting includes no API key and disables the free-provider switch. Local optional explanations use `OPENROUTER_API_KEY` or the existing authorized OS keyring entry; never put a key in `web/`, a saved investigation, the repository or an outreach attachment. Only `openrouter/free` or models ending in `:free` are accepted. Provider availability is external and explanations do not establish correctness.

The owner's private Site preview is separate from this portable source copy; owner-specific hosting identity is deliberately excluded. Create your own hosting identity to publish another copy. Its native source repository is distinct from a GitHub publication. Verify actual access before sending a recruiter any hosted link.

## License

Original project code is MIT licensed; see `LICENSE`. Vendored Three.js r180 and OrbitControls retain their upstream MIT notice in `web/vendor/THREE_LICENSE.txt`. The procedural demo vehicle is authored geometry, not proprietary CAD.
