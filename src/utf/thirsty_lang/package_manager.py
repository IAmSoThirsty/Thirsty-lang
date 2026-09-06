"""Local dependency management with versioned, content-bound lockfiles.

There is no remote registry resolver. A dependency must identify a bundled
stdlib namespace or a project-local .thirsty source file. Lockfile v1 digests
were hashes of labels; they are intentionally rejected as content evidence.
"""

import hashlib
import json
import os
import platform
import tomllib
from pathlib import Path
from typing import Any

LOCKFILE_VERSION = 2


def content_integrity(content: bytes) -> str:
    return "sha256-" + hashlib.sha256(content).hexdigest()


def runtime_source_integrity() -> str:
    """Hash bundled source independently of the host Python implementation."""
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return "sha256-" + digest.hexdigest()


def runtime_integrity() -> str:
    """Bind bundled Python source and the Python runtime version."""
    content = json.dumps(
        [
            platform.python_implementation(),
            platform.python_version(),
            runtime_source_integrity(),
        ],
        separators=(",", ":"),
    ).encode("utf-8")
    return content_integrity(content)


def project_sources(root: Path) -> dict[str, str]:
    """Hash local source inventory, excluding hidden/generated environments."""
    sources = {}
    for directory, children, files in os.walk(root, followlinks=False):
        children[:] = sorted(
            child
            for child in children
            if not child.startswith(".")
            and child not in {"build", "dist", "__pycache__"}
            and not (Path(directory) / child).is_symlink()
        )
        for filename in sorted(files):
            path = Path(directory) / filename
            if path.suffix != ".thirsty":
                continue
            resolved = path.resolve()
            if not resolved.is_relative_to(root):
                raise ValueError(f"Source escapes project root: {path}")
            sources[path.relative_to(root).as_posix()] = content_integrity(
                path.read_bytes()
            )
    return sources


def _read_json_object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate lockfile key: {key}")
        result[key] = value
    return result


def read_lock(path: Path) -> dict:
    value = json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=_read_json_object
    )
    if not isinstance(value, dict):
        raise ValueError("Lockfile must contain an object")
    return value


class PackageManager:
    """Manage a project manifest and content-based local dependency lock."""

    def __init__(self, project_root: str = "."):
        self.project_root = project_root
        self.manifest_path = os.path.join(project_root, "thirsty.toml")
        self.lock_path = os.path.join(project_root, "thirsty.lock")
        self.manifest: dict = {}
        self.lock: dict = {}

    def parse_manifest(self, path: str | None = None) -> dict:
        if path:
            self.manifest_path = path
        if not os.path.exists(self.manifest_path):
            self.manifest = {}
            return self.manifest
        self.manifest = self._parse_toml(
            Path(self.manifest_path).read_text(encoding="utf-8")
        )
        return self.manifest

    def _parse_toml(self, content: str) -> dict:
        return tomllib.loads(content)

    def _parse_toml_value(self, raw: str) -> object:
        return tomllib.loads("value = " + raw)["value"]

    def parse_lock(self, path: str | None = None) -> dict:
        if path:
            self.lock_path = path
        if not os.path.exists(self.lock_path):
            self.lock = {}
        else:
            self.lock = read_lock(Path(self.lock_path))
        return self.lock

    def _dependency_entry(self, name: str, spec: object, runtime: str) -> dict:
        from utf.thirsty_lang.module_system import STDLIB_MODULES

        root = Path(self.project_root).resolve()
        module = name if name.startswith("thirst::") else "thirst::" + name
        if (
            module in STDLIB_MODULES
            and isinstance(spec, str)
            and not spec.endswith(".thirsty")
        ):
            return {"version": str(spec), "resolved": module, "integrity": runtime}
        if isinstance(spec, dict) and set(spec) - {"path", "version"}:
            raise ValueError(
                f"Dependency '{name}' has unsupported specification fields"
            )
        path_spec = spec.get("path") if isinstance(spec, dict) else spec
        if not isinstance(path_spec, str) or not path_spec.endswith(".thirsty"):
            # The existing API also accepts a source pathname as its name.
            path_spec = name if name.endswith(".thirsty") else None
        if path_spec is None:
            raise ValueError(
                f"Unresolved dependency '{name}': use a local .thirsty path; remote registry resolution is unavailable"
            )
        path = (root / path_spec).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(
                f"Dependency '{name}' must be an existing project-local source file"
            )
        return {
            "version": str(spec.get("version", "*")) if isinstance(spec, dict) else "*",
            "resolved": path.relative_to(root).as_posix(),
            "integrity": content_integrity(path.read_bytes()),
        }

    def generate_lock(self, dependencies: dict | None = None) -> dict:
        if dependencies is None:
            dependencies = self.manifest.get("dependencies", {})
        if not isinstance(dependencies, dict):
            raise ValueError("Manifest dependencies must be a table")
        root = Path(self.project_root).resolve()
        runtime = runtime_integrity()
        manifest = Path(self.manifest_path)
        entries = {
            name: self._dependency_entry(name, spec, runtime)
            for name, spec in dependencies.items()
        }
        sources = project_sources(root)
        for entry in entries.values():
            if not entry["resolved"].startswith("thirst::"):
                sources[entry["resolved"]] = entry["integrity"]
        self.lock = {
            "lockfile_version": LOCKFILE_VERSION,
            "runtime_integrity": runtime,
            "manifest_integrity": (
                content_integrity(manifest.read_bytes()) if manifest.exists() else None
            ),
            "dependencies": entries,
            "sources": sources,
        }
        return self.lock

    def _compute_integrity(self, name: str, version: str) -> str:
        return str(
            self._dependency_entry(name, version, runtime_integrity())["integrity"]
        )

    def write_lock(self, path: str | None = None) -> bool:
        if path:
            self.lock_path = path
        try:
            Path(self.lock_path).write_text(
                json.dumps(self.lock, indent=2) + "\n", encoding="utf-8"
            )
            return True
        except OSError:
            return False

    def verify_integrity(self) -> list[dict]:
        violations = []
        root = Path(self.project_root).resolve()

        def mismatch(name: str, expected: object, computed: object) -> None:
            if expected != computed:
                violations.append(
                    {"name": name, "expected": expected, "computed": computed}
                )

        if self.lock.get("lockfile_version") != LOCKFILE_VERSION:
            return [
                {
                    "name": "lockfile_version",
                    "expected": LOCKFILE_VERSION,
                    "computed": self.lock.get("lockfile_version"),
                }
            ]
        runtime = runtime_integrity()
        mismatch("runtime", self.lock.get("runtime_integrity"), runtime)
        manifest = Path(self.manifest_path)
        mismatch(
            "manifest",
            self.lock.get("manifest_integrity"),
            content_integrity(manifest.read_bytes()) if manifest.exists() else None,
        )
        sources = self.lock.get("sources")
        deps = self.lock.get("dependencies")
        if not isinstance(sources, dict) or not isinstance(deps, dict):
            return violations + [
                {
                    "name": "lockfile_structure",
                    "expected": "source/dependency tables",
                    "computed": "invalid",
                }
            ]
        for name, expected in sources.items():
            path = (root / name).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                mismatch(name, expected, None)
            else:
                mismatch(name, expected, content_integrity(path.read_bytes()))
        for name, entry in deps.items():
            if not isinstance(entry, dict) or not isinstance(
                entry.get("resolved"), str
            ):
                violations.append(
                    {
                        "name": name,
                        "expected": "resolved dependency",
                        "computed": "invalid",
                    }
                )
                continue
            target = entry["resolved"]
            if target.startswith("thirst::"):
                from utf.thirsty_lang.module_system import STDLIB_MODULES

                computed = runtime if target in STDLIB_MODULES else None
            else:
                path = (root / target).resolve()
                computed = (
                    content_integrity(path.read_bytes())
                    if path.is_relative_to(root) and path.is_file()
                    else None
                )
                if target not in sources:
                    violations.append(
                        {
                            "name": name,
                            "expected": "locked source",
                            "computed": "missing",
                        }
                    )
            mismatch(name, entry.get("integrity"), computed)
        return violations

    def add_dependency(self, name: str, version_spec: str = "*") -> bool:
        self._dependency_entry(name, version_spec, runtime_integrity())
        self.manifest.setdefault("dependencies", {})[name] = version_spec
        return self._write_manifest()

    def remove_dependency(self, name: str) -> bool:
        deps = self.manifest.get("dependencies", {})
        if name not in deps:
            return False
        del deps[name]
        return self._write_manifest()

    def _write_manifest(self) -> bool:
        try:
            Path(self.manifest_path).write_text(
                self._format_toml(self.manifest), encoding="utf-8"
            )
            return True
        except (OSError, TypeError, ValueError):
            return False

    def _format_toml(self, data: dict, prefix: str = "") -> str:
        from utf.thirsty_lang.module_system import dump_toml

        if prefix:
            raise ValueError(
                "TOML prefix formatting is unsupported; pass a nested mapping"
            )
        return dump_toml(data)

    def audit_dependencies(self) -> list[dict]:
        self.parse_manifest()
        self.parse_lock()
        issues = []
        manifest_deps = self.manifest.get("dependencies", {})
        lock_deps = self.lock.get("dependencies", {})
        for name in manifest_deps:
            if name not in lock_deps:
                issues.append(
                    {
                        "type": "missing_lock",
                        "name": name,
                        "message": f"Dependency '{name}' is absent from lockfile",
                    }
                )
        for name in lock_deps:
            if name not in manifest_deps:
                issues.append(
                    {
                        "type": "orphan_lock",
                        "name": name,
                        "message": f"Dependency '{name}' is absent from manifest",
                    }
                )
        for violation in self.verify_integrity():
            issues.append(
                {
                    "type": "integrity_mismatch",
                    "name": violation["name"],
                    "message": f"Content integrity mismatch for '{violation['name']}'",
                }
            )
        return issues


def create_thirsty_toml(project_dir: str, name: str, version: str = "0.1.0") -> str:
    from utf.thirsty_lang.module_system import dump_toml

    path = os.path.join(project_dir, "thirsty.toml")
    Path(path).write_text(
        dump_toml(
            {
                "package": {
                    "name": name,
                    "version": version,
                    "thirsty-version": "1.0",
                    "mode": "core",
                },
                "dependencies": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def create_thirsty_lock(project_dir: str) -> str:
    manager = PackageManager(project_dir)
    manager.parse_manifest()
    manager.generate_lock()
    if not manager.write_lock():
        raise OSError("Could not write thirsty.lock")
    return manager.lock_path
