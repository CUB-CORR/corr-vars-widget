# corr_vars_widget

An collection of [AnyWidget](https://anywidget.dev/) for the `corr_vars` package.

## Widgets

### ObsWidget

Displays a `polars.DataFrame` in a [Quak Widget](https://github.com/manzt/quak) with additional infos about the shape and the observation level.

### ObsmWidget

Displays a list of `polars.DataFrame` in [Quak Widgets](https://github.com/manzt/quak) within collapsible accordions with additional infos about the shape of the respective `polars.DataFrame`.

## Development

Development requires [`uv`](https://github.com/astral-sh/uv) and
[`pnpm`](https://pnpm.io/).

```sh
uv venv
uv pip install -e . --group dev
pnpm dev # start a development server
uv run jupyter lab notebooks/example.ipynb
```