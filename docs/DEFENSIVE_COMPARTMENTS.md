# Defensive execution with `shield`

**Thirsty-Lang 0.9.1.** The first milestone implements a one-use stdout grant, voluntary surrender and a host stop at the dispatch boundary. The later milestones below extend protection to the worker process and additional effects. The unit of authority is one host-owned run and its descendants.

## Where the language stands

The reference interpreter already mediates sensitive operations through TARL. Importing a module grants no permission to use its sensitive operations. Caller and defining policies both constrain a call. The hardened configuration can verify signed, expiring authority and the host can require durable audit. The interpreter also has cooperative step, time and call-depth limits. [Security model](../SECURITY.md#default-deny) · [Execution limits and their boundaries](EXECUTION_CONTROL.md)

The ordinary governed Node host accepts a host-supplied subject label. The stdout shield uses a separate private channel to the same host-side TARL policy mechanism and requires a verified Ed25519 identity for publication. The Node artifact must match its adjacent source and the host-selected policy before execution. [Earlier Node qualification](operations/LANGUAGE_DEVELOPMENT_QUALIFICATION_20261118.md#governed-node-host-follow-up) · [Language features](FEATURES.md#12-statements)

## The first program

Suppose a status worker can tell another component that a report is ready. Its host permits one public record, exactly the six UTF-8 bytes `ready\n`, on stdout before a deadline. The worker can calculate locally. It cannot select a different recipient, disclose a report field, open a file, or issue another worker a fresh quota.

```thirsty
module report_status: governed
shield {
    pour "ready"
}
```

The first profile accepts a governed module containing exactly one top-level `shield`. Its block supports up to 64 statements: immutable integer locals with bounded addition and subtraction, `pour` of a fixed public string, and standalone `surrender()`. Each UTF-8 record including its newline must fit in 1,024 bytes. Calls, imports, nested blocks, external state and dynamic output are outside this profile. Local computation can finish with an empty grant. Builds that would lose governance reject the shield before emitting output.

### Running the first milestone

```sh
thirsty build report_status.thirsty --target js --policy stdout.tarl
thirsty run report_status.thirsty --policy stdout.tarl --authority-token worker.json --authority-key-file issuer.pub.json
thirsty run-js report_status.js --policy stdout.tarl --authority-token worker.json --authority-key-file issuer.pub.json
```

Use a host-selected policy such as `when authority_authenticated == true and action == "write" and target == "stdout" => ALLOW` followed by `when true => DENY`. The build manifest lists the possible effects and `build.shield.grants`. The issuer must review the source, block location, intended subject and exact output before signing a finite-expiry claim for an allowed scope with `AuthorityIssuer.issue`. Each scope binds the normalized source digest, one-based line and column, and the digest of the exact UTF-8 record. The host supplies the trusted issuer public key independently of the guest.

Each CLI invocation starts a fresh host run. The signed credential establishes eligibility. The supervisor owns the one-use allowance for that run. For concurrent workers, create one `ShieldRun(source, site, verified_authority, binary_sink)` and pass it or a derived handle to each worker. On the reference host attach the TARL runtime, bind the same verified authority, then call `interpreter.interpret_shield(source, handle)`. On Node call `js_host.run_shield(artifact, policy_text, handle)`. A successful first publication produces exact bytes once. A denied publication exits the CLI with status 2. Surrender itself succeeds and subsequent dispatches through the surrendered lineage are denied.

An embedding host can call `stop()` from another thread. Its return acknowledges closure of admission for all handles sharing that run. Inspect `outcome` for `unused`, `in_flight`, `published` or `unknown`. A sink reporting a partial write or failure leaves the allowance spent. A new invocation can use a still-valid credential to open a new run. Durable cross-run replay protection, process-tree termination and an external operator control service belong to later milestones. [Dual-host regression tests](../tests/test_shield_hosts.py) · [Installed CLI verification](../scripts/verify_installed_shield.py)

The issuer can also withdraw its key from the live verifier with `revoke_key(key_id)`. When that call returns, a pending write using the withdrawn key can finish only if the supervisor had already admitted it. Revocation can return while that write is still in the sink. Re-registering a key requires a freshly verified credential for a new shield run.

## Design for later milestones

The following design extends the implemented stdout profile to other workers, effects and recovery paths.

### Authority follows the work

- At compile time, compute the possible effects of supported calls and reject a known operation outside the block's declared upper bound. Dynamic calls in the initial subset require a verified effect bound. At runtime, the existing capability broker still decides each operation against the live policy, caller, defining scope and grant.
- Bind a grant to an authenticated principal, run, operation, destination, expiry and revocation generation. Deriving a child grant can only narrow those fields and its remaining allowance. Aliases, callbacks and child tasks share the parent's remaining budget. An escaped callback retains its restrictions. A peer assistant needs an explicit grant for its own identity. Forwarding a decision receipt confers no permission.
- Keep grant state in a trusted host supervisor shared by every worker in the run. The ordinary Node host starts a fresh helper process for a request. The shield host keeps the grant in the embedding supervisor. A use counter stored there or in guest JavaScript could reset between writes. Route guest output through a private channel to the supervisor. Only the supervisor's adapter can publish externally. Loss of that channel closes access to effects.
- For `pour`, check the destination before evaluating its argument. Bound evaluation and encoding, count UTF-8 bytes including the newline, and check the allowed content, live authority and remaining quota at dispatch. Serialize reservation and release to the adapter with stop and revocation. On a normal run one of two concurrent spends of a one-use grant can succeed. If the adapter may already have emitted bytes when it fails, keep the use spent and record an unknown or partial outcome.

### Protect the data and the host

The first shield permits a fixed public message. General reports need **information-flow labels**. A private value should retain its classification through aliases, containers, `Any`, formatting, errors and branches selected by private data. Check the classification at every supported destination, including `main`, diagnostics and inter-agent messages. A host-authorized release can permit a specific result for a specific recipient. Validating an input's shape leaves its disclosure rules intact. Reject unsupported flows in the protected subset. Timing and other covert channels need a separate threat model.

Bound the work the defender pays for. Enforce a global admission limit before allocating per-principal state, then separate queues and budgets for authenticated principals. Cap input size, queued requests, diagnostic bytes and audit storage. Coalesce repetitive denial telemetry within a fixed window. Effects requiring an individual durable audit record still need that record before dispatch. Reserve capacity for operator commands and other admitted workloads. Repeated denied requests should consume a bounded share of the host and make zero progress toward the protected effect.

Run untrusted workers under OS-enforced process-tree limits for CPU, memory and wall time. Constrain inherited handles, filesystem access and network egress so effects pass through the supervisor. Charge descendants to the same ceiling. Qualify each platform independently before offering this containment profile there. The trusted computing base includes the supervisor, OS isolation, policy and credential verification, and effect adapters.

### How an agent protects itself and a peer

An agent that detects a fault in its own work can surrender a grant over its authenticated control channel. Surrender is always available to the holder, including when ordinary effect admission is saturated. The supervisor revokes that grant and grants derived from it, using the same ordered dispatch boundary and acknowledgement as an operator stop. Previously dispatched work is accounted for. Ancestor grants and independent sibling or peer grants remain usable. The worker cannot reissue what it surrendered.

An agent that observes a possible fault in a peer can use a separately granted reporting channel to one designated supervisor. The host supplies the reporter identity and admits only authorized incident codes and opaque evidence references the recipient may see. Bound message size, rate, queue depth and retention. Treat reporting as disclosure even when a report contains only metadata. A report opens a review. Containing the peer requires an independent operator decision or a host policy that corroborates the report with trusted observations of that peer. A human can inspect the reason for containment and authorize recovery.

### Protecting the code the agents run

A maintenance agent can prepare a patch in a private draft. Updating the protected codebase requires a separate promotion grant held by a reviewer or release operator independent of that worker. Bind approval and test evidence to the exact base revision and candidate bytes. At promotion, recheck both digests and the live grant before changing the protected revision atomically. A stale review or a failed update leaves the last approved revision available. The draft worker has no write authority over the supervisor, its policy or its signing keys.

## Human stop and recovery

1. An authorized operator can stop a specific run over a separate control channel. A host policy may also contain a run on a hard limit or a specified event. An ordinary denial affects the requested operation. Fleet-wide shutdown requires separately authorized scope.
2. The supervisor closes admission and revokes the run and descendant grants before acknowledging **effects stopped**. This acknowledgement means no new dispatch can pass the supervisor boundary. Already dispatched operations can still finish. Kill the worker tree, close its handles and report **workers stopped** only after the host confirms termination. If a worker or adapter cannot be accounted for, surface that uncertainty to the operator.
3. Stopping remains available when the audit store is full or offline. Mark the audit gap. Give the operator a redacted account of the affected run, reason, last dispatch, known outcomes and outstanding uncertainty. Recovery requires an authorized new run with fresh grants. A crash or restart must invalidate old run generations before any publisher comes online. Never automatically repeat an effect whose outcome is unknown.

## Qualification before enabling a profile

Use synthetic data, a controllable clock and an observable local sink. Keep tests of the actual installed runners alongside deterministic tests of the supervisor. These are proposed acceptance criteria.

| Property | Experiment and required observation |
| --- | --- |
| Least privilege works for humans and agents | Run the status program with the intended grant. Observe exactly `ready\n`. Repeat with a different principal, changed artifact, expired grant and ungranted destination. Observe zero bytes and a specific denial. |
| Authority cannot multiply | Give two callbacks in different workers aliases of the same one-use grant. Release them together. Observe one publication, one denial and one debit across the entire parent budget. A sibling with its own grant can still publish. |
| An agent can withdraw and warn safely | Surrender a worker's grant while a child holds a derived grant. Attempts through both fail after acknowledgement. Verify that a sibling still publishes. With a separate reporting grant, deliver one authorized incident to its designated supervisor. Oversized or excess reports are refused. The reported peer keeps its grants until an independently authorized decision contains it. |
| Private data stays with its intended recipient | Run twice with different synthetic private values. Try direct output, a collection, an error and a branch that selects a public-looking message. Compare the bytes and event counts at each public sink across runs. They must be identical. Check separately that a specifically authorized release reaches only its recipient. |
| A worker can propose a fix without installing it | In a disposable source store, have the draft worker request promotion and observe no change. Approve a specific base and draft with a distinct principal. Change one byte in the draft or advance the base and verify refusal. Promote the exact reviewed pair in a fresh fixture and verify the protected revision's digest. |
| Stop wins at a defined point | Hold a request immediately before dispatch, acknowledge stop, then release the hold. Observe zero dispatches. On a fresh run, hold the adapter immediately after dispatch and stop again. Observe one accounted-for in-flight operation. Crash at each boundary and verify recovery produces no duplicate. |
| Denial is affordable | Offer 10,000 small requests from one synthetic tenant to a queue configured for 16. Measure queue high-water mark, retained bytes and audit growth against configured caps. A second tenant completes its status check. Retain stop latency and termination times under the same load. |
| An authorized person can actually intervene | With the worker busy and the archive unavailable, issue stop from outside the worker. Verify revocation, process-tree cleanup, sibling progress and an intelligible audit-gap notice. Set the stop deadline with the operator before the run and publish measured worst-case latency on each supported platform. |

Measure the cost to the defender, the work an untrusted run can complete, and how long an operator needs to contain it. Those measurements support a claim about the system even when an abusive caller keeps trying indefinitely.

## Delivery order

1. **Included in 0.9.1.** The reference and Node hosts support the one-use stdout shield, fixed public literals, authenticated host grants, a shared budget, effect bounds, voluntary surrender and stop at dispatch. The first profile admits no file, network or process operations.
2. Qualify independent operator stop, restart invalidation, required audit under failure and OS worker isolation on Windows and Linux. Test two tenants under pressure and publish per-platform evidence.
3. Add labeled inputs and recipient-specific release, then the bounded peer-report channel and one read-only file adapter for the existing data-report workload. Use policy comparison to produce a runnable witness if changing a rule widens who can receive data. Each added adapter needs its own bounds, cancellation behavior and outcome tests.
4. Qualify draft and promotion grants against a disposable source store before allowing a maintenance agent to propose changes to a protected codebase.
