# Thirsty-Lang

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square)](https://www.python.org/)
[![PyYAML](https://img.shields.io/badge/dep-PyYAML%206.0%2B-orange?style=flat-square)](https://pyyaml.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

**Sovereign Stack workflow definition language.** `thirsty_lang` parses `.tl.yaml` flow definitions, validates them, and compiles them to [Thirstys-Monolith](https://github.com/IAmSoThirsty/Thirstys-Monolith) task payloads or [Thirstys-Waterfall](https://github.com/IAmSoThirsty/Thirstys-waterfall) DAG specs.

---

## Pipeline

```
.tl.yaml source
       │ parse_yaml()
       ▼
  FlowDocument   (AST — grammar.py)
       │ validate_and_normalize()
       ▼
    IRFlow        (normalized IR — ir.py)
       │
       ├─ ir_to_monolith_tasks()  → List[dict]  → Supervisor.submit_task()
       └─ ir_to_waterfall_spec()  → dict         → Waterfall DAG engine
```

**Single runtime dependency:** `pyyaml>=6.0.1`.

---

## Flow Definition Format

Flows are YAML files (`.tl.yaml`):

```yaml
version: 1
id: "rag-pipeline"
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
  risk_level: "medium"       # low | medium | high | critical
  requires_approval: false
  retention: "30d"           # optional
```

**Validation rules:**

- `id` and `tenant` must be non-empty.
- Task `name` and `agent` must be non-empty; names must be unique.
- `edge.from` and `edge.to` must reference known task names.
- `risk_level` must be one of `low`, `medium`, `high`, `critical`.
- `timeout_ms` must be > 0.
- The task graph must be a DAG (cycles are rejected).

---

## Quick Start

```bash
pip install -e ".[dev]"   # PyYAML + pytest, ruff, mypy, …
pytest -q                 # 27 tests across parser, validator, compiler
```

```python
from thirsty_lang import parse_yaml, validate_and_normalize, ir_to_monolith_tasks, ir_to_waterfall_spec

src = open("flow.tl.yaml").read()
doc = parse_yaml(src)                   # → FlowDocument (AST)
ir  = validate_and_normalize(doc)       # → IRFlow (validated, cycle-free)

# Compile to Monolith
tasks = ir_to_monolith_tasks(ir)        # → [{"meta": {...}, "agent": ..., "input": ...}, ...]

# Compile to Waterfall
spec  = ir_to_waterfall_spec(ir)        # → {"id": ..., "tasks": [...], "edges": [...], ...}
```

### End-to-End with Monolith

```python
from thirsty_lang import parse_yaml, validate_and_normalize, ir_to_monolith_tasks
from monolith import Supervisor, load_config

ir = validate_and_normalize(parse_yaml(open("flow.tl.yaml").read()))

with Supervisor(load_config()) as sup:
    for payload in ir_to_monolith_tasks(ir):
        sup.submit_task(payload)
    results = sup.collect_results(timeout=5.0)
```

---

## Package Structure

```
src/thirsty_lang/
  __init__.py    # public API: parse_yaml, validate_and_normalize, ir_to_*
  errors.py      # ThirstyLangError, ParseError, ValidationError, CompileError
  grammar.py     # AST types: FlowDocument, TaskNode, Edge, Policy
  parser.py      # parse_yaml() — YAML → FlowDocument
  ir.py          # IRFlow, IRTask, IREdge, IRPolicy
  validator.py   # validate_and_normalize() — static rules + DAG cycle check
  compiler.py    # ir_to_monolith_tasks() / ir_to_waterfall_spec() + topo sort
  examples/
    hello_world.tl.yaml   # retriever → LLM two-step RAG pipeline
```

---

## Error Handling

| Exception | When |
|---|---|
| `ParseError` | Invalid YAML syntax or missing required top-level fields |
| `ValidationError` | Empty names, unknown edge refs, bad `risk_level`, cycle, `timeout_ms ≤ 0` |
| `CompileError` | Future: compilation target constraints |

All are subclasses of `ThirstyLangError`.

---

## Development

```bash
pip install -e ".[dev]"

pytest -q                  # run tests
ruff check src/ tests/     # lint
mypy src/thirsty_lang/     # type-check
pip-audit                  # dependency audit
```

---

## License

MIT © Thirsty-Lang Team
