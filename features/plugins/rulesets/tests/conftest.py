import json
import pathlib
import sys

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets import spawn_log  # noqa: E402  (path must be set before this import)
from rulesets.facts.model import delegate as delegate_model  # noqa: E402
from rulesets.facts.model import record as model_record  # noqa: E402
from rulesets.facts.model.fact import ModelFact, ModelResolution  # noqa: E402

DECLARED_MODELS = ["opus", "sonnet", "haiku", "fable"]


@pytest.fixture(autouse=True)
def isolated_config_directory(monkeypatch, tmp_path_factory) -> None:
    """Point every test at an empty configuration directory.

    The resolver reads agent definitions from `<config>/agents`, so without
    this a test reads the definitions of whoever runs it. A test that needs
    a configuration directory of its own sets one over this.
    """
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path_factory.mktemp("config")))


class Scene:
    """One session's world: its state, its configuration directory, and its project."""

    def __init__(self, tmp_path) -> None:
        self.state = tmp_path / "state"
        self.config = tmp_path / "config"
        self.project = tmp_path / "project"
        (self.project / ".git").mkdir(parents=True)
        (self.project / "sub").mkdir()

    def parent_runs(self, identifier, session_id="s1") -> None:
        model_record.write_model_record(session_id, identifier, self.state)

    def caller_names(
        self, model, *, prompt_id="p1", agent_type="general-purpose", session="s1"
    ) -> None:
        spawn_log.append_spawn(session, prompt_id, agent_type, model, self.state)

    def define(self, directory, filename, front) -> pathlib.Path:
        path = directory / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\n{front}\n---\nbody\n", encoding="utf-8")
        return path

    @staticmethod
    def registered(filename, front) -> str:
        """The frontmatter lines with the `name` and `description` the harness requires of a file.

        A line the caller wrote stands; the file stem names an agent that names none.
        """
        lines = front.splitlines()
        if not any(line.startswith("name:") for line in lines):
            lines.insert(0, f"name: {pathlib.PurePath(filename).stem}")
        if not any(line.startswith("description:") for line in lines):
            lines.append("description: a test agent")
        return "\n".join(lines)

    def user_agent(self, filename, front) -> pathlib.Path:
        return self.define(self.config / "agents", filename, self.registered(filename, front))

    def project_agent(self, filename, front, *, under=None) -> pathlib.Path:
        return self.define(
            (under or self.project) / ".claude" / "agents",
            filename,
            self.registered(filename, front),
        )

    def install_plugin(self, key="kit@market") -> pathlib.Path:
        install = self.config.parent / "installs" / key
        (self.config / "plugins").mkdir(parents=True, exist_ok=True)
        (self.config / "plugins" / "installed_plugins.json").write_text(
            json.dumps({"version": 2, "plugins": {key: [{"installPath": str(install)}]}}),
            encoding="utf-8",
        )
        return install

    def resolve(
        self, agent_type="general-purpose", *, env=None, models=None, **payload
    ) -> ModelResolution:
        start = {"session_id": "s1", "agent_id": "a1", "prompt_id": "p1", "agent_type": agent_type}
        start = {key: value for key, value in (start | payload).items() if value is not None}
        return delegate_model.resolve_delegate_model(
            start,
            DECLARED_MODELS if models is None else models,
            env or {},
            self.state,
            self.config,
        )

    def fact(self, agent_type="general-purpose", **kwargs) -> ModelFact:
        return self.resolve(agent_type, **kwargs).fact


@pytest.fixture
def scene(tmp_path) -> Scene:
    return Scene(tmp_path)
