"""A configuration directory and the hooks wired in `hooks/hooks.json`, run the way the harness runs them."""

import json
import os
import pathlib
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOKS_JSON = PLUGIN_ROOT / "hooks" / "hooks.json"
TOGGLE_SKILL = PLUGIN_ROOT / "skills" / "toggle" / "SKILL.md"
CLI = PLUGIN_ROOT / "lib" / "rulesets" / "cli.py"

OPUS = "claude-opus-5-5"
HAIKU = "claude-haiku-4-5"
DECLARED = "models: ['opus', 'haiku']\n"

# Variables the engine reads, which the developer's own shell may set.
_ENGINE_PREFIXES = ("ANTHROPIC_", "CLAUDE_CODE_", "CLAUDE_CONTEXT_", "RULESETS_")


# The payload field each event's matcher filters on.
_MATCHED_FIELD = {
    "SessionStart": "source",
    "SubagentStart": "agent_type",
    "PostModelSwitch": "to_model",
    "SessionEnd": "reason",
    "PreToolUse": "tool_name",
    "InstructionsLoaded": "load_reason",
}

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


def matched_value(event: str, payload: dict) -> str:
    """The text the harness matches the event's hook groups against."""

    value = payload.get(_MATCHED_FIELD[event])
    return value if isinstance(value, str) else ""


class Delivery:
    """What one event's hook entries printed: the agent's context and the person's message."""

    def __init__(self, outputs: dict[int, str]):
        self.outputs = outputs
        parsed = {part: json.loads(text) for part, text in outputs.items() if text.strip()}
        self.context = "".join(
            parsed[part].get("hookSpecificOutput", {}).get("additionalContext", "")
            for part in sorted(parsed)
        )
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
        """The agent's context from each part that sent any, by part number."""

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

    def __init__(self, tmp_path: pathlib.Path):
        self.config = tmp_path / "config"
        self.rulesets = self.config / "rulesets"
        self.environment: dict[str, str] = {}
        (self.rulesets / "rules").mkdir(parents=True)

    def rule(self, stem: str, text: str | None = None) -> pathlib.Path:
        path = self.rulesets / "rules" / f"{stem}.md"
        path.write_text(f"text of {stem}\n" if text is None else text, encoding="utf-8")
        return path

    def manifest(self, text: str) -> None:
        (self.rulesets / "manifest.yaml").write_text(text, encoding="utf-8")

    def toggle_flags(self, settings: dict[str, str], session_id: str = "s1") -> None:
        """The session state file a flag toggle leaves: each flag named `set` or `unset`."""

        path = self.config / ".tmp" / "rulesets-engine" / "session" / f"{session_id}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = ["flags:", *(f"  {flag}: {setting}" for flag, setting in settings.items())]
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
        return subprocess.run(
            ["bash", "-c", self._command("PreToolUse", 'record-spawn.py"', "Agent")],
            input=stdin,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

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
            "CLAUDE_CONFIG_DIR": str(self.config),
            "CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT),
            **self.environment,
        }

    def commands_for(self, event: str, value: str = "") -> list[str]:
        """The commands `hooks.json` runs for an event whose matcher field holds `value`."""

        groups = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))["hooks"][event]
        return select_commands(groups, value)

    def _command(self, event: str, last_argument: str, value: str = "") -> str:
        commands = self.commands_for(event, value)
        found = [c for c in commands if c.endswith(last_argument)]
        assert found, (
            f"no {event} entry ending {last_argument!r} runs where the matcher field is {value!r}"
        )
        return found[0]

    def toggle(self, arguments: str, session_id: str = "s1") -> subprocess.CompletedProcess[str]:
        """The command the toggle skill injects, with the placeholders filled as the harness fills them."""

        assert TOGGLE_SKILL.is_file(), "the plugin ships skills/toggle/SKILL.md"
        lines = TOGGLE_SKILL.read_text(encoding="utf-8").splitlines()
        command = next(line[2:-1] for line in lines if line.startswith("!`") and line.endswith("`"))
        filled = command.replace("${CLAUDE_SESSION_ID}", session_id).replace(
            "$ARGUMENTS", arguments
        )
        return subprocess.run(
            ["bash", "-c", filled],
            capture_output=True,
            text=True,
            env=self._environ(),
            check=False,
        )

    def delivery_check(
        self, session_id: str = "s1", root: pathlib.Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        """The `delivery-check` subcommand, run through the launcher as the skill runs it."""

        return self._audit_command("delivery-check", session_id, root)

    def load_check(
        self, session_id: str = "s1", root: pathlib.Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        """The `load-check` subcommand, run through the launcher."""

        return self._audit_command("load-check", session_id, root)

    def deliveries(self, session_id: str = "s1") -> subprocess.CompletedProcess[str]:
        """The `deliveries` subcommand, run through the launcher."""

        return self._audit_command("deliveries", session_id, None)

    def _audit_command(
        self, subcommand: str, session_id: str, root: pathlib.Path | None
    ) -> subprocess.CompletedProcess[str]:
        arguments = [subcommand, "--session", session_id]
        if root is not None:
            arguments += ["--root", str(root)]
        return subprocess.run(
            ["bash", str(PLUGIN_ROOT / "hooks" / "with-python.sh"), str(CLI), *arguments],
            capture_output=True,
            text=True,
            env=self._environ(),
            check=False,
        )

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
        """The InstructionsLoaded entry for a load of `load_reason`, fed `stdin` as the harness feeds it."""

        env = {**self._environ(), **(environment or {})}
        return subprocess.run(
            ["bash", "-c", self._command("InstructionsLoaded", 'record-load.py"', load_reason)],
            input=stdin,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

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

        done = subprocess.run(
            ["bash", "-c", self._command("SessionEnd", "--end", "other")],
            input=json.dumps(
                {"session_id": session_id, "hook_event_name": "SessionEnd", "reason": "other"}
            ),
            capture_output=True,
            text=True,
            env=self._environ(),
            check=False,
        )
        assert done.returncode == 0, done.stderr

    def run_part_process(
        self, event: str, payload: dict, part: int
    ) -> subprocess.CompletedProcess[str]:
        """One hook entry of an event, fed the payload on stdin, with its exit status and stderr."""

        return subprocess.run(
            ["bash", "-c", self._command(event, f"--part {part}", matched_value(event, payload))],
            input=json.dumps({**payload, "hook_event_name": event}),
            capture_output=True,
            text=True,
            env=self._environ(),
            check=False,
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
        self, event: str, last_argument: str, stdin: bytes, matched: str = ""
    ) -> subprocess.CompletedProcess[bytes]:
        """One hook entry of an event whose matcher field holds `matched`, fed raw bytes on stdin."""

        return subprocess.run(
            ["bash", "-c", self._command(event, last_argument, matched)],
            input=stdin,
            capture_output=True,
            env=self._environ(),
            check=False,
        )

    def run_event(self, event: str, payload: dict, parts: range = range(1, 11)) -> Delivery:
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
