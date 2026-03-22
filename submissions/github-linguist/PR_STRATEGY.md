# UTF Upstream PR Strategy

## Executive Judgment

UTF can be modeled as six official languages in this repository.
That is useful for internal governance, editors, and long-term ecosystem clarity.

For upstream GitHub Linguist acceptance, the safer first move is likely a staged approach:

1. Phase 1:
   submit `Thirsty-Lang` as the umbrella language with the strongest evidence and the shared `source.thirsty` grammar.
2. Phase 2:
   once public usage is broader and more distributed, propose explicit family splits for:
   - Thirst of Gods
   - T.A.R.L.
   - Shadow Thirst
   - TSCG
   - TSCG-B

## Why This Is the Safer Path

- GitHub Linguist evaluates public extension usage.
- A single family brand is easier to justify than six low-volume, adjacent new languages.
- UTF already shares one grammar surface and one conceptual lineage.
- Grouping first reduces the risk that a broad family submission is rejected for insufficient per-extension evidence.

## Internal vs Upstream Truth

Internal truth in this repo:

- UTF consists of six official languages.

Upstream strategy truth:

- the first accepted GitHub representation may need to be narrower than the full family model.

That is not surrendering the architecture.
It is sequencing recognition so the public ecosystem can ingest UTF in stages.

## Confirmed Local Commit Series

The local Linguist mirror now confirms this staging is not hypothetical.
There is already a Phase 1 commit on the mirror's `main` branch:

- `60d0b314` `Add support for Thirsty-lang`

And the UTF family expansion is the next layer on top:

- `b8475fab` `Add UTF language entries and sample corpus`

That makes the filing sequence concrete:

1. upstream Phase 1 first
2. upstream Phase 2 only after the ecosystem and evidence justify it

## Phase 1 Candidate

The Phase 1 ask should most likely be:

- Language name: `Thirsty-Lang`
- Shared grammar scope: `source.thirsty`
- Primary extensions:
  - `.thirsty`
  - possibly `.thirstofgods`
  - possibly `.tog`
  - possibly `.tarl`
  - possibly `.shadow`
  - possibly `.tscg`
  - possibly `.tscgb`

This depends on public-usage evidence gathered through the search queries in [SEARCH_QUERIES.md](./SEARCH_QUERIES.md).

## Phase 2 Candidate

If public usage becomes broad enough, propose grouped family entries:

- `Thirst of Gods`
- `T.A.R.L.`
- `Shadow Thirst`
- `TSCG`
- `TSCG-B`

Each would continue to point at the shared grammar initially, with later grammar or parser specialization only if the language surfaces meaningfully diverge.

## Filing Rule

Do not file the six-language split as the first public PR unless the GitHub search evidence is clearly strong across the family.
