"""
Sovereign Runtime — ConfigSnapshot creation/verification, audit log, compliance bundle.
"""

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class ConfigSnapshot:
    """A snapshot of a configuration at a point in time, with SHA-256 hash."""

    name: str
    version: str
    timestamp: float
    config_data: dict[str, Any]
    policy_hash: str
    snapshot_hash: str = ""

    def __post_init__(self):
        if not self.snapshot_hash:
            self.snapshot_hash = self.compute_hash()

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of this snapshot's content."""
        data = {
            "name": self.name,
            "version": self.version,
            "timestamp": self.timestamp,
            "config_data": self.config_data,
            "policy_hash": self.policy_hash,
        }
        content = json.dumps(data, sort_keys=True).encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    def verify(self) -> bool:
        """Verify that the stored hash matches the computed hash."""
        computed = self.compute_hash()
        return computed == self.snapshot_hash

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConfigSnapshot":
        return cls(**data)


class AuditLogWriter:
    """
    Append-only JSONL audit log writer.
    Each entry is timestamped and hashed for integrity.
    """

    def __init__(self, log_path: str):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = None
        self._entry_count = 0
        self._last_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
        """Load the last entry's hash from existing log for chaining."""
        if not self.log_path.exists():
            return hashlib.sha256(b"GENESIS").hexdigest()
        with open(self.log_path) as f:
            lines = f.readlines()
        if not lines:
            return hashlib.sha256(b"GENESIS").hexdigest()
        last_entry = json.loads(lines[-1].strip())
        return last_entry.get("entry_hash", hashlib.sha256(b"GENESIS").hexdigest())

    def append(self, entry: dict[str, Any]) -> str:
        """
        Append an entry to the audit log.
        Returns the entry hash for chaining.
        """
        timestamp = time.time()

        # Build entry with previous hash chaining
        log_entry = {
            "timestamp": timestamp,
            "timestamp_iso": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp)
            ),
            "entry_index": self._entry_count,
            "previous_hash": self._last_hash,
            **entry,
        }

        # Compute entry hash
        content = json.dumps(log_entry, sort_keys=True).encode("utf-8")
        entry_hash = hashlib.sha256(content).hexdigest()
        log_entry["entry_hash"] = entry_hash

        # Write
        with open(self.log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        self._last_hash = entry_hash
        self._entry_count += 1

        return entry_hash

    def read_all(self) -> list[dict[str, Any]]:
        """Read all entries from the audit log."""
        if not self.log_path.exists():
            return []
        entries = []
        with open(self.log_path) as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line.strip()))
        return entries

    def verify_integrity(self) -> bool:
        """Verify the hash chain integrity of the entire audit log."""
        entries = self.read_all()
        if not entries:
            return True

        prev_hash = hashlib.sha256(b"GENESIS").hexdigest()
        for entry in entries:
            stored_hash = entry.get("entry_hash", "")
            if entry.get("previous_hash", "") != prev_hash:
                return False

            # Recompute entry hash (without the entry_hash field)
            verify_entry = {k: v for k, v in entry.items() if k != "entry_hash"}
            content = json.dumps(verify_entry, sort_keys=True).encode("utf-8")
            computed_hash = hashlib.sha256(content).hexdigest()

            if computed_hash != stored_hash:
                return False

            prev_hash = stored_hash

        return True

    def close(self):
        if self._file:
            self._file.close()
            self._file = None


def create_config_snapshot(
    name: str, version: str, config_data: dict[str, Any], policy_hash: str
) -> ConfigSnapshot:
    """Create a new ConfigSnapshot with automatic hashing."""
    return ConfigSnapshot(
        name=name,
        version=version,
        timestamp=time.time(),
        config_data=config_data,
        policy_hash=policy_hash,
    )


def verify_config_snapshot(snapshot: ConfigSnapshot) -> bool:
    """Verify a ConfigSnapshot's integrity."""
    return snapshot.verify()


def export_compliance_bundle(
    audit_log_path: str,
    snapshot: ConfigSnapshot,
    output_dir: str,
    additional_data: dict[str, Any] | None = None,
) -> dict[str, str]:
    """
    Export a compliance bundle: audit log + snapshot verification + report.
    Returns dict of export file paths.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Export snapshot
    snapshot_path = output_path / "config_snapshot.json"
    with open(snapshot_path, "w") as f:
        json.dump(snapshot.to_dict(), f, indent=2)

    # Copy/export audit log
    audit_export = output_path / "audit_log.jsonl"
    if Path(audit_log_path).exists():
        import shutil

        shutil.copy2(audit_log_path, audit_export)

    # Generate verification report
    audit_writer = AuditLogWriter(audit_log_path)
    integrity_ok = audit_writer.verify_integrity()

    report = {
        "export_timestamp": time.time(),
        "export_timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "snapshot_name": snapshot.name,
        "snapshot_hash": snapshot.snapshot_hash,
        "snapshot_verified": snapshot.verify(),
        "audit_integrity": integrity_ok,
        "audit_entry_count": len(audit_writer.read_all()),
    }

    if additional_data:
        report["additional_data"] = additional_data

    report_path = output_path / "verification_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    return {
        "snapshot": str(snapshot_path),
        "audit_log": str(audit_export),
        "report": str(report_path),
    }
