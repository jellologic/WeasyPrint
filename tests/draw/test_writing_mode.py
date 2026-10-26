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


def test_writing_mode_vertical_columns():
    # Wrapped lines stack as vertical-rl columns: the first text is in
    # the rightmost column, the rest to its left.
    w, h, pixels = html_to_pixels('''
      <style>
        @page { size: 60px 100px; margin: 0; background: #fff }
        body { margin: 0; font-family: weasyprint; font-size: 20px;
               line-height: 20px }
        .v { writing-mode: vertical-rl; width: 60px; height: 100px }
        .r { color: red } .b { color: blue }
      </style>
      <div class="v"><span class="r">aaaa</span>
        <span class="b">bbbb cccc dddd</span></div>
    ''')
    red_xs, blue_xs = [], []
    for y in range(h):
        for x in range(w):
            r, g, b = pixels[y * w + x][:3]
            if r > 200 and g < 100 and b < 100:
                red_xs.append(x)
            elif b > 200 and r < 100 and g < 100:
                blue_xs.append(x)
    assert red_xs
    assert blue_xs
    # The first text is in the rightmost column(s), the rest to the left.
    assert min(red_xs) > max(blue_xs)


def test_writing_mode_vertical_lr_columns():
    # vertical-lr: columns stack left-to-right (mirrored from rl).
    w, h, pixels = html_to_pixels('''
      <style>
        @page { size: 60px 100px; margin: 0; background: #fff }
        body { margin: 0; font-family: weasyprint; font-size: 20px;
               line-height: 20px }
        .v { writing-mode: vertical-lr; width: 60px; height: 100px }
        .r { color: red } .b { color: blue }
      </style>
      <div class="v"><span class="r">aaaa</span>
        <span class="b">bbbb cccc dddd</span></div>
    ''')
    red_xs, blue_xs = [], []
    for y in range(h):
        for x in range(w):
            r, g, b = pixels[y * w + x][:3]
            if r > 200 and g < 100 and b < 100:
                red_xs.append(x)
            elif b > 200 and r < 100 and g < 100:
                blue_xs.append(x)
    assert red_xs
    assert blue_xs
    # The first text is in the leftmost column(s), the rest to the right.
    assert max(red_xs) < min(blue_xs)


def test_writing_mode_sideways_lr():
    # sideways-lr: the lines stack left-to-right (the first line's
    # column at the left).
    w, h, pixels = html_to_pixels('''
      <style>
        @page { size: 100px 60px; margin: 0; background: #fff }
        body { margin: 0; font-family: weasyprint; font-size: 20px;
               line-height: 20px }
        .v { writing-mode: sideways-lr; width: 100px; height: 60px }
        .r { color: red } .b { color: blue }
      </style>
      <div class="v"><span class="r">aaaa</span>
        <span class="b">bbbb cccc</span></div>
    ''')
    red_xs, blue_xs = [], []
    for y in range(h):
        for x in range(w):
            r, g, b = pixels[y * w + x][:3]
            if r > 200 and g < 100 and b < 100:
                red_xs.append(x)
            elif b > 200 and r < 100 and g < 100:
                blue_xs.append(x)
    assert red_xs
    assert blue_xs
    # The first line's column is at the left, the rest to the right.
    assert max(red_xs) < min(blue_xs)
