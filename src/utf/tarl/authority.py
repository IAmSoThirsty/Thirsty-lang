"""
Authenticated authority provenance for governed execution.

A bare authority *string* (e.g. ``--authority admin``) is a self-asserted
identity: it identifies who *claims* to be acting, but proves nothing. In
hardened mode it grants no elevated authority on its own.

An :class:`AuthorityClaim` is an Ed25519-signed assertion minted by a trusted
issuer (an identity provider) that binds a ``subject``, a set of ``grants``, and
a validity window. The runtime verifies the claim against trusted issuer public
keys via :class:`AuthorityVerifier` before binding the verified identity into the
governance context. This closes threat-model challenges C027 (authority forged by
passing ``--authority admin``) and C028 (authority asserted from the environment):
authority must come from an authenticated, signed credential, never from a string
or an env var alone.

The governance context exposes:

  authority                — the subject string (compat with existing policies)
  authority_subject        — same subject, explicit
  authority_authenticated  — bool: was a valid signed claim presented?
  authority_grants         — list[str] of grants from a verified claim ([] otherwise)

so policies can require ``authority_authenticated == true`` and gate on grants.
"""

from __future__ import annotations

import datetime
import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from weakref import WeakValueDictionary

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


@dataclass
class AuthorityClaim:
    """A (possibly signed) assertion of identity and grants.

    Unsigned by construction; an :class:`AuthorityIssuer` signs it. ``grants`` is
    a free-form set of capability/role tokens the issuer vouches for.
    """

    subject: str
    grants: tuple[str, ...] = ()
    issued_at: str = ""
    expires_at: str | None = None
    key_id: str = ""
    signature: str = ""  # "ed25519:<hex>"

    def signing_bytes(self) -> bytes:
        """Canonical bytes covered by the signature (excludes the signature)."""
        payload = {
            "subject": self.subject,
            "grants": list(self.grants),
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "key_id": self.key_id,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )

    def to_dict(self) -> dict:
        return {
            "subject": self.subject,
            "grants": list(self.grants),
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "key_id": self.key_id,
            "signature": self.signature,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, d: dict) -> AuthorityClaim:
        if type(d) is not dict or set(d) - {
            "subject",
            "grants",
            "issued_at",
            "expires_at",
            "key_id",
            "signature",
        }:
            raise ValueError("invalid authority claim fields")
        if "subject" not in d or type(d.get("grants", [])) not in (list, tuple):
            raise ValueError("authority requires a subject and an array of grants")
        claim = cls(
            subject=d["subject"],
            grants=tuple(d.get("grants", [])),
            issued_at=d.get("issued_at", ""),
            expires_at=d.get("expires_at"),
            key_id=d.get("key_id", ""),
            signature=d.get("signature", ""),
        )
        claim.validate()
        return claim

    def validate(self) -> None:
        if not all(
            type(v) is str
            for v in (self.subject, self.issued_at, self.key_id, self.signature)
        ):
            raise ValueError("authority identity and signature fields must be strings")
        if not self.subject or not self.key_id:
            raise ValueError("authority subject and issuer key must be nonempty")
        if type(self.grants) not in (tuple, list) or any(
            type(g) is not str or not g for g in self.grants
        ):
            raise ValueError("authority grants must be nonempty strings")
        if len(set(self.grants)) != len(self.grants):
            raise ValueError("duplicate authority grants")
        if self.expires_at is not None and type(self.expires_at) is not str:
            raise ValueError("authority expiry must be a timestamp string")

    @classmethod
    def from_json(cls, s: str) -> AuthorityClaim:
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError(f"duplicate authority field {key!r}")
                result[key] = value
            return result

        return cls.from_dict(json.loads(s, object_pairs_hook=unique))


@dataclass(frozen=True)
class VerifiedAuthority:
    """The result of resolving an authority for a governed run.

    ``authenticated`` is True only when a valid signed claim was verified against
    a trusted issuer key. An unauthenticated authority still carries a subject
    (for logging/policy) but no grants and no authenticity.
    """

    subject: str
    grants: tuple[str, ...] = ()
    authenticated: bool = True
    issued_at: str = ""
    expires_at: str | None = None
    key_id: str = ""
    _revalidate: Callable[[datetime.datetime], str | None] | None = field(
        default=None, repr=False, compare=False
    )

    def authorization_error(self, now: datetime.datetime | None) -> str | None:
        """Recheck the original credential at each effect, including key revocation."""
        if not self.authenticated:
            return "authority is not authenticated"
        if now is None:
            now = datetime.datetime.now(datetime.UTC)
        if (
            not isinstance(now, datetime.datetime)
            or now.tzinfo is None
            or now.utcoffset() is None
        ):
            return "authority requires valid timezone-aware time"
        error = _window_error(self.issued_at, self.expires_at, now)
        if error:
            return error
        if self._revalidate is not None:
            try:
                return self._revalidate(now)
            except Exception:
                return "authority revalidation failed"
        return None

    def has_grant(self, grant: str) -> bool:
        return grant in self.grants

    @classmethod
    def unauthenticated(cls, subject: str) -> VerifiedAuthority:
        return cls(subject=subject, grants=(), authenticated=False)

    def context(self) -> dict:
        """Authority fields to merge into a governance evaluation context."""
        return {
            "authority": self.subject,
            "authority_subject": self.subject,
            "authority_authenticated": self.authenticated,
            "authority_grants": list(self.grants),
        }


class AuthorityIssuer:
    """Mints Ed25519-signed :class:`AuthorityClaim` credentials.

    Held by a trusted identity provider, never by the executing program. Tests
    and local operators can construct one from a raw 32-byte seed.
    """

    def __init__(self, key_id: str, private_key: bytes | Ed25519PrivateKey):
        if isinstance(private_key, Ed25519PrivateKey):
            self._key = private_key
        else:
            self._key = Ed25519PrivateKey.from_private_bytes(private_key)
        self.key_id = key_id

    def public_key_bytes(self) -> bytes:
        return self._key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    def issue(
        self,
        subject: str,
        grants: tuple[str, ...] | list[str] = (),
        ttl_seconds: int | None = None,
        now: datetime.datetime | None = None,
    ) -> AuthorityClaim:
        now = now or datetime.datetime.now(datetime.UTC)
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("authority issue time must be timezone-aware")
        if ttl_seconds is not None and (
            type(ttl_seconds) is not int or ttl_seconds <= 0
        ):
            raise ValueError("authority lifetime must be a positive integer")
        if type(grants) not in (tuple, list):
            raise ValueError("authority grants must be an array")
        issued_at = now.isoformat(timespec="seconds")
        expires_at = None
        if ttl_seconds is not None:
            expires_at = (now + datetime.timedelta(seconds=ttl_seconds)).isoformat(
                timespec="seconds"
            )
        claim = AuthorityClaim(
            subject=subject,
            grants=tuple(grants),
            issued_at=issued_at,
            expires_at=expires_at,
            key_id=self.key_id,
        )
        claim.validate()
        claim.signature = "ed25519:" + self._key.sign(claim.signing_bytes()).hex()
        return claim


@dataclass
class AuthorityVerificationResult:
    """Outcome of verifying a claim — carries a reason on failure."""

    authority: VerifiedAuthority | None
    valid: bool
    reason: str = ""


@dataclass(frozen=True, eq=False)
class _IssuerRegistration:
    """A particular registration; removing and restoring a key creates a new one."""

    key: Ed25519PublicKey
    material: bytes


@dataclass(frozen=True)
class _VerifiedCredential:
    verifier: AuthorityVerifier
    claim: AuthorityClaim
    registration: _IssuerRegistration

    def __call__(self, now: datetime.datetime) -> str | None:
        return self.verifier._validation_error(self.claim, now, self.registration)


class AuthorityVerifier:
    """Verifies :class:`AuthorityClaim` credentials against trusted issuer keys.

    Only Ed25519 is accepted — authority is a non-repudiation decision, so a
    symmetric MAC (forgeable by any holder) is never sufficient.
    """

    # A public VerifiedAuthority also serves legacy trusted embedders. Shields
    # accept only the exact object returned after signature verification.
    _issued: WeakValueDictionary[int, VerifiedAuthority] = WeakValueDictionary()
    _issued_lock = Lock()

    @classmethod
    def is_verified(cls, authority: object) -> bool:
        if not isinstance(authority, VerifiedAuthority):
            return False
        with cls._issued_lock:
            return cls._issued.get(id(authority)) is authority

    def __init__(self) -> None:
        self._keys: dict[str, _IssuerRegistration] = {}
        self._keys_lock = Lock()

    @classmethod
    @contextmanager
    def admission_guard(
        cls, authority: VerifiedAuthority | None
    ) -> Iterator[str | None]:
        """Order a short adapter handoff with issuer changes and sample expiry.

        A successful guard yields None. The caller performs only the slot
        transfer inside it. Policy evaluation and sink I/O run outside it.
        """
        if authority is None or not cls.is_verified(authority):
            yield "unverified authority"
            return
        binding = authority._revalidate
        if not isinstance(binding, _VerifiedCredential):
            yield "authority has no verified issuer registration"
            return
        verifier = binding.verifier
        claim = binding.claim
        with verifier._keys_lock:
            if verifier._keys.get(claim.key_id) is not binding.registration:
                yield "issuer registration revoked or replaced"
            else:
                yield _window_error(
                    claim.issued_at,
                    claim.expires_at,
                    datetime.datetime.now(datetime.UTC),
                )

    def add_ed25519_key(
        self, key_id: str, public_key: bytes | Ed25519PublicKey
    ) -> AuthorityVerifier:
        if isinstance(public_key, Ed25519PublicKey):
            key = public_key
        else:
            key = Ed25519PublicKey.from_public_bytes(public_key)
        material = key.public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        with self._keys_lock:
            existing = self._keys.get(key_id)
            if existing is None or existing.material != material:
                self._keys[key_id] = _IssuerRegistration(key, material)
        return self

    def verify(
        self,
        claim: AuthorityClaim,
        now: datetime.datetime | None = None,
    ) -> AuthorityVerificationResult:
        now = now or datetime.datetime.now(datetime.UTC)
        # Copy first, then verify and bind only that copy. Reading the caller's
        # mutable fields again after verification can bind a different identity
        # from the credential that was actually signed.
        try:
            snapshot = AuthorityClaim.from_dict(claim.to_dict())
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            return AuthorityVerificationResult(
                None, False, f"malformed authority claim: {exc}"
            )
        with self._keys_lock:
            registration = self._keys.get(snapshot.key_id)
        if registration is None:
            return AuthorityVerificationResult(
                None, False, f"unknown issuer key_id {snapshot.key_id!r}"
            )
        binding = _VerifiedCredential(self, snapshot, registration)
        reason = binding(now)
        if reason:
            return AuthorityVerificationResult(None, False, reason)
        authority = VerifiedAuthority(
            subject=snapshot.subject,
            grants=tuple(snapshot.grants),
            authenticated=True,
            issued_at=snapshot.issued_at,
            expires_at=snapshot.expires_at,
            key_id=snapshot.key_id,
            _revalidate=binding,
        )
        with self._issued_lock:
            self._issued[id(authority)] = authority
        return AuthorityVerificationResult(authority, True, "ok")

    def revoke_key(self, key_id: str) -> None:
        """Revoke an issuer in this verifier, including credentials already bound."""
        with self._keys_lock:
            self._keys.pop(key_id, None)

    def _validation_error(
        self,
        claim: AuthorityClaim,
        now: datetime.datetime,
        registration: _IssuerRegistration,
    ) -> str | None:
        try:
            claim.validate()
        except (AttributeError, TypeError, ValueError) as exc:
            return f"malformed authority claim: {exc}"
        if (
            not isinstance(now, datetime.datetime)
            or now.tzinfo is None
            or now.utcoffset() is None
        ):
            return "authority verification time must be timezone-aware"
        alg, _, sig_hex = claim.signature.partition(":")
        if alg != "ed25519" or not sig_hex:
            return "authority claim is unsigned or not Ed25519"
        try:
            registration.key.verify(bytes.fromhex(sig_hex), claim.signing_bytes())
        except (ValueError, InvalidSignature):
            return "authority signature is invalid"
        if not claim.issued_at:
            return "authority claim is missing issue time"
        with self._keys_lock:
            if self._keys.get(claim.key_id) is not registration:
                return "issuer registration revoked or replaced"
        return _window_error(claim.issued_at, claim.expires_at, now)


def _window_error(
    issued_at: str, expires_at: str | None, now: datetime.datetime
) -> str | None:
    try:
        issued = datetime.datetime.fromisoformat(issued_at) if issued_at else None
        expiry = (
            datetime.datetime.fromisoformat(expires_at)
            if expires_at is not None
            else None
        )
        for point in (issued, expiry):
            if point is not None and (
                point.tzinfo is None or point.utcoffset() is None
            ):
                return "authority timestamps must be timezone-aware"
        if issued is not None and now < issued:
            return "authority claim is not yet valid"
        if expiry is not None:
            if issued is not None and expiry <= issued:
                return "authority expiry must follow issue time"
            if now >= expiry:
                return "authority claim has expired"
    except (TypeError, ValueError):
        return "authority claim has a malformed validity window"
    return None


__all__ = [
    "AuthorityClaim",
    "VerifiedAuthority",
    "AuthorityIssuer",
    "AuthorityVerifier",
    "AuthorityVerificationResult",
]
