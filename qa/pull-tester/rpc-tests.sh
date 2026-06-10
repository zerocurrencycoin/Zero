#!/bin/bash
set -e -o pipefail

CURDIR=$(cd $(dirname "$0"); pwd)
# Get BUILDDIR and REAL_BITCOIND
. "${CURDIR}/tests-config.sh"

export BUILDDIR
export BITCOINCLI=${BUILDDIR}/qa/pull-tester/run-bitcoin-cli
export BITCOIND=${REAL_BITCOIND}
export ZERO_RPC_CACHE_DIR="${ZERO_RPC_CACHE_DIR:-$BUILDDIR/cache}"
export PYTHON
export PYTHONPATH="${BUILDDIR}/qa/rpc-tests${PYTHONPATH:+:${PYTHONPATH}}"

#Run the tests

testScripts=(
    'paymentdisclosure.py'
    'prioritisetransaction.py'
    'wallet_treestate.py'
    'wallet_anchorfork.py'
    'wallet_changeaddresses.py'
    'wallet_changeindicator.py'
    'wallet_import_export.py'
    'wallet_protectcoinbase.py'
    'wallet_shieldcoinbase_sapling.py'
    'wallet_listreceived.py'
    'wallet.py'
    'wallet_overwintertx.py'
    'wallet_persistence.py'
    'wallet_nullifiers.py'
    'wallet_1941.py'
    'wallet_addresses.py'
    'wallet_sapling.py'
    'wallet_listnotes.py'
    'mergetoaddress_sprout.py'
    'mergetoaddress_sapling.py'
    'mergetoaddress_mixednotes.py'
    'listtransactions.py'
    'mempool_resurrect_test.py'
    'txn_doublespend.py'
    'txn_doublespend.py --mineblock'
    'getchaintips.py'
    'rawtransactions.py'
    'getrawtransaction_insight.py'
    'rest.py'
    'mempool_limit.py'
    'mempool_spendcoinbase.py'
    'mempool_reorg.py'
    'mempool_nu_activation.py'
    'mempool_tx_expiry.py'
    'httpbasics.py'
    'zapwallettxes.py'
    'proxy_test.py'
    'merkle_blocks.py'
    'fundrawtransaction.py'
    'signrawtransactions.py'
    'signrawtransaction_offline.py'
    'walletbackup.py'
    'key_import_export.py'
    'nodehandling.py'
    'reindex.py'
    'rescan_import.py'
    'rescan_startup.py'
    'addressindex.py'
    'spentindex.py'
    'timestampindex.py'
    'decodescript.py'
    'keypool.py'
    'blockchain.py'
    'disablewallet.py'
    'zkey_import_export.py'
    'reorg_limit.py'
    'getblocktemplate.py'
    'bip65-cltv-p2p.py'
    'bipdersig-p2p.py'
    'p2p_nu_peer_management.py'
    'rewind_index.py'
    'p2p_txexpiry_dos.py'
    'p2p_txexpiringsoon.py'
    'p2p_node_bloom.py'
    'regtest_signrawtransaction.py'
    'finalsaplingroot.py'
    'shorter_block_times.py'
    'sprout_sapling_migration.py'
    'turnstile.py'
);
testScriptsExt=(
    'getblocktemplate_longpoll.py'
    'getblocktemplate_proposals.py'
    'pruning.py'
    'invalidateblock.py'
    'receivedby.py'
    'rpcbind_test.py'
#   'script_test.py'
    'smartfees.py'
    'maxblocksinflight.py'
    'invalidblockrequest.py'
    'p2p-acceptblock.py'
);

if [ "x$ENABLE_ZMQ" = "x1" ]; then
  if [ -n "$PYTHON" ] && "$PYTHON" -c "import zmq" 2>/dev/null; then
    testScripts+=('zmq_test.py')
  fi
fi

if [ "x$ENABLE_PROTON" = "x1" ]; then
  testScripts+=('proton_test.py')
fi

# Tier A: contributor gate (serial default via contrib/run-tests.sh -> rpc-tests.sh -A).
# Slow wallet / rescan / doublespend / heavy-mining scripts live in testScripts (Tier B) only.
# keypool.py: Tier A gate; in testScripts (removed from testScriptsExt).
# prioritisetransaction.py, wallet_treestate.py: Bfail Retired (legacy Sprout / 1121-block priority).
# Keep PYTHON_PASSING in contrib/run-tests.sh in sync (used for --jobs=N parallel runs only).
# Tier inventory CSV: rpc-tests.sh -list-csv [path]  (grouped script names; arrays below are authoritative).
testScriptsTierA=(
    'blockchain.py'
    'disablewallet.py'
    'httpbasics.py'
    'reindex.py'
    'decodescript.py'
    'keypool.py'
    'paymentdisclosure.py'
    'getchaintips.py'
    'rewind_index.py'
    'p2p_nu_peer_management.py'
)

# Tier counts (pass tiers): A=10, B pass=21 (20 unique; txn_doublespend x2), E pass=2; -all runs 33.
# Bfail: Debug=32, Retired=6; -rpcfail runs Bfail+Efail diagnostic tiers.
# Tier B pass: in testScripts but not Tier A.
testScriptsTierBPass=(
    'wallet_anchorfork.py'
    'wallet_changeindicator.py'
    'wallet_import_export.py'
    'wallet_protectcoinbase.py'
    'wallet_shieldcoinbase_sapling.py'
    'wallet_nullifiers.py'
    'wallet_1941.py'
    'listtransactions.py'
    'mempool_resurrect_test.py'
    'txn_doublespend.py'
    'txn_doublespend.py --mineblock'
    'zapwallettxes.py'
    'proxy_test.py'
    'signrawtransactions.py'
    'nodehandling.py'
    'rescan_startup.py'
    'zkey_import_export.py'
    'getblocktemplate.py'
    'p2p_txexpiry_dos.py'
    'p2p_txexpiringsoon.py'
    'p2p_node_bloom.py'
)

# Tier B fail: known broken; diagnostic only (-Bfail). Subgroups for triage (still one -Bfail run).
#   BfailDebug: porting / maturity / insight / comptool / Py3 -- needs engineering
#   BfailRetired: Sprout-era, manual testnet, merge-to-address sprout -- low priority
testScriptsTierBFailDebug=(
    'shorter_block_times.py'
    'wallet.py'
    'wallet_changeaddresses.py'
    'wallet_addresses.py'
    'rescan_import.py'
    'reorg_limit.py'
    'wallet_listreceived.py'
    'wallet_persistence.py'
    'wallet_sapling.py'
    'wallet_listnotes.py'
    'mergetoaddress_sapling.py'
    'mergetoaddress_mixednotes.py'
    'rawtransactions.py'
    'getrawtransaction_insight.py'
    'rest.py'
    'mempool_limit.py'
    'mempool_spendcoinbase.py'
    'mempool_reorg.py'
    'mempool_nu_activation.py'
    'mempool_tx_expiry.py'
    'merkle_blocks.py'
    'fundrawtransaction.py'
    'signrawtransaction_offline.py'
    'walletbackup.py'
    'key_import_export.py'
    'addressindex.py'
    'spentindex.py'
    'timestampindex.py'
    'bip65-cltv-p2p.py'
    'bipdersig-p2p.py'
    'regtest_signrawtransaction.py'
    'finalsaplingroot.py'
)

testScriptsTierBFailRetired=(
    'prioritisetransaction.py'
    'wallet_treestate.py'
    'wallet_overwintertx.py'
    'mergetoaddress_sprout.py'
    'sprout_sapling_migration.py'
    'turnstile.py'
)

testScriptsTierBFail=()
testScriptsTierBFail+=("${testScriptsTierBFailDebug[@]}")
testScriptsTierBFail+=("${testScriptsTierBFailRetired[@]}")

# Ext pass / fail (testScriptsExt subsets).
testScriptsExtPass=(
    'invalidateblock.py'
    'maxblocksinflight.py'
)

testScriptsExtFail=(
    'getblocktemplate_longpoll.py'
    'getblocktemplate_proposals.py'
    'pruning.py'
    'receivedby.py'
    'rpcbind_test.py'
    'smartfees.py'
    'invalidblockrequest.py'
    'p2p-acceptblock.py'
)

# Invocation tiers (documented in TEST_ZERO.md; inventory: -list-csv):
#   Pass: A=10, B=21, E=2 (-all = 33). Bfail: Debug=32, Retired=6. Efail=8.
#   -A | --tier-a       Tier A gate
#   -B | --tier-b       Tier B pass only
#   -Bfail              Tier B fail only (Debug then Retired; diagnostic)
#   -list-csv [path]    Tier/group/script CSV to stdout or path; no tests run
#   -E | --tier-e       Ext pass only
#   -Efail              Ext fail only (diagnostic)
#   -all                -A then -B then -E (pass tiers)
#   -rpcfail            -Bfail then -Efail (diagnostic)
#   (no args)           same as -all (qa/zcash/full_test_suite.py rpc stage)
#   <name>              one script by basename

successCount=0
declare -a failures

function runTestScript
{
    local testName="$1"
    shift

    echo -e "=== Running testscript ${testName} ==="

    if eval "$@"
    then
        successCount=$(expr $successCount + 1)
        echo "--- Success: ${testName} ---"
    else
        failures[${#failures[@]}]="$testName"
        echo "!!! FAIL: ${testName} !!!"
    fi

    echo
}

function runScriptEntry
{
    local entry="$1"
    local script_file="${entry%% *}"
    local extra_args="${entry#"${script_file}"}"
    extra_args="${extra_args# }"
    runTestScript \
        "$entry" \
        "${PYTHON}" "${BUILDDIR}/qa/rpc-tests/${script_file}" \
        --srcdir "${BUILDDIR}/src" ${passOn} ${extra_args}
}

function runScriptArray
{
    local i
    local arr_name="$1"
    eval "local arr=(\"\${${arr_name}[@]}\")"
    for (( i = 0; i < ${#arr[@]}; i++ )); do
        runScriptEntry "${arr[$i]}"
    done
}

function runTierA
{
    runScriptArray testScriptsTierA
}

function runTierBPass
{
    runScriptArray testScriptsTierBPass
}

function runTierBFail
{
    echo "=== RPC tier -Bfail Debug (porting / maturity / comptool) ==="
    runScriptArray testScriptsTierBFailDebug
    echo "=== RPC tier -Bfail Retired (Sprout / manual testnet) ==="
    runScriptArray testScriptsTierBFailRetired
}

function dumpTierCsv
{
    local ent
    echo "tier,group,script"
    for ent in "${testScriptsTierA[@]}"; do echo "A,gate,${ent}"; done
    for ent in "${testScriptsTierBPass[@]}"; do echo "B,pass,${ent}"; done
    for ent in "${testScriptsTierBFailDebug[@]}"; do echo "Bfail,debug,${ent}"; done
    for ent in "${testScriptsTierBFailRetired[@]}"; do echo "Bfail,retired,${ent}"; done
    for ent in "${testScriptsExtPass[@]}"; do echo "E,pass,${ent}"; done
    for ent in "${testScriptsExtFail[@]}"; do echo "Efail,fail,${ent}"; done
}

function runTierEPass
{
    runScriptArray testScriptsExtPass
}

function runTierEFail
{
    runScriptArray testScriptsExtFail
}

function runTierAllPass
{
    runTierA
    runTierBPass
    runTierEPass
}

function runTierAllFail
{
    runTierBFail
    runTierEFail
}

function entryMatchesWant
{
    local ent="$1"
    local want="$2"
    local base="${ent%% *}"
    [ "$want" = "$ent" ] || [ "$want" = "$base" ] || [ "$want.py" = "$base" ]
}

function runSingleByName
{
    local want="$1"
    local lists=(
        testScriptsTierA
        testScriptsTierBPass
        testScriptsTierBFail
        testScriptsExtPass
        testScriptsExtFail
        testScripts
        testScriptsExt
    )
    local list ent i
    for list in "${lists[@]}"; do
        eval "local arr=(\"\${${list}[@]}\")"
        for (( i = 0; i < ${#arr[@]}; i++ )); do
            ent="${arr[$i]}"
            if entryMatchesWant "$ent" "$want"; then
                runScriptEntry "$ent"
                return 0
            fi
        done
    done
    echo "Unknown test script: $want"
    return 1
}

if [ "x${ENABLE_BITCOIND}${ENABLE_UTILS}${ENABLE_WALLET}" = "x111" ]; then
    if [ "$1" = "-list-csv" ]; then
        if [ -n "$2" ]; then
            dumpTierCsv > "$2"
            echo "Wrote tier inventory to $2" >&2
        else
            dumpTierCsv
        fi
        exit 0
    fi
    RPC_TIER=""
    passOn=""
    if [ $# -eq 0 ]; then
        RPC_TIER=all
    elif [ "$1" = "-A" ] || [ "$1" = "--tier-a" ]; then
        RPC_TIER=a
        shift
        passOn="$*"
    elif [ "$1" = "-Bfail" ]; then
        RPC_TIER=bfail
        shift
        passOn="$*"
    elif [ "$1" = "-B" ] || [ "$1" = "--tier-b" ]; then
        RPC_TIER=b
        shift
        passOn="$*"
    elif [ "$1" = "-Efail" ]; then
        RPC_TIER=efail
        shift
        passOn="$*"
    elif [ "$1" = "-E" ] || [ "$1" = "--tier-e" ]; then
        RPC_TIER=e
        shift
        passOn="$*"
    elif [ "$1" = "-rpcfail" ]; then
        RPC_TIER=rpcfail
        shift
        passOn="$*"
    elif [ "$1" = "-all" ]; then
        RPC_TIER=all
        shift
        passOn="$*"
    else
        RPC_TIER=single
        single_name="$1"
        shift
        passOn="$*"
    fi

    case "$RPC_TIER" in
        a)        echo "=== RPC tier -A (Tier A gate) ===" ; runTierA ;;
        b)        echo "=== RPC tier -B (Tier B pass) ===" ; runTierBPass ;;
        bfail)    echo "=== RPC tier -Bfail (Tier B known fail) ===" ; runTierBFail ;;
        e)        echo "=== RPC tier -E (Ext pass) ===" ; runTierEPass ;;
        efail)    echo "=== RPC tier -Efail (Ext known fail) ===" ; runTierEFail ;;
        all)      echo "=== RPC tier -all (-A -B -E pass) ===" ; runTierAllPass ;;
        rpcfail)  echo "=== RPC tier -rpcfail (-Bfail -Efail) ===" ; runTierAllFail ;;
        single)   runSingleByName "$single_name" || exit 1 ;;
    esac

    echo -e "\n\nTests completed: $(expr $successCount + ${#failures[@]})"
    echo "successes $successCount; failures: ${#failures[@]}"

    if [ ${#failures[@]} -gt 0 ]
    then
        echo -e "\nFailing tests: ${failures[*]}"
        exit 1
    else
        exit 0
    fi
else
  echo "No rpc tests to run. Wallet, utils, and bitcoind must all be enabled"
fi
