"""Shadow Thirst CLI - analysis, visualization, and governed admission."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from utf.shadow_thirst.core import AnalysisLevel, MutationParser, PromotionEngine


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _read_json(path: str) -> dict[str, Any]:
    try:
        text = Path(path).read_text(encoding="utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON value: {value}")
            ),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def _read_mutation(path: str):
    try:
        source = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read mutation file: {exc}") from exc
    try:
        return MutationParser.parse(source)
    except ValueError as exc:
        raise ValueError(f"parse error: {exc}") from exc


def _add_existing_commands(subparsers) -> None:
    check_parser = subparsers.add_parser("check", help="Analyze a mutation file")
    check_parser.add_argument("mutation_file", help="Path to mutation file")
    check_parser.add_argument(
        "--json", "-j", action="store_true", help="Output as JSON"
    )

    viz_parser = subparsers.add_parser("visualize", help="Generate Mermaid flowchart")
    viz_parser.add_argument("mutation_file", help="Path to mutation file")
    viz_parser.add_argument("--output", "-o", help="Output file (default stdout)")


def _add_admission_commands(subparsers) -> None:
    admit_parser = subparsers.add_parser(
        "admit",
        help="Evaluate technical change eligibility and emit an admission record",
    )
    admit_parser.add_argument("mutation_file", help="Path to mutation file")
    admit_parser.add_argument(
        "--policy", help="Strict JSON admission policy (defaults are fail-closed)"
    )
    admit_parser.add_argument(
        "--provenance", help="Strict JSON origin metadata; origin grants no authority"
    )
    admit_parser.add_argument(
        "--signing-key",
        help="Private tarl-key/v1 proof-signer key used to sign the record",
    )
    admit_parser.add_argument(
        "--record", required=True, help="Output path for the admission record"
    )
    admit_parser.add_argument(
        "--json", "-j", action="store_true", help="Also print the record as JSON"
    )

    verify_parser = subparsers.add_parser(
        "verify-admission", help="Verify a Change Admission Record"
    )
    verify_parser.add_argument("record_file", help="Admission record JSON")
    verify_parser.add_argument(
        "--public-key", help="Public tarl-key/v1 proof-signer key"
    )
    verify_parser.add_argument(
        "--require-signature",
        action="store_true",
        help="Reject an otherwise valid unsigned record",
    )
    verify_parser.add_argument(
        "--json", "-j", action="store_true", help="Output verification as JSON"
    )


def _run_check(args, module) -> int:
    verdict, results = PromotionEngine().evaluate(module)
    if args.json:
        output = {
            "name": module.name,
            "verdict": verdict,
            "replay_hash": module.replay_hash(),
            "results": [
                {
                    "analyzer": result.analyzer,
                    "passed": result.passed,
                    "level": result.level,
                    "message": result.message,
                }
                for result in results
            ],
        }
        print(json.dumps(output, indent=2))
        return 0

    print(f"Mutation:    {module.name}")
    print(f"Replay Hash: {module.replay_hash()}")
    print(f"{'─' * 60}")
    for result in results:
        status = "✅" if result.passed else "❌"
        level_tag = "[CRITICAL]" if result.level == AnalysisLevel.CRITICAL else "[WARN]"
        print(f"  {status} {level_tag} {result.analyzer}")
        print(f"     {result.message}")
    print(f"{'─' * 60}")
    verdict_icon = (
        "🚀" if verdict == "PROMOTE" else "❌" if verdict == "REJECT" else "⚠️"
    )
    print(f"  {verdict_icon} VERDICT: {verdict}")
    return 0


def _run_visualize(args, module) -> int:
    engine = PromotionEngine()
    verdict, results = engine.evaluate(module)
    mermaid = engine.generate_mermaid(module, verdict, results)
    if args.output:
        Path(args.output).write_text(mermaid, encoding="utf-8")
        print(f"Mermaid flowchart written to {args.output}")
    else:
        print(mermaid)
    return 0


def _run_admit(args, module) -> int:
    from utf.shadow_thirst.admission import (
        AdmissionEngine,
        AdmissionPolicy,
        Provenance,
    )
    from utf.tarl.keystore import load as load_key

    policy = AdmissionPolicy.from_dict(_read_json(args.policy) if args.policy else {})
    provenance = Provenance.from_dict(
        _read_json(args.provenance) if args.provenance else {}
    )
    record = AdmissionEngine(policy).evaluate(module, provenance=provenance)
    if args.signing_key:
        record.sign(load_key(args.signing_key))
    Path(args.record).write_text(record.to_json() + "\n", encoding="utf-8")
    if args.json:
        print(record.to_json())
    else:
        print(f"Admission decision: {record.admission_decision}")
        print(f"Analysis ID:        {record.analysis_id}")
        print(f"Record hash:        {record.record_hash}")
        print(f"Signed:             {'yes' if record.signature else 'no'}")
        print("Execution authority: NOT EVALUATED")
        print(f"Record written to:  {args.record}")
    return 0 if record.admission_decision == "ELIGIBLE" else 2


def _run_verify_admission(args) -> int:
    from utf.shadow_thirst.admission import ChangeAdmissionRecord
    from utf.tarl.keystore import load as load_key

    record = ChangeAdmissionRecord.from_dict(_read_json(args.record_file))
    if args.require_signature and not record.signature:
        valid, reason = False, "signature is required"
    else:
        key = load_key(args.public_key) if args.public_key else None
        valid, reason = record.verify(key)
    output = {
        "valid": valid,
        "reason": reason,
        "record_hash": record.record_hash,
        "admission_decision": record.admission_decision,
        "execution_authorized": False,
    }
    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print(f"Valid:               {'yes' if valid else 'no'}")
        print(f"Reason:              {reason}")
        print(f"Admission decision:  {record.admission_decision}")
        print("Execution authority: NOT EVALUATED")
    return 0 if valid else 1


def main() -> None:
    from utf.console import enable_utf8

    enable_utf8()
    parser = argparse.ArgumentParser(
        description="Shadow Thirst - mutation analysis and governed change admission"
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")
    _add_existing_commands(subparsers)
    _add_admission_commands(subparsers)
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        raise SystemExit(1)

    try:
        if args.command == "verify-admission":
            exit_code = _run_verify_admission(args)
        else:
            module = _read_mutation(args.mutation_file)
            if args.command == "check":
                exit_code = _run_check(args, module)
            elif args.command == "visualize":
                exit_code = _run_visualize(args, module)
            else:
                exit_code = _run_admit(args, module)
    except (OSError, TypeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    if exit_code:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
