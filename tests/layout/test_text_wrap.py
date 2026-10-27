"""Test ``text-wrap: balance`` on single-run text blocks."""
from ..testing_utils import assert_no_logs, render_pages


def line_widths():
    page, = render_pages('''
      <style>
        @page { size: 200px 200px; margin: 0 }
        body { font-family: weasyprint; font-size: 16px }
        div { width: 128px }
      </style>
      <div>aaaa bb cc</div>
    ''')
    return [
        line.width for line in page.descendants()
        if type(line).__name__ == 'LineBox']


@assert_no_logs
def test_text_wrap_balance():
    # Greedy wrapping at 128px gives lines 'aaaa bb' (112px) and 'cc'
    # (32px). balance narrows the line width to 80px so the two lines
    # equalise while keeping the same line count.
    assert line_widths() == [112, 32]


@assert_no_logs
def test_text_wrap_balance_applied():
    page, = render_pages('''
      <style>
        @page { size: 200px 200px; margin: 0 }
        body { font-family: weasyprint; font-size: 16px }
        div { width: 128px; text-wrap: balance }
      </style>
      <div>aaaa bb cc</div>
    ''')
    lines = [
        line for line in page.descendants()
        if type(line).__name__ == 'LineBox']
    assert len(lines) == 2
    assert lines[0].width == 64
    assert lines[1].width == 80


@assert_no_logs
def test_text_wrap_pretty():
    # pretty re-breaks the last lines to avoid a short last line: the
    # lone 'cc' gains the previous word.
    page, = render_pages('''
      <style>
        @page { size: 200px 200px; margin: 0 }
        body { font-family: weasyprint; font-size: 16px }
        div { width: 128px; text-wrap: pretty }
      </style>
      <div>aaaa bb cc</div>
    ''')
    lines = [
        line for line in page.descendants()
        if type(line).__name__ == 'LineBox']
    assert len(lines) == 2
    assert lines[0].width == 64
    assert lines[1].width == 80


@assert_no_logs
def test_text_wrap_style_longhand():
    # The text-wrap-style longhand applies like the shorthand value.
    page, = render_pages('''
      <style>
        @page { size: 200px 200px; margin: 0 }
        body { font-family: weasyprint; font-size: 16px }
        div { width: 128px; text-wrap-style: pretty }
      </style>
      <div>aaaa bb cc</div>
    ''')
    lines = [
        line for line in page.descendants()
        if type(line).__name__ == 'LineBox']
    assert len(lines) == 2
    assert lines[0].width == 64
    assert lines[1].width == 80


@assert_no_logs
def test_text_wrap_shorthand_expansion():
    # text-wrap expands into the text-wrap-style and text-wrap-mode
    # longhands.
    page, = render_pages('''
      <style>
        @page { size: 200px 200px; margin: 0 }
        body { font-family: weasyprint; font-size: 16px }
        div { text-wrap: balance }
        p { text-wrap: nowrap }
        section { text-wrap: pretty nowrap }
      </style>
      <div>x</div>
      <p>x</p>
      <section>x</section>
    ''')
    boxes = {}
    for box in page.descendants():
        tag = getattr(box, 'element_tag', '')
        if tag in ('div', 'p', 'section') and type(box).__name__ == 'BlockBox':
            boxes[tag] = box
    assert boxes['div'].style['text_wrap_style'] == 'balance'
    assert boxes['div'].style['text_wrap_mode'] == 'wrap'
    assert boxes['p'].style['text_wrap_style'] == 'auto'
    assert boxes['p'].style['text_wrap_mode'] == 'nowrap'
    assert boxes['section'].style['text_wrap_style'] == 'pretty'
    assert boxes['section'].style['text_wrap_mode'] == 'nowrap'
