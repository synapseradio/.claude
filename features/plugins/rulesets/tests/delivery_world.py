"""A configuration directory and the hooks wired in `hooks/hooks.json`, run the way the harness runs them."""

import json
import os
import pathlib
import subprocess
from concurrent.futures import ThreadPoolExecutor

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOKS_JSON = PLUGIN_ROOT / "hooks" / "hooks.json"
TOGGLE_SKILL = PLUGIN_ROOT / "skills" / "toggle" / "SKILL.md"

OPUS = "claude-opus-5-5"
HAIKU = "claude-haiku-4-5"
DECLARED = "models: ['opus', 'haiku']\n"

# Variables the engine reads, which the developer's own shell may set.
_ENGINE_PREFIXES = ("ANTHROPIC_", "CLAUDE_CODE_", "CLAUDE_CONTEXT_", "RULESETS_")


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

    def _environ(self) -> dict[str, str]:
        kept = {k: v for k, v in os.environ.items() if not k.startswith(_ENGINE_PREFIXES)}
        return {
            **kept,
            "CLAUDE_CONFIG_DIR": str(self.config),
            "CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT),
            **self.environment,
        }

    def _command(self, event: str, last_argument: str) -> str:
        groups = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))["hooks"][event]
        commands = [hook["command"] for group in groups for hook in group["hooks"]]
        return next(c for c in commands if c.endswith(last_argument))

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

    def end_session(self, session_id: str = "s1") -> None:
        """The SessionEnd hook entry, fed the payload on stdin."""

        done = subprocess.run(
            ["bash", "-c", self._command("SessionEnd", "--end")],
            input=json.dumps(
                {"session_id": session_id, "hook_event_name": "SessionEnd", "reason": "other"}
            ),
            capture_output=True,
            text=True,
            env=self._environ(),
            check=False,
        )
        assert done.returncode == 0, done.stderr

    def run_part(self, event: str, payload: dict, part: int) -> str:
        """The stdout of one hook entry of an event, fed the payload on stdin."""

        done = subprocess.run(
            ["bash", "-c", self._command(event, f"--part {part}")],
            input=json.dumps({**payload, "hook_event_name": event}),
            capture_output=True,
            text=True,
            env=self._environ(),
            check=False,
        )
        assert done.returncode == 0, done.stderr
        return done.stdout

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
