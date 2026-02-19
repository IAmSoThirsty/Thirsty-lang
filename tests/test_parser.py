from __future__ import annotations
import textwrap
import pytest
from thirsty_lang.parser import parse_yaml
from thirsty_lang.errors import ParseError


HELLO_WORLD = textwrap.dedent("""\
    version: 1
    id: "example-flow"
    tenant: "demo-tenant"
    tasks:
      - name: "fetch_context"
        agent: "retriever"
        input:
          query: "{{user.input}}"
        resources:
          priority: 10
          timeout_ms: 2000
      - name: "answer"
        agent: "llm"
        input:
          context_from: "fetch_context"
          question: "{{user.input}}"
        resources:
          priority: 5
          timeout_ms: 8000
    edges:
      - from: "fetch_context"
        to: "answer"
    policy:
      risk_level: "medium"
      requires_approval: false
""")


class TestParseYaml:
    def test_parses_hello_world(self) -> None:
        doc = parse_yaml(HELLO_WORLD)
        assert doc.id == "example-flow"
        assert doc.tenant == "demo-tenant"
        assert doc.version == 1
        assert len(doc.tasks) == 2
        assert len(doc.edges) == 1

    def test_task_fields(self) -> None:
        doc = parse_yaml(HELLO_WORLD)
        fetch = doc.tasks[0]
        assert fetch.name == "fetch_context"
        assert fetch.agent == "retriever"
        assert fetch.resources["priority"] == 10
        assert fetch.resources["timeout_ms"] == 2000

    def test_edge_fields(self) -> None:
        doc = parse_yaml(HELLO_WORLD)
        edge = doc.edges[0]
        assert edge.source == "fetch_context"
        assert edge.target == "answer"
        assert edge.condition is None

    def test_policy_fields(self) -> None:
        doc = parse_yaml(HELLO_WORLD)
        assert doc.policy.risk_level == "medium"
        assert doc.policy.requires_approval is False

    def test_missing_tasks_raises(self) -> None:
        src = "version: 1\nid: x\ntenant: t\n"
        with pytest.raises(ParseError, match="tasks"):
            parse_yaml(src)

    def test_invalid_yaml_raises(self) -> None:
        with pytest.raises(ParseError, match="YAML"):
            parse_yaml(":\t")

    def test_non_mapping_root_raises(self) -> None:
        with pytest.raises(ParseError, match="mapping"):
            parse_yaml("[1, 2, 3]")

    def test_defaults_applied(self) -> None:
        src = textwrap.dedent("""\
            version: 1
            id: "f"
            tenant: "t"
            tasks:
              - name: "t1"
                agent: "a1"
                input: {}
        """)
        doc = parse_yaml(src)
        assert doc.policy.risk_level == "low"
        assert doc.edges == []

    def test_extra_policy_fields_preserved(self) -> None:
        src = textwrap.dedent("""\
            version: 1
            id: "f"
            tenant: "t"
            tasks:
              - name: "t1"
                agent: "a1"
                input: {}
            policy:
              risk_level: "low"
              custom_field: "val"
        """)
        doc = parse_yaml(src)
        assert doc.policy.extra.get("custom_field") == "val"
