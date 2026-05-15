# Eval report: mlx-qwen3-1.7b-4bit-v2

- Run UTC: 2026-05-15T12:26:00+00:00
- Corpus: /Users/nke/.claude/scripts/arbiter/eval/corpus.labeled.jsonl (135 labeled records)
- Bindings: /Users/nke/.claude/scripts/arbiter/eval/bindings-1.7b.yaml

> mlx_lm.server + Qwen3-1.7B-4bit + small-model bindings v2.
> Verdict prompts rewritten with negative examples that anchor the
> 1.7B away from the FP/FN patterns it confused on v1.

## Per-verdict quality

| Verdict | TP | FP | TN | FN | Err | Precision | Recall | F1 | Accuracy | Latency (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| open_questions | 17 | 6 | 93 | 19 | 0 | 0.739 | 0.472 | 0.576 | 0.815 | p50 281 / p95 888 / max 1571 |
| uncommitted_alternatives | 21 | 4 | 95 | 15 | 0 | 0.840 | 0.583 | 0.689 | 0.859 | p50 282 / p95 850 / max 1594 |
| out_of_scope_deferral | 31 | 53 | 46 | 5 | 0 | 0.369 | 0.861 | 0.517 | 0.570 | p50 278 / p95 852 / max 1566 |
| baseline_probe | 1 | 8 | 125 | 1 | 0 | 0.111 | 0.500 | 0.182 | 0.933 | p50 272 / p95 910 / max 1646 |

## Overall

- Calls: 540
- Errors: 0
- Wall: 193.4s
- Latency: p50 280 / p95 864 / max 1646

## Memory

- Peak RSS: 316 MiB (381 samples, pid 44698)

<details><summary>vmmap --summary</summary>

```
Process:         Python [44698]
Path:            /Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python
Load Address:    0x104364000
Identifier:      com.apple.python3
Version:         3.9.6 (3.9.6)
Build Info:      python3-141000000500005~2504
Code Type:       ARM64
Platform:        macOS
Parent Process:  launchd [1]
Target Type:     live task

Date/Time:       2026-05-15 14:25:59.811 +0200
Launch Time:     2026-05-15 14:10:41.078 +0200
OS Version:      macOS 26.4.1 (25E253)
Report Version:  7
Analysis Tool:   /usr/bin/vmmap

Physical footprint:         1.9G
Physical footprint (peak):  3.8G
Idle exit:                  untracked
----

ReadOnly portion of Libraries: Total=1.2G resident=332.6M(28%) swapped_out_or_unallocated=858.0M(72%)
Writable regions: Total=2.1G written=421.6M(20%) resident=1.8G(84%) swapped_out=116.4M(5%) unallocated=225.0M(10%)

                                VIRTUAL RESIDENT    DIRTY  SWAPPED VOLATILE   NONVOL    EMPTY   REGION 
REGION TYPE                        SIZE     SIZE     SIZE     SIZE     SIZE     SIZE     SIZE    COUNT (non-coalesced) 
===========                     ======= ========    =====  ======= ========   ======    =====  ======= 
Activity Tracing                   256K      32K       0K      32K       0K      32K       0K        1 
IOAccelerator                      448K     448K     448K       0K       0K       0K       0K       10 
IOAccelerator (graphics)           1.5G     1.5G     1.5G       0K       0K     1.5G     160K     1454 
IOKit                               80K      80K      80K       0K       0K      16K       0K        5 
IOSurface                           16K       0K       0K       0K       0K       0K       0K        1 
Kernel Alloc Once                   48K      16K      16K      16K       0K       0K       0K        2 
MALLOC guard page                 3824K       0K       0K       0K       0K       0K       0K        4 
MALLOC metadata                   2000K    1072K    1072K     512K       0K       0K       0K        7 
MALLOC_LARGE                      29.5M    16.5M    16.5M    9904K       0K       0K       0K        5         see MALLOC ZONE table below
MALLOC_LARGE (empty)              38.9M    24.1M    24.1M    13.8M       0K       0K       0K        8         see MALLOC ZONE table below
MALLOC_NANO metadata                64K      32K      32K      16K       0K       0K       0K        2         see MALLOC ZONE table below
MALLOC_SMALL                     195.9M    67.2M    67.2M    83.2M       0K       0K       0K       51         see MALLOC ZONE table below
MALLOC_SMALL (empty)              40.1M    4288K    4288K    7904K       0K       0K       0K       12         see MALLOC ZONE table below
MALLOC_TINY                       4096K     256K     256K      48K       0K       0K       0K        1         see MALLOC ZONE table below
Memory Tag 22                     64.0M      32K      32K      32K       0K       0K       0K        1 
STACK GUARD                        432K       0K       0K       0K       0K       0K       0K       27 
Stack                             78.8M     480K     480K     192K       0K       0K       0K       28 
VM_ALLOCATE                      132.0M   130.2M   130.2M    1216K       0K       0K       0K      528 
__AUTH                            1396K     745K      32K      16K       0K       0K       0K      158 
__AUTH_CONST                      19.0M     9.8M      16K      96K       0K       0K       0K      354 
__CTF                               824       0K       0K      824       0K       0K       0K        1 
__DATA                            8094K    3972K    1994K    1749K       0K       0K       0K      391 
__DATA_CONST                      21.1M    9498K     480K    4224K       0K       0K       0K      434 
__DATA_DIRTY                      1344K     663K     199K     315K       0K       0K       0K      293 
__FONT_DATA                        2352      752       0K       0K       0K       0K       0K        1 
__LINKEDIT                       665.1M   122.0M       0K       0K       0K       0K       0K       86 
__OBJC_RO                         79.1M    52.1M       0K       0K       0K       0K       0K        1 
__OBJC_RW                         2597K    2117K       5K      32K       0K       0K       0K        1 
__TEXT                           525.4M   210.6M       0K       0K       0K       0K       0K      445 
__TPRO_CONST                       128K      64K      64K      48K       0K       0K       0K        2 
dyld private memory                304K      16K      16K      80K       0K       0K       0K        6 
mapped file                       75.3M    2336K       0K       0K       0K       0K       0K       13 
owned unmapped (graphics)         72.0M    72.0M    72.0M       0K       0K       0K       0K       18 
page table in kernel              1202K    1202K    1202K       0K       0K       0K       0K        1 
shared memory                      656K      48K      48K      96K       0K       0K       0K        8 
unused but dirty shlib __DATA      169K      74K      74K      96K       0K       0K       0K       92 
===========                     ======= ========    =====  ======= ========   ======    =====  ======= 
TOTAL                              3.5G     2.2G     1.8G   123.0M       0K     1.5G     160K     4452 

                                  VIRTUAL   RESIDENT      DIRTY    SWAPPED ALLOCATION      BYTES DIRTY+SWAP          REGION
MALLOC ZONE                          SIZE       SIZE       SIZE       SIZE      COUNT  ALLOCATED  FRAG SIZE  % FRAG   COUNT
===========                       =======  =========  =========  =========  =========  =========  =========  ======  ======
DefaultMallocZone_0x104a18000      271.2M      89.2M      89.2M     100.9M     724131     139.5M      50.6M     27%      73
LSBindingEvaluator_0x109680000       112K         0K         0K       112K          0         0K       112K    100%       2
===========                       =======  =========  =========  =========  =========  =========  =========  ======  ======
TOTAL                              271.4M      89.2M      89.2M     101.0M     724131     139.5M      50.8M     27%      75
```

</details>
