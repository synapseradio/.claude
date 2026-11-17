"""Tests for hooks/with-python.sh, the uv launcher every hook command runs through.

Hook commands name the launcher instead of an interpreter directly. Run from the plugin root:

    python3 -m unittest discover -s tests -p test_with_python.py -v

The launcher hands every hook script to `uv run --python 3.14 --no-project`.
Most tests put a mock `uv` in a temporary directory that becomes the child
process's whole PATH, so they never depend on a real uv or on which
interpreters the machine has. One test runs the real uv where it can serve a
3.14 interpreter without the network. Every child runs with an isolated
HOME, XDG, and git config, and with CLAUDE_PLUGIN_DATA in a temporary
directory, the only place the launcher may install anything. No test
downloads anything: a stub curl stands in for the network.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import isolated_environment

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = PLUGIN_ROOT / "hooks" / "with-python.sh"

PROBE_SCRIPT = "print('PROBE-OK')\n"
VERSION_SCRIPT = "import sys\nprint('.'.join(map(str, sys.version_info[:2])))\n"


def make_executable(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def recording_uv(path: Path, record: Path, real_interpreter: str) -> None:
    """A stand-in uv that records its arguments and runs its last one as the script.

    The tests give the launcher a script and no further arguments, so the
    script is the final argument the launcher passes to uv. The uv-related
    environment it was started with goes in a file beside the record.
    """
    make_executable(
        path,
        "#!/bin/bash\n"
        f'printf "%s\\n" "$@" > "{record}"\n'
        f'printf "%s\\n%s\\n" "${{UV_PYTHON_INSTALL_DIR-}}" "${{UV_CACHE_DIR-}}" > "{record}.env"\n'
        f'exec "{real_interpreter}" "${{@: -1}}"\n',
    )


def run_launcher(
    script: Path, child_environment: dict[str, str], stdin: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/bash", str(LAUNCHER), str(script)],
        capture_output=True,
        text=True,
        input=stdin,
        env=child_environment,
        timeout=10,
    )


class TheLauncherHandsTheScriptToUvAt3_14(unittest.TestCase):
    def test_uv_runs_the_script_at_3_14_with_no_project(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            scratch = Path(scratch)
            bindir = scratch / "bin"
            bindir.mkdir()
            record = scratch / "uv-args.txt"
            recording_uv(bindir / "uv", record, sys.executable)
            script = scratch / "probe.py"
            script.write_text(PROBE_SCRIPT)

            data = scratch / "data"
            result = run_launcher(
                script,
                isolated_environment(scratch / "home", path_dirs=[str(bindir)], plugin_data=data),
            )
            args = record.read_text().splitlines()
            uv_environment = Path(f"{record}.env").read_text().splitlines()

        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "PROBE-OK"
        assert args[0] == "run"
        assert args[args.index("--python") + 1] == "3.14"
        assert "--no-project" in args, "the repository's own requirement must not pick the Python"
        assert args[-1] == str(script)
        assert uv_environment == [str(data / "python"), str(data / "uv-cache")], (
            "a downloaded Python and uv's cache must land in the plugin data directory"
        )

    def test_stdin_reaches_the_script(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            scratch = Path(scratch)
            bindir = scratch / "bin"
            bindir.mkdir()
            recording_uv(bindir / "uv", scratch / "uv-args.txt", sys.executable)
            script = scratch / "echo.py"
            script.write_text("import sys\nsys.stdout.write(sys.stdin.read())\n")

            result = run_launcher(
                script,
                isolated_environment(
                    scratch / "home", path_dirs=[str(bindir)], plugin_data=scratch / "data"
                ),
                stdin='{"a": 1}',
            )

        assert result.returncode == 0, result.stderr
        assert result.stdout == '{"a": 1}'


INSTALLER_URL = "https://astral.sh/uv/install.sh"
LAUNCHER_TOOLS = (
    "sh",
    "bash",
    "mktemp",
    "rm",
    "date",
    "cat",
    "mkdir",
    "chmod",
    "dirname",
    "grep",
    "head",
    "sed",
)


def tools_directory(scratch: Path) -> Path:
    """A directory of symlinks to the system tools the launcher needs, and no curl, wget, or uv."""
    tools = scratch / "tools"
    tools.mkdir()
    for name in LAUNCHER_TOOLS:
        found = shutil.which(name)
        if found is not None:
            (tools / name).symlink_to(found)
    return tools


def stub_curl(path: Path, log: Path, installer_body: str, exit_code: int = 0) -> None:
    """A curl that logs its arguments and writes `installer_body` to the file named after -o.

    The launcher downloads Astral's installer to a temporary file with
    `curl -LsSf -o <file> <url>`, then runs that file with sh. The stub serves
    a fake installer in place of the network.
    """
    make_executable(
        path,
        "#!/bin/bash\n"
        f'printf "%s\\n" "$*" >> "{log}"\n'
        f"if (( {exit_code} != 0 )); then exit {exit_code}; fi\n"
        "while (( $# > 0 )); do\n"
        '  if [[ "$1" == -o ]]; then target="$2"; fi\n'
        "  shift\n"
        "done\n"
        f"cat > \"$target\" <<'INSTALLER'\n{installer_body}INSTALLER\n",
    )


def fake_installer(record: Path, real_interpreter: str) -> str:
    """An installer that puts a recording uv in UV_INSTALL_DIR and notes its own environment."""
    return (
        'mkdir -p "$UV_INSTALL_DIR"\n'
        f'echo "NO_MODIFY=$UV_NO_MODIFY_PATH INSTALL_DIR=$UV_INSTALL_DIR ARGS=$*"'
        f' > "{record.parent / "installer-env.txt"}"\n'
        "cat > \"$UV_INSTALL_DIR/uv\" <<'UV'\n"
        "#!/bin/bash\n"
        f'printf "%s\\n" "$@" > "{record}"\n'
        f'exec "{real_interpreter}" "${{@: -1}}"\n'
        "UV\n"
        'chmod +x "$UV_INSTALL_DIR/uv"\n'
    )


class TheLauncherInstallsAMissingUv(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch_dir.cleanup)
        self.scratch = Path(self.scratch_dir.name)
        self.home = self.scratch / "home"
        self.data = self.scratch / "plugin-data"
        self.tools = tools_directory(self.scratch)
        self.stubs = self.scratch / "stubs"
        self.stubs.mkdir()
        self.curl_log = self.scratch / "curl-log.txt"
        self.uv_record = self.scratch / "uv-args.txt"
        self.script = self.scratch / "probe.py"
        self.script.write_text(PROBE_SCRIPT)

    def environment(self) -> dict[str, str]:
        child_environment = isolated_environment(
            self.home, path_dirs=[str(self.stubs), str(self.tools)], plugin_data=self.data
        )
        child_environment["TMPDIR"] = str(self.scratch)
        return child_environment

    def test_it_downloads_installs_into_the_data_dir_and_runs_the_script_through_the_new_uv(
        self,
    ) -> None:
        stub_curl(
            self.stubs / "curl",
            self.curl_log,
            fake_installer(self.uv_record, sys.executable),
        )

        result = run_launcher(self.script, self.environment())

        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "PROBE-OK", "installer output must stay off stdout"
        assert (self.data / "bin" / "uv").is_file()
        assert not (self.home / ".local").exists(), "nothing is installed in home"
        assert INSTALLER_URL in self.curl_log.read_text()
        installer_env = (self.scratch / "installer-env.txt").read_text()
        assert "NO_MODIFY=1" in installer_env, "the installer must not edit shell profiles"
        assert f"INSTALL_DIR={self.data / 'bin'}" in installer_env
        args = self.uv_record.read_text().splitlines()
        assert args[args.index("--python") + 1] == "3.14"
        assert list(self.scratch.glob("uv-install.*")) == [], "the downloaded installer is removed"

    def test_it_reuses_a_uv_already_in_the_data_dir_without_downloading(self) -> None:
        data_bin = self.data / "bin"
        data_bin.mkdir(parents=True)
        recording_uv(data_bin / "uv", self.uv_record, sys.executable)
        stub_curl(self.stubs / "curl", self.curl_log, "exit 1\n")

        result = run_launcher(self.script, self.environment())

        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "PROBE-OK"
        assert not self.curl_log.exists(), "an installed uv needs no download"

    def test_a_uv_on_the_path_wins_over_the_data_dir_and_downloads_nothing(self) -> None:
        data_bin = self.data / "bin"
        data_bin.mkdir(parents=True)
        recording_uv(data_bin / "uv", self.scratch / "data-uv-args.txt", sys.executable)
        recording_uv(self.stubs / "uv", self.uv_record, sys.executable)
        stub_curl(self.stubs / "curl", self.curl_log, "exit 1\n")

        result = run_launcher(self.script, self.environment())

        assert result.returncode == 0, result.stderr
        assert self.uv_record.exists()
        assert not (self.scratch / "data-uv-args.txt").exists()
        assert not self.curl_log.exists()
        assert not (self.home / ".local").exists()


class TheLauncherReportsAnInstallThatCannotHappen(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch_dir.cleanup)
        self.scratch = Path(self.scratch_dir.name)
        self.tools = tools_directory(self.scratch)
        self.script = self.scratch / "probe.py"
        self.script.write_text(PROBE_SCRIPT)

    def environment(self, curl_stub: bool = False) -> dict[str, str]:
        path_dirs = [str(self.tools)]
        if curl_stub:
            path_dirs.insert(0, str(self.scratch / "stubs"))
        child_environment = isolated_environment(
            self.scratch / "home", path_dirs=path_dirs, plugin_data=self.scratch / "plugin-data"
        )
        child_environment["TMPDIR"] = str(self.scratch)
        return child_environment

    def stub(self, installer_body: str, exit_code: int = 0) -> None:
        (self.scratch / "stubs").mkdir(exist_ok=True)
        stub_curl(
            self.scratch / "stubs" / "curl",
            self.scratch / "curl-log.txt",
            installer_body,
            exit_code,
        )

    def run_failing(
        self, event: str, stop_hook_active: bool = False, curl_stub: bool = False
    ) -> subprocess.CompletedProcess[str]:
        """Run the launcher on `event` where no uv can be found or installed."""
        payload = json.dumps({"hook_event_name": event, "stop_hook_active": stop_hook_active})
        return run_launcher(self.script, self.environment(curl_stub), stdin=payload)

    def assert_model_and_user_both_told(
        self, result: subprocess.CompletedProcess[str], event: str
    ) -> str:
        """Check the stdout JSON for `event` and return the text the model is sent."""
        assert result.returncode == 0, result.stderr
        output = json.loads(result.stdout)
        text = output["systemMessage"]
        assert "uv" in text
        assert "3.14" in text
        assert "uv" in result.stderr, "the stderr line stays for a person reading the log"
        specific = output.get("hookSpecificOutput", {})
        model_text = (
            output.get("reason")
            or specific.get("additionalContext")
            or specific.get("permissionDecisionReason")
        )
        assert model_text == text, f"{event}: the model must be sent what the user is shown"
        return model_text

    def test_session_start_and_subagent_start_send_additional_context(self) -> None:
        for event in ("SessionStart", "SubagentStart"):
            with self.subTest(event=event):
                result = self.run_failing(event)
                self.assert_model_and_user_both_told(result, event)
                specific = json.loads(result.stdout)["hookSpecificOutput"]
                assert specific["hookEventName"] == event
                assert "decision" not in json.loads(result.stdout)

    def test_post_tool_batch_sends_additional_context_and_does_not_block(self) -> None:
        result = self.run_failing("PostToolBatch")
        self.assert_model_and_user_both_told(result, "PostToolBatch")
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["hookEventName"] == "PostToolBatch"
        assert "decision" not in output

    def test_pre_tool_use_denies_with_the_reason_the_model_reads(self) -> None:
        result = self.run_failing("PreToolUse")
        self.assert_model_and_user_both_told(result, "PreToolUse")
        specific = json.loads(result.stdout)["hookSpecificOutput"]
        assert specific["hookEventName"] == "PreToolUse"
        assert specific["permissionDecision"] == "deny"

    def test_stop_and_subagent_stop_block_with_the_reason_the_model_reads(self) -> None:
        for event in ("Stop", "SubagentStop"):
            with self.subTest(event=event):
                result = self.run_failing(event)
                self.assert_model_and_user_both_told(result, event)
                assert json.loads(result.stdout)["decision"] == "block"

    def test_a_stop_already_continued_by_the_failure_says_nothing_more(self) -> None:
        for event in ("Stop", "SubagentStop"):
            with self.subTest(event=event):
                result = self.run_failing(event, stop_hook_active=True)
                assert result.returncode == 0, result.stderr
                assert result.stdout == "", "a second block would loop until the harness cap"

    def test_an_unreadable_event_sends_the_failure_to_the_model_and_the_user(self) -> None:
        for payload in ('{"hook_event_name": "Foo"}', "nope", ""):
            with self.subTest(payload=payload):
                result = run_launcher(self.script, self.environment(), stdin=payload)
                assert result.returncode == 0, result.stderr
                output = json.loads(result.stdout)
                assert "hookSpecificOutput" not in output, "it requires a hookEventName"
                assert output["decision"] == "block"
                text = output["reason"]
                assert output["systemMessage"] == text
                assert "continue" not in output
                assert "stopReason" not in output
                assert "the hook event could not be read" in text
                assert "uv" in text
                assert "3.14" in text
                assert "uv" in result.stderr

    def test_with_no_downloader_the_text_names_the_missing_downloader(self) -> None:
        text = self.assert_model_and_user_both_told(
            self.run_failing("SessionStart"), "SessionStart"
        )
        assert "no curl or wget" in text

    def test_when_the_download_fails_the_text_says_so_and_the_temp_file_is_gone(self) -> None:
        self.stub("", exit_code=22)
        result = self.run_failing("SessionStart", curl_stub=True)
        text = self.assert_model_and_user_both_told(result, "SessionStart")
        assert "download failed" in text
        assert list(self.scratch.glob("uv-install.*")) == []

    def test_when_the_installer_fails_the_text_says_so_and_no_uv_is_left(self) -> None:
        self.stub("exit 3\n")
        result = self.run_failing("SessionStart", curl_stub=True)
        text = self.assert_model_and_user_both_told(result, "SessionStart")
        assert "installer failed" in text
        assert not (self.scratch / "plugin-data" / "bin" / "uv").exists()
        assert not (self.scratch / "home" / ".local").exists()

    def test_when_the_installer_leaves_no_uv_the_text_says_so(self) -> None:
        self.stub(":\n")
        result = self.run_failing("SessionStart", curl_stub=True)
        text = self.assert_model_and_user_both_told(result, "SessionStart")
        assert "still missing" in text

    def test_with_no_plugin_data_dir_it_fails_to_the_model_and_writes_nothing_to_home(self) -> None:
        stubs = self.scratch / "stubs"
        stubs.mkdir(exist_ok=True)
        uv_record = self.scratch / "uv-args.txt"
        recording_uv(stubs / "uv", uv_record, sys.executable)
        stub_curl(stubs / "curl", self.scratch / "curl-log.txt", "exit 1\n")
        child_environment = isolated_environment(
            self.scratch / "home", path_dirs=[str(stubs), str(self.tools)]
        )
        child_environment["TMPDIR"] = str(self.scratch)
        payload = json.dumps({"hook_event_name": "SessionStart"})

        result = run_launcher(self.script, child_environment, stdin=payload)

        text = self.assert_model_and_user_both_told(result, "SessionStart")
        assert "CLAUDE_PLUGIN_DATA is not set" in text
        assert not uv_record.exists(), "no hook runs where nothing may be installed"
        assert not (self.scratch / "curl-log.txt").exists()
        assert not (self.scratch / "home").exists(), "nothing is written to home"


def real_uv_serves_3_14(child_environment: dict[str, str]) -> bool:
    """Whether the real uv finds a 3.14 without the network, under the isolated environment."""
    probe = subprocess.run(
        ["uv", "python", "find", "3.14", "--no-project", "--offline"],
        capture_output=True,
        text=True,
        env=child_environment,
        timeout=10,
    )
    return probe.returncode == 0


class TheRealUvRunsTheScriptOn3_14(unittest.TestCase):
    def test_the_script_sees_python_3_14(self) -> None:
        uv = shutil.which("uv")
        if uv is None:
            self.skipTest("uv is not installed on this machine")
        with tempfile.TemporaryDirectory() as scratch:
            scratch = Path(scratch)
            child_environment = isolated_environment(
                scratch / "home",
                path_dirs=[str(Path(uv).parent), os.environ.get("PATH", os.defpath)],
                plugin_data=scratch / "data",
            )
            child_environment["UV_OFFLINE"] = "1"
            if not real_uv_serves_3_14(child_environment):
                self.skipTest("uv finds no installed 3.14 interpreter without the network")
            script = scratch / "version.py"
            script.write_text(VERSION_SCRIPT)

            result = run_launcher(script, child_environment)

        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "3.14"


if __name__ == "__main__":
    unittest.main()
