# corr_vars_widget

A collection of [AnyWidgets](https://anywidget.dev/) for the `corr_vars` package.

## Widgets

### ObsWidget

Displays a `polars.DataFrame` in a [Quak Widget](https://github.com/manzt/quak) with additional infos about the shape and the observation level.

![ObsWidget](https://raw.githubusercontent.com/CUB-CORR/corr-vars-widget/main/assets/obs-widget.png)

### ObsmWidget

Displays a list of `polars.DataFrame` in [Quak Widgets](https://github.com/manzt/quak) within collapsible accordions with additional infos about the shape of the respective `polars.DataFrame`.

![ObsmWidget](https://raw.githubusercontent.com/CUB-CORR/corr-vars-widget/main/assets/obsm-widget.png)

### JsonWidget

Displays a searchable JSON viewer (filtering the keys of the first level). The JSON object is displayed in a collapsible view.

![JsonWidget](https://raw.githubusercontent.com/CUB-CORR/corr-vars-widget/main/assets/json-widget.png)

### JsonmWidget

Displays a dict of JSON objects in collapsible accordions. A shared search bar filters the first-level keys across all JSON views.

![JsonmWidget](https://raw.githubusercontent.com/CUB-CORR/corr-vars-widget/main/assets/jsonm-widget.png)

### TimeseriesWidget

Displays per-ID clinical timeseries over a shared, synchronized time axis, backed by DuckDB. It combines three lane types in one view: **interval** lanes (Gantt-style bars), **event** lanes (point-in-time dots), and **value** charts (line/area). Pick an ID with the searchable combobox, pan/zoom via the overview strip, and toggle labels from the settings popover. Provide a `color_col` (any CSS color or shadcn CSS variable) to colour rows explicitly.

A fluent `Timeseries` builder is available as the primary API:

```python
(
    Timeseries(id_col="stay_id", start_col="start", end_col="end", value_col="value")
    .interval("Device", devices)
    .event("Sedation", sedation)
    .value("PaO₂", pao2)
)
```

![TimeseriesWidget](https://raw.githubusercontent.com/CUB-CORR/corr-vars-widget/main/assets/timeseries-widget.png)

## Development

Development requires [`uv`](https://github.com/astral-sh/uv) and
[`pnpm`](https://pnpm.io/).

```sh
uv venv
uv pip install -e . --group dev
pnpm dev # start a development server
uv run jupyter lab notebooks/example.ipynb
```
