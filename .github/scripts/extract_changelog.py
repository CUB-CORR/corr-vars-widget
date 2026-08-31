"""Print the CHANGELOG.md section for one version.

Used to build the GitHub release body. Exits non-zero when the version has no
entry, which fails the release rather than publishing one with empty notes --
the notes are the first thing anyone reads, and a missing changelog entry is
easier to fix before the tag than after it.
"""

from __future__ import annotations

import pathlib
import re
import sys

version = sys.argv[1]
lines = pathlib.Path("CHANGELOG.md").read_text().splitlines()

# Headings look like `## [0.0.10] - 2026-07-28`; match the version, not the date.
heading = re.compile(rf"^##\s+\[{re.escape(version)}\]")
start = next((i for i, line in enumerate(lines) if heading.match(line)), None)
if start is None:
    print(f"FAIL: CHANGELOG.md has no entry for {version}", file=sys.stderr)
    sys.exit(1)

end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
body = "\n".join(lines[start + 1 : end]).strip()

if not body:
    print(f"FAIL: the CHANGELOG.md entry for {version} is empty", file=sys.stderr)
    sys.exit(1)

print(body)
