"""
Iron Path — Sovereign pipeline execution with config snapshots, audit logging, and compliance.
"""

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import yaml

from governance.sovereign_runtime import (
    AuditLogWriter,
    ConfigSnapshot,
    create_config_snapshot,
    export_compliance_bundle,
)


@dataclass
class PipelineStep:
    """A single step in a pipeline configuration."""

    name: str
    module: str
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    timeout: int = 30
    retry: int = 0
    depends_on: list[str] = field(default_factory=list)


@dataclass
class PipelineConfig:
    """Pipeline configuration loaded from YAML."""

    name: str
    version: str
    description: str = ""
    steps: list[PipelineStep] = field(default_factory=list)
    policy_binding: str = ""
    author: str = ""

    @classmethod
    def from_yaml(cls, yaml_data: dict[str, Any]) -> "PipelineConfig":
        steps = []
        for s in yaml_data.get("steps", []):
            steps.append(PipelineStep(**s))
        return cls(
            name=yaml_data.get("name", "unnamed"),
            version=yaml_data.get("version", "0.1.0"),
            description=yaml_data.get("description", ""),
            steps=steps,
            policy_binding=yaml_data.get("policy_binding", ""),
            author=yaml_data.get("author", ""),
        )


class IronPathSovereign:
    """
    Iron Path Sovereign — manages pipeline execution with:
    - Role-based signing
    - Policy state binding
    - SHA-256 artifact hashing
    - Immutable JSONL audit logging
    - Compliance bundle export
    """

    def __init__(self, audit_log_path: str = "governance/audit_log.jsonl"):
        self.audit_log = AuditLogWriter(audit_log_path)
        self.role_signature: str | None = None
        self.policy_binding: str | None = None

    def set_role_signature(self, signature: str):
        """Set the role signature for this sovereign."""
        self.role_signature = signature

    def load_pipeline_yaml(self, path: str) -> PipelineConfig:
        """Load and parse a pipeline YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)

        config = PipelineConfig.from_yaml(data)

        # Audit the load
        self.audit_log.append(
            {
                "action": "load_pipeline",
                "pipeline_name": config.name,
                "pipeline_version": config.version,
                "step_count": len(config.steps),
                "source": path,
            }
        )

        return config

    def compute_artifact_hash(self, artifact_path: str) -> str:
        """Compute SHA-256 hash of an artifact file."""
        sha256 = hashlib.sha256()
        with open(artifact_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def verify_config_snapshot(
        self, config: PipelineConfig, snapshot_hash: str
    ) -> bool:
        """Verify a config snapshot against a stored hash."""
        data = asdict(config)
        content = json.dumps(data, sort_keys=True).encode("utf-8")
        computed = hashlib.sha256(content).hexdigest()
        return computed == snapshot_hash

    def execute_pipeline(self, config: PipelineConfig) -> dict[str, Any]:
        """
        Execute a pipeline with role signature + policy state binding.

        Returns execution results with artifact hashes and audit trail.
        """
        if not self.role_signature:
            raise ValueError("Role signature not set. Call set_role_signature() first.")

        # Create config snapshot
        config_data = asdict(config)
        config_data["role_signature"] = self.role_signature
        snapshot = create_config_snapshot(
            name=config.name,
            version=config.version,
            config_data=config_data,
            policy_hash=self.policy_binding or "",
        )

        # Audit pipeline start
        self.audit_log.append(
            {
                "action": "pipeline_start",
                "pipeline_name": config.name,
                "snapshot_hash": snapshot.snapshot_hash,
                "role_signature": self.role_signature,
                "policy_binding": self.policy_binding or "",
            }
        )

        # Execute steps
        step_results = []
        pipeline_success = True

        for step in config.steps:
            step_start = time.time()

            # Check dependencies
            dep_ok = all(
                any(r["step_name"] == dep and r["success"] for r in step_results)
                for dep in step.depends_on
            )
            if not dep_ok:
                step_results.append(
                    {
                        "step_name": step.name,
                        "success": False,
                        "error": f"Dependency not satisfied: {step.depends_on}",
                        "duration": 0,
                    }
                )
                pipeline_success = False
                continue

            # Execute step (simulated)
            try:
                result = self._execute_step(step)
                step_results.append(
                    {
                        "step_name": step.name,
                        "success": True,
                        "result": result,
                        "duration": time.time() - step_start,
                    }
                )
            except Exception as e:
                step_results.append(
                    {
                        "step_name": step.name,
                        "success": False,
                        "error": str(e),
                        "duration": time.time() - step_start,
                    }
                )
                pipeline_success = False
                if step.retry == 0:
                    break

        # Audit pipeline completion
        self.audit_log.append(
            {
                "action": "pipeline_complete",
                "pipeline_name": config.name,
                "success": pipeline_success,
                "steps_completed": len([r for r in step_results if r["success"]]),
                "steps_total": len(config.steps),
            }
        )

        return {
            "success": pipeline_success,
            "snapshot_hash": snapshot.snapshot_hash,
            "step_results": step_results,
            "pipeline_name": config.name,
        }

    def _execute_step(self, step: PipelineStep) -> dict[str, Any]:
        """Execute a single pipeline step (simulated)."""
        # In production, this would load and run the step's module
        return {
            "module": step.module,
            "action": step.action,
            "params": step.params,
            "status": "completed",
        }

    def export_compliance_bundle(
        self,
        snapshot: ConfigSnapshot,
        output_dir: str = "governance/compliance",
    ) -> dict[str, str]:
        """Export compliance bundle for audit trail."""
        return export_compliance_bundle(
            audit_log_path=self.audit_log.log_path,
            snapshot=snapshot,
            output_dir=output_dir,
        )

    def verify_audit_trail(self) -> bool:
        """Verify the integrity of the entire audit trail."""
        return self.audit_log.verify_integrity()
