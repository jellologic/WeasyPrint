"""Test ``paint-order`` in SVG images."""

from ...testing_utils import FakeHTML, assert_no_logs
from .. import html_to_pixels


def operators(paint_order):
    html = f'''
      <style>@page {{ size: 100px 100px; margin: 0 }}</style>
      <svg width="100" viewBox="0 0 100 100">
        <rect x="10" y="10" width="80" height="80" fill="red"
              stroke="black" stroke-width="4" paint-order="{paint_order}"/>
      </svg>
    '''
    pdf = FakeHTML(string=html).write_pdf(uncompressed_pdf=True)
    return pdf.decode()


@assert_no_logs
def test_paint_order_stroke_first():
    # paint-order: stroke strokes the path and fills it on top.
    content = operators('stroke')
    assert '\nS\nf\n' in content


@assert_no_logs
def test_paint_order_default():
    # The default paints fill and stroke together in one operator.
    content = operators('normal')
    assert '\nB\n' in content


@assert_no_logs
def test_paint_order_whole_run_halo():
    # paint-order="stroke" strokes the whole run before filling it: a
    # wide halo does not erase the previous glyphs’ fills. No dark pixel
    # of the unstroked render may be visibly lightened by the halo.
    # https://github.com/Kozea/WeasyPrint/issues/2322
    def render(stroke_width):
        return html_to_pixels(f'''
          <style>
            @page {{ size: 320px 70px; margin: 0; background: #fff }}
          </style>
          <svg width="320" height="70" style="background: #fff">
            <text x="10" y="45" font-size="30" fill="black"
              stroke="{'white' if stroke_width else 'none'}"
              stroke-width="{stroke_width}" stroke-linejoin="round"
              paint-order="stroke">Diameter Height</text></svg>
        ''')

    _, height, unstroked_data = render(0)
    _, _, stroked_data = render(15)
    visible = sum(
        1 for y in range(height) for x in range(320)
        if max(unstroked_data[y * 320 + x][:3]) < 200 and (
            max(stroked_data[y * 320 + x][:3]) -
            max(unstroked_data[y * 320 + x][:3])) > 64)
    assert visible == 0
