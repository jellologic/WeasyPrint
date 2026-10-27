"""Test where vertical writing modes place their text.

Layout boxes are correct for all modes; these tests check glyph
placement (an off-transform draw put the text beside the box).
"""
from ..testing_utils import assert_no_logs
from . import html_to_pixels


def ink_boxes():
    """Text ink bounds for the four modes in a bordered, offset box."""
    result = {}
    for wm in ('vertical-rl', 'vertical-lr', 'sideways-rl', 'sideways-lr'):
        w, h, pixels = html_to_pixels(f'''
          <style>
            @page {{ size: 192px 240px; margin: 0; background: #fff }}
            body {{ margin: 0; font: 600 9pt/12pt sans-serif }}
            div {{ position: absolute; left: 40px; top: 30px;
                  width: 40px; height: 120px; border: 1px solid;
                  writing-mode: {wm} }}
          </style>
          <div>Elec AB</div>
        ''')
        points = [
            (x, y) for y in range(h) for x in range(w)
            if tuple(pixels[y * w + x]) != (255, 255, 255)
            and 41 < x < 80 and 31 < y < 150]
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        result[wm] = (min(xs), max(xs), min(ys), max(ys))
    return result


def test_vertical_rl_placement():
    # vertical-rl: first column at the right, reading top-to-bottom.
    x0, x1, y0, y1 = ink_boxes()['vertical-rl']
    assert x0 > 55  # at the right of the content box
    assert 31 <= y0 <= 35  # starts at the top


def test_vertical_lr_placement():
    # vertical-lr: first column at the left, reading top-to-bottom.
    x0, x1, y0, y1 = ink_boxes()['vertical-lr']
    assert x1 < 60  # at the left of the content box
    assert 31 <= y0 <= 35


def test_sideways_rl_placement():
    # sideways-rl: like vertical-rl for horizontal text.
    x0, x1, y0, y1 = ink_boxes()['sideways-rl']
    assert x0 > 55
    assert 31 <= y0 <= 35


def test_sideways_lr_placement():
    # sideways-lr: reads bottom-to-top: the text starts at the bottom.
    x0, x1, y0, y1 = ink_boxes()['sideways-lr']
    assert x1 < 60  # at the left of the content box
    assert 145 <= y1 <= 149  # ends at the bottom of the content box


@assert_no_logs
def test_vertical_lr_glyph_orientation():
    # vertical-lr glyphs are rotated like vertical-rl glyphs (90°
    # clockwise), with only the column progression reversed: each row
    # of the vertical-lr render has the same ink as the mirrored row of
    # the vertical-rl render. The broken reflection drew the glyphs
    # mirrored, with different per-row ink.
    def render(wm):
        w, h, pixels = html_to_pixels(f'''
          <style>
            @page {{ size: 192px 240px; margin: 0; background: #fff }}
            body {{ margin: 0; font: 600 9pt/12pt sans-serif }}
            div {{ position: absolute; left: 40px; top: 30px;
                  width: 40px; height: 120px; border: 1px solid;
                  writing-mode: {wm} }}
          </style>
          <div>Elec AB</div>
        ''')
        return pixels

    rl = render('vertical-rl')
    lr = render('vertical-lr')

    def dark_rows(pixels):
        rows = []
        for y in range(31, 150):
            rows.append(sum(
                1 for x in range(41, 80)
                if max(pixels[y * 192 + x][:3]) < 128))
        return rows

    rl_rows = dark_rows(rl)
    lr_rows = dark_rows(lr)
    # The mirror maps columns left-to-right, preserving per-row ink;
    # allow a small AA tolerance per row.
    for rl_count, lr_count in zip(rl_rows, lr_rows):
        assert abs(rl_count - lr_count) <= 2, (rl_count, lr_count)
    assert sum(rl_rows) > 100
