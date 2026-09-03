// Copyright (c) 2026 The Zero developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or https://www.opensource.org/licenses/mit-license.php .

#ifndef ZERO_CRYPTO_EH_HASHSTATE_H
#define ZERO_CRYPTO_EH_HASHSTATE_H

// Equihash's BLAKE2b state, backed by uniblake instead of libsodium.
//
// uniblake's state is opaque: its size is a runtime value from
// ub_state_size(), so it cannot be declared by value the way libsodium's
// fixed-size struct can. This wrapper restores value semantics -- stack
// declaration, copy-assignment, pass by const reference -- so the call sites
// that already use those spellings do not change.
//
// The copy is ub_copy, which is what makes a prefix state shareable: the
// solver absorbs the block header once and then derives every leaf from a
// copy of that state.

#include "uniblake/prefix.h"
#include "uniblake/uniblake.h"

#include <cstdlib>
#include <cstring>
#include <new>

class EhHashState
{
public:
    EhHashState() : p(alloc()) {}
    ~EhHashState() { std::free(p); }

    EhHashState(const EhHashState& o) : p(alloc()) { ub_copy(p, o.p); }
    EhHashState& operator=(const EhHashState& o)
    {
        if (this != &o) ub_copy(p, o.p);
        return *this;
    }

    ub_state* get()             { return p; }
    const ub_state* get() const { return p; }

private:
    // The library reports its size and alignment and leaves allocation to the
    // caller. aligned_alloc requires a size that is a multiple of the
    // alignment, which ub_state_size() already satisfies, but round anyway
    // rather than depend on it.
    //
    // std::aligned_alloc is C++17. The C feature macros say nothing about
    // whether it is in namespace std -- glibc's <cstdlib> defines
    // _ISOC11_SOURCE for its own headers regardless of the C++ standard, so
    // testing them selects the C++17 branch under -std=c++14 and the name is
    // not there. __cplusplus is the only thing that answers the question.
    // posix_memalign covers every other case, and this tree builds as C++14.
    static ub_state* alloc()
    {
        const size_t a = ub_state_align();
        const size_t n = ((ub_state_size() + a - 1) / a) * a;
        void* s = NULL;
#if __cplusplus >= 201703L
        s = std::aligned_alloc(a, n);
#else
        if (posix_memalign(&s, a < sizeof(void*) ? sizeof(void*) : a, n) != 0) s = NULL;
#endif
        if (!s) throw std::bad_alloc();
        return static_cast<ub_state*>(s);
    }
    ub_state* p;
};

#endif // ZERO_CRYPTO_EH_HASHSTATE_H
