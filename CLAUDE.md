# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

WeasyPrint is a visual rendering engine for HTML and CSS that exports to PDF. It is **not** built on a browser engine (WebKit/Gecko) — the CSS layout engine is pure Python, designed for pagination. The public API surface is intentionally small: everything exported from the top-level `weasyprint` package (`HTML`, `CSS`, `Attachment`, `default_url_fetcher`).

## Common commands

Setup (editable install with doc + test extras):

```shell
python -m venv venv
venv/bin/pip install -e '.[doc,test]'
```

Run the tool:

```shell
venv/bin/python -m weasyprint example.html example.pdf
```

Tests (pytest; CI runs with `-n auto` via pytest-xdist):

```shell
venv/bin/python -m pytest                       # full suite
venv/bin/python -m pytest tests/test_api.py      # single file
venv/bin/python -m pytest tests/layout/test_table.py::test_table_simple   # single test
venv/bin/python -m pytest -n auto                # parallel
```

Lint (must pass in CI):

```shell
venv/bin/python -m ruff check
```

Build docs:

```shell
venv/bin/sphinx-build docs docs/_build
```

### Test requirements
Tests require **Ghostscript** on PATH — `tests/conftest.py` shells out to `gs` to rasterize generated PDFs to PNG so visual output can be asserted pixel-by-pixel (see `tests/testing_utils.py` and `tests/draw/`). On Linux the **DejaVu fonts** must also be installed. Text/font work also depends on the **Pango** native library (loaded via cffi).

## Rendering pipeline (the big picture)

A render flows through clearly separated stages, mirroring how a browser works. `HTML.render()` → `Document._render()` in `document.py` orchestrates them:

1. **Parse HTML** — `HTML` class (`__init__.py`) uses `tinyhtml5` to produce a DOM-like ElementTree.
2. **Parse CSS** — `CSS` class uses `tinycss2`; the `css/` package pre-processes: validates/ignores unknown declarations, expands shorthands, replaces hyphens with underscores in property names (`margin-top` → `margin_top`), and pre-compiles selectors with `cssselect2`.
3. **Cascade + compute** — `css/__init__.py:get_all_computed_styles` applies the cascade and returns a `style_for(element, pseudo_type)` accessor. `css/computed_values.py` turns specified values into computed values (units → pixels, etc.).
4. **Build formatting structure** — `formatting_structure/build.py:build_formatting_structure` turns the styled element tree into a tree of rectangular **boxes** (`formatting_structure/boxes.py` holds the box class hierarchy). Logic is driven by the `display` property; per-element overrides live in `html.py` (e.g. `<img>`, `<td colspan>`). Most of HTML's behavior is defined in CSS via the user-agent stylesheets `css/html5_ua.css`, `css/html5_ph.css`, `css/html5_ua_form.css`.
5. **Layout** — `layout/__init__.py:layout_document` assigns fixed dimensions and positions, breaking content across pages. The `layout/` package is split by concern: `block.py`, `inline.py`, `table.py`, `flex.py`, `grid.py`, `float.py`, `absolute.py`, `column.py`, `page.py`, plus `preferred.py`/`min_max.py` for intrinsic sizing. A `LayoutContext` carries shared state (styles, image fetcher, fonts, target collector for cross-references).
6. **Draw** — for each `Page`, boxes are reordered for stacking (`stacking.py`) and painted into a `pydyf` PDF stream (`draw/` package; `draw/border.py`, `draw/text.py`, `draw/color.py`).
7. **PDF assembly** — `pdf/` package adds metadata, attachments, hyperlinks, bookmarks/tags, and applies variants. PDF/A, PDF/UA, PDF/X live in `pdf/pdfa.py`, `pdf/pdfua.py`, `pdf/pdfx.py`; accessibility tags in `pdf/tags.py`.

Key boundary: stages 1–5 produce an immutable laid-out `Document` (list of `Page` objects); `Document.write_pdf()` does stage 6–7. You can call `render()` once and `write_pdf()` multiple times.

## Subsystem map

- `weasyprint/__init__.py` — public API (`HTML`, `CSS`), `DEFAULT_OPTIONS` (the canonical list of every render option; both `render()` and `write_pdf()` validate against it and `LOGGER.error` on unknown keys).
- `weasyprint/document.py` — `Document`, `Page`, render orchestration, disk image cache.
- `weasyprint/html.py` — HTML-specific element handling and presentational hints.
- `weasyprint/images.py` — raster/SVG image loading and embedding.
- `weasyprint/svg/` — self-contained SVG renderer (shapes, paths, text, gradients).
- `weasyprint/text/` — text shaping via Pango through cffi (`text/ffi.py` is the native binding layer), font handling, line breaking.
- `weasyprint/css/validation/` — per-property value parsing and validation.

## Conventions

- **CSS property names use underscores internally** (`margin_top`, not `margin-top`) everywhere after parsing.
- **ruff** enforces style: single quotes (inline and multiline), and the rule set in `pyproject.toml` (`E,W,F,I,N,RUF,T20,PIE,PT,RSE,UP,Q`). `T20` means no stray `print()` — use `weasyprint/logger.py` (`LOGGER`, `PROGRESS_LOGGER`) instead.
- Python 3.10+ (tested on CPython 3.10–3.14 and PyPy).
- Native dependencies (Pango, and Ghostscript for tests) are loaded at runtime; pure-Python deps are pinned in `pyproject.toml`.

## Tests layout

`tests/` mirrors the engine stages: `test_boxes.py` (formatting structure), `tests/layout/` (per-layout-feature), `tests/draw/` (pixel-level visual diffs via Ghostscript rasterization), `tests/css/`, `test_pdf.py`, `test_text.py`, `test_api.py`. Visual tests compare rendered PNGs against expected pixel maps defined inline in the test files.
