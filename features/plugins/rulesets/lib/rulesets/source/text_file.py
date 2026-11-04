"""Read a file as UTF-8 text exactly as it sits on disk, or say why it cannot be read."""

from __future__ import annotations

import pathlib


class UnreadableFile(Exception):
    """The file cannot be read as UTF-8 text.

    `line` is the file line of the first byte that is no UTF-8, and None where the system
    refused the read.
    """

    def __init__(self, cause: str, line: int | None):
        super().__init__(cause)
        self.cause = cause
        self.line = line


def read_text_file(path: pathlib.Path) -> str:
    """The text of `path` with every line ending as written. Raises UnreadableFile."""

    try:
        return path.read_bytes().decode("utf-8")
    except OSError as failure:
        raise UnreadableFile(
            f"the file cannot be read: {failure.strerror or failure}", None
        ) from failure
    except UnicodeDecodeError as failure:
        line = failure.object.count(b"\n", 0, failure.start) + 1
        raise UnreadableFile(
            f"the file is not UTF-8 text: {failure.reason} at byte {failure.start}", line
        ) from failure
