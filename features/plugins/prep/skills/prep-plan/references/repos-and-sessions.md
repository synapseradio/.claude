# Several repositories, several sessions

Read the first part when the change touches more than one repository, and the second when the work outgrows one context or waits on something outside the session. Both are boundaries no shared working tree or shared memory spans, so everything that crosses them is written down.

## Several repositories

### Gather

- Run `scripts/detect-tools.py --repo [path]` once per repository. Each has its own trunk, primary checkout, hooks, and task runner.
- Find every contract between repositories: an API route and its payload, a package's exported names and its version, a schema, a shared config key, a file one writes and another reads. Fix each in the plan. These are the contracts most worth fixing, since no type checker spans the gap.
- Decide the landing order from those contracts. A provider lands before its consumer, unless the consumer tolerates both old and new for a while; then either order holds, and the plan says which removal ends the overlap.
- Find how one repository receives another's change: a published version, a pinned commit, a linked checkout. That step is a unit of its own, owned by the consuming repository.
- Read each repository's contribution rules. Branch names, commit forms, and review requirements differ between them.

### Write

- Give each repository a block from `assets/repo-block.md`, holding its root, trunk, checks, and units. Entry paths inside a block resolve against that block's root.
- State cross-repository contracts in the plan's Contracts section, each naming the repository that owns it.
- With workers, give each repository's work to workers that stay inside it. An agent that edits two repositories carries two sets of rules and hooks, and mixes them.
- Give Verification one check that runs across the repositories as a person would use them together, after every block lands.
- Keep each repository's paths and tools out of the other's commits and tests.

### Verify

- Every contract between repositories is fixed, with its owning repository named.
- The landing order follows from the contracts, and every overlap has an end.
- Each block's checks ran in its own repository.

## Several sessions

A session ends where its context fills, or where the work must wait: on a review, a deploy, a long job, a person's answer. Plan the boundary so the next session starts cold and loses nothing.

### Gather

- Place each boundary at a wave's end, with everything landed. A handoff in the middle of a unit hands over half-held state nobody wrote down.
- For each boundary, name what the next session waits on and the command or page that shows it arrived.
- Hold an outside gate, a deploy or a release for one, as ordering the step it guards and nothing else. Units on both sides of a fixed contract build in the same wave; only shipping, or whatever needs the deployed thing, sits after the handoff. A gate is never written as a unit's wait, and no unit's landing waits on one; only the step that ships or uses the deployed thing does.
- Find where a handoff note lives here. Where the session's rules or a skill define a place and a form for one, use theirs. Otherwise the note sits beside the plan file.

### Write

- Split Work into one part per session, each ending in a handoff step that fills `assets/handoff-note.md`.
- Write each part so its session needs only the plan file and the note before it. Repeat nothing the plan holds; the note carries what the session learned and what the plan could not know.
- Open each later part with a step that reads the note and confirms the awaited event with its command.

### Verify

- Every session part starts from a state the plan describes, and ends with every commit landed and a note written.
- No part depends on what an earlier session knew and never wrote down.
