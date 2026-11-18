# Local language-development qualification, 18 November 2026

Development began from checkpoint `aaa2ed3` on `codex/language-development`. The release reference `master` is `b09bbfc3dda4654cca2e9872423460667eed9498`. The language implementation is in `6d11326` and `11abad2`. The qualified source tree is `a22cf5f339cbe6249041070a2294b2e8b2d1317b`. Candidate builds retain the repository's 0.9.0 distribution metadata. Identify them by source commit and SHA-256.

## Language changes

- Fresh collection constructors can widen compatible scalar values. A writable alias retains its key, element and optional payload types. The checker requires writes to work for each known alternative. For a fully literal collection whose slots the checker still knows, a constant index or key can select an exact slot type. An unknown write, potential call or control-flow join drops that precision. Typed `fountain` field defaults use the same checks.
- Explicit runtime collection boundaries validate native contents and retain alias identity. Direct indexing, member writes, the standard mutation helpers, calls, returns, fields and nested optional payloads observe the retained constraints. Binding and mutation validate before publishing changes. Connected guest calls share constraints. On connection, existing obligations on overlapping identities are checked against live contents and propagated to newly reached objects. Separate host injection before the first connection and direct Python mutation are trusted embedding operations.
- `thirst::tscgb.encode` and `decode` make the version 1 text frame usable in a guest program. Encoding returns native bytes. Decoding accepts bytes or the integer-octet list used by the network library. It checks exact length, zero flags, CRC32, SHA-256 and strict UTF-8. The stream decoder recovers after a damaged frame and retains a partial magic prefix across chunks. CLI encoding preserves piped whitespace and line endings. Base-23 opcode encoding uses two digits per byte. Previously ambiguous one-digit control-byte sequences cannot be reconstructed uniquely from an old opcode stream.
- The wheel includes the data-report program and input. `scripts/verify_installed_language.py` runs the actual installed console launcher from a fresh working directory. It verifies report totals, malformed input, denied file access, valid and invalid aliased writes, an execution-step limit and the guest codec.
- The owner authorized examining the Conclave's TSCG-B behavior for this repository. The local comparison used its qualified `thirsty-lang` V0.9.0 installation and its `TSCGB_TEXT_V1` adapter function. Both directions preserved exact bytes for 0-, 5-, 11- and 65,535-byte UTF-8 payloads. The candidate uses Thirsty-Lang's own codec and adds no Conclave dependency.

## Qualification

The table records the candidate at `a22cf5f339cbe6249041070a2294b2e8b2d1317b`. The Ubuntu archive was exported with `git -c core.autocrlf=false archive`. Both environments used Node v25.9.0 for the executable JavaScript regressions.

| Check | Observed result |
| --- | --- |
| Windows, CPython 3.11.9, full suite | 5,458 passed, 1 POSIX-only skip, 22 subtests passed, 93.14% line coverage. |
| Ubuntu on WSL2, CPython 3.12.3, full suite | 5,458 passed, 1 Windows-only skip, 22 subtests passed, 93.00% line coverage. The POSIX private-key permission test ran here. |
| Code and type checks | Ruff passed. Black checked 171 files. Mypy passed for both `--platform win32` and `--platform linux`, 60 source files each. |
| Packaging and installation | Isolated PEP 517 build produced the sdist and a wheel built from that sdist. Windows and Ubuntu installed the wheel outside the checkout. Both passed `pip check`, the installed CLI checks and all three portable reference cases. |
| Installed application | The report produced 4 orders, 8 units and 8,900 cents with both category subtotals. Malformed JSON exited 1. A denied file read exited 2. Both error cases left stdout empty. The execution-limit, collection-alias and TSCG-B checks passed. |
| Conclave compatibility | Both directions passed on the installed Windows candidate against the Conclave's V0.9.0 codec and representation adapter. Cases covered empty input, control bytes, multibyte Unicode with surrounding whitespace, and the 65,535-byte limit. |
| Manual and API | Regenerated the API reference with pdoc. The 170-page manual has 376 outline entries. Its 20 text inputs produce the same source digest with LF and CRLF. Two rebuilds on each operating system reproduced the delivered PDF byte for byte. |

| Artifact | SHA-256 |
| --- | --- |
| `thirsty_lang-0.9.0-py3-none-any.whl` | `bc978c82735725a835356f2632de52b8f9dcaba0b4044a1038c4d6cf309640af` |
| `thirsty_lang-0.9.0.tar.gz` | `641f428606074f4f9433dba2cc8acd2233a235768b4b40202d7493ded19a7891` |
| Manual source manifest | `c742aa7eba84c1186259d27497a602f024337bf2149cbd5bf7a280eb14eca3bc` |
| `output/pdf/Thirsty-Lang-UTF-101.pdf` | `b4811e3813731c8d70948a58b5b27dda50ab3af2d19681bcd532dde4b973ca51` |

To reproduce the checks, run the following commands from the candidate checkout with the test, analysis and documentation dependencies installed. Run `pip check` and the last two commands with a Python environment holding the candidate wheel. Supply an existing scratch directory outside the checkout to the installed-program verifier. On this machine the checkout, build directories and scratch locations were on T:.

```text
python -m pytest tests -q -ra --cov=utf --cov-report=term --cov-fail-under=90
python -m ruff check src tests scripts/build_thirsty_lang_utf_101.py scripts/verify_installed_language.py docs/operations/fixtures/portable-collections/verify_reference.py
python -m black --check src tests scripts/build_thirsty_lang_utf_101.py scripts/verify_installed_language.py docs/operations/fixtures/portable-collections/verify_reference.py
python -m mypy -p utf --platform win32
python -m mypy -p utf --platform linux
python -m build
python -m pip check
python scripts/verify_thirsty_lang_utf_101.py --check-determinism
python -I scripts/verify_installed_language.py --work-dir <external-scratch-directory>
python -I docs/operations/fixtures/portable-collections/verify_reference.py
```

**Findings during qualification**

- Fixed the checker expectations for known alternatives and shared mutable values. Independent runtime review also found valid optional containers being rejected and an incomplete validation step when joining two interpreters. The regression suites exercise both cases.
- A Windows SQLite archive concurrency test hit its configured lock timeout once. It passed individually and in the next two complete Windows runs with the original timeout. Intermittent write contention remains a follow-up if it recurs.
- Fixed the original Ubuntu manual test failure. Its source manifest now canonicalizes CRLF to LF for the text inputs. Source edits, including whitespace and final-newline changes, still change the fingerprint.
- The original expansion checkout has 24 modified tracked and 34 untracked files, with an empty staging area. All 33 active code, documentation and test files match the saved checkpoint after normalizing text line endings and comparing the PDF byte for byte. The other 25 untracked files are the existing orchestration receipts and two release-alignment reports. The existing index lock remains in that checkout.
- The Edition XXII lexical check found 71 tokens and 58 unique tokens in the task prompt. The authentic dictionary data was unavailable, so dictionary verification remains unverified. This did not affect the language tests.

## Portable backend baseline at a22cf5f

The [portable collection fixtures](fixtures/portable-collections/) are three standalone pure modules. Run `python -I docs/operations/fixtures/portable-collections/verify_reference.py` with the installed candidate to check the reference outcomes. On the installed reference interpreter the valid write produced `main = 2`, and both names referred to the same list. The statically invalid write produced `E021` at line 4, column 1. A write through `Any` passed the checker and raised `TypeError` at runtime with the original list still `[1]` and the alias intact. `thirsty build --target js <fixture>` reported the same `E021` for the statically invalid module. For the other two it refused to build because the JavaScript host cannot enforce the default policy and authority. All three attempts produced zero JavaScript files.

1. Use the three committed modules as the first portable acceptance tests. Implement a host for the JavaScript target that can bind a policy and authority, with an executable test for a valid policy, a missing policy and a denied effect. Keep diagnostic locations tied to the original `.thirsty` source.
2. Run the modules through the installed compiler and the admitted JavaScript host. Match `main = 2`, the static rejection and the runtime rejection before mutation. Use a denied output operation to verify enforcement independently from the pure calculation.
3. Extend the corpus to a nested dictionary and then to the data-report workload. Record individual support for typed alias mutation, imports, JSON, bounded reads, denied effects and cleanup as each becomes available. Require the installed entry point on each platform to pass every case before claiming support for that workload.

The current work concerns the reference interpreter and package. Result, Task and Governed still lack general native guest representations for typed collection elements. Unknown annotation names and untyped foreign values retain their documented gradual behavior.

## Governed Node host follow-up

Local implementation commit `c97e67bbab3dccdf95055a5055b4668f63826c3b` on `codex/language-development` has tree `f79efe57067e1ae873d70816d2fccddd92344e0e`. The V0.9.0 release reference is `b09bbfc3dda4654cca2e9872423460667eed9498`. The commands below use the local development wheel and a host-selected TARL policy.

```text
thirsty build app.thirsty --target js --policy reader.tarl
thirsty run-js app.js --policy reader.tarl --authority reader
```

The installed launcher checks the artifact against the adjacent source and the selected policy, then sends the verified bytes to Node. Guest computation and indexed mutation run in JavaScript. Guest `pour` and host presentation of `main` require permission for `write stdout`. The installed Python helper uses the same TARL capability broker as the reference interpreter. The launcher supplies a host-selected subject with no identity proof or grants. A policy that requires an authenticated subject denies that caller. Signed authority, durable audit, filesystem access and network access are outside this Node profile.

| Installed compiler case | Expected and observed behavior |
| --- | --- |
| Valid typed list alias | Built successfully. The reader received `2` and exit 0. |
| Statically invalid list write | Build exited 1 with `E021` at line 4, column 1. No JavaScript or manifest was created. |
| Invalid write through `Any` | Built successfully. Execution exited 1 at line 4, column 1 with `requires Int` and empty stdout. A separate Node test inspected the original list and alias after the failed write. |
| Explicit guest output | The reader policy allowed the designated subject to print. The same compiled file and policy denied the visitor with exit 2 and empty stdout. |
| Missing or inconsistent bindings | Missing policy or authority failed. Changing either the selected policy or the executable bytes after compilation prevented launch. |

An additional installed Windows check ran `pour 1 / 0`. With output denied, the command returned 2, wrote nothing to stdout and reported `Governance denied: write stdout (DENY)` on stderr. When output was allowed it reached expression evaluation and reported `Division by zero` with exit 1.

Windows used Python 3.11.9 and Ubuntu used Python 3.12.3. Both used Node v25.9.0. The installed host verifier, installed language smoke test (including the data-report application and TSCG-B) and `pip check` passed on both. Mypy passed on 62 source files on each platform. Ruff passed, Black checked 173 files, and each platform reproduced the UTF 101 PDF SHA-256 `b6b632b3b527b06d8fa41859f36809d05559683480e291bb9bc08b474b42daa4`.

The first Windows full suite had three failures (5,531 passed, one platform skip, 93.00% coverage). One concurrent SQLite proof-archive write reached the configured lock timeout. Two data-report subprocesses exceeded 15 seconds. All three passed individually with the original limits. On the Windows full rerun, 5,532 passed, 22 subtests passed, one POSIX-only case was skipped and coverage reached 93.00%. The concurrent archive and end-to-end data-report tests again expired at their original limits. Both passed together in a focused run immediately afterward (19.85s). The next diagnostic is to time lock acquisition, commit and cold CLI startup on the Windows test volume under idle and competing I/O.

On Ubuntu, two disk-backed full runs had seven and three failures respectively. The archive lock timed out on both. Six standalone Node Boolean cases exceeded 10 seconds on the first run, and two malformed-declaration subprocesses exceeded five seconds on the second. The archive test passed on tmpfs, including all 48 writes and verification of the audit chain. A full run with tmpfs scratch passed all except three Node startup timeouts (5,531 passed).

With both the test scratch directory and a byte-identical copy of Node on tmpfs, the full Ubuntu suite passed 5,534 tests and 22 subtests, with one Windows-only skip and 92.89% coverage. The Node executable SHA-256 was `7fd113446e9171a28885227b3c275ff965b2fd1f45ccf1fb3a1c20308f34e627`. All full suites used the original test timeouts, SQLite settings and 90% coverage requirement. Installed-wheel checks on both platforms used ordinary disk storage.

The installed regression command is `python -I scripts/verify_installed_js_host.py --work-dir <external-scratch-directory>`. Local qualification used the same wheel on both platforms. The wheel SHA-256 is `2d6cc6e72a4133cb0a0b884ff49f43a89c7cf77c408dbcc6749d6088deb3d2ab`. The sdist SHA-256 is `4abb6a5cc8f756d7d107becda5b7d1b03fd9cf5f3e596ea8c131af301c72cae1`. Both retain 0.9.0 package metadata for local candidate testing.

The next portable workload is a nested dictionary. The data-report application also needs imports, JSON and policy-controlled file reads on the Node target.
