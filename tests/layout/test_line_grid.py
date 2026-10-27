"""Test the line grid (``line-grid`` / ``line-snap``)."""
from itertools import pairwise
from math import isclose

from weasyprint.formatting_structure import boxes

from ..testing_utils import assert_no_logs, render_pages


def line_baselines(page):
    return [
        line.position_y + line.baseline
        for line in page.descendants()
        if isinstance(line, boxes.LineBox) and line.baseline]


@assert_no_logs
def test_line_snap_baseline():
    # The root element creates a 20pt line grid, and every block with
    # "line-snap: baseline" puts its baselines on grid lines.
    page, = render_pages('''
      <style>
        @page { size: 6in 6in; margin: 0.5in }
        html { font-family: weasyprint; font-size: 16pt;
               line-height: 20pt; line-grid: create }
        p { margin: 0; line-snap: baseline }
        #p1 { font-size: 20pt; line-height: 14pt }
        #p2 { font-size: 8pt; line-height: 9pt }
      </style>
      <p>one</p>
      <p id="p1">two two two two two two</p>
      <p id="p2">three</p>
    ''')
    baselines = line_baselines(page)
    assert len(baselines) >= 3
    pitch = 20 * 96 / 72
    for first, second in pairwise(baselines):
        steps = (second - first) / pitch
        assert abs(steps - round(steps)) < 1e-6, (first, second, steps)


@assert_no_logs
def test_line_snap_without_grid():
    # Without "line-grid: create" on the root, line-snap does nothing:
    # the lines of the middle paragraph keep their 14pt pitch.
    page, = render_pages('''
      <style>
        @page { size: 6in 6in; margin: 0.5in }
        html { font-family: weasyprint; font-size: 16pt; line-height: 20pt }
        p { margin: 0; line-snap: baseline }
        #p1 { font-size: 20pt; line-height: 14pt }
      </style>
      <p>one</p>
      <p id="p1">two two two two two two two two</p>
      <p>three</p>
    ''')
    baselines = line_baselines(page)
    assert len(baselines) >= 3
    diffs = [second - first for first, second in pairwise(baselines)]
    assert any(abs(diff - 14 * 96 / 72) < 1e-6 for diff in diffs)


@assert_no_logs
def test_line_snap_grid_item():
    # Lines snapped inside a grid item are measured at their real
    # position, so the row is as tall as the snapped content.
    text = ''.join(f'<p class="s">line {i}</p>' for i in range(6))
    page, = render_pages('''
      <style>
        @page { size: 6in 6in; margin: 0.5in }
        html { font: 10pt/15pt sans-serif; line-grid: create }
        body { margin: 0 }
        p { margin: 0 }
        .s { line-snap: baseline; line-height: 13pt }
        .g { display: grid; grid-template-columns: 1fr 1fr;
             column-gap: 15pt }
      </style>
      <p style="margin-bottom: 7pt">lead</p>
      <div class="g"><div>%s</div><div><p>short</p></div></div>
      <p class="after">after</p>
    ''' % text)
    snapped = [
        box for box in page.descendants()
        if getattr(box, 'element_tag', '') == 'p' and
        (getattr(box, 'element', None).get('class') or '') == 's']
    # Measurement copies sit at the origin; take the laid-out ones.
    snapped_bottom = max(
        box.position_y + box.margin_height() for box in snapped)
    after_top = max(
        box.position_y for box in page.descendants()
        if getattr(box, 'element_tag', '') == 'p' and
        (getattr(box, 'element', None).get('class') or '') == 'after')
    # The block after the grid starts right at the snapped content's
    # end: the row is neither taller nor shorter than the content.
    assert isclose(after_top, snapped_bottom)
