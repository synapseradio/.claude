# Set up epistemic-marks

Install epistemic-marks for a person by running the commands below in order. After each command, compare its output with the text given here. If the output differs, stop, and tell the person which step failed and what it printed.

Some steps happen inside the person's Claude Code session, which you cannot type into. Hand those steps to the person.

## 1. Check the requirements

1. Run `claude --version`.

   The output must show `2.1.268` or a later version. If the version is earlier, run `claude update`.

2. Run this command:

   ```sh
   python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))'
   ```

   The exit code must be 0. If it is not, ask the person for the path of a Python 3.9 or later. Tell them to set `EPISTEMIC_MARKS_PYTHON` to that path in the environment Claude Code starts from.

## 2. Install

1. Run this command:

   ```sh
   claude plugin marketplace add synapseradio/.claude
   ```

   The output ends with `Successfully added marketplace: claude-root (declared in user settings)`. On a repeat run it says `already on disk`, which is not an error.

   If the clone over SSH fails, run this command instead:

   ```sh
   CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1 claude plugin marketplace add synapseradio/.claude
   ```

2. Run this command:

   ```sh
   claude plugin install epistemic-marks@claude-root
   ```

   The output ends with `Successfully installed plugin: epistemic-marks@claude-root (scope: user)`. On a repeat run it says `is already installed`, which is not an error.

## 3. Check the install

1. Run `claude plugin list`.

   The section for `epistemic-marks@claude-root` contains `Status: ✔ enabled`.

2. Run `claude plugin details epistemic-marks@claude-root`.

   The output contains `Hooks (5)  SessionStart, SubagentStart, PostToolBatch, Stop, SubagentStop`.

## 4. Hand over to the person

Tell the person which checks passed, then ask them to:

1. Run `/reload-plugins` in the open session, or restart Claude Code.
2. Run `/hooks`, and look for the epistemic-marks hooks in its list.

The commands above write every setting the plugin needs, so edit no settings file by hand.

## Turn it off

Run `claude plugin disable epistemic-marks@claude-root`. The output ends with `Successfully disabled plugin: epistemic-marks (scope: user)`. Then ask the person to reload, as in section 4.
