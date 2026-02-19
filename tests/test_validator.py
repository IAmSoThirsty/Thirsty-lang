from __future__ import annotations
import textwrap
import pytest
from thirsty_lang.parser import parse_yaml
from thirsty_lang.validator import validate_and_normalize
from thirsty_lang.errors import ValidationError


def _flow(tasks_yaml: str, edges_yaml: str = "", policy_yaml: str = "") -> str:
    return textwrap.dedent(f"""\
        version: 1
        id: "test-flow"
        tenant: "test-tenant"
        tasks:
{textwrap.indent(textwrap.dedent(tasks_yaml), "          ")}
        {("edges:\n" + textwrap.indent(textwrap.dedent(edges_yaml), "          ")) if edges_yaml else ""}
        {("policy:\n" + textwrap.indent(textwrap.dedent(policy_yaml), "          ")) if policy_yaml else ""}
    """)


SINGLE_TASK = """\
- name: "t1"
  agent: "a1"
  input: {}
"""

TWO_TASKS = """\
- name: "t1"
  agent: "a1"
  input: {}
- name: "t2"
  agent: "a2"
  input: {}
"""


class TestValid:
    def test_minimal_flow_validates(self) -> None:
        doc = parse_yaml(_flow(SINGLE_TASK))
        ir = validate_and_normalize(doc)
        assert ir.id == "test-flow"
        assert ir.tenant == "test-tenant"
        assert "t1" in ir.tasks
        assert ir.tasks["t1"].priority == 0
        assert ir.tasks["t1"].timeout_ms == 10_000

    def test_two_tasks_with_edge(self) -> None:
        doc = parse_yaml(_flow(TWO_TASKS, "- from: t1\n  to: t2\n"))
        ir = validate_and_normalize(doc)
        assert len(ir.edges) == 1
        assert ir.edges[0].source == "t1"

    def test_policy_defaults(self) -> None:
        doc = parse_yaml(_flow(SINGLE_TASK))
        ir = validate_and_normalize(doc)
        assert ir.policy.risk_level == "low"
        assert ir.policy.requires_approval is False


class TestInvalid:
    def test_empty_flow_id_raises(self) -> None:
        src = "version: 1\nid: ''\ntenant: 't'\ntasks:\n  - name: t1\n    agent: a1\n    input: {}\n"
        doc = parse_yaml(src)
        with pytest.raises(ValidationError, match="flow id"):
            validate_and_normalize(doc)

    def test_empty_tenant_raises(self) -> None:
        src = "version: 1\nid: 'f'\ntenant: ''\ntasks:\n  - name: t1\n    agent: a1\n    input: {}\n"
        doc = parse_yaml(src)
        with pytest.raises(ValidationError, match="tenant"):
            validate_and_normalize(doc)

    def test_duplicate_task_name_raises(self) -> None:
        tasks = "- name: t1\n  agent: a1\n  input: {}\n- name: t1\n  agent: a2\n  input: {}\n"
        doc = parse_yaml(_flow(tasks))
        with pytest.raises(ValidationError, match="duplicate"):
            validate_and_normalize(doc)

    def test_edge_to_unknown_task_raises(self) -> None:
        doc = parse_yaml(_flow(SINGLE_TASK, "- from: t1\n  to: ghost\n"))
        with pytest.raises(ValidationError, match="ghost"):
            validate_and_normalize(doc)

    def test_invalid_risk_level_raises(self) -> None:
        doc = parse_yaml(_flow(SINGLE_TASK, "", "risk_level: extreme\n"))
        with pytest.raises(ValidationError, match="risk_level"):
            validate_and_normalize(doc)

    def test_cycle_raises(self) -> None:
        tasks = TWO_TASKS
        edges = "- from: t1\n  to: t2\n- from: t2\n  to: t1\n"
        doc = parse_yaml(_flow(tasks, edges))
        with pytest.raises(ValidationError, match="cycle"):
            validate_and_normalize(doc)

    def test_empty_agent_raises(self) -> None:
        src = "version: 1\nid: f\ntenant: t\ntasks:\n  - name: t1\n    agent: ''\n    input: {}\n"
        doc = parse_yaml(src)
        with pytest.raises(ValidationError, match="agent"):
            validate_and_normalize(doc)
