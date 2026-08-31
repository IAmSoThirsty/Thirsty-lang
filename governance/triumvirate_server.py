"""
Triumvirate Server — FastAPI governance server with 3 pillars.
Port 8001. Endpoints: /intent, /audit, /fourlaws, /chimera/verdict, /chimera/canary
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ─── Pillar Base ──────────────────────────────────────────────────────────────


class PillarVerdict(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    ESCALATE = "ESCALATE"


@dataclass
class PillarResult:
    verdict: PillarVerdict
    reason: str
    patterns_triggered: list[str] = field(default_factory=list)


# ─── Galahad (Ethics Pillar) ──────────────────────────────────────────────────

GALAHAD_HARM_PATTERNS = {
    "deception": "Intent involves misleading or deceptive output",
    "bias": "Output may perpetuate demographic or cultural bias",
    "harmful_content": "Output contains or generates hate speech, violence, or explicit content",
    "privacy_violation": "Intent requires access to private or PII data",
    "manipulation": "Intent seeks to manipulate user behavior or decisions",
    "discrimination": "Intent discriminates against protected groups",
    "exploitation": "Intent exploits vulnerable populations",
    "surveillance": "Intent involves unauthorized monitoring or surveillance",
    "intellectual_property": "Intent violates copyright or IP rights",
    "misinformation": "Intent generates or spreads false information",
    "impersonation": "Intent impersonates individuals or entities",
    "coercion": "Intent involves coercive or threatening language",
    "unauthorized_decision": "Intent makes autonomous decisions without human oversight",
}

ETHICS_GUIDELINES = [
    "Do no harm — avoid output that could cause physical, psychological, or social harm",
    "Be transparent — disclose AI nature when interacting with humans",
    "Respect privacy — never request or expose personal data without consent",
    "Be fair — avoid bias and discrimination in all outputs",
    "Maintain human agency — don't manipulate or coerce users",
    "Accept accountability — provide explanation for all decisions",
]


class GalahadPillar:
    """Ethics pillar — checks 13 harm patterns."""

    def evaluate(self, intent: dict[str, Any]) -> PillarResult:
        intent_text = json.dumps(intent).lower()
        triggered = []

        for pattern_key in GALAHAD_HARM_PATTERNS:
            if (
                pattern_key.replace("_", " ") in intent_text
                or pattern_key in intent_text
            ):
                triggered.append(pattern_key)

        if triggered:
            return PillarResult(
                verdict=PillarVerdict.DENY,
                reason=f"Ethics violation: {', '.join(triggered)}",
                patterns_triggered=triggered,
            )

        return PillarResult(
            verdict=PillarVerdict.ALLOW,
            reason="No ethics violations detected",
            patterns_triggered=[],
        )


# ─── Cerberus (Security Pillar) ──────────────────────────────────────────────

CERBERUS_THREAT_PATTERNS = [
    "sql_injection",
    "xss",
    "command_injection",
    "path_traversal",
    "ssrf",
    "rce",
    "ldap_injection",
    "xxe",
    "open_redirect",
    "file_inclusion",
    "template_injection",
    "nosql_injection",
    "header_injection",
    "cors_misconfig",
    "auth_bypass",
    "privilege_escalation",
    "insecure_deserialization",
    "dos_amplification",
    "smuggling",
    "ssrf_ bypass",
]


class CerberusPillar:
    """Security pillar — checks 20 threat patterns."""

    def evaluate(self, intent: dict[str, Any]) -> PillarResult:
        intent_text = json.dumps(intent).lower()
        triggered = []

        for pattern in CERBERUS_THREAT_PATTERNS:
            pattern_normalized = pattern.replace("_", " ")
            if pattern_normalized in intent_text or pattern in intent_text:
                triggered.append(pattern)

        if triggered:
            return PillarResult(
                verdict=PillarVerdict.DENY,
                reason=f"Security threat: {', '.join(triggered)}",
                patterns_triggered=triggered,
            )

        return PillarResult(
            verdict=PillarVerdict.ALLOW,
            reason="No security threats detected",
            patterns_triggered=[],
        )


# ─── CodexDeus (Constitutional Pillar) ──────────────────────────────────────

CODEX_VIOLATION_PATTERNS = [
    "override_constitution",
    "violate_governance",
    "unauthorized_escalation",
    "bypass_policy",
    "illegal_mutation",
    "shadow_operation",
    "deny_human_oversight",
    "conceal_operation",
    "false_compliance",
    "policy_tampering",
    "audit_log_manipulation",
    "sovereign_override",
]

FOUR_LAWS = [
    "A governed agent may not harm a human through action or inaction",
    "A governed agent must obey lawful human directives unless they conflict with the first law",
    "A governed agent must protect its own existence unless that conflicts with the first or second law",
    "A governed agent must log all decisions and submit to audit",
]


class CodexDeusPillar:
    """Constitutional pillar — checks 12 violation patterns + Four Laws."""

    def evaluate(self, intent: dict[str, Any]) -> PillarResult:
        intent_text = json.dumps(intent).lower()
        triggered = []

        for pattern in CODEX_VIOLATION_PATTERNS:
            pattern_normalized = pattern.replace("_", " ")
            if pattern_normalized in intent_text or pattern in intent_text:
                triggered.append(pattern)

        if triggered:
            return PillarResult(
                verdict=PillarVerdict.DENY,
                reason=f"Constitutional violation: {', '.join(triggered)}",
                patterns_triggered=triggered,
            )

        return PillarResult(
            verdict=PillarVerdict.ALLOW,
            reason="No constitutional violations detected",
            patterns_triggered=[],
        )

    def check_four_laws(self, intent: dict[str, Any]) -> list[dict[str, Any]]:
        """Check intent against each of the Four Laws."""
        intent_text = json.dumps(intent).lower()
        results = []
        for i, law in enumerate(FOUR_LAWS, 1):
            follows = True
            if "harm" in intent_text and i == 1:
                follows = False
            if "override" in intent_text and i == 2:
                follows = False
            results.append(
                {
                    "law_number": i,
                    "law": law,
                    "follows": follows,
                }
            )
        return results


# ─── Triumvirate Server ──────────────────────────────────────────────────────


class IntentRequest(BaseModel):
    intent_id: str = ""
    action: str
    target: str = ""
    context: dict[str, Any] = {}
    metadata: dict[str, Any] = {}


class IntentResponse(BaseModel):
    intent_id: str
    verdict: str
    reason: str
    pillar_results: dict[str, dict[str, Any]]
    unanimous: bool
    timestamp: float


class ChimeraRequest(BaseModel):
    prompt: str
    context: dict[str, Any] = {}
    mode: str = "verdict"  # verdict, canary


app = FastAPI(title="Triumvirate Governance Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

galahad = GalahadPillar()
cerberus = CerberusPillar()
codexdeus = CodexDeusPillar()

# Audit log for all decisions
audit_log: list[dict[str, Any]] = []


@app.on_event("startup")
async def startup():
    pass


@app.post("/intent")
async def evaluate_intent(req: IntentRequest):
    """Evaluate an intent through all 3 pillars. Unanimous ALLOW required."""
    intent = {
        "action": req.action,
        "target": req.target,
        "context": req.context,
        "metadata": req.metadata,
        **req.context,
    }

    # Evaluate each pillar
    galahad_result = galahad.evaluate(intent)
    cerberus_result = cerberus.evaluate(intent)
    codexdeus_result = codexdeus.evaluate(intent)

    verdicts = [
        galahad_result.verdict,
        cerberus_result.verdict,
        codexdeus_result.verdict,
    ]

    unanimous = all(v == PillarVerdict.ALLOW for v in verdicts)

    if unanimous:
        overall_verdict = "ALLOW"
        reason = "All three pillars ALLOW this intent"
    elif any(v == PillarVerdict.DENY for v in verdicts):
        overall_verdict = "DENY"
        reasons = []
        if galahad_result.verdict == PillarVerdict.DENY:
            reasons.append(f"Galahad: {galahad_result.reason}")
        if cerberus_result.verdict == PillarVerdict.DENY:
            reasons.append(f"Cerberus: {cerberus_result.reason}")
        if codexdeus_result.verdict == PillarVerdict.DENY:
            reasons.append(f"CodexDeus: {codexdeus_result.reason}")
        reason = "; ".join(reasons)
    else:
        overall_verdict = "ESCALATE"
        reason = "Mixed verdicts require human escalation"

    timestamp = time.time()

    # Audit
    audit_entry = {
        "timestamp": timestamp,
        "intent_id": req.intent_id
        or hashlib.md5(json.dumps(intent).encode()).hexdigest(),
        "action": req.action,
        "overall_verdict": overall_verdict,
        "pillar_results": {
            "galahad": {
                "verdict": galahad_result.verdict.value,
                "reason": galahad_result.reason,
            },
            "cerberus": {
                "verdict": cerberus_result.verdict.value,
                "reason": cerberus_result.reason,
            },
            "codexdeus": {
                "verdict": codexdeus_result.verdict.value,
                "reason": codexdeus_result.reason,
            },
        },
    }
    audit_log.append(audit_entry)

    return {
        "intent_id": audit_entry["intent_id"],
        "verdict": overall_verdict,
        "reason": reason,
        "pillar_results": audit_entry["pillar_results"],
        "unanimous": unanimous,
        "timestamp": timestamp,
    }


@app.get("/audit")
async def get_audit(limit: int = 100):
    """Get recent audit log entries."""
    return {"entries": audit_log[-limit:]}


@app.get("/fourlaws")
async def get_four_laws():
    """Get the Four Laws of governance."""
    return {
        "four_laws": [{"number": i + 1, "law": law} for i, law in enumerate(FOUR_LAWS)]
    }


@app.post("/chimera/verdict")
async def chimera_verdict(req: ChimeraRequest):
    """Chimera verdict endpoint — evaluate a prompt through combined pillars."""
    intent = {"action": req.prompt, "context": req.context}

    galahad_result = galahad.evaluate(intent)
    cerberus_result = cerberus.evaluate(intent)
    codexdeus_result = codexdeus.evaluate(intent)

    combined_verdict = "ALLOW"
    if (
        galahad_result.verdict == PillarVerdict.DENY
        or cerberus_result.verdict == PillarVerdict.DENY
        or codexdeus_result.verdict == PillarVerdict.DENY
    ):
        combined_verdict = "DENY"

    return {
        "verdict": combined_verdict,
        "galahad": {
            "verdict": galahad_result.verdict.value,
            "reason": galahad_result.reason,
        },
        "cerberus": {
            "verdict": cerberus_result.verdict.value,
            "reason": cerberus_result.reason,
        },
        "codexdeus": {
            "verdict": codexdeus_result.verdict.value,
            "reason": codexdeus_result.reason,
        },
    }


@app.post("/chimera/canary")
async def chimera_canary(req: ChimeraRequest):
    """Chimera canary endpoint — returns a canary analysis without blocking."""
    intent = {"action": req.prompt, "context": req.context}

    galahad_result = galahad.evaluate(intent)
    cerberus_result = cerberus.evaluate(intent)
    codexdeus_result = codexdeus.evaluate(intent)
    four_laws_check = codexdeus.check_four_laws(intent)

    return {
        "canary": True,
        "galahad": {
            "verdict": galahad_result.verdict.value,
            "patterns_triggered": galahad_result.patterns_triggered,
        },
        "cerberus": {
            "verdict": cerberus_result.verdict.value,
            "patterns_triggered": cerberus_result.patterns_triggered,
        },
        "codexdeus": {
            "verdict": codexdeus_result.verdict.value,
            "patterns_triggered": codexdeus_result.patterns_triggered,
        },
        "four_laws": four_laws_check,
    }


def main():
    """Run the Triumvirate server with uvicorn."""
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    main()
