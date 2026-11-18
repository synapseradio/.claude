# Helper library assertions

Use these only where the repository's suites already load the library, and load it the way they do.
Each function prints the values it compared when it fails, where a raw `[ ... ]` prints only the failing line.

Full reference: <https://github.com/bats-core/bats-assert>, <https://github.com/bats-core/bats-file>, <https://github.com/bats-core/bats-support>

## Loading

bats-assert needs bats-support loaded first.

```bash
setup() {
  bats_load_library bats-support
  bats_load_library bats-assert
  bats_load_library bats-file
}
```

Load a library in `setup_file` as well where `setup_file` or `teardown_file` calls it.

## bats-assert

These read `$status`, `$output`, and `${lines[@]}`, so each follows a `run`.

| Function | Passes when |
| --- | --- |
| `assert_success` | `$status` is 0 |
| `assert_failure` | `$status` is not 0 |
| `assert_failure <n>` | `$status` is `<n>` |
| `assert_output '<text>'` | `$output` equals the text |
| `assert_output --partial '<text>'` | `$output` contains the text |
| `assert_output --regexp '<regex>'` | `$output` matches the regex |
| `refute_output` | `$output` is empty |
| `refute_output --partial '<text>'` | `$output` lacks the text |
| `assert_line '<text>'` | some line equals the text |
| `assert_line --index <i> '<text>'` | line `<i>`, counted from 0, equals the text |
| `refute_line '<text>'` | no line equals the text |
| `assert_equal '<actual>' '<expected>'` | the two strings are equal |
| `assert_not_equal '<actual>' '<unexpected>'` | the two strings differ |
| `assert <expression>` | the expression succeeds |
| `refute <expression>` | the expression fails |
| `assert_regex '<value>' '<regex>'` | the value matches the regex |
| `assert_stderr`, `assert_stderr_line` | as their output forms, on `$stderr` after `run --separate-stderr` |

`assert_line` and `refute_line` take `--partial` and `--regexp` as `assert_output` does.

Match a token code or a person acts on, such as a path or a `key=value` pair, and keep message wording out of every `--partial` and `--regexp` argument.

## bats-file

| Function | Passes when |
| --- | --- |
| `assert_exists <path>`, `assert_not_exists <path>` | anything, or nothing, stands at the path |
| `assert_file_exists <path>`, `assert_file_not_exists <path>` | a regular file does, or does not |
| `assert_dir_exists <path>`, `assert_dir_not_exists <path>` | a directory does, or does not |
| `assert_link_exists <path>` | a symbolic link does |
| `assert_symlink_to <target> <link>` | the link points at the target |
| `assert_file_executable <path>` | the file is executable |
| `assert_file_permission <mode> <path>` | the file's mode equals `<mode>` |
| `assert_file_empty <path>`, `assert_file_not_empty <path>` | the file holds nothing, or something |
| `assert_file_contains <path> '<regex>'` | a line of the file matches |
| `assert_file_not_contains <path> '<regex>'` | no line of the file matches |
| `assert_files_equal <a> <b>` | the two files hold the same bytes |

Use `$BATS_TEST_TMPDIR` and `$BATS_FILE_TMPDIR` for temporary directories, in place of the library's `temp_make`.

## bats-support

`fail '<message>'` fails the case with the message, for a helper assertion a suite writes itself.

## Without a helper library

```bash
run -0 "${SCRIPT}" list
[ "${#lines[@]}" -eq 2 ]
[ "${lines[0]}" = "${HOME}/.config/tool/a" ]
```

Make such runs under `--print-output-on-failure`, so a failing case shows what the command printed.
