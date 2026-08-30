"""Check that the built distribution is one we would want to publish.

Every assertion here corresponds to something that has actually gone wrong in
this project or the template it came from. They are cheap; the failures they
catch are not, because a bad wheel on PyPI cannot be replaced, only superseded.

The expected contents are derived from `ensured-targets` in pyproject.toml, so
a new widget is covered the moment it is added to the build.
"""

from __future__ import annotations

import glob
import pathlib
import sys
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import _project

# The largest production bundle here is the timeseries one at ~1.1MB, which
# carries vgplot and DuckDB-WASM's client. A dev bundle is several times that,
# because the inline sourcemap is bigger than the code it maps.
MAX_JS_BYTES = 3_000_000


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def main() -> None:
    package = _project.package()
    wheels = glob.glob("dist/*.whl")
    sdists = glob.glob("dist/*.tar.gz")

    if len(wheels) != 1:
        fail(f"expected exactly one wheel, found {wheels}")
    if len(sdists) != 1:
        fail(f"expected exactly one sdist, found {sdists}")

    expected = {f"{package}/__init__.py", *_project.bundles()}

    wheel = wheels[0]
    with zipfile.ZipFile(wheel) as archive:
        names = {n for n in archive.namelist() if ".dist-info/" not in n}

        # The sdist flattens `py/<pkg>/` to `<pkg>/`, and the wheel is built from
        # the unpacked sdist. Get the paths wrong and the wheel installs cleanly
        # while containing nothing at all.
        missing = expected - names
        if missing:
            fail(f"wheel is missing {sorted(missing)}; it contains {sorted(names)}")

        for name in sorted(expected):
            blob = archive.read(name)
            if not blob:
                fail(f"{name} is empty")

            if name.endswith(".js"):
                # `npm run dev` and `npm run build` share an output directory. A
                # stale dev bundle reaching a release is invisible until someone
                # loads the widget.
                if b"sourceMappingURL" in blob:
                    fail(f"{name} carries a sourcemap -- a dev bundle, not a build")
                if len(blob) > MAX_JS_BYTES:
                    fail(f"{name} is {len(blob):,} bytes, over the {MAX_JS_BYTES:,} limit")

            if name.endswith(".css"):
                # A bundled webfont inlines its subsets as base64. Here that was
                # 291KB -- 82% of the stylesheet -- repeated in all five widgets,
                # for a face that nothing on the page ever resolved to.
                if b"base64" in blob:
                    fail(f"{name} contains base64 data -- a font or image is inlined")

    print(f"OK  {wheel}")
    for name in sorted(expected):
        with zipfile.ZipFile(wheel) as archive:
            print(f"    {len(archive.read(name)):>9,}  {name}")
    print(f"OK  {sdists[0]}")


if __name__ == "__main__":
    main()
