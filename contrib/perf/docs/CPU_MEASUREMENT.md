# Measuring CPU utilization without contradicting yourself

**The problem, stated plainly.** CPU figures in this work have jumped between
~20-40% and near 0, and between 100% and 208%, depending on what was sampled
and when. Those are not different behaviours of the node; they are different
instruments answering different questions, reported as if they were the same
number.

## The four quantities that get conflated

| Quantity | What it answers | Instrument |
|----------|-----------------|------------|
| **Process CPU rate** | how many cores is this process using *now* | delta of CPU time / wall time |
| **ps `%cpu`** | a **decaying average** over the process lifetime | `ps -o %cpu` |
| **Bucket share** | what fraction of *sampled stacks* were in function X | `xctrace` / folded stacks |
| **Wall-clock share** | what fraction of elapsed time a phase took | launcher timing |

A bucket share of 48-55% (Groth16, M-CPU-SEQ) and a process rate of 100% are
both correct and are not comparable: the first is a share of CPU *spent*, the
second is a share of *one core*. Reporting "Groth16 is 50%" beside "CPU is
100%" invites the reading that half the machine is idle when in fact one core
is saturated and thirteen are not being asked to do anything.

## `ps %cpu` is a decaying average -- measured, not assumed

`ps(1)` on this platform: *"%cpu -- The CPU utilization of the process; this is
a decaying average"*.

Sampled side by side against a delta-based rate on a running `-loadblock`
import, 5-second intervals:

| sample | `ps %cpu` | delta rate |
|-------:|----------:|-----------:|
| 1 | 107.6 | 115.2 |
| 2 | **101.8** | 114.4 |
| 3 | 113.4 | 114.8 |
| 4 | 113.8 | 115.0 |
| 5 | 113.6 | 113.2 |

| | mean | range | CV |
|---|---:|---:|---:|
| `ps %cpu` | 110.0 | **12.0** | **4.3%** |
| delta rate | 114.5 | **2.0** | **0.6%** |

`ps` understated by up to **12.6 points** and is **7x noisier**. It lags a step
change by tens of seconds, which is why a sample taken just after a phase
transition reads far below the steady state -- the "jumping to almost 0"
symptom.

## The fix, applied

`postsapling_reindex.sh:sample_util` now records **both**:

- `cpu%` -- `ps` value, kept for continuity with existing rows
- `cpu_rate` -- `(CPU seconds consumed) / (wall seconds elapsed) x 100`
  between consecutive samples

**`cpu_rate` is the number to read.** It is instantaneous, has no decay, and
is directly interpretable as "cores in use".

## Rules

1. **Never compare a bucket share with a process rate.** State which one a
   figure is. A share needs a denominator named; a rate needs the core count
   named.
2. **Never sample CPU within ~30 s of a phase transition** without saying so.
   `ps` is still decaying; the delta rate needs two samples to exist at all.
3. **Report the core count beside any rate.** "107%" means nothing without
   "on a 14-core host" -- it is 7.6% of the machine and 100% of one core.
4. **A rate above 100% is not an error.** It means more than one core; 208%
   observed here was a transient flush phase.
5. **For a phase attribution, use the profiler, not `ps`.** `bucket_profile2.py`
   over `xctrace` output answers "where did the time go"; no process-level
   counter can.

## What this does not fix

The **bucket** side has its own version of this problem: a share is over
sampled stacks, so a function that is 50% of samples on a single-threaded
phase is not 50% of machine capacity. `Perf.md` S2 states its denominators;
newer figures should do the same explicitly rather than by convention.
