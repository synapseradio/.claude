"""What the engine counts as an on/off environment variable being set."""

from collections.abc import Mapping

FALSE_WORDS = frozenset({"0", "false", "False"})


def flag_is_set(env: Mapping[str, str], name: str) -> bool:
    """Whether the on/off variable `name` holds a non-empty value that is no false word.

    The false words are `0`, `false`, and `False`. A variable that carries a value, such
    as `ANTHROPIC_MODEL`, is read for its text and never tested with this.
    """

    value = env.get(name)
    return bool(value) and value not in FALSE_WORDS
