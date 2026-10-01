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

1. Build from source as described in [BUILD_ZERO.md](BUILD_ZERO.md).
2. Make the change.
3. Run the merge gate: `./contrib/run-tests.sh --strict`. Without `--strict` the runner may exit 0 after a failed step.
4. Push the branch and open the pull request.


---

## Coding

Code style and threading conventions follow the upstream Bitcoin Core and Zcash developer notes. Consensus and subsidy code is integer-only and must stay consistent across the miner, block validation, block templates, and RPC. Upstream, vendored, and ported code keeps its original comments and stays close to upstream so later merges remain clean.

---

## Testing

The node has three test layers: GTest (`src/zero-gtest`), Boost (`src/test/test_bitcoin`), and Python RPC tests (`qa/rpc-tests`). Test runners, tiers, and how to interpret results are in [TEST_ZERO.md](TEST_ZERO.md). Bug fixes should include a test that fails without the fix where practical.

---

## Continuous integration

`.github/workflows/tests.yml` runs `./contrib/run-tests.sh --strict` on pushes and pull requests when CI is enabled for the repository.

---

## Release versioning and process

Versions follow `MAJOR.MINOR.PATCH`, with release candidates tagged before the final release. The release lifecycle -- version bump, build, tag, packaging, checksums, and signatures -- is described in [BUILD_ZERO.md](BUILD_ZERO.md).

---

## License

Contributions are licensed under the MIT license in [COPYING](COPYING).
