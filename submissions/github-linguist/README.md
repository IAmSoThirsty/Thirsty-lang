# UTF GitHub Linguist Submission Bundle

This bundle is the handoff for an upstream `github/linguist` submission.

It is designed to answer four practical questions:

1. What is UTF, exactly?
2. What should the first upstream PR ask for?
3. What evidence is already present in this repo?
4. What evidence still has to be gathered from GitHub before filing?

## Included Documents

- [PR_STRATEGY.md](./PR_STRATEGY.md)
- [PULL_REQUEST_DRAFT.md](./PULL_REQUEST_DRAFT.md)
- [SEARCH_QUERIES.md](./SEARCH_QUERIES.md)
- [SAMPLE_INDEX.md](./SAMPLE_INDEX.md)
- [build_submission_bundle.py](./build_submission_bundle.py)
- [UPSTREAM_SERIES.md](./UPSTREAM_SERIES.md)
- [export_upstream_series.py](./export_upstream_series.py)

## What Is Ready

- UTF language registry
- Linguist-compatible language definitions
- TextMate grammar hookup
- local Linguist rehearsal mirror
- representative sample corpus
- editor registration for six UTF language ids
- Tree-sitter scaffold for future structural tooling

## What Still Requires External Validation

GitHub Linguist acceptance depends on public usage evidence, not just internal correctness.
That means the final submission still needs GitHub search evidence for the relevant extensions and a judgment call about whether UTF should enter upstream as one umbrella language first or as a six-language family.

## Recommended Starting Point

Start with the strategy in [PR_STRATEGY.md](./PR_STRATEGY.md).

## Reproducible Export

To build a portable submission bundle from the current UTF assets:

```bash
python build_submission_bundle.py --phase phase-1
python build_submission_bundle.py --phase phase-2
```

`phase-1` builds the safer umbrella-language bundle.
`phase-2` builds the full six-language UTF bundle for later filing rounds.

To export the actual Linguist patch series discovered in the local mirror:

```bash
python export_upstream_series.py
```

That will emit:

- the Phase 1 upstream patch: `origin/main -> main`
- the Phase 2 follow-on patch: `main -> codex/utf-recognition-submission`
