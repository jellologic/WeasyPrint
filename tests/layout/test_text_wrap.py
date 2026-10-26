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
