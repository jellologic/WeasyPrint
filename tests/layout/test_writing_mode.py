"""Test the ``writing-mode`` property."""

from ..testing_utils import assert_no_logs, capture_logs, render_pages

HTML = '''
  <style>
    @page { size: 100px 100px; margin: 0 }
    body { margin: 0; font-family: weasyprint; font-size: 20px;
           line-height: 20px }
    .head { width: 20px; height: 80px; %s }
  </style>
  <div class="head">Head</div>
'''


@assert_no_logs
def test_writing_mode_vertical_geometry():
    # A vertical block keeps the author's dimensions and lays its text
    # along the box height (the swapped inline axis).
    page, = render_pages(HTML % 'writing-mode: vertical-rl')
    html, = page.children
    body, = html.children
    head, = body.children
    assert head.width == 20
    assert head.height == 80
    line, = head.children
    # The line is laid in the swapped frame: its width is the text run
    # (along the box height), its height the column thickness.
    assert line.width <= 80
    assert line.height == 20


@assert_no_logs
def test_writing_mode_horizontal():
    page, = render_pages(HTML % '')
    html, = page.children
    body, = html.children
    head, = body.children
    assert head.width == 20
    assert head.height == 80
    line, = head.children
    assert line.width <= 80
    assert line.height == 20


@assert_no_logs
def test_writing_mode_validation():
    with capture_logs() as logs:
        page, = render_pages('''
      <style>
        div { writing-mode: bogus }
        div + div { writing-mode: sideways-lr }
      </style>
      <div>a</div><div>b</div>
    ''')
    assert len(logs) == 1
    html, = page.children
    body, = html.children
    first, second = body.children
    # Unknown values are ignored.
    assert first.style['writing_mode'] == 'horizontal-tb'
    assert second.style['writing_mode'] == 'sideways-lr'


@assert_no_logs
def test_writing_mode_percentage_height():
    # Percentage heights resolve against the containing block: the
    # vertical text lays within the resolved 100px height.
    page, = render_pages('''
      <style>
        @page { size: 300px 300px; margin: 0 }
        body { margin: 0; font-family: weasyprint; font-size: 20px;
               line-height: 20px }
        .wrap { height: 200px }
        .head { writing-mode: vertical-rl; width: 20px; height: 50% }
      </style>
      <div class="wrap"><div class="head">Head</div></div>
    ''')
    html, = page.children
    body, = html.children
    wrap, = body.children
    head, = wrap.children
    assert head.width == 20
    assert head.height == 100
    line, = head.children
    assert line.width <= 100
