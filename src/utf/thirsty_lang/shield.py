"""Trusted, per-run supervisor for a single signed stdout record."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from typing import BinaryIO

from utf.tarl.authority import AuthorityVerifier, VerifiedAuthority
from utf.tarl.broker import BrokerDecision

MAX_RECORD_BYTES = 1024
_MAX_LINEAGE_DEPTH = 64


class ShieldDenied(Exception):
    """The supervisor refused an operation or cannot confirm its publication."""


def _grant_prefix(source: str, site: tuple[int, int]) -> str:
    if (
        type(source) is not str
        or type(site) is not tuple
        or len(site) != 2
        or any(type(n) is not int or n < 1 for n in site)
    ):
        raise ValueError("shield requires source text and a one-based line and column")
    normalized = source.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    digest = hashlib.sha256(normalized).hexdigest()
    return f"shield:v1:write:stdout:{digest}:{site[0]}:{site[1]}:"


def _record(text: str) -> bytes:
    if type(text) is not str or len(text) >= MAX_RECORD_BYTES:
        raise ValueError("shield requires a bounded UTF-8 stdout record")
    record = text.encode("utf-8") + b"\n"
    if len(record) > MAX_RECORD_BYTES:
        raise ValueError("shield stdout record exceeds the byte limit")
    return record


def stdout_grant(source: str, site: tuple[int, int], text: str) -> str:
    """Construct the scope for the issuer to sign, including the final LF."""
    return _grant_prefix(source, site) + hashlib.sha256(_record(text)).hexdigest()


@dataclass(slots=True)
class _Lineage:
    parent: _Lineage | None = None
    depth: int = 0
    surrendered: bool = False


@dataclass(slots=True)
class _SharedRun:
    prefix: str
    authority: VerifiedAuthority | None
    sink: BinaryIO
    lock: Lock = field(default_factory=Lock)
    stopped: bool = False
    outcome: str = "unused"
    # A single adapter slot. Once it owns a record, admission can never reopen.
    admitted: bytes | None = None


class ShieldRun:
    """Host-owned handle. Derived handles share an adapter and one-use budget."""

    __slots__ = ("_shared", "_lineage")

    def __init__(
        self,
        source: str,
        site: tuple[int, int],
        authority: VerifiedAuthority | None,
        sink: BinaryIO,
    ) -> None:
        self._shared = _SharedRun(
            _grant_prefix(source, site),
            authority if AuthorityVerifier.is_verified(authority) else None,
            sink,
        )
        self._lineage = _Lineage()

    @property
    def authority(self) -> VerifiedAuthority | None:
        return self._shared.authority

    @property
    def outcome(self) -> str:
        """Shared adapter state: unused, in_flight, published, or unknown."""
        with self._shared.lock:
            return self._shared.outcome

    def matches(self, source: str, site: tuple[int, int]) -> bool:
        return self._shared.prefix == _grant_prefix(source, site)

    def derive(self) -> ShieldRun:
        if self._lineage.depth >= _MAX_LINEAGE_DEPTH:
            raise ShieldDenied("shield handle depth limit reached")
        return self._child(self._lineage.depth + 1)

    def _channel_handle(self) -> ShieldRun:
        """Attach one non-derivable transport leaf, even at maximum public depth."""
        if self._lineage.depth > _MAX_LINEAGE_DEPTH:
            raise ShieldDenied("shield channel handle cannot delegate")
        return self._child(_MAX_LINEAGE_DEPTH + 1)

    def _child(self, depth: int) -> ShieldRun:
        child = object.__new__(ShieldRun)
        child._shared = self._shared
        child._lineage = _Lineage(self._lineage, depth)
        return child

    def surrender(self) -> None:
        """Acknowledge revocation for this handle and its descendants."""
        with self._shared.lock:
            self._lineage.surrendered = True

    def stop(self) -> None:
        """Close admission across the run, including while the sink is busy."""
        with self._shared.lock:
            self._shared.stopped = True

    def _require_live(self, grant: str) -> None:
        """Called with the shared lock held."""
        state = self._shared
        if state.stopped:
            raise ShieldDenied("shield run stopped")
        lineage: _Lineage | None = self._lineage
        while lineage is not None:
            if lineage.surrendered:
                raise ShieldDenied("shield grant surrendered")
            lineage = lineage.parent
        if state.admitted is not None:
            raise ShieldDenied("shield stdout grant already spent")
        authority = state.authority
        if authority is None or authority.expires_at is None:
            raise ShieldDenied("shield requires a verified, expiring credential")
        if authority.authorization_error(None) is not None:
            raise ShieldDenied("shield credential is no longer valid")
        if not authority.has_grant(grant):
            raise ShieldDenied("shield credential has no grant for this stdout record")

    def _authorize(
        self, text: str, authorize: Callable[[], object], *, dispatch: bool
    ) -> bytes:
        try:
            record = _record(text)
        except ValueError as exc:
            raise ShieldDenied("invalid shield stdout record") from exc
        state = self._shared
        grant = state.prefix + hashlib.sha256(record).hexdigest()
        with state.lock:
            self._require_live(grant)
        # Proof evaluation can pause or reenter the supervisor. Stop and
        # surrender stay available, and the result cannot reserve a future use.
        try:
            decision = authorize()
        except Exception as exc:
            raise ShieldDenied("stdout policy denied the shield operation") from exc
        if decision is not None and decision is not True:
            if not isinstance(decision, BrokerDecision) or not decision.allowed:
                raise ShieldDenied("stdout policy denied the shield operation")
        with state.lock:
            self._require_live(grant)
            if dispatch:
                # Linearization point: transfer the exact immutable bytes to
                # the host adapter. Only this caller will drain its single slot.
                with AuthorityVerifier.admission_guard(state.authority) as error:
                    if error is not None:
                        raise ShieldDenied(f"shield credential denied: {error}")
                    state.admitted = record
                    state.outcome = "in_flight"
        return record

    def check(self, text: str, authorize: Callable[[], object]) -> None:
        self._authorize(text, authorize, dispatch=False)

    def dispatch(self, text: str, authorize: Callable[[], object]) -> None:
        record = self._authorize(text, authorize, dispatch=True)
        state = self._shared
        outcome = "unknown"
        try:
            count = state.sink.write(record)
            if type(count) is not int or count != len(record):
                raise ShieldDenied("shield adapter did not confirm the full record")
            state.sink.flush()
            outcome = "published"
        except Exception as exc:
            raise ShieldDenied("shield stdout publication outcome unknown") from exc
        finally:
            with state.lock:
                state.outcome = outcome

    def close(self) -> None:
        self.surrender()

    def __enter__(self) -> ShieldRun:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
