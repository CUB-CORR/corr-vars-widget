# Modification of
#   https://github.com/manzt/quak/blob/main/src/quak/_widget.py
#   https://github.com/manzt/quak/blob/main/src/quak/_util.py

# MIT License

# Copyright (c) 2024 Trevor Manz

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import annotations

from datetime import datetime
import io
import json
import logging
import pathlib
import textwrap
import time

import anywidget
import duckdb
import polars as pl
import pyarrow as pa
import pyarrow.feather as feather
import traitlets

from collections.abc import Mapping
from typing import Final

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

BUNDLER_ASSETS_DIR: Final = pathlib.Path(__file__).parent / "static"
SLOW_QUERY_THRESHOLD: Final = 5000


def table_to_ipc(
    table: pa.lib.Table | pa.lib.RecordBatch | pa.lib.RecordBatchReader,
) -> memoryview:
    """Convert Arrow tabular data to an Arrow IPC message."""
    if isinstance(table, pa.RecordBatchReader):
        table = table.read_all()
    elif isinstance(table, pa.RecordBatch):
        table = pa.Table.from_batches([table], schema=table.schema)
    elif not isinstance(table, pa.Table):
        raise TypeError(
            "Expected a pyarrow Table, RecordBatch, or RecordBatchReader,",
            f"got {type(table)!r}",
        )

    sink = io.BytesIO()
    feather.write_feather(table, sink, compression="uncompressed")
    return sink.getbuffer()


class _DuckDBQueryMixin:
    """Serves Mosaic query requests from a DuckDB connection.

    Subclasses must set `self._conn` before calling `self.on_msg`.
    """

    _conn: duckdb.DuckDBPyConnection

    def _handle_custom_msg(self, data: dict, buffers: list) -> None:
        logger.debug(f"{data=}, {buffers=}")

        start = time.time()

        uuid = data["uuid"]
        sql = data["sql"]
        command = data["type"]
        try:
            if command == "arrow":
                result = self._conn.query(sql).arrow()
                buf = table_to_ipc(result)
                self.send({"type": "arrow", "uuid": uuid}, buffers=[buf])
            elif command == "exec":
                self._conn.execute(sql)
                self.send({"type": "exec", "uuid": uuid})
            elif command == "json":
                # Avoid DuckDB's `.df()`, which pulls in pandas and numpy.
                result = self._conn.query(sql)
                records = [dict(zip(result.columns, row)) for row in result.fetchall()]
                self.send({"type": "json", "uuid": uuid, "result": records})
            else:
                raise ValueError(f"Unknown command {command}")
        except Exception as e:
            logger.exception("Error processing query")
            self.send({"error": str(e), "uuid": uuid})

        total = round((time.time() - start) * 1_000)
        if total > SLOW_QUERY_THRESHOLD:
            logger.warning(f"DONE. Slow query {uuid} took {total} ms.\n{sql}")
        else:
            logger.info(f"DONE. Query {uuid} took {total} ms.\n{sql}")


class ObsWidget(_DuckDBQueryMixin, anywidget.AnyWidget):
    """An anywidget for displaying obs data in a table."""

    _esm = BUNDLER_ASSETS_DIR / "obs" / "obs.js"
    _css = BUNDLER_ASSETS_DIR / "obs" / "main.css"

    _obs_level = traitlets.Unicode().tag(sync=True)
    _creation_time = traitlets.Float(allow_none=True).tag(sync=True)

    _table_name = traitlets.Unicode().tag(sync=True)
    _columns = traitlets.List(traitlets.Unicode()).tag(sync=True)

    # The SQL query for the current data (read-only)
    sql = traitlets.Unicode().tag(sync=True)

    def __init__(
        self,
        data: pl.DataFrame,
        obs_level: str | None = None,
        creation_time: datetime | None = None,
    ) -> None:
        """
        Initialize the ObsWidget.

        Args:
            data: A Polars DataFrame containing the observation data.
            obs_level: An optional string representing the observation level
                       (e.g., 'Hospital', 'ICU stay').
        """
        table = "obs"

        conn = duckdb.connect(":memory:")
        # FIXME: special case pl.DataFrame for now until DuckDB
        # supports `[string,bytes]_view` Arrow data types
        # see: https://github.com/manzt/quak/issues/41
        # Polars .to_arrow() method will cast to non-view array types for us
        arrow_table = data.to_arrow()
        conn.register(table, arrow_table)
        self._conn = conn
        self._shape = data.shape
        self._data = data
        super().__init__(
            _obs_level=obs_level or "",
            _creation_time=creation_time.timestamp() if creation_time else None,
            _table_name=table,
            _columns=data.columns,
            sql=f'SELECT * FROM "{table}"',
        )
        self.on_msg(self._handle_custom_msg)

    def __repr__(self) -> str:
        with pl.Config(set_tbl_hide_dataframe_shape=True):
            _data_repr = repr(self._data)
        lines = "\n".join(
            [
                f'obs_level="{self._obs_level}", shape={self._shape},',
                "data=",
                _data_repr,
            ]
        )
        return "Obs(\n" + textwrap.indent(lines, "  ") + "\n)"

    def data(self) -> duckdb.DuckDBPyRelation:
        """Return the current SQL as a DuckDB relation."""
        return self._conn.query(self.sql)


class ObsmWidget(_DuckDBQueryMixin, anywidget.AnyWidget):
    """An anywidget for displaying obsm data in a table."""

    _esm = BUNDLER_ASSETS_DIR / "obsm" / "obsm.js"
    _css = BUNDLER_ASSETS_DIR / "obsm" / "main.css"

    _tables = traitlets.List(
        traitlets.Dict(
            per_key_traits={
                "_table_name": traitlets.Unicode(),
                "_columns": traitlets.List(traitlets.Unicode()),
                "sql": traitlets.Unicode(),
            }
        )
    ).tag(sync=True)

    def __init__(self, data: Mapping[str, pl.DataFrame]) -> None:
        """
        Initialize the ObsmWidget.

        Args:
            data: A dictionary mapping table names to Polars DataFrames.
        """

        conn = duckdb.connect(":memory:")
        tables = []
        for table, df in data.items():
            # FIXME: special case pl.DataFrame for now until DuckDB
            # supports `[string,bytes]_view` Arrow data types
            # see: https://github.com/manzt/quak/issues/41
            # Polars .to_arrow() method will cast to non-view array types for us
            arrow_table = df.to_arrow()
            conn.register(table, arrow_table)
            tables.append(
                {
                    "_table_name": table,
                    "_columns": df.columns,
                    "sql": f'SELECT * FROM "{table}"',
                }
            )
        self._conn = conn
        self._shapes = {name: df.shape for name, df in data.items()}
        super().__init__(_tables=tables)
        self.on_msg(self._handle_custom_msg)

    def __repr__(self) -> str:
        lines = "\n".join(
            [f"{name}: shape={shape}" for name, shape in self._shapes.items()]
        )
        return (
            "ObsmDict(\n" + textwrap.indent(lines, "  ") + "\n)"
            if lines
            else "ObsmDict(Ø)"
        )

    @property
    def sql(self) -> dict[str, str]:
        """Return the current SQL as a DuckDB relation."""
        return {table["_table_name"]: table["sql"] for table in self._tables}

    @property
    def data(self) -> dict[str, duckdb.DuckDBPyRelation]:
        """Return the current SQL as a DuckDB relation."""
        return {
            table["_table_name"]: self._conn.query(table["sql"])
            for table in self._tables
        }


def _quote(identifier: str) -> str:
    """Quote a SQL identifier, escaping any embedded double quotes."""
    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'


class TimeseriesWidget(_DuckDBQueryMixin, anywidget.AnyWidget):
    """An anywidget plotting per-ID timeseries with vgplot.

    Interval tables are drawn as Gantt-style lanes in a single shared plot, one
    lane per table. Event tables become extra lanes in that same plot, drawn as
    dots at a single timestamp (for point-in-time facts such as procedures or
    text-valued observations, where the value belongs in the tooltip rather than
    on a y scale). Value tables are drawn as small line charts stacked beneath,
    one plot per table. All plots share an x scale and are filtered down to a
    single ID chosen from the combobox.
    """

    _esm = BUNDLER_ASSETS_DIR / "timeseries" / "timeseries.js"
    _css = BUNDLER_ASSETS_DIR / "timeseries" / "main.css"

    # DuckDB config: the registered table names the JS side references via
    # vgplot's `from()`, plus the columns that make up the plot encodings.
    _intervals = traitlets.List(traitlets.Unicode()).tag(sync=True)
    _events = traitlets.List(traitlets.Unicode()).tag(sync=True)
    _values = traitlets.List(traitlets.Unicode()).tag(sync=True)
    _ids_table = traitlets.Unicode().tag(sync=True)

    _id_col = traitlets.Unicode().tag(sync=True)
    _start_col = traitlets.Unicode().tag(sync=True)
    _end_col = traitlets.Unicode().tag(sync=True)
    _value_col = traitlets.Unicode().tag(sync=True)
    # Optional column holding a per-interval CSS colour; falls back to the chart
    # palette where null. Empty string means "not provided".
    _color_col = traitlets.Unicode().tag(sync=True)

    # Whether `start_col` is a date/time, so the JS side can rebuild the shared
    # x domain as Dates rather than plain numbers.
    _temporal = traitlets.Bool().tag(sync=True)
    _initial_id = traitlets.Any(allow_none=True).tag(sync=True)
    # Initial state of the in-widget label toggles (the widget owns them at
    # runtime). Interval labels sit inside the bars; event labels beside the dots.
    _interval_labels = traitlets.Bool().tag(sync=True)
    _event_labels = traitlets.Bool().tag(sync=True)

    def __init__(
        self,
        intervals: Mapping[str, pl.DataFrame] | None = None,
        values: Mapping[str, pl.DataFrame] | None = None,
        events: Mapping[str, pl.DataFrame] | None = None,
        id_col: str = "id",
        start_col: str = "start",
        end_col: str = "end",
        value_col: str = "value",
        color_col: str | None = None,
        interval_labels: bool = True,
        event_labels: bool = False,
    ) -> None:
        """
        Initialize the TimeseriesWidget.

        Args:
            intervals: Tables with a start and an end, drawn as one lane each.
                       The dict key labels the lane.
            values: Tables with a single timestamp per row, drawn as one line
                    plot each. The dict key labels the plot.
            events: Tables with a single timestamp per row, drawn as dots on
                    one lane each (appended below the interval lanes). Use for
                    point-in-time facts — procedures, text-valued observations —
                    where the value should not become a y scale; it is shown in
                    the tooltip (or beside the dot with `event_labels=True`).
                    `end_col` is not required.
            id_col: Column identifying the entity (e.g. a stay), present in
                    every table. Drives the menu and filters every plot.
            start_col: Timestamp column starting an interval / locating a value.
            end_col: Timestamp column ending an interval. Interval tables only.
            value_col: Column plotted on the y axis (values) or used as the
                       fill and label (intervals).
            color_col: Optional column holding a CSS colour per row (e.g.
                       "#ff0000" or "var(--chart-4)"), on interval and/or value
                       tables. It is optional per table: tables without it (and
                       rows where it is null) fall back to the default colours
                       (the chart palette for intervals, the primary colour for
                       values), so a single lane/series can be coloured while
                       the rest are not.
        """
        intervals = dict(intervals or {})
        values = dict(values or {})
        events = dict(events or {})
        if not intervals and not values and not events:
            raise ValueError("Pass at least one interval, event or value table.")

        seen: dict[str, str] = {}
        for kind, tables in (("intervals", intervals), ("events", events), ("values", values)):
            for name in tables:
                if name in seen:
                    raise ValueError(
                        f"Table names must be unique across intervals, events and values: "
                        f"{name!r} appears in both {seen[name]} and {kind}"
                    )
                seen[name] = kind

        conn = duckdb.connect(":memory:")
        for name, df, required in [
            *((n, d, (id_col, start_col, end_col, value_col)) for n, d in intervals.items()),
            # Events are point-in-time, so they need no `end_col`.
            *((n, d, (id_col, start_col, value_col)) for n, d in events.items()),
            *((n, d, (id_col, start_col, value_col)) for n, d in values.items()),
        ]:
            missing = [col for col in required if col not in df.columns]
            if missing:
                raise ValueError(f"Table {name!r} is missing column(s): {missing}")
            # `color_col` is optional per table: add it as an all-null VARCHAR
            # column where absent so the JS COALESCE still resolves and those
            # rows fall back to the default colour.
            if color_col and color_col not in df.columns:
                df = df.with_columns(pl.lit(None, dtype=pl.Utf8).alias(color_col))
            # FIXME: special case pl.DataFrame for now until DuckDB
            # supports `[string,bytes]_view` Arrow data types
            # see: https://github.com/manzt/quak/issues/41
            # Polars .to_arrow() method will cast to non-view array types for us
            conn.register(name, df.to_arrow())

        # A view of every ID across every table, so the menu offers the full
        # set even when an ID is absent from some of them.
        ids_table = "__ids"
        union = " UNION ALL ".join(
            f"SELECT {_quote(id_col)} FROM {_quote(name)}"
            for name in (*intervals, *events, *values)
        )
        conn.execute(
            f"CREATE VIEW {_quote(ids_table)} AS "
            f"SELECT DISTINCT {_quote(id_col)} FROM ({union}) "
            f"WHERE {_quote(id_col)} IS NOT NULL "
            f"ORDER BY {_quote(id_col)}"
        )
        first = conn.execute(f"SELECT * FROM {_quote(ids_table)} LIMIT 1").fetchone()

        any_df = next(iter({**intervals, **events, **values}.values()))

        self._conn = conn
        self._shapes = {
            name: df.shape
            for name, df in (*intervals.items(), *events.items(), *values.items())
        }
        super().__init__(
            _intervals=list(intervals),
            _events=list(events),
            _values=list(values),
            _ids_table=ids_table,
            _id_col=id_col,
            _start_col=start_col,
            _end_col=end_col,
            _value_col=value_col,
            _color_col=color_col or "",
            _temporal=any_df.schema[start_col].is_temporal(),
            _initial_id=first[0] if first else None,
            _interval_labels=interval_labels,
            _event_labels=event_labels,
        )
        self.on_msg(self._handle_custom_msg)

    def __repr__(self) -> str:
        lines = "\n".join(
            [f"{name}: shape={shape}" for name, shape in self._shapes.items()]
        )
        return "Timeseries(\n" + textwrap.indent(lines, "  ") + "\n)"

    @property
    def data(self) -> dict[str, duckdb.DuckDBPyRelation]:
        """Return each registered table as a DuckDB relation."""
        return {
            name: self._conn.query(f"SELECT * FROM {_quote(name)}")
            for name in (*self._intervals, *self._events, *self._values)
        }


class Timeseries:
    """Fluent builder for a :class:`TimeseriesWidget` (à la Altair).

    Set the column mapping once, then chain ``.interval()`` / ``.event()`` /
    ``.value()`` to add series. The result is displayable directly — no build
    step — because it renders the underlying widget on demand:

    >>> (
    ...     Timeseries(id_col="stay_id", start_col="start", end_col="end", value_col="value")
    ...     .interval("Device", devices_df)
    ...     .event("ECG", ecg_df)
    ...     .value("Sodium", sodium_df)
    ...     .color("colour")
    ... )
    """

    def __init__(
        self,
        *,
        id_col: str = "id",
        start_col: str = "start",
        end_col: str = "end",
        value_col: str = "value",
    ) -> None:
        self._id_col = id_col
        self._start_col = start_col
        self._end_col = end_col
        self._value_col = value_col
        self._intervals: dict[str, pl.DataFrame] = {}
        self._events: dict[str, pl.DataFrame] = {}
        self._values: dict[str, pl.DataFrame] = {}
        self._color_col: str | None = None
        self._interval_labels = True
        self._event_labels = False
        self._widget: TimeseriesWidget | None = None

    def interval(self, name: str, df: pl.DataFrame) -> "Timeseries":
        """Add a lane of start/end intervals (Gantt-style bars)."""
        self._intervals[name] = df
        return self._touch()

    def event(self, name: str, df: pl.DataFrame) -> "Timeseries":
        """Add a lane of point-in-time events (dots; value in the tooltip)."""
        self._events[name] = df
        return self._touch()

    def value(self, name: str, df: pl.DataFrame) -> "Timeseries":
        """Add a numeric series drawn as its own small line chart."""
        self._values[name] = df
        return self._touch()

    def color(self, col: str | None) -> "Timeseries":
        """Name the optional per-row CSS-colour column (see ``color_col``)."""
        self._color_col = col
        return self._touch()

    def labels(
        self, *, intervals: bool | None = None, events: bool | None = None
    ) -> "Timeseries":
        """Set the initial state of the in-widget label toggles."""
        if intervals is not None:
            self._interval_labels = intervals
        if events is not None:
            self._event_labels = events
        return self._touch()

    def _touch(self) -> "Timeseries":
        # Invalidate any cached widget so the next render reflects new data.
        self._widget = None
        return self

    def build(self) -> TimeseriesWidget:
        """Materialise (and cache) the underlying widget."""
        if self._widget is None:
            self._widget = TimeseriesWidget(
                intervals=self._intervals,
                events=self._events,
                values=self._values,
                id_col=self._id_col,
                start_col=self._start_col,
                end_col=self._end_col,
                value_col=self._value_col,
                color_col=self._color_col,
                interval_labels=self._interval_labels,
                event_labels=self._event_labels,
            )
        return self._widget

    def _repr_mimebundle_(self, **kwargs: object) -> object:
        # Makes the builder itself the thing Jupyter displays.
        return self.build()._repr_mimebundle_(**kwargs)

    def __repr__(self) -> str:
        return repr(self.build())


class JsonWidget(anywidget.AnyWidget):
    """An anywidget for displaying json data"""

    _esm = BUNDLER_ASSETS_DIR / "json" / "json.js"
    _css = BUNDLER_ASSETS_DIR / "json" / "main.css"

    json = traitlets.Unicode().tag(sync=True)

    def __init__(
        self,
        data: object | str,
    ) -> None:
        """
        Initialize the JsonWidget.

        Args:
            data: A JSON-serializable object or a JSON string.
        """
        super().__init__(json=json.dumps(data) if not isinstance(data, str) else data)


class JsonmWidget(anywidget.AnyWidget):
    """An anywidget for displaying a dict of JSON entries in an accordion view."""

    _esm = BUNDLER_ASSETS_DIR / "jsonm" / "jsonm.js"
    _css = BUNDLER_ASSETS_DIR / "jsonm" / "main.css"

    _jsons = traitlets.Dict(
        value_trait=traitlets.Unicode(),
        key_trait=traitlets.Unicode(),
    ).tag(sync=True)

    def __init__(self, data: Mapping[str, object | str]) -> None:
        """
        Initialize the JsonmWidget.

        Args:
            data: A dictionary mapping names to JSON-serializable objects or JSON strings.
        """
        items = {
            key: value if isinstance(value, str) else json.dumps(value)
            for key, value in data.items()
        }
        super().__init__(_jsons=items)


__all__ = [
    "ObsWidget",
    "ObsmWidget",
    "TimeseriesWidget",
    "Timeseries",
    "JsonWidget",
    "JsonmWidget",
]
