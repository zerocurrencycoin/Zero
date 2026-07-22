*** Warning: This document may be incomplete for Zero; verify paths against BUILD_ZERO.md. ***

Wallet Tools
---------------------

### [BitRPC](/contrib/bitrpc) ###
Interactive Python helper for JSON-RPC commands (uses mainnet RPC port 23811 by default).

### [SpendFrom](/contrib/spendfrom) ###

Use the raw transactions API to send coins received on a particular
address (or addresses).

Repository Tools
---------------------

### [Developer tools](/contrib/devtools) ###
Specific tools for developers working on this repository.
Contains the script `github-merge.sh` for merging github pull requests securely and signing them using GPG.

### [Verify-Commits](/contrib/verify-commits) ###
Tool to verify that every merge commit was signed by a developer using the above `github-merge.sh` script.

### [Linearize](/contrib/linearize) ###
Construct a linear, no-fork, best version of the blockchain. RPC `port` in the cfg is the JSON-RPC port (mainnet default 23811).

### [Qos](/contrib/qos) ###

A Linux bash script that will set up traffic control (tc) to limit the outgoing bandwidth for connections to the Zero P2P network (port 23801).

### [Seeds](/contrib/seeds) ###
Utility to generate the pnSeed[] array that is compiled into the client.

Build Tools and Keys
---------------------

### [Debian](/contrib/debian) ###
Contains files used to package zerod for Debian-based Linux systems. Example config: `debian/examples/zero.conf`.

### [MacDeploy](/contrib/macdeploy) ###
Scripts and notes for Mac builds.

Test and Verify Tools
---------------------

### [TestGen](/contrib/testgen) ###
Utilities to generate test vectors for the data-driven tests.

### [Test Patches](/contrib/test-patches) ###
These patches are applied when the automated pull-tester
tests each pull and when master is tested using jenkins.

### [Verify SF Binaries](/contrib/verifysfbinaries) ###
This script attempts to download and verify the signature file SHA256SUMS.asc from SourceForge.
