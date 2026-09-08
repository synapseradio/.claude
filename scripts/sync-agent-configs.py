#!/usr/bin/env python3.14
"""Project Claude Code's canonical configuration onto pi and opencode.

A checkout carries `CLAUDE.md`, the rules under `rules/`, and the agent
definitions under `agents/`. This script reads the checkout it sits in,
resolved from its own path, so a hook running inside a worktree syncs that
worktree. pi and opencode read their own formats from their own directories,
and this script writes those, so the three agents run on the same behavioral
configuration and on whichever checkout last ran it.

`references/working-rules.md` renders `CLAUDE.md` and the always-on rules as
one document, in the order `WORKING_RULES_ORDER` names. That render and
those sources are two forms of one text, and this script moves between them
in either direction. With no argument it writes the render from the sources.
With `--reverse` it splits the render back into `CLAUDE.md` and the rules
files, writing no other output. One run moves text one way, and each
direction reproduces the other's input byte for byte.

Both directions read tag-form sources: `CLAUDE.md` opens on `<hello`, and
each rules file carries one `<rule name="stem">` element whose name is the
filename. A source in any other form stops the run before it writes.

Each direction writes its target side whole, so it refuses where a file it
would write carries changes git has not seen, naming each one. Commit those
changes and run again. No flag overrides the refusal.

`--check` compares without writing and exits nonzero where any output
differs from what a write would produce, which is what the pre-push hook
gates on. It composes with `--reverse`.

Every generated file is owned end to end: the script rewrites it whole and
never merges into hand-written content. One exception carries its own rule:
opencode's `instructions` array lists rule files rather than holding their
text, so it lives inside the hand-written `opencode.json`. The script owns
that one key and leaves every other key in the file as it found it.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "agent-configs"))

from projection import (
    DEFAULT_TARGETS,
    GeneratedFile,
    Plan,
    Targets,
    apply_plan,
    refuse_uncommitted,
)

# `restore_paths`, `parse_document`, `read_agent`, and `rewrite_paths` moved
# with the render and translation jobs below; nothing in this shim's own
# remaining code calls them, but test_sync_agent_configs.py still reads them
# from here, so each import re-exports its name under itself rather than let
# a lint pass drop it.
from projection import parse_document as parse_document
from projection import read_agent as read_agent
from projection import restore_paths as restore_paths
from projection import rewrite_paths as rewrite_paths

# render-working-rules.py is a job, invoked by path and never imported, per
# the convention every job under agent-configs/ follows. This shim still
# promises `build_working_rules`, `build_reverse_plan`, `RuleSection`,
# `TITLE`, and `parse_reference` to whatever already reads them from here, so
# it loads the job by path exactly as a test loads this module, rather than
# keeping a second copy of what that job now owns.
_RENDER_PATH = Path(__file__).resolve().parent / "agent-configs" / "render-working-rules.py"
_render_spec = importlib.util.spec_from_file_location("render_working_rules", _RENDER_PATH)
assert _render_spec is not None and _render_spec.loader is not None
render_working_rules = importlib.util.module_from_spec(_render_spec)
sys.modules["render_working_rules"] = render_working_rules
_render_spec.loader.exec_module(render_working_rules)

RuleSection = render_working_rules.RuleSection
TITLE = render_working_rules.TITLE
build_working_rules = render_working_rules.build_working_rules
parse_reference = render_working_rules.parse_reference

# The job's own `build_reverse_plan` takes a `check` keyword the job's own
# `--check` uses to skip the uncommitted-changes guard on a read-only run.
# Every call written against this shim omits it, so `check` stays False and
# the guard still runs on every call here, matching what those calls expect.
build_reverse_plan = render_working_rules.build_reverse_plan


# translate-for-pi.py, translate-for-opencode.py, and own-opencode-key.py are
# jobs, invoked by path and never imported, the same convention
# render-working-rules.py follows above. This shim still promises
# `build_agents_markdown`, `resolve_skill_paths`, `translate_for_pi`, and
# `translate_for_opencode` to whatever already reads them from here, so it
# loads each job by path exactly as it loads the render job, rather than
# keeping a second copy of what each job now owns.
def _load_job(name: str, filename: str):
    path = Path(__file__).resolve().parent / "agent-configs" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


translate_for_pi_job = _load_job("translate_for_pi_job", "translate-for-pi.py")
translate_for_opencode_job = _load_job("translate_for_opencode_job", "translate-for-opencode.py")
own_opencode_key_job = _load_job("own_opencode_key_job", "own-opencode-key.py")

build_agents_markdown = translate_for_pi_job.build_agents_markdown
resolve_skill_paths = translate_for_pi_job.resolve_skill_paths
translate_for_pi = translate_for_pi_job.translate_for_pi
translate_for_opencode = translate_for_opencode_job.translate_for_opencode


def build_plan(targets: Targets = DEFAULT_TARGETS) -> Plan:
    refuse_uncommitted(targets.claude_home, [targets.working_rules])
    pi_plan = translate_for_pi_job.build_plan(targets)
    opencode_plan = translate_for_opencode_job.build_plan(targets)
    key_plan = own_opencode_key_job.build_plan(targets)
    files = (
        GeneratedFile(
            targets.working_rules,
            build_working_rules(targets.claude_md, targets.rules_dir, targets.working_rules_order),
        ),
        *pi_plan.files,
        *opencode_plan.files,
    )
    return Plan(
        files=files,
        keys=key_plan.keys,
        dropped=pi_plan.dropped + opencode_plan.dropped,
    )


def main(argv: list[str] | None = None, targets: Targets = DEFAULT_TARGETS) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="write nothing; exit nonzero when any generated file is out of date",
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="split the render back into CLAUDE.md and the rules files, writing no other output",
    )
    args = parser.parse_args(argv)
    build = build_reverse_plan if args.reverse else build_plan
    return apply_plan(build(targets), check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
