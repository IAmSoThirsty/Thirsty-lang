# Draft: Add Support For The Universal Thirsty Family

This file is a ready-to-edit draft for an upstream `github/linguist` pull request.

---

## Summary

This PR adds support for `Thirsty-Lang`, the umbrella language of the Universal Thirsty Family (UTF), with a TextMate-compatible grammar and representative samples.

UTF currently spans the following internal language surfaces:

- Thirsty-Lang
- Thirst of Gods
- T.A.R.L.
- Shadow Thirst
- TSCG
- TSCG-B

For upstream GitHub Linguist support, this initial PR focuses on the shared family grammar and the strongest common language surface first.

## What This PR Adds

- a `languages.yml` entry for `Thirsty-Lang`
- a `source.thirsty` grammar mapping
- representative sample files
- extension coverage for the UTF family surface included in this phase

## Public Usage Evidence

GitHub search queries used for public usage validation:

- fill in from [SEARCH_QUERIES.md](./SEARCH_QUERIES.md)

Notes on usage distribution:

- replace this section with observations from manual result sampling across distinct `user/repo` combinations

## Sample Licensing

The sample files included for this submission are derived from the Thirsty-Lang repository and are MIT-licensed.
Source references are listed in [SAMPLE_INDEX.md](./SAMPLE_INDEX.md).

## Grammar Source

Grammar scope:

- `source.thirsty`

Representative grammar source in the UTF repository:

- `integrations/thirsty-lang-engine/vscode-extension/syntaxes/thirsty.tmLanguage.json`

## Additional Notes

UTF is maintained as a six-language family internally, but this submission intentionally stages public recognition to improve acceptance and reduce false positives in early adoption.
