# UTF External Recognition

This document is the canonical handoff for making the Universal Thirsty Family legible to external services.

## What This Repo Can Do Today

- Define the six official UTF languages in a canonical registry.
- Register UTF file extensions for repository-level GitHub Linguist overrides through `.gitattributes`.
- Expose six discrete language identifiers to editor tooling through the VS Code extension manifests.
- Provide representative sample corpora for local Linguist validation and future upstream submission.
- Provide a Tree-sitter parser scaffold and queries for structural tooling.

## What Still Requires External Approval

No repository can unilaterally force GitHub, Google, OpenAI, or any other outside platform to declare a language "official".
What we can do is provide the artifacts those platforms require:

One important boundary: `.gitattributes` can override classification to a language a target platform already knows, but it cannot by itself teach GitHub.com a brand-new language name that has not been added to that platform's Linguist build.

- GitHub language statistics and syntax classification:
  - a language entry in Linguist `languages.yml`
  - a compatible TextMate grammar
  - representative sample files
  - an upstream pull request showing in-the-wild usage
- Editor and IDE support:
  - language ids
  - extension-to-language mappings
  - language configuration
  - syntax grammar and snippets
- Deeper code intelligence:
  - a Tree-sitter parser and queries for navigation, symbols, and structure-aware tooling

## Canonical UTF Surface

The canonical registry lives at [utf_language_registry.json](./utf_language_registry.json).

The six official UTF languages are:

1. Thirsty-Lang
2. Thirst of Gods
3. T.A.R.L.
4. Shadow Thirst
5. TSCG
6. TSCG-B

## Key Artifacts

- GitHub overrides:
  - [../../.gitattributes](../../.gitattributes)
  - [./.gitattributes](./.gitattributes)
- UTF language manifest:
  - [./languages.yml](./languages.yml)
- VS Code / IDE registration:
  - [./vscode-extension/package.json](./vscode-extension/package.json)
  - [./thirsty-extension/package.json](./thirsty-extension/package.json)
  - [./vscode-extension/syntaxes/thirsty.tmLanguage.json](./vscode-extension/syntaxes/thirsty.tmLanguage.json)
- Tree-sitter scaffold:
  - [./tree-sitter-utf/grammar.js](./tree-sitter-utf/grammar.js)
  - [./tree-sitter-utf/tree-sitter.json](./tree-sitter-utf/tree-sitter.json)
  - [./tree-sitter-utf/queries/highlights.scm](./tree-sitter-utf/queries/highlights.scm)
  - [./tree-sitter-utf/queries/tags.scm](./tree-sitter-utf/queries/tags.scm)
- Local Linguist mirror for submission rehearsal:
  - [../linguist-test/lib/linguist/languages.yml](../linguist-test/lib/linguist/languages.yml)
  - [../linguist-test/vendor/grammars/thirsty.tmLanguage.json](../linguist-test/vendor/grammars/thirsty.tmLanguage.json)
  - [../linguist-test/samples](../linguist-test/samples)
- Submission bundle:
  - [./submissions/github-linguist/README.md](./submissions/github-linguist/README.md)
  - [./submissions/github-linguist/PR_STRATEGY.md](./submissions/github-linguist/PR_STRATEGY.md)
  - [./submissions/github-linguist/PULL_REQUEST_DRAFT.md](./submissions/github-linguist/PULL_REQUEST_DRAFT.md)

## Submission Notes

For GitHub upstream inclusion, the practical sequence is:

1. Keep UTF metadata stable in the canonical registry.
2. Use the local Linguist mirror to validate language names, extensions, grammar coverage, and sample shape.
3. Add or refine representative samples from real UTF projects.
4. Submit the corresponding changes upstream to `github/linguist`.
5. Expect GitHub search and some downstream services to lag behind Linguist even after merge.

Relevant platform references:

- GitHub language support: [docs.github.com/get-started/learning-about-github/github-language-support](https://docs.github.com/get-started/learning-about-github/github-language-support)
- VS Code language identifiers: [code.visualstudio.com/docs/languages/identifiers](https://code.visualstudio.com/docs/languages/identifiers)

## Next Frontier

The remaining major unlock for advanced external tooling is a production-grade Tree-sitter parser for UTF.
This repo now includes a scaffold for that work, which is the path from syntax coloring to structural indexing, symbol extraction, semantic navigation, and richer AI/editor support.
