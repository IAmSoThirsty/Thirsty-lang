"""Policy-lint (C039) and ESCALATE-quorum (C050) tests."""

import datetime

from utf.tarl.core import PolicyParser
from utf.tarl.escalation import ApprovalIssuer, QuorumResolver
from utf.tarl.linter import lint_passes, lint_policy
from utf.tarl.runtime import TarlRuntime
from utf.tarl.schema import ContextSchema, FieldSpec
from utf.tarl.spec import TarlDecision, TarlVerdict
from utf.tarl.verifier import ProofVerifier, ReplayGuard

# ── C039: broad-ALLOW policy linting ───────────────────────────────────────────


def test_unconditional_allow_is_flagged_high():
    policy = PolicyParser.parse("policy p\nwhen true => ALLOW\n")
    findings = lint_policy(policy)
    codes = {f.code: f for f in findings}
    assert "TARL-LINT-BROAD-ALLOW" in codes
    assert codes["TARL-LINT-BROAD-ALLOW"].severity == "high"
    assert not lint_passes(policy)


def test_ungated_allow_is_flagged_medium():
    policy = PolicyParser.parse(
        'policy p\nwhen action == "read" => ALLOW\nwhen true => DENY\n'
    )
    codes = {f.code for f in lint_policy(policy)}
    assert "TARL-LINT-UNGATED-ALLOW" in codes


def test_authority_gated_allow_is_clean():
    policy = PolicyParser.parse(
        "policy p\n"
        'when role == "admin" => ALLOW\n'
        "when authority_authenticated == true => ALLOW\n"
        "when true => DENY\n"
    )
    findings = lint_policy(policy)
    assert all(f.code != "TARL-LINT-UNGATED-ALLOW" for f in findings)
    assert all(f.code != "TARL-LINT-BROAD-ALLOW" for f in findings)


def test_missing_default_deny_is_flagged_low():
    policy = PolicyParser.parse('policy p\nwhen role == "admin" => ALLOW\n')
    codes = {f.code for f in lint_policy(policy)}
    assert "TARL-LINT-NO-DEFAULT-DENY" in codes


def test_lint_passes_threshold():
    clean = PolicyParser.parse(
        'policy p\nwhen role == "admin" => ALLOW\nwhen true => DENY\n'
    )
    assert lint_passes(clean)
    assert lint_passes(clean, max_severity="high")


# ── C050: ESCALATE resolves only via signed quorum ─────────────────────────────

ESCALATE_POLICY = (
    "policy p\n" 'when action == "wire_transfer" => ESCALATE\n' "when true => DENY\n"
)
PROOF_KEY_ID = "runtime-proof"
PROOF_SECRET = b"runtime-proof-secret"
ESCALATE_CONTEXT = {"action": "wire_transfer"}
QUORUM_NOW = datetime.datetime(2026, 8, 2, 12, tzinfo=datetime.UTC)


def _escalated(
    policy_source=ESCALATE_POLICY,
    *,
    configure_schema=True,
    sign=True,
    now=QUORUM_NOW,
):
    rt = TarlRuntime(PolicyParser.parse(policy_source))
    rt.set_clock(lambda: now)
    if configure_schema:
        assert rt.ensure_context_schema() is True
    if sign:
        rt.set_signing_key(PROOF_KEY_ID, PROOF_SECRET)
    return rt.evaluate_with_proof(ESCALATE_CONTEXT)


def _resolver(
    threshold,
    issuers,
    policy_source=ESCALATE_POLICY,
    now=QUORUM_NOW,
):
    verifier = ProofVerifier(
        require_policy_source=True,
        max_age_seconds=300,
        replay_guard=ReplayGuard(),
    ).add_hmac_key(
        PROOF_KEY_ID,
        PROOF_SECRET,
    )
    r = QuorumResolver(
        threshold,
        proof_verifier=verifier,
        policy_source=policy_source,
        clock=lambda: now,
    )
    for iss in issuers:
        r.add_approver_key(iss.key_id, iss.public_key_bytes())
    return r


def _resolve(resolver, decision, proof, approvals):
    return resolver.resolve(
        decision,
        proof,
        approvals,
        expected_context=ESCALATE_CONTEXT,
    )


def test_escalate_with_quorum_becomes_allow():
    decision, proof = _escalated()
    assert decision.verdict == TarlVerdict.ESCALATE
    alice = ApprovalIssuer("alice", "ka", bytes(range(32)))
    bob = ApprovalIssuer("bob", "kb", bytes([1] * 32))
    resolver = _resolver(2, [alice, bob])
    result = _resolve(
        resolver, decision, proof, [alice.approve(proof), bob.approve(proof)]
    )
    assert result.decision.verdict == TarlVerdict.ALLOW
    assert result.approvals_counted == 2


def test_quorum_cannot_promote_after_governing_policy_cutoff():
    policy = (
        "policy p\n"
        "  valid_until: 2026-08-02T12:01:00Z\n"
        'when action == "wire_transfer" => ESCALATE for: 5m\n'
        "when true => DENY\n"
    )
    decision, proof = _escalated(policy)
    assert proof.expires_at == "2026-08-02T12:01:00+00:00"

    alice = ApprovalIssuer("alice", "ka", bytes(range(32)))
    after_cutoff = QUORUM_NOW + datetime.timedelta(minutes=2)
    resolver = _resolver(1, [alice], policy_source=policy, now=after_cutoff)
    result = _resolve(resolver, decision, proof, [alice.approve(proof)])

    assert result.decision.verdict == TarlVerdict.ESCALATE
    assert result.approvals_counted == 0
    assert "expired" in result.reason or "not effective" in result.reason


def test_below_threshold_stays_escalate():
    decision, proof = _escalated()
    alice = ApprovalIssuer("alice", "ka", bytes(range(32)))
    resolver = _resolver(2, [alice])
    result = _resolve(resolver, decision, proof, [alice.approve(proof)])
    assert result.decision.verdict == TarlVerdict.ESCALATE
    assert result.approvals_counted == 1


def test_one_approver_cannot_satisfy_quorum_with_duplicates():
    decision, proof = _escalated()
    alice = ApprovalIssuer("alice", "ka", bytes(range(32)))
    resolver = _resolver(2, [alice])
    # Two approvals from the SAME approver count once.
    result = _resolve(
        resolver, decision, proof, [alice.approve(proof), alice.approve(proof)]
    )
    assert result.decision.verdict == TarlVerdict.ESCALATE
    assert result.approvals_counted == 1


def test_approval_for_a_different_decision_is_not_counted():
    decision, proof = _escalated()
    other_policy = ESCALATE_POLICY.replace("policy p", "policy other")
    _other_decision, other_proof = _escalated(other_policy)
    alice = ApprovalIssuer("alice", "ka", bytes(range(32)))
    bob = ApprovalIssuer("bob", "kb", bytes([1] * 32))
    resolver = _resolver(2, [alice, bob])
    # The context is identical, but Bob approved a different policy proof.
    bad = bob.approve(other_proof)
    result = _resolve(resolver, decision, proof, [alice.approve(proof), bad])
    assert result.decision.verdict == TarlVerdict.ESCALATE
    assert result.approvals_counted == 1


def test_partial_approval_does_not_consume_proof_before_quorum():
    decision, proof = _escalated()
    alice = ApprovalIssuer("alice", "ka", bytes(range(32)))
    bob = ApprovalIssuer("bob", "kb", bytes([1] * 32))
    resolver = _resolver(2, [alice, bob])

    partial = _resolve(resolver, decision, proof, [alice.approve(proof)])
    complete = _resolve(
        resolver,
        decision,
        proof,
        [alice.approve(proof), bob.approve(proof)],
    )

    assert partial.decision.verdict == TarlVerdict.ESCALATE
    assert partial.approvals_counted == 1
    assert complete.decision.verdict == TarlVerdict.ALLOW
    assert complete.approvals_counted == 2


def test_identity_proof_requires_exact_original_request_context():
    decision, proof = _escalated()
    alice = ApprovalIssuer("alice", "ka", bytes(range(32)))
    resolver = _resolver(1, [alice])
    approval = alice.approve(proof)

    missing = resolver.resolve(decision, proof, [approval])
    mismatched = resolver.resolve(
        decision,
        proof,
        [approval],
        expected_context={"action": "read"},
    )

    assert missing.decision.verdict == TarlVerdict.ESCALATE
    assert "original request context is required" in missing.reason
    assert mismatched.decision.verdict == TarlVerdict.ESCALATE
    assert "context hash MISMATCH" in mismatched.reason


def test_unknown_approver_key_is_not_counted():
    decision, proof = _escalated()
    alice = ApprovalIssuer("alice", "ka", bytes(range(32)))
    rogue = ApprovalIssuer("mallory", "km", bytes([9] * 32))
    resolver = _resolver(2, [alice])  # rogue's key not registered
    result = _resolve(
        resolver, decision, proof, [alice.approve(proof), rogue.approve(proof)]
    )
    assert result.decision.verdict == TarlVerdict.ESCALATE
    assert result.approvals_counted == 1


def test_missing_proof_verifier_configuration_never_promotes():
    decision, proof = _escalated()
    alice = ApprovalIssuer("alice", "ka", bytes(range(32)))
    resolver = QuorumResolver(1).add_approver_key(
        alice.key_id,
        alice.public_key_bytes(),
    )
    result = _resolve(resolver, decision, proof, [alice.approve(proof)])
    assert result.decision.verdict == TarlVerdict.ESCALATE
    assert result.approvals_counted == 0
    assert "proof verifier and policy source are required" in result.reason


def test_quorum_requires_freshness_replay_and_trusted_time_gates():
    decision, proof = _escalated()
    alice = ApprovalIssuer("alice", "ka", bytes(range(32)))
    approval = alice.approve(proof)
    cases = [
        (
            ProofVerifier(
                require_policy_source=True,
                replay_guard=ReplayGuard(),
            ),
            lambda: QUORUM_NOW,
            "freshness and replay enforcement are required",
        ),
        (
            ProofVerifier(
                require_policy_source=True,
                max_age_seconds=300,
            ),
            lambda: QUORUM_NOW,
            "freshness and replay enforcement are required",
        ),
        (
            ProofVerifier(
                require_policy_source=True,
                max_age_seconds=300,
                replay_guard=ReplayGuard(),
            ),
            None,
            "trusted verification time is required",
        ),
        (
            ProofVerifier(
                require_policy_source=True,
                max_age_seconds=300,
                replay_guard=ReplayGuard(),
            ),
            lambda: datetime.datetime(2026, 8, 2, 12),
            "timezone-aware",
        ),
    ]

    for verifier, clock, expected_reason in cases:
        verifier.add_hmac_key(PROOF_KEY_ID, PROOF_SECRET)
        resolver = QuorumResolver(
            1,
            proof_verifier=verifier,
            policy_source=ESCALATE_POLICY,
            clock=clock,
        ).add_approver_key(alice.key_id, alice.public_key_bytes())
        result = _resolve(resolver, decision, proof, [approval])

        assert result.decision.verdict == TarlVerdict.ESCALATE
        assert expected_reason in result.reason


def test_fabricated_escalate_decision_cannot_promote_a_deny_proof():
    deny_policy = "policy deny\n" 'when action == "wire_transfer" => DENY\n'
    _deny_decision, proof = _escalated(deny_policy)
    fabricated = TarlDecision(
        verdict=TarlVerdict.ESCALATE,
        reason="fabricated",
        rule_index=proof.rule_index,
    )
    alice = ApprovalIssuer("alice", "ka", bytes(range(32)))
    resolver = _resolver(1, [alice], policy_source=deny_policy)
    result = _resolve(resolver, fabricated, proof, [alice.approve(proof)])
    assert result.decision.verdict == TarlVerdict.ESCALATE
    assert result.approvals_counted == 0
    assert "proof verdict does not authorize escalation" in result.reason


def test_schema_unbound_escalation_proof_cannot_be_promoted():
    decision, proof = _escalated(configure_schema=False)
    assert proof.context_schema_validation_status == "not_configured"
    alice = ApprovalIssuer("alice", "ka", bytes(range(32)))
    resolver = _resolver(1, [alice])
    result = _resolve(resolver, decision, proof, [alice.approve(proof)])
    assert result.decision.verdict == TarlVerdict.ESCALATE
    assert result.approvals_counted == 0
    assert "passed authoritative context schema" in result.reason


def test_unsigned_or_tampered_escalation_proof_cannot_be_promoted():
    alice = ApprovalIssuer("alice", "ka", bytes(range(32)))
    resolver = _resolver(1, [alice])

    unsigned_decision, unsigned_proof = _escalated(sign=False)
    unsigned_result = _resolve(
        resolver,
        unsigned_decision,
        unsigned_proof,
        [alice.approve(unsigned_proof)],
    )
    assert unsigned_result.decision.verdict == TarlVerdict.ESCALATE
    assert unsigned_result.approvals_counted == 0

    decision, proof = _escalated()
    approval = alice.approve(proof)
    proof.matched_condition = "true"
    tampered_result = _resolve(resolver, decision, proof, [approval])
    assert tampered_result.decision.verdict == TarlVerdict.ESCALATE
    assert tampered_result.approvals_counted == 0


def test_lenient_verifier_cannot_make_unsigned_escalation_authoritative():
    decision, proof = _escalated(sign=False)
    alice = ApprovalIssuer("alice", "ka", bytes(range(32)))
    resolver = QuorumResolver(
        1,
        proof_verifier=ProofVerifier(
            require_signature=False,
            require_policy_source=True,
            max_age_seconds=300,
            replay_guard=ReplayGuard(),
        ),
        policy_source=ESCALATE_POLICY,
        clock=lambda: QUORUM_NOW,
    ).add_approver_key(alice.key_id, alice.public_key_bytes())
    result = _resolve(resolver, decision, proof, [alice.approve(proof)])
    assert result.decision.verdict == TarlVerdict.ESCALATE
    assert result.approvals_counted == 0
    assert "signature skipped" in result.reason


def test_decision_rule_mismatch_cannot_be_promoted():
    decision, proof = _escalated()
    mismatched = TarlDecision(
        verdict=TarlVerdict.ESCALATE,
        reason=decision.reason,
        rule_index=decision.rule_index + 1,
    )
    alice = ApprovalIssuer("alice", "ka", bytes(range(32)))
    result = _resolve(
        _resolver(1, [alice]),
        mismatched,
        proof,
        [alice.approve(proof)],
    )
    assert result.decision.verdict == TarlVerdict.ESCALATE
    assert result.approvals_counted == 0
    assert "rule indices do not match" in result.reason


def test_source_injected_escalation_requires_both_bound_contexts():
    policy_source = (
        "policy source_escalation\n"
        "when action IN source:risky_actions => ESCALATE\n"
        "when true => DENY\n"
    )
    runtime = TarlRuntime(PolicyParser.parse(policy_source)).set_context_schema(
        ContextSchema(
            fields=[
                FieldSpec("action", kinds=("string",)),
                FieldSpec("source:risky_actions", kinds=("list",)),
            ]
        )
    )
    runtime.register_source("risky_actions", ["wire_transfer"])
    runtime.set_clock(lambda: QUORUM_NOW)
    runtime.set_signing_key(PROOF_KEY_ID, PROOF_SECRET)
    original = {"action": "wire_transfer"}
    evaluated = {
        "action": "wire_transfer",
        "source:risky_actions": ["wire_transfer"],
    }
    decision, proof = runtime.evaluate_with_proof(original)
    alice = ApprovalIssuer("alice", "ka", bytes(range(32)))
    resolver = _resolver(1, [alice], policy_source=policy_source)
    approval = alice.approve(proof)

    missing_contexts = resolver.resolve(decision, proof, [approval])
    accepted = resolver.resolve(
        decision,
        proof,
        [approval],
        expected_context=original,
        expected_evaluated_context=evaluated,
    )

    assert missing_contexts.decision.verdict == TarlVerdict.ESCALATE
    assert "requires original and evaluated contexts" in missing_contexts.reason
    assert accepted.decision.verdict == TarlVerdict.ALLOW


def test_time_bound_escalation_preserves_and_validates_expiry():
    policy_source = (
        "policy timed\n"
        'when action == "wire_transfer" => ESCALATE for: 5m\n'
        "when true => DENY\n"
    )
    decision, proof = _escalated(policy_source)
    alice = ApprovalIssuer("alice", "ka", bytes(range(32)))
    resolver = _resolver(1, [alice], policy_source=policy_source)
    approval = alice.approve(proof)

    accepted = _resolve(resolver, decision, proof, [approval])
    assert accepted.decision.verdict == TarlVerdict.ALLOW
    assert accepted.decision.expires_at == decision.expires_at

    tampered = TarlDecision(
        verdict=decision.verdict,
        reason=decision.reason,
        rule_index=decision.rule_index,
        matched_rule=decision.matched_rule,
        expires_at="2099-01-01T00:00:00+00:00",
    )
    rejected = _resolve(resolver, tampered, proof, [approval])
    assert rejected.decision.verdict == TarlVerdict.ESCALATE
    assert "expiry does not match proof" in rejected.reason


def test_time_bound_escalation_requires_unexpired_trusted_time():
    policy_source = (
        "policy timed\n"
        'when action == "wire_transfer" => ESCALATE for: 5m\n'
        "when true => DENY\n"
    )
    decision, proof = _escalated(policy_source)
    alice = ApprovalIssuer("alice", "ka", bytes(range(32)))
    resolver = _resolver(1, [alice], policy_source=policy_source)
    resolver.set_clock(lambda: QUORUM_NOW + datetime.timedelta(minutes=6))

    result = _resolve(resolver, decision, proof, [alice.approve(proof)])

    assert result.decision.verdict == TarlVerdict.ESCALATE
    assert "expired" in result.reason


def test_time_bound_escalation_rejects_stripped_proof_expiry():
    policy_source = (
        "policy timed\n"
        'when action == "wire_transfer" => ESCALATE for: 5m\n'
        "when true => DENY\n"
    )
    decision, proof = _escalated(policy_source)
    proof.expires_at = None
    alice = ApprovalIssuer("alice", "ka", bytes(range(32)))
    resolver = _resolver(1, [alice], policy_source=policy_source)

    result = _resolve(resolver, decision, proof, [alice.approve(proof)])

    assert result.decision.verdict == TarlVerdict.ESCALATE
    assert "expiry does not match proof" in result.reason
