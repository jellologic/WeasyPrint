"""Test the ``box-snap`` property."""

from weasyprint.text.line_break import strut

from ..testing_utils import assert_no_logs, render_pages


def get_divs(page):
    return [
        box for box in page.descendants()
        if type(box).__name__ == 'BlockBox' and box.element_tag == 'div']


def grid_origin(page):
    """Return the (pitch, origin) of the root line grid for ``page``."""
    html, = page.children
    pitch, baseline = strut(html.style)
    origin = html.position_y + baseline
    return pitch, origin


HTML = '''
  <style>
    @page { size: 200px 200px; margin: 0 }
    html { line-grid: create; font-family: weasyprint; font-size: 10px;
           line-height: 20px; margin: 0 }
    body { margin: 0 }
    div { height: 10px; margin: 0 }
    div.spacer { height: 5px }
    div.target { %s }
  </style>
  <div class="spacer"></div>
  <div class="target"></div>
'''


@assert_no_logs
def test_box_snap_block_start():
    # The div starts 5px below the content top: its top edge snaps down to
    # the first grid line.
    page, = render_pages(HTML % 'box-snap: block-start')
    spacer, div = get_divs(page)
    pitch, origin = grid_origin(page)
    assert pitch == 20
    assert spacer.position_y == 0
    assert div.position_y > spacer.position_y + spacer.height
    assert abs((div.position_y - origin) % pitch) < 1e-6


@assert_no_logs
def test_box_snap_block_end():
    # The div bottom edge snaps down to the first grid line at or below it.
    page, = render_pages(HTML % 'box-snap: block-end')
    spacer, div = get_divs(page)
    pitch, origin = grid_origin(page)
    bottom = div.position_y + div.border_height()
    assert div.position_y > spacer.position_y + spacer.height
    assert abs((bottom - origin) % pitch) < 1e-6


@assert_no_logs
def test_box_snap_none():
    # Without box-snap the div is not moved.
    page, = render_pages(HTML % '')
    spacer, div = get_divs(page)
    _, origin = grid_origin(page)
    assert div.position_y == 5
    assert abs(div.position_y - origin) > 1e-6
