# UTF Upstream Patch Series

This document records the actual commit topology discovered in the local Linguist mirror.

## What We Found

The local `integrations/linguist-test` repository is not a pristine clone of upstream `github/linguist`.
It already contains a UTF-related commit on `main`:

- `60d0b314` `Add support for Thirsty-lang`

That commit sits on top of upstream:

- `origin/main` -> `cfbfb7a8`

The newer UTF-family expansion work is one additional commit on top:

- `b8475fab` `Add UTF language entries and sample corpus`

## Why This Matters

It means the honest upstream filing sequence is:

1. Phase 1:
   file `60d0b314` against `github/linguist` `origin/main`
2. Phase 2:
   after Phase 1 is accepted or when the public-usage case is strong enough, file `b8475fab` on top

This is more credible than pretending the current UTF family split is the very first upstream ask.

## Patch Mapping

- Phase 1 rev range:
  - `origin/main..main`
- Phase 2 rev range:
  - `main..codex/utf-recognition-submission`

## Export

Use [export_upstream_series.py](./export_upstream_series.py) to generate a portable patch set from those exact ranges.
