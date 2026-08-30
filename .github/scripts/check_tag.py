"""Fail if the git tag disagrees with the version in pyproject.toml.

A tag that says one thing while the package says another produces a release
nobody can find, and PyPI will not let the version be uploaded twice.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import _project

tag_version = sys.argv[1]
packaged = _project.version()

if tag_version != packaged:
    print(f"FAIL: tag says {tag_version!r}, pyproject.toml says {packaged!r}")
    sys.exit(1)

print(f"OK  tag and pyproject.toml agree on {packaged}")
