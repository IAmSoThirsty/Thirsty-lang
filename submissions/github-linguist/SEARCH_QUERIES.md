# UTF Search Queries For GitHub Linguist Evidence

These are the candidate GitHub searches to use when gathering the public-usage evidence required by Linguist.

## Core Query Pattern

Use GitHub code search with fork filtering disabled from the results set:

- `NOT is:fork`

Then inspect both the count and the distribution across distinct repositories.

## Candidate Queries

- `.thirsty`
  - [GitHub search](https://github.com/search?q=extension%3Athirsty+NOT+is%3Afork&type=code)
- `.thirstyplus`
  - [GitHub search](https://github.com/search?q=extension%3Athirstyplus+NOT+is%3Afork&type=code)
- `.thirstyplusplus`
  - [GitHub search](https://github.com/search?q=extension%3Athirstyplusplus+NOT+is%3Afork&type=code)
- `.thirstofgods`
  - [GitHub search](https://github.com/search?q=extension%3Athirstofgods+NOT+is%3Afork&type=code)
- `.tog`
  - [GitHub search](https://github.com/search?q=extension%3Atog+NOT+is%3Afork&type=code)
- `.tarl`
  - [GitHub search](https://github.com/search?q=extension%3Atarl+NOT+is%3Afork&type=code)
- `.shadow`
  - [GitHub search](https://github.com/search?q=extension%3Ashadow+NOT+is%3Afork&type=code)
- `.tscg`
  - [GitHub search](https://github.com/search?q=extension%3Atscg+NOT+is%3Afork&type=code)
- `.tscgb`
  - [GitHub search](https://github.com/search?q=extension%3Atscgb+NOT+is%3Afork&type=code)

## What To Record

For each extension, record:

1. the reported file count
2. whether the results are concentrated in a single owner or broadly distributed
3. whether the files appear to be real UTF code rather than incidental collisions
4. whether the extension is strong enough to justify a standalone public language entry

## Filing Advice

If only `.thirsty` shows broad public usage, file the first PR as `Thirsty-Lang` and keep the other family members for a later phase.
