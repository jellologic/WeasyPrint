"""Test the ``hanging-punctuation`` property."""

from weasyprint.text.ffi import FROM_UNITS

from ..testing_utils import assert_no_logs, capture_logs, render_pages


def first_glyph_width(line):
    """Return the advance width of the line’s first glyph."""
    for box in line.descendants():
        if type(box).__name__ == 'TextBox':
            try:
                first_line, _ = box.pango_layout.get_first_line()
            except AttributeError:
                # The layout was deactivated after the split.
                box.pango_layout.reactivate(box.style)
                first_line, _ = box.pango_layout.get_first_line()
            glyph_item = first_line.runs[0].data
            return glyph_item.glyphs.glyphs[0].geometry.width * FROM_UNITS
    return 0


def get_lines(page):
    return [
        box for box in page.descendants()
        if type(box).__name__ == 'LineBox']


@assert_no_logs
def test_hanging_punctuation_first():
    # An opening quote at the line start hangs into the margin, and the
    # rest of the line stays aligned on the content edge.
    page, = render_pages('''
      <style>
        @page { size: 100px 100px; margin: 10px }
        body { font-family: weasyprint; font-size: 10px }
        div { hanging-punctuation: first }
        div.none { hanging-punctuation: none }
      </style>
      <div>"abc</div>
      <div class="none">"abc</div>
    ''')
    hanging, normal = get_lines(page)
    quote_width = first_glyph_width(normal)
    assert quote_width > 0
    assert hanging.position_x == normal.position_x - quote_width


@assert_no_logs
def test_hanging_punctuation_first_not_hangable():
    # A line not starting with hangable punctuation is not shifted.
    page, = render_pages('''
      <style>
        @page { size: 100px 100px; margin: 10px }
        body { font-family: weasyprint; font-size: 10px }
        div { hanging-punctuation: first }
      </style>
      <div>abc</div>
    ''')
    line, = get_lines(page)
    assert line.position_x == 10


@assert_no_logs
def test_hanging_punctuation_force_end():
    # A trailing comma that does not fit stays on the line and hangs into
    # the margin.
    page, = render_pages('''
      <style>
        @page { size: 200px 200px; margin: 10px }
        body { font-family: weasyprint; font-size: 10px }
        div { width: 75px }
        div.none { hanging-punctuation: none }
      </style>
      <div style="hanging-punctuation: force-end">aaa bbb,</div>
      <div class="none">aaa bbb,</div>
    ''')
    lines = get_lines(page)
    texts = [
        ''.join(
            box.text for box in line.descendants()
            if type(box).__name__ == 'TextBox')
        for line in lines]
    # Without hanging, the comma wraps to a second line (the space does
    # not let “aaa bbb” fit in 75px with the test font).
    assert texts[:1] == ['aaa bbb,']
    assert texts[1:] == ['aaa', 'bbb,']


@assert_no_logs
def test_hanging_punctuation_invalid():
    with capture_logs() as logs:
        page, = render_pages('''
      <style>
        div { hanging-punctuation: force-end allow-end }
        div + div { hanging-punctuation: bogus }
      </style>
      <div>a</div><div>b</div>
    ''')
    assert len(logs) == 2
    divs = [
        box for box in page.descendants()
        if type(box).__name__ == 'BlockBox' and box.element_tag == 'div']
    # force-end and allow-end are mutually exclusive, unknown values are
    # ignored: both fall back to the initial value.
    assert divs[0].style['hanging_punctuation'] == 'none'
    assert divs[1].style['hanging_punctuation'] == 'none'
