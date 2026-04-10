# Contributing

How to contribute to the Zero node. Read the project documentation before submitting changes.

---

## Before You Contribute

Read these documents:

- **[BUILD_ZERO.md](BUILD_ZERO.md)** -- Build from source
- **[TEST_ZERO.md](TEST_ZERO.md)** -- Run the test suite
- **[TODO.md](TODO.md)** -- Tracked work items

---

## Build and Test

1. Build: follow [BUILD_ZERO.md](BUILD_ZERO.md).
2. Run tests: `./contrib/run-tests.sh` (see [TEST_ZERO.md](TEST_ZERO.md)).
3. Before submitting, run **`./contrib/run-tests.sh --strict`** so any failed step exits non-zero (matches [`.github/workflows/tests.yml`](.github/workflows/tests.yml) on push/PR when CI is enabled).
4. Without **`--strict`**, the script may exit **0** even when a step logged **FAIL**--see [TEST_ZERO.md](TEST_ZERO.md) (Interpreting results).

---

## Submitting Changes

- Open an issue or PR on the project repository.
- Describe the change and rationale.
- Reference any related issues or TODO items.
- Keep changes focused; avoid mixing unrelated edits.

---

## Scope

Zero is a Zcash-family node. Contributions that improve build, test, or documentation are welcome. Protocol or consensus changes require broader review.
