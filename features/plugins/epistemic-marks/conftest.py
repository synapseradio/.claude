"""Marks the plugin root for pytest, which puts this directory on the import path.

A test then imports `epistemic_marks` by name. `python3 -m unittest`, run from
the plugin root, finds the package the same way through the working directory.
"""
