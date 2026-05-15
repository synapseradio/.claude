# Eval report: mlx-qwen3-1.7b-4bit

- Run UTC: 2026-05-15T12:16:36+00:00
- Corpus: /Users/nke/.claude/scripts/arbiter/eval/corpus.labeled.jsonl (135 labeled records)
- Bindings: /Users/nke/.claude/scripts/arbiter/bindings.yaml

> mlx_lm.server with Qwen3-1.7B 4-bit MLX weights. Free-form yes/no
> output parsed by the harness. Dynamic KV allocation removes the
> static ctx*parallel ceiling that dominates the llama.cpp footprint.

## Per-verdict quality

| Verdict | TP | FP | TN | FN | Err | Precision | Recall | F1 | Accuracy | Latency (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| open_questions | 31 | 24 | 75 | 5 | 0 | 0.564 | 0.861 | 0.681 | 0.785 | p50 277 / p95 902 / max 1542 |
| uncommitted_alternatives | 16 | 4 | 95 | 20 | 0 | 0.800 | 0.444 | 0.571 | 0.822 | p50 270 / p95 879 / max 1514 |
| out_of_scope_deferral | 21 | 25 | 74 | 15 | 0 | 0.457 | 0.583 | 0.512 | 0.704 | p50 276 / p95 864 / max 1490 |
| baseline_probe | 2 | 36 | 97 | 0 | 0 | 0.053 | 1.000 | 0.100 | 0.733 | p50 270 / p95 908 / max 2146 |

## Overall

- Calls: 540
- Errors: 0
- Wall: 193.1s
- Latency: p50 273 / p95 879 / max 2146

## Memory

- Peak RSS: 393 MiB (380 samples, pid 44698)

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

Date/Time:       2026-05-15 14:16:35.557 +0200
Launch Time:     2026-05-15 14:10:41.078 +0200
OS Version:      macOS 26.4.1 (25E253)
Report Version:  7
Analysis Tool:   /usr/bin/vmmap

Physical footprint:         1.8G
Physical footprint (peak):  3.7G
Idle exit:                  untracked
----

ReadOnly portion of Libraries: Total=1.2G resident=336.3M(28%) swapped_out_or_unallocated=854.3M(72%)
Writable regions: Total=2.0G written=399.4M(20%) resident=1.7G(83%) swapped_out=111.8M(5%) unallocated=226.3M(11%)

                                VIRTUAL RESIDENT    DIRTY  SWAPPED VOLATILE   NONVOL    EMPTY   REGION 
REGION TYPE                        SIZE     SIZE     SIZE     SIZE     SIZE     SIZE     SIZE    COUNT (non-coalesced) 
===========                     ======= ========    =====  ======= ========   ======    =====  ======= 
Activity Tracing                   256K      32K       0K      32K       0K      32K       0K        1 
IOAccelerator                      448K     448K     448K       0K       0K       0K       0K       10 
IOAccelerator (graphics)           1.3G     1.3G     1.3G       0K       0K     1.3G      96K     1452 
IOKit                               80K      80K      80K       0K       0K      16K       0K        5 
IOSurface                           16K       0K       0K       0K       0K       0K       0K        1 
Kernel Alloc Once                   48K      16K      16K      16K       0K       0K       0K        2 
MALLOC guard page                 3824K       0K       0K       0K       0K       0K       0K        4 
MALLOC metadata                   2000K    1040K    1040K     544K       0K       0K       0K        7 
MALLOC_LARGE                      29.5M    20.8M    20.8M    5536K       0K       0K       0K        5         see MALLOC ZONE table below
MALLOC_LARGE (empty)              38.9M    24.1M    24.1M    13.8M       0K       0K       0K        8         see MALLOC ZONE table below
MALLOC_NANO metadata                64K      32K      32K      16K       0K       0K       0K        2         see MALLOC ZONE table below
MALLOC_SMALL                     195.9M    67.2M    67.2M    82.9M       0K       0K       0K       51         see MALLOC ZONE table below
MALLOC_SMALL (empty)              40.1M    3696K    3696K    7808K       0K       0K       0K       12         see MALLOC ZONE table below
MALLOC_TINY                       4096K     256K     256K      48K       0K       0K       0K        1         see MALLOC ZONE table below
Memory Tag 22                     64.0M      32K      32K      32K       0K       0K       0K        1 
STACK GUARD                        448K       0K       0K       0K       0K       0K       0K       28 
Stack                             79.3M     512K     512K     208K       0K       0K       0K       29 
VM_ALLOCATE                      131.8M   130.1M   130.1M    1216K       0K       0K       0K      527 
__AUTH                            1396K     777K      32K      16K       0K       0K       0K      158 
__AUTH_CONST                      19.0M    10.4M      32K      80K       0K       0K       0K      354 
__CTF                               824       0K       0K      824       0K       0K       0K        1 
__DATA                            8094K    4069K    1994K    1749K       0K       0K       0K      391 
__DATA_CONST                      21.1M    10.0M     496K    4208K       0K       0K       0K      434 
__DATA_DIRTY                      1344K     685K     199K     315K       0K       0K       0K      293 
__FONT_DATA                        2352      752       0K       0K       0K       0K       0K        1 
__LINKEDIT                       665.1M   124.0M       0K       0K       0K       0K       0K       86 
__OBJC_RO                         79.1M    53.2M       0K       0K       0K       0K       0K        1 
__OBJC_RW                         2597K    2133K       5K      32K       0K       0K       0K        1 
__TEXT                           525.4M   212.3M       0K       0K       0K       0K       0K      445 
__TPRO_CONST                       128K      64K      64K      48K       0K       0K       0K        2 
dyld private memory                304K      16K      16K      80K       0K       0K       0K        6 
mapped file                       75.3M    2352K       0K       0K       0K       0K       0K       13 
owned unmapped (graphics)         72.0M    72.0M    72.0M       0K       0K       0K       0K       18 
page table in kernel              1202K    1202K    1202K       0K       0K       0K       0K        1 
shared memory                      656K      80K      80K      64K       0K       0K       0K        8 
unused but dirty shlib __DATA      169K      74K      74K      96K       0K       0K       0K       92 
===========                     ======= ========    =====  ======= ========   ======    =====  ======= 
TOTAL                              3.4G     2.1G     1.7G   118.3M       0K     1.3G      96K     4451 

                                  VIRTUAL   RESIDENT      DIRTY    SWAPPED ALLOCATION      BYTES DIRTY+SWAP          REGION
MALLOC ZONE                          SIZE       SIZE       SIZE       SIZE      COUNT  ALLOCATED  FRAG SIZE  % FRAG   COUNT
===========                       =======  =========  =========  =========  =========  =========  =========  ======  ======
DefaultMallocZone_0x104a18000      271.2M      92.9M      92.9M      96.2M     724095     139.4M      49.7M     27%      73
LSBindingEvaluator_0x109680000       112K         0K         0K       112K          0         0K       112K    100%       2
===========                       =======  =========  =========  =========  =========  =========  =========  ======  ======
TOTAL                              271.4M      92.9M      92.9M      96.3M     724095     139.4M      49.8M     27%      75
```

</details>
