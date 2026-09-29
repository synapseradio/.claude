import pytest


@pytest.fixture(autouse=True)
def isolated_config_directory(monkeypatch, tmp_path_factory):
    """Point every test at an empty configuration directory.

    The resolver reads agent definitions from `<config>/agents`, so without
    this a test reads the definitions of whoever runs it. A test that needs
    a configuration directory of its own sets one over this.
    """

    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path_factory.mktemp("config")))
