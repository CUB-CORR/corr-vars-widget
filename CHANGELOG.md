# Changelog

## [0.0.10] - 2026-07-28

### Added
- `TimeseriesWidget`: per-ID clinical timeseries over a shared, synchronized time axis, backed by DuckDB. Combines three lane types in one view:
  - **Interval lanes** — Gantt-style bars per category table (e.g. device, ventilator mode).
  - **Event lanes** — point-in-time markers rendered as diamonds.
  - **Value charts** — line/area charts for numeric measurements.
- ID selection: a combobox with server-side search plus previous/next navigation, driving every plot's filter.
- Overview strip for panning and zooming the shared time range, with a reset to the selected ID's full extent.
- `Timeseries` fluent builder API (`.interval().event().value().color().labels().build()`) as the primary way to assemble a widget, alongside the `TimeseriesWidget(...)` constructor.
- Per-row custom colors via `color_col` for interval bars, event markers, and value marks — accepts any CSS color and shadcn CSS variables (e.g. `var(--destructive)`).
- Settings popover to toggle interval and event value labels independently.

### Changed
- Default interval/event colors alternate two chart colors by time order, so adjacent intervals always contrast; provide `color_col` to assign meaning.

## [0.0.9] - 2026-06-19

### Changed
- `ObsmWidget` and `JsonmWidget` constructors now accept any `Mapping` instead of `dict`.

## [0.0.8] - 2026-06-11

### Added
- `JsonmWidget`: displays a `dict[str, object]` of JSON entries in collapsible accordions. A shared search bar filters the first-level keys within each JSON view independently.

## [0.0.7] - 2026-06-02

### Added
- `JsonWidget`: searchable JSON viewer that filters and displays JSON objects in a collapsible tree view.
- `ObsWidget`: added optional `creation_time` parameter displayed in the widget header.

## [0.0.6] - 2026-06-02

### Fixed
- Fixed editable installs (`uv pip install -e .`).
- Fixed recursion error when passing subclassed DataFrames by saving data instead of repr.

## [0.0.5] - 2026-04-15

### Changed
- Switched to `__repr__` for widget string representation.

## [0.0.4] - 2026-04-13

### Fixed
- Reverted build config change that caused incorrect output.
- Removed private uv index from pyproject.toml.

## [0.0.3] - 2026-04-13 [YANKED]

### Added
- `__str__` methods on `ObsWidget` and `ObsmWidget`.

### Changed
- Simplified build steps.

## [0.0.2] - 2026-04-11

### Added
- First release with `ObsWidget` and `ObsmWidget`.
- `ObsWidget`: displays a `polars.DataFrame` in a Quak table with observation level metadata.
- `ObsmWidget`: displays a dict of `polars.DataFrame` in collapsible accordions, each backed by a Quak table.
- MIT License.
