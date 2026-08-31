"""Trusted-clock / time-spoofing tests (THREAT_MODEL C043).

Temporal policy windows must be decided against a verified signed time, so a
spoofed host clock cannot satisfy (or dodge) a window.
"""

import datetime

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from utf.tarl.clock import SignedTime, TimeAuthority, TrustedClock
from utf.tarl.core import PolicyParser
from utf.tarl.runtime import TarlRuntime
from utf.tarl.spec import TarlVerdict

SEED = bytes(range(32))
WRONG_SEED = bytes([7] * 32)


def _authority():
    return TimeAuthority("time-1", SEED)


def _clock(authority=None):
    authority = authority or _authority()
    return TrustedClock().add_ed25519_key(
        authority.key_id, authority.public_key_bytes()
    )


# ── TrustedClock verification ──────────────────────────────────────────────────


def test_valid_signed_time_verifies():
    auth = _authority()
    now = datetime.datetime(2026, 6, 1, 12, 0, tzinfo=datetime.UTC)
    dt = _clock(auth).verify(auth.stamp(now))
    assert dt == now


def test_unsigned_time_is_rejected():
    assert _clock().verify(SignedTime(timestamp="2026-06-01T00:00:00+00:00")) is None


def test_wrong_key_is_rejected():
    real = _authority()
    forger = TimeAuthority("time-1", WRONG_SEED)
    clock = TrustedClock().add_ed25519_key("time-1", real.public_key_bytes())
    assert clock.verify(forger.stamp()) is None


def test_tampered_timestamp_is_rejected():
    auth = _authority()
    signed = auth.stamp()
    signed.timestamp = "2099-01-01T00:00:00+00:00"  # move time after signing
    assert _clock(auth).verify(signed) is None


def test_out_of_skew_signed_time_is_rejected():
    auth = _authority()
    clock = TrustedClock(max_skew_seconds=60).add_ed25519_key(
        auth.key_id, auth.public_key_bytes()
    )
    old = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=2)
    assert clock.verify(auth.stamp(old)) is None


def test_naive_time_is_never_silently_promoted_to_trusted_time():
    auth = _authority()
    with pytest.raises(ValueError, match="timezone-aware"):
        auth.stamp(datetime.datetime(2026, 6, 1))

    signed = SignedTime(timestamp="2026-06-01T00:00:00", key_id=auth.key_id)
    key = Ed25519PrivateKey.from_private_bytes(SEED)
    signed.signature = "ed25519:" + key.sign(signed.signing_bytes()).hex()
    assert _clock(auth).verify(signed) is None


def test_falsey_non_datetime_never_selects_the_host_clock():
    auth = _authority()
    with pytest.raises(TypeError, match="must be a datetime"):
        auth.stamp(False)  # type: ignore[arg-type]

    trusted = auth.stamp(datetime.datetime(2026, 6, 1, tzinfo=datetime.UTC))
    clock = TrustedClock(max_skew_seconds=60).add_ed25519_key(
        auth.key_id, auth.public_key_bytes()
    )
    assert clock.verify(trusted, local_now=False) is None  # type: ignore[arg-type]


def test_naive_local_skew_reference_is_rejected():
    auth = _authority()
    trusted = auth.stamp(datetime.datetime(2026, 6, 1, tzinfo=datetime.UTC))
    clock = TrustedClock(max_skew_seconds=60).add_ed25519_key(
        auth.key_id, auth.public_key_bytes()
    )

    assert clock.verify(trusted, local_now=datetime.datetime(2026, 6, 1)) is None


# ── Runtime uses trusted time for temporal windows ─────────────────────────────

WINDOW_POLICY = (
    "policy p\n"
    "  valid_from: 2026-01-01T00:00:00Z\n"
    "  valid_until: 2026-12-31T23:59:59Z\n"
    "when true => ALLOW\n"
)


def _runtime_with_trusted_now(trusted_dt):
    auth = _authority()
    clock = _clock(auth)
    signed = auth.stamp(trusted_dt)
    rt = TarlRuntime(PolicyParser.parse(WINDOW_POLICY))
    # The runtime consults trusted time, never the host clock.
    rt.set_clock(lambda: clock.verify(signed))
    return rt


def test_trusted_time_inside_window_allows():
    inside = datetime.datetime(2026, 6, 1, tzinfo=datetime.UTC)
    decision = _runtime_with_trusted_now(inside).evaluate({"x": 1})
    assert decision.verdict == TarlVerdict.ALLOW


def test_trusted_time_after_window_is_not_allowed():
    after = datetime.datetime(2027, 6, 1, tzinfo=datetime.UTC)
    decision = _runtime_with_trusted_now(after).evaluate({"x": 1})
    # Outside the window the policy is not in effect (on_expiry / ESCALATE).
    assert decision.verdict != TarlVerdict.ALLOW


def test_trusted_time_before_window_is_not_allowed():
    before = datetime.datetime(2025, 6, 1, tzinfo=datetime.UTC)
    decision = _runtime_with_trusted_now(before).evaluate({"x": 1})
    assert decision.verdict != TarlVerdict.ALLOW


def test_invalid_configured_clock_never_falls_back_to_host_time():
    invalid_clocks = [
        lambda: None,
        lambda: datetime.datetime(2026, 6, 1),
        lambda: "2026-06-01T00:00:00Z",
    ]

    for clock in invalid_clocks:
        runtime = TarlRuntime(PolicyParser.parse(WINDOW_POLICY)).set_clock(clock)
        decision, proof = runtime.evaluate_with_proof({"x": 1})

        assert decision.verdict == TarlVerdict.DENY
        assert "trusted clock failure" in decision.reason
        assert proof.verdict == TarlVerdict.DENY
        assert proof.trace[0]["kind"] == "trusted-time-failure"


def test_configured_clock_exception_fails_closed():
    def unavailable():
        raise RuntimeError("time authority unavailable")

    runtime = TarlRuntime(PolicyParser.parse(WINDOW_POLICY)).set_clock(unavailable)
    decision = runtime.evaluate({"x": 1})

    assert decision.verdict == TarlVerdict.DENY
    assert "time authority unavailable" in decision.reason
