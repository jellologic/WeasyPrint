"""Test the ``shape-outside`` and ``shape-margin`` properties."""

import pytest

from ..testing_utils import assert_no_logs, capture_logs, render_pages


def line_positions(page):
    return [
        (round(box.position_x, 1), round(box.position_y, 1))
        for box in page.descendants()
        if type(box).__name__ == 'LineBox']


HTML = '''
  <style>
    @page { size: 200px 200px; margin: 10px }
    body { margin: 0; font-family: weasyprint; font-size: 10px;
           line-height: 10px }
    p { margin: 0 }
    .f { float: left; width: 40px; height: 40px; %s }
  </style>
  <div class="f"></div>
  <p>aa aa aa aa aa aa aa aa aa aa aa aa</p>
'''


@assert_no_logs
def test_shape_outside_polygon():
    # A right triangle: the first lines clear the hypotenuse, walking
    # left as it descends, instead of the full rectangle.
    page, = render_pages(HTML % 'shape-outside: polygon(0 0, 100% 0, 0 100%)')
    positions = line_positions(page)
    # The hypotenuse is at x = 40 - y on the float: each line walks 10px
    # to the left.
    assert positions[0][0] == 50
    assert positions[1][0] == 40
    assert positions[2][0] == 30


@assert_no_logs
def test_shape_outside_none():
    # Without a shape the whole rectangle is avoided.
    page, = render_pages(HTML % '')
    positions = line_positions(page)
    assert positions[0][0] == 50
    assert positions[1][0] == 50
    assert positions[2][0] == 50


@assert_no_logs
def test_shape_outside_circle():
    # A circle is narrower than its box at the top: the first line is
    # closer to the float than for a rectangle.
    circle, = render_pages(HTML % 'shape-outside: circle(50%)')
    rectangle, = render_pages(HTML % '')
    circle = line_positions(circle)
    rectangle = line_positions(rectangle)
    # The circle of radius 20 is narrower than the box on the first line
    # band: the line gets a bit closer to the float.
    assert rectangle[0][0] == 50
    assert 40 < circle[0][0] < 50


@assert_no_logs
def test_shape_margin():
    # shape-margin inflates the shape: lines clear it earlier.
    page, = render_pages(HTML % (
        'shape-outside: polygon(0 0, 100% 0, 0 100%); shape-margin: 10px'))
    positions = line_positions(page)
    # The 45° hypotenuse moves right by 10px / cos(45°) on the band.
    assert positions[0][0] == pytest.approx(64.1, abs=0.1)


@assert_no_logs
def test_shape_outside_inset():
    # An inset shape avoids less than the full box.
    page, = render_pages(HTML % 'shape-outside: inset(0 20px 0 0)')
    positions = line_positions(page)
    assert positions[0][0] == 30


@assert_no_logs
def test_shape_outside_invalid():
    # Invalid values are ignored.
    with capture_logs() as logs:
        page, = render_pages(HTML % 'shape-outside: bogus')
    assert len(logs) == 1
    positions = line_positions(page)
    assert positions[0][0] == 50
