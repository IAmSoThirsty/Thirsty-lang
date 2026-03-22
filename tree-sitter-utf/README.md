# tree-sitter-utf

This is the Tree-sitter grammar scaffold for the Universal Thirsty Family.

It is intended to give UTF a structural tooling lane for:

- symbol extraction
- semantic highlighting
- code navigation
- parser-backed editor integrations
- future AI and IDE ingestion

## Scope

The scaffold covers the shared UTF surface:

- Thirsty-Lang
- Thirst of Gods
- T.A.R.L.
- Shadow Thirst
- TSCG
- TSCG-B

## Current State

- `grammar.js` defines the core syntax family
- `queries/highlights.scm` maps syntax nodes to highlight categories
- `queries/tags.scm` exposes functions and classes for tag generation
- `queries/locals.scm` provides a starting point for local symbol reasoning

## Next Step

To turn this into a production parser, generate and validate the parser with `tree-sitter-cli`, then expand the grammar against real UTF programs until the sample corpus parses cleanly.
