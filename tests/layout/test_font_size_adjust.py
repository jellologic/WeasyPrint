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


@assert_no_logs
def test_font_size_adjust_without_os2_metrics():
    # Fonts whose OS/2 table has no sCapHeight/sxHeight (version below 2),
    # or that live in a collection (.ttc), must not crash the render: the
    # reference glyph is measured, or the adjustment is skipped.
    # https://github.com/Kozea/WeasyPrint/issues/2161
    render_pages('''
      <style>
        @page { size: 100px 40px; margin: 0 }
        body { margin: 0; font-size: 12px }
        code { font: 12px monospace; font-size-adjust: cap-height 0.7 }
      </style>
      <p><code>H</code></p>
    ''')
    render_pages('''
      <style>
        @page { size: 100px 40px; margin: 0 }
        body { margin: 0; font-size: 12px }
        code { font: 12px monospace; font-size-adjust: ex-height 0.5 }
      </style>
      <p><code>x</code></p>
    ''')
    render_pages('''
      <style>
        @page { size: 100px 40px; margin: 0 }
        body { margin: 0; font: 12px monospace; font-synthesis: none }
      </style>
      <p>x</p>
    ''')
