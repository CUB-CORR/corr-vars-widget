"""Read the packaging facts out of pyproject.toml.

Derived rather than hard-coded so that adding a sixth widget is a one-line
change to `ensured-targets` and the release guards follow automatically. A
verifier that has to be updated by hand is one that quietly stops verifying.

Deliberately avoids `tomllib`, which is 3.11+, so this runs under whatever
interpreter the workflow happens to have.
"""

from __future__ import annotations

import pathlib
import re

TEXT = pathlib.Path("pyproject.toml").read_text()


def version() -> str:
    """The version from the [project] table."""
    project = TEXT.split("[project]", 1)[-1]
    match = re.search(r'^version\s*=\s*"([^"]+)"', project, re.MULTILINE)
    if not match:
        raise SystemExit("FAIL: could not find a version in pyproject.toml")
    return match.group(1)


def package() -> str:
    """The import name, taken from the wheel's own package list."""
    wheel = TEXT.split("[tool.hatch.build.targets.wheel]", 1)[-1]
    match = re.search(r'packages\s*=\s*\[\s*"([^"]+)"', wheel)
    if not match:
        raise SystemExit("FAIL: could not find the wheel package in pyproject.toml")
    return match.group(1).strip("/").split("/")[-1]


def bundles() -> list[str]:
    """Every built asset, as the path it takes inside the wheel.

    `ensured-targets` lists them as `py/<pkg>/static/...`; the sdist flattens
    `py/<pkg>/` to `<pkg>/`, and the wheel is built from the unpacked sdist.
    """
    block = TEXT.split("ensured-targets = [", 1)[-1].split("]", 1)[0]
    targets = re.findall(r'"([^"]+)"', block)
    return sorted(re.sub(r"^py/", "", target) for target in targets)
