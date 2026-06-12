# Changelog

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
