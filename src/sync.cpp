// Copyright (c) 2011-2012 The Bitcoin Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or https://www.opensource.org/licenses/mit-license.php .

#include "sync.h"

#include "util.h"
#include "utilstrencodings.h"

#include <stdio.h>
#include <algorithm>
#include <map>
#include <vector>

#include <boost/foreach.hpp>
#include <boost/thread.hpp>

#ifdef DEBUG_LOCKCONTENTION
void PrintLockContention(const char* pszName, const char* pszFile, int nLine)
{
    LogPrintf("LOCKCONTENTION: %s\n", pszName);
    LogPrintf("Locker: %s:%d\n", pszFile, nLine);
}
#endif /* DEBUG_LOCKCONTENTION */

#ifdef DEBUG_LOCKORDER
//
// Early deadlock detection.
// Problem being solved:
//    Thread 1 locks  A, then B, then C
//    Thread 2 locks  D, then C, then A
//     --> may result in deadlock between the two threads, depending on when they run.
// Solution implemented here:
// Keep track of pairs of locks: (A before B), (A before C), etc.
// Complain if any thread tries to lock in a different order.
//

struct CLockLocation {
    CLockLocation(const char* pszName, const char* pszFile, int nLine, bool fTryIn)
    {
        mutexName = pszName;
        sourceFile = pszFile;
        sourceLine = nLine;
        fTry = fTryIn;
    }

    std::string ToString() const
    {
        return mutexName + "  " + sourceFile + ":" + itostr(sourceLine) + (fTry ? " (TRY)" : "");
    }

    std::string MutexName() const { return mutexName; }

    bool fTry;
private:
    std::string mutexName;
    std::string sourceFile;
    int sourceLine;
};

typedef std::vector<std::pair<void*, CLockLocation> > LockStack;

static boost::mutex dd_mutex;

// Lock-hygiene counters, reported by LogLockStats(). Guarded by dd_mutex like
// everything else here.
//
//   nLockRecursive  same thread re-acquiring a lock it already holds. Legal,
//                   but the prevalence is worth knowing: a path that locks at
//                   two depths is where a lock contract is easiest to break.
//   nLockUnderflow  LeaveCritical() with an empty stack. Always a defect --
//                   an unbalanced LOCK/unlock, or a lock released twice.
static uint64_t nLockRecursive = 0;
static uint64_t nLockUnderflow = 0;

// Per-site attribution for recursive acquires. ~30 per block is high enough
// that "recursive mutexes allow it" is not an answer -- the question is which
// call sites, and whether the same site re-locks or different ones nest.
//
// Key: "<mutex> <file>:<line> under <file>:<line>" -- the acquiring site and
// the site that already holds it. Same file:line on both sides means one
// function re-locking itself, which is almost always removable; different
// sites mean genuine nesting, which may be structural.
static std::map<std::string, uint64_t> recursiveSites;
static std::map<std::pair<void*, void*>, LockStack> lockorders;
static boost::thread_specific_ptr<LockStack> lockstack;


static void potential_deadlock_detected(const std::pair<void*, void*>& mismatch, const LockStack& s1, const LockStack& s2)
{
    // We attempt to not assert on probably-not deadlocks by assuming that
    // a try lock will immediately have otherwise bailed if it had
    // failed to get the lock
    // We do this by, for the locks which triggered the potential deadlock,
    // in either lockorder, checking that the second of the two which is locked
    // is only a TRY_LOCK, ignoring locks if they are reentrant.
    bool firstLocked = false;
    bool secondLocked = false;
    bool onlyMaybeDeadlock = false;

    LogPrintf("POTENTIAL DEADLOCK DETECTED\n");
    LogPrintf("Previous lock order was:\n");
    BOOST_FOREACH (const PAIRTYPE(void*, CLockLocation) & i, s2) {
        if (i.first == mismatch.first) {
            LogPrintf(" (1)");
            if (!firstLocked && secondLocked && i.second.fTry)
                onlyMaybeDeadlock = true;
            firstLocked = true;
        }
        if (i.first == mismatch.second) {
            LogPrintf(" (2)");
            if (!secondLocked && firstLocked && i.second.fTry)
                onlyMaybeDeadlock = true;
            secondLocked = true;
        }
        LogPrintf(" %s\n", i.second.ToString());
    }
    firstLocked = false;
    secondLocked = false;
    LogPrintf("Current lock order is:\n");
    BOOST_FOREACH (const PAIRTYPE(void*, CLockLocation) & i, s1) {
        if (i.first == mismatch.first) {
            LogPrintf(" (1)");
            if (!firstLocked && secondLocked && i.second.fTry)
                onlyMaybeDeadlock = true;
            firstLocked = true;
        }
        if (i.first == mismatch.second) {
            LogPrintf(" (2)");
            if (!secondLocked && firstLocked && i.second.fTry)
                onlyMaybeDeadlock = true;
            secondLocked = true;
        }
        LogPrintf(" %s\n", i.second.ToString());
    }
    assert(onlyMaybeDeadlock);
}

static void push_lock(void* c, const CLockLocation& locklocation, bool fTry)
{
    if (lockstack.get() == NULL)
        lockstack.reset(new LockStack);

    dd_mutex.lock();

    (*lockstack).push_back(std::make_pair(c, locklocation));

    if (!fTry) {
        BOOST_FOREACH (const PAIRTYPE(void*, CLockLocation) & i, (*lockstack)) {
            if (i.first == c) {
                // Record acquiring site and holding site. lockstack.back() is
                // the entry just pushed for this acquisition.
                if ((*lockstack).size() >= 2) {
                    const CLockLocation& acquiring = (*lockstack).back().second;
                    recursiveSites[i.second.MutexName() + " " +
                                   acquiring.ToString() + " under " +
                                   i.second.ToString()]++;
                }
                // This thread already holds c: a recursive acquisition. Legal
                // for the recursive mutexes Zero uses, and the loop must stop
                // here or it would compare c against itself. Counted because
                // without concurrency the prevalence should be low and a
                // *rising* count is a signal: it means a call path acquires
                // the same lock at two depths, which is where an
                // AssertLockHeld contract is easiest to get wrong (P12).
                nLockRecursive++;
                break;
            }

            std::pair<void*, void*> p1 = std::make_pair(i.first, c);
            if (lockorders.count(p1))
                continue;
            lockorders[p1] = (*lockstack);

            std::pair<void*, void*> p2 = std::make_pair(c, i.first);
            if (lockorders.count(p2))
                potential_deadlock_detected(p1, lockorders[p2], lockorders[p1]);
        }
    }
    dd_mutex.unlock();
}

static void pop_lock()
{
    dd_mutex.lock();
    // Unlocking something never locked is a real defect, not a curiosity:
    // pop_back() on an empty vector is undefined behaviour, so the original
    // would corrupt the stack rather than report. Count and refuse instead.
    if ((*lockstack).empty()) {
        nLockUnderflow++;
        LogPrintf("LOCK UNDERFLOW: LeaveCritical() with no lock held\n");
    } else {
        (*lockstack).pop_back();
    }
    dd_mutex.unlock();
}

void LogLockStats()
{
    dd_mutex.lock();
    const uint64_t rec = nLockRecursive, und = nLockUnderflow;
    dd_mutex.unlock();
    LogPrintf("LockStats: recursive_acquires=%llu underflows=%llu\n",
              (unsigned long long)rec, (unsigned long long)und);

    // Top sites, descending. Attribution is the point: a flat total cannot
    // distinguish a hot path re-locking itself from deep structural nesting.
    dd_mutex.lock();
    std::vector<std::pair<uint64_t, std::string> > v;
    for (std::map<std::string, uint64_t>::const_iterator it = recursiveSites.begin();
         it != recursiveSites.end(); ++it)
        v.push_back(std::make_pair(it->second, it->first));
    dd_mutex.unlock();
    std::sort(v.rbegin(), v.rend());
    for (size_t i = 0; i < v.size() && i < 25; i++)
        LogPrintf("LockStats:   %10llu  %s\n",
                  (unsigned long long)v[i].first, v[i].second.c_str());
    LogPrintf("LockStats: %llu distinct recursive sites\n",
              (unsigned long long)v.size());
}

void EnterCritical(const char* pszName, const char* pszFile, int nLine, void* cs, bool fTry)
{
    push_lock(cs, CLockLocation(pszName, pszFile, nLine, fTry), fTry);
}

void LeaveCritical()
{
    pop_lock();
}

std::string LocksHeld()
{
    std::string result;
    BOOST_FOREACH (const PAIRTYPE(void*, CLockLocation) & i, *lockstack)
        result += i.second.ToString() + std::string("\n");
    return result;
}

void AssertLockHeldInternal(const char* pszName, const char* pszFile, int nLine, void* cs)
{
    BOOST_FOREACH (const PAIRTYPE(void*, CLockLocation) & i, *lockstack)
        if (i.first == cs)
            return;
    fprintf(stderr, "Assertion failed: lock %s not held in %s:%i; locks held:\n%s", pszName, pszFile, nLine, LocksHeld().c_str());
    abort();
}

#endif /* DEBUG_LOCKORDER */
