"""Test the ``font-size-adjust`` property."""
from fontTools.ttLib import TTFont

from ..testing_utils import assert_no_logs, render_pages, resource_path


@assert_no_logs
def test_font_size_adjust_cap_height():
    # used size = font-size * adjust / cap-ratio, so a 100px font with
    # adjust 0.5 renders at 100 * 0.5 / cap-ratio. The cap ratio is read
    # from the same font file the test font family resolves to.
    font = TTFont(resource_path('weasyprint.otf'))
    ratio = font['OS/2'].sCapHeight / font['head'].unitsPerEm
    page, = render_pages('''
      <style>
        @page { size: 400px 400px; margin: 0 }
        body { font-family: weasyprint; font-size: 100px }
        div { font-size-adjust: cap-height 0.5 }
      </style>
      <div>xxx</div>
    ''')
    line = next(
        box for box in page.descendants()
        if type(box).__name__ == 'LineBox')
    used_size = line.height
    expected = 100 * 0.5 / ratio
    assert abs(used_size - expected) < 0.01


@assert_no_logs
def test_font_size_adjust_from_font():
    # 'from-font' computes the adjustment from the first available font's
    # own metric, so that font renders at its natural (unadjusted) size.
    for value in ('from-font', 'cap-height from-font', 'ex-height from-font'):
        page, = render_pages(f'''
          <style>
            @page {{ size: 400px 400px; margin: 0 }}
            body {{ font-family: weasyprint; font-size: 100px }}
          </style>
          <div>xxx</div>
          <div style="font-size-adjust: {value}">xxx</div>
        ''')
        lines = [
            box for box in page.descendants()
            if type(box).__name__ == 'LineBox']
        assert lines[1].height == lines[0].height
