#!/usr/bin/env python3
"""Nothing in this plugin imports the configuration around it.

The plugin installs on its own, into a cache directory where no `scripts/`
tree sits beside it. An import reaching outward would resolve in the author's
checkout and fail nowhere else until a second person installed it.

Run with `python3.14 -m pytest features/model-scoped-rulesets/tests/test_boundary.py`.
"""

import ast
import pathlib

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

# The module the render seam used to be owned by, and the tree it lives in.
OUTWARD_MODULES = frozenset({"projection"})
OUTWARD_PREFIX = "scripts"


def sources() -> list[pathlib.Path]:
    """Every Python file the plugin runs, tests excluded."""

    return sorted([*(PLUGIN_ROOT / "lib").rglob("*.py"), *(PLUGIN_ROOT / "hooks").rglob("*.py")])


def imported_names(path: pathlib.Path) -> list[str]:
    """Every module name one file imports, dotted form kept."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.append(node.module)
    return names


def suite_files() -> list[pathlib.Path]:
    """Every test file in this plugin."""

    return sorted((PLUGIN_ROOT / "tests").glob("test_*.py"))


def outward_parents(path: pathlib.Path) -> list[int]:
    """Each `parents[N]` in one file that reaches above the plugin root.

    A test file sits one directory below that root, so `parents[1]` is the
    plugin and anything higher is the checkout around it.
    """

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        target = node.value
        if isinstance(target, ast.Attribute) and target.attr == "parents":
            index = node.slice
            if (
                isinstance(index, ast.Constant)
                and isinstance(index.value, int)
                and index.value >= 2
            ):
                found.append(index.value)
    return found


class TestTheTestsReadNoCorpusButTheirOwn:
    """Every test builds its corpus under tmp_path, so none reads a real one.

    A test reading the corpus its author happens to keep beside this code
    passes for them and fails for everyone else, and it would fail for them
    too the moment they edited a rule.
    """

    def test_the_plugin_holds_tests_to_check(self):
        assert suite_files(), "a hermeticity test that finds no test proves nothing"

    def test_no_test_resolves_a_path_above_the_plugin_root(self):
        offenders = {path.name: outward_parents(path) for path in suite_files()}
        offenders = {name: found for name, found in offenders.items() if found}

        assert offenders == {}, (
            "a test reading a corpus outside this plugin reads rules nobody shipped with it, "
            f"and passes or fails on whatever those happen to say: {offenders}"
        )


class TestTheImportsRunInward:
    def test_the_plugin_holds_python_to_check(self):
        assert sources(), "a boundary test that finds no source proves nothing"

    def test_no_module_imports_the_configuration_around_it(self):
        offenders = {
            path: [
                name
                for name in imported_names(path)
                if name in OUTWARD_MODULES or name.split(".")[0] == OUTWARD_PREFIX
            ]
            for path in sources()
        }
        offenders = {path: names for path, names in offenders.items() if names}

        assert offenders == {}, (
            "an import reaching outside the plugin resolves in the author's checkout and "
            "nowhere else, so a second person's install fails at the first hook run"
        )

    def test_every_sys_path_insert_derives_from_the_file_it_sits_in(self):
        for path in sources():
            for line in path.read_text(encoding="utf-8").split("\n"):
                if "sys.path.insert" not in line:
                    continue
                assert "__file__" in line, (
                    f"{path} extends the import path with {line.strip()!r}, and a hook runs "
                    "from a versioned cache copy, so only the file's own location finds its "
                    "library"
                )
