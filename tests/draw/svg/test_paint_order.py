"""Test ``paint-order`` in SVG images."""

from ...testing_utils import FakeHTML, assert_no_logs


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
