# Changelog

## [Unreleased]

### Added

- `TimeseriesWidget` windows and anchors (#4). A **window** is a shaded band
  between two timestamps (an admission, an ICU stay); an **anchor** is a vertical
  rule at one (a death, a transfer). Both are drawn across the lanes, every value
  chart and the overview strip rather than occupying a lane, so a reading can be
  placed against them directly. Passed as `windows=` / `anchors=`, or built with
  `.window()` / `.anchor()`; named by the dict key, labelled once on the topmost
  plot and toggleable from the settings popover.

  They are neutral grey unless `color_col` names a colour, so the red death line
  is opt-in. They do not widen the fitted time range and contribute no IDs to the
  menu, since they annotate data rather than being data.

- A `theme` trait on every widget, accepting `"auto"` (the default), `"light"`
  or `"dark"`, and assignable at runtime to re-theme a widget already on screen.
  `auto` infers the host notebook's theme from what it has actually painted,
  falling back to the browser's colour-scheme preference. Useful in VS Code,
  which paints the widget output area white whatever the editor theme is.
- `Timeseries.theme()` on the fluent builder.

### Fixed

- `TimeseriesWidget` tooltips were unreadable in dark mode. Observable Plot fills
  the bubble with `--plot-background`, which it hard-codes to white on the `svg`
  itself, while drawing the text in `currentColor` — so the text followed the
  dark theme onto a white bubble.
- `ObsWidget` and `ObsmWidget` are legible in dark mode. quak renders into a
  shadow root with light-only styling and has no dark theme yet, so the table is
  inverted with a filter until it does.
- The `TimeseriesWidget` settings button no longer stands taller than the ID
  navigator beside it; both now take the same size from the button variant.
- Dropped a `console.log` that fired on every keystroke in the JSON search box.
- Widget styles no longer leak into the host notebook. The base layer applied
  `border-color` and `outline-color` to `*`, unscoped, which reached every
  element on the page including other widgets; it is now confined to the
  widget's own root.
- Every widget now paints its own background and foreground. The rules meant to
  do this were written as `:host(body)` and `:host(html)`, which only match
  inside a shadow root — anywidget renders into the host document, so they never
  applied and the widgets inherited whatever the notebook painted.

### Changed

- Dropped the bundled Inter webfont, which inlined 291KB of base64 into each of
  the five stylesheets — 82% of every file — for a face nothing resolved to.
  Stylesheets fall from 356KB to 63KB, and the wheel from 2.0MB to 916KB. The
  widgets inherit the host notebook's typography, as they already did in
  practice.

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
