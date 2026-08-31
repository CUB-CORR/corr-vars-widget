"""Exercise the installed package, on the oldest Python we claim to support.

This is not a substitute for a test suite. It checks the things that would make
a release useless: that the module imports at all, that all five bundles made it
into the wheel, and that each widget's documented contract holds.
"""

from __future__ import annotations

import sys

import corr_vars_widget as cvw
import polars as pl
import traitlets
from corr_vars_widget import (
    JsonmWidget,
    JsonWidget,
    ObsmWidget,
    ObsWidget,
    Timeseries,
    TimeseriesWidget,
)

print(f"python {sys.version.split()[0]}, corr_vars_widget from {cvw.__file__}")

# Every bundle the build promises, present and non-empty.
for widget, entry in [
    ("obs", "obs.js"),
    ("obsm", "obsm.js"),
    ("json", "json.js"),
    ("jsonm", "jsonm.js"),
    ("timeseries", "timeseries.js"),
]:
    for name in (entry, "main.css"):
        path = cvw.BUNDLER_ASSETS_DIR / widget / name
        assert path.exists(), f"{path} missing from the installed package"
        assert path.stat().st_size > 0, f"{path} is empty"

obs = pl.DataFrame({"id": [1, 2, 3], "value": ["a", "b", "c"]})

# ObsWidget: the SQL is the public handle on the data, and `.data()` runs it.
w = ObsWidget(obs, obs_level="stay")
assert w.sql == 'SELECT * FROM "obs"', w.sql
assert w.data().fetchall() == [(1, "a"), (2, "b"), (3, "c")]
assert w._columns == ["id", "value"], w._columns

# ObsmWidget: one registered table per key, each with its own SQL.
m = ObsmWidget({"first": obs, "second": obs.head(1)})
assert set(m.sql) == {"first", "second"}, m.sql
assert m.data["second"].fetchall() == [(1, "a")]

# JsonWidget takes an object or a string; both end up as a JSON string.
assert JsonWidget({"a": 1}).json == '{"a": 1}'
assert JsonWidget('{"a": 1}').json == '{"a": 1}'
assert JsonmWidget({"one": {"a": 1}})._jsons == {"one": '{"a": 1}'}

# TimeseriesWidget: at least one table is required, names must not collide
# across kinds, and every table must carry the configured columns.
intervals = pl.DataFrame(
    {"id": [1, 1], "start": [0, 5], "end": [5, 10], "value": ["vent", "wean"]}
)
values = pl.DataFrame({"id": [1, 1], "start": [0, 5], "value": [140.0, 138.0]})

for bad, why in [
    ({}, "no tables at all"),
    ({"intervals": {"x": intervals}, "values": {"x": values}}, "a name used twice"),
    ({"values": {"x": values.drop("value")}}, "a missing column"),
]:
    try:
        TimeseriesWidget(**bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"TimeseriesWidget should reject {why}")

# Windows and anchors annotate; they need no value column, and a window needs an
# end while an anchor does not.
windows = pl.DataFrame({"id": [1, 2], "start": [-5, 0], "end": [20, 3]})
anchors = pl.DataFrame({"id": [1], "start": [7]})

for bad, why in [
    (dict(intervals={"D": intervals}, windows={"W": anchors}), "a window with no end column"),
    (dict(intervals={"D": intervals}, windows={"D": windows}), "a name colliding with an interval"),
    (dict(windows={"W": windows}), "annotations with nothing to annotate"),
]:
    try:
        TimeseriesWidget(**bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"TimeseriesWidget should reject {why}")

annotated = TimeseriesWidget(
    intervals={"Device": intervals}, windows={"Admission": windows}, anchors={"Death": anchors}
)
assert annotated._windows == ["Admission"] and annotated._anchors == ["Death"]
# `data` hands back every registered table, annotations included.
assert set(annotated.data) == {"Device", "Admission", "Death"}, set(annotated.data)
# id 2 appears only in the window, so it must not reach the menu: it has nothing
# to plot and no extent to fit a time range to.
menu = [row[0] for row in annotated._conn.execute('SELECT * FROM "__ids"').fetchall()]
assert menu == [1], menu

ts = TimeseriesWidget(intervals={"Device": intervals}, values={"Sodium": values})
assert ts._intervals == ["Device"] and ts._values == ["Sodium"]
# The id view unions every table, so an id present in only one still appears.
assert ts._initial_id == 1, ts._initial_id
assert set(ts.data) == {"Device", "Sodium"}, set(ts.data)

# The builder produces the same widget, and re-renders after a change.
builder = Timeseries(id_col="id").interval("Device", intervals).value("Sodium", values)
built = builder.build()
assert built is builder.build(), "build() should cache"
assert (
    builder.event("ECG", values).build() is not built
), "adding a table should rebuild"
assert builder.build()._events == ["ECG"]

# The `theme` trait is shared by every widget through `_ThemeMixin`, so check it
# on every widget rather than trusting the mixin to have been inherited.
for name, make in [
    ("ObsWidget", lambda **k: ObsWidget(obs, **k)),
    ("ObsmWidget", lambda **k: ObsmWidget({"a": obs}, **k)),
    ("TimeseriesWidget", lambda **k: TimeseriesWidget(intervals={"Device": intervals}, **k)),
    ("JsonWidget", lambda **k: JsonWidget({"a": 1}, **k)),
    ("JsonmWidget", lambda **k: JsonmWidget({"a": {"b": 1}}, **k)),
]:
    assert make().theme == "auto", f"{name} should default to auto"
    widget = make(theme="dark")
    assert widget.theme == "dark", name
    # Unsynced, and the frontend would never see it.
    assert widget.traits()["theme"].metadata.get("sync"), f"{name}.theme is not synced"
    # Live, or `widget.theme = ...` in a later cell would do nothing.
    widget.theme = "light"
    assert widget.theme == "light", name
    try:
        widget.theme = "puce"
    except traitlets.TraitError:
        pass
    else:
        raise AssertionError(f"{name} accepted an invalid theme")

# The builder carries it through, and changing it rebuilds.
# The builder carries windows and anchors through too.
annotated_builder = (
    Timeseries(id_col="id")
    .interval("Device", intervals)
    .window("Admission", windows)
    .anchor("Death", anchors)
    .labels(annotations=False)
)
built_annotated = annotated_builder.build()
assert built_annotated._windows == ["Admission"], built_annotated._windows
assert built_annotated._anchors == ["Death"], built_annotated._anchors
assert built_annotated._annotation_labels is False

themed = Timeseries(id_col="id").interval("Device", intervals).theme("dark")
assert themed.build().theme == "dark"
assert themed.theme("light").build().theme == "light"

print("OK  all smoke checks passed")
