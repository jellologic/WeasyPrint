"""Test the ``text-box-trim`` and ``text-box-edge`` properties."""

from fontTools.ttLib import TTFont

from ..testing_utils import assert_no_logs, capture_logs, render_pages, resource_path


def get_p(page):
    return [
        box for box in page.descendants()
        if type(box).__name__ == 'BlockBox' and box.element_tag == 'p']


def get_lines(page):
    return [
        box for box in page.descendants()
        if type(box).__name__ == 'LineBox']


HTML = '''
  <style>
    @page {{ size: 200px 200px; margin: 10px }}
    body {{ font-family: weasyprint; font-size: 10px }}
    p {{ line-height: 20px; margin: 0; {trim} }}
  </style>
  <p>abc</p>
'''


@assert_no_logs
def test_text_box_trim_none():
    page, = render_pages(HTML.format(trim=''))
    p, = get_p(page)
    assert p.height == 20


@assert_no_logs
def test_text_box_trim_both_cap_alphabetic():
    # trim-both with cap alphabetic: the block is as tall as the distance
    # from the cap height to the baseline.
    font = TTFont(resource_path('weasyprint.otf'))
    cap_ratio = font['OS/2'].sCapHeight / font['head'].unitsPerEm
    page, = render_pages(HTML.format(
        trim='text-box-trim: trim-both; text-box-edge: cap alphabetic'))
    p, = get_p(page)
    line, = get_lines(page)
    start = line.baseline - cap_ratio * 10
    end = 20 - line.baseline
    assert abs(p.height - (20 - start - end)) < 0.01
    # The cap height sits on the content box top edge.
    assert abs(line.position_y - (p.position_y - start)) < 0.01


@assert_no_logs
def test_text_box_trim_start():
    # trim-start only trims above the cap height.
    font = TTFont(resource_path('weasyprint.otf'))
    cap_ratio = font['OS/2'].sCapHeight / font['head'].unitsPerEm
    page, = render_pages(HTML.format(
        trim='text-box-trim: trim-start; text-box-edge: cap'))
    p, = get_p(page)
    line, = get_lines(page)
    start = line.baseline - cap_ratio * 10
    assert abs(p.height - (20 - start)) < 0.01
    assert abs(line.position_y - (p.position_y - start)) < 0.01


@assert_no_logs
def test_text_box_trim_end():
    # trim-end only trims below the baseline.
    page, = render_pages(HTML.format(
        trim='text-box-trim: trim-end; text-box-edge: alphabetic'))
    p, = get_p(page)
    line, = get_lines(page)
    assert abs(p.height - line.baseline) < 0.01
    assert line.position_y == p.position_y


@assert_no_logs
def test_text_box_trim_validation():
    with capture_logs() as logs:
        page, = render_pages('''
      <style>
        @page { size: 200px 200px; margin: 10px }
        body { font-family: weasyprint; font-size: 10px }
        p { line-height: 20px; margin: 0; text-box-trim: bogus;
            text-box-edge: cap bogus }
      </style>
      <p>abc</p>
    ''')
    assert len(logs) == 2
    p, = get_p(page)
    # Invalid values are ignored.
    assert p.style['text_box_trim'] == 'none'
    assert p.style['text_box_edge'] == ('text', 'alphabetic')
    assert p.height == 20
