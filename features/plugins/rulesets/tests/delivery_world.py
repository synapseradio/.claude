"""A configuration directory, and the entry functions of the hooks `hooks/hooks.json` wires, called in-process.

Each hook script is one call of its entry function in `rulesets.hook_entry`, so a call here with
the script's argv, the payload's bytes, and the world's environment answers as the script does.
`test_hooks_json.py` holds the commands themselves to the scripts and arguments called here.
"""

import contextlib
import functools
import io
import json
import os
import pathlib
import re
import shlex
import subprocess
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor

from rulesets import cli
from rulesets.delivery.parts import MAX_PARTS
from rulesets.hook_entry import (
    HookResult,
    deliver,
    record_load,
    record_spawn,
)

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOKS = PLUGIN_ROOT / "hooks"
HOOKS_JSON = HOOKS / "hooks.json"
LAUNCHER = HOOKS / "with-python.sh"
DELIVER = HOOKS / "deliver.py"
TOGGLE_SKILL = PLUGIN_ROOT / "skills" / "rulesets" / "SKILL.md"
CLI = PLUGIN_ROOT / "lib" / "rulesets" / "cli.py"


OPUS = "claude-opus-5-5"
HAIKU = "claude-haiku-4-5"
DECLARED = "models: opus haiku\n"

# Variables the engine reads, which the developer's own shell may set.
_ENGINE_PREFIXES = ("ANTHROPIC_", "CLAUDE_CODE_", "CLAUDE_CONTEXT_", "RULESETS_")


def scratch_environment(scratch: pathlib.Path) -> dict[str, str]:
    """The variables that point a hook at a scratch directory's home, cache, git config, and `config` directory."""
    return {
        "HOME": str(scratch / "home"),
        "XDG_CACHE_HOME": str(scratch / "cache"),
        "GIT_CONFIG_GLOBAL": str(scratch / "gitconfig"),
        "CLAUDE_CONFIG_DIR": str(scratch / "config"),
    }


def core_rules_config(scratch: pathlib.Path, rule_text: str) -> pathlib.Path:
    """The `config` directory under `scratch`, its pool giving every context one rule, `core-rules`."""
    world = World(scratch)
    world.rule("core-rules", rule_text)
    world.write_config(DECLARED + "defaults: core-rules\n")
    return world.config


type HookEntry = Callable[[Sequence[str], bytes, Mapping[str, str]], HookResult]

_RECORD_HOOKS: dict[str, HookEntry] = {
    "record-load.py": record_load,
    "record-spawn.py": record_spawn,
}


def call_hook(
    entry: HookEntry, argv: list[str], stdin: bytes, environ: Mapping[str, str]
) -> subprocess.CompletedProcess[str]:
    """`entry` called as its script calls it, with the part locks it took let go once it returns.

    The script's process exits after writing what the entry returned, which lets go of its locks;
    the release here stands in for that exit.
    """
    result = entry(argv, stdin, environ)
    result.release()
    return subprocess.CompletedProcess(argv, result.exit_code, result.stdout, result.stderr)


def call_main(
    main: Callable[[list[str]], int], arguments: Sequence[str]
) -> subprocess.CompletedProcess[str]:
    """A command line's `main` called in-process on `arguments`, with what it printed and its status.

    argparse ends a run it rejects by raising `SystemExit` with the status a process would exit with:
    https://docs.python.org/3.15/library/argparse.html#exiting-methods
    """
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            status = main(list(arguments))
        except SystemExit as exited:
            status = exited.code
    return subprocess.CompletedProcess(
        list(arguments), status, stdout.getvalue(), stderr.getvalue()
    )


def run_cli(
    arguments: Sequence[str], environ: Mapping[str, str]
) -> subprocess.CompletedProcess[str]:
    """`cli.py` on `arguments`, called in-process under the configuration `environ` names."""
    return call_main(functools.partial(cli.main, environ=environ), arguments)


_EXACT_MATCHER = re.compile(r"[\w\- ,|]+")


def matcher_admits(matcher: str | None, value: str) -> bool:
    """Whether the harness runs a hook group whose matcher is `matcher` for an event matched on `value`.

    https://code.claude.com/docs/en/hooks.md#matcher-patterns: an absent, empty, or `*` matcher
    admits every value, a matcher of plain characters lists exact values, and any other matcher
    is an unanchored regular expression.
    """
    if matcher in (None, "", "*"):
        return True
    if _EXACT_MATCHER.fullmatch(matcher):
        return value in [alternative.strip() for alternative in re.split(r"[|,]", matcher)]
    return re.search(matcher, value) is not None


def select_commands(groups: list[dict], value: str) -> list[str]:
    """The commands of the hook groups whose matcher admits `value`, in file order."""
    return [
        hook["command"]
        for group in groups
        if matcher_admits(group.get("matcher"), value)
        for hook in group["hooks"]
    ]


def delivered(rule: str, body: str) -> str:
    """A rule's body as a context receives it: the rule's marker, a blank line, then the body."""
    return f"<!-- rule: {rule} -->\n\n{body}"


_MARKER_AND_BLANK = re.compile(r"^<!-- rule: \S+ -->\n\n", re.MULTILINE)


def without_markers(text: str) -> str:
    """`text` less the marker and blank line delivery writes before each rule's body."""
    return _MARKER_AND_BLANK.sub("", text)


class Delivery:
    """What one event's hook entries printed: the agent's context and the person's message.

    `context` and `part_texts` hold the rule text alone, less the markers; `received` and
    `received_parts` hold the exact bytes.
    """

    def __init__(self, outputs: dict[int, str]) -> None:
        self.outputs = outputs
        parsed = {part: json.loads(text) for part, text in outputs.items() if text.strip()}
        self.received = "".join(
            parsed[part].get("hookSpecificOutput", {}).get("additionalContext", "")
            for part in sorted(parsed)
        )
        self.context = without_markers(self.received)
        self.messages = [
            parsed[part]["systemMessage"]
            for part in sorted(parsed)
            if "systemMessage" in parsed[part]
        ]
        self.targets = {
            parsed[part]["hookSpecificOutput"]["hookEventName"]
            for part in parsed
            if "hookSpecificOutput" in parsed[part]
        }

    @property
    def part_texts(self) -> dict[int, str]:
        """The rule text from each part that sent any, less the markers, by part number."""
        return {part: without_markers(text) for part, text in self.received_parts.items()}

    @property
    def received_parts(self) -> dict[int, str]:
        """The agent's context from each part that sent any, exactly, by part number."""
        found = {part: json.loads(text) for part, text in self.outputs.items() if text.strip()}
        return {
            part: output["hookSpecificOutput"]["additionalContext"]
            for part, output in found.items()
            if "hookSpecificOutput" in output
        }

    @property
    def message(self) -> str | None:
        return "\n".join(self.messages) if self.messages else None


class World:
    """One configuration directory with a rulesets directory, and the hooks run against it."""

    def __init__(self, tmp_path: pathlib.Path) -> None:
        self.config = tmp_path / "config"
        self.rulesets = self.config / "rulesets"
        self.environment: dict[str, str] = {}
        (self.rulesets / "rules").mkdir(parents=True)

    def rule(self, stem: str, text: str | None = None) -> pathlib.Path:
        path = self.rulesets / "rules" / f"{stem}.md"
        path.write_text(f"text of {stem}\n" if text is None else text, encoding="utf-8")
        return path

    def write_config(self, text: str) -> None:
        (self.rulesets / "config.yaml").write_text(text, encoding="utf-8")

    def toggle_flags(self, settings: dict[str, str], session_id: str = "s1") -> None:
        """The session state file a flag toggle leaves: each flag named `set` or `unset`."""
        path = self.config / ".tmp" / "rulesets-engine" / "session" / f"{session_id}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = ["flags:\n", *(f"  {flag}: {setting}" for flag, setting in settings.items())]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def state_file(self, session_id: str = "s1") -> pathlib.Path:
        return self.config / ".tmp" / "rulesets-engine" / "session" / f"{session_id}.yaml"

    @property
    def transcripts(self) -> pathlib.Path:
        """The project directory the harness keeps every transcript of one project in."""
        return self.config / "projects" / "-work-project"

    def record_files(self, session_id: str = "s1") -> pathlib.Path:
        return self.config / ".tmp" / "rulesets-engine" / "audit" / session_id

    def records(self, session_id: str = "s1") -> list[dict]:
        path = self.record_files(session_id) / "deliveries.jsonl"
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    def delegate_records(self, session_id: str = "s1") -> list[dict]:
        """The delivery records written for delegates."""
        return [record for record in self.records(session_id) if record["scope"] == "delegate"]

    def withheld_rules(self, session_id: str = "s1") -> list[str]:
        """The rule stems each delivery record lists as withheld, in record order."""
        return [w["rule"] for record in self.records(session_id) for w in record["withheld"]]

    def emitted_records(self, session_id: str = "s1") -> list[dict]:
        """The `emitted` records every later part of the session wrote, by part number."""
        files = sorted(self.record_files(session_id).glob("emitted-*.jsonl"))
        lines = [line for file in files for line in file.read_text(encoding="utf-8").splitlines()]
        return sorted((json.loads(line) for line in lines), key=lambda record: record["part"])

    def model_record(self, session_id: str = "s1") -> dict | None:
        """The session's model record as the engine keeps it, or None where none is written."""
        path = self.config / ".tmp" / "rulesets-engine" / "models" / f"{session_id}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def user_agent(self, agent_type: str, model: str) -> None:
        """An agent definition file that pins its model."""
        path = self.config / "agents" / f"{agent_type}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"---\nname: {agent_type}\ndescription: a test agent\nmodel: {model}\n---\nbody\n",
            encoding="utf-8",
        )

    def run_spawn_hook(
        self, stdin: str, environment: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        """The PreToolUse entry wired for the `Agent` tool, fed `stdin` as the harness feeds it."""
        env = {**self._environ(), **(environment or {})}
        argv = [str(HOOKS / "record-spawn.py")]
        return call_hook(record_spawn, argv, stdin.encode("utf-8"), env)

    def spawn(
        self,
        agent_type: str,
        model: str | None,
        prompt_id: str = "p1",
        session_id: str = "s1",
    ) -> subprocess.CompletedProcess[str]:
        """A caller spawning `agent_type`, as the PreToolUse payload of the `Agent` tool shows it."""
        tool_input = {
            "prompt": "Review the diff",
            "description": "Review the diff",
            "subagent_type": agent_type,
        }
        if model is not None:
            tool_input["model"] = model
        payload = {
            "session_id": session_id,
            "prompt_id": prompt_id,
            "transcript_path": str(self.transcripts / f"{session_id}.jsonl"),
            "cwd": str(self.config.parent),
            "permission_mode": "default",
            "hook_event_name": "PreToolUse",
            "tool_name": "Agent",
            "tool_input": tool_input,
            "tool_use_id": "toolu_01ABC123",
        }
        return self.run_spawn_hook(json.dumps(payload))

    def _environ(self) -> dict[str, str]:
        kept = {k: v for k, v in os.environ.items() if not k.startswith(_ENGINE_PREFIXES)}
        return {
            **kept,
            **scratch_environment(self.config.parent),
            "CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT),
            **self.environment,
        }

    def toggle(self, arguments: str, session_id: str = "s1") -> subprocess.CompletedProcess[str]:
        """The skill's toggle command, its placeholders filled as the harness and the model fill them.

        The harness substitutes `${CLAUDE_SESSION_ID}` and `${CLAUDE_PLUGIN_ROOT}` in a skill's
        text, and the model replaces `ACTION` with the action's words.
        https://code.claude.com/docs/en/skills.md
        The command runs `cli.py` through the launcher, so its words after the script's path are
        the arguments `cli.main` is called with.
        """
        assert TOGGLE_SKILL.is_file(), "the plugin ships skills/rulesets/SKILL.md"
        lines = TOGGLE_SKILL.read_text(encoding="utf-8").splitlines()
        commands = [line for line in lines if " toggle --session " in line]
        assert len(commands) == 1, f"one toggle command line in the skill, found {commands}"
        filled = (
            commands[0]
            .replace("${CLAUDE_SESSION_ID}", session_id)
            .replace("${CLAUDE_PLUGIN_ROOT}", str(PLUGIN_ROOT))
            .replace("ACTION", arguments)
        )
        words = shlex.split(filled)
        assert words[:3] == ["bash", str(LAUNCHER), str(CLI)], (
            f"the skill's toggle command runs cli.py through the launcher: {filled}"
        )
        return run_cli(words[3:], self._environ())

    def delivery_check(
        self, session_id: str = "s1", root: pathlib.Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        """The `delivery-check` subcommand, as the skill runs it."""
        return self._audit_command("delivery-check", session_id, root)

    def load_check(
        self, session_id: str = "s1", root: pathlib.Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        """The `load-check` subcommand."""
        return self._audit_command("load-check", session_id, root)

    def deliveries(self, session_id: str = "s1") -> subprocess.CompletedProcess[str]:
        """The `deliveries` subcommand."""
        return self._audit_command("deliveries", session_id, None)

    def _audit_command(
        self, subcommand: str, session_id: str, root: pathlib.Path | None
    ) -> subprocess.CompletedProcess[str]:
        arguments = [subcommand, "--session", session_id]
        if root is not None:
            arguments += ["--root", str(root)]
        return run_cli(arguments, self._environ())

    @property
    def project(self) -> pathlib.Path:
        """The project directory beside the configuration directory."""
        return self.config.parent / "project"

    def load_records(self, session_id: str = "s1") -> list[dict]:
        path = self.record_files(session_id) / "loads.jsonl"
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    def run_load_hook(
        self,
        stdin: str,
        environment: dict[str, str] | None = None,
        load_reason: str = "session_start",
    ) -> subprocess.CompletedProcess[str]:
        """The InstructionsLoaded entry, fed `stdin` as the harness feeds it, which it does for every `load_reason`."""
        env = {**self._environ(), **(environment or {})}
        argv = [str(HOOKS / "record-load.py")]
        return call_hook(record_load, argv, stdin.encode("utf-8"), env)

    def load(
        self,
        file_path: pathlib.Path | str,
        load_reason: str = "session_start",
        session_id: str = "s1",
        **extra,
    ) -> subprocess.CompletedProcess[str]:
        """The harness loading an instruction file, as the InstructionsLoaded payload shows it."""
        payload = {
            "session_id": session_id,
            "transcript_path": str(self.transcripts / f"{session_id}.jsonl"),
            "cwd": str(self.project),
            "hook_event_name": "InstructionsLoaded",
            "file_path": str(file_path),
            "memory_type": "Project",
            "load_reason": load_reason,
            **extra,
        }
        return self.run_load_hook(json.dumps(payload), load_reason=load_reason)

    def end_session(self, session_id: str = "s1") -> None:
        """The SessionEnd hook entry, fed the payload on stdin."""
        payload = {"session_id": session_id, "hook_event_name": "SessionEnd", "reason": "other"}
        done = call_hook(
            deliver,
            [str(DELIVER), "--end"],
            json.dumps(payload).encode("utf-8"),
            self._environ(),
        )
        assert done.returncode == 0, done.stderr

    def run_part_process(
        self, event: str, payload: dict, part: int
    ) -> subprocess.CompletedProcess[str]:
        """One hook entry of an event, fed the payload on stdin, with its exit status and stderr."""
        return call_hook(
            deliver,
            [str(DELIVER), "--part", str(part)],
            json.dumps({**payload, "hook_event_name": event}).encode("utf-8"),
            self._environ(),
        )

    def run_part(self, event: str, payload: dict, part: int) -> str:
        """The stdout of one hook entry of an event, fed the payload on stdin."""
        done = self.run_part_process(event, payload, part)
        assert done.returncode == 0, done.stderr
        return done.stdout

    def run_shell(self, command: str) -> subprocess.CompletedProcess[str]:
        """A shell command, run with the environment the hooks run in."""
        return subprocess.run(
            ["bash", "-c", command],
            capture_output=True,
            text=True,
            env=self._environ(),
            check=False,
        )

    def run_hook_bytes(
        self, last_argument: str, stdin: bytes
    ) -> subprocess.CompletedProcess[bytes]:
        """One hook entry, named by its command's last argument, fed raw bytes on stdin.

        `last_argument` is `--part K` or `--end` for `deliver.py`, or a record script's name with
        the closing quote its command gives it.
        """
        script = last_argument.removesuffix('"')
        if script in _RECORD_HOOKS:
            entry, argv = _RECORD_HOOKS[script], [str(HOOKS / script)]
        else:
            entry, argv = deliver, [str(DELIVER), *last_argument.split()]
        done = call_hook(entry, argv, stdin, self._environ())
        return subprocess.CompletedProcess(
            argv, done.returncode, done.stdout.encode("utf-8"), done.stderr.encode("utf-8")
        )

    def run_event(
        self, event: str, payload: dict, parts: range = range(1, MAX_PARTS + 1)
    ) -> Delivery:
        """Every entry of the event at once, as the harness runs them."""
        with ThreadPoolExecutor(max_workers=len(parts)) as pool:
            outputs = list(pool.map(lambda part: self.run_part(event, payload, part), parts))
        return Delivery(dict(zip(parts, outputs, strict=True)))

    def start_session(self, model: str | None = OPUS, session_id: str = "s1", **extra) -> Delivery:
        payload = {"session_id": session_id, "source": "startup", **extra}
        if model is not None:
            payload["model"] = model
        return self.run_event("SessionStart", payload)

    def switch_model(
        self,
        to_model: str,
        from_model: str | None,
        prompt_id: str | None = None,
        session_id: str = "s1",
    ) -> Delivery:
        """The PostModelSwitch entries, fed a payload shaped as the harness shapes it."""
        payload = {
            "session_id": session_id,
            "from_model": from_model,
            "to_model": to_model,
            "requested_model": "opus",
            "source": "command",
            "prompt_id": prompt_id,
        }
        named = {field: value for field, value in payload.items() if value is not None}
        return self.run_event("PostModelSwitch", named)

    def start_delegate(
        self, agent_type: str = "critic", session_id: str = "s1", agent_id: str = "a1", **extra
    ) -> Delivery:
        payload = {
            "session_id": session_id,
            "agent_id": agent_id,
            "agent_type": agent_type,
            "prompt_id": "p1",
            **extra,
        }
        named = {field: value for field, value in payload.items() if value is not None}
        return self.run_event("SubagentStart", named)
