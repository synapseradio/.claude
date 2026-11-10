# Set up epistemic-marks

These steps are for an AI agent that installs the plugin for a person. Run each command as written. Compare its output with the text given. If the output differs, stop and tell the person which step failed and what it printed.

Some steps need the person. An agent cannot type a slash command into the person's session. Tell the person to do these steps.

## 1. Check the requirements

1. Run `claude --version`.

   The output must show `2.1.268` or a higher version. If the version is lower, run `claude update`.

2. Run this command:

   ```sh
   python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))'
   ```

   The exit code must be 0. If it is not 0, ask the person for the path of a Python 3.9 or later. Tell the person to set `EPISTEMIC_MARKS_PYTHON` to that path where Claude Code starts.

## 2. Install

1. Run this command:

   ```sh
   claude plugin marketplace add synapseradio/.claude
   ```

   The output ends with `Successfully added marketplace: claude-root (declared in user settings)`. A repeat run says `already on disk` and is not an error.

   If the SSH connection to GitHub fails, run this command instead:

   ```sh
   CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1 claude plugin marketplace add synapseradio/.claude
   ```

2. Run this command:

   ```sh
   claude plugin install epistemic-marks@claude-root
   ```

   The output ends with `Successfully installed plugin: epistemic-marks@claude-root (scope: user)`. A repeat run says `is already installed` and is not an error.

## 3. Check the install

1. Run `claude plugin list`.

   The section for `epistemic-marks@claude-root` contains `Status: ✔ enabled`.

2. Run `claude plugin details epistemic-marks@claude-root`.

   The output contains `Hooks (5)  SessionStart, SubagentStart, PostToolBatch, Stop, SubagentStop`.

## 4. Hand over to the person

Tell the person to do these two steps:

1. Run `/reload-plugins` in the open session, or restart Claude Code.
2. Run `/hooks`, and check that it shows the five epistemic-marks hooks.

Edit no settings file by hand. The commands above write every setting the plugin needs.

## Turn it off

Run `claude plugin disable epistemic-marks@claude-root`. The output ends with `Successfully disabled plugin: epistemic-marks (scope: user)`. Then tell the person to reload, as in section 4.
