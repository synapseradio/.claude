---
name: bats-testing
description: >-
  Load this before you write, change, run, or judge a bats test or any test of bash code. A prompt that hands such work to another agent names this skill for that agent to load. It holds the mandatory bats practice: run and its checks, assertions, isolation, stubs, setup, parallel runs, and forms that pass falsely.
---

# Bats testing

For every bats test and every test of bash code you write, change, run, or judge, optimize for a case that fails only when the behavior it names breaks, touches nothing outside its own temporary directory, and adds no wait the behavior does not need.

This binds every `.bats` file, every helper a suite loads, and everyone who works on one. A prompt that hands work on one to another agent names `bats-testing` for that agent to load.

## Notation

- `A -> B`: step A then step B of one instruction
- guard block: a name line then `| condition = act` lines, the first that fits taken and `otherwise` last

## Skills to load beside this one

Load `testing-software` first.
It decides which behaviors get a test, what a test asserts, how to judge a test, and what a run lets you claim.
This skill holds only how to carry that out in bats.

Load `bash-style` for every line of bash in a suite: its setup code, its helpers, and its stubs.

## The docs

The bats-core documentation is the reference for everything here, and each section below links the page to read further.
The links follow the latest release.
Run `bats --version`, and where the repository pins another version, replace `stable` in a link with `v<version>`.

- Usage and command line: <https://bats-core.readthedocs.io/en/stable/usage.html>
- Writing tests: <https://bats-core.readthedocs.io/en/stable/writing-tests.html>
- Gotchas: <https://bats-core.readthedocs.io/en/stable/gotchas.html>
- FAQ: <https://bats-core.readthedocs.io/en/stable/faq.html>
- Warnings BW01 to BW03: <https://bats-core.readthedocs.io/en/stable/warnings/index.html>
- Helper libraries: <https://github.com/bats-core/bats-support>, <https://github.com/bats-core/bats-assert>, <https://github.com/bats-core/bats-file>

## Before the first line

Read what the repository pins: the bats version, the command that runs its suites with its flags, the bash that command resolves, the helper libraries its suites load and from where, and the timeout its files set.
Follow each pin.
Write a new file in the form the suites beside it hold: the same load lines, the same shared setup function, the same assertion style.

## Bats missing or needs setup

Assume a machine that has none of it: no bats, no GNU parallel, no helper library, and only bash 3.2.
Check in this order before the first run, and stop at the first miss:

1. The repository's own bats: a `bats` entry in its manifest, a `test/bats` or similar git submodule, or a setup step that installs it. Where one exists, run bats through it, as `npx bats` or `./test/bats/bin/bats`, after the repository's install step has run.
2. `command -v bats` -> `bats --version`, against the version the suites need.
3. Each helper library the suites load, at the path their `load` or `bats_load_library` line resolves to.
4. `command -v parallel`, only where the run would pass `--jobs`.

Install nothing on your own.
Where bats, GNU parallel, or a helper library is missing, or older than the work needs, ask whether you may install it, in one question that gives:

- what is missing or too old, with the version found
- why the work needs it, such as the suite's `load` line or a `run` option that needs bats 1.5.0
- the exact command you would run: the repository's own setup step where it has one, such as a `just tools` or an onboard script, and otherwise the platform's package command
- what that command changes on the machine

Pick the command by where the repository keeps its tools:

| Missing | macOS with Homebrew | Debian or Ubuntu | Vendored in the repository |
| --- | --- | --- | --- |
| bats | `brew install bats-core` | `sudo apt-get install bats` | `npm install --save-dev bats`, or `git submodule add https://github.com/bats-core/bats-core.git test/bats` |
| bats-support, bats-assert, bats-file | `brew install bats-core/bats-core/<name>` | `sudo apt-get install <name>` | `git submodule add https://github.com/bats-core/<name>.git test/test_helper/<name>` |
| GNU parallel | `brew install parallel` | `sudo apt-get install parallel` | none |

A system install changes the machine for every project, and a distribution's bats may be older than the suites need, so read `bats --version` after it.
A vendored copy changes the repository: it adds a dependency or a submodule that the change must commit, so offer it only where the repository already vendors its tools or the person asks for it.
Homebrew puts the libraries under `$(brew --prefix)/lib`, and a vendored library sits beside the suites: have the test command set `BATS_LIB_PATH` to the first, or `load` the second by relative path.

Install only after a yes, with the command you showed, then run the checks again.

declined
  | bats is missing = write or change the suite, run `bash -n` on its `.bash` helpers and shellcheck on each file where shellcheck is present, and report that no case ran
  | bats is older than a form needs = write the form the installed version runs, such as an explicit `[ "$status" -eq 1 ]` in place of `run -1`
  | GNU parallel is missing = run without `--jobs`
  | a helper library is missing and the suite loads it = report the cases that cannot run, and run the files that do not load it
  | a helper library is missing and you are writing a new suite = write the assertions as `[ ... ]`

Reference: <https://bats-core.readthedocs.io/en/stable/installation.html>, <https://bats-core.readthedocs.io/en/stable/faq.html#how-can-i-use-helper-libraries-like-bats-assert>

## What a bats file is

Bats evaluates a test file once to count its cases and once more per case, each case in its own process.
Code outside a function therefore runs on every evaluation.

Keep everything out of file scope except `bats_require_minimum_version`, `BATS_TEST_TIMEOUT`, `load` lines the suites beside it already place there, and function definitions.
Print nothing from file scope.
Source the code under test inside `setup` or the case, since a file that fails while sourced at file scope or in `setup_file` breaks the run with an error that names no case.
Register generated cases with `bats_test_function`, since a `@test` inside a loop redefines one function.
Pass a parameter to a case through an environment variable, since bats passes no arguments to files or cases.

Reference: <https://bats-core.readthedocs.io/en/stable/writing-tests.html#code-outside-of-test-cases>, <https://bats-core.readthedocs.io/en/stable/writing-tests.html#dynamic-test-registration-via-bats-test-function>

## Loading code

load target
  | the code under test, a `.sh` file = `source` it inside `setup`
  | a helper beside the suite = `load` it with its exact file name
  | a helper library installed on the system, bats-assert for one = `bats_load_library <name>`, with `BATS_LIB_PATH` set by the test command

Declare a helper's shared variable with `declare -g` on bash 4.2 or later and with a plain assignment on bash 3.2, since `load` sources inside a function and a bare `declare` there makes the variable local.
Give a script whose functions a suite sources a guard around its entry call, in the form `bash-style` gives, so that sourcing defines the functions and runs nothing.

Reference: <https://bats-core.readthedocs.io/en/stable/writing-tests.html#load-share-common-code>, <https://bats-core.readthedocs.io/en/stable/writing-tests.html#bats-load-library-load-system-wide-libraries>

## Driving the subject

Drive the subject the way its person does.

subject
  | an executable script = run it as its own process, by path, through `run`
  | a function whose result is a variable or a change in the calling shell = source its file -> call it without `run`, since `run` executes in a subshell and the change is lost
  | a function whose result is its output or status = source its file -> call it through `run`

## `run` and its checks

`run` always returns 0 and stores the command's status in `$status`, its output in `$output`, and its lines in `${lines[@]}`.
A case that calls `run` and checks nothing passes whatever the command did.

expectation
  | the command succeeds and the case reads no output = call it without `run`, since bats runs each case under `set -e`
  | the command succeeds and the case reads its output = `run -0 <command>`
  | the command exits with status N = `run -N <command>`
  | the command fails with any status = `run ! <command>`

Write `run !` for every expected failure, since a bare `! <command>` fails a case only as its last line.
Put every `run` option before the command, and put `--` before a command that starts with `-`.
Call `bats_require_minimum_version 1.5.0` at the top of each file that passes `run` an option, since an older bats takes the option for the command and passes silently.
Use `run --separate-stderr` where the case tells the streams apart, and `run --keep-empty-lines` where an empty line carries meaning.
Treat warning BW01 as a defect in the case: `run` met status 127, command not found, so either the command line is wrong or the case means `run -127`.

pipe
  | the command under `run` holds a pipe = `run bats_pipe <a> \| <b>`, or `run bash -c '<a> | <b>'`, or a function that wraps the pipeline

A bare `run <a> | <b>` pipes the output of `run` itself, so `<b>` reads nothing and the check passes.

Reference: <https://bats-core.readthedocs.io/en/stable/writing-tests.html#run-test-other-commands>, <https://bats-core.readthedocs.io/en/stable/writing-tests.html#bats-pipe-run-commands-with-pipes>

## Assertions

Assert what the person or the calling code relies on: the exit status, a file's presence or content, the commands the subject ran, a value another program parses.
Keep the wording of messages out of every assertion, a `--partial` match on a sentence included.
Where the only evidence of a behavior is a message, assert a token in it that code or a person acts on, such as a path, a command name, or a `key=value` pair.

assertion form
  | the repository's suites load bats-assert or bats-file = use their functions, which print the compared values when they fail
  | otherwise = `[ ... ]`, with the run made under `--print-output-on-failure`

Read `references/assertions.md` for the functions of the three helper libraries.

On bash 3.2 a failing `[[ ... ]]` or `(( ... ))` aborts a case only as its last line.
Where the suite runs on bash 3.2, write `[ ... ]`, or end each `[[ ... ]]` and `(( ... ))` with `|| false`.

Record what a stub was asked to do, and assert that record.
A stub that appends its name and arguments to a log file lets a case compare the whole log against the expected commands, which holds through any change to what the script prints.

Reference: <https://bats-core.readthedocs.io/en/stable/gotchas.html>, <https://bats-core.readthedocs.io/en/stable/faq.html#how-can-i-debug-a-failing-test>

## Isolation

Give every case its own world under `$BATS_TEST_TMPDIR`, a case whose subject reads no config today included.
In `setup`:

- set `HOME` to a directory there
- set `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME`, and `XDG_CACHE_HOME` inside that `HOME`
- set `GIT_CONFIG_GLOBAL` to a file there and `GIT_CONFIG_NOSYSTEM=1` wherever the subject or the case runs git
- set `TMPDIR` there where the subject makes temporary files
- point every other path the subject reads, a config or state file for one, there too
- unset each variable of the machine that would steer the subject, a token or a `CI` flag for one
- `cd` to a directory there where the subject reads the working directory

Write fixtures a whole file shares under `$BATS_FILE_TMPDIR` in `setup_file`, and treat them as read-only in every case.
Bats removes these directories after the run, so a suite needs a `teardown` only for what lives outside them, a background process for one.

A `teardown` runs without `set -e`, and only its last command or a `return` decides whether it fails the case.

where shared setup goes
  | every file of the suite needs it = a function in a helper file, called from each file's `setup`
  | it must run once for the whole run = `setup_suite` in a file named `setup_suite.bash` beside the `.bats` files, never in a `.bats` file

Export a variable in `setup_file` to hand it to that file's cases.

Reference: <https://bats-core.readthedocs.io/en/stable/writing-tests.html#setup-and-teardown-pre-and-post-test-hooks>, <https://bats-core.readthedocs.io/en/stable/writing-tests.html#special-variables>

## Stubs

Stub an external command with an executable of the same name in a directory placed first on `PATH`.
Stub a function of the code under test by redefining it after sourcing.
Narrow `PATH` to the stub directory plus a directory of links to the utilities the subject needs wherever a command found on the machine would change the result.

Build each stub executable once, in `setup_file` under `$BATS_FILE_TMPDIR`, run it once there, and give each case a link to it in its own stub directory.
On macOS the first exec of a freshly written executable is assessed by the system, and a link to a file that has already run skips that.
Measured on macOS 26 on Apple silicon: about 240ms for the first exec of a fresh file, about 5ms through a symlink or hard link to one already run.
The measurement comes from macOS, and the link form also runs on Linux, so write it wherever a suite may run on a Mac.
A stub that reads its own name from `$0` serves every command linked to it.

Give a stub that must hang a hang that ends at teardown, such as a read from a FIFO the `teardown` removes or writes to.
Bats waits for every process that still holds the case's file descriptors, so a stub that sleeps keeps the run waiting for each time the subject calls it.

## Background processes

Close file descriptor 3 for every process a case leaves running, as `<command> 3>&- &`, since bats waits for each holder of it.
Stop in `teardown` every process the case started, by PID.
Where the subject enforces a deadline on a child, assert that no process the child started outlives it, checking each by PID.

Reference: <https://bats-core.readthedocs.io/en/stable/writing-tests.html#file-descriptor-3-read-this-if-bats-hangs>

## Timeout

Set `BATS_TEST_TIMEOUT` in every file you create or edit, at file scope or in `setup_file`, to the value the repository's suites use.
A value set in `setup` or in a case arrives after the countdown starts and changes nothing.

Reference: <https://bats-core.readthedocs.io/en/stable/faq.html#how-to-set-a-test-timeout-in-bats>

## Skipping and focusing

Skip a case with `skip '<reason>'`, where the reason names the condition, such as a tool the machine lacks.
`setup` and `teardown` still run for a skipped case.
Keep the `bats:focus` tag out of every commit, since a focused run executes only the tagged cases and exits 1 even when they pass.

Reference: <https://bats-core.readthedocs.io/en/stable/writing-tests.html#tagging-tests>

## Running

Run suites through the repository's test command, so its flags and its bash apply.

run
  | the repository has a test command = that command, scoped to the files covering the change
  | otherwise = `bats <file>`
  | one case = `bats --filter '<regex on the case name>' <file>`
  | only the cases that failed last time = `bats --filter-status failed <path>`
  | a directory with suites in subdirectories = add `--recursive`, since bats reads only a directory's top level

Read a failing case with `--print-output-on-failure`, and trace one with `--trace`.
Find the slow cases with `--timing` before changing a suite for speed.
Count a run that reports no cases as a miss.

Reference: <https://bats-core.readthedocs.io/en/stable/usage.html>

## Parallel runs

`bats --jobs <n>` needs GNU parallel on `PATH` and runs cases in no fixed order.
Detect it with `command -v parallel` before passing `--jobs`, and run in series where it is absent, or ask to install it by the setup section above.
Have a test command you write make the same check, so it runs on a machine without parallel.
Before turning `--jobs` on, confirm no two cases write the same location, which the isolation above gives.

The docs offer two levels of parallelism under `--jobs`, across files and within a file, both on by default.
Within a file, bats hands out slots through a semaphore that polls while every slot is taken.
Measured with bats 1.14.0 and GNU parallel: about 1s of waiting per round of slots.
That wait belongs to within-file parallelism, and `--no-parallelize-within-files` keeps the parallelism across files without it.

parallelism
  | the cases of a file are short, as nearly every case that stubs its commands is = `--jobs <n> --no-parallelize-within-files`
  | each case of a file outlasts one poll of the semaphore, a case that builds or starts something real for one = `--jobs <n>` alone
  | one file's cases share a fixture they write = `export BATS_NO_PARALLELIZE_WITHIN_FILE=true` in that file's `setup_file`
  | the run must print each file's results as they come = `--no-parallelize-across-files`

Reference: <https://bats-core.readthedocs.io/en/stable/usage.html#parallel-execution>

## Linting a suite

Run shellcheck on each `.bats` file and helper you change, in the form the repository's hook runs it.
ShellCheck reads the `@test` syntax, and shfmt reads it under `-ln bats`.

## A file in this form

```bash
#!/usr/bin/env bats

bats_require_minimum_version 1.5.0

export BATS_TEST_TIMEOUT=10

setup_file() {
  export STUBS="${BATS_FILE_TMPDIR}/stubs"
  mkdir -p "${STUBS}"
  cat >"${STUBS}/log-call" <<'EOF'
#!/bin/bash
echo "${0##*/} $*" >>"${CALL_LOG}"
EOF
  chmod +x "${STUBS}/log-call"
  CALL_LOG=/dev/null "${STUBS}/log-call"
}

setup() {
  export HOME="${BATS_TEST_TMPDIR}/home"
  export XDG_CONFIG_HOME="${HOME}/.config"
  export XDG_DATA_HOME="${HOME}/.local/share"
  export XDG_STATE_HOME="${HOME}/.local/state"
  export XDG_CACHE_HOME="${HOME}/.cache"
  export GIT_CONFIG_GLOBAL="${HOME}/gitconfig"
  export GIT_CONFIG_NOSYSTEM=1
  export CALL_LOG="${BATS_TEST_TMPDIR}/calls.log"
  mkdir -p "${HOME}" "${BATS_TEST_TMPDIR}/bin"
  : >"${GIT_CONFIG_GLOBAL}"
  : >"${CALL_LOG}"
  ln -s "${STUBS}/log-call" "${BATS_TEST_TMPDIR}/bin/brew"
  PATH="${BATS_TEST_TMPDIR}/bin:${PATH}"
}

@test "a run that names a missing tool installs it through brew" {
  "${BATS_TEST_DIRNAME}/../install-tools.sh" jq
  [ "$(<"${CALL_LOG}")" = 'brew install jq' ]
}

@test "an unknown flag exits 2 and installs nothing" {
  run -2 "${BATS_TEST_DIRNAME}/../install-tools.sh" --bogus
  [ ! -s "${CALL_LOG}" ]
}
```

Read `references/worked-example.md` for a real suite of this kind, the ui-amboss onboard script and its tests: the patterns to copy from it and the ones to write differently.
