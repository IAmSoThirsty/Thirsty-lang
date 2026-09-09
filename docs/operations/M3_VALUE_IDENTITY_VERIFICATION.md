# M3.5 constructor and governed value identity: verification

Date: 2026-09-08. Repository: `T:\01-Projects\thirsty_lang_exploration_0754`.
Branch: `codex/function-expansion-pack`.
Base HEAD: `b09bbfc3dda4654cca2e9872423460667eed9498`.
Metadata remains 0.9.0; cumulative M3.1-M3.5 work is local and unreleased.

## Status

**4,868 passed, 1 skipped, 22 subtests passed; 92.48% statement coverage.**
All 99 discovered test modules are represented, with no failures or errors.
All seven full-suite/quality gates and installed-package verification passed.
The rebuilt manual passes structural, deterministic, and visual checks. This
closes the local M3.5 increment. Earlier increment totals do not validate
this source. The broader language vision and M3-M7 remain open; robotics remains
deferred. No release, version change, rename, or remote operation occurred.

## Scope

| Surface | Correction and consequence |
|---|---|
| Nominal constructors | `ConstructorType` preserves declaration identity through aliases, annotations, collections, and callable alternatives. A constructor and its instance no longer share one descriptor. |
| Calls and member access | Known noncallables report E031; constructor signatures check argument count/types. Struct fields require instances and enum variants require constructors. `new` follows runtime callable semantics. |
| Pipes and cascade | Constructor aliases retain argument/result typing. Noncallable pipe fallback remains. Cascade infers the actual runtime result and evaluates a rejected dynamic callee/arguments once. |
| Governed values | Owned, bounded JSON projection tags registered struct/fountain/enum values with a session-scoped declaration identity and all declared fields or the enum variant. Existing JSON policy paths are preserved. |
| Call integrity | Bound receivers participate. Entry/exit snapshots are checked after callback-capable authorization work. Positive policy proofs must bind the original context submitted to that policy. |
| Failure certificates | Rejected native/host values cannot receive ALLOW with rejected normalization metadata. Projection failure produces a bounded diagnostic DENY without invoking representation/copy hooks on the rejected object. |
| Reserved names | Raw native metadata key segments cannot impersonate runtime metadata. A governed parameter named `result` denies before entry because it conflicts with the exit result binding. |
| Parameter bindings | Duplicate parameter names report E010 and cannot silently overwrite bindings at runtime. Method arguments cannot replace the implicit `this` receiver; initializer validation precedes defaults. |
| Manual layout | Running headers follow the first heading placed on a page, landscape furniture uses the active page size, and heading chains remain with wide tables. |

## Evidence

Current evidence root: `.tmp/m3-values-20260908-01/`.
Governed-value investigation: `.tmp/m3-governed-values-20260909-01/`.
Historical M3.1-M3.4 records and artifacts remain preserved.

Independent review reproduced a connected receiver bypass after the initial
projection tests passed: `take(self, self)` let policy inspect the supplied
object with value 1 while the method's actual `this` object returned 99 with
ALLOW. Packaging paused before any candidate build. The reproduction and
nine-case source/AST matrix are preserved under `review/` in the evidence root.
This finding required runtime binding guards and checker diagnostics, including
valid controls for ordinary nonleading `self` parameters. Source already rejects
`this` as a parameter keyword; explicit leading `this` is an AST embedding
convention. The regression distinguishes those interfaces.

### Full local validation

The repository virtual environment is Python 3.11.9; imports resolve to this
checkout's `src/utf`. The helper `.tmp/m3-values-20260908-01/verify.py final`
records every command, exit status, and duration in `final/checks.json`, plus
complete logs, JUnit, XML/JSON coverage, and a module inventory in `final/`.

| Gate | Command / result |
|---|---|
| Complete suite | `python -m pytest tests -q -ra --cov=utf --cov-fail-under=90` with XML/JSON/JUnit outputs, disabled pytest cache, and fresh project-specific scratch: 4,868 passed, 1 skipped, 22 subtests in 82.18 seconds. |
| Coverage | 12,537 / 13,556 statements; 1,019 missing; 22 excluded lines unchanged. Exact percentage 92.48303334316908. |
| Lint | `python -m ruff check src tests`: passed. |
| Formatting | `python -m black --check src tests`: all 160 files unchanged. |
| Types | `python -m mypy -p utf --platform win32` and `--platform linux`: both passed, 59 source files each. The Linux option checks types; this was not a Linux runtime execution. |
| Dependencies | `python -m pip check`: no broken requirements. |
| Diff | `git diff --check`: passed. |

The only skip is `test_keystore.test_private_key_file_is_0600`, which checks
POSIX file modes. Scratch is
`T:\Temp\thirsty-lang-m35-full-896e28d46cce46b0997db4d779690971`, the ordinary
Windows temporary location on the same T: volume. No archive timeout or test
assertion was weakened. This complete M3.5 run passed on its first attempt.

The five new conformance modules contain constructor (103), cascade (46),
governed-value integrity (272), projection (81), and parameter-binding (36)
cases. Eight PDF regressions bring the total increase over M3.4 to 546 cases.
Focused test failures exposed stale unsupported-value error expectations,
bare Mock values implicitly returned by callback fixtures, missing statement
separators before array expressions, and source fixtures using the reserved
`this` keyword as a parameter. Fixtures now preserve the intended assertions
and distinguish valid host AST conventions from source syntax. These issues
are fixed now; no admission or negative security assertion was weakened.

Tracked and newly added files are checked with the repository pre-commit
hooks. Generated API HTML required the existing whitespace/end-of-file
normalization hooks; the corrected tracked-file run passed. API generation
used `python -m pdoc utf` with the absolute repository `docs/src` output path.

### Package verification

`package/package_check.py --source-frozen` built an isolated candidate and
ran Twine checks, installation, and installed-target smoke checks. All 78
selected source/fixture/metadata inputs match the frozen checkpoint. Every
one of the 57 shipped Python files matches working source, snapshot, sdist,
wheel, and installation byte for byte, including `governed_values.py`.
The final source drift check passed after the full suite.

Installed checks cover all six tier imports, seven console-entrypoint metadata
dispatches, 33 M3.5 cases, and the prior security, callable, iteration, arity,
semantic/formatting, rejection, proof, and required-archive smoke cases.
The 16 stdlib namespaces retain 43 classified effect exports and 56 exports
without ambient effects. These checks use an isolated installed import target
and repository virtual-environment dependencies; they do not prove a clean
machine installation or exercise native Windows console launchers.

| Artifact | SHA-256 |
|---|---|
| Wheel | `9df834fd817549a93bbfea5230cfa6601847e2bc3851f2951ee487cdddb55271` |
| Sdist | `75115d3045fda40055919d9a1924679f9407ac16a3edebc4b9263297b72fd6ff` |
| Runtime source integrity | `sha256-590095a5d08f5af0d886f2dae72db892c3dd067aa884d288147171c8892a3a97` |

These are unpublished cumulative M3.5 artifacts retaining 0.9.0 metadata;
they are not the previously published PyPI 0.9.0 distribution.

### Manual and artifact verification

The current manual includes 17 repository documents, with its builder and
composition manifest bound into the source digest. It contains 161 pages
(145 portrait, 16 landscape), 361 outlines, and 487,022 extracted characters.
Structural checks report no errors or warnings and all 161 pages rendered.
A deterministic rebuild produced identical bytes. All 74,848 extracted word
boxes remain inside their page boundaries within the 0.5-point tolerance.

| Artifact | SHA-256 |
|---|---|
| Final PDF | `e38e897c2b0ee8fc92cf397c684f6da6e3664867ac3cbee40342451e6160d2bb` |
| Manual source set | `abe68e04e7b5dfbec0f4bec07473cb09633c728aa5eb3250b4bad51a0855d064` |

Initial visual review found two empty transition pages after moving headings
with wide tables. Adjacent tables had generated a portrait reset immediately
followed by another landscape transition. The builder now coalesces that
redundant reset, keeps each table on its own landscape page, and returns
following prose to portrait. Four regressions cover headed/unheaded transitions
and single/split first tables. The first 163-page PDF, builder, and QA remain
preserved; `pdf-final/` records the corrected artifact's checks.

Final visual review inspected all 161 pages through six contact sheets and
14 detailed renders. It found no remaining body-empty pages, clipping, or
overlap. All 161 retained pages preserve their ordered body text after the
documented furniture, whitespace, contents-page-number, and source/builder
digest normalization. The agent receipt identifies its 11 detailed pages;
root additionally inspected the cover, page 17, and the final provenance page.

### Changed surfaces and preservation

M3.5 package-source changes are limited to `__init__.py`, `checker.py`,
`diagnostics.py`, `governed_values.py`, `interpreter.py`, and `typesys.py` under
`src/utf/thirsty_lang`. Test changes include the five new modules above,
callable type/arity expectations, and PDF regressions. Active plan, feature,
specification, general-purpose, native context, manual, continuity, and
generated API documents reflect the implementation. Historical verification
records remain unchanged.

The checkout retains 97 cumulative dirty paths, with no deletion or rename.
All paths and added content were checked for unintended project crossover;
none was found. Current source, test, package, and PDF evidence remains local
to this repository, apart from its explicitly recorded generated test scratch.

## Remaining issues and boundaries

- Requires separate follow-up work: broader type soundness, mixed constructor
  and instance joins, Task representation, callable/foreign/tuple/bytes governed
  profiles, resource ownership and cancellation, portable code provenance,
  deterministic execution replay, and independent acceptance.
- Requires separate follow-up work: canonical JSON hashes ignore dictionary
  insertion order and alias identity. Callback checks do not detect order-only
  or mutate-restore histories and are not an atomic concurrent-memory boundary.
- Not blocking this increment: body or callback effects already performed are
  not rolled back by a later denial. Python embedding and injected callbacks
  remain trusted; private runtime metadata is not unforgeable against the host.
- Environment/dependency observation: M3.4 recorded one archive timeout and an
  HTML write error, both followed by successful unchanged checks. Their causes
  remain unproven; that history is not reclassified as repaired storage.
- No remote publication, workflow dispatch, version change, new repository,
  rename, or cross-project import is part of this increment.
