# Contracts between units

Read this when the plan has several work units. What can run at the same time is decided by which contracts the plan fixes, more than by which files collide: two units that agree on a signature in advance can be built apart, in any order, by agents that never speak. A unit that must discover the signature from another unit's code can only follow it.

## Gather

### Find each boundary

Walk every user story through the change, from what the person does to where the result reaches them. Each place the story crosses from one unit to another, or from changed code into code the plan leaves alone, is a boundary. Look also at these, which stories tend to skip:

- a type, an enum, or a set of ids two units both name
- a file, a config key, an environment variable, or a message one unit writes and another reads
- a test helper, a fixture, or exact strings in assertions that several units' tests rely on
- an error or an empty result one unit returns and another must handle
- the order in which one unit calls another, where that order matters

### Fix what a read can settle

For each boundary, write the contract from the consuming side: what does the caller want to say, and what must it never have to know? Then state it in full, in the language of the code:

- the exact signature, with parameter and return types
- every case of each sum type and every id in each set, spelled as the code will spell them
- what happens on failure: the error type, the empty value, or the guarantee that none occurs
- the file each declaration lives in, and the one unit that owns that file

Mark the contract line fixed once nothing in it waits on the work. Read existing code, types, docs, and test kits now to get there, in parallel delegates where you can: what a read settles during planning costs one agent one read, and left open it costs every consumer a wait.

A contract stays open only where the work itself must show its shape, a spike's result or a measured limit for one. Keep each open contract as small as it can be: fix the signature and leave open only the value the work will find.

### Turn waits into contracts

Read each unit's waits. For each, ask what the waiting unit needs from the other:

- its interface, to call or implement ? fix the contract, name it in both unit lines as provides and consumes, and remove the wait
- its real behavior, to pass an integration check ? keep the wait, and move that check into a unit that runs after both
- the same function or region to rewrite ? see hotspots below

A consumer of a fixed contract builds against the plan's statement. Where its commit needs the declaration to exist, to compile or to pass type checks, choose one:

- a contracts unit: a small first unit that commits every shared declaration, as types and as stubs that fail loudly when called. It runs alone in the first wave and costs little because it holds no logic. Every unit that needs a declaration names the contracts unit in its waits, and starts from its commit.
- a local test double: where only tests need something to call, the consumer writes a double that follows the contract, and the integrating unit replaces it.

Prefer the contracts unit where three or more units share declarations, or where a type checker runs on commit.

### Split each hotspot

A hotspot is a file or function several units rewrite. Units that share one must run in sequence, however independent their logic is. `plan-waves.py` lists each one.

Split it by ownership:

1. Move each unit's logic into a file of its own, behind a fixed contract. These module units own different files and consume only contracts, so they share a wave.
2. Give the hotspot to one integrator unit. It owns the file whole, wires the modules in through their contracts, and waits on them, since its checks run the real code.
3. Give tests the same split: each module unit owns its module's test file, and the integrator owns the tests of the hotspot.

Three units that each edited one file in turn become three module units in one wave and one integrator behind them, and the plan's length in waves stops growing with the number of modules.

Leave a hotspot whole where the units' changes to it are small and entangled, and say so in the plan: those units join into one, or run in sequence, in the order they rewrite it. Units that change different regions of one file, naming their regions, share a wave without a split.

### Let researchers settle the next wave

Some unknowns sit behind work that has yet to run: whether a test kit supports a case, which assertion strings a later unit must rewrite, what a generated file looks like after the first wave. Settle during planning every one a read can settle now. For each of the rest, plan a researcher: a delegate that reads and reports while an earlier wave builds, so the next wave starts on answers. Give each researcher line its question, where it writes the answer, and the unit that consumes it.

## Write

- Give the plan a Contracts section ahead of Work, one entry per contract: its name, its statement in full inside a code fence, the file and unit that own its declaration, each unit that consumes it, and whether it is fixed or open.
- Under each open contract, state what stays open, which unit closes it, and how that unit tells its consumers.
- State once, in Constraints, how a contract changes: no unit changes a fixed contract. A worker that finds one wrong or insufficient stops that part of its work and reports the conflict, with the change it proposes, to whoever coordinates. The coordinator amends the plan's Contracts section, then tells every unit that provides or consumes it before any of them continues.
- Name beside each unit the contracts it provides and consumes, by the names the Contracts section uses.
- Put the contracts unit, where there is one, alone in the first wave.

## Verify

- Every boundary between two units carries a contract line, and every fixed one is stated in the plan as code a unit could paste.
- No unit consumes a contract the plan states only by name.
- Every remaining wait names code no contract can stand in for.
- Every hotspot `plan-waves.py` prints is either split or kept whole with its reason in the plan.
