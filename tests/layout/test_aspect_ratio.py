"""Test the ``aspect-ratio`` property on block-level boxes."""
from ..testing_utils import assert_no_logs, render_pages


def find_div(page):
    return next(
        box for box in page.descendants()
        if getattr(box, 'element_tag', '') == 'div')


@assert_no_logs
def test_aspect_ratio_height_from_width():
    # width: 200px, height auto, ratio 2/1 -> height 100px
    page, = render_pages('''
      <style>
        @page { size: 400px 400px; margin: 0 }
        div { width: 200px; aspect-ratio: 2 / 1 }
      </style>
      <div></div>
    ''')
    div = find_div(page)
    assert abs(div.width - 200) < 0.01
    assert abs(div.height - 100) < 0.01


@assert_no_logs
def test_aspect_ratio_width_from_height():
    # height: 100px, width auto, ratio 2/1 -> width 200px
    page, = render_pages('''
      <style>
        @page { size: 400px 400px; margin: 0 }
        div { height: 100px; aspect-ratio: 2 / 1 }
      </style>
      <div></div>
    ''')
    div = find_div(page)
    assert abs(div.width - 200) < 0.01
    assert abs(div.height - 100) < 0.01


@assert_no_logs
def test_aspect_ratio_single_number():
    # ratio 0.5 with width 100px -> height 200px
    page, = render_pages('''
      <style>
        @page { size: 400px 400px; margin: 0 }
        div { width: 100px; aspect-ratio: 0.5 }
      </style>
      <div></div>
    ''')
    div = find_div(page)
    assert abs(div.width - 100) < 0.01
    assert abs(div.height - 200) < 0.01
