# Eval report: baseline-llama-cpp-qwen3-4b

- Run UTC: 2026-05-15T12:08:02+00:00
- Corpus: /Users/nke/.claude/scripts/arbiter/eval/corpus.labeled.jsonl (135 labeled records)
- Bindings: /Users/nke/.claude/scripts/arbiter/bindings.yaml

> llama.cpp llama-server, Qwen3-4B Q4_K_M, ctx=8192 parallel=4,
> JSON-schema-forced {"yes": bool} output. Matches what
> arbiter-up.sh launches today.

## Per-verdict quality

| Verdict | TP | FP | TN | FN | Err | Precision | Recall | F1 | Accuracy | Latency (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| open_questions | 33 | 3 | 96 | 3 | 0 | 0.917 | 0.917 | 0.917 | 0.956 | p50 955 / p95 2584 / max 3632 |
| uncommitted_alternatives | 32 | 3 | 96 | 4 | 0 | 0.914 | 0.889 | 0.901 | 0.948 | p50 896 / p95 2497 / max 3558 |
| out_of_scope_deferral | 28 | 5 | 94 | 8 | 0 | 0.848 | 0.778 | 0.812 | 0.904 | p50 903 / p95 2492 / max 3599 |
| baseline_probe | 2 | 0 | 133 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | p50 836 / p95 2435 / max 3500 |

## Overall

- Calls: 540
- Errors: 0
- Wall: 586.9s
- Latency: p50 901 / p95 2450 / max 3632

## Memory

- Peak RSS: 13651 MiB (1153 samples, pid 52794)

<details><summary>vmmap --summary</summary>

```
Process:         llama-server [52794]
Path:            /opt/homebrew/*/llama-server
Load Address:    0x104c9c000
Identifier:      llama-server
Version:         0
Code Type:       ARM64
Platform:        macOS
Parent Process:  launchd [1]
Target Type:     live task

Date/Time:       2026-05-15 14:08:00.862 +0200
Launch Time:     2026-05-15 13:16:33.442 +0200
OS Version:      macOS 26.4.1 (25E253)
Report Version:  7
Analysis Tool:   /usr/bin/vmmap

Physical footprint:         11.5G
Physical footprint (peak):  14.5G
Idle exit:                  untracked
----

ReadOnly portion of Libraries: Total=1.1G resident=386.2M(33%) swapped_out_or_unallocated=781.8M(67%)
Writable regions: Total=12.0G written=10.4G(86%) resident=10.1G(83%) swapped_out=1.5G(12%) unallocated=509.7M(4%)

                                VIRTUAL RESIDENT    DIRTY  SWAPPED VOLATILE   NONVOL    EMPTY   REGION 
REGION TYPE                        SIZE     SIZE     SIZE     SIZE     SIZE     SIZE     SIZE    COUNT (non-coalesced) 
===========                     ======= ========    =====  ======= ========   ======    =====  ======= 
Activity Tracing                   256K      32K       0K      32K       0K      32K       0K        1 
IOAccelerator                       64K      64K      64K       0K       0K       0K       0K        2 
IOAccelerator (graphics)          5008K    4864K    4864K       0K       0K    4864K       0K      142 
IOKit                               64K      64K      64K       0K       0K      16K       0K        4 
Kernel Alloc Once                   32K      16K      16K       0K       0K       0K       0K        1 
MALLOC guard page                 3872K       0K       0K       0K       0K       0K       0K        4 
MALLOC metadata                   3104K    2560K    1744K     208K       0K       0K       0K        9 
MALLOC_LARGE                       8.9G     7.8G     7.8G     1.1G       0K       0K       0K      106         see MALLOC ZONE table below
MALLOC_LARGE (empty)               1.4G   982.2M   982.2M   400.2M       0K       0K       0K       19         see MALLOC ZONE table below
MALLOC_NANO metadata                32K      32K      32K       0K       0K       0K       0K        1         see MALLOC ZONE table below
MALLOC_SMALL                     100.0M    54.5M    41.2M    12.4M       0K       0K       0K       25         see MALLOC ZONE table below
MALLOC_SMALL (empty)              40.0M    8896K     320K    2080K       0K       0K       0K       10         see MALLOC ZONE table below
MALLOC_TINY                       4096K     224K     224K      64K       0K       0K       0K        1         see MALLOC ZONE table below
Memory Tag 22                     64.0M      32K      32K       0K       0K       0K       0K        1 
STACK GUARD                       56.3M       0K       0K       0K       0K       0K       0K       17 
Stack                             16.5M     512K     512K      64K       0K       0K       0K       17 
Stack (reserved)                   544K       0K       0K       0K       0K       0K       0K        1         reserved VM address space (unallocated)
Stack Guard                         16K       0K       0K       0K       0K       0K       0K        1 
VM_ALLOCATE                       16.8M    10.1M    10.1M    1600K       0K       0K       0K        5 
__AUTH                            2437K    1367K      16K     1840       0K       0K       0K      259 
__AUTH_CONST                      45.2M    16.8M      16K      96K       0K       0K       0K      503 
__CTF                               824      824       0K       0K       0K       0K       0K        1 
__DATA                            19.5M    4928K     266K     688K       0K       0K       0K      470 
__DATA_CONST                      25.9M    12.6M      96K      79K       0K       0K       0K      516 
__DATA_DIRTY                      3001K    1258K     189K     394K       0K       0K       0K      431 
__FONT_DATA                        2352      752       0K       0K       0K       0K       0K        1 
__LINKEDIT                       580.2M   120.3M       0K       0K       0K       0K       0K       14 
__OBJC_RO                         79.1M    53.2M       0K       0K       0K       0K       0K        1 
__OBJC_RW                         2597K    2133K       5K      32K       0K       0K       0K        1 
__TEXT                           587.8M   265.9M       0K       0K       0K       0K       0K      531 
__TPRO_CONST                       128K      16K      16K      64K       0K       0K       0K        2 
mapped file                        2.4G     2.3G       0K       0K       0K       0K       0K        8 
owned unmapped (graphics)         72.0M    72.0M       0K       0K       0K       0K       0K       18 
page table in kernel              7996K    7996K    7996K       0K       0K       0K       0K        1 
shared memory                      1.4G     1.1G     1.1G     176K       0K       0K       0K       24 
unused but dirty shlib __DATA      233K      51K      51K     182K       0K       0K       0K      122 
===========                     ======= ========    =====  ======= ========   ======    =====  ======= 
TOTAL                             15.8G    12.8G    10.0G     1.5G       0K    4912K       0K     3270 
TOTAL, minus reserved VM space    15.8G    12.8G    10.0G     1.5G       0K    4912K       0K     3270 

                                 VIRTUAL   RESIDENT      DIRTY    SWAPPED ALLOCATION      BYTES DIRTY+SWAP          REGION
MALLOC ZONE                         SIZE       SIZE       SIZE       SIZE      COUNT  ALLOCATED  FRAG SIZE  % FRAG   COUNT
===========                      =======  =========  =========  =========  =========  =========  =========  ======  ======
DefaultMallocZone_0x106d1c000       9.1G       7.9G       7.8G       1.1G     337217       9.0G         0K      0%     150
```

</details>
