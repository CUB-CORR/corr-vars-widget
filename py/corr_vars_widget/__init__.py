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

import io
import logging
import pathlib
import time

import anywidget
import duckdb
import polars as pl
import pyarrow as pa
import pyarrow.feather as feather
import traitlets

import pathlib

import anywidget
import traitlets

bundler_assets_dir = pathlib.Path(__file__).parent / "static"

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

SLOW_QUERY_THRESHOLD = 5000


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


class ObsWidget(anywidget.AnyWidget):
    """An anywidget for displaying obs data in a table."""

    _esm = bundler_assets_dir / "obs.js"
    _css = bundler_assets_dir / "main.css"

    _table_name = traitlets.Unicode().tag(sync=True)
    _columns = traitlets.List(traitlets.Unicode()).tag(sync=True)

    # The SQL query for the current data (read-only)
    sql = traitlets.Unicode().tag(sync=True)

    def __init__(self, data: pl.DataFrame) -> None:
        table = "obs"

        conn = duckdb.connect(":memory:")
        # FIXME: special case pl.DataFrame for now until DuckDB
        # supports `[string,bytes]_view` Arrow data types
        # see: https://github.com/manzt/quak/issues/41
        # Polars .to_arrow() method will cast to non-view array types for us
        arrow_table = data.to_arrow()
        conn.register(table, arrow_table)
        self._conn = conn
        super().__init__(
            _table_name=table,
            _columns=data.columns,
            sql=f'SELECT * FROM "{table}"',
        )
        self.on_msg(self._handle_custom_msg)

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
                result = self._conn.query(sql).df()
                json = result.to_dict(orient="records")
                self.send({"type": "json", "uuid": uuid, "result": json})
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

    def data(self) -> duckdb.DuckDBPyRelation:
        """Return the current SQL as a DuckDB relation."""
        return self._conn.query(self.sql)


class ObsmWidget(anywidget.AnyWidget):
    """An anywidget for displaying obsm data in a table."""

    _esm = bundler_assets_dir / "obsm.js"
    _css = bundler_assets_dir / "main.css"

    _tables = traitlets.List(
        traitlets.Dict(
            per_key_traits={
                "_table_name": traitlets.Unicode(),
                "_columns": traitlets.List(traitlets.Unicode()),
                "sql": traitlets.Unicode(),
            }
        )
    ).tag(sync=True)

    def __init__(self, data: dict[str, pl.DataFrame]) -> None:

        conn = duckdb.connect(":memory:")
        tables = []
        for table, data in data.items():
            # FIXME: special case pl.DataFrame for now until DuckDB
            # supports `[string,bytes]_view` Arrow data types
            # see: https://github.com/manzt/quak/issues/41
            # Polars .to_arrow() method will cast to non-view array types for us
            arrow_table = data.to_arrow()
            conn.register(table, arrow_table)
            tables.append(
                {
                    "_table_name": table,
                    "_columns": data.columns,
                    "sql": f'SELECT * FROM "{table}"',
                }
            )
        self._conn = conn
        super().__init__(_tables=tables)
        self.on_msg(self._handle_custom_msg)

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
                result = self._conn.query(sql).df()
                json = result.to_dict(orient="records")
                self.send({"type": "json", "uuid": uuid, "result": json})
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
