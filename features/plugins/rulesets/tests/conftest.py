import json
import pathlib
import sys

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets import spawn_log  # noqa: E402  (path must be set before this import)
from rulesets.facts.model import delegate as delegate_model  # noqa: E402
from rulesets.facts.model import record as model_record  # noqa: E402

DECLARED_MODELS = ["opus", "sonnet", "haiku", "fable"]


@pytest.fixture(autouse=True)
def isolated_config_directory(monkeypatch, tmp_path_factory):
    """Point every test at an empty configuration directory.

    The resolver reads agent definitions from `<config>/agents`, so without
    this a test reads the definitions of whoever runs it. A test that needs
    a configuration directory of its own sets one over this.
    """

    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path_factory.mktemp("config")))


class Scene:
    """One session's world: its state, its configuration directory, and its project."""

    def __init__(self, tmp_path):
        self.state = tmp_path / "state"
        self.config = tmp_path / "config"
        self.project = tmp_path / "project"
        (self.project / ".git").mkdir(parents=True)
        (self.project / "sub").mkdir()

    def parent_runs(self, identifier, session_id="s1"):
        model_record.write_model_record(session_id, identifier, self.state)

    def caller_names(self, model, *, prompt_id="p1", agent_type="general-purpose", session="s1"):
        spawn_log.append_spawn(session, prompt_id, agent_type, model, self.state)

    def define(self, directory, filename, front):
        path = directory / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\n{front}\n---\nbody\n", encoding="utf-8")
        return path

    def user_agent(self, filename, front):
        return self.define(self.config / "agents", filename, front)

    def project_agent(self, filename, front, *, under=None):
        return self.define((under or self.project) / ".claude" / "agents", filename, front)

    def install_plugin(self, key="kit@market"):
        install = self.config.parent / "installs" / key
        (self.config / "plugins").mkdir(parents=True, exist_ok=True)
        (self.config / "plugins" / "installed_plugins.json").write_text(
            json.dumps({"version": 2, "plugins": {key: [{"installPath": str(install)}]}}),
            encoding="utf-8",
        )
        return install

    def resolve(self, agent_type="general-purpose", *, env=None, models=None, **payload):
        start = {"session_id": "s1", "agent_id": "a1", "prompt_id": "p1", "agent_type": agent_type}
        start = {key: value for key, value in (start | payload).items() if value is not None}
        return delegate_model.resolve_delegate_model(
            start,
            DECLARED_MODELS if models is None else models,
            env or {},
            self.state,
            self.config,
        )

    def fact(self, agent_type="general-purpose", **kwargs):
        return self.resolve(agent_type, **kwargs).fact


class ReadSpy(dict):
    """An environment that remembers each name the engine asked it for."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reads: set[str] = set()

    def get(self, key, default=None):
        self.reads.add(key)
        return super().get(key, default)

    def __getitem__(self, key):
        self.reads.add(key)
        return super().__getitem__(key)

    def __contains__(self, key):
        self.reads.add(key)
        return super().__contains__(key)


@pytest.fixture
def scene(tmp_path):
    return Scene(tmp_path)


@pytest.fixture
def read_spy():
    """The environment class that records which names the engine reads."""

    return ReadSpy


@pytest.fixture
def definition_reads(monkeypatch):
    """The agent types whose definitions a delegate's model fact looked up, in order."""

    reads: list[str] = []
    look_up = delegate_model.agent_model

    def recording(agent_type, cwd, config_dir):
        reads.append(agent_type)
        return look_up(agent_type, cwd, config_dir)

    monkeypatch.setattr(delegate_model, "agent_model", recording)
    return reads
