"""Test how vertical writing mode is drawn."""

from ..draw import html_to_pixels


def test_writing_mode_rotation():
    # The vertical rendering is exactly the horizontal rendering rotated
    # 90° clockwise: vertical[x', y'] == horizontal[y', H - 1 - x'].
    hw, hh, hpixels = html_to_pixels('''
      <style>
        @page { size: 80px 20px; margin: 0; background: #fff }
        body { margin: 0; font-family: weasyprint; font-size: 20px;
               line-height: 20px }
        div { width: 80px; height: 20px }
      </style>
      <div>Head</div>
    ''')
    vw, vh, vpixels = html_to_pixels('''
      <style>
        @page { size: 20px 80px; margin: 0; background: #fff }
        body { margin: 0; font-family: weasyprint; font-size: 20px;
               line-height: 20px }
        div { width: 20px; height: 80px; writing-mode: vertical-rl }
      </style>
      <div>Head</div>
    ''')
    assert (vw, vh) == (hh, hw)
    for x in range(vw):
        for y in range(vh):
            assert vpixels[y * vw + x] == hpixels[y + (hh - 1 - x) * hw], (
                x, y)
