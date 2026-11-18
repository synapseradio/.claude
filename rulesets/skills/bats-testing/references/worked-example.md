# Worked example: the ui-amboss onboard script

The onboard script sets up a developer machine, so every command it runs is one a test must keep off the real machine.
Its suites show the patterns of this skill at full size.

- Entry script: `~/projects/ui-amboss/scripts/onboard.sh`
- Library modules: `~/projects/ui-amboss/scripts/onboard/*.sh`
- Suites and helpers: `~/projects/ui-amboss/scripts/onboard/tests/`
- Shared helper: `~/projects/ui-amboss/scripts/tests/test_helper.bash`
- Runner: `~/projects/ui-amboss/scripts/test-scripts.sh`

Read the files themselves before copying a pattern, since the notes below describe them as they stood when this was written.

## Patterns to copy

### A thin entry script over sourced modules

The entry script sources each module, sets its shell options, and calls one function with its arguments:

```bash
# shellcheck source=onboard/plan.sh
source "$(dirname "${BASH_SOURCE[0]}")/onboard/plan.sh"

set -Eeuo pipefail

onboard::run "$@"
```

The modules set no shell options and run nothing when sourced, so a suite sources one module in `setup` and calls its functions directly.

### Two levels of test

Most suites source the modules and call a function such as `bun::install` with its collaborators stubbed.
One suite, `entrypoint.test.bats`, runs the real entry script as its own process: it copies the script into a fixture directory beside stand-in modules, runs it from another working directory, and asserts the exit status and the arguments the stand-in received.
That one suite covers what sourcing cannot: the shebang, the option line, path resolution from another directory, and the status the process exits with.

### A sandbox built in one shared function

`setup_sandbox_test_env` in the shared helper gives every case a `HOME` and a `TMPDIR` under `$BATS_TEST_TMPDIR`, unsets the machine's variables that would steer the script, and puts a per-case stub directory first on `PATH`.
Every suite calls it from `setup`, so no suite can forget part of the isolation.

### A narrowed PATH of links, built once per file

`use_sandbox_path` replaces `PATH` with the stub directory plus one directory of symlinks to the utilities the script needs.
It builds the link directory once under `$BATS_FILE_TMPDIR`, in a staging directory it then renames, so an interrupted case never leaves it half built.
A command that happens to be installed on the machine cannot leak into a case.

### A call log in place of output matching

Each stub appends its name and arguments to `$CALL_LOG`, and `assert_call_log` diffs the expected commands against that file:

```bash
assert_call_log "nvm install PWD=${UIA_REPO_ROOT}" "nvm use PWD=${UIA_REPO_ROOT}"
```

The case states which commands ran, in order, with which arguments.
It holds through any rewording of what the script prints, and a failure shows a diff.

### State compared before and after

A case that promises to leave a file alone copies it first and compares after:

```bash
cmp "${BATS_TEST_TMPDIR}/zshrc.before" "${HOME}/.zshrc"
```

### Function stand-ins for interactive collaborators

`use_prompt_doubles` redefines the prompt functions after sourcing, so a case scripts the answers and logs each prompt to the call log.
No case waits on a terminal.

### The oldest bash, exercised on purpose

`run_strict_bash32` runs a snippet through `/bin/bash -c` under the script's own option line.
A case run this way catches a form that only a newer bash accepts.
Every `[[ ... ]]` assertion ends in `|| false`, which fails the case on bash 3.2 wherever the line stands.

### Parallel across files only

The runner calls bats with `--jobs <cores> --no-parallelize-within-files --print-output-on-failure`, and checks for GNU parallel first with a message naming how to get it.

## Patterns to write differently

### Assertions on message wording

Assertions in several suites match a fragment of a printed sentence, such as `[[ "${output}" == *'nvm use'* ]] || false`.
Each fails when someone rewords the message and the behavior is unchanged.
Write the outcome in its place: the call log entry, the exit status, or the file the script wrote.
Where the message is the behavior, as with a hint naming the command to run next, hold that command in a constant the script prints and the test reads, and assert the constant's presence.

### Git config left to the machine

The sandbox sets `HOME` and unsets the XDG variables, which sends XDG lookups into the sandboxed `HOME`.
It leaves git's system config readable, and `preinstall.test.bats` looks up the machine's git.
Set `GIT_CONFIG_GLOBAL` to a file in the sandbox and `GIT_CONFIG_NOSYSTEM=1` in the shared setup function.

### A machine PATH behind the stubs

`entrypoint.test.bats` calls the sandbox function without narrowing `PATH`, so every tool on the machine sits behind its stub directory.
Narrow `PATH` in each suite that runs the subject as a process.

### Stubs written fresh for every case

`write_executable` writes each stub into the case's own directory, so every case pays the first-exec assessment on macOS for every stub it runs.
Write each stub once in `setup_file` under `$BATS_FILE_TMPDIR`, run it once, and link it into the case's stub directory.
A stub whose behavior a case varies reads that variation from an environment variable.

### Inline shellcheck directives that silence a finding

Several modules open on a line such as `# shellcheck disable=SC2154`, with a comment naming the module that sets the variable.
Clear the finding in the code instead: pass the value as an argument, or have the module that reads the variable source the one that sets it under a `# shellcheck source=` line.

### No timeout

No suite sets `BATS_TEST_TIMEOUT`, so a case that hangs holds the whole run.
Set it at the top of each file.

### No version floor

The suites call `run` without options today, so nothing breaks.
A file that starts passing `run` an option needs `bats_require_minimum_version 1.5.0` at its top.
