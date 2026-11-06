import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


research = load("research", "hindsight-research-retain.py")
thinkies = load("thinkies", "hindsight-thinkies-retain.py")
subagent = load("subagent", "hindsight-retain-thinkies-subagent.py")


def prompt(text):
    return {"type": "user", "uuid": "u1", "message": {"role": "user", "content": text}}


def assistant(*blocks):
    return {"type": "assistant", "message": {"role": "assistant", "content": list(blocks)}}


def skill_call(name, call_id="toolu_1"):
    return {"type": "tool_use", "name": "Skill", "id": call_id, "input": {"skill": name}}


def text(body):
    return {"type": "text", "text": body}


def tool_result():
    return {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result"}]}}


def test_web_tools_and_research_mcp_count_as_research():
    for tool in (
        "WebFetch",
        "WebSearch",
        "mcp__linkup__linkup-search",
        "mcp__plugin_context7_context7__query-docs",
    ):
        assert research.is_research(tool, {})


def test_bash_counts_only_for_tvly_or_curl_over_http():
    assert research.is_research("Bash", {"command": "tvly search 'bats'"})
    assert research.is_research("Bash", {"command": "curl -sfL https://example.com/llms.txt"})
    assert not research.is_research("Bash", {"command": "curl -s localhost:8888/v1/x"})
    assert not research.is_research("Bash", {"command": "git status"})


def test_bash_curl_to_a_local_server_is_not_online_research():
    for url in (
        "http://127.0.0.1:9077/health",
        "http://localhost:8000/v1/systemone",
        "http://[::1]:8000/",
    ):
        assert not research.is_research("Bash", {"command": f"curl -s {url}"}), url


def test_other_tools_are_not_research():
    assert not research.is_research("Read", {"file_path": "/x"})
    assert not research.is_research("mcp__hindsight__recall", {})


def test_skill_tool_turn_yields_text_after_the_call():
    turn = [
        prompt("think about this"),
        assistant(text("before the skill"), skill_call("thinkies:ponder")),
        tool_result(),
        assistant(text("first finding")),
        assistant(text("second finding")),
    ]
    assert thinkies.thinkies_output(turn) == (
        "thinkies:ponder",
        "toolu_1",
        "first finding\n\nsecond finding",
    )


def test_slash_command_turn_yields_all_assistant_text():
    turn = [
        prompt("<command-name>/thinkies:wonder</command-name>\n<command-args>x</command-args>"),
        assistant(text("an answer")),
    ]
    assert thinkies.thinkies_output(turn) == ("thinkies:wonder", "u1", "an answer")


def test_other_skills_yield_nothing():
    turn = [
        prompt("go"),
        assistant(skill_call("harness-config:update-claude-settings")),
        assistant(text("done")),
    ]
    assert thinkies.thinkies_output(turn) is None


def test_last_turn_starts_at_the_latest_typed_prompt(tmp_path):
    transcript = tmp_path / "t.jsonl"
    lines = [
        prompt("old"),
        assistant(skill_call("thinkies:ponder")),
        assistant(text("old output")),
        prompt("new"),
        assistant(text("plain answer")),
    ]
    transcript.write_text("\n".join(json.dumps(line) for line in lines))
    assert thinkies.thinkies_output(thinkies.last_turn(transcript)) is None


def run_subagent_hook(monkeypatch, payload, repo="ui-amboss"):
    """Runs the SubagentStop hook with retain stubbed; returns the recorded calls."""
    calls = []
    monkeypatch.setattr(subagent, "retain", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(subagent, "repo_name", lambda cwd: repo)
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO(json.dumps(payload)))
    subagent.main()
    return calls


def thinkies_payload(report, **extra):
    return {
        "agent_type": "thinkies",
        "agent_id": "a1",
        "cwd": "/work/repo",
        "last_assistant_message": report,
        **extra,
    }


def test_thinkies_subagent_report_goes_to_global_and_repo_banks(monkeypatch):
    calls = run_subagent_hook(monkeypatch, thinkies_payload("Output of thinkies:ponder\n\nbody"))
    assert [args[0] for args, _ in calls] == ["global", "coding-agent::ui-amboss"]
    args, _ = calls[0]
    assert args[2] == "thinkies:thinkies:ponder:a1"
    assert args[3] == ["source:thinkies", "repo:ui-amboss"]


def test_thinkies_subagent_report_without_skill_name_uses_the_agent_id(monkeypatch):
    calls = run_subagent_hook(monkeypatch, thinkies_payload("plain findings"))
    assert calls[0][0][2] == "thinkies:a1"


def test_thinkies_subagent_outside_a_repo_retains_to_global_only(monkeypatch):
    calls = run_subagent_hook(monkeypatch, thinkies_payload("findings"), repo=None)
    assert [args[0] for args, _ in calls] == ["global"]
    assert calls[0][0][3] == ["source:thinkies", "repo:none"]


def test_thinkies_subagent_report_is_capped(monkeypatch):
    calls = run_subagent_hook(monkeypatch, thinkies_payload("x" * (subagent.MAX_CHARS + 500)))
    assert len(calls[0][0][1]) <= subagent.MAX_CHARS + 200


def test_other_agents_and_empty_reports_retain_nothing(monkeypatch):
    other = thinkies_payload("findings", agent_type="spider")
    assert run_subagent_hook(monkeypatch, other) == []
    assert run_subagent_hook(monkeypatch, thinkies_payload("  ")) == []
    assert run_subagent_hook(monkeypatch, thinkies_payload("x", stop_hook_active=True)) == []
