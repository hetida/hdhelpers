## [Unreleased]

- Add validated, immutable metadata models with helpers to read, attach, update, and serialize them. Pandas operations share attached models instead of repeatedly copying metadata.
- Improve metadata lookups with consistent fallbacks for missing values, display names, and inherited properties (`include_inherited=True` for dedicated unit/name helpers).
- Add helpers for default time zones, recording information, default aggregation methods, and copying pandas objects without metadata (`copy_without_metadata`).
- **Breaking:** Only the current metadata conventions are supported. Invalid metadata returns no information. Legacy formats and arbitrary glom specs are removed; queries accept field names and dotted paths.
- Make Plotly optional: install `hdhelpers[plotting]` for plotting helpers. Core metadata and time zone functionality works without it.
- Add Python 3.15 support and update Python/tooling requirements to address the CA certificate security issue.
- Expand validation and regression tests, correct lint configuration, and add CI checks of actual installations without Plotly.

## [0.0.9] - 2026-09-10
- singletsframe support

## [0.0.8] - 2026-07-07
- add new plotting-module to wheel

## [0.0.7] - 2026-07-07
- fix circular import
- set pandas dependency >= 3
- minor improvement in tick formats

## [0.0.6] - 2026-07-06
- add color, locale, Plotly theme, timestamp ticks

## [0.0.5] - 2026-07-06
- Nothing changed

## [0.0.4] - 2026-06-25
- Avoid RangeIndex being modified in modify_timezone
- Enhance documentation of modify_timezone

## [0.0.3] - 2026-06-23
- Fixes in modify_timezone
- Disarm dependencies to ease compatibility to designer development
- Enhance documentation

## [0.0.2] - 2026-05-21
- Include helpers for metadata
- Include helper function for modify timezone
- Publish sphinx documentation on GitHub Pages

## [0.0.1] - 2025-09-11
- Test upload on pypi of hdhelpers
- Note: No tagging used as it was only a test upload on pypi
