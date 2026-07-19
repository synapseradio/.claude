# Google Shell Style Guide

> **Source**: [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html)
>
> This document distills the guide into sudolang. It preserves every rule, not every example — consult the original for full worked examples and rationale.

```sudolang
GoogleShellStyle {
  Background {
    language = bash, the only shell permitted for executables
    shebang = #!/bin/bash
    shellOptions via `set`, so behavior survives invocation as `bash script_name`
    exception: external constraints mandate POSIX sh (legacy OS, restricted runtime)

    isShellTheRightTool(task)? {
      small utility or simple wrapper — mostly orchestrating other tools,
        minimal data manipulation => yes
      performanceCritical => no; pick another language
    }

    shouldItStayShell(script)? {
      lines > 100 || control flow beyond straightforward =>
        no; rewrite in a structured language now
      // judge complexity by maintainability beyond the original author
    }
  }

  FilesAndInvocation {
    extensionFor(file)? {
      library => `.sh` required; never executable
      executable {
        build rule produces `foo` from source => prefer `foo.sh`
        invoked directly from PATH => none
          // users needn't know the implementation language
        otherwise => either
      }
    }

    Constraints {
      SUID/SGID forbidden on shell scripts — use sudo for privilege escalation
    }
  }

  Environment {
    streamFor(message)? {
      error | problem => STDERR
      normal output   => STDOUT
    }
    // canonical err() helper under "Canonical forms" below
  }

  Comments {
    fileHeader: every file opens with a top-level comment describing contents
      // copyright and author optional

    functionComment required iff !obviouslyBrief || libraryFunction {
      document: purpose, globals used/modified, arguments,
                outputs (STDOUT/STDERR), return values beyond exit status
      // banner format under "Canonical forms" below
    }

    implementationComment earned iff tricky || nonObvious || important
      // target complex algorithms and unusual patterns; never excessive

    todo: "# TODO(identifier): ..." — uppercase TODO plus the person most
      familiar with the issue (name, email, or username)
  }

  Formatting {
    indent = 2 spaces, never tabs
      // sole tab exception: <<- here-document bodies
    blank lines between blocks for readability

    overlong(line > 80)? {
      long string          => here-document | embedded newline
      long path or URL     => may exceed, alone or in a variable,
                              to preserve searchability
      anything else        => wrap
    }

    pipeline {
      fitsOneLine? {
        yes => one line
        no  => split at each segment; pipe opens each continuation line;
               indent 2
               // command1 \
               //   | command2 \
               //   | command3
      }
      comments precede the whole pipeline, never interleave
    }

    controlFlow {
      `; then` and `; do` share the line with if | for | while | until | select
      `else` on its own line; fi/done aligned vertically with their opener
      for loops spell out `in "$@"` rather than relying on the implicit form
    }

    case {
      alternatives indent 2
      alternativeFitsOneLine? {
        yes => space after `)`, space before `;;`
               // a) aflag='true' ;;
        no  => pattern, body, `;;` each on their own lines
      }
      always a `*)` arm for the unexpected
    }

    braceThe(variable)? {
      // priority order; earlier rules win
      1: whatever existing code already does
      2: single-character special or positional ($1, $?, $#) => no,
         unless disambiguation requires it ("${1}0${2}0")
      3: everything else, including ${10}+ => yes
    }
    // braces are not quoting — "${var}" still needs its double quotes

    quoteThe(value)? {
      holds variables, command substitutions, spaces, or metacharacters =>
        yes — unless careful unquoted expansion is the point
      command substitution, even one expecting an integer => yes
      shell-internal integer ($?, $#, $$, $!) => optional
      literal integer assignment (value=32) => never
      "word" string vs command option or pathname => prefer quoting the word
    }
    singleVsDouble? {
      no substitution wanted => 'single'
      substitution wanted    => "double"
    }
    allArgsAs? {
      default => "$@"   // preserves arguments intact: no word
                        // splitting, no lost empties
      string concatenation specifically wanted => $*
    }
    // know how quoting changes pattern matching inside [[ ... ]]
    // lists of elements, especially command-line flags => Arrays below
  }

  FeaturesAndBugs {
    shellcheck: run on every script regardless of size  // shellcheck.net

    commandSubstitution: $(command), never backticks
      // $(...) nests without escapes; backticks don't

    testConstruct: [[ ... ]] over [ ... ], test, and /usr/bin/[
      // no pathname expansion or word splitting inside [[ ]];
      // supports == and =~, which [ ] lacks

    testFor(condition)? {
      empty | nonEmpty  => -z | -n, explicitly
        // never bare [[ "${var}" ]], never filler chars
        // ("${var}X" == "some_stringX")
      string equality   => ==      // encourages [[ usage
      numeric           => (( var > 3 )) | [[ "${var}" -gt 3 ]]
      pattern | regex   => == glob | =~ regex, inside [[ ... ]]
    }

    wildcardExpansion: ./* never bare *
      // a file named -f otherwise becomes an option to rm

    eval => avoid
      // masks assignment failures, enables unwanted variable sets

    Arrays {
      trigger: a list exists — above all, command arguments
      store it in an array; expand "${arr[@]}"
      never a space-separated string as a pseudo-list

      Constraints {
        command substitution yields a string, not an array —
          declare -a files=($(ls dir)) and mybinary $(get_args) both
          break on whitespace and special characters
        advanced data manipulation => another language
      }
    }

    iterate(commandOutput)? {
      byLine => while read ... done < <(command) | readarray -t (bash4+)
      never  => command | while read
        // the pipe's subshell drops every variable written in the loop
      never  => for word in $(command)
        // for splits on whitespace, not lines
    }

    arithmetic {
      (( ... )) | $(( ... ))
      never let    // globbing and word splitting
      never $[ ]   // non-portable, deprecated
      never expr   // an external process, far slower than the builtin
      inside $(( ... )): omit ${} braces — the shell resolves names itself
    }

    aliasOrFunction? {
      almost every purpose => function
        // aliases evaluate at definition time and resist debugging;
        // functions take "$@" and quote sanely
    }
  }

  Naming {
    functions: lower_snake_case; library namespace via `::`
      (mypackage::my_func); brace on the same line, no space before ();
      `function` keyword optional but consistent within a project
    variables: as functions; loop variable named for what it loops over
      // for zone in "${zones[@]}"
    constantsAndExported: UPPER_SNAKE_CASE, declared at the top of the file
      readonly NAME='...' | declare -xr NAME='...'
      assignedConditionally? => `readonly NAME` immediately after the
        last assignment
    sourceFilenames: lowercase, underscores if desired —
      make_template, never make-template
  }

  StructureAndScope {
    locals: every function-specific variable declared `local`

    localWithCommandSubstitution? {
      $? checked next => declare first, assign second
        // local my_var
        // my_var="$(my_func)" || return
        // local's own exit status masks the command's
      otherwise => combined form acceptable
    }

    fileOrder [ includes, set statements, constants, functions, main call ]
    all functions grouped together below constants;
      never intersperse executable code among them

    main() required iff script defines multiple functions {
      last non-comment line: main "$@"
      // short linear scripts exempt
    }
  }

  CallingCommands {
    onReturn(command) {
      check every return value, with an informative error:
        if ! cmd; then echo "why it matters" >&2; exit 1; fi |
        cmd; if (( $? != 0 )); then ... fi
    }

    PIPESTATUS {
      trigger: any subsequent command overwrites it
      needMoreThanTheImmediateCheck? => copy first:
        return_codes=( "${PIPESTATUS[@]}" )
    }

    builtinOrExternal? {
      builtin exists => builtin
        // parameter expansion ("${string/#foo/bar}") and =~ with
        // BASH_REMATCH beat spawning sed/expr: faster, more robust, portable
    }
  }

  whenInDoubt {
    match the surrounding codebase — consistency resolves ambiguous style
    consistency never justifies perpetuating an outdated approach once a
      newer style shows clear benefit
  }
}
```

## Canonical forms

The error-reporting helper:

```bash
err() {
  echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')]: $*" >&2
}
```

The function comment banner:

```bash
#######################################
# Cleanup files from the backup directory.
# Globals:
#   BACKUP_DIR
#   ORACLE_SID
# Arguments:
#   None
#######################################
function cleanup() {
  ...
}
```
