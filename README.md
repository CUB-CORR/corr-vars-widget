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

## Theming

Every widget takes a `theme` of `"auto"` (the default), `"light"` or `"dark"`.

```python
ObsWidget(df, theme="dark")

w = ObsWidget(df)
w.theme = "dark"   # live: re-themes a widget that is already on screen
```

`auto` infers the host notebook's theme, which is guesswork — there is no
standard way for a host to announce it, so a host that paints nothing readable
will be guessed wrong. Pin it when that happens, when a notebook will be read by
someone whose OS setting you do not know, or simply because you prefer one.

**In VS Code**, the widget output area is painted white whatever the editor theme
is. That area lies outside the widget, so a dark widget sits on a white surround
there; `theme="light"` avoids the mismatch.

The `Timeseries` builder takes it as a step, like the other options:

```python
Timeseries(id_col="stay_id").interval("Device", devices).theme("dark")
```

The trait is declared once, in `_ThemeMixin`, and every widget inherits it; the
frontend mirrors that as the `Themed` type in `src/lib/theme.svelte.ts`, which
each widget's own model intersects with. Adding another shared trait means
editing those two places, not ten.

## Development

Development requires [`uv`](https://github.com/astral-sh/uv) and `npm`.

```sh
uv venv
uv pip install -e . --group dev
npm ci
npm run dev # rebuild every widget on change
uv run jupyter lab notebooks/example.ipynb
```

`npm run dev` and `npm run build` write to the same directories. The dev bundles
carry an inline sourcemap and are several times the size of a build, so run
`npm run build` before measuring anything — and note that `uv build` always
rebuilds from source, so a dev bundle cannot reach a release.

Both gates are expected to pass before a change lands:

```sh
npm run check   # svelte-check, then tsc over the vite configs
npm run lint    # prettier --check
```

## Continuous integration

`ci.yml` typechecks and lints the frontend, builds the distribution, and installs
that wheel on the oldest and newest supported Python to exercise every widget.
Keep the matrix floor in step with `requires-python`: 3.9 is the version that
catches both syntax a newer interpreter accepts silently and a dependency that
has quietly stopped publishing wheels for it.

`.github/scripts/verify_dist.py` holds the release guards, and each corresponds
to a failure this project or its template actually produced:

- The wheel must contain the package and all ten built assets. The sdist
  flattens `py/corr_vars_widget/` to `corr_vars_widget/` and the wheel is built
  from the unpacked sdist, so wrong paths give a wheel that installs cleanly and
  contains nothing.
- No bundle may carry a sourcemap, or be implausibly large — that is a dev
  bundle, invisible until someone loads the widget.
- No stylesheet may contain base64, which is how a bundled webfont adds a few
  hundred KB to every widget on the page.

The expected contents are derived from `ensured-targets` in `pyproject.toml`, so
adding a sixth widget extends the guards automatically.

## Releasing

Publishing runs on a `v*` tag, through PyPI's Trusted Publishing, so there is no
API token to store. Before the first release, on PyPI add a publisher for this
repository naming the workflow file `release.yml` and the environment `pypi` —
then create that environment in the repository settings. A mismatch in any of
the three fails at the OIDC exchange.

```sh
# bump the version in pyproject.toml and package.json, add a CHANGELOG entry
npm install --package-lock-only   # keep the lockfile's version in step
git tag v0.0.11 && git push origin v0.0.11
```

The tag version must match `pyproject.toml`, and the version must have a
`CHANGELOG.md` entry — both are checked before anything is uploaded, so a
mismatch fails the release rather than putting a version nobody can find on
PyPI. PyPI is upload-once: a version can be superseded but never replaced, which
is why the GitHub release is created after the upload rather than before.
