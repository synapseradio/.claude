"""Marks the plugin root for pytest, which puts this directory on the import path.

A test then imports `epistemic_marks` by name. `uv run --no-project --python 3.14 python -m unittest`, run from
the plugin root, finds the package the same way through the working directory.
"""
