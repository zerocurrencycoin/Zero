# Contributing to Zero

Zero is a fork of Zcash, which is itself a fork of Bitcoin Core. This document follows the structure of the [Zcash Development Guidelines](https://zcash.readthedocs.io/en/latest/rtd_pages/development_guidelines.html): the GitHub workflow for proposing a change, the local developer workflow, and where coding, testing, and release conventions are defined.

---

## GitHub workflow

### Fork and connect to upstream

Fork `zerocurrencycoin/Zero` on GitHub, clone your fork, and add the project repository as `upstream`:

```bash
git clone https://github.com/<you>/Zero.git
cd Zero
git remote add upstream https://github.com/zerocurrencycoin/Zero.git
```

### Create a branch

`master` must always build and pass the merge gate. Create a descriptively named topic branch from `master` for each change.

### Make and commit changes

Keep commits focused; each commit should build and pass tests on its own. Use a short imperative subject line (about 50 characters), a blank line, and a body wrapped at 72 characters that explains what changed and why. Reference related issues by number. Do not add co-author or attribution trailers. Rebase on `upstream/master` before opening a pull request to keep merge conflicts small.

Ports from Zcash or Bitcoin Core name the upstream commit or pull request and stay close to the upstream diff.

### Create a pull request

Describe the change, its motivation, and how it was tested. Keep each pull request to one topic; do not mix refactoring, formatting, and behavior changes. Mark unfinished work as a draft. Consensus changes (block validity, subsidy, proof verification, network upgrades) need broader review and an activation plan.

### Discuss and review

Anyone may review. Reviewers state what they checked, using the terms common to Bitcoin Core and Zcash:

| Term | Meaning |
|------|---------|
| Concept ACK | Agrees with the goal; code not reviewed |
| utACK | Code reviewed, not tested |
| Tested ACK | Code reviewed and tested |
| NACK | Disagrees; must give a reason |

Address feedback with additional commits, then squash when a maintainer asks.

### Merge

Maintainers merge once review concerns are resolved and the merge gate passes.

---

## Developer workflow

1. Build from source per BUILD_ZERO "Build".
2. Make the change.
3. Run the merge gate, TEST_ZERO "Run".
4. Push the branch and open the pull request.


---

## Coding

Code style and threading conventions follow the upstream Bitcoin Core and Zcash developer notes. Consensus and subsidy code is integer-only and must stay consistent across the miner, block validation, block templates, and RPC. Upstream, vendored, and ported code keeps its original comments and stays close to upstream so later merges remain clean.

### Shell scripts

Scripts start with `#!/usr/bin/env bash` and must give the same result under bash 3.2 (macOS `/bin/bash`) and bash 5 (Linux; Homebrew on macOS, first on `PATH` when installed). `#!/bin/bash` always runs 3.2 on macOS. Constructs that differ:

- `~` or quotes in the replacement of `${var/pattern/replacement}`: bash 5 expands `~` to the home directory, and bash 3.2 keeps quotes and backslashes literally, so no spelling of `${VERSION/-/~}` works in both. Use `sed` or `tr`.
- Bash 4 features (`declare -A`, `mapfile`, `${var,,}`): absent in 3.2.

Check a script under both: `/bin/bash script.sh` and `/opt/homebrew/bin/bash script.sh` on macOS.

### Options and defaults

The code is the only source of `zerod` options and their defaults: `HelpMessage` in `src/init.cpp` prints each default from the constant the code uses, so a default changes in one place. A new or changed option needs its help line and an updated `doc/Options.csv` row (`contrib/tools/inventory-check.py --apply`) in the same change; `contrib/zero.conf` and `contrib/conf-templates/` are written by hand and show the help-text default, so a changed default is updated there too. The man pages are regenerated at the next version change (`contrib/devtools/gen-manpages.sh`).

### Development fee naming

Zero's 7.5% development fee runs on the founders-reward code inherited from Zcash. Zcash's founders reward is a different payment, so new text never calls Zero's fee a founders reward.

| Text | Name used |
|------|-----------|
| Documents, help text, log and error messages, comments in Zero-written code, Zero's Python test helpers (`dev_fee_share`, `REGTEST_DEV_FEE_START`) | "development fee" |
| C++ identifiers inherited from Zcash (`GetFoundersRewardAmount`, `vFoundersRewardAddress`, `GetLastFoundersRewardBlockHeight`, `txoutFounders`, `REGTEST_FOUNDERS_START`) | Unchanged: renaming touches consensus code and moves away from upstream |
| RPC field names and values, block reject reasons, listed in ZERO_COIN "Coinbase split" | Unchanged: pools and clients parse them |
| Upstream code and its comments, published release notes | Unchanged |

Text that names an unchanged identifier or field gives both once: "the development fee (`founders`)".

### Vendored subtrees

`src/leveldb`, `src/secp256k1`, and `src/univalue` match the upstream commits recorded by `git subtree` (`contrib/devtools/git-subtree-check.sh`), except for changes required to build or run, listed here. Code derived from Bitcoin Core and Zcash outside these subtrees keeps the upstream names and comments, so it compares and merges against upstream with small diffs.

| Subtree | File | Change | Reason |
|---------|------|--------|--------|
| `src/secp256k1` | `src/tests.c` | `shortkey` zero-initialized | GCC `-Wmaybe-uninitialized` on Ubuntu 24.04; upstream made the same change |

---

## Testing

A bug fix includes a test that fails without the fix where practical, and every change passes the merge gate. Test layers, runners, and tiers: TEST_ZERO.

---

## Continuous integration

`.github/workflows/tests.yml` builds on Ubuntu 24.04 and runs `./contrib/run-tests.sh --strict` on pushes to `master`, `main`, and `develop` and on pull requests; pushes to a release branch such as `zero-410` do not start it.

---

## Release versioning and process

Versions follow `MAJOR.MINOR.PATCH`, with release candidates tagged before the final release. The release lifecycle -- version bump, build, tag, packaging, checksums, and signatures -- is in BUILD_ZERO "Release".

---

## License

Contributions are licensed under the MIT license in [COPYING](COPYING).
