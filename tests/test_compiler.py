from __future__ import annotations
import textwrap
import pytest
from thirsty_lang.parser import parse_yaml
from thirsty_lang.validator import validate_and_normalize
from thirsty_lang.compiler import ir_to_monolith_tasks, ir_to_waterfall_spec


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


@pytest.fixture()
def ir_flow():
    doc = parse_yaml(HELLO_WORLD)
    return validate_and_normalize(doc)


class TestIrToMonolithTasks:
    def test_returns_two_tasks(self, ir_flow) -> None:
        tasks = ir_to_monolith_tasks(ir_flow)
        assert len(tasks) == 2

    def test_topological_order_sources_first(self, ir_flow) -> None:
        tasks = ir_to_monolith_tasks(ir_flow)
        names = [t["meta"]["labels"]["task_name"] for t in tasks]
        assert names.index("fetch_context") < names.index("answer")

    def test_tenant_becomes_owner(self, ir_flow) -> None:
        tasks = ir_to_monolith_tasks(ir_flow)
        for t in tasks:
            assert t["meta"]["owner"] == "demo-tenant"

    def test_priority_preserved(self, ir_flow) -> None:
        tasks = ir_to_monolith_tasks(ir_flow)
        by_name = {t["meta"]["labels"]["task_name"]: t for t in tasks}
        assert by_name["fetch_context"]["meta"]["priority"] == 10
        assert by_name["answer"]["meta"]["priority"] == 5

    def test_timeout_in_resource_hints(self, ir_flow) -> None:
        tasks = ir_to_monolith_tasks(ir_flow)
        by_name = {t["meta"]["labels"]["task_name"]: t for t in tasks}
        assert by_name["fetch_context"]["meta"]["resource_hints"]["timeout_ms"] == 2000

    def test_flow_id_label(self, ir_flow) -> None:
        tasks = ir_to_monolith_tasks(ir_flow)
        for t in tasks:
            assert t["meta"]["labels"]["flow_id"] == "example-flow"


class TestIrToWaterfallSpec:
    def test_returns_dict_with_required_keys(self, ir_flow) -> None:
        spec = ir_to_waterfall_spec(ir_flow)
        assert "id" in spec
        assert "tenant" in spec
        assert "policy" in spec
        assert "tasks" in spec
        assert "edges" in spec

    def test_edge_preserved(self, ir_flow) -> None:
        spec = ir_to_waterfall_spec(ir_flow)
        assert len(spec["edges"]) == 1
        assert spec["edges"][0]["from"] == "fetch_context"
        assert spec["edges"][0]["to"] == "answer"

    def test_policy_fields(self, ir_flow) -> None:
        spec = ir_to_waterfall_spec(ir_flow)
        assert spec["policy"]["risk_level"] == "medium"
        assert spec["policy"]["requires_approval"] is False

    def test_single_task_no_edges(self) -> None:
        src = textwrap.dedent("""\
            version: 1
            id: "solo"
            tenant: "t"
            tasks:
              - name: "only"
                agent: "agent-x"
                input: {}
        """)
        ir = validate_and_normalize(parse_yaml(src))
        monolith_tasks = ir_to_monolith_tasks(ir)
        waterfall_spec = ir_to_waterfall_spec(ir)
        assert len(monolith_tasks) == 1
        assert waterfall_spec["edges"] == []
