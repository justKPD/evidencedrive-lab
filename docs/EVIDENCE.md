# EvidenceDrive — knowledge, contracts and change impact

`web/evidence.js` implements the C+A workflow. It uses reviewed, **independently authored demonstration clauses**, a typed contract, a recorded numerical trace and a dependency graph. None of its sources is a Bosch requirement or evidence of a private team deficiency. The precise Python-test artifact for REF299133V remains unconfirmed.

## What is actually implemented

1. Retrieve candidate clauses with exact source spans, explicit approval and operating-context checks. This is bounded lexical matching with a small engineering vocabulary, not universal semantic RAG.
2. Propose a contract using the source clause's structured metric, limit, unit, settling grace, operating conditions and influential dependencies. Missing fields remain missing. Free prose alone cannot invent a numerical acceptance threshold.
3. Require explicit contract review. Source text cannot approve itself, change an execution tool or run arbitrary code.
4. Evaluate actual numerical observations against the reviewed criterion. Recompute the numerical trace using the browser model before accepting it, including traces returned by the independent Python service. Required model/trace identities, sampled states, summary and event ledger must agree. The property checker is separate from the simulator, but this deterministic recomputation does not independently validate physical brake behavior.
5. Retain source, clause, contract, configuration and simulation snapshots with the result. PASS and FAIL are computed outcomes; NOT_APPLICABLE and UNQUALIFIED are visible alternatives.
6. Append source revisions and derive property-specific change impact. A prior result is not rewritten to make a revised threshold pass. Graph edges connect the exact source version to the reviewed contract and result.
7. Validate bounded workspace exports/imports and recompute imported property outcomes. A content checksum detects accidental inconsistency, **not authenticity or a trusted reviewer's identity**. A person controlling every imported input can declare their own criterion; the application does not assert it is a genuine external requirement.

The UI may explore an unreviewed model independently. That is distinct from a reviewed test result. A CURRENT failure stays a failure; CURRENT is an applicability state, not a verdict.

## Initial source corpus

| Source ID | Clause ID | Criterion |
|---|---|---|
| `source-response-r1` | `tracking` | Maximum absolute requested-versus-modeled braking-effort error; 0.8 m/s² after 0.7 s settling; speed above 1 m/s |
| `source-release-r1` | `release` | Maximum remaining normalized pressure in either actuator; 0.05 after 0.8 s release grace |
| `source-recovery-r1` | `recovery` | First sustained system-level tracking recovery following a fault end; 0.9 s bound, 0.8 m/s² tracking tolerance, 0.15 s sustained window |
| `source-incomplete-r1` | `unresolved` | Deliberately incomplete, unreviewed note; no threshold or grace is invented |

These values are chosen example acceptance contracts for a declared model. They are not safety limits, product requirements or tuned Bosch thresholds. The default response/recovery sources require variant `demo-v1`, controller `arbitration-1` and friction coefficient at least 0.85. They intentionally do not require independent topology: a shared-supply loss can therefore generate a legitimate computed failure under the same response criterion.

Structured source fields are the authority inside this demonstration; cited prose supplies an exact contextual passage. This is a contract workflow over an explicit schema, not an assertion that arbitrary natural-language requirements have been formally understood.

## API shapes

All operations are synchronous. Workspace collections are mutated by adding new records; numerical/source/contract/result snapshots in past runs are preserved. `reviewContract` appends a local review decision and updates the current contract's review state, without changing its cited criterion or input.

| Function | Return / behavior |
|---|---|
| `defaultSources()` | Four sealed authored source examples |
| `createWorkspace()` | `{schema_version,sequence,sources,contracts,runs,changes}` with source examples |
| `addSource(ws,payload)` | Adds a genuinely new source/family. `{title,text,clauses?,reviewed?,id?,family?,revision?}`; review defaults false. Missing clauses become an explicitly incomplete prose note |
| `searchSources(ws,query,config)` | `{matches,excluded,abstained,reason}`; matches contain `source_id`, `clause_id`, `source`, `clause`, `excerpt`, offsets, citation ID and score |
| `proposeContract(ws,sourceId,clauseId,config)` | Appends a direct contract with status PROPOSED, INCOMPLETE or INCOMPATIBLE, `missing`, `reasons` and exact snapshots |
| `reviewContract(ws,contractId,approved)` | Explicit true/false decision; incomplete/incompatible/superseded contracts cannot be approved |
| `runContract(ws,contractId,simulation)` | Direct run record with verdict, findings, first failure, checked count, maximum observation, limit/unit and input/source/contract snapshots |
| `reviseSource(ws,sourceId,patch)` | `{source,change,affected_contracts,affected_runs}`; adds a unique revision. Review defaults to false unless explicitly supplied |
| `assessEvidence(ws,runId,config)` | `{status,reasons,run_id,source_id,current_source_id,recorded_verdict}` |
| `impact(ws)` | Source/contract/run nodes, current assessments, changes and exact support/evaluation/supersession edges |
| `exportWorkspace(ws)` / `importWorkspace(data)` | Plain JSON export/import with an integrity checksum and schema, graph, criteria, numerical and result checks |
| `evaluateChangePolicies()` | Actual controlled comparison on twelve declared source/context changes; ephemeral workspaces, no model/API call fees |

`contentHash(value)` is a synchronous 16-hex content checksum and is exported for consistency tests. It is not a cryptographic signature or authenticated audit log.

### Source revision patch

Allowed fields: `{revision,title,text,reviewed,clauses}`. Family and identity cannot be silently reassigned. Clause text must remain an exact span of the source body. `revision` must be new within the family. Original records remain in the source list; lookup uses the newest family version. An unreviewed latest version cannot silently fall back to an approved but superseded source.

Clauses allow only the documented metrics, compatible units, finite nonnegative limits, explicit conditions and model dependencies. Missing values can be stored as incomplete notes. Unknown fields and invalid supplied values are rejected. Recovery clauses additionally need `recovery_tolerance_mps2` and `recovery_window_s`; they cannot borrow an implicit response criterion.

## Property checker semantics

**Tracking error:** evaluate each trace sample after the most recent demand-value transition has exceeded the source's settling grace. Only samples with positive demand and speed above 1 m/s qualify. The observed value is `abs(requested_decel_mps2 - brake_decel_mps2)`. A fault does not reset the settling grace, which would hide a failure. Every eligible sample is checked, not just visual frames.

**Release pressure:** with zero demand after the declared grace, evaluate `max(pressure_a,pressure_b)`. A stuck high request can fail this property even if the vehicle slows as expected. The diagram finding identifies the observed actuator, not a certified root cause.

**Recovery time:** for each distinct declared fault end, seek the first sequence maintaining positive demand, speed above 1 m/s and tracking error within the declared tolerance for the declared sustained window. This measures system-level tracking, not restoration of every channel. An independent-channel fault may therefore have zero response-recovery delay if the other channel already preserves the property. No post-fault request means NOT_APPLICABLE. A horizon too short to assess the deadline is UNQUALIFIED. A sufficiently observed failure to recover is FAIL, with a visible censored observation rather than an invented finite recovery time.

The checker reports finding time, observed value, limit, observed part, pass/fail and reason. `max_observed` excludes null/censored values; inspect each finding's `censored` flag and verdict rather than interpreting a missing recovery value as zero. Findings are bounded by the numerical trace length.

## Applicability and selective invalidation

| Status | Meaning |
|---|---|
| CURRENT | Same explicit criterion and relevant model/context inputs. Original verdict, including FAIL, is retained |
| REVIEW_CITATION | Explicit structured criterion and relevant inputs are unchanged, but the source version/title identity changed; provenance needs review |
| RETEST_REQUIRED | Acceptance criterion, declared applicability/dependencies or an influential model input changed; require a fresh reviewed evaluation |
| INCOMPATIBLE | Current source scope does not cover the requested context |
| UNKNOWN | Latest source is unreviewed/quarantined, a clause disappeared, a criterion is incomplete or free prose changed without established equivalence |

Semantic equivalence is deliberately narrow: explicit structured fields, sorted dependency sets, and supported canonical units (`m/s²`/`m/s^2`/`m/s2`; seconds/milliseconds for time). Rewriting arbitrary prose is not called editorial merely because its numbers look similar.

Every metric enforces the minimum influential dependency set. A source cannot omit `faults`, demand, timing or actuator dynamics to keep evidence CURRENT after those inputs change. Tracking also depends on speed eligibility, friction and maximum deceleration. Mass is intentionally irrelevant to the modeled tracking-effort metric; changing it changes force output but not that property. Retaining CURRENT for tracking is **not** permission to reuse every numerical output or another property.

## Controlled evaluation and limitations

`verification/change_policy_fixture.json` contains twelve self-authored changes: unchanged control, unrelated source, title/revision changes, canonical unit spelling, tightened criterion, slower dynamics, irrelevant mass, low friction, variant mismatch, unreviewed update and changed free prose. Labels are used only to score outcomes; `assessEvidence` and policy decisions receive actual source/configuration records, not expected labels.

The comparison creates real baseline traces, then executes permitted reruns for conservative invalidate-everything, exact-revision-and-config and dependency-aware policies. The current run records:

| Policy | False reuse | Additional recorded executions | Unnecessary additional executions | Initial executions | Integrity recomputations | Total model evaluations | Withheld |
|---|---:|---:|---:|---:|---:|---:|---:|
| Invalidate everything after a change | 0 | 8 | 6 | 12 | 20 | 40 | 3 |
| Exact revision and complete config | 0 | 7 | 5 | 12 | 19 | 38 | 3 |
| Dependency-aware | 0 | 2 | 0 | 12 | 14 | 28 | 4 |

All policies withhold or re-evaluate the risky cases in this fixture. The benefit shown is avoiding certain unnecessary reruns, not proof of superior safety, general retrieval accuracy or factory-time savings. The dependency-aware policy withholds four cases versus three for the baselines: fewer executions are not automatically more useful answers. Extra fixture-generation work comprises 36 baseline simulations. Each accepted run is also numerically recomputed for integrity; these recomputations and initial runs are excluded from the legacy `actual_numerical_runs` counter, which means **additional recorded workflow executions only**. The result includes explicit counter definitions and totals; do not interpret 2 versus 7/8 as all computation or cost saved. Recommendations blocked by incomplete/incompatible sources are counted as withheld, not as completed numerical runs. Clean controls where all policies make the same decision remain in the report.

The 20 Node contracts currently cover new authored sources, unstructured notes, review gates, missing fields, scope mismatch, actual independent/shared-fault outcomes, release, recovery/censoring, immutable histories, dependency changes, exact citations, malformed inputs, numeric recomputation and forged imports. A pass count does not establish physical correctness or comprehensive AI understanding.

## Reproduce

From the project directory:

```powershell
& 'C:\Program Files\nodejs\node.exe' '.\tests_evidence.mjs'
```

Outputs: `verification/evidence_tests.json`, `change_policy_fixture.json`, `change_policy_evaluation.json`. Evaluation uses temporary in-memory workspaces, not the user's current browser investigation. No provider, network, paid API, physical hardware or proprietary source is involved.
