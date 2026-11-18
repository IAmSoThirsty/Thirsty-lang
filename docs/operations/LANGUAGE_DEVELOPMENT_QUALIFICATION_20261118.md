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

## Next general-purpose increment

The [portable collection fixtures](fixtures/portable-collections/) are three standalone pure modules. Run `python -I docs/operations/fixtures/portable-collections/verify_reference.py` with the installed candidate to check the reference outcomes. On the installed reference interpreter the valid write produced `main = 2`, and both names referred to the same list. The statically invalid write produced `E021` at line 4, column 1. A write through `Any` passed the checker and raised `TypeError` at runtime with the original list still `[1]` and the alias intact. `thirsty build --target js <fixture>` reported the same `E021` for the statically invalid module. For the other two it refused to build because the JavaScript host cannot enforce the default policy and authority. All three attempts produced zero JavaScript files.

1. Use the three committed modules as the first portable acceptance tests. Implement a host for the JavaScript target that can bind a policy and authority, with an executable test for a valid policy, a missing policy and a denied effect. Keep diagnostic locations tied to the original `.thirsty` source.
2. Run the modules through the installed compiler and the admitted JavaScript host. Match `main = 2`, the static rejection and the runtime rejection before mutation. Use a denied output operation to verify enforcement independently from the pure calculation.
3. Extend the corpus to a nested dictionary and then to the data-report workload. Record individual support for typed alias mutation, imports, JSON, bounded reads, denied effects and cleanup as each becomes available. Require the installed entry point on each platform to pass every case before claiming support for that workload.

The current work concerns the reference interpreter and package. Result, Task and Governed still lack general native guest representations for typed collection elements. Unknown annotation names and untyped foreign values retain their documented gradual behavior.
