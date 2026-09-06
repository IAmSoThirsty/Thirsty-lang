"""Credential lifetime and issuer revocation must reach already-bound effects."""

import datetime as dt

import pytest

from utf.tarl.authority import (
    AuthorityClaim,
    AuthorityIssuer,
    AuthorityVerifier,
    VerifiedAuthority,
)
from utf.tarl.broker import CapabilityBroker
from utf.tarl.core import PolicyParser
from utf.tarl.runtime import TarlRuntime

NOW = dt.datetime(2026, 9, 6, tzinfo=dt.UTC)


def credential():
    issuer = AuthorityIssuer("issuer", bytes(range(32)))
    verifier = AuthorityVerifier().add_ed25519_key("issuer", issuer.public_key_bytes())
    claim = issuer.issue("operator", ["write"], ttl_seconds=60, now=NOW)
    result = verifier.verify(claim, now=NOW)
    assert result.valid and result.authority is not None
    return issuer, verifier, claim, result.authority


def test_bound_broker_expires_at_exclusive_deadline():
    _, _, _, authority = credential()
    current = NOW
    runtime = TarlRuntime(PolicyParser.parse("when true => ALLOW\n"))
    runtime.set_clock(lambda: current)
    broker = CapabilityBroker(runtime, authority, require_authenticated=True)
    assert broker.request("write", "stdout").allowed
    current += dt.timedelta(seconds=60)
    denied = broker.request("write", "stdout")
    assert not denied.allowed
    assert "expired" in denied.reason


@pytest.mark.parametrize("operation", ["revoke", "replace"])
def test_bound_authority_observes_issuer_trust_changes(operation):
    _, verifier, _, authority = credential()
    assert authority.authorization_error(NOW) is None
    if operation == "revoke":
        verifier.revoke_key("issuer")
    else:
        replacement = AuthorityIssuer("issuer", bytes(reversed(range(32))))
        verifier.add_ed25519_key("issuer", replacement.public_key_bytes())
    assert authority.authorization_error(NOW) is not None


def test_mutating_original_claim_cannot_extend_bound_authority():
    _, _, claim, authority = credential()
    claim.expires_at = (NOW + dt.timedelta(days=99)).isoformat()
    claim.grants = ("admin",)
    assert authority.grants == ("write",)
    assert "expired" in authority.authorization_error(NOW + dt.timedelta(seconds=60))


def test_verification_binds_only_the_detached_signed_snapshot(monkeypatch):
    issuer = AuthorityIssuer("issuer", bytes(32))
    verifier = AuthorityVerifier().add_ed25519_key("issuer", issuer.public_key_bytes())
    claim = issuer.issue("operator", ["write"], ttl_seconds=60, now=NOW)
    copy_claim = AuthorityClaim.from_dict

    def mutate_after_copy(raw):
        detached = copy_claim(raw)
        claim.subject = "admin"
        claim.grants = ("admin",)
        return detached

    monkeypatch.setattr(AuthorityClaim, "from_dict", mutate_after_copy)
    result = verifier.verify(claim, now=NOW)
    assert result.valid
    assert result.authority.subject == "operator"
    assert result.authority.grants == ("write",)
    assert result.authority.authorization_error(NOW) is None


def test_future_issue_time_and_naive_verification_time_are_rejected():
    _, verifier, claim, _ = credential()
    assert "not yet" in verifier.verify(claim, NOW - dt.timedelta(seconds=1)).reason
    assert "timezone" in verifier.verify(claim, NOW.replace(tzinfo=None)).reason


@pytest.mark.parametrize("ttl", [0, -1, True, 1.5])
def test_issuer_rejects_invalid_lifetimes(ttl):
    with pytest.raises(ValueError, match="positive integer"):
        AuthorityIssuer("issuer", bytes(32)).issue("operator", ttl_seconds=ttl)


@pytest.mark.parametrize(
    "field,value",
    [
        ("grants", "admin"),
        ("grants", ["write", "write"]),
        ("grants", [1]),
        ("grants", [""]),
        ("subject", 123),
        ("key_id", ""),
        ("expires_at", 123),
        ("extra", "hidden"),
    ],
)
def test_claim_schema_rejects_ambiguous_values(field, value):
    _, _, claim, _ = credential()
    raw = claim.to_dict()
    raw[field] = value
    with pytest.raises(ValueError):
        AuthorityClaim.from_dict(raw)


def test_duplicate_json_fields_are_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        AuthorityClaim.from_json('{"subject":"a","subject":"b"}')


@pytest.mark.parametrize("window", ["bad", "2026-09-06T00:00:00", NOW.isoformat()])
def test_signed_malformed_expiry_is_rejected(window):
    issuer, verifier, claim, _ = credential()
    claim.expires_at = window
    claim.signature = "ed25519:" + issuer._key.sign(claim.signing_bytes()).hex()
    assert not verifier.verify(claim, NOW).valid


def test_invalid_configured_clock_does_not_fall_back_to_host():
    _, _, _, authority = credential()
    runtime = TarlRuntime(PolicyParser.parse("when true => ALLOW\n"))
    runtime.set_clock(lambda: None)
    assert not CapabilityBroker(runtime, authority).request("write").allowed


def test_direct_embedding_authority_checks_and_validator_failure():
    assert VerifiedAuthority("trusted").authorization_error(None) is None
    assert VerifiedAuthority.unauthenticated("claim").authorization_error(NOW)
    assert VerifiedAuthority("trusted").authorization_error(NOW.replace(tzinfo=None))

    def broken(_now):
        raise RuntimeError("trust service unavailable")

    assert "revalidation failed" in VerifiedAuthority(
        "trusted", _revalidate=broken
    ).authorization_error(NOW)


def test_issue_rejects_naive_time_and_string_grants():
    issuer = AuthorityIssuer("issuer", bytes(32))
    with pytest.raises(ValueError):
        issuer.issue("operator", now=NOW.replace(tzinfo=None))
    with pytest.raises(ValueError):
        issuer.issue("operator", grants="write")
